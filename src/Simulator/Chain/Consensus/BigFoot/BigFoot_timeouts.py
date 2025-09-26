from Parameters import Parameters

from Chain.Consensus.BigFoot import BigFoot_messages as messages
from Chain.Consensus import Rounds

from Engine.Scheduler import Scheduler

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Chain.Consensus.BigFoot.BigFoot_state import BigFoot
    from Engine.Event import Event

import logging

logger = logging.getLogger(__name__.split(".")[-1])


def handle_timeout(state: "BigFoot", event: "Event"):
    """
    Handles a timeout event for a BigFoot node
    Specifically for BigFoot, also handles the fast_path logic wherein a node has to check
    if the node has enough prepare votes (2f+1) to move to the prepared state broadcasting a commit message
    """
    if event.payload["round"] != state.rounds.round:
        logger.debug(
            f"INVALID - stale timeout - {event.payload['round']}!={state.rounds.round}"
        )
        return "invalid"

    time = event.time

    if event.payload["type"] == "fast_path_timeout":
        # set fast_path to false and remove TO event
        state.fast_path = False
        state.fast_path_timeout = None

        if not state.node.state.synced:
            logger.debug(f"INVALID - node is desynced")
            return "handled"

        logger.debug(
            f"Node {state.node.id} had it's fast path time out for round {state.rounds.round}!"
        )

        # In case fast path times out - check if we have enough prepare votes
        # now (if so go to prepared state)
        if (
            state.block is not None
            and len(state.msgs["prepare"])
            >= Parameters.application["required_messages"] - 1
        ):
            logger.debug(f"Node {state.node.id} has enough vote to broadcast COMMIT!")

            # change to prepared
            state.state = "prepared"
            # send commit message
            messages.broadcast_commit(state, time, state.block)
            # count own vote
            state.process_vote("commit", state.node, time)
            return "new_state"
    else:
        # check for updates
        if event.actor.update(time):
            return 0

        is_syncing = event.actor.attempt_sync(event.time)
        if is_syncing:
            return "detected_desync"

        # try to change round
        Rounds.change_round(state.node, event.time)
        return "handled"


def schedule_timeout(state, time, add_time=True, fast_path=False):
    if fast_path:
        # set nodes fast_path attribute to True since fast path just started
        state.fast_path = True

        if add_time:
            time += float(Parameters.BigFoot["fast_path_timeout"])

        if (
            state.fast_path_timeout is not None
            and Parameters.simulation["debugging_mode"]
        ):
            state.node.queue.remove_event(state.fast_path_timeout)

        # schedule timeout
        payload = {
            "type": "fast_path_timeout",
            "round": state.rounds.round,
            "CP": state.NAME,
        }
        event = Scheduler.schedule_event(state.node, time, payload, state.handle_event)

        # keep a reference to the timeout
        state.fast_path_timeout = event
    else:
        if add_time:
            time += float(Parameters.BigFoot["timeout"])

        if state.timeout is not None and Parameters.simulation["debugging_mode"]:
            state.node.queue.remove_event(state.timeout)

        # schedule timeout
        payload = {"type": "timeout", "round": state.rounds.round, "CP": state.NAME}

        event = Scheduler.schedule_event(state.node, time, payload, state.handle_event)

        # keep a reference to the timeout
        state.timeout = event
