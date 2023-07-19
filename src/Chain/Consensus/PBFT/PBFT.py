'''
    Practival Byzantime Fault Tollerance Consensus Protocol
    
    PBFT State:
        round - current round
        change_to - canditate round to change to
        state - PBFT node state (new_round, pre-prepared, prepared, committed, round_change)]
        msgs: list of messages received from other nodes
        timeout - reference to latest timeout event (when node state updates it is used to find event and delte from event queue)
        block -  the current proposed block
'''

from Chain.Block import Block
from Chain.Parameters import Parameters

import Chain.Consensus.Rounds as Rounds
import Chain.Consensus.HighLevelSync as Sync

from types import SimpleNamespace

from random import randint
from sys import modules

from copy import copy

########################## PROTOCOL CHARACTERISTICS ###########################

NAME = "PBFT"

def set_state(node):
    # add a reference to the CP module to to allow for CP method calls
    node.state.cp = modules[__name__]

    node.state.cp_state = SimpleNamespace(
        round=Rounds.round_change_state(),
        state="",
        miner="",
        msgs={'prepare': [], 'commit': []},
        timeout=None,
        block=None,
    )


def state_to_string(node):
    s = f"{Rounds.state_to_string(node)} | CP_state: {node.state.cp_state.state} | block: {node.state.cp_state.block.id if node.state.cp_state.block is not None else -1} | msgs: {node.state.cp_state.msgs} | TO: {round(node.state.cp_state.timeout.time,3) if node.state.cp_state.timeout is not None else -1}"
    return s


def reset_msgs(node):
    node.state.cp_state.msgs = {'prepare': [], 'commit': []}
    Rounds.reset_votes(node)


def get_miner(node, round_robin=True):
    if round_robin:  # new miner in a round robin fashion
        node.state.cp_state.miner = node.state.cp_state.round.round % Parameters.application[
            "Nn"]
    else:  # get new miner based on the hash of the last block
        node.state.cp_state.miner = node.last_block.id % Parameters.application["Nbp"]


def init(node, time=0, starting_round=0):
    set_state(node)
    start(node, starting_round, time)


def create_PBFT_block(node, time):
    # calculate block creation delays
    time += Parameters.data["block_interval"] + Parameters.execution["creation_time"]

    # create block according to CP
    block = Block(
        depth=len(node.blockchain),
        id=randint(1, 10000),
        previous=node.last_block.id,
        time_created=time,
        miner=node.id,
        consensus=modules[__name__]
    )
    block.extra_data = {
        'proposer': node.id,
        'round': node.state.cp_state.round.round
    }

    # add transactions to the block
    # get current transaction from transaction pool and timeout time
    current_pool = [t for t in node.pool if t.timestamp <= time]
    timeout_time = node.state.cp_state.timeout.time

    # while the pool is empty and the current time is less than the timeout wait for transactions to be added to the pool
    # ( basically the transactions are there - the nodes check when the first transaction in time apears and forwards the clock to that time
    # if not txions are found before the round times out, we return -1 and let the block proposal timeout

    while not current_pool and time + 1 < timeout_time:
        time += 1
        current_pool = [t for t in node.pool if t.timestamp <= time]

    if current_pool and time < timeout_time:
        block.transactions, block.size = Parameters.simulation["txion_model"].execute_transactions(
            current_pool)

        return block, time
    else:
        return -1, -1

########################## HANDLERER ###########################


def handle_event(event):  # specific to PBFT - called by events in Handler.handle_event()
    if event.payload['type'] == 'pre_prepare':
        return pre_prepare(event)
    elif event.payload['type'] == 'prepare':
        return prepare(event)
    elif event.payload['type'] == 'commit':
        return commit(event)
    elif event.payload['type'] == 'timeout':
        return timeout(event)
    elif event.payload['type'] == 'new_block':
        return new_block(event)
    else:
        return 'unhadled'

########################## PROTOCOL COMMUNICATION ###########################


def validate_message(event, node):
    node_state, cp_state = node.state, node.state.cp_state
    payload = event.payload

    if payload['round'] < cp_state.round.round:
        return False

    return True


def process_vote(node, type, sender):
    # PBFT does not allow for mutliple blocks to be submitted in 1 round
    node.state.cp_state.msgs[type] += [sender.id]


