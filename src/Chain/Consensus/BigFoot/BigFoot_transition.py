from Chain.Parameters import Parameters
import Chain.Consensus.HighLevelSync as Sync

import Chain.Consensus.BigFoot.BigFoot_messages as BigFoot_messages
import Chain.Consensus.Rounds as Rounds


def propose(state, event):
    time = event.time

    # attempt to create block
    block, creation_time = state.create_BigFoot_block(time)

    if block is None:
        # if there is still time in the round, attempt to reschedule later when txions might be there
        if creation_time + 1 + Parameters.execution['creation_time'] <= state.timeout.time:
            BigFoot_messages.schedule_propose(state, creation_time + 1)
        else:
            print(
                f"Block creationg failed at {time} for CP {state.NAME}")
    else:
        # block created, change state, and broadcast it.
        state.state = 'pre_prepared'
        state.block = block.copy()

        BigFoot_messages.broadcast_pre_prepare(state, time, block)

    return 'handled'


def pre_prepare(state, event):
    time = event.time
    block = event.payload['block']

    # validate message: old (invalid), current (continue processing), future (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        return 'invalid'
    if future is not None:
        return future
    time += Parameters.execution["msg_val_delay"]

    # if node is a new round state (i.e waiting for a new block to be proposed)
    match state.state:
        case 'new_round':
            # validate block
            time += Parameters.execution["block_val_delay"]

            if state.validate_block(block):
                # store block as current block
                state.block = event.payload['block'].copy()
                # change state to pre_prepared since block was accepted
                state.state = 'pre_prepared'

                # broadcast preare message
                BigFoot_messages.broadcast_prepare(state, time, state.block)

                # count own vote
                state.process_vote('prepare', state.node,
                                   state.rounds.round, time)

                return 'new_state'  # state changed (will check backlog)
            else:
                # if the block was invalid begin round change
                Rounds.change_round(state.node, time)
                return 'handled'  # event handled but state did not change
        case 'pre_prepared':
            # consider raising an error as 2 nodes cannot propose block at
            # the same round maybe its possible if a node has not realised
            # its not synced but that node should be on an older round
            return 'invalid'
        case 'prepared':
            return 'invalid'  # as above
        case 'round_change':
            return 'invalid'  # node has decided to skip this round
        case _:
            raise ValueError(
                f"Unexpected state '{state.state} for cp BigFoot...'")


def prepare(state, event):
    time = event.time
    block = event.payload['block']
    round = state.rounds.round

    # validate message: old (invalid), current (continue processing), future (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        return 'invalid'
    if future is not None:
        return future
    time += Parameters.execution["msg_val_delay"]

    match state.state:
        case 'pre_prepared':
            # count prepare vote
            state.process_vote('prepare', event.creator,
                               state.rounds.round, time)

            if not state.fast_path:
                #################### SLOW PATH/RECOVERY ##########################
                # leader does not issue a prepare message (thus 2f required votes)
                if state.count_votes('prepare', round) >= Parameters.application["required_messages"] - 1:
                    # change to prepared
                    state.state = 'prepared'
                    # broadcast commit message
                    BigFoot_messages.broadcast_commit(state, time, block)
                    # count own vote
                    state.process_vote('commit', state.node,
                                       state.rounds.round, time)
                    return 'new_state'
                return "handled"
            else:
                #################### FAST PATH ##########################
                # leader does not issue a prepare message (thus N-1)
                if state.count_votes('prepare', round) == Parameters.application["Nn"] - 1:
                    state.node.add_block(state.block, time)

                    if state.node.id == state.miner:
                        BigFoot_messages.broadcast_new_block(
                            state, time, block)

                    state.start(state.rounds.round + 1, time)
                    return 'new_state'

                # not enough votes yet...
                return "handled"
        case 'new_round':
            return 'backlog'  # node has yet to receive enough pre_prepare messages
        case 'prepared':
            return 'invalid'  # node has allready received enough prepared votes
        case 'round_change':
            return 'invalid'  # node has decided to skip this round
        case _:
            raise ValueError(
                f"Unexpected state '{state.state} for cp BigFoot...'")


def commit(state, event):
    time = event.time
    block = event.payload['block']
    round = state.rounds.round

    # validate message: old (invalid), current (continue processing), future (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        return 'invalid'
    if future is not None:
        return future
    time += Parameters.execution["msg_val_delay"]

    match state.state:
        case 'prepared':
            # count vote
            state.process_vote('commit', event.creator,
                               state.rounds.round, time)
            # if we have enough votes
            if state.count_votes('commit', round) >= Parameters.application["required_messages"]:
                # add block to BC
                state.node.add_block(state.block, time)
                # if miner: broadcase new block to nodes
                if state.node.id == state.miner:
                    BigFoot_messages.broadcast_new_block(state, time, block)
                # start new round
                state.start(state.rounds.round + 1, time)

                return 'new_state'
            # not enough votes yet...
            return 'handled'
        case 'new_round':
            return 'backlog'  # node is behind in votes... add to backlog
        case "pre_prepared":
            return 'backlog'  # node is behind in votes... add to blocklog
        case 'round_change':
            return 'invalid'  # node has decided to skip this round
        case _:
            raise ValueError(
                f"Unexpected state '{state.state} for cp BigFoot...'")


def new_block(state, event):
    block = event.payload['block']
    time = event.time

    time += Parameters.execution["msg_val_delay"]
    time += Parameters.execution["block_val_delay"]

    if block.depth <= state.node.blockchain[-1].depth:
        return "invalid"  # old block: ingore
    elif block.depth > state.node.blockchain[-1].depth + 1:
        # future block: initiate sync
        if state.node.state.synced:
            state.node.state.synced = False
            Sync.create_local_sync_event(state.node, event.creator, time)
        # if not synced then we have to wait for ohter blocks in order to validate this so we cannot accept it
        return "handled"
    else:  # valid block
        # update_round if necessary
        state.rounds.round = event.payload['round']

        # add block and start new round
        state.node.add_block(block.copy(), time)

        state.start(event.payload['round']+1, time)

        return "handled"
