from Parameters import Parameters

from Chain.Consensus.BigFoot import BigFoot_messages

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from BigFoot_state import BigFoot
    from Engine.Event import Event

import logging

logger = logging.getLogger(__name__.split(".")[-1])


def propose(state: "BigFoot", event: "Event") -> str:
    """
    Handles the propose phase of BigFoot consensus.

    Attempts to create a new block and transitions the state to pre_prepared if successful.
    If no block can be created, schedules a retry for later in the round.

    Args:
        state (BigFoot): The BigFoot consensus state object.
        event (Event): The propose event containing timing information.

    Returns:
        str: "handled" indicating the event was processed successfully.
    """
    time = event.time
    logger.debug(f"[Node {state.node.id}] PROPOSE: Starting propose phase at time {time}, current state: {state.state}, round: {state.rounds.round}")

    # attempt to create block
    block, creation_time = state.create_BigFoot_block(time)

    if block is None:
        when_next = 1
        # if there is still time in the round, attempt to reschedule later when txions might be there
        if creation_time + when_next + Parameters.execution["creation_time"] <= state.timeout.time:
            logger.debug(f"[Node {state.node.id}] PROPOSE: Scheduling retry at time {creation_time + when_next}")
            BigFoot_messages.schedule_propose(state, creation_time + when_next)
        else:
            logger.debug(f"[Node {state.node.id}] PROPOSE: No time left in round for retry")

    else:
        # block created, change state, and broadcast it.
        state.state = "pre_prepared"
        state.block = block.copy()

        logger.debug(f"[Node {state.node.id}] PROPOSE: Broadcasting pre_prepare message")
        BigFoot_messages.broadcast_pre_prepare(state, time, block)

    return "handled"


