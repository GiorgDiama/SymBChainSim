'''
    Hanldes the logic for consensus rounds
'''
from types import SimpleNamespace
from Chain.Parameters import Parameters


def round_change_state(round=0):
    '''
        Rounc chage state
    '''
    return SimpleNamespace(
        round=round,
        change_to=-1,
        votes={}
    )


def state_to_string(node):
    '''
        returns the state of *node* as a string
    '''
    s = f"round: {node.cp.rounds.round} | change_to: {node.cp.rounds.change_to} | round_votes: {node.cp.rounds.votes}"
    return s


def reset_votes(node):
    '''
        resets round change votes of node
    '''
    node.cp.rounds.votes = {}


def handle_event(event):
    '''
        handles round change events
    '''
    if event.payload['type'] == "round_change":
        handle_round_change_msg(event)


def change_round(node, time):
    '''
        Begins the round change process in *node*
    '''
    node.cp.init_round_chage(time)
    state = node.cp

    state.state = 'round_change'

    new_round = get_next_round(node)

    state.rounds.change_to = new_round

    payload = {
        'type': 'round_change',
        'new_round': new_round,
        'CP': node.cp.NAME
    }

    node.scheduler.schedule_broadcast_message(
        node, time, payload, handle_event)


def handle_round_change_msg(event):
    node = event.receiver
    time = event.time
    new_round = event.payload['new_round']
    state = node.cp

    msgs = state.rounds.votes

    if state.rounds.round >= new_round:
        return 'invalid'

    if ret := count_round_change_vote(node, new_round, event.creator) == 'invalid':
        return ret

    if (len(msgs[new_round]) == Parameters.application["f"]+1) and (new_round > state.rounds.change_to):
        state.state = 'round_change'
        state.rounds.change_to = new_round

    if len(msgs[new_round]) == Parameters.application["required_messages"] - 1:
        # if a node receives enough round messages to change round and has not send a round change message in the past
        # send message (the node wants to change round since majority wants to change round)
        state.rounds.change_to == new_round
        change_round(node, time)

        node.cp.start(new_round, time)
        return "handled"


def get_next_round(node):
    change_msgs = node.cp.rounds.votes

    new_round_candidates = [
        x for x in change_msgs.items() if len(x[1]) >= Parameters.application["f"]]

    if new_round_candidates:
        largest_proposed = max(new_round_candidates, key=lambda x: x[0])[0]
        own = node.cp.rounds.round + 1
        return max(largest_proposed, own)

    return node.cp.rounds.round + 1


def count_round_change_vote(node, new_round, voter):
    msgs = node.cp.rounds.votes

    for key in msgs:
        # check if the voter has voted for some other round
        if any([x == voter for x in msgs[key]]):
            if key < new_round:  # if the voter voted for a smaller round then vote is removed from that
                msgs[key].remove(voter)
            else:  # else vote is not valid
                return 'invalid'

    # count vote
    if new_round in msgs.keys():
        msgs[new_round] += [voter]
    else:
        msgs[new_round] = [voter]

    return "handled"
