from Parameters import Parameters, read_yaml
from Engine.Event import SystemEvent
from Chain.Network import Network

from random import normalvariate

from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from Manager.Manager import Manager


class DynamicParameters:
    """
    Holds dynamic simulation parameter distributions loaded from YAML.

    Attributes:
        network (Dict[str, Any]): Network-related dynamic parameters.
        workload (Dict[str, Any]): Workload-related dynamic parameters.
    """

    network: Dict[str, Any] = {}
    workload: Dict[str, Any] = {}

    @staticmethod
    def init_parameters() -> None:
        """Load dynamic simulation parameters from configuration file.

        Returns:
            None
        """
        params = read_yaml(Parameters.dynamic_sim["config"])

        DynamicParameters.network = params["network"]
        DynamicParameters.workload = params["workload"]


# -----------------------------------------------------------
#                      Network
# -----------------------------------------------------------


def schedule_update_network_event(manager: "Manager", init: bool = False) -> None:
    """
    Schedule periodic dynamic updates for network parameters.

    Args:
        manager (Manager): Simulation manager.
        init (bool): If True, schedule at current clock; otherwise offset by tx_interval.

    Returns:
        None
    """
    if DynamicParameters.network["use"] == False:
        return

    time = manager.sim.clock
    if not init:
        time += Parameters.application["tx_interval"]

    event = SystemEvent(
        time=time,
        payload={
            "type": "update_network",
        },
    )

    manager.sim.q.add_event(event)


def handle_update_network_event(manager: "Manager", event: SystemEvent) -> None:
    """
    Handle dynamic network updates by sampling new bandwidth parameters and applying them.

    Args:
        manager (Manager): Simulation manager.
        event (SystemEvent): Dynamic network update event.

    Returns:
        None
    """
    Parameters.network["bandwidth"]["mean"] = normalvariate(*DynamicParameters.network["mu_dist"])

    Parameters.network["bandwidth"]["dev"] = normalvariate(*DynamicParameters.network["sigma_dist"])

    if Parameters.dynamic_sim.get("print_updates", False):
        print(f"{'Network updated':<20}: mu= {Parameters.network['bandwidth']['mean']} sigma= {Parameters.network['bandwidth']['dev']}")

    Network.set_bandwidths()

    schedule_update_network_event(manager)


# -----------------------------------------------------------
#                      Workload
# -----------------------------------------------------------


def schedule_update_workload_event(manager: "Manager", init: bool = False) -> None:
    """
    Schedule periodic dynamic updates for workload parameters.

    Args:
        manager (Manager): Simulation manager.
        init (bool): If True, schedule at current clock; otherwise offset by tx_interval.

    Returns:
        None
    """
    if DynamicParameters.workload["use"] == False:
        return

    time = manager.sim.clock
    if not init:
        time += Parameters.application["tx_interval"]

    event = SystemEvent(
        time=time,
        payload={
            "type": "update_workload",
        },
    )

    manager.sim.q.add_event(event)


def handle_update_workload_event(manager: "Manager", event: SystemEvent) -> None:
    """
    Handle dynamic workload updates by sampling new TPS and transaction size.

    Args:
        manager (Manager): Simulation manager.
        event (SystemEvent): Dynamic workload update event.

    Returns:
        None
    """
    # generation algorithm requires an int
    Parameters.application["tx_per_sec"] = int(normalvariate(*DynamicParameters.workload["tx_per_sec_norm_dist"]))

    # since transaction sizes are quire small abs to ensure no negative values
    Parameters.application["tx_size"] = abs(normalvariate(*DynamicParameters.workload["tx_size_norm_dist"]))

    if Parameters.dynamic_sim.get("print_updates", False):
        print(f"{'Workload  updated':<20}: TPS= {Parameters.application['tx_per_sec']} size= {Parameters.application['tx_size']}")

    schedule_update_workload_event(manager)
