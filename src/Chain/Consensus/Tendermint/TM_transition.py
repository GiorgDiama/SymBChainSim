from Chain.Parameters import Parameters

import Chain.Consensus.HighLevelSync as Sync
import Chain.Consensus.Tendermint.TM_messages as messages
import Chain.Consensus.Rounds as Rounds

from Chain.Network import Network


def propose(state, event):
    time = event.time
    
    # attempt to create block
    block, creation_time = state.create_block(time)

    if block is None:
        when_next = 0.1
        if len(state.node.pool) >= 1:
            when_next = state.node.pool[0].timestamp
        # if there is still time in the round, attempt to reschedule later when txions might be there
        if creation_time + when_next + Parameters.execution['creation_time'] <= state.timeout.time:
            messages.schedule_propose(state, when_next)
    else:
        time = creation_time
        # block created, change state, and broadcast it.
        state.state = 'pre_prepared'
        state.block = block.copy()
        # create the votes extra_data field and log votes
        state.block.extra_data['votes'] = {
            'pre_prepare': [], 'prepare': [], 'commit': []}
        state.block.extra_data['votes']['pre_prepare'].append((
            event.creator.id, time, Network.size(event)))
        messages.broadcast_pre_prepare(state, time, block)

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
                # create the votes extra_data field and log votes
                state.block.extra_data['votes'] = {
                    'pre_prepare': [], 'prepare': [], 'commit': []}
                
                state.block.extra_data['votes']['pre_prepare'].append((
                    event.creator.id, time, Network.size(event)))

                # change state to pre_prepared since block was accepted
                state.state = 'pre_prepared'

                # broadcast prepare message
                messages.broadcast_prepare(state, time, state.block)

                # count own vote
                state.process_vote('prepare', state.node,
                                   state.rounds.round, time)

                state.block.extra_data['votes']['prepare'].append((
                    event.actor.id, time, Network.size(event)))
                
                return 'new_state'  # state changed (will check backlog)
            else:
                # if the block was invalid begin round change
                Rounds.change_round(state.node, time)
                return 'handled'  # event handled but state did not change
        case 'pre_prepared':
            return 'invalid'
        case 'prepared':
            return 'invalid'
        case 'round_change':
            return 'invalid'  # node has decided to skip this round
        case _:
            raise ValueError(
                f"Unexpected state '{state.state} for cp PBFT...'")


def prepare(state, event):
    time = event.time
    block = state.block
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
            state.block.extra_data['votes']['prepare'].append((
                event.creator.id, time, Network.size(event)))
            # if we have enough prepare messages (2f messages since leader does not participate)
            if state.count_votes('prepare', round) >= Parameters.application["required_messages"] - 1:
                # change to prepared
                state.state = 'prepared'
                # broadcast commit message
                messages.broadcast_commit(state, time, block)
                # count own vote
                state.process_vote('commit', state.node,
                                   state.rounds.round, time)
                state.block.extra_data['votes']['commit'].append((
                    event.actor.id, time, Network.size(event)))
                return 'new_state'
            # not enough votes yet...
            return 'handled'
        case 'new_round':
            return 'backlog'  # node has yet to receive enough pre_prepare messages
        case 'prepared':
            return 'invalid'  # node has already received enough prepared votes
        case 'round_change':
            return 'invalid'  # node has decided to skip this round
        case _:
            raise ValueError(
                f"Unexpected state '{state.state} for cp PBFT...'")


def commit(state, event):
    time = event.time
    block = state.block
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
            state.process_vote('commit', event.creator, state.rounds.round, time) # count vote
            state.block.extra_data['votes']['commit'].append(
                (event.creator.id, time, Network.size(event)))
            # if we have enough votes
            if state.count_votes('commit', round) >= Parameters.application["required_messages"]: 
                state.node.add_block(state.block, time) # add block to BC
                state.start(state.rounds.round + 1, time) # start new round
                return 'new_state'
            return 'handled' # not enough votes yet...
        case 'new_round':
            return 'backlog'  # node is behind in votes... add to backlog
        case "pre_prepared":
            return 'backlog'  # node is behind in votes... add to backlog
        case 'round_change':
            return 'invalid'  # node has decided to skip this round
        case _:
            raise ValueError(
                f"Unexpected state '{state.state} for cp BigFoot...'")


def new_block(state, event):
    block = state.block
    time = event.time

    time += Parameters.execution["msg_val_delay"]
    time += Parameters.execution["block_val_delay"]

    if block.depth <= state.node.blockchain[-1].depth:
        return "invalid"  # old block: ignore
    elif block.depth > state.node.blockchain[-1].depth + 1:
        # future block: initiate sync
        if state.node.state.synced:
            state.node.state.synced = False
            Sync.create_local_sync_event(state.node, event.creator, time)
        # if not synced then we have to wait for other blocks in order to validate this so we cannot accept it
        return "handled"
    else:  # valid block
        # update_round if necessary
        state.rounds.round = event.payload['round']

        # add block and start new round
        state.node.add_block(block.copy(), time)

        state.start(event.payload['round']+1, time)

        return "handled"
