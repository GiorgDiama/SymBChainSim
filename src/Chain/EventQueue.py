import bisect
from Chain.Event import MessageEvent

import heapq
import itertools


class PrioQueue:
    def __init__(self) -> None:
        self.pq = []

    def add_task(self, task, priority):
        heapq.heappush(self.pq, (priority, task))

    def pop_task(self):
        return heapq.heappop(self.pq)[1]

    def size(self):
        return len(self.pq)

    def remove(self, tasks):
        '''
            IMPORTANT: 
                Expensive opperation! Dont use unless you absolutely have to!
        '''
        self.pq.remove(tasks)
        heapq.heapify(self.pq)


class Queue:
    '''
        Event queue implementation - holds future events scheduled to be executed

        event_list - holds future node events (in ascending time order)
    '''
    _MESSAGE_HISTORY_CAP = 100

    def __init__(self):
        self.prio_queue = PrioQueue()
        self.old_messages = {}

    def add_old_to_old_messages(self, item):
        pass

    def add_event(self, event):
        '''
            inserts events while mainiting time order
        '''
        self.prio_queue.add_task(event, event.time)

    def remove_event(self, event):
        self.prio_queue.remove((event.time, event))

    def pop_next_event(self):
        '''
            REMOVES and returns next event to be executed
        '''
        return self.prio_queue.pop_task()

    def size(self):
        return self.prio_queue.size()

    def isEmpty(self):
        return self.event_list

    def contains_event_message(self, event):
        '''
            Check if node has received message
        '''
        def compare(x): return isinstance(x, MessageEvent) and x.id == event.id

        # True if message is in event list or old messages
        return any(map(compare, self.event_list)) or any(map(compare, self.old_messages))
