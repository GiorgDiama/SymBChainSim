from Parameters import Parameters

from Engine.Scheduler import Scheduler

from sys import getsizeof
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from Chain.Consensus.Tendermint.TM_state import Tendermint
    from Chain.Block import Block
    from Engine.Event import Event


def schedule_propose(state: "Tendermint", time: float) -> "Event":
    """Schedule a local propose event.

    Args:
        state (Tendermint): The Tendermint protocol state instance.
        time (float): Simulation time when the event should fire.

    Returns:
        Event: The scheduled event instance.
    """
    payload = {"type": "propose", "round": state.rounds.round, "CP": state.NAME}

    event = Scheduler.schedule_event(state.node, time, payload, state.handle_event)

    return event


def broadcast_pre_prepare(state: "Tendermint", time: float, block: "Block") -> "Event":
    """Broadcast a pre-prepare message with the proposed block.

    Args:
        state (Tendermint): The Tendermint protocol state instance.
        time (float): Simulation time when to broadcast.
        block (Block): The proposed block.

    Returns:
        Event: The scheduled broadcast event.
    """
    payload: dict[str, Any] = {
        "type": "pre_prepare",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    if Parameters.Tendermint["use_net_msg_size"]:
        payload["net_msg_size"] = get_payload_size(payload)

    event = Scheduler.schedule_broadcast_message(
        state.node, time, payload, state.handle_event
    )

    return event


def broadcast_prepare(state: "Tendermint", time: float, block_hash: int) -> "Event":
    """Broadcast a prepare vote for a block hash.

    Args:
        state (Tendermint): The Tendermint protocol state instance.
        time (float): Simulation time when to broadcast.
        block_hash (int): Hash/identifier of the block being prepared.

    Returns:
        Event: The scheduled broadcast event.
    """
    payload: dict[str, Any] = {
        "type": "prepare",
        "block_hash": block_hash,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    if Parameters.Tendermint["use_net_msg_size"]:
        payload["net_msg_size"] = get_payload_size(payload)

    event = Scheduler.schedule_broadcast_message(
        state.node, time, payload, state.handle_event
    )

    return event


def broadcast_commit(state: "Tendermint", time: float, block_hash: int) -> "Event":
    """Broadcast a commit vote for a block hash.

    Args:
        state (Tendermint): The Tendermint protocol state instance.
        time (float): Simulation time when to broadcast.
        block_hash (int): Hash/identifier of the block being committed.

    Returns:
        Event: The scheduled broadcast event.
    """
    payload: dict[str, Any] = {
        "type": "commit",
        "block_hash": block_hash,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    if Parameters.Tendermint["use_net_msg_size"]:
        payload["net_msg_size"] = get_payload_size(payload)

    event = Scheduler.schedule_broadcast_message(
        state.node, time, payload, state.handle_event
    )

    return event


def broadcast_new_block(state: "Tendermint", time: float, block: "Block") -> "Event":
    """Broadcast a message announcing a newly decided block.

    Args:
        state (Tendermint): The Tendermint protocol state instance.
        time (float): Simulation time when to broadcast.
        block (Block): The newly decided block.

    Returns:
        Event: The scheduled broadcast event.
    """
    payload: dict[str, Any] = {
        "type": "new_block",
        "block": block,
        "round": state.rounds.round,
        "CP": state.NAME,
    }

    if Parameters.Tendermint["use_net_msg_size"]:
        payload["net_msg_size"] = get_payload_size(payload)

    event = Scheduler.schedule_broadcast_message(
        state.node, time, payload, state.handle_event
    )

    return event


def get_payload_size(payload: dict[str, Any]) -> float:
    """Compute an approximate network payload size in MB for Tendermint messages.

    Args:
        payload (dict[str, Any]): The payload dictionary to estimate.

    Returns:
        float: Estimated size in megabytes.
    """
    size = Parameters.network["base_msg_size"]

    for key in payload:
        match key:
            case "block":
                size += (
                    payload[key].size + Parameters.Tendermint["base_block_size"] / 1e6
                )
            case "block_hash":
                size += Parameters.Tendermint["hash_size"] / 1e6
            case _:
                size += float(getsizeof(payload[key]) / 1e6)

    return size
