import bisect

from Chain.Parameters import Parameters
from Chain.Network import Network

import Chain.tools as tools

from Chain.Event import Event, MessageEvent

'''
    Handling and running Events
'''


def handle_event(event, backlog=True):
    '''
        Handless events by calling their respctive handlers and backlogs

        Possible outcomes from handlers:
            handled     - Event was handled sucessfully (no state change e.g vote counted but not enough votes yet, old message ETC..)
            new_state   - Event was handled and node changed state -> check backlog to see if messages can be handled under this new state
            invalid     - Invalid message
            unhadled    - Could not handle (error message)
            backlog     - future message, add to backlog
    '''
    if event.payload["type"] in Parameters.simulation["events"].keys():
        Parameters.simulation["events"][event.payload["type"]] += 1
    else:
        Parameters.simulation["events"][event.payload["type"]] = 1

    # if node is dead - event will not be handled
    if not event.actor.state.alive:
        return 'dead_node'

    # if this event is CP specific and the CP of the event does not mactch the current CP - old message
    if "CP" in event.payload and event.payload['CP'] != event.actor.cp.NAME:
        return 'invalid'

    # if network mode is gossip - the node will mutlticast message to it's neighbours.
    # Checking if backlog == True since we don't want want to multicast when cheking backlog (Backlog == True when handling an event for the first time)
    if Parameters.network["gossip"] and backlog and isinstance(event, MessageEvent):
        Network.multicast(event.actor, event)

    # handlle event using it's respective handler
    ret = event.handler(event)

    if ret == 'backlog' and backlog:
        # add event to backlog
        # if backloged event (when backlog == False) returns backlog -> still future event)
        bisect.insort(event.actor.backlog, event)
    elif ret == 'new_state' and backlog:
        # if the event caused a new satate, check the backlog
        handle_backlog(event.actor)
    elif ret == 'unhadled':
        raise ValueError("Event was not handled by its own handler!")

    return ret


def handle_backlog(node):
    '''
        Tries to handle every event in the backlog - removes handled events
    '''
    remove_list = []

    for event in node.backlog:
        tools.debug_logs(
            msg=f"{node.__str__(full=True)}", input=f"HANDLING BACKLOOOG: {event} ", in_col="43", clear=False)

        ret = handle_event(event, backlog=False)

        tools.debug_logs(msg=f"event returned {ret}")

        if ret == 'handled' or ret == 'new_state' or ret == 'invalid':
            remove_list.append(event)

    # if event causes node to enter new round - backlog is cleared and thus this will error out
    if node.backlog:
        for e in remove_list:
            node.backlog.remove(e)
