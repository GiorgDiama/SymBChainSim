from ...Parameters import Parameters
from ...Network import Network

from ...Consensus import HighLevelSync
from ...Consensus import Rounds

from  ..PBFT import PBFT_messages


def propose(state, event):
    time = event.time

    # attempt to create block
    block, creation_time = state.create_PBFT_block(time)

    if block is None:
        # we can be smart and look ahead to directly move to the time transactions will be here 
        # there is a chance that transactions are there but not generated yet so we cannot abort early
        when_next = 0.1
        if Parameters.application["transaction_model"] == "global":
            if len(Parameters.tx_factory.global_mempool) >= 1:
                when_next = Parameters.tx_factory.global_mempool[0].timestamp
        else:
            if len(state.node.pool) >= 1:
                when_next = state.node.pool[0].timestamp

        # if there is still time in the round, attempt to reschedule later when txions might be generated
        if creation_time + when_next + Parameters.execution['creation_time'] <= state.timeout.time:
            PBFT_messages.schedule_propose(state, creation_time + when_next)
    else:
        # block created, change state, and broadcast it.
        state.state = 'pre_prepared'
        state.block = block.copy()

        # create the extra_data field and log votes
        state.block.extra_data['votes'] = {
            'pre_prepare': [], 'prepare': [], 'commit': []}
        
        state.block.extra_data['votes']['pre_prepare'].append((
            event.creator.id, time, Network.size(event)))
        
        PBFT_messages.broadcast_pre_prepare(state, time, block)

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

    match state.state:
        # if node is a new round state (i.e waiting for a new block to be proposed)
        case 'new_round':
            # validate block
            time += Parameters.execution["block_val_delay"]
            if not state.validate_block(block):
                # if the block is invalid begin round change
                Rounds.change_round(state.node, time)
                return 'handled'  # event handled but state did not change

            # store block as current block
            state.block = event.payload['block'].copy()

            # create the votes extra_data field and log votes
            state.block.extra_data['votes'] = {
                'pre_prepare': [],
                'prepare': [],
                'commit': []
            }
            
            state.block.extra_data['votes']['pre_prepare'].append((
                event.creator.id, time, Network.size(event)))

            # change state to pre_prepared since block was accepted
            state.state = 'pre_prepared'

            # broadcast prepare message
            PBFT_messages.broadcast_prepare(state, time, state.block)

            # count own vote
            state.process_vote('prepare', state.node,
                                state.rounds.round, time)

            state.block.extra_data['votes']['prepare'].append((
                event.actor.id, time, Network.size(event)))
            
            return 'new_state'  # state changed (will check backlog)

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

            state.block.extra_data['votes']['prepare'].append((
                event.creator.id, time, Network.size(event)))

            # if we have enough prepare messages (2f messages since leader does not participate)
            if state.count_votes('prepare', round) >= Parameters.application["required_messages"] - 1:
                # change to prepared
                state.state = 'prepared'

                # broadcast commit message
                PBFT_messages.broadcast_commit(state, time, block)

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
            state.process_vote('commit', event.creator,state.rounds.round, time)
            state.block.extra_data['votes']['commit'].append(
                (event.creator.id, time, Network.size(event)))
            
            # if we have enough votes
            if state.count_votes('commit', round) >= Parameters.application["required_messages"]:
                # add block to local blockchain
                state.node.add_block(state.block, time)

                # if this node is the miner: broadcast the block to the nodes
                if state.node.id == state.miner:
                    PBFT_messages.broadcast_new_block(state, time, block)

                # start new round
                state.start(state.rounds.round + 1, time)

                return 'new_state'
            
            # not enough votes yet...
            return 'handled'
        case 'new_round':
            return 'backlog'  # node is behind in votes... add to backlog
        case "pre_prepared":
            return 'backlog'  # node is behind in votes... add to backlog
        case 'round_change':
            return 'invalid'  # node has decided to skip this round
        case _:
            raise ValueError(
                f"Unexpected state '{state.state} for cp PBFT...'")


def new_block(state, event):
    block = event.payload['block']
    time = event.time

    time += Parameters.execution["msg_val_delay"]
    time += Parameters.execution["block_val_delay"]

    # check: already added
    if block.depth <= state.node.blockchain[-1].depth:
        return "invalid"  # old block: ignore
    
    # check: future block
    if block.depth > state.node.blockchain[-1].depth + 1:
        # TODO: add logic to cache this block so we dont have to request it
        if state.node.state.synced: # check: do we know we are desynced?
            state.node.state.synced = False
            HighLevelSync.create_local_sync_event(state.node, event.creator, time)
        return "handled"
    
    # add block local blockchain and start new round (round in block + 1)
    state.node.add_block(block.copy(), time)
    state.start(block.extra_data['round']+1, time)

    return "handled"
