from Chain.Parameters import Parameters

import Chain.Consensus.BigFoot.BigFoot_messages as messages
import Chain.Consensus.HighLevelSync as Sync
import Chain.Consensus.Rounds as Rounds


def handle_timeout(state, event):
    if event.payload['round'] == state.rounds.round:
        if event.payload['type'] == "fast_path_timeout":
            time = event.time

            # set fast_path to false and remove TO event
            state.fast_path = False
            state.fast_path_timeout = None

            if not state.node.state.synced:
                # if node is not synced it cannot send any commit messages
                return "handled"

            # In case fast path times out - check if we have enough prepare votes now (if so go to prepared state)
            if state.block is not None and len(state.msgs['prepare']) >= Parameters.application["required_messages"] - 1:
                # change to prepared
                state.state = 'prepared'

                # send commit message
                messages.broadcast_commit(state, time, state.block)

                # count own vote
                state.process_vote('commit', state.node)
                return 'new_state'
        else:
            if event.actor.update(event.time):
                return 0

            if state.node.state.synced:
                synced, in_sync_neighbour = state.node.synced_with_neighbours()
                if not synced:
                    state.node.state.synced = False
                    Sync.create_local_sync_event(
                        state.node, in_sync_neighbour, event.time)

            Rounds.change_round(state.node, event.time)

        # handled because even though we change state to round_chage or new_state there is no need to handle backlog
        return "handled"

    return "invalid"


def schedule_timeout(state, time, add_time=True, fast_path=False):
    if fast_path:
        # set nodes fast_path attribute to True since fast path just started
        state.node.state.fast_path = True

        if add_time:
            time += float(Parameters.BigFoot["fast_path_timeout"])

        if state.fast_path_timeout is not None and Parameters.simulation["remove_timeouts"]:
            state.node.queue.remove_event(state.fast_path_timeout)

        payload = {
            'type': 'fast_path_timeout',
            'round': state.rounds.round,
        }
        event = state.node.scheduler.schedule_event(
            state.node, time, payload, state.handle_event)

        state.fast_path_timeout = event
    else:
        if add_time:
            time += float(Parameters.BigFoot['timeout'])

        if state.timeout is not None and Parameters.simulation["remove_timeouts"]:
            state.node.queue.remove_event(state.timeout)

        payload = {
            'type': 'timeout',
            'round': state.rounds.round,
        }

        event = state.node.scheduler.schedule_event(
            state.node, time, payload, state.handle_event)

        state.timeout = event
