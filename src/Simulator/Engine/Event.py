from Parameters import Parameters

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from Chain.Node import Node


class Event:
    """
    Models a local event in SBS.

    When ID is not provided (-1), event receives an incremental ID based on Parameters.simulation['event_id'].

    Attributes:
        id (int): Unique identifier for the event.
        handler (Any): Handler responsible for processing the event.
        creator (Any): The node that created the event.
        time (float): Timestamp when the event will occur.
        payload (Dict[str, Any]): Data associated with the event.
        actor (Any): The node that will act upon the event (defaults to creator).
    """

    def __hash__(self) -> int:
        return hash((self.id, self.time))

    def __lt__(self, other: "Event") -> bool:
        return self.time < other.time

    def __le__(self, other: "Event") -> bool:
        return self.time <= other.time

    def __eq__(self, other: "Event") -> bool:
        return self.time == other.time

    def __ne__(self, other: "Event") -> bool:
        return self.time != other.time

    def __gt__(self, other: "Event") -> bool:
        return self.time > other.time

    def __ge__(self, other: "Event") -> bool:
        return self.time >= other.time

    def __str__(self) -> str:
        return f"LCL: {self.creator.id} at {round(self.time, 3)} - payload {self.payload}"

    def __repr__(self) -> str:
        return f"LCL: {self.creator.id} {round(self.time, 3)} {self.payload['type']}"

    def __init__(
        self,
        handler: Any,
        creator: "Node",
        time: float,
        payload: Dict[str, Any],
        id: int = -1,
    ) -> None:
        # unique id (or hash) used to identify received messages for gossip
        if id == -1:
            self.id = Parameters.simulation["event_id"]
            Parameters.simulation["event_id"] += 1
        else:
            self.id = id

        self.handler = handler
        self.creator = creator
        self.time = time
        self.payload = payload
        self.actor = creator


class MessageEvent(Event):
    """
    Models network messages between nodes (i.e., CP message, sync message, new blocks, etc.).

    MessageEvents are created by the Network model so that relative delays can be calculated.

    Attributes:
        receiver (Any): The intended recipient of the message.
        forwarded_by (Optional[str]): The node that forwarded the message (gossip), if any.
    """

    def __str__(self) -> str:
        return f"MSG: {self.creator} -> {self.receiver}  {round(self.time, 3)} - payload {self.payload}"

    def __repr__(self) -> str:
        return f"MSG: {self.creator} -> {self.receiver} - time {round(self.time, 3)} - payload {self.payload}"

    def __init__(
        self,
        handler: Any,
        creator: "Node",
        time: float,
        payload: Dict[str, Any],
        id: int,
        receiver: "Node",
    ) -> None:
        super().__init__(handler, creator, time, payload, id)
        self.receiver = receiver
        self.actor = receiver
        self.forwarded_by: Optional[str] = None

    def is_same(self, other: "MessageEvent") -> bool:
        """
        Checks if this message event is the same as another based on their IDs.

        Args:
            other (MessageEvent): The other message event to compare with.

        Returns:
            bool: True if the events have the same ID, False otherwise.
        """
        return self.id == other.id

    @staticmethod
    def from_Event(event: Event, receiver: "Node") -> "MessageEvent":
        """
        Creates a MessageEvent from an existing Event.

        Args:
            event (Event): The source event to convert.
            receiver (Any): The intended recipient of the message.

        Returns:
            MessageEvent: A new MessageEvent instance based on the source event.
        """
        return MessageEvent(event.handler, event.creator, event.time, event.payload, event.id, receiver)


class SystemEvent(Event):
    """
    Simplified event for simulation management tasks.

    Attributes:
        id (int): Unique identifier for the system event.
        time (float): Timestamp when the system event occurred.
        payload (Dict[str, Any]): Data associated with the system event.
    """

    def __str__(self) -> str:
        return f"SYSTEM: {round(self.time, 3)} - payload {self.payload['type']}"

    def __repr__(self) -> str:
        return f"SYSTEM: {round(self.time, 3)} - payload {self.payload['type']}"

    def __init__(self, time: float, payload: Dict[str, Any]) -> None:
        super().__init__(None, None, time, payload, Parameters.simulation["event_id"])
        Parameters.simulation["event_id"] += 1
