from .Network import Network
from .Event import MessageEvent
from .Utils import tools

import bisect

def handle_event(event, checking_backlog=False):
    '''
        Generic event handler of SBS: handless general logic only!
        Calls event specific handler for events
        Handles the backlog when an event triggers a node to move into a new state (declared by the nodes)

        Frequently returned outcomes from individual handlers:
            handled     - Event was handled successfully but cause no significant state updates (e.g vote counted but not enough votes yet)
            new_state   - Event was handled and node changed state -> check backlog to see if messages can be handled under this new state
            invalid     - Invalid message (straggler from older rounds, etc..)
            unhandled   - Could not handle (error message)
            backlog     - future message, add to backlog

        Successful handling of events is split into two responses (handled and new_state) to reduce the number of times check_back log is called.
        If we know an event did not change the state of a node enough - checking the backlog will be a waste of computation
            - in this cases the local handler can return handled which will not trigger a handle_backlog call
    '''

    # if node is 'dead': ignore all events
    if not event.actor.state.alive:
        return 'dead_node'
    
    #                   THINK/TODO: any point in leaving this check to the protocols?
    # if this event is CP specific and the CP of the event does not match the current CP of the node - old/old message
    if "CP" in event.payload and event.payload['CP'] != event.actor.cp.NAME:
        return 'invalid'
    
    # if network message: handle receiving logic specified by the Network (should not be called on replayed messages)
    if not checking_backlog and isinstance(event, MessageEvent):
        if (result := Network.on_receive(event.actor, event)) != 'process':
            return result
    
    # handle event using it's respective handler
    ret = event.handler(event)

    if ret == 'backlog' and not checking_backlog:
        # future event: add to backlog
        bisect.insort(event.actor.backlog, event)
    elif ret == 'new_state' and not checking_backlog:
        # event caused a new sate, check the backlog (some stored events could be handled now)
        handle_backlog(event.actor, event.time)
    elif ret == 'unhandled':
        raise RuntimeError(f"Event: '{event}' - was not handled by its own handler...")
    
    # return the status of handling the event
    return ret

def handle_backlog(node, call_time):
    '''
        Tries to handle events in the backlog of this node
            Events successfully handled are removed
    '''
    remove_list = []

    for event in node.backlog:
        tools.debug_logs(
            msg=f"{node.__str__(full=True)}", input=f"HANDLING BACKLOG: {event} ", in_col="43", clear=False)

        event.time = call_time # ensure the message is replayed at call_time
        ret = handle_event(event, checking_backlog=True)

        tools.debug_logs(msg=f"event returned {ret}")

        if ret == 'handled' or ret == 'new_state' or ret == 'invalid':
            remove_list.append(event)

    #  some events may clear the backlog - this prevents trying to remove already removed events 
    if node.backlog: 
        node.backlog = [e for e in node.backlog if e not in remove_list]