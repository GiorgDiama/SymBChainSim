import bisect
from Chain.Event import MessageEvent

class Queue:
    '''
        Event queue implementation - holds future events scheduled to be executed

        event_list - holds future node events (in ascending time order)
    '''
    _MESSAGE_HISTORY_CAP = 100

    def __init__(self):
        self.event_list = []
        self.old_messages = []

    @property
    def time_next(self):
        return self.event_list[0].time if self.event_list else None

    def add_old_to_old_messages(self, item):
        if len(self.old_messages) > Queue._MESSAGE_HISTORY_CAP:
            self.old_messages.pop(0)
            self.old_messages.append(item)

    def add_event(self, event):
        '''
            inserts events while mainiting time order
        '''
        bisect.insort(self.event_list, event)

    def remove_event(self, event, search=False):
        '''
            removes given event - if serach is true, first search for event to make sure it exists
            search is set as false to reduce comp. complexity when events are knows to be in the queue
        '''
        if search:
            if event in self.event_list:
                self.event_list.remove(event)
                self.add_old_to_old_messages(event)
        else:
            self.event_list.remove(event)
            self.add_old_to_old_messages(event)
        

    def get_next_event(self):
        '''
            returns next event to be executed event 
        '''
        return self.event_list[0] if self.event_list else None


    def pop_next_event(self):
        '''
            REMOVES and returns next event to be executed event 
        '''
        event = self.event_list.pop(0)
        self.old_messages.append(event)
        return event

    def size(self):
        return len(self.event_list)

    def isEmpty(self):
        return self.event_list

    def contains_event_message(self, event):
        '''
            Check if node has received message
        '''
        def compare(x): return isinstance(x, MessageEvent) and x.id == event.id
        
        # True if message is in event list or old messages
        return any(map(compare, self.event_list)) or any(map(compare, self.old_messages))
