from Chain.Block import Block
from Chain.Parameters import Parameters

import Chain.Consensus.Rounds as Rounds
import Chain.Consensus.HighLevelSync as Sync

import Chain.Consensus.BigFoot.BigFoot_transition as state_transition
import Chain.Consensus.BigFoot.BigFoot_timeouts as timeouts

from random import randint

########################## PROTOCOL CHARACTERISTICS ###########################


class BigFoot():
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
        # new miner in a round robin fashion
        if Parameters.execution["proposer_selection"] == "round_robin":
            self.miner = self.rounds.round % Parameters.application["Nn"]
        elif Parameters.execution["proposer_selection"] == "hash":
            # get new miner based on the hash of the last block
            self.miner = self.node.last_block.id % Parameters.application["Nn"]
        else:
            raise (ValueError(
                f"No such 'proposer_selection {Parameters.execution['proposer_selection']}"))

    def validate_message(self, event):
        payload = event.payload

        if payload['round'] < self.rounds.round:
            return False

        return True

    def process_vote(self, type, sender):
        self.msgs[type] += [sender.id]

    def init(self, time=0, starting_round=0):
        self.set_state()
        self.start(starting_round, time)

    def create_BigFoot_block(self, time):
        # create block according to CP
        block = Block(
            depth=len(self.node.blockchain),
            id=randint(1, 10000),
            previous=self.node.last_block.id,
            time_created=time,
            miner=self.node.id,
            consensus=BigFoot,
        )
        block.extra_data = {
            'proposer': self.node.id,
            'round': self.rounds.round
        }

        transactions, size = Parameters.tx_factory.execute_transactions(
            self.node.pool, time)

        if transactions:
            block.transactions = transactions
            block.size = size
            return block, time + Parameters.execution['creation_time']
        else:
            return None, time

    ########################## HANDLERER ###########################

    @staticmethod
    def handle_event(event):  # specific to BigFoot - called by events in Handler.handle_event()
        match event.payload["type"]:
            case 'propose':
                return state_transition.propose(event.actor.cp, event)
            case 'pre_prepare':
                return state_transition.pre_prepare(event.actor.cp, event)
            case 'prepare':
                return state_transition.prepare(event.actor.cp, event)
            case 'commit':
                return state_transition.commit(event.actor.cp, event)
            case 'timeout':
                return timeouts.handle_timeout(event.actor.cp, event)
            case "fast_path_timeout":
                return timeouts.handle_timeout(event.actor.cp, event)
            case 'new_block':
                return state_transition.new_block(event.actor.cp, event)
            case _:
                return 'unhadled'

    def init_round_chage(self, time):
        timeouts.schedule_timeout(self, time, add_time=True)

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

        # taking into account block interval for the propossal round timeout
        time += Parameters.data["block_interval"]

        timeouts.schedule_timeout(self, time)
        timeouts.schedule_timeout(self, time, fast_path=True)

        if self.miner == self.node.id:
            payload = {
                'type': 'propose',
            }

            self.node.scheduler.schedule_event(
                self.node, time, payload, BigFoot.handle_event)

    ########################## RESYNC CP SPECIFIC ACTIONS ###########################

    def resync(self, payload, time):
        '''
            BigFoot specific resync actions
        '''
        self.set_state()
        if self.rounds.round < payload['blocks'][-1].extra_data['round']:
            self.rounds.round = payload['blocks'][-1].extra_data['round']

        timeouts.schedule_timeout(self, time=time)
