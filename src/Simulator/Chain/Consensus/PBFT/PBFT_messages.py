"""
Helper functions for the creation of simulation events from protocol calls
"""

from Engine.Scheduler import Scheduler

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Chain.Consensus.PBFT.PBFT_state import PBFT
    from Chain.Block import Block


def schedule_propose(state: "PBFT", time: float) -> None:
    """
    Schedule a local propose event.

    Args:
        state (PBFT): The PBFT protocol state instance.
        time (float): Simulation time when the event should fire.

    Returns:
        None
    """
    payload = {
        "type": "propose",
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_event(state.node, time, payload, state.handle_event)


def broadcast_pre_prepare(state: "PBFT", time: float, block: "Block") -> None:
    """
    Broadcast a pre-prepare message with the proposed block.

    Args:
        state (PBFT): The PBFT protocol state instance.
        time (float): Simulation time when to broadcast.
        block (Block): The proposed block.

    Returns:
        None
    """
    payload = {
        "type": "pre_prepare",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)


def broadcast_prepare(state: "PBFT", time: float, block: "Block") -> None:
    """
    Broadcast a prepare message for a block.

    Args:
        state (PBFT): The PBFT protocol state instance.
        time (float): Simulation time when to broadcast.
        block (Block): The block being prepared.

    Returns:
        None
    """
    payload = {
        "type": "prepare",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)


def broadcast_commit(state: "PBFT", time: float, block: "Block") -> None:
    """
    Broadcast a commit message for a block.

    Args:
        state (PBFT): The PBFT protocol state instance.
        time (float): Simulation time when to broadcast.
        block (Block): The block being committed.

    Returns:
        None
    """
    payload = {
        "type": "commit",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)


def broadcast_new_block(state: "PBFT", time: float, block: "Block") -> None:
    """
    Broadcast a message announcing a newly decided block.

    Args:
        state (PBFT): The PBFT protocol state instance.
        time (float): Simulation time when to broadcast.
        block (Block): The newly decided block.

    Returns:
        None
    """
    payload = {
        "type": "new_block",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)
