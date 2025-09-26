"""
Models a high-level sync functionality. Calculates how long it would take for the node to receive the data
(missing blocks) and creates a local event which copies the missing blocks to the de-synced node saving communication
events
"""

from Parameters import Parameters

from Chain.Network import Network

from Engine.Scheduler import Scheduler
from Engine.Event import Event

from typing import Optional, TYPE_CHECKING

from random import sample

if TYPE_CHECKING:
    from ..Node import Node

import logging

logger = logging.getLogger(__name__.split(".")[-1])


class SyncingState:
    """
    Node state for de-synced nodes
    """

    NAME = "DESYNC"

    def __init__(self, node) -> None:
        self.node: "Node" = node
        self.state: str = "desynced"
        self.local_fast_sync_event_data: Optional[Event] = None
        self.local_fast_sync_event_configuration: Optional[Event] = None

    def state_to_string(self):
        return f"SYNCING STATE: data_chain_event={
            self.local_fast_sync_event_data
        } configuration_chain_event={self.local_fast_sync_event_configuration}"

    def ready_to_rejoin(self):
        return (
            self.local_fast_sync_event_configuration is None
            and self.local_fast_sync_event_data is None
        )


def handler(event: Event) -> str:
    """
    Calls the appropriate method to handle events produced by the HighLevelSync module.

    Returns:
        A string briefly describing the event execution
    """
    if event.payload["type"] == "local_fast_sync":
        return handle_local_sync_event(event)
    elif event.payload["type"] == "local_fast_sync_configuration":
        return handle_local_sync_event_configuration(event)
    else:
        return "unhandled"


def create_local_sync_event(
    desynced_node: "Node", request_node: "Node", time: float
) -> None:
    """
    Gets missing blocks from request node
    Request node: node from which we request missing blocks
        examples:
            - the node whose message made us aware that we are de-synced
            - the peer with the longest chain)
    Calculates transmission + validation delay and creates a local sync event
    (local event of the desynced node) at the moment in time when the sync
    processes would have finished
    """
    logger.debug(
        f"Node {desynced_node.id} is requesting a BLOCKCHAIN sync from Node {request_node.id}..."
    )
    # get the last block of de-synced node
    latest_block = desynced_node.last_block

    # find missing blocks in blockchain of request_node
    missing_blocks = []
    for b in reversed(request_node.blockchain):
        if b.depth > latest_block.depth:
            # TODO: Insert is o(n) ... append o(1) and reverse
            missing_blocks.insert(0, b.copy())
        else:
            break

    # take into account a static delay for sending the sync message
    total_delay = Parameters.execution["sync_message_request_delay"]

    # for each missing block
    for i, b in enumerate(missing_blocks):
        # calculate the transmission delay + validation delay for the block
        delay_network = Network.calculate_message_propagation_delay(
            request_node, desynced_node, b.size
        )

        delay = (
            delay_network
            + Parameters.execution["block_val_delay"]
            + Parameters.execution["sync_message_request_delay"]
        )

        # add the delay of the current block to the total delay
        total_delay += delay

        # update the time added for the block and mark it as a 'synced' block
        missing_blocks[i].time_added = time + total_delay
        missing_blocks[i].extra_data["synced"] = True

    logger.debug(f"Requested {len(missing_blocks)} and the sync time is {total_delay}")

    # schedule the sync event
    payload = {
        "request_node": request_node,
        "type": "local_fast_sync",
        "blocks": missing_blocks,
        "fail": False,
    }
    event = Scheduler.schedule_event(
        desynced_node, time + total_delay, payload, handler
    )

    if desynced_node.cp is None or desynced_node.cp.NAME != "DESYNC":
        desynced_node.cp = SyncingState(desynced_node)

    desynced_node.cp.local_fast_sync_event_data = event


