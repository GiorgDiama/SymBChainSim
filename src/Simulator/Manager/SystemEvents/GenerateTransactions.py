from Parameters import Parameters
from Engine.Event import SystemEvent
from Chain.TransactionFactory import TransactionFactory

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Manager.Manager import Manager


def schedule_transaction_generation_event(manager: "Manager", init: bool = False) -> None:
    """
    Schedule the next periodic transaction generation system event.

    Args:
        manager (Manager): Simulation manager.
        init (bool): If True, schedule at current clock; otherwise offset by TI_dur.

    Returns:
        None
    """
    time = manager.sim.clock
    if not init:
        time += Parameters.application["TI_dur"]

    event = SystemEvent(
        time=time,
        payload={
            "type": "generate_txions",
        },
    )

    manager.sim.q.add_event(event)


def handle_transaction_generation_event(manager: "Manager", event: SystemEvent) -> None:
    """
    Handle a transaction generation event by producing interval transactions.

    Args:
        manager (Manager): Simulation manager.
        event (SystemEvent): The event at whose time transactions are generated.

    Returns:
        None
    """
    TransactionFactory.generate_interval_txions(event.time)
    schedule_transaction_generation_event(manager)
