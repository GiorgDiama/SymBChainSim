from .Parameters import Parameters
from .Event import SystemEvent

import heapq


def log_events(event):    
    if isinstance(event, SystemEvent):
        # count system events
        Parameters.simulation['events'][event.payload['type']] = Parameters.simulation["events"].get(
            event.payload['type'], 0) + 1
    else:
        # count Local and Message events per node
        event_type = Parameters.simulation['events'].get(
            event.payload['type'], {})

        event_type[event.actor.id] = event_type.get(event.actor.id, 0) + 1

        Parameters.simulation['events'][event.payload['type']] = event_type


class PrioQueue:
    ''' 
        Implements a priority queue as a min-heap
    '''

    def __init__(self) -> None:
        self.pq = []

    def add_task(self, task, priority):
        log_events(task)
        heapq.heappush(self.pq, (priority, task))

    def pop_task(self):
        return heapq.heappop(self.pq)[1]

    def size(self):
        return len(self.pq)

    def remove(self, task):
        if task in self.pq:
            self.pq.remove(task)
            heapq.heapify(self.pq)


class Queue:
    '''
        Event queue implementation - holds future events scheduled to be executed
    '''

    def __init__(self):
        self.prio_queue = PrioQueue()
        self.old_messages = {}

    def add_event(self, event):
        self.prio_queue.add_task(event, event.time)

    def remove_event(self, event):
        self.prio_queue.remove((event.time, event))

    def pop_next_event(self):
        return self.prio_queue.pop_task()

    def size(self):
        return self.prio_queue.size()
