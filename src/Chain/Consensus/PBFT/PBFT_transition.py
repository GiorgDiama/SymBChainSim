from Chain.Parameters import Parameters

import Chain.Consensus.HighLevelSync as Sync
import Chain.Consensus.PBFT.PBFT_messages as PBFT_messages
import Chain.Consensus.Rounds as Rounds


def propose(state, event):
    time = event.time

    block, creation_time = state.create_PBFT_block(time)

    if block is None:
        if creation_time + 1 + Parameters.execution['creation_time'] <= state.timeout.time:
            PBFT_messages.schedule_propose(creation_time + 1)
        else:
            print(f"Block creationg failed at {time} for CP {state.NAME}")
    else:
        state.state = 'pre_prepared'
        state.block = block.copy()

        PBFT_messages.broadcast_pre_prepare(state, creation_time, block)

    return 'handled'


def pre_prepare(state, event):
    time = event.time
    block = event.payload['block']

    if not state.validate_message(event):
        return 'invalid'

    time += Parameters.execution["msg_val_delay"]

    # if node is a new round state (i.e waiting for a new block to be proposed)
    match state.state:
        case 'new_round':
            # validate block
            if block.depth - 1 == state.node.last_block.depth and block.extra_data["round"] == state.rounds.round:
                time += Parameters.execution["block_val_delay"]

                # store block as current block
                state.block = event.payload['block'].copy()

                # change state to pre_prepared since block was accepted
                state.state = 'pre_prepared'

                # broadcast preare message
                PBFT_messages.broadcast_prepare(state, time, state.block)

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

    match state.state:
        case 'pre_prepared':
            # count prepare votes from other nodes
            state.process_vote('prepare', event.creator)

            # if we have enough prepare messages (2f messages since leader does not participate)
            if len(state.msgs['prepare']) == Parameters.application["required_messages"] - 1:
                # change to prepared
                state.state = 'prepared'

                PBFT_messages.broadcast_commit(state, time, block)

                # count own vote
                state.process_vote('commit', state.node)

                return 'new_state'

            return 'handled'
        case 'new_round':
            # node has yet to receive enough pre_prepare messages
            return 'backlog'
        case "round_change":
            state.process_vote('prepare', event.creator)

            # if we have enough prepare messages (2f - 2 messages since we trust our state so that makes it 2f (leader does not participate))
            if len(state.msgs['prepare']) >= Parameters.application["required_messages"] - 1:
                time += Parameters.execution["block_val_delay"]

                if block.depth - 1 == state.node.last_block.depth:
                    # if the block is valid, update round
                    state.rounds.round = event.payload['round']

                    # store block as current block
                    state.block = event.payload['block'].copy()

                    # change state to pre_prepared since block was accepted
                    state.state = 'pre_prepared'

                    PBFT_messages.broadcast_prepare(state, time, state.block)

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
                PBFT_messages.broadcast_new_block(state, time, block)

            state.start(state.rounds.round + 1, time)

            return 'new_state'
        return 'handled'
    elif state.state == 'new_round' or state.state == "pre_prepared":
        return 'backlog'
    elif state.state == 'round_change':
        state.process_vote('commit', event.creator)

        # if we have enough commit messages (2f messages since we trust our state so that makes it 2f+1)
        if len(state.msgs['commit']) >= Parameters.application["required_messages"]:
            time += Parameters.execution["block_val_delay"]

            if block.depth - 1 == state.node.last_block.depth:
                # if the block is valid, update round
                state.rounds.round = event.payload['round']

                state.block = block.copy()

                # send commit message (since now node agrees that this block should be commited)
                PBFT_messages.broadcast_commit(state, time, state.block)

                state.process_vote('commit', state.node)

                state.node.add_block(state.block, time)

                if state.node.id == state.miner:
                    PBFT_messages.broadcast_new_block(state, time, block)

                state.start(state.rounds.round + 1, time)

                return 'new_state'
            else:
                # if the node still think the block is invalid -> desynced node
                if state.node.state.synced:
                    state.node.state.synced = False
                    Sync.create_local_sync_event(
                        state.node, event.creator, time)

                return "handled"

    return "invalid"


def new_block(state, event):
    block = event.payload['block'].copy()
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
    # Valid block
    else:
        # correct round
        if event.payload['round'] > state.rounds.round:
            state.rounds.round = event.payload['round']
        # add block and start new round
        state.node.add_block(block, time)
        state.start(event.payload['round']+1, time)
        return "handled"
