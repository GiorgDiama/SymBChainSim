from ...Parameters import Parameters, read_yaml
from ...Utils import tools

import random

class Behaviour:
    byzantine = {}
    faulty = {}

    faulty_nodes = None
    byzantine_nodes = None

    @staticmethod
    def init(manager):
        # read behaviour config file
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
            n.behaviour.mean_recovery_time = random.randint(*mean_recover_range)


########### RANDOM FAULTS ##########

def schedule_random_fault_event(manager, time, node=None):
    if node is None:
        # if no node is given, initialise faults for all faulty nodes
        for faulty_node in Behaviour.faulty_nodes:
            schedule_random_fault_event(manager, time, faulty_node)
        return 'initialised_fault_events'
    
    fail_at = time + random.expovariate(1/node.behaviour.mean_fault_time)
    payload={
        "type": "random_fault",
        "node": node
    }
    event = manager.schedule_system_event(fail_at, payload)
    node.behaviour.fault_event = event

    return

def handle_random_fault_event(manager, event):
    event.payload['node'].kill()

    if Parameters.behaviour.get('print_updates', False):
        s = tools.color(f"Node {event.payload['node'].id} failed!", c=41)
        print(s)

    schedule_recovery_event(manager, event.time, event.payload['node'])


def schedule_recovery_event(manager, time, node):
    recover_at = time + random.expovariate(1/node.behaviour.mean_recovery_time)
    payload={
        "type": "recovery",
        'node': node
    }
    event = manager.schedule_system_event(recover_at, payload)
    node.behaviour.recovery_event = event
    

def handle_recover_event(manager, event):
    node = event.payload['node']
    time = event.time

    node.resurrect(time)

    if Parameters.behaviour.get('print_updates', False):
        s = tools.color(f"Node {event.payload['node'].id} recovered!", c=42)
        print(s)

    schedule_random_fault_event(manager, event.time, event.payload['node'])
