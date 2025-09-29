from Parameters import Parameters

from Engine.Event import SystemEvent

from Chain.TransactionFactory import TransactionFactory

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from Manager.Manager import Manager


# -----------------------------------------------------------
#                      Network
# -----------------------------------------------------------


def schedule_scenario_update_network_event(manager: "Manager", info: List, time: float) -> None:
    """Schedule a scenario-driven network update system event.

    Args:
        manager (Manager): Simulation manager.
        info (List): List of (node_id, bandwidth) pairs.
        time (float): Simulation time to execute the event.

    Returns:
        None
    """
    event = SystemEvent(time=time, payload={"type": "scenario_update_network", "network_info": info})
    manager.sim.q.add_event(event)


def handle_scenario_update_network_event(manager: "Manager", event: SystemEvent) -> None:
    """Apply scenario-provided bandwidth values to nodes.

    Args:
        manager (Manager): Simulation manager.
        event (SystemEvent): Event whose payload contains "network_info": Iterable[(id, bw)].

    Returns:
        None
    """
    network_info = event.payload["network_info"]

    for id, bw in network_info:
        manager.sim.nodes[id].bandwidth = bw


# -----------------------------------------------------------
#                      Transactions
# -----------------------------------------------------------
def schedule_scenario_transactions_event(manager: "Manager", txion_list: List, time: float) -> None:
    """Schedule a system event to inject scenario-specified transactions.

    Args:
        manager (Manager): Simulation manager.
        txion_list (List): List of transactions (creator, id, timestamp, size_bytes).
        time (float): Simulation time to inject transactions.

    Returns:
        None
    """
    event = SystemEvent(
        time=time,
        payload={"type": "scenario_generate_txions", "txion_list": txion_list},
    )
    manager.sim.q.add_event(event)


def handle_scenario_transactions_event(manager: "Manager", event: SystemEvent) -> None:
    """Handle injection of scenario-provided transactions into the simulation.

    Args:
        manager (Manager): Simulation manager.
        event (SystemEvent): Event containing "txion_list" with transactions.

    Returns:
        None
    """
    TransactionFactory.add_scenario_transactions(event.payload["txion_list"])


# -----------------------------------------------------------
#                      Fault and Recovery
# -----------------------------------------------------------


def schedule_scenario_fault_and_recovery_events(manager: "Manager", fault_list: List) -> None:
    """Schedule fault and recovery events for nodes based on scenario.

    Each tuple is (node_id, fail_at, downtime). Recovery is scheduled at fail_at + downtime.

    Args:
        manager (Manager): Simulation manager.
        fault_list (List): List of fault specifications.

    Returns:
        None
    """
    for entry in fault_list:
        fail_at = entry[1]
        node = manager.sim.nodes[entry[0]]

        event = SystemEvent(time=fail_at, payload={"type": "scenario_fault", "node": node})
        node.behaviour.fault_event = event
        manager.sim.q.add_event(event)

        recover_at = entry[1] + entry[2]
        event = SystemEvent(time=recover_at, payload={"type": "scenario_recovery", "node": node})
        node.behaviour.recovery_event = event
        manager.sim.q.add_event(event)


def handle_scenario_fault_event(manager: "Manager", event: SystemEvent) -> None:
    """Handle a scenario-driven node fault by killing the node.

    Args:
        manager (Manager): Simulation manager.
        event (SystemEvent): Fault event with "node" to be killed.

    Returns:
        None
    """
    event.payload["node"].kill()


def handle_scenario_recovery_event(manager: "Manager", event: SystemEvent) -> None:
    """Handle a scenario-driven node recovery by resurrecting the node.

    Args:
        manager (Manager): Simulation manager.
        event (SystemEvent): Recovery event with "node" to resurrect.

    Returns:
        None
    """
    node = event.payload["node"]
    time = event.time

    node.resurrect(time)
