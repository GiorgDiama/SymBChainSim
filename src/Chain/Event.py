from random import randint

class Event():
    '''
        Models events for the descrete event simulation

        Each event contains a reference to it's specific handler
            Example: an event generated representing an PBFT message will contain a referene to Consensus.PBFT.handle_event()
            and can be handled by calling event.handler(event)

        Event: Models a local event (i.e timeouts) - is added straight into the EventQueue of the node

        actor: reference to the node that this event is meant for - any object inheriting base event *MUST* use the "actor" attribute
    '''
    def __hash__(self) -> int:
        return hash((self.id, self.time))
    
    def __lt__(self, other):
        return self.time < other.time

    def __le__(self, other):
        return self.time <= other.time

    def __eq__(self, other):
        return self.time == other.time

    def __ne__(self, other):
        return self.time != other.time

    def __gt__(self, other):
        return self.time > other.time

    def __ge__(self, other):
        return self.time >= other.time

    def __str__(self):
        return f"LCL: {self.creator.id} at {round(self.time,3)} - payload {self.payload}"

    def __repr__(self):
        return f"LCL: {self.creator.id} {round(self.time,3)} {self.payload['type']}"

    def __init__(self, handler, creator, time, payload, id = -1) -> None:
        # unique id (or hash) used to identeify received messages for gossip
        self.id = randint(0, 1000000) if id == -1 else id
        
        self.handler = handler
        self.creator = creator
        self.time = time
        self.payload = payload

        self.actor = creator
    
    def to_serializable(self):
        return {
            "creator": self.creator.id,
            "time": self.time,
            "type": self.payload["type"]
        }

class MessageEvent(Event):
    '''
        Models messages betwee nodes (i.e cp message, sync msessage, new blocks etc)
        is created by the netwrok through a node Event and added to the EQ's of other nodes
    '''
    def __str__(self):
        return f"MSG: {self.creator} -> {self.receiver}  {round(self.time,3)} - payload {self.payload}"

    def __repr__(self):
        return f"MSG: {self.creator} -> {self.receiver} - time {round(self.time,3)} - payload {self.payload}"

    def __init__(self, handler, creator, time, payload, id, receiver) -> None:
        super().__init__(handler, creator, time, payload, id)

        self.receiver = receiver

        self.actor = receiver

    def isSame(self, other):
        return self.id == other.id

    @staticmethod
    def from_Event(event, receiver):
        return MessageEvent(event.handler, event.creator, event.time, event.payload, event.id, receiver)
    
    def to_serializable(self):
        return {
            "creator": self.creator.id,
            "receiver": self.receiver.id,
            "time": self.time,
            "type": self.payload["type"]
        }

class SystemEvent():
    '''
        Simplified event for simulation managemnt tasks
    '''
    def __hash__(self) -> int:
        return hash((self.id, self.time))
    
    def __lt__(self, other):
        return self.time < other.time

    def __le__(self, other):
        return self.time <= other.time

    def __eq__(self, other):
        return self.time == other.time

    def __ne__(self, other):
        return self.time != other.time

    def __gt__(self, other):
        return self.time > other.time

    def __ge__(self, other):
        return self.time >= other.time

    def __str__(self):
        return f"SYSTEM: {round(self.time,3)} - payload {self.payload}"

    def __repr__(self):
        return f"SYSTEM: {round(self.time,3)} - payload {self.payload}"

    def __init__(self, time, payload) -> None:
        self.id = randint(0, 1000000) if id == -1 else id
        self.time = time
        self.payload = payload