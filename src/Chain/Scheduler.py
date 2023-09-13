from Chain.Event import Event
from Chain.Network import Network

class Scheduler:
    def __init__(self, node) -> None:
        self.node = node

    def schedule_broadcast_message(self, creator, time, payload, handler):
        payload["CP"] = creator.cp.NAME
        # Schedules a message broadcast from node
        event = Event(handler, creator, time, payload)

        Network.send_message(creator, event)
        return event

    def schedule_event(self, creator, time, payload, handler):
        # Schedules a local event
        event = Event(handler, creator, time, payload)

        payload["CP"] = creator.cp.NAME
        creator.add_event(event)
        
        return event