def pre_prepare(event):
    node = event.receiver
    time = event.time
    state = node.state.cp_state
    block = event.payload['block']
    
    time += Parameters.execution["msg_val_delay"]

    # if node is a new round state (i.e waiting for a new block to be proposed)
    if state.state == 'new_round':
        # validate block
        if block.depth - 1 == node.last_block.depth and block.extra_data["round"] == state.round.round:
            time += Parameters.execution["block_val_delay"]

            # store block as current block
            state.block = event.payload['block'].copy()
            block = state.block

            # change state to pre_prepared since block was accepted
            state.state = 'pre_prepared'
            state.block = block

            # broadcast preare message
            payload = {
                'type': 'prepare',
                'block': block,
                'round': state.round.round,
            }
            node.scheduler.schedule_broadcast_message(
                node, time, payload, handle_event)

            # count own vote
            process_vote(node, 'prepare', node)

            return 'new_state'  # state changed (will check backlog)
        else:
            # if the block was invalid begin round check
            Rounds.change_round(node, time)

        return 'handled'  # event handled but state did not change

    return 'unhandled'

def prepare(event):
    node = event.receiver
    time = event.time
    state = node.state.cp_state
    block = event.payload['block']

    if not validate_message(event, node):
        return "invalid"
    
    time += Parameters.execution["msg_val_delay"]

    if state.state == 'pre_prepared':
        # count prepare votes from other nodes
        process_vote(node, 'prepare', event.creator)

        # if we have enough prepare messages (2f messages since leader does not participate || has allread 'voted')
        if len(state.msgs['prepare']) == Parameters.application["required_messages"] - 1:
            # change to prepared
            state.state = 'prepared'

            # send commit message
            payload = {
                'type': 'commit',
                'block': block,
                'round': state.round.round,
            }
            node.scheduler.schedule_broadcast_message(
                node, time, payload, handle_event)

            # count own vote
            process_vote(node, 'commit', node)
            return 'new_state'

        return 'handled'
    elif state.state == 'new_round':
        # node has yet to receive enough pre_prepare messages
        return 'backlog'
    elif state.state == "round_change":
        # The only thing that could make the node go into round change during this time
        # is either a timeout or an invalid block. Node will count the messages and if it receieves
        # enough it will depending on the reason do the following:
        # 1) (node timed out) will accept block and keep working as normal
        # 2) (node though block was invalid) try to sync using block_data else initialise sync
        process_vote(node, 'prepare', event.creator)

        # if we have enough prepare messages (2f - 2 messages since we trust our self so that makes it 2f (leader does not participate))
        # in the case where the node has entered rounch switch we do not count our own vote then 2f - 2 for prepare
        if len(state.msgs['prepare']) >= Parameters.application["required_messages"] - 2:
            time += Parameters.execution["block_val_delay"]

            if block.depth - 1 == node.last_block.depth:
                state.round.round = event.payload['round']

                # store block as current block
                state.block = event.payload['block'].copy()
                block = state.block

                # change state to pre_prepared since block was accepted
                state.state = 'pre_prepared'
                state.block = block

                # broadcast preare message
                payload = {
                    'type': 'prepare',
                    'block': block,
                    'round': state.round.round,
                }
                node.scheduler.schedule_broadcast_message(
                    node, time, payload, handle_event)

                # count own vote
                process_vote(node, 'prepare', node)

                return 'new_state'  # state changed (will check backlog)
            else:
                # if the node still thinks the block is still invalid and still thinks that
                # it is synced initiate syncing process
                if node.state.synced:
                    node.state.synced = False
                    Sync.create_local_sync_event(node, event.creator, time)

                return "handled"

    return 'invalid'


def commit(event):
    node = event.receiver
    time = event.time
    state = node.state.cp_state
    block = event.payload['block'].copy()

    if not validate_message(event, node):
        return "invalid"
    time += Parameters.execution["msg_val_delay"]

    # if prepared
    if state.state == 'prepared':
        process_vote(node, 'commit', event.creator)

        if len(state.msgs['commit']) >= Parameters.application["required_messages"]:
            payload = {
                'type': 'commit',
                'block': block,
                'round': state.round.round,
            }
            node.scheduler.schedule_broadcast_message(
                node, time, payload, handle_event)

            process_vote(node, 'commit', node)

            node.add_block(state.block, time)
            
            payload = {
                'type': 'new_block',
                'block': block,
                'round': state.round.round,
            }

            node.scheduler.schedule_broadcast_message(
                node, time, payload, handle_event)

            start(node, state.round.round + 1, time)

            return 'new_state'
        return 'handled'
    elif state.state == 'new_round' or state.state == "pre_prepared":
        return 'backlog'
    elif state.state == 'round_change':
        # The only thing that could make the node go into round change during this time
        # is either a timeout or an invalid block !additionally for commit, the node must have missed the prepare messages!
        # ** otherwise they would have priority and correct the node **
        # Node will count the messages and if it receieves enough it will depending on the reason do the following:
        # 1) (node timed out) will accept block and keep working as normal
        # 2) (node though block was invalid) try to sync using block_data else initialise sync
        process_vote(node, 'commit', event.creator)

        # if we have enough commit messages (2f messages since we trust our self so that makes it 2f+1)
        if len(state.msgs['commit']) >= Parameters.application["required_messages"] - 1:
            time += Parameters.execution["block_val_delay"]

            if block.depth - 1 == node.last_block.depth:
                state.round.round = event.payload['round']

                # send commit message (since now node agrees that this block should be commited)
                payload = {
                    'type': 'commit',
                    'block': block,
                    'round': state.round.round,
                }
                node.scheduler.schedule_broadcast_message(
                    node, time, payload, handle_event)

                process_vote(node, 'commit', node)

                # send new block message since we have received enough commit messages
                node.add_block(block, time)

                payload = {
                    'type': 'new_block',
                    'block': block,
                    'round': state.round.round,
                }
                node.scheduler.schedule_broadcast_message(
                    node, time, payload, handle_event)

                start(node, state.round.round + 1, time)

                return 'new_state'
            else:
                # if the node still thinks the block is still invalid and still thinks that
                # it is synced initiate syncing process
                if node.state.synced:
                    node.state.synced = False
                    Sync.create_local_sync_event(node, event.creator, time)

                return "handled"

    return "invalid"

