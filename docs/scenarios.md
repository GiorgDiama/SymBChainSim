# Scenario Generation in SymBChainSim (SBS)

This document outlines the process of generating custom scenarios for the SymBChainSim (SBS) blockchain simulator. Scenarios define the network conditions, node behaviors, and transaction workloads to be simulated, allowing for comprehensive testing of different consensus protocols and network configurations.

## Generation Scenarios

The `src/ScenarioGenerationAndVisualisation` directory contains tools for creating and visualizing blockchain simulation scenarios. The primary script for scenario generation is `generate_scenario.py`.

### `generate_scenario.py`

The `generate_scenario.py` script is responsible for creating JSON scenario files. These files encapsulate various aspects of a simulation, including:

-   **Network Configuration**: Defines the bandwidth characteristics for each node in the network.
-   **Node Behavior**: Simulates node failures, specifying their timing and duration.
-   **Transaction Workloads**: Generates streams of transactions with configurable rates and sizes.
-   **Time Intervals**: Divides the total simulation duration into distinct segments, allowing for dynamic changes in network conditions and node behavior.

### Usage

To generate a scenario, to run the `generate_scenario.py` script with a specified name:

```bash
cd src/ScenarioGenerationAndVisualisation
uv run generate_scenario.py --name <scenario_name>
```

Replace `<scenario_name>` with your desired name for the scenario. The generated JSON file will be saved in `../Resources/Scenarios/<scenario_name>.json`.

### Parameters

The `generate_scenario.py` script uses a dictionary of parameters to define the characteristics of the generated scenario. These parameters are currently defined within the script and can be modified for different simulation needs. Below are the key parameters and their descriptions:

-   `dur` (int): Total duration of the simulation in seconds.
-   `ti_mu` (float): Mean of the normal distribution used to determine the length of time intervals.
-   `ti_sigma` (float): Standard deviation of the normal distribution used to determine the length of time intervals.
-   `num_nodes` (int): The total number of blockchain nodes participating in the simulation.
-   `networks` (list of tuples `(mean, std_dev)`): 
    - A list of network models. Each tuple represents a normal distribution from which node bandwidths (in some unit, e.g., Mbps) are sampled. Each node is randomly assigned one of these network models.
-   `fail_duration` (list of tuples `(mean, std_dev)`):
    - A list of normal distributions defining the duration of node failures. When a node fails, its downtime is sampled from one of these distributions.
-   `workloads` (list of tuples `(mean, std_dev)`): A list of normal distributions representing transaction rates (e.g., transactions per second) within a given interval. The number of transactions for an interval is sampled from one of these distributions.
-   `sizes` (tuple `(min, max)`): A tuple specifying the minimum and maximum transaction sizes. Transaction sizes are uniformly sampled within this range.

### Example Parameters (from `generate_scenario.py`)

```python
parameters_dict = {
    "dur": 1200,          # Total simulation duration in seconds
    "ti_mu": 300,         # Mean for time interval length
    "ti_sigma": 20,       # Standard deviation for time interval length
    "num_nodes": 8,       # Number of nodes in the simulation
    "networks": [(10, 0.1), (5, 0.1), (2.5, 0.1)], # Bandwidth models (mean, std_dev)
    "fail_duration": [(20, 5), (60, 10), (120, 20)], # Failure duration models
    "workloads": [(50, 10), (100, 20), (100, 50)], # Transaction rate models
    "sizes": (8, 20.5),   # Transaction size range (min, max)
}
```

### Scenario JSON Schema

Generated scenarios adhere to the following JSON structure:

```json
{
    "set_up": {
        "num_nodes": <number>,
        "duration": <total_time>,
        "parameters": <generation_parameters>
    },
    "intervals": {
        "<interval_id>": {
            "start": <start_time>,
            "end": <end_time>,
            "network": [(node_id, bandwidth), ...],
            "faults": [(node_id, fail_time, duration), ...],
            "transactions": [(creator, id, timestamp, size), ...]
        }
    }
}
```

-   **`set_up`**: Contains overall simulation parameters.
    -   `num_nodes`: The total number of nodes in the simulation.
    -   `duration`: The total simulation duration.
    -   `parameters`: The dictionary of parameters used to generate this specific scenario.
-   **`intervals`**: An object where each key is an `interval_id` (0, 1, 2, ...) representing a time segment within the simulation.
    -   `start`: The start time of the interval.
    -   `end`: The end time of the interval.
    -   `network`: A list of tuples, where each tuple `(node_id, bandwidth)` specifies the assigned bandwidth for a given node during this interval.
    -   `faults`: A list of tuples `(node_id, fail_time, duration)` indicating when a specific node fails and for how long within this interval.
    -   `transactions`: A sorted list of tuples `(creator, id, timestamp, size)` representing the transactions generated during this interval. Transactions are sorted by `timestamp`.

### Output

Generated scenarios are saved as JSON files in the `../Resources/Scenarios/` directory, named after the `--name` parameter provided during script execution (e.g., `../Resources/Scenarios/my_scenario.json`). These files are then used as input for the blockchain simulator to test various consensus protocols and network conditions.

## Executing Scenarios

Scenario files can be used to run a simulation with SymBChainSim. The main entry point for running simulations is the `src/Simulator/Blockchain.py` script.

To execute a simulation using a previously generated scenario, you need to specify the scenario's name using the `--sc` command-line argument.

```bash
uv run src/Simulator/Blockchain.py --sc <scenario_name>
```

Replace `<scenario_name>` with the name you provided when generating the scenario (e.g., `my_scenario`). The system will automatically look for the scenario file in the `Resources/Scenarios/` directory.

A default scenario `light_scenario.json` is provided for testing.

### Scenario Configuration

The `src/Configs/scenario.yaml` file allows for control over parameters that are not defined by the scenario itself. While a scenario file defines dynamic elements like network changes and transaction loads, `scenario.yaml` configures the static properties and operational parameters of the simulation engine and blockchain components. The parameters in `scenario.yaml` are a subset of those in `base.yaml` thus details on the specifics for each can be found in the parameters section. 






