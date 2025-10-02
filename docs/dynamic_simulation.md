# Dynamic Simulation

The SymBChainSim is designed to model blockchain networks and consensus protocols under various dynamic conditions. It allows users to configure and observe how different parameters, network behaviors, and workloads impact blockchain performance and resilience.

## Core Components

The simulator orchestrates several key components:

1.  **Configuration Parameters (`Parameters`):**
    *   The entire simulation is driven by a set of parameters loaded primarily from `src/Configs/base.yaml`. Specific dynamic behaviors and network/workload changes are managed through separate configuration files:
        *   `src/Configs/behaviour_config.yaml`: Defines the number of Byzantine and faulty nodes and their respective behaviors (e.g., sending bad sync data, not responding).
        *   `src/Configs/dynamic_config.yaml`: Dictates if and how network (bandwidth) and workload (transaction rates, sizes) parameters are dynamically updated during the simulation.

1.  **The Manager:**
    *   The `Manager` (found in `src/Simulator/Manager/Manager.py`) is the central orchestrator of the simulation. It's responsible for setting up the environment, initializing nodes and the network, and dynamically controlling the simulation's state and parameters during runtime.
    *   The Manager uses `SystemEvents` to introduce changes and trigger actions throughout the simulation.
    *   For a detailed explanation of the Manager's functionality, please refer to the [Manager](`manager.md`) documentation.

1.  **`DynamicSimulation` System Events:**
    *   These are special events, managed by the `Manager`, that allow the simulation's state and parameters to be updated dynamically during runtime. They are crucial for modeling complex scenarios and behaviors. The `Manager` dispatches these events to dedicated handlers. Key types of System Events include:
        *   **Dynamic Simulation:** Updates network characteristics (like bandwidth, as seen in `src/Simulator/Manager/SystemEvents/DynamicSimulation.py`) and workload parameters (like transactions per second and transaction size) dynamically throughout the simulation, sampling from defined distributions in `dynamic_config.yaml`.
        *   **Behaviour Events:** Manages the introduction of faults (e.g., node crashes) and recoveries, as configured in `behaviour_config.yaml`.

## Simulation Flow (High-Level)

A typical dynamic simulation runs as follows:

1.  **Parameter Loading:** The `Manager` loads all initial parameters from `base.yaml` and other specific configuration files like `behaviour_config.yaml` and `dynamic_config.yaml`.
1.  **Setup:** The `Manager` initializes the simulation environment, including creating nodes, setting up the network, and scheduling the initial Dynamic Simulation `SystemEvents`.
1.  **Execution Loop:** The `Manager` starts the simulation loop, continuously advancing the `Simulation` clock and processing events from its queue. During this loop, `SystemEvents` are triggered to introduce dynamic changes (e.g., updating network conditions, workload generation, simulating node faults etc...).
1.  **Termination:** The simulation continues until a predefined finish condition is met (e.g., simulation time elapses, a certain number of blocks are produced, or a specific number of transactions are processed).
1.  **Results:** Upon completion, if enabled, simulation snapshots are saved for post-analysis.

## Extending Dynamic Simulation

The above approach allows control over virtually all aspects of the modeled blockchain system. Specifically, anything that is controlled by simulation parameters can be dynamically adapted by introducing new `SystemEvent` and defining their frequency and effect on such parameters.