# Configuring SymbChainSim simulations

Most of SymbChainSims components are controlled through the configuration yaml files found is the Configs directory. The yaml file is split up into named categories according to the broad area that they control. Specifically these are: simulation, application, execution, data, network, consensus, behaviour, dynamic_sim and reconfiguration.

## simulation
| Parameter           | Default Value | Description                            |
| ------------------- | ------------- | -------------------------------------- |
| `init_CP`           | `"PBFT"`      | Initial consensus protocol             |
| `simTime`           | `1200`        | Stop after simulating X seconds (s)       |
| `stop_after_blocks` | `-1`          | Stop after producing X blocks          |
| `stop_after_tx`     | `-1`          | Stop after processing X transactions   |
| `debugging_mode`    | `False`       | Run the simulation in debug mode       |
| `logging_level`     | `INFO`        | Sets the logging level                 |
| `print_every`       | `200`         | How often to print simulation progress (s) |
| `snapshots`         | `False`       | Take snapshot every timer interval (see application configuration TI_dur)    |
| `print_info`        | `False`       | Print simulation parameters at start   |

## application

| Parameter               | Default Value | Description                   |
| ----------------------- | ------------- | ----------------------------- |
| `Nn`                    | `16`          | Number of nodes               |
| `workload`              | `'generate'`  | Generate a workload or path to workload file  |
| `TI_dur`                | `5`           | Transaction interval duration (s) |
| `Tn`                    | `50`          | Number of transactions generated per second      |
| `base_transaction_size` | `0`           | Base size of a transaction  (MB)   |
| `Tsize`                 | `0.004`       | Transaction size mean (exponential dist)  (MB)      |
| `transaction_model`     | `"global"`    | Transaction pool model type  (see transaction_factory.md for details) |

## execution

| Parameter                    | Default Value | Description                     |
| ---------------------------- | ------------- | -------------------------------                                    |
| `creation_time`              | `0.02`        | Time required to create a block  (s)                                  |
| `block_val_delay`            | `0.01`        | Block validation delay  (s)                                           |
| `msg_val_delay`              | `0.001`       | Message validation delay  (s)                                         |
| `sync_message_request_delay` | `0.1`         | Delay for sync message requests (s)                                    |
| `time_per_tx`                | `0.001`       | Time to validate a transaction    (s)                                 |
| `proposer_selection`         | `"hash"`      | Method to select block proposers (see conseusus.md for details)    |

## data

| Parameter         | Default Value | Description                  |
| ----------------- | ------------- | ---------------------------- |
| `Bsize`           | `1`           | Max. block  (MB)        |
| `base_block_size` | `0.002`       | Base size of a block   (MB)      |
| `block_interval`  | `0.1`         | Minimum block interval (MB) |


## network

| Parameter              | Default Value | Description                     |
| ---------------------- | ------------- | ------------------------------- |
| `base_msg_size`        | `0.1`         | Base message size  (MB)             |
| `gossip`               | `True`        | Use gossip protocol             |
| `num_neighbours`       | `4`           | Number of peers per nodes     |
| `use_latency`          | `"measured"`  | Latency model to use (see network for details)            |
| `same_city_latency_ms` | `5`           | Latency within same city (ms)   |
| `same_city_dev_ms`     | `0`           | Deviation for same-city latency (ms) |
| `queueing_delay`       | `0`           | Delay due to queueing (seconds)           |
| `processing_delay`     | `0`           | Processing delay (seconds)                |

### bandwidth

| Parameter | Default Value | Description               |
| --------- | ------------- | ------------------------- |
| `mean`    | `10`          | Average bandwidth  (MB/s)       |
| `dev`     | `0.5`         | Bandwidth deviation  (MB/s)     |
| `min`     | `0.24`        | Minimum bandwidth  (MB/s)       |
| `sample`  | `'always'`    | Bandwidth sampling policy (see network for details) |

## consensus

Links the protocol names to a path that contains a specific configuration file for that protocol

## behaviour and dynamic simulation

Node behavior and dynamic simulation updates are defined in a separate configuration file. These fields simply  provides a path to that configuration file, whether this is enabled and whether to print information about this to the console.