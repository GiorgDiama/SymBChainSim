from .Scheduler import Scheduler
from .Parameters import Parameters
from .Consensus import HighLevelSync
from .Utils.tools import color

from types import SimpleNamespace
from collections import deque

class Node():
    '''
    Node - models a generic blockchain node

    Attributes:
        id: unique node id
        blockchain: list of blocks
        pool: list of new transactions not yet added to blocks
        blocks: No. of blocks
        state: A namespace denoting the sate of the node
            synced...
            alive...
            cp: a reference to the CP class
            cp_state: a namespace storing CP specific data (defined by the CP)
            extra_data: a map storing extra data needed in the node

        Queue: The event queue of the DES

        Backlog: Stores 'future' events
            When an event appears to be from the future (e.g. from nodes that are further ahead in the consensus processes) it as added to the backlog.
            Once the state is updated, the backlogged events are checked to see whether they can be executed.
            example in PBFT:
                Node_1 receives a valid commit message while in the 'pre-prepare' state.
                Node_1 cannot process such a message since he has not received enough prepare messages to move to the 'prepared' state
                Node_1 stores the commit message in its backlog (instead of ignoring since it could be valid).
                After node_1 receives enough prepare messages and its state is updated to 'prepared' the backlog is checked
                The commit message can now be handled properly
                Without the backlog mechanism Node_1 might not have been able to complete the CP protocol and could eventually desync!
    '''

    def __init__(self, id, queue):
        self.id = id
        self.blockchain = []
        self.pool = deque([])
        self.blocks = 0

        self.neighbours = None
        self.location = None
        self.bandwidth = None

        self.state = SimpleNamespace(
            alive=True,
            synced=True,
        )

        self.cp = None

        self.behaviour = SimpleNamespace(
            faulty = None,
            mean_fault_time = None,
            mean_recovery_time = None,
            fault_event = None,
            recovery_event = None,
            byzantine = None,
            sync_fault_chance = None,
        )

        self.backlog = []

        self.scheduler = Scheduler(self)

        self.queue = queue

        # reconfiguration
        self.configuration = []

    def __repr__(self):
        if self.state.alive:
            return f"Node: {self.id}"
        else:
            return f"\tDEAD - Node: {self.id}"

    def __str__(self, full=False):
        if self.state.alive:
            if full:
                return f"{color(f'Node: {self.id}',42)}\n   LATEST_BLOCKS {self.trunc_ids}  local_pool: {len(self.pool)} global_pool: {len(Parameters.tx_factory.global_mempool)} \n   SYNCED: {self.state.synced} | CP: {self.cp.NAME} | CHANGE_TO: {Parameters.application['CP'].NAME} | req msg: {Parameters.application['required_messages']} f: {Parameters.application['f']} \
                        \n   CP_state: {self.cp.state_to_string()} \n   BEHAVIOUR: {self.behaviour_state_to_string}\n"
            else:
                return f"Node: {self.id}"
        else:
            if full:
                return f"{color(f'**dead** Node: {self.id}',41)} \n   LATEST_BLOCKS {self.trunc_ids} local_pool: {len(self.pool)} global_pool: {len(Parameters.tx_factory.global_mempool)} \n   SYNCED: {self.state.synced} | CP: {self.cp.NAME} | CHANGE_TO: {Parameters.application['CP'].NAME}\
                        \n   CP_state: {self.cp.state_to_string()} \n   BEHAVIOUR: {self.behaviour_state_to_string}\n"
            else:
                return f"**DEAD** - Node: {self.id}"

    @property
    def ids(self):
        '''
            returns a list of all block ids in the nodes local blockchain
        '''
        return [x.id for x in self.blockchain]

    @property
    def trunc_ids(self):
        '''
            returns a list of the last 5 block ids in nodes local blockchain
        '''
        hidden_blocks = len(self.blockchain) - \
            5 if len(self.blockchain)-5 > 0 else 0
        return f"{hidden_blocks} hidden_blocks...{[f'{x.id} {x.consensus.NAME if x.consensus is not None else None}' for x in self.blockchain[-5:]]} {self.blockchain[-1].depth}"

    @property
    def last_block(self):
        return self.blockchain[-1]

    @property
    def behaviour_state_to_string(self):
        s = ""
        if self.behaviour.faulty:
            s += f"{color('FAULTY',41)} -> mean_fault_time: {self.behaviour.mean_fault_time} | recover_at: {self.behaviour.recovery_event}"
        else:
            s += "NOT FAULTY"
        s += '\t'
        if self.behaviour.byzantine:
            s += f"{color('BYZANTINE',41)}  -> fault_chance: {self.behaviour.sync_fault_chance}"
        else:
            s += "HONEST"

        return s

    def update(self, time):
        if Parameters.application["CP"].NAME != self.cp.NAME:
            self.cp = Parameters.application["CP"](self)
            self.cp.init(time)
            return True
        
        return False

    def reset(self):
        pass

    def stored_txions(self, num=None):
        '''
            Returns the last 'num' txions from the pool - if num is None returns a list of all txions in the pool
        '''
        num = 0 if num is None else -num

        return [x.id for x in self.pool[num:]]

    def blockchain_length(self):
        '''
            Returns the length of the blockchain (excluding the genesis block)
        '''
        return len(self.blockchain)-1

    def synced_with_neighbours(self):
        '''
            Compares the latest block of current node with all peers to check sync status
            If desynced, returns the node that is furthest
            TODO: associate a delay with this (only useful when this is called as part of an event)
        '''
        # create (neighbour, block, depth) pairs from neighbours that have a later block than us
        neighbours_ahead = [
            (n, n.last_block, n.last_block.depth) for n in self.neighbours
            if n.last_block.depth > self.last_block.depth]

        if neighbours_ahead:
            # return false and the node that is furthest ahead
            node_furthest_ahead = max(neighbours_ahead, key=lambda x: x[2])
            return False, node_furthest_ahead[0]
        else:
            return True, None

    def kill(self):
        self.state.alive = False

    def resurrect(self, time):
        '''
            Gracefully resurrects an offline node - attempts to retrieve new blocks from peers 
            if still synced calls protocol specific rejoin method
        '''
        self.state.alive = True
        
        # after the node is online, attempt to resync
        synced, synced_neighbour = self.synced_with_neighbours()
        if not synced:
            self.state.synced = False
            HighLevelSync.create_local_sync_event(self, synced_neighbour, time)
        else:
            self.cp.rejoin(time)
        

    def add_block(self, block, time, update_time_added=True):
        '''
            Adds 'block' to blockchain at time 'time'
            Removes included transactions from the memory pool
        '''
        if update_time_added:
            block.time_added = time
            
        self.blockchain.append(block)
        
        Parameters.tx_factory.mark_transactions_as_processed(block, self.pool)

    def add_event(self, event):
        '''
            Adds an event to the event queue
        '''
        if self.state.alive:
            self.queue.add_event(event)
