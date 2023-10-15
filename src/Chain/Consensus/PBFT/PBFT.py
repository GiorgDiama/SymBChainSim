from Chain.Block import Block
from Chain.Parameters import Parameters

import Chain.Consensus.Rounds as Rounds
import Chain.Consensus.HighLevelSync as Sync

from random import randint


class PBFT():
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

    NAME = "PBFT"

    def __init__(self, node) -> None:
        self.rounds = Rounds.round_change_state()
        self.state = ""
        self.miner = ""
        self.msgs = {'prepare': [], 'commit': []}
        self.timeout = None
        self.block = None

        self.node = node

    def set_state(self):
        self.rounds = Rounds.round_change_state()
        self.state = ""
        self.miner = ""
        self.msgs = {'prepare': [], 'commit': []}
        self.timeout = None
        self.block = None

    def state_to_string(self):
        s = f"{self.rounds.round} | CP_state: {self.state} | block: {self.block.id if self.block is not None else -1} | msgs: {self.msgs} | TO: {round(self.timeout.time,3) if self.timeout is not None else -1}"
        return s

    def reset_msgs(self):
        self.msgs = {'prepare': [], 'commit': []}
        Rounds.reset_votes(self.node)

    def get_miner(self, round_robin=False):
        # new miner in a round robin fashion
        if Parameters.execution["proposer_selection"] == "round_robin":
            self.miner = self.rounds.round % Parameters.application["Nn"]
        elif Parameters.execution["proposer_selection"] == "hash":
            # get new miner based on the hash of the last block
            self.miner = self.node.last_block.id % Parameters.application["Nn"]
        else:
            raise (ValueError(
                f"No such 'proposer_selection {Parameters.execution['proposer_selection']}"))

    def init(self, time=0, starting_round=0):
        self.set_state()
        self.start(starting_round, time)

    def create_PBFT_block(self, time):
        # create block according to CP
        block = Block(
            depth=len(self.node.blockchain),
            id=randint(1, 10000),
            previous=self.node.last_block.id,
            time_created=time,
            miner=self.node.id,
            consensus=PBFT,
        )
        block.extra_data = {
            'proposer': self.node.id,
            'round': self.rounds.round
        }

        transactions, size = Parameters.simulation["txion_model"].execute_transactions(
            self.node.pool, time)

        if transactions:
            block.transactions = transactions
            block.size = size
            return block, time + Parameters.execution['creation_time']
        else:
            return None, time

    @staticmethod
    def handle_event(event):
        # specific to PBFT - called by events in Handler.handle_event()
        match event.payload["type"]:
            case 'propose':
                return event.actor.cp.propose(event)
            case 'pre_prepare':
                return event.actor.cp.pre_prepare(event)
            case 'prepare':
                return event.actor.cp.prepare(event)
            case 'commit':
                return event.actor.cp.commit(event)
            case 'timeout':
                return event.actor.cp.handle_timeout(event)
            case 'new_block':
                return event.actor.cp.new_block(event)
            case _:
                return 'unhadled'

    ########################## PROTOCOL COMMUNICATION ###########################

    def validate_message(self, event):
        payload = event.payload

        if payload['round'] < self.rounds.round:
            return False

        return True

    def process_vote(self, type, sender):
        self.msgs[type] += [sender.id]

    def propose(self, event):
        time = event.time

        block, creation_time = self.create_PBFT_block(time)

        if block is None:
            if creation_time + 1 + Parameters.execution['creation_time'] <= self.timeout.time:
                payload = {'type': 'propose'}
                self.node.scheduler.schedule_event(
                    self.node, creation_time+1, payload, PBFT.handle_event)
            else:
                print(f"Block creationg failed at {time} for CP {PBFT.NAME}")
        else:
            self.state = 'pre_prepared'
            self.block = block.copy()

            payload = {
                'type': 'pre_prepare',
                'block': block,
                'round': self.rounds.round,
            }

            self.node.scheduler.schedule_broadcast_message(
                self.node, creation_time, payload, PBFT.handle_event)

        return 'handled'

    def pre_prepare(self, event):
        node = self.node
        time = event.time
        block = event.payload['block']

        time += Parameters.execution["msg_val_delay"]

        # if node is a new round state (i.e waiting for a new block to be proposed)
        if self.state == 'new_round':
            # validate block
            if block.depth - 1 == node.last_block.depth and block.extra_data["round"] == self.rounds.round:
                time += Parameters.execution["block_val_delay"]

                # store block as current block
                self.block = event.payload['block'].copy()
                block = self.block

                # change state to pre_prepared since block was accepted
                self.state = 'pre_prepared'
                self.block = block

                # broadcast preare message
                payload = {
                    'type': 'prepare',
                    'block': block,
                    'round': self.rounds.round,
                }
                node.scheduler.schedule_broadcast_message(
                    node, time, payload, PBFT.handle_event)

                # count own vote
                self.process_vote('prepare', node)

                return 'new_state'  # state changed (will check backlog)
            else:
                # if the block was invalid begin round check
                Rounds.change_round(node, time)

            return 'handled'  # event handled but state did not change

        return 'unhandled'

    def prepare(self, event):
        node = self.node
        time = event.time
        block = event.payload['block']

        if not self.validate_message(event):
            return "invalid"

        time += Parameters.execution["msg_val_delay"]

        if self.state == 'pre_prepared':
            # count prepare votes from other nodes
            self.process_vote('prepare', event.creator)

            # if we have enough prepare messages (2f messages since leader does not participate || has allread 'voted')
            if len(self.msgs['prepare']) == Parameters.application["required_messages"] - 1:
                # change to prepared
                self.state = 'prepared'

                # send commit message
                payload = {
                    'type': 'commit',
                    'block': block,
                    'round': self.rounds.round,
                }
                node.scheduler.schedule_broadcast_message(
                    node, time, payload, PBFT.handle_event)

                # count own vote
                self.process_vote('commit', node)
                return 'new_state'

            return 'handled'
        elif self.state == 'new_round':
            # node has yet to receive enough pre_prepare messages
            return 'backlog'
        elif self.state == "round_change":
            # The only thing that could make the node go into round change during this time
            # is either a timeout or an invalid block. Node will count the messages and if it receieves
            # enough it will depending on the reason do the following:
            # 1) (node timed out) will accept block and keep working as normal
            # 2) (node though block was invalid) try to sync using block_data else initialise sync
            self.process_vote('prepare', event.creator)

            # if we have enough prepare messages (2f - 2 messages since we trust our self so that makes it 2f (leader does not participate))
            # in the case where the node has entered rounch switch we do not count our own vote then 2f - 2 for prepare
            if len(self.msgs['prepare']) >= Parameters.application["required_messages"] - 1:
                time += Parameters.execution["block_val_delay"]

                if block.depth - 1 == node.last_block.depth:
                    self.rounds.round = event.payload['round']

                    # store block as current block
                    self.block = event.payload['block'].copy()
                    block = self.block

                    # change state to pre_prepared since block was accepted
                    self.state = 'pre_prepared'
                    self.block = block

                    # broadcast preare message
                    payload = {
                        'type': 'prepare',
                        'block': block,
                        'round': self.rounds.round,
                    }
                    node.scheduler.schedule_broadcast_message(
                        node, time, payload, PBFT.handle_event)

                    # count own vote
                    self.process_vote('prepare', node)

                    return 'new_state'  # state changed (will check backlog)
                else:
                    # if the node still thinks the block is still invalid and still thinks that
                    # it is synced initiate syncing process
                    if node.state.synced:
                        node.state.synced = False
                        Sync.create_local_sync_event(node, event.creator, time)

                    return "handled"

        return 'invalid'

    def commit(self, event):
        node = self.node
        time = event.time
        block = event.payload['block'].copy()

        if not self.validate_message(event):
            return "invalid"
        time += Parameters.execution["msg_val_delay"]

        # if prepared
        if self.state == 'prepared':
            self.process_vote('commit', event.creator)

            if len(self.msgs['commit']) >= Parameters.application["required_messages"]:
                node.add_block(self.block, time)

                payload = {
                    'type': 'new_block',
                    'block': block,
                    'round': self.rounds.round,
                }

                node.scheduler.schedule_broadcast_message(
                    node, time, payload, PBFT.handle_event)

                self.start(self.rounds.round + 1, time)

                return 'new_state'
            return 'handled'
        elif self.state == 'new_round' or self.state == "pre_prepared":
            return 'backlog'
        elif self.state == 'round_change':
            # The only thing that could make the node go into round change during this time
            # is either a timeout or an invalid block !additionally for commit, the node must have missed the prepare messages!
            # ** otherwise they would have priority and correct the node **
            # Node will count the messages and if it receieves enough it will depending on the reason do the following:
            # 1) (node timed out) will accept block and keep working as normal
            # 2) (node though block was invalid) try to sync using block_data else initialise sync
            self.process_vote('commit', event.creator)

            # if we have enough commit messages (2f messages since we trust our self so that makes it 2f+1)
            if len(self.msgs['commit']) >= Parameters.application["required_messages"]:
                time += Parameters.execution["block_val_delay"]

                if block.depth - 1 == node.last_block.depth:
                    self.rounds.round = event.payload['round']

                    # send commit message (since now node agrees that this block should be commited)
                    payload = {
                        'type': 'commit',
                        'block': block,
                        'round': self.rounds.round,
                    }
                    node.scheduler.schedule_broadcast_message(
                        node, time, payload, PBFT.handle_event)

                    self.process_vote('commit', node)

                    # send new block message since we have received enough commit messages
                    node.add_block(block, time)

                    payload = {
                        'type': 'new_block',
                        'block': block,
                        'round': self.rounds.round,
                    }
                    node.scheduler.schedule_broadcast_message(
                        node, time, payload, PBFT.handle_event)

                    self.start(self.rounds.round + 1, time)

                    return 'new_state'
                else:
                    # if the node still thinks the block is still invalid and still thinks that
                    # it is synced initiate syncing process
                    if node.state.synced:
                        node.state.synced = False
                        Sync.create_local_sync_event(node, event.creator, time)

                    return "handled"

        return "invalid"

    def new_block(self, event):
        node = event.receiver
        block = event.payload['block']
        time = event.time

        if not self.validate_message(event):
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
            if event.payload['round'] > self.rounds.round:
                self.rounds.round = event.payload['round']
            # add block and start new round
            node.add_block(block, time)
            self.start(event.payload['round']+1, time)
            return "handled"

    ########################## ROUND CHANGE ###########################

    def init_round_chage(self, time):
        self.schedule_timeout(time, remove=True, add_time=True)

    def start(self, new_round=0, time=0):
        if self.node.update(time):
            return 0

        self.state = 'new_round'
        self.node.backlog = []

        self.reset_msgs()

        self.rounds.round = new_round
        self.block = None

        self.get_miner()

        # taking into account block interval for the propossal round timeout
        self.schedule_timeout(Parameters.data["block_interval"] + time)

        # if the current node is the miner, schedule propose block event
        if self.miner == self.node.id:
            payload = {
                'type': 'propose',
            }
            self.node.scheduler.schedule_event(
                self.node, time + Parameters.data["block_interval"], payload, PBFT.handle_event)

    ########################## TIMEOUTS ###########################

    def handle_timeout(self, event):
        node = self.node

        if event.payload['round'] == self.rounds.round:
            if self.node.update(event.time):
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

    def schedule_timeout(self, time, remove=True, add_time=True):
        if add_time:
            time += Parameters.PBFT['timeout']

        payload = {
            'type': 'timeout',
            'round': self.rounds.round,
        }

        if self.timeout is not None and Parameters.simulation["remove_timeouts"]:
            self.node.queue.remove_event(self.timeout)

        event = self.node.scheduler.schedule_event(
            self.node, time, payload, PBFT.handle_event)
        self.timeout = event

    ########################## RESYNC CP SPECIFIC ACTIONS ###########################

    def resync(self, payload, time):
        '''
            PBFT specific resync actions
        '''
        self.set_state()
        if self.rounds.round < payload['blocks'][-1].extra_data['round']:
            self.rounds.round = payload['blocks'][-1].extra_data['round']

        self.schedule_timeout(time=time)

    ######################### OTHER #################################################

    def clean_up(self):
        pass
