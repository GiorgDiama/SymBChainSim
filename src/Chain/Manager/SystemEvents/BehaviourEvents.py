from Chain.Parameters import Parameters, read_yaml
from Chain.Event import SystemEvent
from Chain.Network import Network
from Chain.Metrics import Metrics


import random

class Behaviour:
    byzantine = {}
    faulty = {}

    faulty_nodes = None
    byzantine_nodes = None

    @staticmethod
    def init(manager):
        # read parameters from behaviour config file
        params = read_yaml(Parameters.behaviour["config"])
        Behaviour.byzantine = params["byzantine"]
        Behaviour.faulty = params["faulty"]

        # chose faulty nodes
        Behaviour.faulty_nodes = random.sample(
            manager.sim.nodes, k=Behaviour.faulty["num"])

        # set behaviour settings for each faulty node
        for n in Behaviour.faulty_nodes:
            mean_fault_range = Behaviour.faulty['mean_fault_range']
            mean_recover_range = Behaviour.faulty['mean_recovery_range']
            n.behaviour.faulty = True
            n.behaviour.mean_fault_time = random.randint(*mean_fault_range)
            n.behaviour.mean_recovery_time = random.randint(
                *mean_recover_range)


########### RANDOM FAULTS ########

def schedule_random_fault_event(manager, time, node=None):
    if node is None:
        # if no node is given, initialise faults for all faulty nodes
        for n in Behaviour.faulty_nodes:
            fail_at = time + \
                random.expovariate(1/n.behaviour.mean_fault_time)

            event = SystemEvent(
                time=fail_at,
                payload={
                    "type": "random_fault",
                    "node": n
                }
            )
            n.behaviour.fault_event = event
            manager.sim.q.add_event(event)
    else:
        fail_at = time + \
            random.expovariate(1/node.behaviour.mean_fault_time)
        event = SystemEvent(
            time=fail_at,
            payload={
                "type": "random_fault",
                "node": node
            }
        )
        node.behaviour.fault_event = event
        manager.sim.q.add_event(event)


def handle_random_fault_event(manager, event):
    event.payload['node'].kill()
    schedule_recovery_event(manager, event.time, event.payload['node'])


def schedule_recovery_event(manager, time, node):
    recover_at = time + \
        random.expovariate(1/node.behaviour.mean_recovery_time)
    event = SystemEvent(
        time=recover_at,
        payload={
            "type": "recovery",
            'node': node
        }
    )
    node.behaviour.recovery_event = event
    manager.sim.q.add_event(event)


def handle_recover_event(manager, event):
    node = event.payload['node']
    time = event.time

    node.resurrect(time)

    schedule_random_fault_event(manager, event.time, event.payload['node'])
