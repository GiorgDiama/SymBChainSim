"""
Helper functions for the creation of simulation events from protocol calls
"""

from Engine.Scheduler import Scheduler

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Chain.Consensus.PBFT.PBFT_state import PBFT
    from Chain.Block import Block

def schedule_propose(state: "PBFT", time: float) -> None:
    payload = {
        "type": "propose",
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_event(state.node, time, payload, state.handle_event)


def broadcast_pre_prepare(state: "PBFT", time: float, block: Block) -> None:
    payload = {
        "type": "pre_prepare",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)


def broadcast_prepare(state: "PBFT", time: float, block: Block) -> None:
    payload = {
        "type": "prepare",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)


def broadcast_commit(state: "PBFT", time: float, block: Block) -> None:
    payload = {
        "type": "commit",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)


def broadcast_new_block(state: "PBFT", time: float, block: Block) -> None:
    payload = {
        "type": "new_block",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    Scheduler.schedule_broadcast_message(state.node, time, payload, state.handle_event)
