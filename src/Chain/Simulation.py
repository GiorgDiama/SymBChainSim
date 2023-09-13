from Chain.Node import Node
from Chain.Block import Block
from Chain.Transaction import TransactionFactory
from Chain.Parameters import Parameters
from Chain.EventQueue import Queue
from Chain.Handler import handle_event

from Chain.Consensus.PBFT.PBFT import PBFT
from Chain.Consensus.BigFoot.BigFoot import BigFoot

import Chain.tools as tools

CPs = {
    PBFT.NAME: PBFT,
    BigFoot.NAME: BigFoot
}

class Simulation:
    def __init__(self) -> None:
        # load params (cmd and env)
        tools.set_env_vars_from_config()
        Parameters.load_params_from_config()
        Parameters.application["CP"] = CPs[Parameters.simulation["init_CP"]]

        self.q = Queue()

        self.nodes = [Node(x, self.q) for x in range(Parameters.application["Nn"])]

        self.clock = 0
        
        self.current_cp = Parameters.application['CP']

        Parameters.simulation['txion_model'] = TransactionFactory(self.nodes)

    def init_simulation(self):
        genesis = Block.genesis_block()

        Parameters.simulation['txion_model'].generate_interval_txions(self.clock)
    
        for n in self.nodes:
            n.add_block(genesis, self.clock)
            n.cp = self.current_cp(n)
            n.cp.init()

    def sim_next_event(self):        
        next_event = self.q.pop_next_event()
        self.clock = next_event.time

        handle_event(next_event)

    def run_simulation(self):
        self.sim_next_event()
        
        next_ti = Parameters.application["TI_dur"]
        while self.clock <= Parameters.simulation['simTime']:
            if self.clock >= next_ti:
                Parameters.simulation['txion_model'].generate_interval_txions(next_ti)
                next_ti += Parameters.application["TI_dur"]
                
            self.sim_next_event()
        
    