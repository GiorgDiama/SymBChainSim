# SymbChainSims approach to reconfiguration

Modeling dynamic reconfiguration is core to SBS due to dynamic blockchain management being one of the tools core use cases. SBS utilises the same ideas for dynamic updating of the blockchain conditions to reconfiguration. However, reconfiguration in SBS is not abstracted (as simple simulation state updated) it is modeled as a mechanism of the blockchain system allowing SBS to capture the dynamics of the reconfiguration and their interactions with the systems conditions.

## Reconfiguration mechanism

To model reconfiguration the idea of a configuration chain is introduced and modeled in SBS. Briefly, the configuration chain is a utility, secondary blockchain that consists of configuration blocks. Configuration blocks are typical blockchain blocks that, instead of transactions included system configurations. This mechanisms enables linking the configuration of the blockchain nodes to the latest block in the nodes configuration chain.

The above has numerous benefits:
- It allows modeling the propagation and reconfiguration of nodes through modeling the propagation of configuration blocks
- As a blockchain structure, its immutable and transparent nature allows linking data blocks to configuration blocks immutably. This ensures the main chain will remain verifiable and can simplifies block validation under  reconfiguration
- Finally, as a blockchain structure it can be constructed in a decentralised manner ensuring the management process does not violate the decentraliation properties of the underlying blockchain system.

More information about this can be found in the following publication proposing the approach:

> Cite AsiaSim paper when online

## Modeling in SBS

This section briefly described how the above is modeled in SBS.

Initially the node model is updated with a configuration chain. The initial configuration of the blockchain is in the genesis block (this is the case even when reconfiguration is not used; the configuration chain simply never get any new blocks). The node model also gets the updated method, which when called, checks whether any new blocks were added in the local configuration blockchain and updates the configuration of the node. The update process asynchronous (meaning that new blocks do not immediately trigger reconfiguration) to prevent disrupting ongoing consensus rounds. Thus, when modeling new consensus protocols it is at the discretion of the developer to call node.update() at times when doing so is generally safe (after new blocks, timeouts, end of rounds etc..). For an example see any of the implemented protocols.

To model the dynamics of reconfiguration, the future_receive_configuration event is added, which when triggered, models a configuration block arriving at the node. The node then validates it, request any missing configuration blocks before it, and gossips the block to its peers that do the same. With the new block added to their blockchain nodes will eventually adopt the new configuration when update is called.

As a blockchain, the logic for synchronising and validating configuration blocks remains largely unchanged. 

Furthermore, in a reconfigurable blockchain validating data blocks required ensuring the block was produced under the latest configuration. This is achieved by linking configuration blocks to data blocks (with hash references)


## Implementation details

### Overview

SBS models reconfiguration via a secondary configuration blockchain. Nodes adopt configuration updates asynchronously by syncing the configuration chain, then switching their consensus protocol/state at safe points. The main participating components are:

- `Parameters.global_configuration_chain`: manager-side configuration chain tracking the global state of the configuration chain
- `Chain.Reconfiguration.ConfigurationBlock`: configuration block data model
- `Chain.Reconfiguration.ReconfigurationState`: node-local configuration chain, validation, adoption, gossip/sync
- `Chain.Consensus.HighLevelSync`: extending with logic to handle syncing configuration chain
- `Chain.Node`: applies/validates configuration, coordinates sync, and transitions consensus protocol
- `Manager.SystemEvents.ReconfigurationEvents`: emits reconfiguration decisions and kicks off propagation
- `Manager.Manager`: enables scheduling of reconfiguration events based on `base.yaml`

### Data model and linkage

- **Configuration blocks** (`ConfigurationBlock`) carry a configuration payload (e.g., new CP, `block_time`, `block_size`) and standard block metadata: `depth`, `id`, `previous`, `proposer`, `size`, timestamps, and `extra_data`.
- Each data block produced under consensus includes a reference to the configuration depth it was created under via `block.extra_data["configuration_depth"]`. Validation in `Node.validate_block(...)` enforces:
  - Reject if the block uses an older configuration than the local latest
  - Treat as future if it references a configuration ahead of the local node, triggering configuration sync

### Node bootstrap and adoption

- On node creation, `Node.reconfiguration_state = ReconfigurationState(self)` initialises an empty local configuration chain.
- To start or after reconfig, nodes enter `join_latest_conf(time)` which:
  - Reads the latest configuration (`CP`) from `reconfiguration_state.confchain[-1]`
  - Instantiates the appropriate CP class from `Parameters.CPs`
  - Calls `cp.init(time=time, starting_round=last_block_round + 1)` to resume safely
- Nodes opportunistically call `node.update(time)` from protocol states at safe boundaries to try applying a newly synced configuration (`ReconfigurationState.try_apply_configuration(...)`). This decouples block processing from configuration changes.

### Syncing: data and configuration chains

