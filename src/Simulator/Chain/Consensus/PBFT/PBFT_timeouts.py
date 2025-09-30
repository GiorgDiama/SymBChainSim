from Parameters import Parameters

from Engine.Scheduler import Scheduler

from Chain.Consensus import Rounds

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Chain.Consensus.PBFT.PBFT_state import PBFT
    from Engine.Event import Event

import logging

logger = logging.getLogger(__name__.split(".")[-1])


def handle_timeout(state: "PBFT", event: "Event") -> str:
    """
    Handle a timeout event for a PBFT node.

    Validates the event round, checks for protocol updates or desynchronisation,
    and triggers a round change when appropriate.

    Args:
        state (PBFT): The PBFT protocol state instance.
        event (Event): The timeout event to process.

    Returns:
        str: One of "invalid", "changed_cp", "detected_desync", or "handled".
    """
    # ignore timeout events from other rounds (a timeout at future round should never happen)
    if event.payload["round"] != state.rounds.round:
        logger.debug(f"[Node {state.node.id}] ignoring TO - not from this round")
        return "invalid"

    if state.node.update(event.time):
        return "changed_cp"

    is_syncing = event.actor.attempt_sync(event.time)
    if is_syncing:
        return "detected_desync"

    Rounds.change_round(state.node, event.time)
    return "handled"  # changes state to round_change but no need to handle backlog


def schedule_timeout(state: "PBFT", time: float, add_time: bool = True) -> None:
    """
    Schedule a round timeout for a PBFT node and keep a reference to it.

    Args:
        state (PBFT): The PBFT protocol state instance.
        time (float): Base simulation time to schedule relative to.
        add_time (bool, optional): If True, add the configured PBFT timeout duration. Defaults to True.

    """
    if add_time:
        time += Parameters.PBFT["timeout"]

    payload = {"type": "timeout", "round": state.rounds.round, "CP": state.NAME}

    if state.timeout is not None and Parameters.simulation["debugging_mode"]:
        state.node.queue.remove_event(state.timeout)

    logger.debug(f"[Node {state.node.id}] scheduling TO event @ {time}")

    event = Scheduler.schedule_event(state.node, time, payload, state.handle_event)

    state.timeout = event
