from Chain.Block import Block
from Chain.Consensus.Rounds import RoundChangeState

import abc
from typing import Optional, Tuple


class ConsensusProtocol(abc.ABC):
    """
    An abstract class for the state definition of consensus protocols.

    Specifically for protocols that work in rounds
    """

    NAME: str
    rounds: RoundChangeState

    @abc.abstractmethod
    def __init__(self, node) -> None:
        """Initialize the consensus protocol state."""

    @abc.abstractmethod
    def set_state(self) -> None:
        """Reset/initialize the protocol state variables."""
        pass

    @abc.abstractmethod
    def state_to_string(self) -> str:
        """Return a string representation of the current protocol state."""
        pass

    @abc.abstractmethod
    def validate_message(self, event) -> Tuple[bool, Optional[str]]:
        """
        Validate an incoming message event.

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, action)
            where action can be None or "backlog"
        """
        pass

    @abc.abstractmethod
    def validate_block(self, block: Block, time: float) -> str:
        """
        Validate a proposed block.

        Returns:
            str: One of "valid", "invalid", "backlog", "future_block", "future_conf"
        """
        pass

    @abc.abstractmethod
    def init(self, time: float, starting_round: int) -> None:
        """Initialize the protocol state and start consensus."""
        pass

    @abc.abstractmethod
    def start(self, time: float, starting_round: int) -> int:
        """Start a new consensus round."""
        pass

    @abc.abstractmethod
    def init_round_change(self, time: float) -> None:
        """
        Handles protocol specific logic for starting a round change
        """
        pass

    @abc.abstractmethod
    def rejoin(self, time: float) -> None:
        """Handle protocol-specific logic when a node rejoins the network."""
        pass

    @staticmethod
    @abc.abstractmethod
    def handle_event(event) -> str:
        """
        Handle protocol-specific events.

        Returns:
            str: Result of event handling
        """
        pass