- When a node detects it is behind on the data chain (`Node.attempt_sync(...)`, `Node.is_synced_with_neighbours()`), it transitions into a temporary syncing state (`HighLevelSync.SyncingState`) and schedules a local fast-sync event that models network + validation costs without simulating every message.
- There are two symmetric sync paths handled in `HighLevelSync`:
  - `create_local_sync_event(...)` / `handle_local_sync_event(...)` for data blocks
  - `create_local_sync_event_configuration(...)` / `handle_local_sync_event_configuration(...)` for configuration blocks
- Both paths:
  - Compute missing blocks by comparing local `depth` to a peer
  - Estimate total delay as network propagation + validation + request overheads using `Network.calculate_message_propagation_delay(...)` and `Parameters.execution` constants
  - Schedule a single local event at `time + total_delay` that applies the copied blocks to the local chains
  - If still behind at application time, schedule another sync
  - Only when both data and configuration syncs complete does the node rejoin consensus via `node.join_latest_conf(...)`

### Configuration validation during block intake

When a data block arrives, `Node.validate_block(...)` performs generic checks (round, height) and configuration checks:

- `block.extra_data["configuration_depth"] < local_conf_depth` → invalid
- `block.extra_data["configuration_depth"] > local_conf_depth` → future configuration, trigger configuration-chain sync
- `==` and other checks pass → valid or future data block depending on height

This ensures data blocks are only accepted under the correct configuration.

### Centralised reconfiguration flow

1. The `Manager` schedules periodic reconfiguration system events via `ReconfigurationEvents.schedule_reconfiguration_event(...)` using:
   - Interval duration: `Parameters.reconfiguration.reconfiguration_interval`
   - Random range: `reconfiguration_interval_range`
2. On event, `handle_random_centralised_reconfiguration_event(...)` chooses a configuration from `random_configuration` in `base.yaml` and appends a new `ConfigurationBlock` to `Parameters.global_configuration_chain`.
3. Propagation is modeled according to `reconfiguration.propagation`:
   - If `model=True`, only a random subset of nodes (controlled by `per_cent_nodes`) receive the new configuration block after a random delay in `delay=[min,max]`. Delivery schedules `node.reconfiguration_state.schedule_future_receive_configuration(block.copy(), time=...)`, after which nodes gossip/sync to converge.
   - If `model=False`, the manager instantly appends the new block to the configuration chains of all nodes.
4. After reception, nodes eventually call `node.update(time)` at safe points to apply the latest configuration and re-initialise the CP.

### Scheduling and parameters

- All reconfiguration timings and costs are governed by `base.yaml`:
  - `reconfiguration.*`: interval, random ranges, propagation fraction, conf block size, printing
  - `execution.*`: latency of validation and message requests used in high-level sync delay calculations
  - `network.*`: bandwidth/latency model used by `Network.calculate_message_propagation_delay(...)`

### Failure and recovery

- When a node is resurrected (`Node.resurrect(...)`), it attempts fast sync. If sync is not needed it directly rejoins the latest configuration (`join_latest_conf`).
- During sync, the node remains out of consensus until both chains are caught up.

### Extending the mechanism (skeleton)

To add a new reconfiguration approach:

1. Decision production
   - Create a system event handler that emits reconfiguration decisions and produces a `ConfigurationBlock` candidate.

2. Block validation and linking
   - Ensure configuration blocks are validated similarly to data blocks (depth continuity, `previous`, proposer rules, signatures if modeled).
   - Keep `block.extra_data["configuration_depth"]` linkage in data blocks.

3. Propagation model
   - Modify the existing propagation model by selecting the initial receiver nodes and the propagation strategy
   - Reuse `HighLevelSync.create_local_sync_event_configuration(...)` for catch-up after late arrivals.

4. Adoption policy
   - Decide and document when `node.update(time)` is safe to call in your CP (e.g., end-of-round, after commit). Invoke it accordingly.

5. Parameters
   - Add a dedicated section under `reconfiguration` in `base.yaml` for your method’s tunables (e.g., quorum size, committee rotation period, signature sizes).

6. Modeling effects of reconfiguration
    - Change existing models (CP, Node, Network etc..) to be configured by the configuration blocks instead of Parameters

## Supported reconfiguration

Currently only centralised (and random) reconfiguration is supported. Although the random part can be easily changed by incorporating various optimisation approaches (heuristics, machine learning, RL, traditional optimisation etc..).

The decentralised version utilising a secondary blockchain for decentralsised agreement on decisions will be added soon.

### Instrumenting the blockchain system to feed the optimisation process

Due to blockchain's  decentralised nature and Byzantine assumptions extracting the state of the blockchain network is non-trivial. Although the existence of the simulation state trivialises state extraction such approaches are not realistic. An approach for blockchain network state extraction is proposes in:

> Diamantopoulos, Georgios, Nikos Tziritas, Rami Bahsoon, Nan Zhang, and Georgios Theodoropoulos. "Dynamic Digital Twins of Blockchain Systems: State Extraction and Mirroring." In 2024 28th International Symposium on Distributed Simulation and Real Time Applications (DS-RT), pp. 26-33. IEEE, 2024.

An implementation of the above approach is expected to be added in the simulator soon.
