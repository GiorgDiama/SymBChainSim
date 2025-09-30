from Parameters import Parameters
from Engine.Scheduler import Scheduler

from Chain.Consensus import Rounds


if TYPE_CHECKING:
    from Chain.Consensus.Tendermint.TM_state import Tendermint
    from Engine.Event import Event

import logging

logger = logging.getLogger(__name__.split(".")[-1])

def handle_timeout(state: "Tendermint", event: "Event") -> str:
    """
    Handle a timeout event for a Tendermint node.

    Validates round, checks for protocol updates or desynchronisation, and
    changes round if appropriate.

    Args:
        state (Tendermint): The Tendermint protocol state instance.
        event (Event): The timeout event to process.

    Returns:
        str: One of "invalid", "changed_protocol", "detected_desync", or "handled".
    """
    if event.payload["round"] != state.rounds.round:
        return "invalid"

    if state.node.update(event.time):
        return "changed_protocol"

    is_syncing = event.actor.attempt_sync(event.time)
    if is_syncing:
        return "detected_desync"

    Rounds.change_round(state.node, event.time)
    return "handled"  # changes state to round_change but no need to handle backlog


def schedule_timeout(state: "Tendermint", time: float, add_time: bool = True) -> None:
    """
    Schedule a round timeout for a Tendermint node and keep a reference to it.

    Args:
        state (Tendermint): The Tendermint protocol state instance.
        time (float): Base simulation time to schedule relative to.
        add_time (bool, optional): If True, add the configured timeout duration.
            Defaults to True.
    """
    if add_time:
        time += Parameters.Tendermint["timeout"]

    payload = {"type": "timeout", "round": state.rounds.round, "CP": state.NAME}

    if state.timeout is not None and Parameters.simulation["debugging_mode"]:
        state.node.queue.remove_event(state.timeout)

    event = Scheduler.schedule_event(state.node, time, payload, state.handle_event)

    state.timeout = event
