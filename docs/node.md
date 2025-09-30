## Node model overview

The Node class models a generic blockchain node in SBS. It encapsulates the local chain state, the active consensus protocol, peer connectivity, behaviour flags, reconfiguration state, and interactions with the simulation engine (events, scheduler, queue). Nodes are designed to be protocol-agnostic at the core, while delegating consensus-specific logic to a pluggable consensus protocol (CP) instance.

### Key responsibilities
- Maintain the local blockchain, memory pool, and runtime state (alive/synced)
- Host the active consensus protocol instance and expose safe hooks for joining/updating it
- Validate incoming blocks against generic rules and configuration depth
- Detect desynchronisation and initiate high-level sync
- Apply configuration updates via the configuration chain
- Interact with the simulation queue to send/receive events

### Core attributes
- `id`: Unique node identifier
- `blockchain`: Local list of blocks (genesis at index 0)
- `pool`: Deque holding pending transactions
- `neighbours`: Peers for gossip/sync checks
- `location`, `bandwidth`: Network placement and link capacity (used by Network)
- `state`: `alive` and `synced` flags
- `cp`: Active consensus protocol instance (`ConsensusProtocol`)
- `behaviour`: Fault/Byzantine behaviour flags and timings
- `backlog`: Future events to be replayed (local to node)
- `queue`: Reference to the simulation event queue
- `reconfiguration_state`: Configuration-chain logic and local config blocks

### Lifecycle and consensus integration
- `join_latest_conf(time)`: Creates the CP specified by the latest configuration block and initialises it with:
  - `time = time`
  - `starting_round = last_block_round + 1`
- `update(time)`: Attempts to adopt a newly synced configuration by delegating to `ReconfigurationState.try_apply_configuration(...)`. Should be called at protocol-defined safe points to avoid mid-round interference.

### Block intake and validation
`validate_block(block)` performs CP-agnostic checks before protocol-specific handling:
- Round check: block round must match `cp.rounds.round`
- Height/depth checks: reject non-advancing or malformed depths; mark gaps as `future_block`
- Configuration checks using `block.extra_data["configuration_depth"]`:
  - `< local conf depth` → `invalid`
  - `> local conf depth` → `future_conf` (triggers config-chain sync elsewhere)
  - `==` → proceed with decision (`valid` or `future_block`)

### Sync detection and high-level sync
- `is_synced_with_neighbours()`: Compares local latest block depth with neighbours; if any neighbour is ahead, returns `(False, node_furthest_ahead)`
- `attempt_sync(time, sync_node=None)`: If desynced, flips `state.synced=False` and schedules a high-level local sync event via `HighLevelSync.create_local_sync_event(...)`. When a node is resurrected, it first tries to fast-sync before rejoining the latest configuration.

### Liveness controls
- `kill()`: Marks node offline (`alive=False`); message/local events are ignored while offline
- `resurrect(time)`: Marks node online and attempts data-chain fast sync; if already in sync, rejoins the latest configuration immediately

### Chain mutation and event handling
- `add_block(block, time, update_time_added=True)`: Appends a verified block, updates `block.time_added` (optional), and removes included transactions from the local pool via `TransactionFactory`
- `add_event(event)`: Enqueues an event if the node is online

### Helpful utilities
- `blockchain_length()`: Number of data blocks excluding genesis
- `ids`, `trunc_ids`: Quick views of local chain
- `last_block`: Convenience accessor for the latest block
- Readable `__repr__`/`__str__` forms for debugging and UI

### In summary
- Consensus protocols (PBFT, Tendermint, BigFoot, etc.) run inside `node.cp` and call `node.update(time)` at safe boundaries to allow configuration adoption.
- High-level sync uses propagation estimates from the Network model (transmission, latency, queueing, processing) to schedule a single local event that applies missing blocks, repeating as needed until up-to-date.
- The configuration chain links data blocks to the configuration in force at creation time via `configuration_depth`, ensuring nodes accept blocks under the correct configuration and kick off configuration sync when needed.

This design keeps the Node generic by placing protocol-specific mechanics in CPs and configuration-chain logic in `ReconfigurationState`, while the Network and Manager components provide propagation timing and system events driving dynamic scenarios.
