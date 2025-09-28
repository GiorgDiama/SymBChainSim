from Engine.Scheduler import Scheduler
from Chain.Consensus import HighLevelSync

from types import SimpleNamespace

import logging
logger = logging.getLogger(__name__.split(".")[-1])

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Chain.Reconfiguration.ConfigurationBlock import ConfigurationBlock
    from Chain.Node import Node
    from Engine.Event import Event

class ReconfigurationState():
    """
        Controls node reconfiguration through a secondary blockchain structure and configuration blocks

        Arguments:
            node (Node): a back reference to the node
            confchain (List): the configuration blockchain structure
            current_configuration_depth (int): the depth of the latest block in the confchain
            configuration ()
    """
    def __init__(self, node: "Node"):
        self.node = node
    
        # configuration & reconfiguration
        self.confchain: list["ConfigurationBlock"] = []
        self.configuration_synced: bool = True
        self.current_configuration_depth: int = -2

        self.configuration = SimpleNamespace(
            block_size=None,
            block_time=None,
        )
    
    def add_configuration_block(self, block: "ConfigurationBlock", time: float, update_time_added: bool = True,) -> None:
        """ Adds configuration block to configuration blockchain """
        if update_time_added:
            block.time_added = time

        self.confchain.append(block)

        logger.debug(f"Node {self.node.id}: Configuration block {block.id} added at depth {block.depth}.")

    def try_apply_configuration(self, configuration_block: "ConfigurationBlock", time: float) -> bool:
        """Attempts to apply the latest configuration defined by the latest configuration block

        Configuration updates are not events! That is, they are not triggered automatically when
        a new conf block is received. The nodes manually check if a new configuration is
        available at certain points when they know its safe to update (e.g., before a new consensus round).
        Switching immediately after receiving a block could lead to many failed rounds

        Node.update() (and thus Node.apply_configuration()), are called from some specific consensus states
            (E.G In PBFT when a new block added and before going to the next round)
        some configuration changes do not require the state to be changed (e.g. changing the block size)
        some others (like changing protocol) do! In the latter cases, we need to let the original state know to
        stop execution, otherwise, their logic will run against the new state causing all sorts of problems
        """

        # check if we updated up to this block depth
        if self.current_configuration_depth >= configuration_block.depth:
            logger.debug(f"Node {self.node.id}: Configuration block at depth {configuration_block.depth} already applied.")
            return False

        self.current_configuration_depth = configuration_block.depth

        reinit_state = False

        if "block_size" in configuration_block.configuration:
            self.configuration.block_size = configuration_block.configuration["block_size"]
            logger.debug(f"Node {self.node.id}: Block size updated to {self.configuration.block_size} at time {time}.")

        if "block_time" in configuration_block.configuration:
            self.configuration.block_time = configuration_block.configuration["block_time"]
            logger.debug(f"Node {self.node.id}: Block interval updated to {self.configuration.block_time} at time {time}.")

        if protocol := configuration_block.configuration.get("CP", ""):
            if self.node.cp is None or self.node.cp.NAME != protocol:
                self.node.join_latest_conf(time)
                reinit_state = True
                logger.debug(f"Node {self.node.id}: Consensus protocol changed from {self.node.cp.NAME if self.node.cp is not None else 'None'} to {protocol} at time {time}.")
            else:
                logger.debug(f"Node {self.node.id}: Consensus protocol remains {self.node.cp.NAME}.")

        configuration_block.extra_data["applied"] = time

        logger.debug(f"Node {self.node.id}: Configuration block at depth {configuration_block.depth} applied at time {time}.")
        return reinit_state

    def is_synced_with_neighbours_configuration(self) -> tuple[bool, "Node"]:
        """Compares the latest configuration of current node with all peers to check sync status
        If desynced, returns the node that is furthest

        Returns:
            (bool, Node): 
                (True, None) if node is synced. 
                (False, Node) where the Node is the neighbour that is ahead.
        """
        logger.debug(f"Node {self.node.id}: Checking configuration sync status with neighbours.")

        # creates (neighbour, block, depth) triplet from
        # neighbours that have a later CONF blocks than us
        neighbours_ahead = [
            (n, n.reconfiguration_state.confchain[-1], n.reconfiguration_state.confchain[-1].depth)
            for n in self.node.neighbours
            if n.reconfiguration_state.confchain[-1].depth > self.confchain[-1].depth
        ]

        if neighbours_ahead:
            node_furthest_ahead = max(neighbours_ahead, key=lambda x: x[2])
            logger.debug(f"Node {self.node.id}: Desynced with neighbour {node_furthest_ahead[0].id} (ahead at depth {node_furthest_ahead[2]}).")
            return False, node_furthest_ahead[0]
        
        logger.debug(f"Node {self.node.id}: Synced with all neighbour configurations")
        return True, None

    def attempt_sync_configuration(self, time: float, sync_node: "Node" = None) -> bool:
        """Attempts to synchronise node to latest configuration block.
        
        Args:
            Time:

        Returns:
            bool: True when node is detected to be desynced

        If the caller is part of the old state it should terminate
        without attempting to modify the node state as the node state changed to SyncingState
        """
        if not self.configuration_synced:
            logger.debug(f"Node {self.node.id}: Already configuration-desynced.")
            return True

        if sync_node is None:
            is_synced, sync_node = self.is_synced_with_neighbours_configuration()
        else:
            is_synced = False

        if not is_synced:
            assert sync_node is not None, "request node cannot be None"

            self.configuration_synced = False
            logger.debug(f"Node {self.node.id}: Detected configuration desync with node {sync_node.id} at time {time}. Triggering local config sync event.")
            
            HighLevelSync.create_local_sync_event_configuration(
                desynced_node=self.node,
                request_node=sync_node,
                time=time
            )

            return True

        logger.debug(f"Node {self.node.id}: Configuration sync check passed at time {time}.")
        return False

    def schedule_future_receive_configuration(self, block: "ConfigurationBlock", time: float) -> None:
        """Models the optimisation nodes gossiping a new config block to this node"""
        payload = {
            "type": "prop_conf_block",
            "block": block
        }
        Scheduler.schedule_event(self.node, time, payload, self.event_handler)

    def handle_receive_configuration_block(self, event: "Event") -> str:
        """Models the logic of receiving a new configuration block
        checks its validity, appends to local confchain and gossips to peers
        """
        block:ConfigurationBlock = event.payload["block"].copy()
        time = event.time
        logger.debug(f"Node {self.node.id}: Handling received configuration block {block.id} at depth {block.depth} at time {time}.")

        if block.depth <= self.confchain[-1].depth:
            logger.debug(f"Node {self.node.id}: Received old configuration block {block.id} at depth {block.depth} (ignored).")
            return "invalid"  # old block

        # gossip to peers
        Scheduler.schedule_broadcast_message(
            creator=self.node,
            time=time,
            payload=event.payload,
            handler=self.event_handler,
            id=event.id,
        )

        if block.depth > self.confchain[-1].depth + 1:
            logger.debug(f"Node {self.node.id}: Received future configuration block {block.id} at depth {block.depth} (attempting sync).")
            self.attempt_sync_configuration(time=time, sync_node=None)
            return "handled"

        self.add_configuration_block(block, time)
        logger.debug(f"Node {self.node.id}: New configuration block {block.id} applied at depth {block.depth}.")
        return "new_state"

    def event_handler(self, event: "Event") -> str:
        """Event handler for events generated by Node"""
        match event.payload["type"]:
            case "prop_conf_block":
                return event.actor.reconfiguration_state.handle_receive_configuration_block(event)
            case _:
                logger.error(f"Node {self.node.id}: Event handler could not handle event: {event}!")
                raise ValueError(f"Event handler could not handle its own event: {event}!")