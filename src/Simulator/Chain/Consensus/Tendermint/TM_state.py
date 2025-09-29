from Parameters import Parameters

from Engine.Handler import handle_backlog

from Chain.Block import Block
from Chain.TransactionFactory import TransactionFactory
from Chain.Consensus import Rounds
from Chain.Consensus.Tendermint import TM_transition as state_transitions
from Chain.Consensus.Tendermint import TM_timeouts as timeouts
from Chain.Consensus.Tendermint import TM_messages as messages
from Chain.Consensus.ConsensusProtocol import ConsensusProtocol

from random import randint

from typing import TYPE_CHECKING, Optional, Dict, Tuple

if TYPE_CHECKING:
    from Chain.Node import Node
    from Engine.Event import Event


class Tendermint(ConsensusProtocol):
    """
    Implements the Tendermint consensus protocol state machine for a node.

    Attributes:
        rounds (Rounds.RoundChangeState): The current round state for the protocol.
        state (str): The current protocol state (e.g., 'new_round', 'pre-prepared', etc.).
        miner (Union[str, int]): The current round's proposer/miner.
        msgs (Dict[str, list]): Messages received from other nodes, keyed by type ('prepare', 'commit').
        timeout (Optional[Any]): Reference to the latest timeout event.
        block (Optional[Block]): The current proposed block.
        node (Node): The node running this protocol instance.
    """

    NAME = "Tendermint"

    def __init__(self, node: "Node") -> None:
        """
        Initialize the Tendermint protocol state for a node.

        Args:
            node (Node): The node running this protocol instance.
        """
        self.rounds: Rounds.RoundChangeState = Rounds.init_round_change_state()
        self.state: str
        self.miner: int
        self.msgs: Dict = {}
        self.timeout: "Event"
        self.block: Block
        self.node: "Node" = node

    def set_state(self) -> None:
        """
        Reset/initialize the protocol state variables for a new round or after rejoining.
        """
        self.rounds = Rounds.init_round_change_state()
        self.msgs = {"prepare": [], "commit": []}
        self.timeout = None
        self.block = None

    def state_to_string(self) -> str:
        """
        Return a string representation of the current protocol state.

        Returns:
            str: Human-readable summary of the protocol state.
        """
        s = (
            f"round: {self.rounds.round} | "
            f"round_votes: {self.rounds.votes} | "
            f"CP_state: {self.state} | "
            f"miner: {self.miner} | "
            f"block: {self.block.id if self.block is not None else -1} | "
            f"msgs: {self.msgs} | "
            f"TO: {round(self.timeout.time, 3) if self.timeout is not None else -1}"
        )
        return s

    def reset_msgs(self) -> None:
        """
        Reset the prepare/commit message lists and round votes for a new round.

        Args:
            round (int): The round number to reset for.
        """
        self.msgs = {"prepare": [], "commit": []}
        Rounds.reset_votes(self.node)

    def count_votes(self, type: str) -> int:
        """
        Count the number of votes of a given type for the current round.

        Args:
            type (str): The type of vote ('prepare' or 'commit').
            round (int): The round number (unused, for interface compatibility).

        Returns:
            int: The number of votes of the given type.
        """
        return len(self.msgs[type])

    def process_vote(self, type: str, sender: "Node") -> None:
        """
        Record a vote from a sender for a given type and round.

        Args:
            type (str): The type of vote ('prepare' or 'commit').
            sender (Node): The node sending the vote.
        """
        self.msgs[type] += [sender.id]

    def validate_message(self, event: "Event") -> Tuple[bool, Optional[str]]:
        """
        Validate an incoming message event for round consistency.

        Args:
            event (Event): The event/message to validate.

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, action), where action can be None or 'backlog'.
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
        Validate a proposed block using node logic and protocol-specific checks.

        Args:
            block (Block): The block to validate.
            time (float): The current simulation time.

        Returns:
            str: One of 'valid', 'invalid', 'backlog', 'future_block', 'future_conf'.
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
        Initialize the protocol state and start consensus at a given round and time.

        Args:
            time (float): The current simulation time.
            starting_round (int): The round to start at.
        """
        self.set_state()
        self.start(time, starting_round)

    def get_miner(self) -> None:
        """
        Determine the miner/proposer for the current round based on the configured selection method.
        """
        if Parameters.execution["proposer_selection"] == "round_robin":
            # new miner in a round robin fashion
            self.miner = self.rounds.round % Parameters.application["Nn"]
        elif Parameters.execution["proposer_selection"] == "hash":
            # get new miner based on the hash of the last block + the round (to
            # avoid endlessly waiting for offline nodes)
            self.miner = (self.node.last_block.id + self.rounds.round) % Parameters.application["Nn"]
        else:
            raise (ValueError(f"No such 'proposer_selection {Parameters.execution['proposer_selection']}"))

    def create_TM_block(self, time: float) -> Tuple[Optional[Block], float]:
        """
        Create a new block according to the consensus protocol.

        Args:
            time (float): The current simulation time.

        Returns:
            Tuple[Optional[Block], float]: The created block (or None if no transactions). If no transactions are in the pool return the time of the first future transaction.
        """
        block = Block(
            depth=len(self.node.blockchain),
            id=randint(1, 10000),
            previous=self.node.last_block.id,
            time_created=time,
            miner=self.node.id,
            consensus=Tendermint.NAME,
        )
        block.extra_data = {
            "proposer": self.node.id,
            "round": self.rounds.round,
            "configuration_depth": self.node.reconfiguration_state.confchain[-1].depth,
        }

        if "votes" in self.node.blockchain[-1].extra_data.keys() and self.node.blockchain[-1].consensus == Tendermint:
            block.extra_data["last_proof"] = self.node.blockchain[-1].extra_data["votes"]["commit"]

        transactions, size = TransactionFactory.execute_transactions(self.node.reconfiguration_state.configuration, self.node.pool, time)

        if transactions:
            block.transactions = transactions
            block.size = size + Parameters.data["base_block_size"]
            time += Parameters.execution["creation_time"]
            time += len(transactions) * Parameters.execution["time_per_tx"]

            return block, time
        else:
            return None, time

    def start(self, time: float, new_round: int) -> Optional[int]:
        """
        Start a new consensus round at the given round and time.

        Args:
            new_round (int): The round to start.
            time (float): The current simulation time.

        Returns:
            Optional[int]: 0 if the protocol was interrupted by a configuration update, otherwise None.
        """
        if self.node.update(time):
            return 0

        self.state = "new_round"
        self.reset_msgs()
        self.rounds.round = new_round
        self.block = None
        self.get_miner()

        # taking into account block interval for the proposal round timeout
        time += self.node.reconfiguration_state.configuration.block_time

        timeouts.schedule_timeout(self, time)

        # if the current node is the miner, schedule propose block event
        if self.miner == self.node.id:
            messages.schedule_propose(self, time)
        else:
            # check if any future events are here for this round
            # slow nodes might miss pre_prepare vote so its good to check early
            handle_backlog(self.node, time)

    def init_round_change(self, time: float) -> None:
        """
        Schedule a timeout for the current round change process.

        Args:
            time (float): The current simulation time.
        """
        timeouts.schedule_timeout(self, time)

    def rejoin(self, time: float) -> None:
        """
        Defines the protocol-specific rejoin logic for Tendermint. Resets state and starts at the latest known round.

        Args:
            time (float): The current simulation time.
        """
        self.set_state()  # set node's protocol state
        round = self.node.blockchain[-1].extra_data["round"] + 1  # set round to latest known round (latest block round + 1)
        # NOTE: if this node rejoins at earlier round it's possible that it
        # will try to propose a block. This will be ignored now but if wrong
        # proposals are tracked this should be considered
        self.start(time, round)  # start the protocol

    ########################## HANDLER ###########################

    @staticmethod
    def handle_event(event: "Event") -> str:
        """
        Handle protocol-specific events for Tendermint. Called by events in Handler.handle_event().

        Args:
            event (Event): The event to handle.

        Returns:
            str: Result of event handling
        """
        if event.actor.cp.NAME != Tendermint.NAME:
            print(f"actor at {event.actor.cp.NAME} tried to execute event {event} at Tendermint state")
            return "different_state"
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
                return "unhandled"
