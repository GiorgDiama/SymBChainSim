'''
    Handles the logic used by nodes to agree on a new round when they detect the current round has failed
'''
from types import SimpleNamespace
from ..Parameters import Parameters

############### EVENTS ###############

def broadcast_round_change_message(node, new_round, time):
    payload = {
        'type': 'round_change',
        'new_round': new_round,
        'CP': node.cp.NAME
    }

    node.scheduler.schedule_broadcast_message(
        node, time, payload, handle_event)
    
############### STATE  ###############

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
    node.cp.rounds.votes = {}

def state_to_string(node):
    return f"round: {node.cp.rounds.round} | change_to: {node.cp.rounds.change_to} | round_votes: {node.cp.rounds.votes}"

def handle_event(event):
    match event.payload['type']:
        case "round_change":
            handle_round_change_msg(event)
        case _:
            raise ValueError(
                f"Event '{event.payload['type']}' was not handled by its own handler...")

############### LOGIC ###############

def change_round(node, time):
    '''
        Begins the round change process in *node*. Specifically, changes the node CP state  to 'round_change'
        and broadcasts 'round_change' message for new_round (new_round is decided by get_next_round)
    '''
    # executes protocol specific actions that might be required when entering round change mode
    node.cp.init_round_change(time) 

    # sets node CP state to 'round_change' - usually has the effect of making the node ignore protocol messages
    node.cp.state = 'round_change'

    # calculate what the new round we should be changing into is
    new_round = get_next_round(node)
    node.cp.rounds.change_to = new_round
    
    broadcast_round_change_message(node, new_round, time)
    process_round_change_vote(node, new_round, node) # count own vote
  

def handle_round_change_msg(event):
    '''
        Logic to handle received round_change messages:
            if the vote makes a candidate round > our chosen new_round have f+1 votes
                - adopt that candidate round and broadcast round_change message for that round
            if 'new_round' receives 2f+1 votes:
                start a new concuss round at round 'new_round' 
    '''
    
    node = event.receiver
    time = event.time
    new_round = event.payload['new_round']
    cp_state = node.cp

    msgs = cp_state.rounds.votes

    # ignore messages voting for a round lower than the current round
    if cp_state.rounds.round >= new_round:
        return 'invalid'

    # try to count the vote (if message contains an invalid vote return)
    if (ret := process_round_change_vote(node, new_round, event.creator)) == 'invalid':
        return ret
    
    if (len(msgs[new_round]) == Parameters.application["f"]+1):
        if cp_state.state != 'round_change':
            # if the node is not in 'round_change' - start the round change process on node
            change_round(node, time)
        if new_round > cp_state.rounds.change_to:
            # if the node has realised that a higher 'new_round' has received f+1 nodes - change 'new_round' and broadcast round_change for 'new_round'
            cp_state.rounds.change_to = new_round
            broadcast_round_change_message(node, new_round, time)
            process_round_change_vote(node, new_round, node) # count own vote
            
    # if a node receives 2f+1 round messages for a specific round change to that round
    if len(msgs[new_round]) == Parameters.application["required_messages"]:
        node.cp.start(new_round, time)
    
    return "handled"
    
def get_next_round(node):
    '''
        Logic for nodes to decide which round should be 'next_round'
            if any rounds have received f+1 votes 
                next round: highest round among rounds with f+1 votes
            otherwise:
                next round: current_round + 1
    '''
    change_msgs = node.cp.rounds.votes

    # get all new_round candidates that have f+1 votes
    new_round_candidates = [round for round, votes in change_msgs.items() 
                            if len(votes) >= Parameters.application["f"]+1]
    
    # if any candidate round numbers have received f+1 votes adopt the max round
    if new_round_candidates:
        return max(new_round_candidates)

    # otherwise new_round = current_round + 1
    return node.cp.rounds.round + 1

def process_round_change_vote(node, new_round, voter):
    '''
        Logic that keeps track of votes for new_rounds
            If no record of the voter voting then:
                record the vote
            If the votes has voted for a round < current_vote (new_round)
                delete the old vote and record the new one
            else:
                vote is invalid
    '''
    msgs = node.cp.rounds.votes
    voter = voter.id

    for key, value in msgs.items():
        # check if the voter has voted for some other round
        if voter in value:
            if key < new_round:  # if the voter voted for a smaller round then vote is removed from that
                msgs[key].remove(voter)
            else:  # voter is voting for an earlier round than its last vote
                return 'invalid'

    # record valid vote
    msgs[new_round] = msgs.get(new_round, []) + [voter]

    return "handled"