from Chain.Scheduler import Scheduler

from Chain.Parameters import Parameters

from types import SimpleNamespace

from Chain.tools import color


class Behaviour():
    pass

class Node():
    '''
    Node - models a blockchain node

    Attributes:
        id: unique node id
        blockchain: list of blocks
        pool: list of new transactions not yet added to blocks
        bloks: No. of blocks
        state: A namespace denoting the sate of the node
            synced...
            alive...
            cp: a reference to the CP class
            cp_state: a namepsace storring CP specific data (defined by the CP)
            extra_data: a map sotring extra data needed in the node

        Queue: The event queue sotring events (used in the simulation)

        Backlog: Stores 'future' events
            When current event cannot be executed (due to message delays
            causing lag in state updates) it is added to the backlog. Once
            state is updated the backlogged events are checked to see whether
            they can be excecuted.
            example in PBFT:
                Node_1 recieves a valid commit message in pre-prepare state.
                Node_1 cannot process such a message since he has not received enough prepare messges to move to prepared state
                Node_1 stores commit message in the backlog (instead of ingoring since it).
                After node_1 recieves enough prepare messages and its state is updated to prepared the backlog is checked
                The commit message can be handled now
                Without backlog Node_1 would have not be able to complete the CP protocol
        p: Simulation parameters
    '''

    def __init__(self, id, queue):
        self.id = id
        self.blockchain = []
        self.pool = []
        self.blocks = 0

        self.neighbours = []
        self.location = None
        self.bandwidth = None

        self.state = SimpleNamespace(
            alive=True,
            synced=True
        )

        self.cp = None

        self.behaviour = Behaviour()

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
                return f"{color(f'Node: {self.id}',42)}\n   LATEST_BLOCKS {self.trunc_ids}  local_pool: {len(self.pool)}\n SYNCED: {self.state.synced} | CP: {self.cp.NAME} | CHANGE_TO: {Parameters.application['CP'].NAME} | req msg: {Parameters.application['required_messages']} f: {Parameters.application['f']} \
                        \n   CP: {self.cp.state_to_string()} \n   BEHAVIOUR: {self.behaviour_state_to_string}\n"
            else:
                return f"Node: {self.id}"
        else:
            if full:
                return f"{color(f'**dead** Node: {self.id}',41)} \n   LATEST_BLOCKS {self.trunc_ids} local_pool: {len(self.pool)}\n    SYNCED: {self.state.synced} | CP: {self.cp.NAME} | CHANGE_TO: {Parameters.application['CP'].NAME}\
                        \n   CP: {self.cp.state_to_string()} \n   BEHAVIOUR: {self.behaviour_state_to_string}\n"
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
        pass

    def stored_txions(self, num=None):
        '''
            Returns the last 'num' txions from the pool - if num is None get everything
        '''
        if num is not None:
            num = -num

        return [x.id for x in self.pool[num:]]

    def blockchain_length(self):
        return len(self.blockchain)-1

    def synced_with_neighbours(self):
        '''
            Comparing the latest block of current node with all neighbours to check sync status
        '''
        # create (neighbour, block, depth) pairs from neighbours that have a later block than us
        neighbours_ahead = [
            (n, n.last_block, n.last_block.depth) for n in self.neighbours
            if n.last_block.depth > self.last_block.depth]

        if neighbours_ahead:
            # return false and the node that is furthurest ahead
            node_furthest_ahead = max(neighbours_ahead, key=lambda x: x[2])
            return False, node_furthest_ahead[0]
        else:
            return True, None

    def kill(self):
        self.state.alive = False

    def resurect(self):
        self.state.alive = True

    def add_block(self, block, time):
        '''
            Adds 'block' to blockchain at time 'time'
        '''
        block.time_added = time
        self.blockchain.append(block)

        self.pool = Parameters.tx_factory.remove_transactions_from_pool(
            block.transactions, self.pool)


    def add_event(self, event):
        if self.state.alive:
            self.queue.add_event(event)

    def update(self, time):
        pass