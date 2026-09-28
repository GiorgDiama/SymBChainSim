# Configuration

Every run reads one config file.
The file sets all the parameters of the simulation, such as the number of nodes, the network and the consensus protocol.
You can change any value in the file, or on the command line.

## The config files

| File | What it holds |
|---|---|
| [`base.yaml`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Configs/base.yaml) | The default config. Every run uses it, unless you pick another file. |
| [`scenario.yaml`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Configs/scenario.yaml) | The config for `--scenario` runs. It has no run length and no workload settings, because the scenario file sets them. |
| [`behaviour_config.yaml`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Configs/behaviour_config.yaml) | The faulty nodes. Used when `behaviour.use` is on. |
| [`dynamic_config.yaml`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Configs/dynamic_config.yaml) | How the network and the workload change. Used when `dynamic_sim.use` is on. |
| `<protocol>_config.yaml` | The settings of each protocol, such as its timeout. There is one file in the folder of each protocol, in [`Chain/Consensus`](https://github.com/GiorgDiama/SymBChainSim/tree/base/src/Simulator/Chain/Consensus). |

Each file has a comment for every setting.

To use your own config file, put it in `src/Configs` and pass its name with `--config`:

```console
uv run Blockchain.py --config my_config.yaml
```

## Changing a value

Use `--set` to change a value for one run.
You name the value as `group.name`:

```console
uv run Blockchain.py --set application.num_nodes=8 --set network.bandwidth.mean=10 --set PBFT.timeout=5 --set simulation.sim_time=200
```

```text
SymBChainSim | PBFT | 8 nodes | 200 s | seed 1837413

0 / 200 s                 0 blocks           0 tx
100 / 200 s             100 blocks      12,000 tx
200 / 200 s             199 blocks      23,880 tx

 RESULTS (mean over 8 nodes)
  Blocks                   199  (PBFT 199)
  Transactions             23,880 confirmed, 1,320 pending
  Throughput               120.0 tx/s
  Mean latency             0.99 s
  Mean block time          1.00 s
  Mean block size          0.29 MB
  Decentralisation (Gini)  0.11 (0 = perfectly decentralised)

Snapshots → Outputs/Snapshots/snapshot.json (plot with ScenarioGenerationAndVisualisation/snapshot_visualisation.ipynb)
Finished in 0.8 s
```

Some rules:

- You can repeat `--set` as many times as you need.
- A value inside a group of its own has a longer name, such as `network.bandwidth.mean`.
- The settings of a protocol use the protocol's name as the group, such as `PBFT.timeout`.
- Values are read like YAML. So `5` is a number, `True` is a boolean and `[1, 2]` is a list.

The name must already exist in the config file.
So a typo stops the run with an error:

```console
uv run Blockchain.py --set network.num_neighbors=4
```

```text
error: 'network.num_neighbors' is not a valid parameter ('num_neighbors' not found in the loaded config)
```

!!! note "Behaviour and dynamic settings"
    `--set` cannot change the values in `behaviour_config.yaml` and `dynamic_config.yaml`.
    To change them, edit the file.
    Or copy it, and point `behaviour.config` or `dynamic_sim.config` to your copy.

## Command-line shortcuts

Some common settings have their own flag.

| Flag | What it does |
|---|---|
| `--cp NAME` | Sets `simulation.init_cp`, the protocol to start with. |
| `--name NAME` | Sets `simulation.run_name`, the name of the snapshot file. |
| `--reconfig` / `--no-reconfig` | Sets `reconfiguration.reconfigure`. Not available with `--scenario`. |
| `-v`, `--verbose` | Sets `simulation.print_info`, to print more detail. |
| `--debug` / `--no-debug` | Sets `simulation.debugging_mode`. |
| `--debug-at TIME` | Sets `simulation.start_debugging_at`. |
| `--seed N` | Sets the random seed. Two runs with the same seed and config give the same results. |
| `--scenario NAME` | Runs a scenario from `src/Resources/Scenarios` (see the [Scenarios](../tutorials/scenarios.md) tutorial). |
| `--config FILE` | Uses another config file from `src/Configs`. |

`--seed`, `--scenario` and `--config` do not set a value in the config file.

## The groups

The config file has one group for each part of the simulation.

| Group | What it sets | Read more |
|---|---|---|
| `simulation` | When the run stops, the protocol to start with, printing, snapshots and debugging. | [Metrics](metrics.md), [The simulation engine](../concepts/simulation_engine.md#when-the-run-stops) |
| `application` | The number of nodes, the workload and the transaction pool model. | [Nodes, blocks and transactions](../concepts/nodes_blocks_transactions.md) |
| `execution` | How long the nodes take to create and check blocks and messages, and how the proposer is chosen. | [Nodes, blocks and transactions](../concepts/nodes_blocks_transactions.md), [Choosing the proposer](../concepts/consensus.md#choosing-the-proposer) |
| `data` | The maximum block size and the block time. | [Nodes, blocks and transactions](../concepts/nodes_blocks_transactions.md#blocks) |
| `network` | Message sizes, gossip, latency and bandwidth. | [The network](../concepts/network.md) |
| `consensus` | The path to the config file of each protocol. | [Consensus](../concepts/consensus.md) |
| `PBFT`, `Tendermint`, `BigFoot` | The settings of each protocol, from its own config file. | [The three protocols](../concepts/consensus.md#the-three-protocols) |
| `behaviour` | Turns faulty nodes on, and points to `behaviour_config.yaml`. | [Runtime changes](../tutorials/runtime_changes.md) |
| `dynamic_sim` | Turns the changing network and workload on, and points to `dynamic_config.yaml`. | [Runtime changes](../tutorials/runtime_changes.md) |
| `reconfiguration` | Turns reconfiguration on, and sets how often and to what. | [Reconfiguration](../concepts/reconfiguration.md) |

## Where it lives

- Loading the config and `--set`: [`Parameters.py`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Simulator/Parameters.py)
- The command-line flags: [`Blockchain.py`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Simulator/Blockchain.py)
- The config files: [`src/Configs`](https://github.com/GiorgDiama/SymBChainSim/tree/base/src/Configs)