def pre_prepare(state: "BigFoot", event: "Event") -> str:
    """
    Handles the pre_prepare phase of BigFoot consensus.

    Validates incoming pre_prepare messages and transitions the state accordingly.
    If the node is in new_round state, validates the block and broadcasts prepare messages.

    Args:
        state (BigFoot): The BigFoot consensus state object.
        event (Event): The pre_prepare event containing block and timing information.

    Returns:
        str: Status of message processing - "handled", "invalid", "backlog", "new_state", or error message.
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

            logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Block validation successful, transitioning from {state.state} to pre_prepared")

            # store block as current block
            state.block = event.payload["block"].copy()

            # change state to pre_prepared since block was accepted
            state.state = "pre_prepared"

            # broadcast prepare message
            logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Broadcasting prepare message")
            BigFoot_messages.broadcast_prepare(state, time, state.block)

            # count own vote
            state.process_vote("prepare", state.node, time)

            return "new_state"  # state changed (will check backlog)

        case "pre_prepared":
            logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Node already in pre_prepared state")
            return "invalid"
        case "prepared":
            logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Node in prepared state")
            return "invalid"  # as above
        case "round_change":
            logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Node in round_change state")
            return "invalid"  # node has decided to skip this round
        case _:
            logger.error(f"[Node {state.node.id}] PRE_PREPARE: Unexpected state: {state.state}")
            raise ValueError(f"Unexpected state '{state.state} for cp BigFoot...'")


def prepare(state: "BigFoot", event: "Event") -> str:
    """
    Handles the prepare phase of BigFoot consensus.

    Processes prepare votes and determines whether to transition to prepared state (slow path)
    or directly commit the block (fast path) based on vote counts.

    Args:
        state (BigFoot): The BigFoot consensus state object.
        event (Event): The prepare event containing block and timing information.

    Returns:
        str: Status of message processing - "handled", "invalid", "backlog", "new_state", or error message.
    """
    time = event.time
    block = event.payload["block"]
    round = state.rounds.round
    logger.debug(f"[Node {state.node.id}] PREPARE: Processing prepare vote from node {event.creator} for block {block.id} at time {time}, current state: {state.state}, fast_path: {state.fast_path}")

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
            state.process_vote("prepare", event.creator, time)
            current_votes = state.count_votes("prepare")

            logger.debug(f"[Node {state.node.id}] PREPARE: Current prepare votes: {current_votes}")

            if not state.fast_path:
                # -----------------------------------------------------------
                #                      SLOW PATH/RECOVERY
                # -----------------------------------------------------------
                logger.debug(f"[Node {state.node.id}] PREPARE: Using SLOW PATH, required votes: {Parameters.application['required_messages'] - 1}")
                # leader does not issue a prepare message (thus 2f required votes)
                if state.count_votes("prepare") >= Parameters.application["required_messages"] - 1:
                    # change to prepared
                    logger.debug(f"[Node {state.node.id}] PREPARE: Sufficient prepare votes received, transitioning from {state.state} to prepared")
                    state.state = "prepared"
                    # broadcast commit message
                    logger.debug(f"[Node {state.node.id}] PREPARE: Broadcasting commit message for block {block.id}")
                    BigFoot_messages.broadcast_commit(state, time, block)
                    # count own vote
                    state.process_vote("commit", state.node, time)
                    return "new_state"
                logger.debug(f"[Node {state.node.id}] PREPARE: Not enough prepare votes yet, waiting for more")
                return "handled"
            else:
                # -----------------------------------------------------------
                #                      FAST PATH
                # -----------------------------------------------------------
                logger.debug(f"[Node {state.node.id}] PREPARE: Using FAST PATH, required votes: {Parameters.application['Nn'] - 1}")
                if state.count_votes("prepare") == Parameters.application["Nn"] - 1:
                    logger.debug(f"[Node {state.node.id}] PREPARE: Fast path successful! Adding block {block.id} to blockchain")
                    state.node.add_block(state.block, time)

                    glob_chain = Parameters.simulation["blockchain"] = Parameters.simulation.get("blockchain", dict())
                    if block.id not in glob_chain:
                        glob_chain[block.id] = state.block.copy()

                    if state.node.id == state.miner:
                        logger.debug(f"[Node {state.node.id}] PREPARE: As miner, broadcasting new block {block.id}")
                        BigFoot_messages.broadcast_new_block(state, time, state.block)

                    logger.debug(f"[Node {state.node.id}] PREPARE: Starting new round {state.rounds.round + 1}")
                    state.start(time, state.rounds.round + 1)

                    return "new_state"

                # not enough votes
                logger.debug(f"[Node {state.node.id}] PREPARE: Not enough prepare votes for fast path yet, waiting for more")
                return "handled"
        case "new_round":
            logger.debug(f"[Node {state.node.id}] PREPARE: Node in new_round state, adding to backlog")
            return "backlog"  # node has yet to receive enough pre_prepare messages
        case "prepared":
            logger.debug(f"[Node {state.node.id}] PREPARE: Node already in prepared state - invalid late message")
            return "invalid"  # node has allready received enough prepared votes
        case "round_change":
            logger.debug(f"[Node {state.node.id}] PREPARE: Node in round_change state - invalid")
            return "invalid"  # node has decided to skip this round
        case _:
            raise ValueError(f"Unexpected state '{state.state} for cp BigFoot...'")


def commit(state: "BigFoot", event: "Event") -> str:
    """
    Handles the commit phase of BigFoot consensus.

    Processes commit votes and finalizes the block when sufficient votes are received.
    Adds the block to the local blockchain and starts a new round.

    Args:
        state (BigFoot): The BigFoot consensus state object.
        event (Event): The commit event containing block and timing information.

    Returns:
        str: Status of message processing - "handled", "invalid", "backlog", "new_state", or error message.
    """
    time = event.time
    block = event.payload["block"]
    round = state.rounds.round
    logger.debug(f"[Node {state.node.id}] COMMIT: Processing commit vote from node {event.creator} for block {block.id} at time {time}, current state: {state.state}")

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
            # count vote
            logger.debug(f"[Node {state.node.id}] COMMIT: Processing commit vote from node {event.creator}")
            state.process_vote("commit", event.creator, time)
            current_votes = state.count_votes("commit")
            logger.debug(f"[Node {state.node.id}] COMMIT: Current commit votes: {current_votes}, required: {Parameters.application['required_messages']}")

            # if we have enough votes
            if state.count_votes("commit") >= Parameters.application["required_messages"]:
                # add block to local BC
                logger.debug(f"[Node {state.node.id}] COMMIT: Sufficient commit votes received! Adding block {block.id} to blockchain")
                state.node.add_block(state.block, time)

                glob_chain = Parameters.simulation["blockchain"] = Parameters.simulation.get("blockchain", dict())
                if block.id not in glob_chain:
                    glob_chain[block.id] = state.block.copy()

                # if miner: broadcast new block to nodes
                if state.node.id == state.miner:
                    logger.debug(f"[Node {state.node.id}] COMMIT: As miner, broadcasting new block {block.id}")
                    BigFoot_messages.broadcast_new_block(state, time, state.block)

                # start new round
                logger.debug(f"[Node {state.node.id}] COMMIT: Starting new round {state.rounds.round + 1}")
                state.start(time, state.rounds.round + 1)

                return "new_state"
            # not enough votes yet...
            logger.debug(f"[Node {state.node.id}] COMMIT: Not enough commit votes yet, waiting for more")
            return "handled"
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
            raise ValueError(f"Unexpected state '{state.state} for cp BigFoot...'")


def new_block(state: "BigFoot", event: "Event") -> str:
    """Handles new block events in BigFoot consensus.

    Processes incoming new block announcements, validates them, and updates the local state.
    Handles synchronization when blocks are missing from the chain.

    Args:
        state (BigFoot): The BigFoot consensus state object.
        event (Event): The new_block event containing block and timing information.

    Returns:
        str: Status of block processing - "invalid", "detected_desync", "new_state", or error message.
    """
    block = event.payload["block"]
    time = event.time
    logger.debug(
        f"[Node {state.node.id}] NEW_BLOCK: Processing new block {block.id} from node {event.creator} at time {time}, block depth: {block.depth}, local chain depth: {state.node.blockchain[-1].depth}"
    )

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
