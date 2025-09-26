from Engine.Event import Event

from Chain.Network import Network

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from Chain.Node import Node


class Scheduler:
    """
    The `Scheduler` class is responsible for scheduling local and network events.
    It abstracts event management to minimise the event management logic required in model files.
    """

    @staticmethod
    def schedule_broadcast_message(
        creator: "Node",
        time: float,
        payload: dict[str, Any],
        handler: Any,
        id: int = -1,
    ) -> Event:
        """
        Schedules a broadcast message event in the network.
        This function creates an event representing the broadcasting of a message
        and adds it to the event queue. It utilizes the network module to handle
        the specifics of the broadcast, which may include algorithms like Gossip.
        Args:
            creator (Node): The node initiating the broadcast.
            time (float): The time at which the broadcast is scheduled.
            payload (dict[str, Any]): The content of the message to be broadcasted.
            handler (Callable): The function to handle the event when it is processed.
            id (int, optional): The unique identifier of the message. Defaults to -1.
                                If a previously received message ID is provided,
                                it models the "gossiping" of that message.
        Returns:
            Event (Event): The event object representing the scheduled broadcast.
        """

        # Schedules a message broadcast from node
        event = Event(handler, creator, time, payload, id=id)
        Network.send_message(creator, event)
        return event

    @staticmethod
    def schedule_event(
        creator: "Node", time: float, payload: dict[str, Any], handler: Any
    ) -> Event:
        """
        Schedules a local event by adding it to the event queue.

        Args:
            creator (Node): The entity responsible for creating the event.
                      It must have an `add_event` method to add the event to its queue.
            time (float): The time at which the event is scheduled to occur.
            payload (dict[str, Any]): The data or information associated with the event.
            handler (callable): The function or method to be executed when the event is triggered.

        Returns:
            Event: The created event instance that was added to the event queue.
        """
        # Schedules a local event
        event = Event(handler, creator, time, payload)
        creator.add_event(event)
        return event
