"""
Helper functions for the creation of simulation events from protocol calls
for the BigFoot consensus state.
"""

from Engine.Scheduler import Scheduler

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Chain.Consensus.BigFoot.BigFoot_state import BigFoot
    from Chain.Block import Block


def schedule_propose(state: "BigFoot", time: float) -> None:
    """Schedule a local propose event for the given BigFoot state.

    Args:
        state (BigFoot): The BigFoot protocol state instance on the node.
        time (float): Simulation time at which to schedule the event.
    """
    payload = {"type": "propose", "round": state.rounds.round, "CP": state.NAME}

    Scheduler.schedule_event(state.node, time, payload, state.handle_event)


def broadcast_pre_prepare(state: "BigFoot", time: float, block: "Block") -> None:
    """Broadcast a pre-prepare message containing the proposed block.

    Args:
        state (BigFoot): The BigFoot protocol state instance on the node.
        time (float): Simulation time at which to broadcast the message.
        block (Block): The proposed block to pre-prepare.
    """
    payload = {
        "type": "pre_prepare",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)


def broadcast_prepare(state: "BigFoot", time: float, block: "Block") -> None:
    """Broadcast a prepare vote for a proposed block.

    Args:
        state (BigFoot): The BigFoot protocol state instance on the node.
        time (float): Simulation time at which to broadcast the message.
        block (Block): The block being prepared.
    """
    payload = {
        "type": "prepare",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)


def broadcast_commit(state: "BigFoot", time: float, block: "Block") -> None:
    """Broadcast a commit vote for a prepared block.

    Args:
        state (BigFoot): The BigFoot protocol state instance on the node.
        time (float): Simulation time at which to broadcast the message.
        block (Block): The block being committed.
    """
    payload = {
        "type": "commit",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }
    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)


def broadcast_new_block(state: "BigFoot", time: float, block: "Block") -> None:
    """Broadcast a message announcing a newly decided block.

    Args:
        state (BigFoot): The BigFoot protocol state instance on the node.
        time (float): Simulation time at which to broadcast the message.
        block (Block): The newly decided block.
    """
    payload = {
        "type": "new_block",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)
