from Chain.Node import Node
from Chain.Block import Block
from Chain.TransactionFactory import TransactionFactory
from Chain.Parameters import Parameters
from Chain.EventQueue import Queue
from Chain.Handler import handle_event

import Chain.tools as tools

from Chain.Event import SystemEvent

from Chain.Consensus.PBFT.PBFT_state import PBFT
from Chain.Consensus.BigFoot.BigFoot_state import BigFoot


class Simulation:
    '''
        Basic blockchain simulation instance (must be managed by a Manager object)

        q: The event queue storing simulation events
        clock: The event driven simulation clock

        nodes: a list of blockchain nodes 
        current_cp: (string) the name of current consensus protocol
        manager: a reference to the manager instance managing this simulation

    '''
    def __init__(self) -> None:
        self.q = Queue()
        self.clock = 0

        self.nodes = [Node(x, self.q)
                      for x in range(Parameters.application["Nn"])]

        self.current_cp = Parameters.application['CP']

        self.manager = None

        '''
            TODO: Move this somewhere else
                - ideally, stop storing the TX factory in the parameters module!
        '''
        # initialise the transaction factory for this simulation and store in the in the Parameters module so that it can be accessed by all models (...)
        Parameters.tx_factory = TransactionFactory(self.nodes)

    def init_simulation(self):
        '''
            Initialises the simulation (genesis block and consensus protocols)
        '''
        genesis = Block.genesis_block()

        # for each node: add the genesis block, set and initialise CP (NOTE: cp.init() produces the first events to kickstart the simulation)
        for n in self.nodes:
            n.add_block(genesis, self.clock)
            n.cp = self.current_cp(n)
            n.cp.init()

    def sim_next_event(self):
        '''
            Retrieves and executes the next event in the event queue (q) updating the event driven clock
        '''
        tools.debug_logs(msg=tools.sim_info(self, print_event_queues=True))

        # get next event
        next_event = self.q.pop_next_event()
        # update sim clocks
        self.clock = next_event.time

        tools.debug_logs(msg=f"Next:{next_event}",
                         command="Command:", simulator=self)

        # call appropriate handler based on event type
        if isinstance(next_event, SystemEvent):
            self.manager.handle_system_event(next_event)
        else:
            handle_event(next_event)
