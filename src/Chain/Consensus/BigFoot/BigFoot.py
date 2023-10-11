'''
    BigFoot Consensus Protocol
    Implementation based on: R. Saltini "BigFooT: A robust optimal-latency BFT blockchain consensus protocol with
    dynamic validator membership"

    BigFoot State:
        round - round change state defined by the rounds module
        fast_path - boolean value determining wether the node is in the fast path or not 
        state - BigFoot node state (new_round, pre-prepared, prepared, committed)]
        msgs: list of messages received from other nodes
        timeout - reference to latest timeout event (when node state updates it is used to find event and delte from event queue)
        fast_path_timeout - reference to fast_path_timeout event
        block -  the proposed block in current round
'''

from Chain.Block import Block
from Chain.Parameters import Parameters

import Chain.Consensus.Rounds as Rounds
import Chain.Consensus.HighLevelSync as Sync

from random import randint

########################## PROTOCOL CHARACTERISTICS ###########################


class BigFoot():
    NAME = "BigFoot"

    def __init__(self, node) -> None:
        self.rounds = Rounds.round_change_state()
        self.fast_path = None
        self.state = ""
        self.miner = ""
        self.msgs = {'prepare': [], 'commit': []}
        self.timeout = None
        self.fast_path_timeout = None
        self.block = None

        self.node = node

    def set_state(self):
        self.rounds = Rounds.round_change_state()
        self.fast_path = None
        self.state = ""
        self.miner = ""
        self.msgs = {'prepare': [], 'commit': []}
        self.timeout = None
        self.fast_path_timeout = None
        self.block = None

    def state_to_string(self):
        s = f"{Rounds.state_to_string(self.node)} | CP_state: {self.state} | block: {self.block.id if self.block is not None else -1} | msgs: {self.msgs} | TO: {round(self.timeout.time,3) if self.timeout is not None else -1} | FastTO: {round(self.fast_path_timeout.time,3) if self.fast_path_timeout is not None else -1}"
        return s

    def reset_msgs(self):
        self.msgs = {'prepare': [], 'commit': []}
        Rounds.reset_votes(self.node)

    def get_miner(self, round_robin=False):
        if round_robin:  # new miner in a round robin fashion
            self.miner = self.rounds % Parameters.application["Nn"]
        else:  # get new miner based on the hash of the last block
            self.miner = self.node.last_block.id % Parameters.application["Nn"]

    def init(self, time=0, starting_round=0):
        self.set_state()
        self.start(starting_round, time)

    def create_BigFoot_block(self, time):
        # calculate block creation delays
        time += Parameters.data["block_interval"] + \
            Parameters.execution["creation_time"]

        # create block according to CP
        block = Block(
            depth=len(self.node.blockchain),
            id=randint(1, 10000),
            previous=self.node.last_block.id,
            time_created=time,
            miner=self.node.id,
            consensus=BigFoot
        )
        block.extra_data = {'proposer': self.node.id,
                            "round": self.rounds.round}

        transactions, size, created_time = Parameters.simulation["txion_model"].execute_transactions(
            self.node.pool, time, time + self.timeout.time)

        if transactions:
            block.transactions = transactions
            block.size = size
            return block, created_time
        else:
            return -1, -1

    ########################## HANDLERER ###########################

    @staticmethod
    def handle_event(event):  # specific to BigFoot - called by events in Handler.handle_event()
        match event.payload["type"]:
            case 'pre_prepare':
                return event.actor.cp.pre_prepare(event)
            case 'prepare':
                return event.actor.cp.prepare(event)
            case 'commit':
                return event.actor.cp.commit(event)
            case 'timeout':
                return event.actor.cp.handle_timeout(event)
            case "fast_path_timeout":
                return event.actor.cp.handle_timeout(event)
            case 'new_block':
                return event.actor.cp.new_block(event)
            case _:
                return 'unhadled'

    ########################## PROTOCOL COMMUNICATION ###########################

    def process_vote(self, type, sender):
        # BigFoot does not allow for mutliple blocks to be submitted in 1 round
        self.msgs[type] += [sender.id]

    def pre_prepare(self, event):
        time = event.time
        block = event.payload['block']

        time += Parameters.execution["msg_val_delay"]

        # if node is a new round state (i.e waiting for a new block to be proposed)
        if self.state == 'new_round':
            # validate block
            if block.depth - 1 == self.node.last_block.depth and block.extra_data["round"] == self.rounds.round:
                time += Parameters.execution["block_val_delay"]

                # store block as current block
                self.block = event.payload['block'].copy()

                # change state to pre_prepared since block was accepted
                self.state = 'pre_prepared'

                # broadcast preare message
                payload = {
                    'type': 'prepare',
                    'block': self.block,
                    'round': self.rounds.round,
                }
                self.node.scheduler.schedule_broadcast_message(
                    self.node, time, payload, self.handle_event)

                # count own vote
                self.process_vote('prepare', self.node)

                return 'new_state'  # state changed (will check backlog)
            else:
                # if the block was invalid begin round check
                Rounds.change_round(self.node, time)

            return 'handled'  # event handled but state did not change

        return 'unhandled'

    def prepare(self, event):
        time = event.time
        block = event.payload['block']

        time += Parameters.execution["msg_val_delay"]

        if self.state == 'pre_prepared':
            # count prepare votes from other nodes
            self.process_vote('prepare', event.creator)

            # if we have enough prepare messages
            if not self.fast_path:
                # leader does not issue a prepare message
                if len(self.msgs['prepare']) >= Parameters.application["required_messages"] - 1:
                    # change to prepared
                    self.state = 'prepared'

                    # send commit message
                    payload = {
                        'type': 'commit',
                        'block': block,
                        'round': self.rounds.round,
                    }
                    self.node.scheduler.schedule_broadcast_message(
                        self.node, time, payload, self.handle_event)

                    # count own vote
                    self.process_vote('commit', self.node)
                    return 'new_state'
            else:
                # leader does not issue a prepare message
                if len(self.msgs['prepare']) == Parameters.application["Nn"] - 1:
                    if self.block is None:
                        self.block = block.copy()

                    self.node.add_block(self.block, time)

                    if self.node.id == self.miner:
                        payload = {
                            'type': 'new_block',
                            'block': block,
                            'round': self.rounds.round,
                        }

                        self.node.scheduler.schedule_broadcast_message(
                            self.node, time, payload, self.handle_event)

                    self.start(self.rounds.round + 1, time)

                    return 'new_state'
                return "handled"
        elif self.state == 'new_round':
            # node has yet to receive enough pre_prepare messages
            return 'backlog'
        elif self.state == "round_change":
            # The only thing that could make the node go into round change during this time
            # is either a timeout or an invalid block. Node will count the messages and if it receieves
            # enough it will, depending on the reason do the following:
            # 1) (node timed out) will accept block and keep working as normal
            # 2) (node though block was invalid) try to sync using block_data else request sync
            self.process_vote('prepare', event.creator)

            # if we have enough prepare messages (-1 for leader -1 for slef)
            if len(self.msgs['prepare']) >= Parameters.application["required_messages"] - 2:
                time += Parameters.execution["block_val_delay"]

                if block.depth - 1 == self.node.last_block.depth:
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
                    self.node.scheduler.schedule_broadcast_message(
                        self.node, time, payload, self.handle_event)

                    # count own vote
                    self.process_vote('prepare', self.node)

                    return 'new_state'  # state changed (will check backlog)
                else:
                    # if the node still thinks the block is still invalid and still thinks that
                    # it is synced initiate syncing process
                    if self.node.state.synced:
                        self.node.state.synced = False
                        Sync.create_local_sync_event(
                            self.node, event.creator, time)

                return "handled"

        return 'invalid'

    def commit(self, event):
        time = event.time
        block = event.payload['block'].copy()

        time += Parameters.execution["msg_val_delay"]

        # if prepared
        if self.state == 'prepared':
            self.process_vote('commit', event.creator)

            if len(self.msgs['commit']) >= Parameters.application["required_messages"]:
                payload = {
                    'type': 'commit',
                    'block': block,
                    'round': self.rounds.round,
                }
                self.node.scheduler.schedule_broadcast_message(
                    self.node, time, payload, self.handle_event)

                self.process_vote('commit', self.node)

                self.node.add_block(self.block, time)

                if self.node == self.miner:
                    payload = {
                        'type': 'new_block',
                        'block': block,
                        'round': self.rounds.round,
                    }

                    self.node.scheduler.schedule_broadcast_message(
                        self.node, time, payload, self.handle_event)

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

            # if we have enough commit messages (-1 for self)
            if len(self.msgs['commit']) >= Parameters.application["required_messages"] - 1:
                time += Parameters.execution["block_val_delay"]

                if block.depth - 1 == self.node.last_block.depth:
                    self.rounds.round = event.payload['round']

                    # try to correct round
                    if self.rounds.round < event.payload['round']:
                        self.rounds.round = event.payload['round']

                    if self.block is None:
                        self.block = block.copy()

                    # send commit message (since now node agrees that this block should be commited)
                    payload = {
                        'type': 'commit',
                        'block': block,
                        'round': self.rounds.round,
                    }
                    self.node.scheduler.schedule_broadcast_message(
                        self.node, time, payload, self.handle_event)

                    self.process_vote('commit', self.node)

                    block.extra_data["votes"] = self.msgs

                    # send new block message since we have received enough commit messages
                    self.node.add_block(block, time)

                    payload = {
                        'type': 'new_block',
                        'block': block,
                        'round': self.rounds.round,
                    }
                    self.node.scheduler.schedule_broadcast_message(
                        self.node, time, payload, self.handle_event)

                    self.start(self.rounds.round + 1, time)

                    return 'new_state'
                else:
                    # if the node still thinks the block is still invalid and still thinks that
                    # it is synced initiate syncing process
                    if self.node.state.synced:
                        self.node.state.synced = False
                        Sync.create_local_sync_event(
                            self.node, event.creator, time)

                    return "handled"

        return "invalid"

    def new_block(self, event):
        block = event.payload['block']
        time = event.time

        time += Parameters.execution["msg_val_delay"] + \
            Parameters.execution["block_val_delay"]

        # old block (ignore)
        if block.depth <= self.node.blockchain[-1].depth:
            return "invalid"

        # future block (sync)
        elif block.depth > self.node.blockchain[-1].depth + 1:
            if self.node.state.synced:
                self.node.state.synced = False
                Sync.create_local_sync_event(self.node, event.creator, time)

                return "handled"
        else:
            # Valid block (we assume message + block are valid)
            # correct round - since message is valid and contains validator votes then if this is a future round
            # node did not participate in the CP (likely to have just recieved sync but missed a round-change)
            if event.payload['round'] > self.rounds.round:
                self.rounds.round

            # add block and start new round
            self.node.add_block(block, time)
            self.start(event.payload['round']+1, time)
            return "handled"

    ########################## ROUND CHANGE ###########################

    def init_round_chage(self, time):
        self.schedule_timeout(time, remove=True, add_time=True)

    def start(self, new_round, time):
        if self.node.update(time):
            return 0

        self.state = 'new_round'
        self.fast_path = True

        self.node.backlog = []

        self.reset_msgs()

        self.rounds.round = new_round
        self.block = None

        self.get_miner()

        if self.miner == self.node.id:
            self.schedule_timeout(Parameters.data["block_interval"] + time)
            self.schedule_timeout(
                Parameters.data["block_interval"] + time, fast_path=True)

            block, creation_time = self.create_BigFoot_block(time)

            if creation_time == -1:
                print(f"Block creationg failed at {time} for CP {self.NAME}")
                return 0

            self.state = 'pre_prepared'
            self.block = block.copy()

            payload = {
                'type': 'pre_prepare',
                'block': block,
                'round': new_round,
            }

            self.node.scheduler.schedule_broadcast_message(
                self.node, creation_time, payload, self.handle_event)
        else:
            self.schedule_timeout(Parameters.data["block_interval"] + time)
            self.schedule_timeout(
                Parameters.data["block_interval"] + time, fast_path=True)

    ########################## TIMEOUTS ###########################

    def handle_timeout(self, event):
        if event.payload['round'] == self.rounds.round:
            if event.payload['type'] == "fast_path_timeout":
                time = event.time

                # set fast_path to false and remove TO event
                self.fast_path = False
                self.fast_path_timeout = None

                if not self.node.state.synced:
                    # if node is not synced it cannot send any commit messages
                    return "handled"

                # In case fast path times out - check if we have enough prepare votes now (if so go to prepared state)
                if self.block is not None and len(self.msgs['prepare']) >= Parameters.application["required_messages"] - 1:
                    # change to prepared
                    self.state = 'prepared'

                    # send commit message
                    payload = {
                        'type': 'commit',
                        'block': self.block,
                        'round': self.rounds.round,
                    }
                    self.node.scheduler.schedule_broadcast_message(
                        self.node, time, payload, self.handle_event)

                    # count own vote
                    self.process_vote('commit', self.node)
                    return 'new_state'
            else:
                if event.actor.update(event.time):
                    return 0

                if self.node.state.synced:
                    synced, in_sync_neighbour = self.node.synced_with_neighbours()
                    if not synced:
                        self.node.state.synced = False
                        Sync.create_local_sync_event(
                            self.node, in_sync_neighbour, event.time)

                Rounds.change_round(self.node, event.time)

            # handled because even though we change state to round_chage or new_state there is no need to handle backlog
            return "handled"

        return "invalid"

    def schedule_timeout(self, time, remove=True, add_time=True, fast_path=False):
        if fast_path:
            # set nodes fast_path attribute to True since fast path just started
            self.node.state.fast_path = True

            if add_time:
                time += float(Parameters.BigFoot["fast_path_timeout"])

            if self.fast_path_timeout is not None and Parameters.simulation["remove_timeouts"]:
                self.node.queue.remove_event(self.fast_path_timeout)

            payload = {
                'type': 'fast_path_timeout',
                'round': self.rounds.round,
            }
            event = self.node.scheduler.schedule_event(
                self.node, time, payload, self.handle_event)

            self.fast_path_timeout = event
        else:
            if add_time:
                time += float(Parameters.BigFoot['timeout'])

            if self.timeout is not None and Parameters.simulation["remove_timeouts"]:
                self.node.queue.remove_event(self.timeout)

            payload = {
                'type': 'timeout',
                'round': self.rounds.round,
            }

            event = self.node.scheduler.schedule_event(
                self.node, time, payload, self.handle_event)

            self.timeout = event

    ########################## RESYNC CP SPECIFIC ACTIONS ###########################

    def resync(self, payload, time):
        '''
            BigFoot specific resync actions
        '''
        self.set_state()
        if self.rounds.round < payload['blocks'][-1].extra_data['round']:
            self.rounds.round = payload['blocks'][-1].extra_data['round']

        self.schedule_timeout(time=time)

    ######################### OTHER #################################################

    def clean_up(self):
        pass
