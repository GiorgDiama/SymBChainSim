# High-Level Sync Module

This module models a **node synchronization mechanism**. It simulates how long it takes for a desynced node 
to catch up with the rest of the network, both for regular blockchain data and configuration chains. Instead of 
modelling every message exchange explicitly, it creates *local events* that approximate the time and effect of a 
full synchronization. This speeds up simulation while preserving timing realism.


## Purpose

Nodes can fall out of sync if they miss blocks or configuration updates.  
The High-Level Sync module ensures that such nodes eventually receive the missing data and rejoin the consensus process.

## SyncingState

`SyncingState` is a temporary consensus protocol (CP) state representing a **desynced node**:

- `NAME`: `"DESYNC"`  
- `state`: string flag (default `"desynced"`)  
- `local_fast_sync_event_data`: event scheduled for data chain sync  
- `local_fast_sync_event_configuration`: event scheduled for configuration chain sync  

Helper methods:
- `state_to_string()`: debugging view of sync state.  
- `ready_to_rejoin()`: returns true if both sync events are completed.


## Events and Handlers

- **Types of events**:  
  - `local_fast_sync`: syncing blockchain data.  
  - `local_fast_sync_configuration`: syncing configuration chain.

- **handler(event)**: routes sync-related events to the correct handler.

- **handle_local_sync_event(event)**: applies missing blockchain blocks, possibly reschedules sync if still behind.  
- **handle_local_sync_event_configuration(event)**: applies missing configuration blocks, reschedules if needed.


## Sync Process

1. **Creating a Sync Event (Data)**  
   - `create_local_sync_event(desynced_node, request_node, time)`  
   - Collects missing blocks from `request_node`.  
   - Simulates per-block delays:  
     - network transmission delay (`Network.calculate_message_propagation_delay`)  
     - validation delay (`block_val_delay`)  
     - sync message overhead (`sync_message_request_delay`)  
   - Schedules a local event when all blocks would have been delivered.  
   - Marks the node as running `SyncingState` if not already.

2. **Creating a Sync Event (Configuration)**  
   - `create_local_sync_event_configuration(desynced_node, request_node, time)`  
   - Same as above but for the configuration chain (`confchain`).

3. **Applying Sync**  
   - When the event is executed, missing blocks are appended to the node’s blockchain or confchain (in configuration_state).  
   - If still behind the request node, another sync event is scheduled.  
   - Once both chains are caught up, the node re-enters the consensus protocol by calling `join_latest_conf`.

## Example Flow

1. Node A discovers it is behind Node B’s blockchain.  
2. `create_local_sync_event` schedules a local sync event for the missing blocks.  
3. When the event triggers, blocks are copied into Node A’s chain.  
4. If A is still behind, another event is scheduled.  
5. Once both blockchain and configuration chains are synced, Node A calls `join_latest_conf` and resumes consensus.


In summary, this module abstracts the complexity of node resynchronization while preserving the key timing and state transitions relevant to consensus behaviour.