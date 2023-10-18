from Chain.Parameters import Parameters
from Chain.Event import SystemEvent
import heapq


def log_events(event):
    if isinstance(event, SystemEvent):
        if event.payload["type"] in Parameters.simulation["events"].keys():
            Parameters.simulation["events"][event.payload["type"]] += 1
        else:
            Parameters.simulation["events"][event.payload["type"]] = 1
    else:
        if event.payload["type"] not in Parameters.simulation["events"].keys():
            Parameters.simulation["events"][event.payload["type"]] = {}

        event_type = Parameters.simulation["events"][event.payload["type"]]

        if event.actor.id in event_type:
            event_type[event.actor.id] += 1
        else:
            event_type[event.actor.id] = 1


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
        '''
            IMPORTANT: 
                Expensive opperation! Dont use unless you absolutely have to!
        '''
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

    def add_old_to_old_messages(self, item):
        pass

    def add_event(self, event):
        self.prio_queue.add_task(event, event.time)

    def remove_event(self, event):
        '''
            NOTE: Expensive opperation! Dont use unless you absolutely have to!
        '''
        self.prio_queue.remove((event.time, event))

    def pop_next_event(self):
        return self.prio_queue.pop_task()

    def size(self):
        return self.prio_queue.size()
