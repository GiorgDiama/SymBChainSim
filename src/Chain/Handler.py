import bisect

from Chain.Parameters import Parameters
from Chain.Network import Network

import Chain.tools as tools

from Chain.Event import Event, MessageEvent

'''
    Handling and running Events
'''


def handle_event(event, backlog=False):
    '''
        Handless events by calling their respctive handlers and backlogs

        Possible outcomes from handlers:
            handled     - Event was handled sucessfully (no state change e.g vote counted but not enough votes yet, old message ETC..)
            new_state   - Event was handled and node changed state -> check backlog to see if messages can be handled under this new state
            invalid     - Invalid message
            unhadled    - Could not handle (error message)
            backlog     - future message, add to backlog
    '''

    # if node is dead - event will not be handled
    if not event.actor.state.alive:
        return 'dead_node'

    # if this event is CP specific and the CP of the event does not mactch the current CP - old message
    if "CP" in event.payload and event.payload['CP'] != event.actor.cp.NAME:
        return 'invalid'

    # if we are not handling backlog events and this is a network event
    if not backlog and isinstance(event, MessageEvent):
        Network.receive(event.actor, event)

    # handlle event using it's respective handler
    ret = event.handler(event)

    if ret == 'backlog' and not backlog:
        # add future event to backlog (not backlog prevents us infinetely adding events to backlog while checking the backlog)
        bisect.insort(event.actor.backlog, event)
    elif ret == 'new_state' and backlog:
        # if the event caused the node to go to a new satate, check the backlog (some future events might be ready to be handled)
        handle_backlog(event.actor)
    elif ret == 'unhadled':
        raise ValueError("Event was not handled by its own handler!")

    return ret


def handle_backlog(node):
    '''
        Tries to handle every event in the backlog - removes handled events
    '''
    i = 0
    while i < len(node.backlog):
        tools.debug_logs(
            msg=f"{node.__str__(full=True)}", input=f"HANDLING BACKLOOOG: {node.backlog[i]} ", in_col="43", clear=False)

        ret = handle_event(node.backlog[i], backlog=False)

        tools.debug_logs(msg=f"event returned {ret}")

        if ret == 'handled' or ret == 'new_state' or ret == 'invalid':
            # if the event was handled, pop the event - i now points to next event so no need to increment
            node.backlog.pop(i)
        else:
            # the event was not handled and is not invalid thus must still be "future event" -> stays in backlog
            i += 1
