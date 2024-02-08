from Chain.Block import Block
from Chain.Parameters import Parameters
from Chain.Handler import handle_backlog

import Chain.Consensus.Rounds as Rounds

from random import randint

import Chain.Consensus.PBFT.PBFT_transition as state_transitions
import Chain.Consensus.PBFT.PBFT_timeouts as timeouts
import Chain.Consensus.PBFT.PBFT_messages as messages


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

        self.msgs = {}

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
        msgs = {'prepare': self.count_votes('prepare', self.rounds.round)}
        s = f"{self.rounds.round} | CP_state: {self.state} | miner: {self.miner}| block: {self.block.id if self.block is not None else -1} | msgs: {self.msgs} | TO: {round(self.timeout.time,3) if self.timeout is not None else -1}"
        return s

    def reset_msgs(self, round):
        self.msgs = {'prepare': [], 'commit': []}
        Rounds.reset_votes(self.node)

    def count_votes(self, type, round):
        return len(self.msgs[type])

    def process_vote(self, type, sender, round, time):
        self.msgs[type] += [sender.id]

    def validate_message(self, event):
        round, current_round = event.payload['round'], self.rounds.round

        if round < current_round:
            return False, None
        elif round == current_round:
            return True, None
        else:
            return True, 'backlog'

    def validate_block(self, block):
        return block.depth - 1 == self.node.last_block.depth and block.extra_data["round"] == self.rounds.round

    def init(self, time=0, starting_round=0):
        self.set_state()
        self.start(starting_round, time)

    def get_miner(self):
        if Parameters.execution["proposer_selection"] == "round_robin":
            # new miner in a round robin fashion
            self.miner = self.rounds.round % Parameters.application["Nn"]
        elif Parameters.execution["proposer_selection"] == "hash":
            # get new miner based on the hash of the last block + the round (to avoid endlessly waiting for offline nodes)
            self.miner = (self.node.last_block.id +
                          self.rounds.round) % Parameters.application["Nn"]
        else:
            raise (ValueError(
                f"No such 'proposer_selection {Parameters.execution['proposer_selection']}"))

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
            'round': self.rounds.round,
        }

        transactions, size = Parameters.tx_factory.execute_transactions(
            self.node.pool, time)

        if transactions:
            block.transactions = transactions
            block.size = size
            return block, time + Parameters.execution['creation_time']
        else:
            return None, time

    def start(self, new_round=0, time=0):
        if self.node.update(time):
            return 0

        self.state = 'new_round'

        self.reset_msgs(new_round)

        self.rounds.round = new_round
        self.block = None

        self.get_miner()

        # taking into account block interval for the propossal round timeout
        time += Parameters.data["block_interval"]

        timeouts.schedule_timeout(self, time)

        # if the current node is the miner, schedule propose block event
        if self.miner == self.node.id:
            messages.schedule_propose(self, time)
        else:
            # check if any future events are here for this round
            # slow nodes might miss pre_prepare vote so its good to check early
            handle_backlog(self.node)

    def init_round_chage(self, time):
        timeouts.schedule_timeout(self, time, add_time=True)

    ########################## RESYNC CP SPECIFIC ACTIONS ###########################

    def resync(self, payload, time):
        '''
            PBFT specific resync actions
        '''
        self.set_state()
        round = payload['blocks'][-1].extra_data['round']

        self.start(round, time)

    ########################## HANDLERER ###########################

    @staticmethod
    def handle_event(event):  # specific to PBFT - called by events in Handler.handle_event()
        match event.payload["type"]:
            case 'propose':
                return state_transitions.propose(event.actor.cp, event)
            case 'pre_prepare':
                return state_transitions.pre_prepare(event.actor.cp, event)
            case 'prepare':
                return state_transitions.prepare(event.actor.cp, event)
            case 'commit':
                return state_transitions.commit(event.actor.cp, event)
            case 'timeout':
                return timeouts.handle_timeout(event.actor.cp, event)
            case 'new_block':
                return state_transitions.new_block(event.actor.cp, event)
            case _:
                return 'unhadled'
