from Parameters import Parameters

from Chain.Network import Network
from Chain.Consensus.Tendermint import TM_messages as messages

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TM_state import Tendermint
    from Engine.Event import Event


def propose(state: "Tendermint", event: "Event") -> str:
    """
    Handles the proposal phase in the Tendermint consensus protocol.
    Attempts to create a new block. If successful, broadcasts a pre-prepare message and updates state.
    If not, reschedules the proposal if there is still time in the round.

    Args:
        state (Tendermint): The current protocol state for the node.
        event (Event): The event triggering the proposal.

    Returns:
        str: 'handled' if the event was processed.
    """
    time = event.time

    # attempt to create block
    block, creation_time = state.create_TM_block(time)

    if block is None:
        when_next = 1

        # if there is still time in the round, attempt to reschedule later when
        # txions might be there
        if creation_time + when_next + Parameters.execution["creation_time"] < state.timeout.time - 5:
            messages.schedule_propose(state, creation_time + when_next)
    else:
        time = creation_time

        # block created, change state, and broadcast it.
        state.state = "pre_prepared"
        state.block = block.copy()

        # create the votes extra_data field and log votes
        state.block.extra_data["votes"] = {
            "pre_prepare": [],
            "prepare": [],
            "commit": [],
        }

        state.block.extra_data["votes"]["pre_prepare"].append((event.creator.id, time, Network.size(event)))

        messages.broadcast_pre_prepare(state, time, block)

    return "handled"


def pre_prepare(state: "Tendermint", event: "Event") -> str:
    """
    Handles the pre-prepare phase in the Tendermint consensus protocol.
    Validates the block and message, updates state, and broadcasts prepare if valid.

    Args:
        state (Tendermint): The current protocol state for the node.
        event (Event): The event containing the pre-prepare message and block.

    Returns:
        str: Result of processing ('new_state', 'invalid', 'backlog', or future event).
    """
    time = event.time
    block = event.payload["block"]

    # validate message: old (invalid), current (continue processing), future
    # (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        return "invalid"
    if future is not None:
        return future

    time += Parameters.execution["msg_val_delay"]

    match state.state:
        # if node is a new round state (i.e waiting for a new block to be
        # proposed)
        case "new_round":
            # validate block
            time += Parameters.execution["block_val_delay"]

            if (ret := state.validate_block(block, time)) != "valid":
                return ret

            # store block as current block
            state.block = event.payload["block"].copy()

            # create the votes extra_data field and log votes
            state.block.extra_data["votes"] = {
                "pre_prepare": [],
                "prepare": [],
                "commit": [],
            }

            state.block.extra_data["votes"]["pre_prepare"].append((event.creator.id, time, Network.size(event)))

            # change state to pre_prepared since block was accepted
            state.state = "pre_prepared"

            # broadcast prepare message
            messages.broadcast_prepare(state, time, state.block)

            # count own vote
            state.process_vote("prepare", state.node)

            state.block.extra_data["votes"]["prepare"].append((event.actor.id, time, Network.size(event)))

            return "new_state"  # state changed (will check backlog)

        case "pre_prepared":
            return "invalid"
        case "prepared":
            return "invalid"
        case "round_change":
            return "invalid"  # node has decided to skip this round
        case _:
            raise ValueError(f"Unexpected state '{state.state} for cp TM...'")


def prepare(state: "Tendermint", event: "Event") -> str:
    """
    Handles the prepare phase in the Tendermint consensus protocol.
    Processes prepare votes, updates state, and broadcasts commit if enough votes are collected.

    Args:
        state (Tendermint): The current protocol state for the node.
        event (Event): The event containing the prepare message.

    Returns:
        str: Result of processing ('new_state', 'handled', 'invalid', 'backlog').
    """
    time = event.time
    block = state.block
    round = state.rounds.round

    # validate message: old (invalid), current (continue processing), future
    # (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        return "invalid"
    if future is not None:
        return future
    time += Parameters.execution["msg_val_delay"]

    match state.state:
        case "pre_prepared":
            # count prepare vote
            state.process_vote("prepare", event.creator)

            state.block.extra_data["votes"]["prepare"].append((event.creator.id, time, Network.size(event)))

            # if we have enough prepare messages (2f messages since leader does
            # not participate)
            if state.count_votes("prepare") >= Parameters.application["required_messages"] - 1:
                # change to prepared
                state.state = "prepared"

                # broadcast commit message
                messages.broadcast_commit(state, time, block)

                # count own vote
                state.process_vote("commit", state.node)

                state.block.extra_data["votes"]["commit"].append((event.actor.id, time, Network.size(event)))

                return "new_state"
            # not enough votes yet...
            return "handled"
        case "new_round":
            return "backlog"  # node has yet to receive enough pre_prepare messages
        case "prepared":
            return "invalid"  # node has already received enough prepared votes
        case "round_change":
            return "invalid"  # node has decided to skip this round
        case _:
            raise ValueError(f"Unexpected state '{state.state} for cp TM...'")


def commit(state: "Tendermint", event: "Event") -> str:
    """
    Handles the commit phase in the Tendermint consensus protocol.
    Processes commit votes, adds the block to the blockchain if enough votes are collected, and starts a new round.

    Args:
        state (Tendermint): The current protocol state for the node.
        event (Event): The event containing the commit message.

    Returns:
        str: Result of processing ('new_state', 'handled', 'invalid', 'backlog').
    """
    time = event.time
    block = state.block
    round = state.rounds.round

    # validate message: old (invalid), current (continue processing), future
    # (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        return "invalid"
    if future is not None:
        return future
    time += Parameters.execution["msg_val_delay"]

    match state.state:
        case "prepared":
            state.process_vote("commit", event.creator)  # count vote
            state.block.extra_data["votes"]["commit"].append((event.creator.id, time, Network.size(event)))
            # if we have enough votes
            if state.count_votes("commit") >= Parameters.application["required_messages"]:
                state.node.add_block(state.block, time)  # add block to BC

                if state.node.id == state.miner:
                    messages.broadcast_new_block(state, time, state.block.copy())

                state.start(time, state.rounds.round + 1)  # start new round
                return "new_state"
            return "handled"  # not enough votes yet...
        case "new_round":
            return "backlog"  # node is behind in votes... add to backlog
        case "pre_prepared":
            return "backlog"  # node is behind in votes... add to backlog
        case "round_change":
            return "invalid"  # node has decided to skip this round
        case _:
            raise ValueError(f"Unexpected state '{state.state} for cp TM...'")


def new_block(state: "Tendermint", event: "Event") -> str:
    """
    Handles the reception of a new block in the Tendermint consensus protocol.
    Validates the block's depth, attempts to synchronize if desynced, and starts a new round if valid.

    Args:
        state (Tendermint): The current protocol state for the node.
        event (Event): The event containing the new block.

    Returns:
        str: Result of processing ('new_state', 'invalid', 'detected_desync').
    """
    block = event.payload["block"]
    time = event.time

    time += Parameters.execution["msg_val_delay"]
    time += Parameters.execution["block_val_delay"]

    if block.depth <= state.node.blockchain[-1].depth:
        return "invalid"  # old block: ignore

    if block.depth > state.node.blockchain[-1].depth + 1:
        state.node.attempt_sync(time=time, sync_node=event.creator)
        return "detected_desync"

    state.node.add_block(block.copy(), time)
    state.start(time, event.payload["round"] + 1)

    return "new_state"  # check backlog for any missed messages from early nodes
