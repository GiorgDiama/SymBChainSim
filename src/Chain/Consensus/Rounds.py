'''
    Handles the logic for consensus rounds
'''
from types import SimpleNamespace
from Chain.Parameters import Parameters


def round_change_state(round=0):
    '''
        Round change state
            round: current round the node is on
            change_to: (default -1) denotes the round number the node wants to change to
            votes: stores round_change votes from other nodes
    '''
    return SimpleNamespace(
        round=round,
        change_to=-1,
        votes={}
    )

def reset_votes(node):
    '''
        resets round change votes of node
    '''
    node.cp.rounds.votes = {}


def handle_event(event):
    '''
        handles round change events
    '''
    match event.payload['type']:
        case "round_change":
            handle_round_change_msg(event)
        case _:
            raise ValueError(
                f"Event '{event.payload['type']}' was not handled by its own handler...")

def change_round(node, time):
    '''
        Begins the round change process in *node*
    '''
    node.cp.init_round_change(time)
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
    '''
        Logic to handle received round_change messages
    '''
    node = event.receiver
    time = event.time
    new_round = event.payload['new_round']
    state = node.cp

    msgs = state.rounds.votes

    # ignore messages voting for a round lower than the current round
    if state.rounds.round >= new_round:
        return 'invalid'

    # try to count the vote (if message contains an invalid vote return)
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
    '''
        analyses the received round changes messages to figure out which round should be 'next_round'
            if 1/3+1 of the nodes have votes for a round higher than ours:
                next round: that round
            otherwise:
                next round: current_round + 1
    '''
    change_msgs = node.cp.rounds.votes

    new_round_candidates = [
        x for x in change_msgs.items() if len(x[1]) >= Parameters.application["f"]]

    if new_round_candidates:
        largest_proposed = max(new_round_candidates, key=lambda x: x[0])[0]
        own = node.cp.rounds.round + 1
        return max(largest_proposed, own)

    return node.cp.rounds.round + 1


def count_round_change_vote(node, new_round, voter):
    '''
        implements logic that counts votes received from other nodes
    '''
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

def state_to_string(node):
    '''
        returns the round change state of *node* as a string
    '''
    return f"round: {node.cp.rounds.round} | change_to: {node.cp.rounds.change_to} | round_votes: {node.cp.rounds.votes}"
