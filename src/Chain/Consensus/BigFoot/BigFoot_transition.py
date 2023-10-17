from Chain.Parameters import Parameters
import Chain.Consensus.HighLevelSync as Sync

import Chain.Consensus.BigFoot.BigFoot_messages as BigFoot_messages
import Chain.Consensus.Rounds as Rounds


def propose(state, event):
    time = event.time

    block, creation_time = state.create_BigFoot_block(time)

    if block is None:
        if creation_time + 1 + Parameters.execution['creation_time'] <= state.timeout.time:
            BigFoot_messages.schedule_propose(state, creation_time + 1)
        else:
            print(
                f"Block creationg failed at {time} for CP {state.NAME}")
    else:
        state.state = 'pre_prepared'
        state.block = block.copy()

        BigFoot_messages.broadcast_pre_prepare(state, time, block)

    return 'handled'


def pre_prepare(state, event):
    time = event.time
    block = event.payload['block']

    if not state.validate_message(event):
        return 'invalid'

    time += Parameters.execution["msg_val_delay"]

    # if node is a new round state (i.e waiting for a new block to be proposed)
    if state.state == 'new_round':
        # validate block
        if block.depth - 1 == state.node.last_block.depth and block.extra_data["round"] == state.rounds.round:
            time += Parameters.execution["block_val_delay"]

            # store block as current block
            state.block = event.payload['block'].copy()

            # change state to pre_prepared since block was accepted
            state.state = 'pre_prepared'

            # broadcast preare message
            BigFoot_messages.broadcast_prepare(state, time, state.block)

            # count own vote
            state.process_vote('prepare', state.node)

            return 'new_state'  # state changed (will check backlog)
        else:
            # if the block was invalid begin round change
            Rounds.change_round(state.node, time)

        return 'handled'  # event handled but state did not change

    return 'unhandled'


def prepare(state, event):
    time = event.time
    block = event.payload['block']

    if not state.validate_message(event):
        return "invalid"

    time += Parameters.execution["msg_val_delay"]

    if state.state == 'pre_prepared':
        # count prepare votes from other nodes
        state.process_vote('prepare', event.creator)

        # if we have enough prepare messages
        if not state.fast_path:
            # leader does not issue a prepare message (thus 2f required votes)
            if len(state.msgs['prepare']) >= Parameters.application["required_messages"] - 1:
                # change to prepared
                state.state = 'prepared'

                BigFoot_messages.broadcast_commit(state, time, block)

                # count own vote
                state.process_vote('commit', state.node)

                return 'new_state'
        else:
            # leader does not issue a prepare message (thus N-1)
            if len(state.msgs['prepare']) == Parameters.application["Nn"] - 1:
                state.node.add_block(state.block, time)

                if state.node.id == state.miner:
                    BigFoot_messages.broadcast_new_block(state, time, block)

                state.start(state.rounds.round + 1, time)

                return 'new_state'
            return "handled"
    elif state.state == 'new_round':
        # node has yet to receive enough pre_prepare messages
        return 'backlog'
    elif state.state == "round_change":
        state.process_vote('prepare', event.creator)

        # if we have enough prepare messages (-1 for leader -1 for slef)
        if len(state.msgs['prepare']) >= Parameters.application["required_messages"] - 2:
            time += Parameters.execution["block_val_delay"]

            if block.depth - 1 == state.node.last_block.depth:
                state.rounds.round = event.payload['round']

                # store block as current block
                state.block = event.payload['block'].copy()
                block = state.block

                # change state to pre_prepared since block was accepted
                state.state = 'pre_prepared'
                state.block = block

                # broadcast preare message
                BigFoot_messages.broadcast_prepare(state, time, block)

                # count own vote
                state.process_vote('prepare', state.node)

                return 'new_state'  # state changed (will check backlog)
            else:
                # if the node still thinks the block is still invalid and still thinks that
                # it is synced initiate syncing process
                if state.node.state.synced:
                    state.node.state.synced = False
                    Sync.create_local_sync_event(
                        state.node, event.creator, time)

            return "handled"

    return 'invalid'


def commit(state, event):
    time = event.time
    block = event.payload['block'].copy()

    if not state.validate_message(event):
        return "invalid"

    time += Parameters.execution["msg_val_delay"]

    # if prepared
    if state.state == 'prepared':
        state.process_vote('commit', event.creator)

        if len(state.msgs['commit']) >= Parameters.application["required_messages"]:
            state.node.add_block(state.block, time)

            if state.node.id == state.miner:
                BigFoot_messages.broadcast_commit(state, time, block)

            state.start(state.rounds.round + 1, time)

            return 'new_state'
        return 'handled'
    elif state.state == 'new_round' or state.state == "pre_prepared":
        return 'backlog'
    elif state.state == 'round_change':
        state.process_vote('commit', event.creator)

        # if we have enough commit messages (-1 for state)
        if len(state.msgs['commit']) >= Parameters.application["required_messages"] - 1:
            time += Parameters.execution["block_val_delay"]

            if block.depth - 1 == state.node.last_block.depth:
                # if the block is valid, update round
                state.rounds.round = event.payload['round']

                state.block = block.copy()

                # send commit message (since now node agrees that this block should be commited)
                BigFoot_messages.broadcast_commit(state, time, block)

                state.process_vote('commit', state.node)

                state.node.add_block(state.block, time)

                if state.node.id == state.miner:
                    BigFoot_messages.broadcast_new_block(state, time, block)

                state.start(state.rounds.round + 1, time)

                return 'new_state'
            else:
                # if the node still thinks the block is still invalid and still thinks that
                # it is synced initiate syncing process
                if state.node.state.synced:
                    state.node.state.synced = False
                    Sync.create_local_sync_event(
                        state.node, event.creator, time)

                return "handled"

    return "invalid"


def new_block(state, event):
    block = event.payload['block']
    time = event.time

    if not state.validate_message(event):
        return "invalid"

    time += Parameters.execution["msg_val_delay"]
    time += Parameters.execution["block_val_delay"]

    # old block (ignore)
    if block.depth <= state.node.blockchain[-1].depth:
        return "invalid"
    # future block (sync)
    elif block.depth > state.node.blockchain[-1].depth + 1:
        if state.node.state.synced:
            state.node.state.synced = False
            Sync.create_local_sync_event(state.node, event.creator, time)

            return "handled"
    else:
        # Valid block (we assume message + block are valid)
        # correct round - since message is valid and contains validator votes then if this is a future round
        # node did not participate in the CP (likely to have just recieved sync but missed a round-change)
        if event.payload['round'] > state.rounds.round:
            state.rounds.round

        # add block and start new round
        state.node.add_block(block, time)
        state.start(event.payload['round']+1, time)
        return "handled"
