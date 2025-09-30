from Parameters import Parameters

from Chain.Consensus import HighLevelSync
from Chain.Consensus.ConsensusProtocol import ConsensusProtocol
from Chain.TransactionFactory import TransactionFactory
from Chain.Block import Block

from Chain.Reconfiguration.ConfigurationBlock import ConfigurationBlock
from Chain.Reconfiguration.ReconfigurationState import ReconfigurationState

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
    Models a generic blockchain node

    Attributes:
        id (int): unique node id
        blockchain(list): the local blockchain structure
        pool(deque): the memory pool of the node
        neighbours (list): a list of the nodes peers
        location (str): the geographical location of the node
        bandwidth (union[float, (float,float)]): either the bandwidth on a normal dist. to sample the bandwidth
        state (SimpleNamespace): contains information about the node: alive & synced
        cp (ConsensusProtocol): the state of the currently active consensus protocol
        behaviour (SimpleNamespace): parameters controlling the behaviour of the node
        backlog (list): a list of future events to be replayed
        queue (Queue): reference to the event queue of the simulation
        reconfiguration_state (ReconfigurationState): controls dynamic reconfiguration of the node
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

        self.reconfiguration_state = ReconfigurationState(self)

        logger.debug(f"Node {self.id} initialized.")

    def join_latest_conf(self, time: float) -> None:
        """
        Initialises the node consensus state using the protocol in the latest configuration block with the following parameters:
            time  = time
            round = last_block_round + 1
        """
        protocol = self.reconfiguration_state.confchain[-1].configuration["CP"]
        self.cp = Parameters.CPs[protocol](self)

        assert self.cp is not None, "failed to retrieve CP from latest configuration block"

        self.cp.init(
            time=time,
            starting_round=self.blockchain[-1].extra_data["round"] + 1,
        )

        logger.debug(f"Node {self.id}: Joining latest configuration at time {time} with protocol {self.cp.NAME}.")

    def update(self, time: float) -> bool:
        """
        Attempts to updated the nodes configuration using the latest configuration block

        When this is called from a consensus state, the caller should ensure that the old state does not attempt to modify the state any more

        Returns:
            state_updated (bool): True if the state was updated

        """
        logger.debug(f"Node {self.id}: Attempting to update configuration at time {time}.")
        return self.reconfiguration_state.try_apply_configuration(self.reconfiguration_state.confchain[-1], time)

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
            return "invalid"

        if block.depth <= self.last_block.depth:
            return "invalid"

        if block.depth > self.last_block.depth + 1:
            decision = "future_block"

        block_conf_depth = block.extra_data["configuration_depth"]

        if block_conf_depth < self.reconfiguration_state.confchain[-1].depth:
            return "invalid"

        if block_conf_depth > self.reconfiguration_state.confchain[-1].depth:
            return "future_conf"

        return decision

    def is_synced_with_neighbours(self) -> tuple[bool, "Node"]:
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
        neighbours_ahead = [(n, n.last_block, n.last_block.depth) for n in self.neighbours if n.last_block.depth > self.last_block.depth]

        if neighbours_ahead:
            node_furthest_ahead = max(neighbours_ahead, key=lambda x: x[2])
            logger.debug(f"Node {self.id}: Desynced with neighbour {node_furthest_ahead[0].id} (ahead at depth {node_furthest_ahead[2]}).")
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
            self.state.synced = False
            logger.debug(f"Node {self.id}: Detected desync with node {sync_node.id} at time {time}. Triggering local sync event.")
            HighLevelSync.create_local_sync_event(desynced_node=self, request_node=sync_node, time=time)
            return True

        logger.debug(f"Node {self.id}: Sync check passed at time {time}.")
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
            logger.debug(f"Node {self.id}: Rejoining latest configuration after resurrection at time {time}.")
            self.join_latest_conf(time)

    def add_block(self, block: "Block", time: float, update_time_added: bool = True) -> None:
        """
        Adds 'block' to blockchain at time 'time'.
        Removes included transactions from the memory pool
        """
        logger.debug(f"Node {self.id}: Adding block {block.id} at depth {block.depth} at time {time}.")
        if update_time_added:
            block.time_added = time

        self.blockchain.append(block)
        TransactionFactory.mark_transactions_as_processed(block, self.pool)

    def add_event(self, event: "Event") -> None:
        """Adds an event to the event queue (if the node is online)"""
        if self.state.alive:
            self.queue.add_event(event)

    # -----------------------------------------------------------
    #                      UTILITY
    # -----------------------------------------------------------

    def __repr__(self):
        if self.state.alive:
            return f"Node: {self.id}"
        else:
            return f"\tDEAD - Node: {self.id}"

    def __str__(self, full=False):
        assert self.cp is not None

        if self.state.alive:
            if full:
                return (
                    f"{Tools.color(f'Node: {self.id}', 42)}\n"
                    f"   LATEST_BLOCKS {self.trunc_ids}  local_pool: {len(self.pool)} "
                    f"global_pool: {len(TransactionFactory.global_mempool)}\n"
                    f"   SYNCED: {self.state.synced} | CP: {self.cp.NAME} | "
                    f"CHANGE_TO: {Parameters.application['CP'].NAME} | "
                    f"req msg: {Parameters.application['required_messages']} "
                    f"f: {Parameters.application['f']}\n"
                    f"   CP_state: {self.cp.state_to_string()}\n"
                    f"   BEHAVIOUR: {self.behaviour_state_to_string}\n"
                )
            else:
                return f"Node: {self.id}"
        else:
            if full:
                return (
                    f"{Tools.color(f'**dead** Node: {self.id}', 41)}\n"
                    f"   LATEST_BLOCKS {self.trunc_ids} local_pool: {len(self.pool)} "
                    f"global_pool: {len(TransactionFactory.global_mempool)}\n"
                    f"   SYNCED: {self.state.synced} | CP: {self.cp.NAME} | "
                    f"CHANGE_TO: {Parameters.application['CP'].NAME}\n"
                    f"   CP_state: {self.cp.state_to_string()}\n"
                    f"   BEHAVIOUR: {self.behaviour_state_to_string}\n"
                )
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
        """returns a list of all block ids in the nodes local blockchain"""
        return [x.id for x in self.blockchain]

    @property
    def trunc_ids(self):
        """returns a list of the last 5 block ids in nodes local blockchain"""
        hidden_blocks = len(self.blockchain) - 5 if len(self.blockchain) - 5 > 0 else 0
        return f"{hidden_blocks} hidden_blocks...{[f'{x.id} {x.consensus if x.consensus is not None else None}' for x in self.blockchain[-5:]]} {self.blockchain[-1].depth}"

    @property
    def last_block(self):
        return self.blockchain[-1]

    @property
    def behaviour_state_to_string(self):
        s = ""
        if self.behaviour.faulty:
            s += f"{Tools.color('FAULTY', 41)} -> mean_fault_time: {self.behaviour.mean_fault_time} | recover_at: {self.behaviour.recovery_event}"
        else:
            s += "NOT FAULTY"
        s += "\t"
        if self.behaviour.byzantine:
            s += f"{Tools.color('BYZANTINE', 41)} -> fault_chance: {self.behaviour.sync_fault_chance}"
        else:
            s += "HONEST"
        return s