def new_block(event):
    node = event.receiver
    block = event.payload['block']
    time = event.time

    if not validate_message(event, node):
        return "invalid"
    time += Parameters.execution["msg_val_delay"]

    time += Parameters.execution["block_val_delay"]

    # old block (ignore)
    if block.depth <= node.blockchain[-1].depth:
        return "invalid"

    # future block (sync)
    elif block.depth > node.blockchain[-1].depth + 1:
        if node.state.synced:
            node.state.synced = False
            Sync.create_local_sync_event(node, event.creator, time)

            return "handled"
    else:  # Valid block
        # correct round
        if event.payload['round'] > node.state.cp_state.round.round:
            # BUG: minor bug: fix and test
            node.state.cp_state.round.round
        # add block and start new round
        node.add_block(block, time)
        start(node, event.payload['round']+1, time)
        return "handled"

########################## ROUND CHANGE ###########################

def init_round_chage(node, time):
    schedule_timeout(node, time, remove=True, add_time=True)


def start(node, new_round, time):
    if node.update(time):
        return 0

    state = node.state.cp_state

    state.state = 'new_round'
    node.backlog = []

    reset_msgs(node)

    state.round.round = new_round
    state.block = None

    get_miner(node)

    if state.miner == node.id:
        # taking into account block interval for the propossal round timeout
        schedule_timeout(node, Parameters.data["block_interval"] + time)

        block, creation_time = create_PBFT_block(node, time)

        if creation_time == -1:
            print(f"Block creationg failed at {time} for CP {NAME}")
            return 0

        state.state = 'pre_prepared'
        state.block = block.copy()
        
        payload = {
            'type': 'pre_prepare',
            'block': block,
            'round': new_round,
        }   

        node.scheduler.schedule_broadcast_message(
            node, creation_time, payload, handle_event)
    else:
        # taking into account block interval for the propossal round timeout
        schedule_timeout(node, Parameters.data["block_interval"] + time)

########################## TIMEOUTS ###########################


def timeout(event):
    node = event.creator

    if event.payload['round'] == node.state.cp_state.round.round:
        if event.actor.update(event.time):
            return 0

        if node.state.synced:
            synced, in_sync_neighbour = node.synced_with_neighbours()
            if not synced:
                node.state.synced = False
                Sync.create_local_sync_event(
                    node, in_sync_neighbour, event.time)

        Rounds.change_round(node, event.time)
        return "handled"  # changes state to round_chage but no need to handle backlog

    return "invalid"


def schedule_timeout(node, time, remove=True, add_time=True):
    if node.state.cp_state.timeout is not None and remove:
        try:
            node.remove_event(node.state.cp_state.timeout)
        except ValueError:
            pass

    if add_time:
        time += Parameters.PBFT['timeout']

    payload = {
        'type': 'timeout',
        'round': node.state.cp_state.round.round,
    }

    event = node.scheduler.schedule_event(node, time, payload, handle_event)
    node.state.cp_state.timeout = event

########################## RESYNC CP SPECIFIC ACTIONS ###########################


def resync(node, payload, time):
    '''
        PBFT specific resync actions
    '''
    set_state(node)
    if node.state.cp_state.round.round < payload['blocks'][-1].extra_data['round']:
        node.state.cp_state.round.round = payload['blocks'][-1].extra_data['round']

    schedule_timeout(node, time=time)

######################### OTHER #################################################

def clean_up(node):
    for event in node.queue.event_list:
        if event.payload["CP"] == NAME:
            node.queue.remove_event(event)
