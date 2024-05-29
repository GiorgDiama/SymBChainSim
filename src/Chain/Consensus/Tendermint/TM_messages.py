from Chain.Parameters import Parameters
from sys import getsizeof

def schedule_propose(state, time):
    payload = {
        'type': 'propose',
        'round': state.rounds.round,
        'CP': state.NAME
    }

    event = state.node.scheduler.schedule_event(
        state.node, time, payload, state.handle_event)

    return event

def broadcast_pre_prepare(state, time, block):
    payload = {
        'type': 'pre_prepare',
        'block': block,
        'round': state.rounds.round,
        'CP': state.NAME
    }

    payload['net_msg_size'] = get_payload_size(payload)

    event = state.node.scheduler.schedule_broadcast_message(
        state.node, time, payload, state.handle_event)
    
    return event

def broadcast_prepare(state, time, block_hash):
    payload = {
        'type': 'prepare',
        'block_hash': block_hash,
        'round': state.rounds.round,
        'CP': state.NAME
    }

    payload['net_msg_size'] = get_payload_size(payload)

    event = state.node.scheduler.schedule_broadcast_message(
        state.node, time, payload, state.handle_event)
    
    return event


def broadcast_commit(state, time, block_hash):
    payload = {
        'type': 'commit',
        'block_hash': block_hash,
        'round': state.rounds.round,
        'CP': state.NAME
    }

    payload['net_msg_size'] = get_payload_size(payload)

    event = state.node.scheduler.schedule_broadcast_message(
        state.node, time, payload, state.handle_event)

    return event

def get_payload_size(payload):
    size = Parameters.network["base_msg_size"]

    for key in payload:
        match key:
            case "block":
                size += payload[key].size + Parameters.Tendermint['base_block_size'] / 1e6
                # size += Parameters.Tendermint['base_block_size'] / 1e6
            case "block_hash":
                size += Parameters.Tendermint['hash_size'] / 1e6
            case _:
                size += float(getsizeof(payload[key]) / 1e6)

    return size