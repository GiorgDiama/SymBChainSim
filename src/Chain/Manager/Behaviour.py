from Chain.Parameters import Parameters
from Chain.Event import SystemEvent

from random import sample, randint, expovariate
import sys


class Behaviour:
    def __init__(self, sim) -> None:
        self.sim = sim
        self.faulty = []
        self.byzantine = []

    def update_behaviour(self):
        self.set_faulty_nodes()
        self.set_byzantine_nodes()

    def set_byzantine_nodes(self):
        byzantine_params = Parameters.behaviour["byzantine_nodes"]
        sync_params = Parameters.behaviour["sync"]

        # Randomly choose which nodes will be byzantine
        self.byzantine = sample(
            self.sim.nodes, byzantine_params["num_byzantine"])

        # for each byzantine node
        for node in self.byzantine:
            node.behaviour.byzantine = True
            # set probability the node will intentionally make the sync process fail
            node.behaviour.sync_fault_chance = randint(sync_params["probs"]["low"],
                                                       sync_params["probs"]["high"])

    def set_faulty_nodes(self, node=None):
        fault_params = Parameters.behaviour["crash_probs"]

        self.faulty = sample(self.sim.nodes, fault_params["faulty_nodes"])

        for node in self.faulty:
            node.behaviour.faulty = True

            node.behaviour.mean_fault_time = randint(
                fault_params["mean_fault_time"]['low'],
                fault_params["mean_fault_time"]["high"]
            )

            node.behaviour.mean_recovery_time = randint(
                fault_params["mean_recovery_time"]['low'],
                fault_params["mean_recovery_time"]["high"]
            )

    def apply_behaviour(self):
        if "behaviour-off" in sys.argv:
            return 0

        ################ FAULT LOGIC ########################
        for fnode in self.faulty:
            if fnode.state.alive and (fnode.behaviour.fault_event is None or fnode.behaviour.fault_event.time > Parameters.simulation["simTime"]):
                next_fault_time = self.sim.clock + \
                    expovariate(1/fnode.behaviour.mean_fault_time)

                event = SystemEvent(
                    time=next_fault_time,
                    payload={
                        "type": "node fault",
                        "node": fnode
                    }
                )

                if fnode.behaviour.fault_event is not None:
                    self.sim.q.remove_event(fnode.behaviour.fault_event)

                fnode.behaviour.fault_event = event
                self.sim.q.add_event(event)
