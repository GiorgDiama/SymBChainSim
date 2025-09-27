# Scenario Generation and Visualisation

This directory contains tools for generating blockchain simulation scenarios and analyzing their results. It provides functionality to create realistic test scenarios with configurable network conditions, node behaviors, and transaction workloads.

## Files

### `generate_scenario.py`
Main script for generating blockchain simulation scenarios. Creates JSON scenario files with the following components:

- **Network Configuration**: Assigns different network models to nodes with configurable bandwidth
- **Node Behavior**: Simulates node failures with configurable duration and timing
- **Transaction Workloads**: Generates transaction streams with configurable rates and sizes
- **Time Intervals**: Divides simulation into configurable time segments

**Usage:**
```bash
uv run generate_scenario.py --name <scenario_name>
```

**Parameters:**
- `dur`: Total simulation duration
- `ti_mu`, `ti_sigma`: Time interval distribution parameters
- `num_nodes`: Number of blockchain nodes
- `networks`: List of network models (mean, std_dev) for bandwidth assignment
- `fail_duration`: Node failure duration distributions
- `workloads`: Transaction rate distributions
- `sizes`: Transaction size range

### `scenario_visualistation.ipynb`
Jupyter notebook for visualizing generated scenarios. Provides:

### `result_viz.ipynb`
Jupyter notebook for visualising simulation results. Features:

## Scenario Schema

Generated scenarios follow this JSON structure:

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

## Output

Generated scenarios are saved to `../Resources/Scenarios/<name>.json` and can be used by the blockchain simulator for testing different consensus protocols and network conditions.
