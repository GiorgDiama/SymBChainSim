from Parameters import Parameters
from Engine.Event import SystemEvent
import Utils.Snapshots as Snapshots

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Manager.Manager import Manager


def schedule_snapshot_event(manager: "Manager") -> None:
    """Schedule the next periodic snapshot system event.

    Args:
        manager (Manager): The simulation manager orchestrating the DES.

    Returns:
        None
    """
    time = manager.sim.clock + Parameters.simulation["snapshot_interval"]

    event = SystemEvent(
        time=time, payload={"type": "snapshot", "time_last": manager.sim.clock}
    )
    manager.sim.q.add_event(event)


def handle_snapshot_event(manager: "Manager", event: SystemEvent) -> None:
    """Handle a snapshot event by persisting the current simulation state.

    Args:
        manager (Manager): The simulation manager.
        event (SystemEvent): The snapshot system event containing the time of the last tick ("time_last").

    Returns:
        None
    """
    Snapshots.take_snapshot(manager.sim, event.payload["time_last"])
    schedule_snapshot_event(manager)