def create_local_sync_event_configuration(
    desynced_node: "Node", request_node: "Node", time: float
) -> None:
    """
    Gets missing configuration blocks from request node
    Request node: node from which we request missing blocks
        examples:
            - the node whose message made us aware that we are de-synced
            - the peer with the longest chain
    Calculates transmission + validation delay and creates a local sync event
    (local event of the desynced node) at the moment in time when the sync
    processes would have finished
    """
    logger.debug(
        f"Node {desynced_node.id} is requesting a CONFIGURATION sync from Node {request_node.id}..."
    )

    latest_block = desynced_node.confchain[-1]
    sync_chain = request_node.confchain

    missing_blocks = []
    for b in reversed(sync_chain):
        if b.depth > latest_block.depth:
            missing_blocks.insert(0, b.copy())
        else:
            break

    total_delay = Parameters.execution["sync_message_request_delay"]

    for i, b in enumerate(missing_blocks):
        # calculate the transmission delay + validation delay for the block
        delay_network = Network.calculate_message_propagation_delay(
            sender=request_node, receiver=desynced_node, message_size=b.size
        )

        delay = (
            delay_network
            + Parameters.execution["block_val_delay"]
            + Parameters.execution["sync_message_request_delay"]
        )

        total_delay += delay
        missing_blocks[i].time_added = time + total_delay
        missing_blocks[i].extra_data["synced"] = True

    logger.debug(f"Requested {len(missing_blocks)} and the sync time is {total_delay}")

    # schedule the sync event
    payload = {
        "request_node": request_node,
        "type": "local_fast_sync_configuration",
        "blocks": missing_blocks,
        "fail": False,
    }

    event = Scheduler.schedule_event(
        desynced_node, time + total_delay, payload, handler
    )

    if desynced_node.cp is None or desynced_node.cp.NAME != "DESYNC":
        desynced_node.cp = SyncingState(desynced_node)

    desynced_node.cp.local_fast_sync_event_configuration = event


def handle_local_sync_event(event):
    """
    Copies missing blocks to end of the callers blockchain.
    Additionally, checks if the node we are syncing with has received
    any blocks while we were waiting for the currents once
        If so, also requests the new blocks through another local_sync_event
    Relies on calling the CP specific rejoin method for the node to
    rejoin the consensus process
    """
    node: "Node" = event.creator

    if event.payload["fail"]:
        create_local_sync_event(node, sample(node.neighbours, 1)[0], event.time)
        return "sync_failed"

    received_blocks = event.payload["blocks"]

    blockchain = node.blockchain
    sync_chain = event.payload["request_node"].blockchain

    for b in received_blocks:
        if b.depth == blockchain[-1].depth + 1:
            node.add_block(
                block=b,
                time=-1,  # time added is calculated by create_local_sync_event_configuration
                # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                update_time_added=False,
                blockchain="blockchain",
            )

    if blockchain[-1].depth < sync_chain[-1].depth:
        logger.debug(
            f"Node {node.id} is still out of sync in BLOCKCHAIN! Scheduling a new sync event..."
        )

        create_local_sync_event(
            desynced_node=node,
            request_node=event.payload["request_node"],
            time=event.time,
        )
        return "still_out_of_sync"

    # adds time of final check
    event.time += Parameters.execution["sync_message_request_delay"]

    assert node.cp.NAME == "DESYNC"

    node.cp.local_fast_sync_event_data = None
    node.state.synced = True
    if node.cp.ready_to_rejoin():
        node.join_latest_conf(event.time)
        return "successfully_synced"

    logger.debug(f"Node {node.id} is still out of sync in CONFCHAIN! waiting...")
    return "still_out_of_sync"


def handle_local_sync_event_configuration(event: Event):
    """
    Copies missing blocks to end of the callers configuration blockchain.
    Additionally, checks if the node we are syncing with has received any
    conf blocks while we were waiting for the currents once
        If so, also requests the new blocks through another local_sync_event_configuration
    """
    node: "Node" = event.creator

    if event.payload["fail"]:  # retry
        create_local_sync_event_configuration(
            desynced_node=node,
            request_node=sample(node.neighbours, 1)[0],
            time=event.time,
        )
        return "sync_failed"

    received_blocks = event.payload["blocks"]
    blockchain = node.confchain
    sync_chain = event.payload["request_node"].confchain

    for b in received_blocks:
        if b.depth == blockchain[-1].depth + 1:
            node.add_block(
                block=b,
                time=-1,  # time added is calculated by create_local_sync_event_configuration
                # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                update_time_added=False,
                blockchain="configuration",
            )

    if blockchain[-1].depth < sync_chain[-1].depth:
        logger.debug(
            f"Node {node.id} is still out of sync in CONFCHAIN! Scheduling a new sync event..."
        )
        create_local_sync_event_configuration(
            desynced_node=node,
            request_node=event.payload["request_node"],
            time=event.time,
        )
        return "still_out_of_sync"

    event.time += Parameters.execution["sync_message_request_delay"]

    assert node.cp.NAME == "DESYNC"
    node.cp.local_fast_sync_event_configuration = None

    node.configuration_synced = True
    if node.cp.ready_to_rejoin():
        node.join_latest_conf(event.time)
        return "successfully_synced"

    logger.debug(f"Node {node.id} is still out of sync in BLOCKCHAIN! waiting...")
    return "still_out_of_sync"
