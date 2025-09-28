from Parameters import Parameters

from Chain.Consensus import HighLevelSync
from Chain.Consensus.ConsensusProtocol import ConsensusProtocol
from Chain.TransactionFactory import TransactionFactory
from Chain.Block import Block 
from Chain.Reconfiguration.ConfigurationBlock import ConfigurationBlock

from Engine.Scheduler import Scheduler

from Utils import Tools

from types import SimpleNamespace
from collections import deque

from typing import Union, Optional, TYPE_CHECKING, Deque

if TYPE_CHECKING:
    from Engine.EventQueue import Queue
    from Engine.Event import Event
    from Chain.TransactionFactory import Transaction


import logging

logger = logging.getLogger(__name__.split(".")[-1])


class Node:
    """
    Node  models a generic blockchain node

    Attributes:
    id (int): unique node id
    blockchain: list of blocks
    pool: list of new transactions not yet added to blocks
    blocks: No. of blocks
    neighbours: the nodes peers in the network
    location: the nodes physical location
    bandwidth = None
    state: A namespace denoting the sate of the node
    synced...
    alive...
    cp: a reference to the CP class
    cp_state: a namespace storing CP specific data (defined by the CP)
    extra_data: a map storing extra data needed in the node
    Queue: The event queue of the DES
    Backlog: Stores 'future' events

    When an event appears to be from the future (e.g. from nodes that are further ahead in the consensus processes) it as added to the backlog.
    Once the state is updated, the backlogged events are checked to see whether they can be executed.
    example in PBFT:
        Node_1 receives a valid commit message while in the 'pre-prepare' state.
        Node_1 cannot process such a message since he has not received enough prepare messages to move to the 'prepared' state
        Node_1 stores the commit message in its backlog (instead of ignoring since it could be valid).
        After node_1 receives enough prepare messages and its state is updated to 'prepared' the backlog is checked
        The commit message can now be handled properly
        Without the backlog mechanism Node_1 might not have been able to complete the CP protocol and could eventually desync!
    """

    def __init__(self, id: int, queue: "Queue"):
        self.id: int = id
        self.blockchain: list["Block"] = []
        self.pool: Deque["Transaction"] = deque([])
        self.blocks: int = 0

        self.neighbours: list["Node"] = []
        self.location: str = ""
        self.bandwidth: Union[tuple[float, float], float] = None

        self.state = SimpleNamespace(
            alive=True,
            synced=True,
        )

        self.cp: ConsensusProtocol = None

        self.behaviour = SimpleNamespace(
            faulty=None,
            mean_fault_time=None,
            mean_recovery_time=None,
            fault_event=None,
            recovery_event=None,
            byzantine=None,
            sync_fault_chance=None,
        )

        self.backlog: list["Event"] = []

        self.queue: Queue = queue

        # configuration & reconfiguration
        self.confchain: list["ConfigurationBlock"] = []
        self.configuration_synced: bool = True
        self.current_configuration_depth: int = -2

        self.configuration = SimpleNamespace(
            block_size=None,
            block_time=None,
        )
        logger.debug(f"Node {self.id} initialized.")

    def try_apply_configuration(
        self, configuration_block: "ConfigurationBlock", time: float
    ) -> bool:
        """
        Attempts to apply the latest configuration defined by the latest configuration block

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
            logger.debug(
                f"Node {self.id}: Configuration block at depth {configuration_block.depth} already applied."
            )
            return False

        self.current_configuration_depth = configuration_block.depth

        reinit_state = False

        updated = ""
        if "block_size" in configuration_block.configuration:
            updated += f"block_size: {self.configuration.block_size}"
            self.configuration.block_size = configuration_block.configuration[
                "block_size"
            ]
            updated += f"->{self.configuration.block_size} | "
            logger.debug(
                f"Node {self.id}: Block size updated to {self.configuration.block_size} at time {time}."
            )

        if "block_interval" in configuration_block.configuration:
            updated += f"block_time: {self.configuration.block_time}"
            self.configuration.block_time = configuration_block.configuration[
                "block_interval"
            ]
            updated += f"->{self.configuration.block_time} | "
            logger.debug(
                f"Node {self.id}: Block interval updated to {self.configuration.block_time} at time {time}."
            )

        if protocol := configuration_block.configuration.get("CP", ""):
            if self.cp is None or self.cp.NAME != protocol:
                updated += f"consensus: {self.cp.NAME if self.cp is not None else 'None'}->{protocol}"
                self.join_latest_conf(time)
                reinit_state = True
                logger.debug(
                    f"Node {self.id}: Consensus protocol changed from {self.cp.NAME if self.cp is not None else 'None'} to {protocol} at time {time}."
                )
            else:
                updated += f"consensus: {self.cp.NAME}->{self.cp.NAME}"
                logger.debug(
                    f"Node {self.id}: Consensus protocol remains {self.cp.NAME}."
                )

        configuration_block.extra_data["applied"] = time

        logger.debug(
            f"Node {self.id}: Configuration block at depth {configuration_block.depth} applied at time {time}."
        )
        return reinit_state

    def join_latest_conf(self, time: float) -> None:
        """
        Initialises the node consensus state using the protocol in the latest configuration block with the following parameters:
            time  = time
            round = last_block_round + 1
        """
        protocol = self.confchain[-1].configuration["CP"]
        self.cp = Parameters.CPs[protocol](self)

        assert self.cp is not None, (
            "failed to retrieve CP from latest configuration block"
        )

        self.cp.init(
            time=time,
            starting_round=self.blockchain[-1].extra_data["round"] + 1,
        )

        logger.debug(
            f"Node {self.id}: Joining latest configuration at time {time} with protocol {self.cp.NAME}."
        )

    def update(self, time: float) -> bool:
        """
        Attempts to updated the nodes configuration using the latest configuration block
        Returns:
            bool:
                State updated?
            
        When this is called from a consensus state, the
        caller should ensure that the old state does not attempt to modify the state any more
        """
        logger.debug(
            f"Node {self.id}: Attempting to update configuration at time {time}."
        )
        return self.try_apply_configuration(self.confchain[-1], time)

    def validate_block(self, block: "Block") -> str:
        """
        Handles generic validation of new blocks and the configuration used to create them
        This is wrapped by PROTOCOL.state.validate_block

        First evaluate general conditions (block height, round, proposer...)
            future blocks return 'future_block'

        Configuration validation:
            if older configuration is used then the block is invalids
            if 'future', attempt to synchronise configuration chain and return 'future_conf'
        """
        assert self.cp is not None, "node does not have a CP"

        decision = "valid"

        if block.extra_data["round"] != self.cp.rounds.round:
            # Even if round >= r future is not a good idea
            # proposers could propose blocks at future rounds and cause
            # everyone to sync forever
            return "invalid"

        if block.depth <= self.last_block.depth:
            return "invalid"

        if block.depth > self.last_block.depth + 1:
            decision = "future_block"

        block_conf_depth = block.extra_data["configuration_depth"]

        if block_conf_depth < self.confchain[-1].depth:
            return "invalid"

        if block_conf_depth > self.confchain[-1].depth:
            return "future_conf"

        return decision

    def is_synced_with_neighbours(self) -> tuple[bool, Optional["Node"]]:
        """
        Compares the latest block of current node with all peers to check sync status
        If desynced, returns the node that is furthest

        Returns:
            (bool, Node): 
                (True, None) if node is synced. 
                (False, Node) where the Node is the neighbour that is ahead.
        """
        logger.debug(f"Node {self.id}: Checking blockchain sync status with neighbours")

        # creates (neighbour, block, depth) triplet from
        # neighbours that have a later DATA blocks than us
        neighbours_ahead = [
            (n, n.last_block, n.last_block.depth)
            for n in self.neighbours
            if n.last_block.depth > self.last_block.depth
        ]

        if neighbours_ahead:
            node_furthest_ahead = max(neighbours_ahead, key=lambda x: x[2])
            logger.debug(
                f"Node {self.id}: Desynced with neighbour {node_furthest_ahead[0].id} (ahead at depth {node_furthest_ahead[2]})."
            )
            return False, node_furthest_ahead[0]
        logger.debug(f"Node {self.id}: Synced with all neighbours for {type} chain.")
        return True, None

    def attempt_sync(self, time: float, sync_node: Optional["Node"] = None) -> bool:
        """
        Attempts to synchronize the node to the latest data block.
        This method checks whether the node is synchronized with its neighbors
        or a specified synchronization node. If the node is found to be desynchronized,
        it transitions the node's state to a desynchronized state and triggers a local
        synchronization event.
        Args:
            time (float): The current simulation time at which the synchronization
                          attempt is being made.
            sync_node (Optional[Node]): The node to synchronize with. If None, the
                                        method will check synchronization status
                                        with neighboring nodes.
        Returns:
            bool: True if the node is detected to be desynchronized, False otherwise.
        Notes:
            - If the node is already in a desynchronized state (`self.state.synced` is False),
              the method immediately returns True without further processing.
            - If `sync_node` is not provided, the method determines synchronization status
              with neighboring nodes using the `is_synced_with_neighbours` method.
            - If the node is found to be desynchronized, it updates the node's state to
              unsynchronized and creates a local synchronization event using
              `HighLevelSync.create_local_sync_event`.
        """

        if not self.state.synced:
            logger.debug(f"Node {self.id}: Already desynced.")
            return True

        if sync_node is None:
            is_synced, sync_node = self.is_synced_with_neighbours()
        else:
            is_synced = False

        if not is_synced:
            assert sync_node is not None, "request node cannot be None"

            self.state.synced = False
            logger.debug(
                f"Node {self.id}: Detected desync with node {sync_node.id} at time {time}. Triggering local sync event."
            )
            HighLevelSync.create_local_sync_event(
                desynced_node=self, request_node=sync_node, time=time
            )
            return True
        logger.debug(f"Node {self.id}: Sync check passed at time {time}.")
        return False

    def is_synced_with_neighbours_configuration(self) -> tuple[bool, Optional["Node"]]:
        """
        Compares the latest configuration of current node with all peers to check sync status
        If desynced, returns the node that is furthest

        Returns:
            (bool, Node): 
                (True, None) if node is synced. 
                (False, Node) where the Node is the neighbour that is ahead.
        """
        logger.debug(
            f"Node {self.id}: Checking configuration sync status with neighbours."
        )

        # creates (neighbour, block, depth) triplet from
        # neighbours that have a later CONF blocks than us
        neighbours_ahead = [
            (n, n.confchain[-1], n.confchain[-1].depth)
            for n in self.neighbours
            if n.confchain[-1].depth > self.confchain[-1].depth
        ]

        if neighbours_ahead:
            node_furthest_ahead = max(neighbours_ahead, key=lambda x: x[2])
            logger.debug(
                f"Node {self.id}: Desynced with neighbour {node_furthest_ahead[0].id} (ahead at depth {node_furthest_ahead[2]})."
            )
            return False, node_furthest_ahead[0]
        logger.debug(f"Node {self.id}: Synced with all neighbours for {type} chain.")
        return True, None

    def attempt_sync_configuration(
        self, time: float, sync_node: Optional["Node"] = None
    ) -> bool:
        """
        Attempts to synchronise node to latest configuration block.
        
        Args:
            Time:

        Returns:
            bool: True when node is detected to be desynced

        If the caller is part of the old state it should terminate
        without attempting to modify the node state as the node state changed to SyncingState
        """
        if not self.configuration_synced:
            logger.debug(f"Node {self.id}: Already configuration-desynced.")
            return True

        if sync_node is None:
            is_synced, sync_node = self.is_synced_with_neighbours_configuration()
        else:
            is_synced = False

        if not is_synced:
            assert sync_node is not None, "request node cannot be None"

            self.configuration_synced = False
            logger.debug(
                f"Node {self.id}: Detected configuration desync with node {sync_node.id} at time {time}. Triggering local config sync event."
            )
            HighLevelSync.create_local_sync_event_configuration(
                desynced_node=self, request_node=sync_node, time=time
            )
            return True

        logger.debug(f"Node {self.id}: Configuration sync check passed at time {time}.")
        return False

    def kill(self) -> None:
        """
        Makes a node appear offline (sets node.state.alive to False)
        Offline nodes ignored all events (message and local) until they self.alive is set to True
        System events changing the state of the system (e.g network bandwidth) are NOT affected by offline nodes
        """
        self.state.alive = False
        logger.debug(f"Node {self.id}: Killed (set to offline).")

    def resurrect(self, time: float) -> None:
        """
        Gracefully resurrects an offline node by checking for future blocks and attempting to sync chains
        if still synced calls protocol specific rejoin method
        """
        self.state.alive = True
        logger.debug(f"Node {self.id}: Resurrected at time {time}.")

        is_desynced = self.attempt_sync(time)

        if not is_desynced:
            logger.debug(
                f"Node {self.id}: Rejoining latest configuration after resurrection at time {time}."
            )
            self.join_latest_conf(time)

    def add_block(
        self,
        block: Union["Block", "ConfigurationBlock"],
        time: float,
        update_time_added: Optional[bool] = True,
        blockchain: str = "blockchain",
    ) -> None:
        """
        Adds 'block' to blockchain at time 'time'
        Removes included transactions from the memory pool
        """
        logger.debug(
            f"Node {self.id}: Adding block {block.id} at depth {block.depth} to {blockchain} at time {time}."
        )
        if update_time_added:
            block.time_added = time

        match blockchain:
            case "blockchain":
                assert isinstance(block, Block), (
                    "attempted to add confiugration block to blockchain"
                )
                self.blockchain.append(block)
                TransactionFactory.mark_transactions_as_processed(block, self.pool)
                logger.debug(
                    f"Node {self.id}: Block {block.id} added to blockchain at depth {block.depth}."
                )
            case "configuration":
                assert isinstance(block, ConfigurationBlock), (
                    "attempted to add block block to configurationChain"
                )
                self.confchain.append(block)
                logger.debug(
                    f"Node {self.id}: Configuration block {block.id} added at depth {block.depth}."
                )
            case _:
                raise ValueError(f"No such blockchain type: {blockchain}")

    def add_event(self, event: "Event") -> None:
        """Adds an event to the event queue (if the node is online)"""
        if self.state.alive:
            self.queue.add_event(event)

    def schedule_future_receive_configuration(
        self, block: "ConfigurationBlock", time: float
    ) -> None:
        """Models the optimisation nodes gossiping a new config block to this node"""
        payload = {"type": "prop_conf_block", "block": block}

        Scheduler.schedule_event(self, time, payload, self.event_handler)

    def handle_receive_configuration_block(self, event: "Event") -> str:
        """
        Models the logic of receiving a new configuration block
        checks its validity, appends to local confchain and gossips to peers
        """
        block = event.payload["block"].copy()
        time = event.time
        logger.debug(
            f"Node {self.id}: Handling received configuration block {block.id} at depth {block.depth} at time {time}."
        )

        if block.depth <= self.confchain[-1].depth:
            logger.debug(
                f"Node {self.id}: Received old configuration block {block.id} at depth {block.depth} (ignored)."
            )
            return "invalid"  # old block

        # gossip to peers
        Scheduler.schedule_broadcast_message(
            creator=self,
            time=time,
            payload=event.payload,
            handler=self.event_handler,
            id=event.id,
        )

        if block.depth > self.confchain[-1].depth + 1:
            logger.debug(
                f"Node {self.id}: Received future configuration block {block.id} at depth {block.depth} (attempting sync)."
            )
            self.attempt_sync_configuration(time=time, sync_node=None)
            return "handled"

        self.add_block(block, time, blockchain="configuration")
        logger.debug(
            f"Node {self.id}: New configuration block {block.id} applied at depth {block.depth}."
        )
        return "new_state"

    def event_handler(self, event: "Event") -> str:
        """Event handler for events generated by Node"""
        match event.payload["type"]:
            case "prop_conf_block":
                return event.actor.handle_receive_configuration_block(event)
            case _:
                logger.error(
                    f"Node {self.id}: Event handler could not handle event: {event}!"
                )
                raise ValueError(
                    f"Event handler could not handle its own event: {event}!"
                )

    ################################ UTILITY ############################

    def __repr__(self):
        if self.state.alive:
            return f"Node: {self.id}"
        else:
            return f"\tDEAD - Node: {self.id}"

    def __str__(self, full=False):
        assert self.cp is not None

        if self.state.alive:
            if full:
                return f"{Tools.color(f'Node: {self.id}', 42)}\n   LATEST_BLOCKS {
                    self.trunc_ids
                }  local_pool: {len(self.pool)} global_pool: {
                    len(TransactionFactory.global_mempool)
                } \n   SYNCED: {self.state.synced} | CP: {self.cp.NAME} | CHANGE_TO: {
                    Parameters.application['CP'].NAME
                } | req msg: {Parameters.application['required_messages']} f: {
                    Parameters.application['f']
                } \
                        \n   CP_state: {self.cp.state_to_string()} \n   BEHAVIOUR: {
                    self.behaviour_state_to_string
                }\n"
            else:
                return f"Node: {self.id}"
        else:
            if full:
                return f"{
                    Tools.color(f'**dead** Node: {self.id}', 41)
                } \n   LATEST_BLOCKS {self.trunc_ids} local_pool: {
                    len(self.pool)
                } global_pool: {len(TransactionFactory.global_mempool)} \n   SYNCED: {
                    self.state.synced
                } | CP: {self.cp.NAME} | CHANGE_TO: {Parameters.application['CP'].NAME}\
                        \n   CP_state: {self.cp.state_to_string()} \n   BEHAVIOUR: {
                    self.behaviour_state_to_string
                }\n"
            else:
                return f"**DEAD** - Node: {self.id}"

    def stored_txions(self, num=None):
        """Returns the last 'num' txions from the pool - if num is None returns a list of all txions in the pool"""
        if num is None:
            return [x.id for x in self.pool]
        return [x.id for x in list(self.pool)[-num:]]

    def blockchain_length(self):
        """Returns the length of the blockchain (excluding the genesis block)"""
        return len(self.blockchain) - 1

    @property
    def ids(self):
        """
        returns a list of all block ids in the nodes local blockchain
        """
        return [x.id for x in self.blockchain]

    @property
    def trunc_ids(self):
        """
        returns a list of the last 5 block ids in nodes local blockchain
        """
        hidden_blocks = len(self.blockchain) - 5 if len(self.blockchain) - 5 > 0 else 0
        return f"{hidden_blocks} hidden_blocks...{
            [
                f'{x.id} {x.consensus if x.consensus is not None else None}'
                for x in self.blockchain[-5:]
            ]
        } {self.blockchain[-1].depth}"

    @property
    def last_block(self):
        return self.blockchain[-1]

    @property
    def behaviour_state_to_string(self):
        s = ""
        if self.behaviour.faulty:
            s += f"{Tools.color('FAULTY', 41)} -> mean_fault_time: {
                self.behaviour.mean_fault_time
            } | recover_at: {self.behaviour.recovery_event}"
        else:
            s += "NOT FAULTY"
        s += "\t"
        if self.behaviour.byzantine:
            s += f"{Tools.color('BYZANTINE', 41)} -> fault_chance: {
                self.behaviour.sync_fault_chance
            }"
        else:
            s += "HONEST"

        return s
