# Blockchain Simulator Metrics

This document outlines the approach to metric collection and provides an overview of the currently supported metrics within the blockchain simulator.

## Metric Collection Facilitation

The `Metrics` class (found in `src/Simulator/Utils/Metrics.py`) is used for the systematic collection and calculation of various performance metrics of the blockchain network.

Currently the metrics are calculated from analyzing the blockchain structures of the nodes. This, allows for granular monitoring and snapshots by allowing the analysis of specific time intervals.

## Currently Supported Metrics

The simulator currently supports the following key blockchain metrics:

- **Latency:** Measures the time delay between the creation of a transaction and its inclusion in a confirmed block.
    - **Details:** Calculated on a per-transaction and per-block basis, with an average latency reported for each node.
- **Throughput (Transactions Per Second - TPS):** Quantifies the number of transactions processed and confirmed by the network per second. 
    * **Details:** Measured for each node, representing the rate at which it processes transactions into its blockchain.
- **Inter-Block Time (Block Time):** The time elapsed between the creation of consecutive blocks in the blockchain. This metric reflects the block production rate of the network.
    - **Details:** Measured as the time difference between block additions for each pair of consecutive blocks, with an average reported. 
- **Decentralization:** Assesses the distribution of block production power among the nodes in the network.
    - **Details:** Measured using the Gini coefficient based on the distribution of blocks mined by each node.
- **Transaction Information (Mempool & Confirmed Transactions):** Provides insights into the state of transactions within the network from each node's perspective.
    - **Details:** Includes the current size of a node's transaction pool (mempool) and the total number of transactions it has successfully processed and added to its blockchain.
- **Block Sizes:** Records the size of each block, with an average block size reported for each node.
- **Confirmed Blocks:** Indicates the minimum number of blocks that are common and synchronized across all participating nodes in the simulation. 
- **Processed Transactions (System Average):** Calculates the average number of transactions processed across all nodes in the entire simulation.
