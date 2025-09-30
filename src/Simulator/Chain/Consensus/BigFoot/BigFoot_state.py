from Parameters import Parameters

from Engine.Handler import handle_backlog

from Chain.TransactionFactory import TransactionFactory
from Chain.Block import Block
from Chain.Consensus import Rounds

from Chain.Consensus.BigFoot import BigFoot_transition as state_transition
from Chain.Consensus.BigFoot import BigFoot_timeouts as timeouts
from Chain.Consensus.BigFoot import BigFoot_messages as messages
from Chain.Consensus.ConsensusProtocol import ConsensusProtocol

from random import randint

from typing import Any, Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from Node import Node
    from Engine.Event import Event

import logging

logger = logging.getLogger(__name__.split(".")[-1])


class BigFoot(ConsensusProtocol):
    """
    BigFoot Consensus Protocol.

    Implementation based on: R. Saltini "BigFooT: A robust optimal-latency BFT blockchain consensus protocol with dynamic validator membership"

    Attributes:
        rounds (Rounds.RoundChangeState): Round change state defined by the rounds module.
        fast_path (bool): Boolean value determining whether the node is in the fast path or not.
        state (str): BigFoot node state (new_round, pre-prepared, prepared, committed).
        miner (Union[str, int]): The id of the miner for the current round.
        msgs (Dict[int, Dict[str, List[Tuple[int, float]]]]): Messages received from other nodes, organized by round and type.
        timeout (Event): Reference to latest timeout event.
        fast_path_timeout (Event): Reference to fast_path_timeout event.
        block (Block): The proposed block in current round.
        node (Node): The node running this protocol instance.
    """

    NAME = "BigFoot"

    def __init__(self, node: "Node") -> None:
        """
        Initializes the BigFoot consensus protocol state.

        Args:
            node (Node): The node running this protocol instance.
        """
        logger.debug(f"Node {node.id}: Initializing BigFoot consensus protocol")
        self.rounds: Rounds.RoundChangeState = Rounds.init_round_change_state()
        self.node: "Node" = node
        self.msgs: Dict = {}

        self.fast_path: bool
        self.state: str
        self.miner: int
        self.timeout: "Event"
        self.fast_path_timeout: "Event"
        self.block: Block

    def state_to_string(self) -> str:
        """
        Returns a string representation of the current protocol state.

        Returns:
            str: Human-readable state string.
        """
        return (
            f"round: {self.rounds.round} | "
            f"node_state: {self.state} | "
            f"miner: {self.miner} | "
            f"block: {self.block.id if self.block is not None else -1} | "
            f"msgs: {self.msgs} | "
            f"timeout_event: "
            f"{(round(self.timeout.time, 3), self.timeout.payload['round']) if self.timeout is not None else -1}"
        )

    def set_state(self) -> None:
        """Resets/initializes the protocol state variables."""
        self.rounds = Rounds.init_round_change_state()
        self.fast_path = True
        self.state = ""
        self.miner = None
        self.msgs = {}
        self.timeout = None
        self.fast_path_timeout = None
        self.block = None

    def reset_msgs(self) -> None:
        """
        Resets the message storage for a given round.

        Args:
            round (int): The round number to reset messages for.
        """
        self.msgs = {
            "prepare": [],
            "commit": [],
        }
        Rounds.reset_votes(self.node)

    def count_votes(self, type: str) -> int:
        """
        Counts the number of votes of a given type for a round.

        Args:
            type (str): The type of vote ("prepare" or "commit")
        Returns:
            int: Number of votes.
        """
        return len(self.msgs[type])

    def process_vote(self, type: str, sender: Any, time: float) -> None:
        """
        Processes a vote by adding it to the message store.

        Args:
            type (str): The type of vote ("prepare" or "commit").
            sender (Any): The sender node.
            time (float): The time the vote was received.
        """
        self.msgs[type] += [(sender.id, time)]

    def get_miner(self) -> None:
        """Determines the miner for the current round based on the configured proposer selection method."""
        match Parameters.execution["proposer_selection"]:
            case "round_robin":
                # new miner in a round robin fashion
                self.miner = self.rounds.round % Parameters.application["Nn"]
            case "hash":
                # get new miner based on the hash of the last block + the round
                # (to avoid endlessly waiting for offline nodes)
                self.miner = (self.node.last_block.id + self.rounds.round) % Parameters.application["Nn"]
            case _:
                raise (ValueError(f"No such 'proposer_selection {Parameters.execution['proposer_selection']}"))

    def validate_message(self, event: Any) -> Tuple[bool, str]:
        """
        Validates an incoming message event.

        Args:
            event (Any): The event to validate.

        Returns:
            Tuple[bool, str]: (is_valid, action), where action can be None or "backlog". Backlog indicates that the message is from the future and must be put in the backlog.
        """
        round, current_round = event.payload["round"], self.rounds.round

        if round < current_round:
            return False, None
        elif round == current_round:
            return True, None
        else:
            return True, "backlog"

    def validate_block(self, block: Block, time: float) -> str:
        """
        Validates a proposed block.

        Args:
            block (Block): The block to validate.
            time (float): The current simulation time.

        Returns:
            str: One of "valid", "invalid", "backlog", "future_block", "future_conf".
        """
        result = self.node.validate_block(block)

        match result:
            case "invalid":
                Rounds.change_round(self.node, time)
                return "invalid"
            case "future_block":
                return "backlog"
            case "future_conf":
                return "backlog"
            case "valid":
                return "valid"
            case _:
                raise ValueError(f"Node block validation returned unexpected: {result}")

    def init(self, time: float, starting_round: int) -> None:
        """
        Initializes the protocol state and starts consensus.

        Args:
            time (float): The current simulation time.
            starting_round (int): The round to start from.
        """
        logger.debug(f"Node {self.node.id}: Initializing BigFoot protocol at time {time}, starting round: {starting_round}")
        self.set_state()
        self.start(time, starting_round)

    def create_BigFoot_block(self, time: float) -> Tuple[Block, float]:
        """
        Creates a new block according to the consensus protocol.

        Args:
            time (float): The current simulation time.

        Returns:
            Tuple[Block, float]: The created block (or None). When no transactions are found, the time of the next future transaction in the tx_pool is returned.
        """
        logger.debug(f"Node {self.node.id}: Creating BigFoot block at time {time}")
        block = Block(
            depth=len(self.node.blockchain),
            id=randint(1, 10000),
            previous=self.node.last_block.id,
            time_created=time,
            miner=self.node.id,
            consensus=BigFoot.NAME,
        )
        block.extra_data = {
            "proposer": self.node.id,
            "round": self.rounds.round,
            "configuration_depth": self.node.reconfiguration_state.confchain[-1].depth,
            "votes": {},
        }

        transactions, size = TransactionFactory.execute_transactions(self.node.reconfiguration_state.configuration, self.node.pool, time)

        if transactions:
            block.transactions = transactions
            block.size = size
            time += +Parameters.execution["creation_time"]
            time += len(transactions) * Parameters.execution["time_per_tx"]

            logger.debug(f"Node {self.node.id}: Successfully created block {block.id} with {len(transactions)} transactions, size: {size}, extra_data: {block.extra_data}")

            return block, time
        else:
            logger.debug(f"Node {self.node.id}: Block creation failed - no transactions available, will retry at time {time}")
            return None, time

    def init_round_change(self, time: float) -> None:
        """
        Schedules a timeout for the round change process.

        Args:
            time (float): The current simulation time.
        """
        logger.debug(f"Node {self.node.id}: Initializing round change timeout at time {time}")
        timeouts.schedule_timeout(self, time, add_time=True)

    def start(self, time: int, new_round: int) -> None:
        """
        Starts a new consensus round.

        Args:
            time (float): The current simulation time.
            new_round (int): The round to start.
        """
        logger.debug(f"Node {self.node.id}: Starting new consensus round {new_round} at time {time}")

        if self.node.update(time):
            logger.debug(f"Node {self.node.id}: Node update returned True, aborting round start")
            return

        self.state = "new_round"
        self.fast_path = True

        self.reset_msgs()

        self.rounds.round = new_round
        self.block = None

        self.get_miner()

        # taking into account block interval for the proposal round timeout
        time += self.node.reconfiguration_state.configuration.block_time

        timeouts.schedule_timeout(self, time)
        timeouts.schedule_timeout(self, time, fast_path=True)

        if self.miner == self.node.id:
            logger.debug(f"Node {self.node.id}: This node is the miner for round {new_round}, scheduling propose message")
            messages.schedule_propose(self, time)
        else:
            logger.debug(f"Node {self.node.id}: This node is not the miner (miner: {self.miner}), checking backlog for future events")
            # check if any future events are here for this round slow nodes might miss pre_prepare vote so its good to check early
            handle_backlog(self.node, time)

    def rejoin(self, time: float) -> None:
        """
        Defines the protocol specific rejoin logic for BigFoot.

        Args:
            time (float): The current simulation time.
        """
        logger.debug(f"Node {self.node.id}: Rejoining BigFoot protocol at time {time}")
        # set node's protocol state
        self.set_state()
        # set round to latest known round (latest block round + 1)
        round = self.node.blockchain[-1].extra_data["round"] + 1
        logger.debug(f"Node {self.node.id}: Rejoining at round {round} (latest block round + 1)")
        self.start(time, round)  # start the protocol

    # -----------------------------------------------------------
    #                      HANDLER
    # -----------------------------------------------------------

    @staticmethod
    def handle_event(event: "Event") -> str:
        """Handles protocol-specific events for BigFoot.

        Args:
            event (Event): The event to handle.

        Returns:
            str: Result of event handling
        """
        if event.actor.cp.NAME != BigFoot.NAME:
            print(f"actor at {event.actor.cp.NAME} tried to execute event {event} at BigFoot state")
            return "different_state"
        match event.payload["type"]:
            case "propose":
                ret = state_transition.propose(event.actor.cp, event)
            case "pre_prepare":
                ret = state_transition.pre_prepare(event.actor.cp, event)
            case "prepare":
                ret = state_transition.prepare(event.actor.cp, event)
            case "commit":
                ret = state_transition.commit(event.actor.cp, event)
            case "timeout":
                ret = timeouts.handle_timeout(event.actor.cp, event)
            case "fast_path_timeout":
                ret = timeouts.handle_timeout(event.actor.cp, event)
            case "new_block":
                ret = state_transition.new_block(event.actor.cp, event)
            case _:
                logger.debug(f"Node {event.actor.id}: Unhandled event type: {event.payload['type']}")
                return "unhandled"

        return ret
