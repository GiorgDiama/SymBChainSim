from ...Block import Block
from ...Parameters import Parameters
from ...Handler import handle_backlog

from  ...Consensus import Rounds

from  ..PBFT import PBFT_transition as state_transitions
from  ..PBFT import PBFT_timeouts as timeouts
from  ..PBFT import PBFT_messages as messages

from random import randint

class PBFT():
    '''
    Practical Byzantine Fault Tolerance Consensus Protocol

    PBFT State:
        round - current round
        change_to - candidate round to change to
        state - PBFT node state (new_round, pre-prepared, prepared, committed, round_change)]
        msgs: list of messages received from other nodes
        timeout - reference to latest timeout event (when node state updates it is used to find event and delete from event queue)
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
        return f"round: {self.rounds.round} | node_state:{self.state} | miner:{self.miner}| block:{self.block.id if self.block is not None else -1} | msgs: {self.msgs} | timeout_event: {(round(self.timeout.time,3), self.timeout.payload['round']) if self.timeout is not None else -1}"
        
    def reset_msgs(self, round):
        '''
            Reset the state of the consensus messages and change round votes
        '''
        self.msgs = {'prepare': [], 'commit': []}
        Rounds.reset_votes(self.node)

    def count_votes(self, type, round):
        '''
            Returns the number of votes for specific message type 
        '''
        return len(self.msgs[type])

    def process_vote(self, type, sender, round, time):
        '''
            Counts a vote of 'type' by 'sender'
        '''
        self.msgs[type] += [sender.id]

    def validate_message(self, event):
        '''
            Defines logic to validate messages according to the protocol
        '''
        round, current_round = event.payload['round'], self.rounds.round

        if round < current_round:
            return False, None
        elif round == current_round:
            return True, None
        else:
            return True, 'backlog'

    def validate_block(self, block):
        '''
            Logic to validate block 
        '''
        return block.depth - 1 == self.node.last_block.depth and block.extra_data["round"] == self.rounds.round

    def init(self, time=0, starting_round=0):
        self.set_state()
        self.start(starting_round, time)

    def get_miner(self):
        '''
            Implements proposer selection algorithms used by the block producers to figure out who is the proposer per round

            round_robin: current round mod number of block producers
            hash_based: (last_block_hash + self.round) mod number of block producers
        '''
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
        '''
            Logic to create a PBFT block
        '''
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
            block.size = size + Parameters.data['base_block_size']
            time += + Parameters.execution['creation_time']
            time += len(transactions) * Parameters.execution['time_per_tx']
            return block, time  
        else:
            return None, time

    def start(self, new_round=0, time=0):
        '''
            Entry point into the protocol initialises state and utilises the
            proposer selection mechanisms to dictate the behaviour of the node
        '''
        if self.node.update(time):
            return 0

        self.state = 'new_round'
        self.reset_msgs(new_round)
        self.rounds.round = new_round
        self.block = None
        self.get_miner()

        # taking into account block interval for the proposal round timeout
        time += Parameters.data["block_interval"]

        timeouts.schedule_timeout(self, time)

        # if the current node is the miner, schedule propose block event
        if self.miner == self.node.id:
            messages.schedule_propose(self, time)
        else:
            # check if any future events are here for this round
            # slow nodes might miss pre_prepare vote so its good to check early
            handle_backlog(self.node, time)

    def init_round_change(self, time):
        '''
            Executes any protocol specific actions!
            Called by the Rounds module when a node enters the round_change state 
        '''
        timeouts.schedule_timeout(self, time, add_time=True)

    def rejoin(self, time):
        '''
            Defines the protocol specific rejoin logic for PBFT
        '''
        self.set_state() # set node's protocol state 
        round = self.node.blockchain[-1].extra_data['round'] + 1 # set round to latest known round (latest block round + 1)
        # NOTE: if this node rejoins at earlier round it's possible that it will try to propose a block. This will be ignored now but if wrong proposals are tracked this should be considered
        self.start(round, time) # start the protocol

    ########################## HANDLER ###########################

    @staticmethod
    def handle_event(event):
        '''
            Local handler of PBFT handles all event types produced by the protocol
        '''
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
                return 'unhandled'
