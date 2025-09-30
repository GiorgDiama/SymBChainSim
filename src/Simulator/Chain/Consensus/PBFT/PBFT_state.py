from Parameters import Parameters

from Chain.Block import Block
from Chain.TransactionFactory import TransactionFactory
from Chain.Consensus import Rounds
from Chain.Consensus.PBFT import PBFT_transition as state_transitions
from Chain.Consensus.PBFT import PBFT_timeouts as timeouts
from Chain.Consensus.PBFT import PBFT_messages as messages
from Chain.Consensus import ConsensusProtocol

from Engine.Handler import handle_backlog

from random import randint
from typing import Optional, TYPE_CHECKING, List, Dict
import logging

if TYPE_CHECKING:
    from Engine.Event import Event
    from Block import Block
    from Node import Node

logger = logging.getLogger(__name__.split(".")[-1])


class PBFT(ConsensusProtocol.ConsensusProtocol):
    """
    Practical Byzantine Fault Tolerance Consensus Protocol State

    PBFT State:
        round - current round
        change_to - candidate round to change to
        state - PBFT node state (new_round, pre-prepared, prepared, committed, round_change)]
        msgs: list of messages received from other nodes
        timeout - reference to latest timeout event (when node state updates it is used to find event and delete from event queue)
        block -  the current proposed block
    """

    NAME = "PBFT"

    def __init__(self, node: "Node") -> None:
        """
        Initialize a new PBFT consensus protocol instance.

        Args:
            node: The node running this consensus protocol instance
        """
        logger.debug(f"Node {node.id}: Initializing PBFT consensus protocol")
        self.rounds: Rounds.RoundChangeState = Rounds.init_round_change_state()
        self.state: str = ""
        self.miner: str = ""
        self.msgs: Dict[str, List[str]] = {}
        self.timeout: "Event" = None
        self.block: "Block" = None
        self.node: "Node" = node

    def set_state(self) -> None:
        """Reset the PBFT state to its initial values."""
        self.rounds = Rounds.init_round_change_state()
        self.state = ""
        self.miner = ""
        self.msgs = {"prepare": [], "commit": []}
        self.timeout = None
        self.block = None

    def state_to_string(self) -> str:
        """
        Convert the current PBFT state to a human-readable string representation.

        Returns:
            str: A string representation of the current state
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

    def reset_msgs(self) -> None:
        """Reset the state of the consensus messages and change round votes."""
        self.msgs = {"prepare": [], "commit": []}
        Rounds.reset_votes(self.node)

    def count_votes(self, type: str) -> int:
        """
        Returns the number of votes for a specific message type.

        Args:
            type: The type of message to count votes for

        Returns:
            int: The number of votes for the specified message type
        """
        return len(self.msgs[type])

    def process_vote(self, type: str, sender: "Node") -> None:
        """
        Counts a vote of specified type by the sender.

        Args:
            type: The type of vote to process
            sender: The node that sent the vote
        """
        if type not in self.msgs:
            self.msgs[type] = []
        self.msgs[type].append(str(sender.id))

    def validate_message(self, event: "Event") -> tuple[bool, Optional[str]]:
        """
        Validates messages according to the protocol rules.
            - old messages are invalid
            - future messages sent to backlog
            - current round messages are valid

        Args:
            event: The event containing the message to validate

        Returns:
            tuple: A tuple containing (is_valid: bool, action: Optional[str])
                  where action can be None or "backlog"
        """
        round, current_round = event.payload["round"], self.rounds.round

        if round < current_round:
            return False, None
        elif round == current_round:
            return True, None
        else:
            return True, "backlog"

    def validate_block(self, block: "Block", time: float) -> str:
        """
        Validates a block according to protocol rules.
        Wraps the node validation logic to allow for protocol specific checks
        Handles the logic with possible fail cases node (future block, invalid block etc..)
        passes the results to CP transition which decides what should happen next
        Args:
            block: The block to validate
            time: Current simulation time

        Returns:
            str: Validation result ("invalid", "backlog", "future_conf", or "valid")
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
        Initialize the PBFT protocol with a starting round.

        Args:
            time: Current simulation time
            starting_round: The round number to start from
        """
        self.set_state()
        self.start(time, starting_round)

    def get_miner(self) -> None:
        """
        Implements proposer selection algorithms to determine the proposer for the current round.

        Selection can be either:
            - round_robin: current round mod number of block producers
            - hash_based: (last_block_hash + self.round) mod number of block producers
        """
        if Parameters.execution["proposer_selection"] == "round_robin":
            self.miner = self.rounds.round % Parameters.application["Nn"]
        elif Parameters.execution["proposer_selection"] == "hash":
            self.miner = (self.node.last_block.id + self.rounds.round) % Parameters.application["Nn"]
        else:
            raise ValueError(f"No such 'proposer_selection {Parameters.execution['proposer_selection']}")
        logger.debug(f"Node {self.node.id}: Selected miner {self.miner} for round {self.rounds.round}")

    def create_PBFT_block(self, time: float) -> tuple[Optional["Block"], float]:
        """
        Creates a new PBFT block with the current pending transactions.

        If no transactions are available, looks ahead in the transaction pool and returns the time of the earliest future transactions.

        This is used to know exactly when to reschedule this event.

        Args:
            time: Current simulation time

        Returns:
            tuple: A tuple containing (created_block: Optional[Block], new_time: float)
        """
        logger.debug(f"Node {self.node.id}: Creating PBFT block at time {time}")
        block = Block(
            depth=len(self.node.blockchain),
            id=randint(1, 10000),
            previous=self.node.last_block.id,
            time_created=time,
            miner=self.node.id,
            consensus=PBFT.NAME,
        )
        block.extra_data = {
            "proposer": self.node.id,
            "round": self.rounds.round,
            "configuration_depth": self.node.reconfiguration_state.confchain[-1].depth,
        }

        transactions, size = TransactionFactory.execute_transactions(self.node.reconfiguration_state.configuration, self.node.pool, time)

        if transactions:
            block.transactions = transactions
            block.size = size + Parameters.data["base_block_size"]
            time += Parameters.execution["creation_time"]
            time += len(transactions) * Parameters.execution["time_per_tx"]
            logger.debug(f"Node {self.node.id}: Successfully created block {block.id} with {len(transactions)} transactions, size: {block.size}, extra_data: {block.extra_data}")
            return block, time
        else:
            logger.debug(f"Node {self.node.id}: Block creation failed - no transactions available, will retry at time {time}")
            return None, time

    def start(self, time: float, new_round: int) -> Optional[int]:
        """
        Entry point into the protocol.

        Initializes state and utilizes the proposer selection mechanisms to dictate the behavior of the node.

        Args:
            new_round: The round number to start from
            time: Current simulation time

        Returns:
            Optional[int]: 0 if node needs update, None otherwise
        """
        logger.debug(f"Node {self.node.id}: Starting new consensus round {new_round} at time {time}")

        if self.node.update(time):
            logger.debug(f"Node {self.node.id}: Node update returned True, aborting round start")
            return 0

        self.state = "new_round"
        self.reset_msgs()
        self.rounds.round = new_round
        self.block = None
        self.get_miner()

        time += self.node.reconfiguration_state.configuration.block_time
        timeouts.schedule_timeout(self, time)

        if self.miner == self.node.id:
            logger.debug(f"Node {self.node.id}: This node is the miner for round {new_round}, scheduling propose message")
            messages.schedule_propose(self, time)
        else:
            logger.debug(f"Node {self.node.id}: This node is not the miner (miner: {self.miner}), checking backlog for future events")
            # check for any existing events!
            handle_backlog(self.node, time)
        return None

    def init_round_change(self, time: float) -> None:
        """
        Executes protocol specific actions when entering round_change state.

        Args:
            time: Current simulation time
        """
        logger.debug(f"Node {self.node.id}: Initializing round change timeout at time {time}")
        timeouts.schedule_timeout(self, time, add_time=True)

    def rejoin(self, time: float) -> None:
        """
        Defines the protocol specific rejoin logic for PBFT.

        Args:
            time: Current simulation time
        """
        logger.debug(f"Node {self.node.id}: Rejoining PBFT protocol at time {time}")

        self.set_state()
        round = self.node.blockchain[-1].extra_data["round"] + 1

        logger.debug(f"Node {self.node.id}: Rejoining at round {round} (latest block round + 1)")

        self.start(time, round)

    # -----------------------------------------------------------
    #                      HANDLER
    # -----------------------------------------------------------

    @staticmethod
    def handle_event(event: "Event") -> str:
        """
        Local handler for PBFT events. Processes all event types produced by the protocol.

        Args:
            event: The event to handle

        Returns:
            str: Result of event handling ("different protocol", "unhandled", or protocol-specific result)
        """
        if not event.actor or not event.actor.cp or event.actor.cp.NAME != PBFT.NAME:
            print(f"actor with {event.actor.cp.NAME} tried to execute event {event} at PBFT state")
            return "different protocol"

        match event.payload["type"]:
            case "propose":
                return state_transitions.propose(event.actor.cp, event)
            case "pre_prepare":
                return state_transitions.pre_prepare(event.actor.cp, event)
            case "prepare":
                return state_transitions.prepare(event.actor.cp, event)
            case "commit":
                return state_transitions.commit(event.actor.cp, event)
            case "timeout":
                return timeouts.handle_timeout(event.actor.cp, event)
            case "new_block":
                return state_transitions.new_block(event.actor.cp, event)
            case _:
                logger.debug(f"Node {event.actor.id}: Unhandled event type: {event.payload['type']}")
                return "unhandled"
