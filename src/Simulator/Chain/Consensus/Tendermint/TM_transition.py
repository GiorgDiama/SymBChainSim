from Parameters import Parameters

from Chain.Network import Network
from Chain.Consensus.Tendermint import TM_messages as messages

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TM_state import Tendermint
    from Engine.Event import Event

import logging

logger = logging.getLogger(__name__.split(".")[-1])


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
    logger.debug(f"[Node {state.node.id}] PROPOSE: Starting propose phase at time {time}, current state: {state.state}, round: {state.rounds.round}")

    # attempt to create block
    block, creation_time = state.create_TM_block(time)

    if block is None:
        when_next = 1

        # if there is still time in the round, attempt to reschedule later when txions might be there
        if creation_time + when_next + Parameters.execution["creation_time"] < state.timeout.time - 5:
            logger.debug(f"[Node {state.node.id}] PROPOSE: Scheduling retry at time {creation_time + when_next}")
            messages.schedule_propose(state, creation_time + when_next)
        else:
            logger.debug(f"[Node {state.node.id}] PROPOSE: No time left in round for retry")
    else:
        time = creation_time

        # block created, change state, and broadcast it.
        logger.debug(f"[Node {state.node.id}] PROPOSE: Block created successfully, transitioning from {state.state} to pre_prepared")
        state.state = "pre_prepared"
        state.block = block.copy()

        # create the votes extra_data field and log votes
        state.block.extra_data["votes"] = {
            "pre_prepare": [],
            "prepare": [],
            "commit": [],
        }

        state.block.extra_data["votes"]["pre_prepare"].append((event.creator.id, time, Network.size(event)))

        logger.debug(f"[Node {state.node.id}] PROPOSE: Broadcasting pre_prepare message")
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
    logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Processing pre_prepare from node {event.creator} for block {block.id} at time {time}, current state: {state.state}")

    # validate message: old (invalid), current (continue processing), future (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Message validation failed - invalid")
        return "invalid"
    if future is not None:
        logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Message is for future round - adding to backlog")
        return future

    time += Parameters.execution["msg_val_delay"]

    match state.state:
        # if node is a new round state (i.e waiting for a new block to be proposed)
        case "new_round":
            # validate block
            time += Parameters.execution["block_val_delay"]

            if (ret := state.validate_block(block, time)) != "valid":
                logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Block validation failed: {ret}")
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
            logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Block validation successful, transitioning from {state.state} to pre_prepared")
            state.state = "pre_prepared"

            # broadcast prepare message
            logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Broadcasting prepare message")
            messages.broadcast_prepare(state, time, state.block)

            # count own vote
            state.process_vote("prepare", state.node)

            state.block.extra_data["votes"]["prepare"].append((event.actor.id, time, Network.size(event)))

            return "new_state"  # state changed (will check backlog)

        case "pre_prepared":
            logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Node already in pre_prepared state")
            return "invalid"
        case "prepared":
            logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Node in prepared state")
            return "invalid"
        case "round_change":
            logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Node in round_change state")
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
    logger.debug(f"[Node {state.node.id}] PREPARE: Processing prepare vote from node {event.creator} for block {block.id if block else 'None'} at time {time}, current state: {state.state}")

    # validate message: old (invalid), current (continue processing), future (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        logger.debug(f"[Node {state.node.id}] PREPARE: Message validation failed - invalid")
        return "invalid"
    if future is not None:
        logger.debug(f"[Node {state.node.id}] PREPARE: Message is for future round, adding to backlog")
        return future
    time += Parameters.execution["msg_val_delay"]

    match state.state:
        case "pre_prepared":
            # count prepare vote
            logger.debug(f"[Node {state.node.id}] PREPARE: Processing prepare vote from node {event.creator}")
            state.process_vote("prepare", event.creator)

            state.block.extra_data["votes"]["prepare"].append((event.creator.id, time, Network.size(event)))

            # if we have enough prepare messages (2f messages since leader does not participate)
            current_votes = state.count_votes("prepare")
            logger.debug(f"[Node {state.node.id}] PREPARE: Current prepare votes: {current_votes}, required: {Parameters.application['required_messages'] - 1}")
            if state.count_votes("prepare") >= Parameters.application["required_messages"] - 1:
                # change to prepared
                logger.debug(f"[Node {state.node.id}] PREPARE: Sufficient prepare votes received, transitioning from {state.state} to prepared")
                state.state = "prepared"

                # broadcast commit message
                logger.debug(f"[Node {state.node.id}] PREPARE: Broadcasting commit message for block {block.id}")
                messages.broadcast_commit(state, time, block)

                # count own vote
                state.process_vote("commit", state.node)

                state.block.extra_data["votes"]["commit"].append((event.actor.id, time, Network.size(event)))

                return "new_state"

            # not enough votes yet...
            logger.debug(f"[Node {state.node.id}] PREPARE: Not enough prepare votes yet, waiting for more")
            return "handled"
        case "new_round":
            logger.debug(f"[Node {state.node.id}] PREPARE: Node in new_round state, adding to backlog")
            return "backlog"  # node has yet to receive enough pre_prepare messages
        case "prepared":
            logger.debug(f"[Node {state.node.id}] PREPARE: Node already in prepared state - invalid late message")
            return "invalid"  # node has already received enough prepared votes
        case "round_change":
            logger.debug(f"[Node {state.node.id}] PREPARE: Node in round_change state - invalid")
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

    # validate message: old (invalid), current (continue processing), future (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        logger.debug(f"[Node {state.node.id}] COMMIT: Message validation failed - invalid")
        return "invalid"
    if future is not None:
        logger.debug(f"[Node {state.node.id}] COMMIT: Message is for future round, adding to backlog")
        return future
    time += Parameters.execution["msg_val_delay"]

    match state.state:
        case "prepared":
            logger.debug(f"[Node {state.node.id}] COMMIT: Processing commit vote from node {event.creator}")
            state.process_vote("commit", event.creator)  # count vote
            state.block.extra_data["votes"]["commit"].append((event.creator.id, time, Network.size(event)))
            # if we have enough votes
            current_votes = state.count_votes("commit")
            logger.debug(f"[Node {state.node.id}] COMMIT: Current commit votes: {current_votes}, required: {Parameters.application['required_messages']}")
            if state.count_votes("commit") >= Parameters.application["required_messages"]:
                state.node.add_block(state.block, time)  # add block to BC

                if state.node.id == state.miner:
                    logger.debug(f"[Node {state.node.id}] COMMIT: As miner, broadcasting new block {state.block.id}")
                    messages.broadcast_new_block(state, time, state.block.copy())

                logger.debug(f"[Node {state.node.id}] COMMIT: Starting new round {state.rounds.round + 1}")
                state.start(time, state.rounds.round + 1)  # start new round
                return "new_state"
            logger.debug(f"[Node {state.node.id}] COMMIT: Not enough commit votes yet, waiting for more")
            return "handled"  # not enough votes yet...
        case "new_round":
            logger.debug(f"[Node {state.node.id}] COMMIT: Node in new_round state, adding to backlog")
            return "backlog"  # node is behind in votes... add to backlog
        case "pre_prepared":
            logger.debug(f"[Node {state.node.id}] COMMIT: Node in pre_prepared state, adding to backlog")
            return "backlog"  # node is behind in votes... add to backlog
        case "round_change":
            logger.debug(f"[Node {state.node.id}] COMMIT: Node in round_change state - invalid")
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
    logger.debug(f"[Node {state.node.id}] NEW_BLOCK: Processing new block {block.id} from node {event.creator} at {time}, depth: {block.depth}, local depth: {state.node.blockchain[-1].depth}")

    time += Parameters.execution["msg_val_delay"]
    time += Parameters.execution["block_val_delay"]

    if block.depth <= state.node.blockchain[-1].depth:
        logger.debug(f"[Node {state.node.id}] NEW_BLOCK: Block {block.id} is old (depth {block.depth} <= local {state.node.blockchain[-1].depth}) - ignoring")
        return "invalid"  # old block: ignore

    if block.depth > state.node.blockchain[-1].depth + 1:
        logger.debug(f"[Node {state.node.id}] NEW_BLOCK: Block {block.id} depth {block.depth} > local {state.node.blockchain[-1].depth} + 1, attempting sync with node {event.creator}")
        state.node.attempt_sync(time=time, sync_node=event.creator)
        return "detected_desync"

    logger.debug(f"[Node {state.node.id}] NEW_BLOCK: Adding block {block.id} to local blockchain and starting new round {event.payload['round'] + 1}")
    state.node.add_block(block.copy(), time)
    state.start(time, event.payload["round"] + 1)

    return "new_state"  # check backlog for any missed messages from early nodes
