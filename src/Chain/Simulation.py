from Chain.Node import Node
from Chain.Block import Block
from Chain.Transaction import TransactionFactory
from Chain.Parameters import Parameters
from Chain.EventQueue import Queue
from Chain.Handler import handle_event

from Chain.Consensus.PBFT.PBFT import PBFT
from Chain.Consensus.BigFoot.BigFoot import BigFoot

import Chain.tools as tools

from Chain.Event import SystemEvent

import sys


class Simulation:
    def __init__(self) -> None:
        self.q = Queue()

        self.nodes = [Node(x, self.q)
                      for x in range(Parameters.application["Nn"])]

        self.clock = 0

        self.current_cp = Parameters.application['CP']

        self.manager = None

        Parameters.simulation['txion_model'] = TransactionFactory(self.nodes)

    def init_simulation(self):
        genesis = Block.genesis_block()

        Parameters.simulation['txion_model'].generate_interval_txions(
            self.clock)

        for n in self.nodes:
            n.add_block(genesis, self.clock)
            n.cp = self.current_cp(n)
            n.cp.init()

    def sim_next_event(self):
        next_event = self.q.pop_next_event()

        self.clock = next_event.time

        print(
            f"\rSimulation clock: {'%.2f'%self.clock}/{Parameters.simulation['simTime']}", end='', flush=True)

        tools.debug_logs(msg=tools.sim_info(self, print_event_queues=True),
                         command=f"Next event: {next_event}", simulator=self)

        if isinstance(next_event, SystemEvent):
            self.manager.handle_next_event(next_event)
        else:
            handle_event(next_event)

    def run_simulation(self):
        while self.clock <= Parameters.simulation['simTime']:
            self.sim_next_event()
