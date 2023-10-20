'''
    Models a high-level sync functionality. Caclulates how long it would take for the node to receive the data
    (missing blocks) and creats a local event which copies the missing blocks to the desynced node saving communication
    events
'''

from Chain.Network import Network
from Chain.Parameters import Parameters

import Chain.tools as tools

from random import randint, sample


def handler(event):
    if event.payload["type"] == "local_fast_sync":
        return handle_local_sync_event(event)
    else:
        return "unhadled"


def create_local_sync_event(desynced_node, request_node, time):
    '''
        get missing blocks from request node
        (node from which we request missing blocks i.e node whos message made us know we are desynced)
        Calculate transmission + validation delay and create local sync event after
    '''
    # get the last block of desynced node
    latest_block = desynced_node.last_block

    # find missing blocks in blockchain of request_node
    missing_blocks = []
    for b in reversed(request_node.blockchain):
        if b.depth > latest_block.depth:
            missing_blocks.insert(0, b.copy())
        else:
            break

    total_delay = 0

    # for each missing block
    for i, b in enumerate(missing_blocks):
        # caclulate the transmission delay + validation delay for the block
        delay_network = Network.calculate_message_propagation_delay(
            request_node, desynced_node, b.size)

        delay = delay_network + \
            Parameters.execution["block_val_delay"] + \
            Parameters.execution["sync_message_request_delay"]

        # add the delay of the current block to the total delay
        total_delay += delay

        # update time desynced node will recieve missing block
        missing_blocks[i].time_added += time + total_delay

    missbehave_delay, missbehaviour = apply_sync_missbehaiviour(request_node)

    # create local sync event on desynced_node
    if missbehaviour:  # the request node missbehaved

        payload = {
            "request_node": request_node,
            "type": 'local_fast_sync',
            "blocks": None,
            "fail": True,
        }

        desynced_node.scheduler.schedule_event(
            desynced_node, time+missbehave_delay, payload, handler)
    else:
        # add an event signifying the end of the transmission of missing blocks
        payload = {
            "request_node": request_node,
            "type": 'local_fast_sync',
            "blocks": missing_blocks,
            "fail": False,
        }

        desynced_node.scheduler.schedule_event(
            desynced_node, time+total_delay, payload, handler)


def handle_local_sync_event(event):
    ''' check for failures and copy missing blocks to end of blockchain and call CP specific resync method '''
    node = event.creator

    if event.payload['fail']:
        # if the previous request failed - try to sync with a random neighbour
        create_local_sync_event(node, sample(
            node.neighbours, 1)[0], event.time)
    else:  # sucessfully synced
        received_blocks = event.payload['blocks']
        # update blockchain with received blocks
        for b in received_blocks:
            # there is a chance the node was updated before this message made it to them
            # so checking to not add repeat blocks
            if b.depth == node.blockchain[-1].depth + 1:
                node.blockchain.append(b)

        # check if the request node has received any new blocks while we were syncing
        if node.last_block.depth < event.payload["request_node"].last_block.depth:
            # if so continue the sync process
            create_local_sync_event(
                node, event.payload["request_node"], event.time)
            return 0

        # adds time of final check
        event.time += Parameters.execution["sync_message_request_delay"]

        # change state to sync
        node.state.synced = True

        # perform the CP specific resync actions
        if received_blocks:
            node.cp.resync(event.payload, event.time)

        # attempt to get any updates
        node.update(event.time)


def apply_sync_missbehaiviour(sender):
    '''
        Checks whether the requesting node is:
            - offline: adds no_respoce delay
            - byzantine: randomly drops message (no_responce delay) or reply with bad data (bad_data delay)
    '''
    # if request_node is dead, sync fails with no delay
    if not sender.state.alive:
        return Parameters.behaiviour["sync"]["no_response"]["delay"], True

    # if the request node is byzantine
    if sender.behaviour.byzantine:
        # roll for missbehave
        roll_missbehave = randint(0, 100)
        if roll_missbehave < sender.behaviour.sync_fault_chance:
            # if missbehave: roll for type
            roll_type = randint(0, 100)
            if roll_type < 50:
                ########### BAD DATA ############
                tools.debug_logs(
                    msg=f"node {sender} sent bad sync data!", col=47)
                delay = Parameters.behaiviour["sync"]["bad_data"]["delay"]
            else:
                ########### NO RESPONSE #########
                tools.debug_logs(
                    msg=f"node {sender} did not respond to sync message!", col=47)
                delay = Parameters.behaiviour["sync"]["no_response"]["delay"]
            return delay, True

    # node will not missbehaive
    return 0, False
