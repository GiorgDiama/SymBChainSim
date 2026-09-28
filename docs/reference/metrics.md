# Metrics

At the end of a run, SBS measures how well the blockchain performed.
Each node has its own copy of the chain, so SBS measures the metrics on each node's chain.
The results show the mean over all the nodes.

The metrics leave out the genesis block, the first block that every chain starts with.

## The results

Every run ends with the results.
This is a run of 300 seconds:

```console
uv run Blockchain.py -v --set simulation.sim_time=300
```

```text
 RESULTS (mean over 16 nodes)
  Blocks                   197  (PBFT 197)
  Transactions             35,880 confirmed, 120 pending
  Throughput               119.8 tx/s
  Mean latency             2.06 s
  Mean block time          1.52 s
  Mean block size          0.44 MB
  Decentralisation (Gini)  0.16 (0 = perfectly decentralised)
```

## Definitions

| Metric | How SBS measures it on one node |
|---|---|
| Blocks | The number of blocks in the chain. In brackets, the number of blocks made with each protocol. |
| Confirmed transactions | The number of transactions in the blocks of the chain. |
| Pending transactions | The number of transactions in the pool that are not in a block yet. |
| Throughput | The number of transactions in the chain, divided by the length of the window. The window starts when the first block was created, and ends when the last block was added. |
| Latency | For each block, the mean time from when its transactions were sent to when the block was added. Then the mean over all blocks. |
| Block time | The mean time between two blocks that follow each other in the chain. |
| Block size | The mean size of the blocks, in MB. |
| Decentralisation | The Gini coefficient of the number of blocks each node proposed. 0 means every node proposed the same number of blocks. 1 means one node proposed all of them. |

!!! note "Latency is a mean over blocks"
    Each block counts once, no matter how many transactions it holds.
    So a small block has the same weight as a full one.

### Confirmed blocks

`Metrics.confirmed_blocks` gives the number of blocks that **all** nodes have.
It is not in the results, but you can use it in your own code.

This metric stops growing while any node is offline.
The other nodes still add blocks, but the offline node does not get them.

## More detail with `-v`

With `-v`, SBS also prints the metrics of each node.
This is part of the same run:

```text
 PER NODE
      node  blocks  synced  mean latency  throughput  mean block time  mean block size    Gini  mempool  confirmed
         0     197       0          2.00       119.8             1.52             0.44    0.16      120      35880
         1     197       0          2.07       119.8             1.52             0.44    0.16      120      35880
         2     197       0          2.08       119.8             1.52             0.44    0.16      120      35880
```

- `synced` is the number of blocks the node got by catching up, and not through consensus (see [Catching up](../concepts/nodes_blocks_transactions.md#catching-up-sync)).
- `mempool` is the number of pending transactions.

SBS then prints how many events of each type ran, in total and for each node.

## Snapshots

A snapshot records the metrics and the state of the nodes during the run.
SBS takes one every `simulation.snapshot_interval` seconds.
At the end of the run, it saves them to `src/Outputs/Snapshots/<run_name>.json`.

The metrics in a snapshot cover only the blocks added since the last snapshot.
So the snapshots show how the metrics change over time.

For each snapshot, the file holds:

- The time of the snapshot, and the time of the last one.
- The latency, throughput, block time and decentralisation of each node.
- The state of each node: its bandwidth, location, neighbours, protocol, whether it is online, its latest block and its latest configuration block.
- The pool of each node: the number of transactions and their total size.
- The blocks each node added since the last snapshot.

To plot the snapshots, use [`snapshot_visualisation.ipynb`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/ScenarioGenerationAndVisualisation/snapshot_visualisation.ipynb).

To turn snapshots off, set `simulation.snapshot_interval` to `-1`.

## Adding a metric

1. Write a function that measures it in `Metrics`.
2. Call it in `Metrics.measure_all` and store the value for each node.
3. To print it, add a row to `Report.print_summary`.
4. To record it over time, add it to the snapshot in `Snapshots.take_snapshot`.

## Where it lives

- The metrics: [`Utils/Metrics.py`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Simulator/Utils/Metrics.py)
- The printed results: [`Utils/Report.py`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Simulator/Utils/Report.py)
- The snapshots: [`Utils/Snapshots.py`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Simulator/Utils/Snapshots.py)
