# Configuring SymbChainSim simulations

Most of SymbChainSims components are controlled through the configuration yaml files found is the Configs directory. The yaml file is split up into named categories according to the broad area that they control. Specifically these are: simulation, application, execution, data, network, consensus, behaviour, dynamic_sim and reconfiguration.

## simulation
| Parameter           | Default Value | Description                            |
| ------------------- | ------------- | -------------------------------------- |
| `init_CP`           | `"PBFT"`      | Initial consensus protocol (Options: "PBFT", "Tendermint", "BigFoot") |
| `simTime`           | `1800`        | Stop after simulating X seconds (s)       |
| `stop_after_blocks` | `-1`          | Stop after producing X blocks (-1 = no limit) |
| `stop_after_tx`     | `-1`          | Stop after processing X transactions (-1 = no limit) |
| `debugging_mode`    | `False`       | Enable detailed debugging mode (step-by-step event processing) |
| `logging_level`     | `"INFO"`      | Logging verbosity level ("DEBUG" or "INFO") |
| `print_every`       | `100`         | Print simulation progress every N seconds |
| `snapshot_interval` | `30`          | Take snapshots of simulation state every N seconds |
| `print_info`        | `True`        | Print simulation information at the start of execution |

## application

| Parameter               | Default Value | Description                   |
| ----------------------- | ------------- | ----------------------------- |
| `Nn`                    | `16`          | Number of nodes in the blockchain network |
| `workload`              | `'generate'`  | Workload generation mode: 'generate' (based on parameters) or 'path_to_workload_trace' (use transitions from trace) |
| `TI_dur`                | `10`          | Transaction generation interval (every N seconds generate transactions for the next N seconds) |
| `Tn`                    | `180`         | Total number of transactions to generate per second |
| `base_transaction_size` | `0.0016`      | Base size of transactions in MB |
| `Tsize`                 | `0.0008`      | Transaction size variation in MB (standard deviation) |
| `transaction_model`     | `"global"`    | Transaction pool model: "global" (abstracted model with 1 global pool) or "local" (each node gets its own pool) |

## execution

| Parameter                    | Default Value | Description                     |
| ---------------------------- | ------------- | ------------------------------- |
| `creation_time`              | `0.02`        | Time required to create a block (s) |
| `block_val_delay`            | `0.01`        | Time required for block validation (s) |
| `msg_val_delay`              | `0.001`       | Time required to validate a network message (s) |
| `sync_message_request_delay` | `0.1`         | Time required to request missing data from a peer (s) |
| `time_per_tx`                | `0.001`       | Time required to validate each transaction in a received block (s) |
| `proposer_selection`         | `"hash"`      | Proposer selection algorithm: "hash" (pseudorandom based on latest block hash) or "round_robin" |

## data

| Parameter         | Default Value | Description                  |
| ----------------- | ------------- | ---------------------------- |
| `Bsize`           | `1`           | Maximum block size in MB |
| `base_block_size` | `0.002`       | Base block size in MB (excluding transactions) |
| `block_time`      | `0.2`         | Minimum time interval between blocks in seconds |


## network

| Parameter              | Default Value | Description                     |
| ---------------------- | ------------- | ------------------------------- |
| `base_msg_size`        | `0.1`         | Base message size in MB |
| `gossip`               | `True`        | Enable gossip protocol for message propagation (True: cascading peer multicast, False: full network broadcasts) |
| `num_neighbours`       | `6`           | Number of neighbors each node connects to |
| `use_latency`          | `"measured"`  | Latency model: "measured" (based on dataset), "distance" (calculated based on geographical distance), "local" (uses only local model), "off" (no additional delay) |
| `same_city_latency_ms` | `5`           | Latency for nodes in the same city in milliseconds |
| `same_city_dev_ms`     | `0`           | Standard deviation for same-city latency in milliseconds |
| `queueing_delay`       | `0`           | Additional queueing delay in seconds |
| `processing_delay`     | `0`           | Additional processing delay in seconds |

### bandwidth

| Parameter | Default Value | Description               |
| --------- | ------------- | ------------------------- |
| `mean`    | `5`           | Mean bandwidth in Mbps |
| `dev`     | `2`           | Standard deviation of bandwidth in Mbps |
| `min`     | `2`           | Minimum bandwidth in Mbps |
| `sample`  | `'always'`    | Bandwidth sampling frequency: 'always' (sample from distribution always), 'once' (sample once), 'scenario' (never, scenario logic handles network state) |

## consensus

Links the protocol names to a path that contains a specific configuration file for that protocol

| Parameter | Default Value | Description |
| --------- | ------------- | ----------- |
| `BigFoot` | `Chain/Consensus/BigFoot/BigFoot_config.yaml` | Path to BigFoot consensus protocol configuration |
| `PBFT` | `Chain/Consensus/PBFT/PBFT_config.yaml` | Path to PBFT consensus protocol configuration |
| `Tendermint` | `Chain/Consensus/Tendermint/TM_config.yaml` | Path to Tendermint consensus protocol configuration |

## behaviour

| Parameter | Default Value | Description |
| --------- | ------------- | ----------- |
| `use` | `False` | Enable behavioral modeling |
| `config` | `"Configs/behaviour_config.yaml"` | Path to behavior configuration file |
| `print_updates` | `True` | Print behavior updates during simulation |

## dynamic_sim

| Parameter | Default Value | Description |
| --------- | ------------- | ----------- |
| `use` | `False` | Enable dynamic simulation features |
| `config` | `"Configs/dynamic_config.yaml"` | Path to dynamic simulation configuration file |
| `print_updates` | `True` | Print dynamic simulation updates during execution |

## reconfiguration

| Parameter | Default Value | Description |
| --------- | ------------- | ----------- |
| `reconfigure` | `True` | Enable reconfiguration of blockchain system |
| `reconfiguration_interval` | `300` | How often to reconfigure the system (seconds) |
| `reconfiguration_interval_range` | `[-20,20]` | Range used to randomly change the interval duration (seconds) |
| `conf_block_size` | `0.25` | Block size of produced configuration blocks in MB |
| `reconfiguration_method` | `'random_centralised'` | How to reconfigure the system: "random_centralised" (randomly picks configuration from random_configuration) |
| `random_configuration` | `{protocols: ["PBFT", "BigFoot", "Tendermint"], block_sizes: [0.5, 1, 2, 5, 10], block_times: [0.1, 0.2, 0.5, 1, 2]}` | List of configuration parameters used to randomly reconfigure the blockchain |
| `propagation.model` | `True` | Controls whether configuration block is instantly added (False) or propagated with delay (True) |
| `propagation.delay` | `[0.02, 0.1]` | Delay range for configuration block propagation (seconds) |
| `propagation.per_cent_nodes` | `0.25` | Percentage of nodes that initially receive the configuration block |
| `print_updates` | `True` | Controls printing the details of the reconfiguration |