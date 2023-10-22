from Chain.Parameters import Parameters

import Chain.Consensus.HighLevelSync as Sync
import Chain.Consensus.Rounds as Rounds


def handle_timeout(state, event):
    if event.payload['round'] == state.rounds.round:
        if state.node.update(event.time):
            return 0

        if state.node.state.synced:
            synced, in_sync_neighbour = state.node.synced_with_neighbours()
            if not synced:
                state.node.state.synced = False
                Sync.create_local_sync_event(
                    state.node, in_sync_neighbour, event.time)

        Rounds.change_round(state.node, event.time)
        return "handled"  # changes state to round_chage but no need to handle backlog

    return "invalid"


def schedule_timeout(state, time, add_time=True):
    if add_time:
        time += Parameters.PBFT['timeout']

    payload = {
        'type': 'timeout',
        'round': state.rounds.round,
        'CP': state.NAME
    }

    if state.timeout is not None and Parameters.simulation["remove_timeouts"]:
        state.node.queue.remove_event(state.timeout)

    event = state.node.scheduler.schedule_event(
        state.node, time, payload, state.handle_event)
    state.timeout = event
