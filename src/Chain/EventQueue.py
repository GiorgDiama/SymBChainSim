import bisect
from Chain.Event import MessageEvent

import heapq, itertools

class PrioQueue:
    def __init__(self) -> None:
        self.pq = []
        
    def add_task(self, task, priority):
        heapq.heappush(self.pq, (priority, task))

    def remove_task(self, task):
        exit()

    def pop_task(self):
        return heapq.heappop(self.pq)[1]
    
class Queue:
    '''
        Event queue implementation - holds future events scheduled to be executed

        event_list - holds future node events (in ascending time order)
    '''
    _MESSAGE_HISTORY_CAP = 100

    HEAP = True

    def __init__(self):
        self.event_list = []
        self.prio_queue = PrioQueue()
        self.old_messages = []

    def add_old_to_old_messages(self, item):
        pass
    
    def add_event(self, event):
        '''
            inserts events while mainiting time order
        '''
        if Queue.HEAP:
            self.prio_queue.add_task(event, event.time)
        else:
            bisect.insort(self.event_list, event)

    def remove_event(self, event):
        '''
            removes given event - if serach is true, first search for event to make sure it exists
            search is set as false to reduce comp. complexity when events are knows to be in the queue
        '''
        if Queue.HEAP:
            self.prio_queue.remove_task(event)
        else:
            self.event_list.remove(event)
           
    def pop_next_event(self):
        '''
            REMOVES and returns next event to be executed event 
        '''
        if Queue.HEAP:
            return self.prio_queue.pop_task()
        else:
            return self.event_list.pop(0)
        

    # def size(self):
    #     return len(self.event_list)

    # def isEmpty(self):
    #     return self.event_list

    # def contains_event_message(self, event):
    #     '''
    #         Check if node has received message
    #     '''
    #     def compare(x): return isinstance(x, MessageEvent) and x.id == event.id
        
    #     # True if message is in event list or old messages
    #     return any(map(compare, self.event_list)) or any(map(compare, self.old_messages))
