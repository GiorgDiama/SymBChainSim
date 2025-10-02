# Configuring SymbChainSim simulations

Most of SymbChainSim’s components are controlled through the configuration yaml files found in the `Configs` directory. The yaml file is split into named categories according to the broad area they control. Specifically these are: `simulation`, `application`, `execution`, `data`, `network`, `consensus`, `behaviour`, `dynamic_sim`, and `reconfiguration`.

## simulation
| Parameter           | Description |
| ------------------- | ----------- |
| `init_CP`           | Initial consensus protocol at simulation start (Options: "PBFT", "Tendermint", "BigFoot") |
| `simTime`           | Stop simulation after this many seconds (-1 = no limit) |
| `stop_after_blocks` | Stop after this many blocks are produced (-1 = no limit) |
| `stop_after_tx`     | Stop after this many transactions are processed (-1 = no limit) |
| `debugging_mode`    | Enable detailed debugging mode (step-by-step event processing) |
| `logging_level`     | Logging verbosity level ("DEBUG" or "INFO") |
| `print_every`       | Print simulation progress every N seconds |
| `snapshot_interval` | Take snapshots of simulation state every N seconds |
| `print_info`        | Print simulation information at the start of execution |

## application
| Parameter               | Description |
| ----------------------- | ----------- |
| `Nn`                    | Number of nodes in the blockchain network |
| `workload`              | Workload generation mode: `'generate'` (parameter based) or `'path_to_workload_trace'` (trace-based) |
| `TI_dur`                | Transaction generation interval (every N seconds generate transactions for the next N seconds) |
| `Tn`                    | Total number of transactions to generate per second |
| `base_transaction_size` | Base size of transactions in MB |
| `Tsize`                 | Transaction size variation in MB (standard deviation) |
| `transaction_model`     | Transaction pool model: `"global"` (one pool) or `"local"` (each node has its own pool) |

## execution
| Parameter                    | Description |
| ---------------------------- | ----------- |
| `creation_time`              | Time required to create a block (s) |
| `block_val_delay`            | Time required for block validation (s) |
| `msg_val_delay`              | Time required to validate a network message (s) |
| `sync_message_request_delay` | Time required to request missing data from a peer (s) |
| `time_per_tx`                | Time required to validate each transaction in a received block (s) |
| `proposer_selection`         | Proposer selection algorithm: `"hash"` (based on latest block hash) or `"round_robin"` |

## data
| Parameter         | Description |
| ----------------- | ----------- |
| `Bsize`           | Maximum block size in MB |
| `base_block_size` | Base block size in MB (excluding transactions) |
| `block_time`      | Minimum time interval between blocks in seconds |

## network
| Parameter              | Description |
| ---------------------- | ----------- |
| `base_msg_size`        | Base message size in MB |
| `gossip`               | Enable gossip protocol for message propagation (True = cascading peer multicast, False = full broadcasts) |
| `num_neighbours`       | Number of neighbors each node connects to |
| `use_latency`          | Latency model: `"measured"`, `"distance"`, `"local"`, or `"off"` |
| `same_city_latency_ms` | Latency for nodes in the same city (ms) |
| `same_city_dev_ms`     | Standard deviation for same-city latency (ms) |
| `queueing_delay`       | Additional queueing delay (s) |
| `processing_delay`     | Additional processing delay (s) |

### bandwidth
| Parameter | Description |
| --------- | ----------- |
| `mean`    | Mean bandwidth in Mbps |
| `dev`     | Standard deviation of bandwidth in Mbps |
| `min`     | Minimum bandwidth in Mbps |
| `sample`  | Bandwidth sampling frequency: `'always'`, `'once'`, or `'scenario'` |

## consensus
Links the protocol names to a path that contains a specific configuration file for that protocol.

| Parameter   | Description |
| ----------- | ----------- |
| `BigFoot`   | Path to BigFoot consensus protocol configuration |
| `PBFT`      | Path to PBFT consensus protocol configuration |
| `Tendermint`| Path to Tendermint consensus protocol configuration |

## behaviour
| Parameter       | Description |
| --------------- | ----------- |
| `use`           | Enable behavioural modeling |
| `config`        | Path to behaviour configuration file |
| `print_updates` | Print behaviour updates during simulation |

## dynamic_sim
| Parameter       | Description |
| --------------- | ----------- |
| `use`           | Enable dynamic simulation features |
| `config`        | Path to dynamic simulation configuration file |
| `print_updates` | Print dynamic simulation updates during execution |

## reconfiguration
| Parameter                     | Description |
| ----------------------------- | ----------- |
| `reconfigure`                 | Enable reconfiguration of blockchain system |
| `reconfiguration_interval`    | How often to reconfigure the system (s) |
| `reconfiguration_interval_range` | Random range to adjust reconfiguration interval (s) |
| `conf_block_size`             | Block size of produced configuration blocks in MB |
| `reconfiguration_method`      | How to reconfigure the system (e.g., `"random_centralised"`) |
| `random_configuration`        | Parameters used for random reconfiguration (`protocols`, `block_sizes`, `block_times`) |
| `propagation.model`           | If True, config block is propagated with delay; if False, instantly applied to all nodes |
| `propagation.delay`           | Delay range for configuration block propagation (s) |
| `propagation.per_cent_nodes`  | Percentage of nodes initially receiving the config block |
| `print_updates`               | Print details of reconfiguration |
"""