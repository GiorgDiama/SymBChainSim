# Introduction to SymbChainSim

**SymbChainSim (SBS)** is a blockchain simulation tool written in Python that supports dynamic updates **during runtime**. The motivation behind SymbChainSim is dynamic blockchain optimisation / management while the ultimate goal is the creation of blockchain digital twins. SymbChainSim is designed to be modular and takes a low abstraction approach to modelling consensus protocols to accurately capture their dynamics. 

SymbChainSim is a Discrete Event Simulation (DES) tool. A quick introduction to DES can be found [here](https://softwaresim.com/blog/a-gentle-introduction-to-discrete-event-simulation/). In general, working with SymbChainSim does not require deep understanding of the concepts behind DES; an intuitive idea of DES is enough to start using and even extending SBS.

## Table of Contents
-   [**Quick Start**](quick_start.md): Get up and running with SymBChainSim. This section covers installation, basic execution, and configuration of your first simulation.
-   [**Simulation Engine**](simulation_engine.md): Delve into the core Discrete Event Simulation (DES) engine that powers SymBChainSim, understanding its components and how to extend them.
-   [**Blockchain Models**](node.md): Details on the fundamental building blocks of the simulated blockchain.s
    -   **Node**: Details about the generic blockchain node model, its responsibilities and attributes.
    -   **Block**: Details on the data structure for blocks, including their key fields and helpers.
    -   **Transaction Factory**: Details on how transactions are produced, propagated, selected, and finalized across the network.
    -   **Network**: Details on the peer-to-peer layer model, message propagation, delay models, and network topology.
- [**Consensus**](consensus.md): Understand how consensus is modeled in SBS.
    -   **Consensus Protocols**: Details the low-abstraction, modular approach to modeling various consensus protocols.
    -   **High-Level Sync**: The node synchronization mechanism for catching up on missing blockchain data and configuration chains.
    -   **Rounds**: A generic round-change mechanism used by round-based consensus protocols.
- [**Manager**](manager.md): The central orchestrator for dynamic simulations.
    -   **Manager**: The module responsible for setting up, running, and dynamically controlling the simulation.
    -   **Dynamic Simulation**: Explore how parameters, network behaviors, and workloads are dynamically updated during runtime.
- [**Reconfiguration**](reconfiguration.md): Details on how SymBChainSim models dynamic reconfiguration of the blockchain system.
- [**Metrics**](metrics.md): Understand how performance metrics are collected and calculated to provide insights into the blockchain network's behavior.
- [**Scenarios**](scenarios.md): Details on how to generate custom scenarios that define network conditions, node behaviors, and transaction workloads for comprehensive testing.
- [**Parameters**](simulation_parameters.md): Get a detailed overview of all configurable parameters that control SymBChainSim's components and behaviors.

### Learn more

You may find the following publication useful as they discuss the higher level ideas behind the simulator and motivate the design choices. (If you use SymbChainSim please also cite these):

>*Diamantopoulos, G., Bahsoon, R., Tziritas, N., & Theodoropoulos, G. (2023, June). Symbchainsim: A novel simulation tool for dynamic and adaptive blockchain management and its trilemma tradeoff. In Proceedings of the 2023 ACM SIGSIM Conference on Principles of Advanced Discrete Simulation (pp. 118-127).*
>
>*Diamantopoulos, G., Bahsoon, R., Tziritas, N., & Theodoropoulos, G. (2025). SymBChainSim: A novel simulation system for info-symbiotic blockchain management. ACM Transactions on Modeling and Computer Simulation, 35(2), 1-25.* 
