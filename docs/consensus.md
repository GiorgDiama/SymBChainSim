# Consensus Protocols in SymbChainSim

The consensus process is the heart of the blockchain system. It is this process that governs block production through decentralised consensus. As a result, accurately capturing the dynamics of the consensus process in key to a fidel blockchain model. 

Besides accuracy, another critical consideration is modularity and extensibility. With SBS being designed for blockchain management, a modular and extensible consensus model allows for both easy reconfiguration and an easily extensible solution space.

### Model fidelity

To ensure the dynamics of consensus protocols are captured as accurately as possible, SBS takes a very low abstraction to modelling the consensus process. This means the following:

- All message exchanges are modelled as events
- Abstraction at a significant cost of accuracy is avoided 

Abstractions that sacrifice little in accuracy for a big increase in efficiency are most welcome and should be made to ensure the simulation can execute faster-than-real-time (FTRT).

### Modularity

Reconfiguration and runtime adaptation of the simulation benefit greatly from a modular approach to modelling. Keeping models and their logic self contained and enforcing minimal connections between the models ensures that adaptation affects the rest of the models as little as possible.

A core example of this is separating the consensus state from the node state (most existing simulators have the node and consensus logic mixes; a reasonable approach but one that complicated reconfiguration). 

## The ConsensusProtocol abstract class

The `ConsensusProtocol` abstract class introduces all the necessary methods a round based consensus protocol requires. Specifically, `ConsensusProtocol` models the state of a node in the modelled blockchain and contains logic to propose and validate blocks, and general auxiliary logic necessary for the consensus process. 

Specifically, protocols implementing `ConsensusProtocol` require the following method implementation:

- `__init__(node)`: Initializes the consensus protocol instance for a given node.
    - This method defines the state variables of the modelled protocol

- ``set_state()``  
  Resets or initializes the internal state variables of the protocol. Used to prepare the protocol for a fresh start or recovery.  

- ``validate_message(event)``  
  Checks whether an incoming message is valid for the current protocol state. Returns a tuple `(is_valid, action)`, where `action` can be `None` or `"backlog"` if the message should be deferred.  

- ``validate_block(block, time)``  
  Determines if a proposed block is valid according to the rules of the protocol.
    - general validity is also checked through a node specific method (see `Chain.Consensus.PBFT_state.validate_block(...)`)

- ``init(time, starting_round)``  
  Initializes the consensus protocol and starts the first round at the given time and round index.  

- ``start(time, starting_round)``  
  Starts a new consensus round and returns the round number.  

- ``init_round_change(time)``  
  Handles logic for initiating a round change when the current round cannot progress.  

- ``rejoin(time)``  
  Defines the behavior of a node rejoining the protocol after being offline, ensuring it synchronizes with the current state of the network.  

- ``handle_event(event)`` *(static)*  
  Processes protocol-specific events and returns the outcome as a string.  

## Transitions

Consensus protocols in SymbChainSim are modeled as **finite state machines (FSMs)**. Each protocol implementation defines the valid states of a node (in a class implementing `ConsensusProtocol` if a round based protocol), the transitions between those states, and the messages/events that trigger those transitions ( (usually in a separate python files).  

All transitions are explicit and modeled as **simulation events**. This ensures that the passage of time, message delays, and asynchronous execution are captured.  

## Example: PBFT 

PBFT (Practical Byzantine Fault Tolerance) is one of the provided consensus protocols. Its operation can be described in terms of **phases**:

1. **Propose phase** (`propose`)  
   - The designated miner (proposer) for the round attempts to create a new block.  
   - If successful, it transitions to `pre_prepared` and broadcasts a `pre_prepare` message to the network.  
   - If unsuccessful (no transactions available), it may reschedule the propose attempt within the same round if time permits.  

2. **Pre-prepare phase** (`pre_prepare`)  
   - Nodes receive the proposed block.  
   - They validate the block and, if valid, transition from `new_round` to `pre_prepared`.  
   - At this point, each node broadcasts a `prepare` message and logs its vote.  

3. **Prepare phase** (`prepare`)  
   - Nodes collect `prepare` messages from others.  
   - Once a node gathers a sufficient number of `prepare` votes (≥ `2f` where `f` is the number of tolerated Byzantine faults), it transitions to the `prepared` state.  
   - Upon reaching `prepared`, the node broadcasts a `commit` message.  

4. **Commit phase** (`commit`)  
   - Nodes collect `commit` messages.  
   - Once a node gathers a sufficient number of `commit` votes (≥ `2f + 1`), the block is finalized.  
   - The block is appended to the node’s blockchain, and the node transitions to the next round (`new_round`).  
   - If the node was the proposer, it also broadcasts the finalized block.  

5. **Round change phase** (`timeout` / `round_change`)  
   - If progress stalls (e.g., insufficient votes or missing proposals), a timeout is triggered.  
   - The node transitions into `round_change` state and initiates the next consensus round.  
   - Round changes prevent deadlocks and ensure eventual consensus.  

6. **Rejoin**  
   - Nodes that were offline rejoin by syncing to the latest block and starting consensus from the next round.  
   - This ensures resilience against temporary network failures.  


### PBFT Protocol State

The PBFT implementation in SymbChainSim tracks the following **state variables** for each node:

- `rounds`  
  Stores the current round number and round-change metadata.  

- `state`  
  The protocol state of the node (`new_round`, `pre_prepared`, `prepared`, `committed`, `round_change`).  

- `miner`  
  The designated proposer for the current round, determined by the configured proposer selection algorithm.  

- `msgs`  
  A dictionary tracking received messages of types `prepare` and `commit`. Used to count votes.  

- `timeout`  
  Reference to the timeout event for the current round. If consensus stalls, this is used to trigger a round change.  

- `block`  
  The current proposed block being processed in the round.  

- `node`  
  A back-reference to the parent `Node` object for access to node-level state and logic.  

### Timeouts

Timeouts are essential to guarantee **liveness**.  
- Each round schedules a timeout event.  
- If the timeout expires without reaching consensus, the node transitions to `round_change`.  
- Timeouts are adaptive, and the configuration (`PBFT_config.yaml`) defines the base timeout duration.  

Timeout handling ensures the protocol does not stall indefinitely even in the presence of faulty or malicious nodes.  


### Messages

All messages in SymbChainSim are modeled as **simulation events**. PBFT defines four primary message types:

- `propose` – Internal event for block proposal.  
- `pre_prepare` – Broadcast of a proposed block.  
- `prepare` – Broadcast vote on a proposed block.  
- `commit` – Broadcast final vote to commit the block.  
- `new_block` – Broadcast of a finalized block by the proposer.  

Each message carries metadata such as:
- The round number.  
- The consensus protocol identifier (`CP`).  
- The block being voted on (when applicable).  

By modeling these as events, the simulator captures **message delays, ordering, and network effects**.  

### Proposer Selection

The proposer (or leader) is responsible for initiating block proposals in each round.  
SymbChainSim supports multiple proposer selection mechanisms:

- **Round robin**  
  `miner = round_number mod N`  
  where `N` is the number of nodes.  

- **Hash-based**  
  `(last_block_hash + round_number) mod N`  
  This ties proposer selection to blockchain state, ensuring randomness and fairness.  

The selection algorithm is defined in the global `Parameters.execution["proposer_selection"]`.  

## Summary

The consensus model in SymbChainSim emphasizes:
- **Accuracy**: Low-abstraction, event-driven modeling of consensus.  
- **Extensibility**: Protocols are modular and self-contained.  

By capturing the full state machine dynamics of consensus protocols, SymbChainSim provides a powerful platform for studying blockchain consensus. 