'''
    Models a high-level sync functionality. Calculates how long it would take for the node to receive the data
    (missing blocks) and creates a local event which copies the missing blocks to the de-synced node saving communication
    events
'''
from ..Network import Network
from ..Parameters import Parameters

from random import sample


def handler(event):
    if event.payload["type"] == "local_fast_sync":
        return handle_local_sync_event(event)
    else:
        return "unhandled"

def create_local_sync_event(desynced_node, request_node, time):
    '''
        Gets missing blocks from request node
        Request node: node from which we request missing blocks
            examples: 
                - the node whose message made us aware that we are de-synced
                - the peer with the longest chain)
        Calculates transmission + validation delay and creates a local sync event (local event of the desynced node) at the moment in time when the sync processes would have finished
    '''
    # get the last block of de-synced node
    latest_block = desynced_node.last_block

    # find missing blocks in blockchain of request_node
    missing_blocks = []
    for b in reversed(request_node.blockchain):
        if b.depth > latest_block.depth:
            # TODO: Insert is o(n) ... append o(1) and reverse 
            missing_blocks.insert(0, b.copy())
        else:
            break
        
    # take into account a static delay for sending the sync message
    total_delay = Parameters.execution['sync_message_request_delay']

    # for each missing block
    for i, b in enumerate(missing_blocks):
        # calculate the transmission delay + validation delay for the block
        delay_network = Network.calculate_message_propagation_delay(
            request_node, desynced_node, b.size)

        delay = delay_network + \
            Parameters.execution["block_val_delay"] + \
            Parameters.execution["sync_message_request_delay"]

        # add the delay of the current block to the total delay
        total_delay += delay

        # update the time added for the block and mark it as a 'synced' block
        missing_blocks[i].time_added = time + total_delay
        missing_blocks[i].extra_data['synced'] = True

    # schedule the sync event
    payload = {
        "request_node": request_node,
        "type": 'local_fast_sync',
        "blocks": missing_blocks,
        "fail": False,
    }

    desynced_node.scheduler.schedule_event(
        desynced_node, time+total_delay, payload, handler)


def handle_local_sync_event(event):
    '''
        Copies missing blocks to end of the callers blockchain. 
        Additionally, checks if the node we are syncing with has received any blocks while we were waiting for the currents once
            If so, also requests the new blocks through another local_sync_event
        Relies on calling the CP specific rejoin method for the node to rejoin the consensus process 
    '''
    node = event.creator

    if event.payload['fail']:
        # if the previous request failed - try to sync with a random neighbour
        create_local_sync_event(node, sample(
            node.neighbours, 1)[0], event.time)
        return 'sync_failed'
    
    # successfully synced
    received_blocks = event.payload['blocks']
    # update blockchain with received blocks
    for b in received_blocks:
        # there is a chance the node was updated before this message made it to them
        # checking depth to prevent adding repeat blocks
        if b.depth == node.blockchain[-1].depth + 1:
            node.add_block(b, -1, update_time_added=True)

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
    node.cp.rejoin(event.time)

    return 'successfully_synced'