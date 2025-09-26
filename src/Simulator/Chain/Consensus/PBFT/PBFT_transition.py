from Parameters import Parameters

from Chain.Network import Network
from Chain.Consensus.PBFT import PBFT_messages

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Chain.Consensus.PBFT.PBFT_state import PBFT
    from Engine.Event import Event

import logging

logger = logging.getLogger(__name__.split(".")[-1])


def propose(state: "PBFT", event: "Event") -> str:
    """Handle the propose phase of the PBFT consensus protocol.

    This function attempts to create a new block. If successful, it changes the state to
    'pre_prepared' and broadcasts the block. If unsuccessful, it may reschedule another
    attempt if there's time remaining in the round.

    Args:
        state: The current PBFT state object containing consensus state information
        event: The propose event being processed

    Returns:
        str: Indicates the outcome of the event
    """
    time = event.time
    logger.debug(
        f"[Node {state.node.id}] PROPOSE: Starting propose phase at time {time}, current state: {state.state}, round: {state.rounds.round}"
    )

    # attempt to create block
    block, creation_time = state.create_PBFT_block(time)

    if block is None:
        when_next = 1
        # if there is still time in the round, attempt to reschedule later when
        # txions might be generated
        if (
            creation_time + when_next + Parameters.execution["creation_time"]
            <= state.timeout.time
        ):
            logger.debug(
                f"[Node {state.node.id}] PROPOSE: Scheduling retry at time {creation_time + when_next}"
            )
            PBFT_messages.schedule_propose(state, creation_time + when_next)
        else:
            logger.debug(
                f"[Node {state.node.id}] PROPOSE: No time left in round for retry"
            )
        return "no transactions - rescheduled"
    else:
        # block created, change state, and broadcast it.
        logger.debug(
            f"[Node {state.node.id}] PROPOSE: Block created successfully, transitioning from {state.state} to pre_prepared"
        )
        state.state = "pre_prepared"
        state.block = block.copy()

        # create the extra_data field and log votes
        state.block.extra_data["votes"] = {
            "pre_prepare": [],
            "prepare": [],
            "commit": [],
        }

        state.block.extra_data["votes"]["pre_prepare"].append(
            (event.creator.id, time, Network.size(event))
        )

        logger.debug(
            f"[Node {state.node.id}] PROPOSE: Broadcasting pre_prepare message"
        )

        PBFT_messages.broadcast_pre_prepare(state, time, block)
        return "proposed block"


def pre_prepare(state: "PBFT", event: "Event") -> str:
    """Handle the pre-prepare phase of the PBFT consensus protocol.

    This function validates and processes a pre-prepare message. If in 'new_round' state and
    the block is valid, it transitions to 'pre_prepared' state and broadcasts prepare messages.

    Args:
        state: The current PBFT state object containing consensus state information
        event: The pre-prepare event being processed

    Returns:
       str: Status of the message processing:
            - "invalid": Message was invalid
            - "new_state": State changed, should check backlog
    """
    time = event.time
    block = event.payload["block"]
    logger.debug(
        f"[Node {state.node.id}] PRE_PREPARE: Processing pre_prepare from node {event.creator} for block {block.id} at time {time}, current state: {state.state}"
    )

    # validate message: old (invalid), current (continue processing), future
    # (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        logger.debug(
            f"[Node {state.node.id}] PRE_PREPARE: Message validation failed - invalid"
        )
        return "invalid"
    if future is not None:
        logger.debug(
            f"[Node {state.node.id}] PRE_PREPARE: Message is for future round - adding to backlog"
        )
        return future

    time += Parameters.execution["msg_val_delay"]

    match state.state:
        # if node is a new round state (i.e waiting for a new block to be
        # proposed)
        case "new_round":
            # validate block
            time += Parameters.execution["block_val_delay"]
            if (ret := state.validate_block(block, time)) != "valid":
                logger.debug(
                    f"[Node {state.node.id}] PRE_PREPARE: Block validation failed: {ret}"
                )
                return ret

            logger.debug(
                f"[Node {state.node.id}] PRE_PREPARE: Block validation successful, transitioning from {state.state} to pre_prepared"
            )
            # store block as current block
            state.block = event.payload["block"].copy()

            # create the votes extra_data field and log votes
            state.block.extra_data["votes"] = {
                "pre_prepare": [],
                "prepare": [],
                "commit": [],
            }

            state.block.extra_data["votes"]["pre_prepare"].append(
                (event.creator.id, time, Network.size(event))
            )

            # change state to pre_prepared since block was accepted
            state.state = "pre_prepared"

            # broadcast prepare message
            logger.debug(
                f"[Node {state.node.id}] PRE_PREPARE: Broadcasting prepare message"
            )
            PBFT_messages.broadcast_prepare(state, time, state.block)

            # count own vote
            state.process_vote("prepare", state.node)

            state.block.extra_data["votes"]["prepare"].append(
                (event.actor.id, time, Network.size(event))
            )

            return "new_state"  # state changed (will check backlog)

        case "pre_prepared":
            logger.debug(
                f"[Node {state.node.id}] PRE_PREPARE: Node already in pre_prepared state"
            )
            return "invalid"
        case "prepared":
            logger.debug(f"[Node {state.node.id}] PRE_PREPARE: Node in prepared state")
            return "invalid"
        case "round_change":
            logger.debug(
                f"[Node {state.node.id}] PRE_PREPARE: Node in round_change state"
            )
            return "invalid"  # node has decided to skip this round
        case _:
            logger.error(
                f"[Node {state.node.id}] PRE_PREPARE: Unexpected state: {state.state}"
            )
            raise ValueError(f"Unexpected state '{state.state} for cp PBFT...'")


