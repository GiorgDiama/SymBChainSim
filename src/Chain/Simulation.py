from .Node import Node
from .Block import Block
from .TransactionFactory import TransactionFactory
from .Parameters import Parameters
from .EventQueue import Queue
from .Handler import handle_event

from .Utils import tools

from .Event import SystemEvent


class Simulation:
    '''
        Basic blockchain simulation instance (must be managed by a Manager object)

        q: The event queue storing simulation events
        clock: The event driven simulation clock

        nodes: the list of blockchain nodes 
        current_cp: (string) the name of current consensus protocol
        manager: a reference to the manager managing this simulation
    '''

    def __init__(self) -> None:
        self.q = Queue()
        self.clock = 0

        self.nodes = [Node(x, self.q)
                      for x in range(Parameters.application["Nn"])]

        self.current_cp = Parameters.application['CP']

        self.manager = None

        # TODO: stop storing the TX factory in the parameters module ... 
        # initialise the transaction factory for this simulation and store in the in the Parameters module so that it can be accessed by all models (...)
        Parameters.tx_factory = TransactionFactory(self.nodes)

    def init_simulation(self):
        '''
            Initialises the blockchains with the genesis block and start the consensus protocol on the nodes
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
        
        # SANITY: this should NEVER happen
        if self.clock > next_event.time:
            raise RuntimeError(f"Next event: {next_event} is in the past! current clock: {self.clock}")

        # update sim clocks
        self.clock = next_event.time

        tools.debug_logs(msg=f"Next:{next_event}", command="Command:", simulator=self)

        # call appropriate handler based on event type
        if isinstance(next_event, SystemEvent):
            self.manager.handle_system_event(next_event)
        else:
            handle_event(next_event)
