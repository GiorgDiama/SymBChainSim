from Chain.Network import Network

from Engine.Event import MessageEvent, Event

from Utils import Tools

import bisect
import typing

if typing.TYPE_CHECKING:
    from Chain.Node import Node

import logging

logger = logging.getLogger(__name__.split(".")[-1])


def handle_event(event: Event, checking_backlog: bool = False) -> str:
    """
    Handles an event in the SymBChainSim system, managing general logic and delegating
    to event-specific handlers. It also processes the backlog when an event causes
    a node to transition to a new state.
    Args:
        event (Event): The event to be handled. Contains details about the action
            and the actor involved.
        checking_backlog (bool, optional): Indicates whether the function is being
            called as part of backlog processing. Defaults to False.
    Returns:
        str: The outcome of the event handling. Possible values include:
            - 'handled':     Event was processed successfully without significant state updates.
            - 'new_state':   Event caused a node state change, triggering backlog processing.
            - 'invalid':     Event is invalid (e.g., outdated or irrelevant).
            - 'unhandled':   Event could not be processed (raises an error).
            - 'backlog':     Event is a future message and is added to the backlog.
            - 'dead_node':   Event actor is not alive.
    Raises:
        RuntimeError: If the event is marked as 'unhandled' by its specific handler.
    Notes:
        - Events that do not change the state of a node significantly return 'handled',
          avoiding unnecessary backlog checks.
        - If the event is a `MessageEvent`, it interacts with the network layer to
          determine whether it should be processed further.
        - Backlog processing is triggered only when an event results in a 'new_state'.
    """

    if not event.actor.state.alive:
        logger.debug(f"[Node: {event.actor.id}] is offline - skipping exectuion")
        return "dead_node"

    # if this event is CP specific and the CP of the event does not match the
    # current CP of the node - old/old message
    if "CP" in event.payload and (event.actor.cp is not None and event.payload["CP"] != event.actor.cp.NAME):
        logger.debug(f"[Node: {event.actor.id}] uses {event.actor.cp.NAME} but event is for protocol {event.payload['CP']}...")
        return "invalid"

    if not checking_backlog and isinstance(event, MessageEvent):
        network_rcv_result = Network.on_receive(event.actor, event)
        if network_rcv_result != "process":
            return network_rcv_result

    ret = event.handler(event)

    if ret == "backlog" and not checking_backlog:
        bisect.insort(event.actor.backlog, event)
    elif ret == "new_state" and not checking_backlog:
        handle_backlog(event.actor, event.time)
    elif ret == "unhandled":
        raise RuntimeError(f"Event: '{event}' - was not handled by its own handler...")

    return ret


def handle_backlog(node: "Node", call_time: float) -> None:
    """
    Handles events in the backlog of a given node.
    This function iterates through the backlog of a node and attempts to handle each event.
    Events that are successfully handled, result in a new state, or are deemed invalid
    are removed from the backlog.
    Args:
        node (Node): The node whose backlog is being processed.
        call_time (float): The timestamp at which the backlog handling is initiated.
                           This ensures events are replayed at the correct time.
    Behavior:
        - Each event in the backlog is processed by the `handle_event` function.
        - Events successfully handled (returning 'handled', 'new_state', or 'invalid')
          are marked for removal.
        - The backlog is updated to exclude events that have been handled.
    Notes:
        - The function ensures that events already removed from the backlog during
          processing are not removed again, preventing potential errors.
    """

    remove_list = []

    for event in node.backlog:
        event.time = call_time  # ensure the message is replayed at call_time

        logger.debug(f"BACKLOG CHECK: {event.payload['type']} creator:{'' if event.creator is None else event.creator.id} actor:{'' if event.actor is None else event.actor.id} time:{event.time}")

        Tools.debug_logs(
            msg=f"",
            input=f"HANDLING BACKLOG: {event} ",
            in_col="43",
            clear=False,
        )

        ret = handle_event(event, checking_backlog=True)

        if ret == "handled" or ret == "new_state" or ret == "invalid":
            logger.debug("BACKLOG STATUS: Event processed!")
            remove_list.append(event)
        else:
            logger.debug("BACKLOG STATUS: not time for this yet...")

    # some events may clear the backlog - this prevents trying to remove
    # already removed events
    if node.backlog:
        node.backlog = [e for e in node.backlog if e not in remove_list]