def prepare(state: "PBFT", event: "Event") -> str:
    """Handle the prepare phase of the PBFT consensus protocol.

    This function processes prepare messages, counts votes, and transitions to 'prepared' state
    when enough prepare messages are received.

    Args:
        state: The current PBFT state object containing consensus state information
        event: The prepare event being processed

    Returns:
        str: Status of the message processing:
            - "invalid": Message was invalid
            - "new_state": State changed, should check backlog
            - "handled": Message was processed successfully
            - "backlog": Message should be added to backlog
    """
    time = event.time
    block = event.payload["block"]
    round = state.rounds.round
    logger.debug(
        f"[Node {state.node.id}] PREPARE: Processing prepare vote from node {event.creator} for block {block.id} at time {time}, current state: {state.state}"
    )

    # validate message: old (invalid), current (continue processing), future
    # (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        logger.debug(
            f"[Node {state.node.id}] PREPARE: Message validation failed - invalid"
        )
        return "invalid"
    if future is not None:
        logger.debug(
            f"[Node {state.node.id}] PREPARE: Message is for future round, adding to backlog"
        )
        return future

    time += Parameters.execution["msg_val_delay"]

    match state.state:
        case "pre_prepared":
            # count prepare vote
            logger.debug(
                f"[Node {state.node.id}] PREPARE: Processing prepare vote from node {event.creator}"
            )
            state.process_vote("prepare", event.creator)

            state.block.extra_data["votes"]["prepare"].append(
                (event.creator.id, time, Network.size(event))
            )

            current_votes = state.count_votes("prepare")
            logger.debug(
                f"[Node {state.node.id}] PREPARE: Current prepare votes: {current_votes}, required: {Parameters.application['required_messages'] - 1}"
            )

            # if we have enough prepare messages (2f messages since leader does
            # not participate)
            if (
                state.count_votes("prepare")
                >= Parameters.application["required_messages"] - 1
            ):
                # change to prepared
                logger.debug(
                    f"[Node {state.node.id}] PREPARE: Sufficient prepare votes received, transitioning from {state.state} to prepared"
                )
                state.state = "prepared"

                # broadcast commit message
                logger.debug(
                    f"[Node {state.node.id}] PREPARE: Broadcasting commit message for block {block.id}"
                )
                PBFT_messages.broadcast_commit(state, time, block)

                # count own vote
                state.process_vote("commit", state.node)

                state.block.extra_data["votes"]["commit"].append(
                    (event.actor.id, time, Network.size(event))
                )

                return "new_state"

            # not enough votes yet...
            logger.debug(
                f"[Node {state.node.id}] PREPARE: Not enough prepare votes yet, waiting for more"
            )
            return "handled"
        case "new_round":
            logger.debug(
                f"[Node {state.node.id}] PREPARE: Node in new_round state, adding to backlog"
            )
            return "backlog"  # node has yet to receive enough pre_prepare messages
        case "prepared":
            logger.debug(
                f"[Node {state.node.id}] PREPARE: Node already in prepared state - invalid late message"
            )
            return "invalid"  # node has already received enough prepared votes
        case "round_change":
            logger.debug(
                f"[Node {state.node.id}] PREPARE: Node in round_change state - invalid"
            )
            return "invalid"  # node has decided to skip this round
        case _:
            logger.error(
                f"[Node {state.node.id}] PREPARE: Unexpected state: {state.state}"
            )
            raise ValueError(f"Unexpected state '{state.state} for cp PBFT...'")


