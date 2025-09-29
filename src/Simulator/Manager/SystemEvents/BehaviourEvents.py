from Parameters import Parameters, read_yaml
from Utils import Tools

import random

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from Manager.Manager import Manager
    from Chain.Node import Node


class Behaviour:
    """Holds behaviour configuration and chosen faulty/byzantine nodes.

    Attributes:
        byzantine (dict): Byzantine behaviour parameters loaded from YAML.
        faulty (dict): Faulty behaviour parameters loaded from YAML.
        faulty_nodes (list[Node]): Nodes selected to exhibit faulty behaviour.
        byzantine_nodes (list[Node]): Nodes selected to exhibit byzantine behaviour.
    """

    byzantine = {}
    faulty = {}

    faulty_nodes = []
    byzantine_nodes = []

    @staticmethod
    def init(manager: "Manager") -> None:
        """Initialise behaviour settings and select faulty nodes.

        Args:
            manager (Manager): Simulation manager.

        Returns:
            None
        """
        # read behaviour config file
        params = read_yaml(Parameters.behaviour["config"])
        Behaviour.byzantine = params["byzantine"]
        Behaviour.faulty = params["faulty"]

        # chose faulty nodes
        Behaviour.faulty_nodes = random.sample(manager.sim.nodes, k=Behaviour.faulty["num"])

        # set behaviour settings for each faulty node
        for n in Behaviour.faulty_nodes:
            mean_fault_range = Behaviour.faulty["mean_fault_range"]
            mean_recover_range = Behaviour.faulty["mean_recovery_range"]
            n.behaviour.faulty = True
            n.behaviour.mean_fault_time = random.randint(*mean_fault_range)
            n.behaviour.mean_recovery_time = random.randint(*mean_recover_range)


# -----------------------------------------------------------
#                      Random Faults
# -----------------------------------------------------------


def schedule_random_fault_event(manager: "Manager", time: float, node: Optional["Node"] = None) -> Optional[str]:
    """Schedule a random fault event for a specific node or initialise all.

    Args:
        manager (Manager): Simulation manager.
        time (float): Current simulation time used as base for sampling.
        node (Optional[Node]): Target node; if None, schedule for all faulty nodes.

    Returns:
        Optional[str]: "initialised_fault_events" when initialising all; otherwise None.
    """
    if node is None:
        # if no node is given, initialise faults for all faulty nodes
        for faulty_node in Behaviour.faulty_nodes:
            schedule_random_fault_event(manager, time, faulty_node)
        return "initialised_fault_events"

    fail_at = time + random.expovariate(1 / node.behaviour.mean_fault_time)
    payload = {"type": "random_fault", "node": node}
    event = manager.schedule_system_event(fail_at, payload)
    node.behaviour.fault_event = event

    return None


def handle_random_fault_event(manager: "Manager", event) -> None:
    """Handle a random fault event by killing the node and scheduling recovery.

    Args:
        manager (Manager): Simulation manager.
        event: SystemEvent with payload {"node": Node} and event.time.

    Returns:
        None
    """
    event.payload["node"].kill()

    if Parameters.behaviour.get("print_updates", False):
        print(Tools.color(f"Node {event.payload['node'].id} failed!", c=41))

    schedule_recovery_event(manager, event.time, event.payload["node"])


# -----------------------------------------------------------
#                      Recovery
# -----------------------------------------------------------


def schedule_recovery_event(manager: "Manager", time: float, node: "Node") -> None:
    """Schedule a recovery event for a node following a failure.

    Args:
        manager (Manager): Simulation manager.
        time (float): Base time used for sampling the recovery delay.
        node (Node): Failed node to recover.

    Returns:
        None
    """
    recover_at = time + random.expovariate(1 / node.behaviour.mean_recovery_time)
    payload = {"type": "recovery", "node": node}
    event = manager.schedule_system_event(recover_at, payload)
    node.behaviour.recovery_event = event


def handle_recover_event(manager: "Manager", event) -> None:
    """Handle a node recovery by resurrecting and re-scheduling its next fault.

    Args:
        manager (Manager): Simulation manager.
        event: SystemEvent with payload {"node": Node} and event.time.

    Returns:
        None
    """
    node = event.payload["node"]
    time = event.time

    node.resurrect(time)

    if Parameters.behaviour.get("print_updates", False):
        print(Tools.color(f"Node {event.payload['node'].id} recovered!", c=42))

    schedule_random_fault_event(manager, event.time, event.payload["node"])
