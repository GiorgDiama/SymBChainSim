from Parameters import Parameters

from Engine.Event import SystemEvent, Event

import heapq


def log_events(event: Event):
    """
    Logs events into the simulation parameters.

    This function updates the `Parameters.simulation['events']` dictionary to keep track of
    the occurrences of different types of events during the simulation. It distinguishes
    between system-wide events and node-specific events.

    Args:
        event (Event): The event to be logged. It can be a `SystemEvent` or another type
                       of event with an associated actor.

    Behavior:
        - For `SystemEvent` instances, the event type count is incremented globally.
        - For other events, the count is incremented per actor (node) for the specific event type.
    """

    if isinstance(event, SystemEvent):
        Parameters.simulation["events"][event.payload["type"]] = (
            Parameters.simulation["events"].get(event.payload["type"], 0) + 1
        )
    else:
        event_type = Parameters.simulation["events"].get(event.payload["type"], {})
        event_type[event.actor.id] = event_type.get(event.actor.id, 0) + 1
        Parameters.simulation["events"][event.payload["type"]] = event_type


class PrioQueue:
    """
    Implements a priority queue as a min-heap
    """

    def __init__(self) -> None:
        self.pq = []

    def add_task(self, task: Event, priority: float):
        log_events(task)
        heapq.heappush(self.pq, (priority, task))

    def pop_task(self):
        return heapq.heappop(self.pq)[1]

    def size(self):
        return len(self.pq)

    def remove(self, task: Event, priority: float):
        if (priority, task) in self.pq:
            self.pq.remove((priority, task))
            heapq.heapify(self.pq)


class Queue:
    """
    Event queue implementation as a minHeap from heapq
    """

    def __init__(self):
        self.prio_queue = PrioQueue()
        self.old_messages = {}

    def add_event(self, event: Event):
        self.prio_queue.add_task(event, event.time)

    def remove_event(self, event: Event):
        self.prio_queue.remove(event, event.time)

    def pop_next_event(self) -> Event:
        return self.prio_queue.pop_task()

    def size(self) -> int:
        return self.prio_queue.size()