def commit(state: "PBFT", event: "Event") -> str:
    """Handle the commit phase of the PBFT consensus protocol.

    This function processes commit messages, counts votes, and finalizes block addition when
    enough commit messages are received.

    Args:
        state: The current PBFT state object containing consensus state information
        event: The commit event being processed

    Returns:
        str: Status of the message processing:
            - "invalid": Message was invalid
            - "new_state": State changed, should check backlog
            - "handled": Message was processed successfully
            - "backlog": Message should be added to backlog
    """
    time = event.time
    block = event.payload["block"]
    logger.debug(
        f"[Node {state.node.id}] COMMIT: Processing commit vote from node {event.creator} for block {block.id} at time {time}, current state: {state.state}"
    )

    # validate message: old (invalid), current (continue processing), future
    # (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        logger.debug(
            f"[Node {state.node.id}] COMMIT: Message validation failed - invalid"
        )
        return "invalid"
    if future is not None:
        logger.debug(
            f"[Node {state.node.id}] COMMIT: Message is for future round, adding to backlog"
        )
        return future
    time += Parameters.execution["msg_val_delay"]

    match state.state:
        case "prepared":
            # count vote
            logger.debug(
                f"[Node {state.node.id}] COMMIT: Processing commit vote from node {event.creator}"
            )
            state.process_vote("commit", event.creator)
            state.block.extra_data["votes"]["commit"].append(
                (event.creator.id, time, Network.size(event))
            )

            current_votes = state.count_votes("commit")
            logger.debug(
                f"[Node {state.node.id}] COMMIT: Current commit votes: {current_votes}, required: {Parameters.application['required_messages']}"
            )

            # if we have enough votes
            if (
                state.count_votes("commit")
                >= Parameters.application["required_messages"]
            ):
                # add block to local blockchain
                logger.debug(
                    f"[Node {state.node.id}] COMMIT: Sufficient commit votes received! Adding block {block.id} to blockchain"
                )
                state.node.add_block(state.block, time)

                Parameters.simulation["blockchain"] = Parameters.simulation.get(
                    "blockchain", dict()
                )
                if block.id not in Parameters.simulation["blockchain"]:
                    Parameters.simulation["blockchain"][block.id] = state.block.copy()
                # if this node is the miner: broadcast the block to the nodes
                if state.node.id == state.miner:
                    logger.debug(
                        f"[Node {state.node.id}] COMMIT: As miner, broadcasting new block {block.id}"
                    )
                    PBFT_messages.broadcast_new_block(state, time, state.block)

                # start new round
                logger.debug(
                    f"[Node {state.node.id}] COMMIT: Starting new round {state.rounds.round + 1}"
                )
                state.start(time, state.rounds.round + 1)

                return "new_state"

            # not enough votes yet...
            logger.debug(
                f"[Node {state.node.id}] COMMIT: Not enough commit votes yet, waiting for more"
            )
            return "handled"
        case "new_round":
            logger.debug(
                f"[Node {state.node.id}] COMMIT: Node in new_round state, adding to backlog"
            )
            return "backlog"  # node is behind in votes... add to backlog
        case "pre_prepared":
            logger.debug(
                f"[Node {state.node.id}] COMMIT: Node in pre_prepared state, adding to backlog"
            )
            return "backlog"  # node is behind in votes... add to backlog
        case "round_change":
            logger.debug(
                f"[Node {state.node.id}] COMMIT: Node in round_change state - invalid"
            )
            return "invalid"  # node has decided to skip this round
        case _:
            logger.error(
                f"[Node {state.node.id}] COMMIT: Unexpected state: {state.state}"
            )
            raise ValueError(f"Unexpected state '{state.state} for cp PBFT...'")


def new_block(state: "PBFT", event: "Event") -> str:
    """Handle the reception of a new block in the PBFT consensus protocol.

    This function processes new block messages, validates them, and updates the local blockchain
    accordingly. It also handles potential desynchronization scenarios.

    Args:
        state: The current PBFT state object containing consensus state information
        event: The new block event being processed

    Returns:
        str: Status of the block processing:
            - "invalid": Block was invalid (old)
            - "new_state": State changed, should check backlog
            - "detected_desync": Node is out of sync and needs synchronization
    """
    block = event.payload["block"]
    time = event.time
    logger.debug(
        f"[Node {state.node.id}] NEW_BLOCK: Processing new block {block.id} from node {event.creator} at time {time}, block depth: {block.depth}, local chain depth: {state.node.blockchain[-1].depth}"
    )

    time += Parameters.execution["msg_val_delay"]
    time += Parameters.execution["block_val_delay"]

    if block.depth <= state.node.blockchain[-1].depth:
        logger.debug(
            f"[Node {state.node.id}] NEW_BLOCK: Block {block.id} is old (depth {block.depth} <= local {state.node.blockchain[-1].depth}) - ignoring"
        )
        return "invalid"  # old block: ignore

    if block.depth > state.node.blockchain[-1].depth + 1:
        logger.debug(
            f"[Node {state.node.id}] NEW_BLOCK: Block {block.id} depth {block.depth} > local {state.node.blockchain[-1].depth} + 1, attempting sync with node {event.creator}"
        )
        state.node.attempt_sync(time=time, sync_node=event.creator)
        return "detected_desync"

    logger.debug(
        f"[Node {state.node.id}] NEW_BLOCK: Adding block {block.id} to local blockchain and starting new round {block.extra_data['round'] + 1}"
    )
    state.node.add_block(block.copy(), time)
    state.start(time, block.extra_data["round"] + 1)

    # we are now in a new round - check the backlog for any missed round
    # messages from early nodes
    return "new_state"
