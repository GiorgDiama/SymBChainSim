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
    latest_block = desynced_node.last_block
    missing_blocks = [
        b.copy() for b in request_node.blockchain if b.depth > latest_block.depth]

    total_delay = 0

    for i, b in enumerate(missing_blocks):
        delay_network = Network.calculate_message_propagation_delay(
            request_node, desynced_node, b.size)

        delay = delay_network + \
            Parameters.execution["block_val_delay"] + \
            Parameters.execution["sync_message_request_delay"]

        total_delay += delay

        missing_blocks[i].time_added += time + delay

    missbehave_delay, missbehaviour = apply_sync_missbehaiviour(request_node)

    # create local sync event on desynced_node after delay
    if missbehaviour:
        payload = {
            "request_node": request_node,
            "type": 'local_fast_sync',
            "blocks": None,
            "fail": True,
        }

        desynced_node.scheduler.schedule_event(
            desynced_node, time+missbehave_delay, payload, handler)
    else:
        payload = {
            "request_node": request_node,
            "type": 'local_fast_sync',
            "blocks": missing_blocks,
            "fail": False,
        }

        desynced_node.scheduler.schedule_event(
            desynced_node, time+delay, payload, handler)


def handle_local_sync_event(event):
    '''
        check for failures and copy missing blocks to end of blockchain and call CP specific resync method
    '''
    node = event.creator

    if event.payload['fail']:
        # if the previous request failed - request data from a random neighbour
        create_local_sync_event(node, sample(
            node.neighbours, 1)[0], event.time)
    else:
        received_blocks = event.payload['blocks']
        for b in received_blocks:
            # there is a chance the node was updated before this message made it to them
            # so checking to not add repeat blocks
            if b.depth == node.blockchain[-1].depth + 1:
                node.blockchain.append(b)

        # while the node is desynced keep asking for blocks
        if node.last_block.depth < event.payload["request_node"].last_block.depth:
            create_local_sync_event(
                node, event.payload["request_node"], event.time)
            return 0

        # adds time of final check
        event.time += Parameters.execution["sync_message_request_delay"]

        node.state.synced = True

        if received_blocks:
            node.cp.resync(event.payload, event.time)
            # received_blocks[-1].consensus.resync(node, event.payload, event.time)

        if node.update(event.time):
            return 0


def apply_sync_missbehaiviour(sender):
    '''
        Checks whether the requesting node is:
            - offline: adds no response delay
            - byzantine: and randomly drops message or reply with bad data
    '''
    if not sender.state.alive:
        return Parameters.behaiviour["sync"]["no_response"]["delay"], True

    if sender.behaviour.byzantine:
        roll_missbehave = randint(0, 100)
        if roll_missbehave < sender.behaviour.sync_fault_chance:
            roll_type = randint(0, 100)
            if roll_type < 50:
                ########### BAD DATA ############
                tools.debug_logs(
                    msg=f"node {sender} sent bad sync data!", col=47)
                delay = Parameters.behaiviour["sync"]["bad_data"]["delay"]
            else:
                tools.debug_logs(
                    msg=f"node {sender} did not respond to sync message!", col=47)
                ########### NO RESPONSE #########
                delay = Parameters.behaiviour["sync"]["no_response"]["delay"]
            return delay, True
    return 0, False
