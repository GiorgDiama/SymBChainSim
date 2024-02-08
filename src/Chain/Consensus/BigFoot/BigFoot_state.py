from Chain.Block import Block
from Chain.Parameters import Parameters
from Chain.Handler import handle_backlog

import Chain.Consensus.Rounds as Rounds

import Chain.Consensus.BigFoot.BigFoot_transition as state_transition
import Chain.Consensus.BigFoot.BigFoot_timeouts as timeouts
import Chain.Consensus.BigFoot.BigFoot_messages as messages

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
        self.msgs = {}

        self.timeout = None
        self.fast_path_timeout = None

        self.block = None

        self.node = node

    def state_to_string(self):
        msgs = {'prepare': self.count_votes('prepare', self.rounds.round)}
        s = f"{self.rounds.round} | CP_state: {self.state} | miner: {self.miner}| block: {self.block.id if self.block is not None else -1} | msgs: {self.msgs} | TO: {round(self.timeout.time,3) if self.timeout is not None else -1}"
        return s

    def set_state(self):
        self.rounds = Rounds.round_change_state()
        self.fast_path = None
        self.state = ""
        self.miner = ""
        self.msgs = {}
        self.timeout = None
        self.fast_path_timeout = None
        self.block = None

    def reset_msgs(self, round):
        self.msgs[round] = {'prepare': [], 'commit': []}
        Rounds.reset_votes(self.node)

    def count_votes(self, type, round):
        return len(self.msgs[round][type])

    def process_vote(self, type, sender, round, time):
        self.msgs[round][type] += [(sender.id, time)]

    def get_miner(self):
        match Parameters.execution["proposer_selection"]:
            case "round_robin":
                # new miner in a round robin fashion
                self.miner = self.rounds.round % Parameters.application["Nn"]
            case "hash":
                # get new miner based on the hash of the last block + the round (to avoid endlessly waiting for offline nodes)
                self.miner = (self.node.last_block.id +
                              self.rounds.round) % Parameters.application["Nn"]
            case _:
                raise (ValueError(
                    f"No such 'proposer_selection {Parameters.execution['proposer_selection']}"))

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
            'round': self.rounds.round,
            'votes': {}
        }

        transactions, size = Parameters.tx_factory.execute_transactions(
            self.node.pool, time)

        if transactions:
            block.transactions = transactions
            block.size = size
            return block, time + Parameters.execution['creation_time']
        else:
            return None, time

    def init_round_chage(self, time):
        timeouts.schedule_timeout(self, time, add_time=True)

    def start(self, new_round, time):
        if self.node.update(time):
            return 0

        self.state = 'new_round'
        self.fast_path = True

        self.reset_msgs(new_round)

        self.rounds.round = new_round
        self.block = None

        self.get_miner()

        # taking into account block interval for the propossal round timeout
        time += Parameters.data["block_interval"]

        timeouts.schedule_timeout(self, time)
        timeouts.schedule_timeout(self, time, fast_path=True)

        if self.miner == self.node.id:
            messages.schedule_propose(self, time)
        else:
            # check if any future events are here for this round
            # slow nodes might miss pre_prepare vote so its good to check early
            handle_backlog(self.node)

    ########################## RESYNC CP SPECIFIC ACTIONS ###########################

    def resync(self, payload, time):
        '''
            BigFoot specific resync actions
        '''
        self.set_state()
        round = payload['blocks'][-1].extra_data['round']

        self.start(round, time)

    ########################## HANDLERER ###########################

    @staticmethod
    def handle_event(event):  # specific to BigFoot - called by events in Handler.handle_event()
        if event.actor.cp.state == "round_chage":
            print("Ayoo")
        match event.payload["type"]:
            case 'propose':
                ret = state_transition.propose(event.actor.cp, event)
            case 'pre_prepare':
                ret = state_transition.pre_prepare(event.actor.cp, event)
            case 'prepare':
                ret = state_transition.prepare(event.actor.cp, event)
            case 'commit':
                ret = state_transition.commit(event.actor.cp, event)
            case 'timeout':
                ret = timeouts.handle_timeout(event.actor.cp, event)
            case "fast_path_timeout":
                ret = timeouts.handle_timeout(event.actor.cp, event)
            case 'new_block':
                ret = state_transition.new_block(event.actor.cp, event)
            case _:
                return 'unhadled'

        return ret
