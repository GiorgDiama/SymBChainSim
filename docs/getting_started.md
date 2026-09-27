# Get started

On this page you run your first simulation and learn to read its results.

## Before you start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/).
uv installs the right Python version and all the packages SBS needs.

## Run your first simulation

```console
git clone https://github.com/GiorgDiama/SymBChainSim.git
cd SymBChainSim/src/Simulator
uv run Blockchain.py
```

This runs the default configuration simulates a blockchain of 16 nodes running PBFT for 1800 seconds. You will get to explore the configuration options of SBS a bit later.

!!! tip "Run SBS from `src/Simulator`"
    SBS finds its config files relative to this folder.
    Run all commands in these docs from here.

## Make it shorter

You can change any setting from the command line with `--set`.
For quick tests, simulate 300 seconds instead of 1800:

```console
uv run Blockchain.py --set simulation.sim_time=300
```

## Read the output

This is the output of the short run:

```text
SymBChainSim | PBFT | 16 nodes | 300 s | seed 1837413

0 / 300 s                 0 blocks           0 tx
100 / 300 s              66 blocks      11,760 tx
200 / 300 s             131 blocks      23,858 tx
300 / 300 s             197 blocks      35,880 tx

 RESULTS (mean over 16 nodes)
  Blocks                   197  (PBFT 197)
  Transactions             35,880 confirmed, 120 pending
  Throughput               119.8 tx/s
  Mean latency             2.06 s
  Mean block time          1.52 s
  Mean block size          0.44 MB
  Decentralisation (Gini)  0.16 (0 = perfectly decentralised)

Snapshots → Outputs/Snapshots/snapshot.json (plot with ScenarioGenerationAndVisualisation/snapshot_visualisation.ipynb)
Finished in 2.9 s
```

The output has four parts.

**1. The header** shows the setup: the consensus protocol, the number of nodes, the simulated time and the random seed.

**2. The progress lines** appear every 100 simulated seconds.
They show the blocks and the transactions confirmed so far.

**3. The results.**
Every node keeps its own copy of the blockchain.
SBS measures each copy and shows the mean over all nodes.

| Row | Meaning |
|---|---|
| Blocks | Blocks added to the chain. The brackets show how many each protocol made. |
| Transactions | *Confirmed* transactions are in a block. *Pending* transactions are waiting for one. |
| Throughput | Confirmed transactions per second. |
| Mean latency | Time from when a transaction is created until its block is added to the chain. |
| Mean block time | Time between two blocks. |
| Mean block size | Size of a block, in MB. |
| Decentralisation (Gini) | How evenly the nodes share the work of making blocks. 0 means every node made the same number of blocks. 1 means one node made all of them. |

**4. The snapshots line** tells you where SBS saved data over time.
You plot it in the first tutorial.

!!! tip "Naming results"
    You can use `--name <name>` to set the name of the output file.


## Changing the default configuration

Try a different consensus protocol with `--cp`:

```console
uv run Blockchain.py --set simulation.sim_time=300 --cp Tendermint
```

Or send more transactions than PBFT can handle:

```console
uv run Blockchain.py --set simulation.sim_time=300 --set application.tx_per_sec=200
```

```text
  Transactions             49,070 confirmed, 10,930 pending
  Throughput               165.0 tx/s
  Mean latency             27.82 s
```

PBFT confirms about 165 transactions per second here.
The other transactions wait, so the transaction confirmation latency grows.

Every `--set` names a setting as `group.name`.
You can find all the settings, with comments, in [`src/Configs/base.yaml`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Configs/base.yaml).
[Configuration](reference/configuration.md) explains how the config files work.

## See more detail

Add `-v` to also print the nodes, the parameters, the results of each node and the number of events:

```console
uv run Blockchain.py --set simulation.sim_time=300 -v
```

`uv run Blockchain.py --help` lists all the command-line options.

## What next

- [Compare two runs](tutorials/compare_runs.md) and plot them side by side.
- [Add failing nodes and a changing workload and network](tutorials/runtime_changes.md).
- [Run a scenario](tutorials/scenarios.md) with changing network, workload and node failures.
- Curious how it works inside? Start with [DES in 2 minutes](concepts/des.md).
