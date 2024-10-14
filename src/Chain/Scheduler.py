from Chain.Event import Event
from Chain.Network import Network


class Scheduler:
    '''
        Schedules local and network events
            Abstracts event management from the models
            Allows changing how events are generated added to the queue without having to modify models
    '''
    def __init__(self, node) -> None:
        self.node = node

    def schedule_broadcast_message(self, creator, time, payload, handler):
        '''
            Utilises the network module to create and add to the event queue events that model the broadcasting of messages
            (This is agnostic to the broadcast algorithm - the specifics of the broadcast (Gossip etc..) are handled by the Network)
        '''
        # Schedules a message broadcast from node
        event = Event(handler, creator, time, payload)
        Network.send_message(creator, event)
        return event

    def schedule_event(self, creator, time, payload, handler):
        '''
            Adds local events to the event queue
        '''
        # Schedules a local event
        event = Event(handler, creator, time, payload)

        creator.add_event(event)
        return event
