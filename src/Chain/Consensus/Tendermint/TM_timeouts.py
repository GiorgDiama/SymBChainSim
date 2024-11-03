from ...Parameters import Parameters

from ...Consensus import HighLevelSync
from ...Consensus import Rounds


def handle_timeout(state, event):
    # ignore timeout events from other rounds (a timeout at future round should never happen)
    if event.payload['round'] != state.rounds.round:
        return 'invalid'
    
    if state.node.update(event.time):
        return 'changed_protocol'

    if state.node.state.synced:
        synced, in_sync_neighbour = state.node.synced_with_neighbours()
        if not synced:
            state.node.state.synced = False
            HighLevelSync.create_local_sync_event(
                state.node, in_sync_neighbour, event.time)
            return 'detected_desync'
        
    Rounds.change_round(state.node, event.time)
    return "handled"  # changes state to round_change but no need to handle backlog


def schedule_timeout(state, time, add_time=True):
    if add_time:
        time += Parameters.Tendermint['timeout']

    payload = {
        'type': 'timeout',
        'round': state.rounds.round,
        'CP': state.NAME
    }
    
    event = state.node.scheduler.schedule_event(
        state.node, time, payload, state.handle_event)
    
    state.timeout = event
