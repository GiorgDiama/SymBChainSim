import Chain.Consensus.Rounds as Rounds

class X():
    ''' 
    This is a template showing the general structure of CP protocols in SBS.

    Use this to understand what the necessary methods of a CP protocol in SBS are
    in order to implement your own protocols 

    Reading this in combination with an allredy implemented protocol (like PBFT)
    can help you understand better what each required function does
    '''
        
    # this is used to assing the protocol to nodes by name
    NAME = "X"

    def __init__(self, node) -> None:
        '''
            Models the conseusus protocol state
        '''
        #EXAMPLE

        # Rounds module for managing round based protocols
        self.rounds = Rounds.round_change_state()
        # messages received from the consensus 
        self.msgs = {...}

        '''
            referance to the node this instance is attached to
        '''
        self.node = node
    
    def set_state(self):
        '''
            Important if you want to reset the sate / want to define it differently based on the node - can be skipped
        '''
        pass
        
    def state_to_string(self):
        '''
            This returns the state of the CP in a string and is NECESSARY FOR DEBUGGING
        '''
        # EXAMPLE
        s = f"{self.rounds.round} | CP_state: {self.state} | block: {self.block.id if self.block is not None else -1} | msgs: {self.msgs} | TO: {round(self.timeout.time,3) if self.timeout is not None else -1}"
        return s


    def init(self, time=0, starting_round=0):
        ''' 
            This sets the states of the CP and starts the CP process
        '''
        self.set_state()
        # CALL TO THE METHOD STARTING THE CP
        self.start(...)

    def create_X_block(self, time):
        ''' method to create CP specific block'''
        # see examples in implemented CP's
        pass

    @staticmethod
    def handle_event(event):  # specific to PBFT - called by events in Handler.handle_event()
        '''
            X specialised event handler

            Is a static method - passed into every evennt generated
            by X in order for the handler to call this event
        '''
        pass
    
    ########################## PROTOCOL COMMUNICATION ###########################

    '''
        ALL THE EVENT HANDLING METHODS, CALLED BY THE HANDLER, PROGRESSING THE CP
    '''
    def start(self):
        '''
            STARTS PROTOCOL
        '''
        pass
    ########################## RESYNC CP SPECIFIC ACTIONS ###########################

    def resync(self, payload, time):
        ''' 
            X's specific actions to be run in order to resync a node - used by the high level sync module
        '''
        pass

    ######################### OTHER #################################################

    def clean_up(self):
        ""