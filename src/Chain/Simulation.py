from Chain.Node import Node
from Chain.Block import Block
from Chain.Transaction import TransactionFactory
from Chain.Parameters import Parameters
from Chain.EventQueue import Queue

import Chain.Consensus.PBFT.PBFT as PBFT
import Chain.Consensus.BigFoot.BigFoot as BigFoot

import Chain.tools as tools

class Simulation:
    def __init__(self, config=None) -> None:
        self.nodes = [Node(x) for x in range(Parameters.application["Nn"])]

        self.clock = 0
        
        self.manager = None

        self.current_cp = Parameters.simulation['init_CP']

        Parameters.simulation['txion_model'] = TransactionFactory(self.nodes)

        self.system_queue = Queue()

        self.q = Queue()

    def init_simulation(self, CP):
        genesis = Block.genesis_block()

        Parameters.simulation['txion_model'].generate_interval_txions(self.clock)

        for n in self.nodes:
            n.add_block(genesis, self.clock)
            CP.init(n)

    def get_next_event(self):
        # get next blockchain event
        next_events = [
            (x, x.next_event) for x in self.nodes 
            if x.state.alive and x.next_event is not None
        ]
        ret = min(next_events, key=lambda x: x[1])
        node, event = ret[0], ret[1]

        # get next system event
        sys_event = self.system_queue.get_next_event()
        
        if sys_event is not None and sys_event.time <= event.time:
            return self.manager, sys_event
        else:
            return node, event

    def sim_next_event(self):        
        handler, next_event = self.get_next_event()

        self.clock = next_event.time
    
        tools.debug_logs(msg=tools.print_global_eq(self, ret=True),
                             command=f"next -> {next_event} (enter to cont or give command): ",
                             simulator=self,
                             cmd_col=41,
                             clear=False)
        
        handler.handle_next_event()


    def run_simulation(self):
        state = self.sim_next_event()

        while self.clock <= Parameters.simulation['simTime']:
            state = self.sim_next_event(state)
        
        dist = {node.id: 0 for node in self.nodes}

        for block in self.nodes[0].blockchain[1:]:
            dist[block.miner] += 1

        print(dist)
    