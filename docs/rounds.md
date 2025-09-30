# Round Change Module

This module implements a **generic round-change mechanism** used by consensus protocols that operate in rounds. 
Its purpose is to coordinate nodes when the current round stalls, fails, or otherwise needs to be abandoned, 
so that all honest nodes eventually converge on the same new round.

---

## Core Ideas

Consensus protocols that use rounds (e.g., PBFT, HotStuff, Tendermint) must decide what to do when progress halts. 
The *round-change* process ensures liveness: nodes collect votes for advancing to a new round, adopt a candidate round 
if it gains sufficient support, and start that round when quorum is reached.

---

## Events

- **Round Change Message**  
  Broadcast when a node wants to move to a new round. Payload includes:
  - `type`: `"round_change"`
  - `new_round`: proposed round number
  - `CP`: the consensus protocol instance name

- **Event Handler (`handle_event`)**  
  Dispatches messages to the correct handler based on `payload["type"]`.

---

## State

The round-change state is represented by `RoundChangeState`:

- `round`: current round the node is on  
- `change_to`: the round the node intends to move into (defaults to -1)  
- `votes`: mapping of `round_number -> list of node_ids` that voted for it  

Helper functions:
- `init_round_change_state`: initializes state
- `reset_votes`: clears votes when a new round starts
- `state_to_string`: human-readable snapshot of state

---

## Logic

1. **Initiating a Round Change (`change_round`)**  
   - Node enters `round_change` mode.  
   - Computes next round via `get_next_round`.  
   - Broadcasts a round-change message.  
   - Casts its own vote for the new round.

2. **Processing a Round Change Message (`handle_round_change_msg`)**  
   - Rejects stale or invalid votes.  
   - Counts the vote with `process_round_change_vote`.  
   - If some candidate round reaches `f+1` votes:  
     - Node adopts that round if it is higher than its current `change_to`.  
     - Rebroadcasts a round-change message for the higher round.  
   - If a candidate round reaches `2f+1` votes:  
     - The node starts the consensus protocol at that round.

3. **Vote Tracking (`process_round_change_vote`)**  
   - Ensures each node votes for at most one round, and may replace a smaller vote with a higher one.  
   - Records the vote in the `votes` dictionary.  
   - Returns `"handled"` or `"invalid"` depending on validity.

4. **Choosing the Next Round (`get_next_round`)**  
   - If any round has `f+1` votes, adopt the **highest** such round.  
   - Otherwise, set next round = `current_round + 1`.

---

## Example Flow

1. Node A detects round 5 is stalled. It calls `change_round`, proposing round 6.  
2. Node B also detects the stall and proposes round 6.  
3. Nodes C and D later receive round-change messages. Once **f+1** nodes support round 6, all honest nodes adopt 6.  
4. When **2f+1** nodes support round 6, every node starts round 6 of the consensus protocol.

---

## Key Properties

- **Liveness**: ensures nodes can escape stalled rounds.  
- **Safety**: nodes only move to higher rounds and votes are tracked consistently.  
- **Extensibility**: works with different consensus protocols as long as they support round-based execution.

---

## Notes for Developers

- Ensure voter identity (`node.id`) is used consistently when tracking votes.  
- Quorum checks (`f+1` and `2f+1`) should be `>=` comparisons to handle duplicate votes.  
- `reset_votes` should only be called once a new round has **started**, never earlier.  
- Logging is available for debugging round transitions.

---

This module forms a crucial backbone for any consensus protocol in the simulator that relies on round-based progression.
"""