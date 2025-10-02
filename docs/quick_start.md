# SymBChainSim Quick Start Guide

**SymBChainSim (SBS)** is a blockchain simulation tool written in Python that supports dynamic updates **during runtime**. The main feature of SBS is its ability to support dynamic updates to both the workload and the simulated blockchain during runtime. Furthermore, SBS is designed to be modular and provide an easily extensible generic blockchain simulator.

## Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Running Your First Simulation](#running-your-first-simulation)
4. [Configuration](#configuration)
5. [Supported Consensus Protocols](#supported-consensus-protocols)
8. [Troubleshooting and Notes](#troubleshooting)

## Overview

### What is SymBChainSim?

SymBChainSim is a Discrete Event Simulation (DES) tool designed for blockchain research and development. It provides:

- **Dynamic Runtime Updates**: Modify blockchain parameters, consensus protocols, and workloads during simulation
- **Modular Architecture**: Easily extensible design for adding new consensus protocols and features
- **Low Abstraction Modeling**: Accurate representation of consensus protocol dynamics
- **Multiple Consensus Support**: Built-in support for PBFT, Tendermint, and BigFoot.
- **Comprehensive Metrics**: Detailed performance and behaviours analysis

### Discrete Event Simulation

SBS takes a Discrete Event Simulation (DES) approach to blockchain simulation. In DES:
- Simulated systems contain state and logic to produce events
- Each event has a timestamp denoting when it should take effect
- Events are stored in an Event Queue awaiting processing
- The Event Processor continuously picks the earliest event, executes it, and updates the simulation clock
- Event execution updates the state of the models and leads to production of more events

## Installation & Setup

### Prerequisites

- Python 3.13 or higher
- [UV](https://docs.astral.sh/uv/) package manager

### Steps for running your first simulation:

1. **Install UV** (if not already installed):

    UV will automatically:
    - Create a virtual environment
    - Install all dependencies

2. **Clone repo and cd to src/Simulator**:
   ```bash
   git clone <repository-url>
   cd SymBChainSim/src/Simulator
   ```

3. **Run Your First Simulation**:
   ```bash
   uv run Blockchain.py
   ```


### VS Code Setup

If using VS Code, set the Python interpreter to the UV-created environment:
- **Windows**: `.venv/Scripts/python`
- **macOS/Linux**: `.venv/bin/python`

VS Code may automatically detect and prompt you to set this interpreter.

## Running Your First Simulation

### Basic Execution

```bash
# Run with default configuration
uv run Blockchain.py

# Run with existing example scenario
uv run Blockchain.py --sc light_scenario
```

### Default Configuration

The default simulation uses:
- **16 nodes** with PBFT consensus
- **30-minute simulation time** (1800 seconds)
- **180 transactions per second**


### Understanding the Output

After running, you'll see:
- Block production statistics by consensus protocol
- Performance metrics (throughput, latency, etc.)
- Event processing summary
- Simulation and execution times

## Configuration

### Configuration Files

SBS uses YAML configuration files located in `src/Configs/`:

- `base.yaml` - Default simulation parameters
- `scenario.yaml` - Scenario-specific settings
- `behaviour_config.yaml` - Node behaviour configurations
- `dynamic_config.yaml` - Dynamic simulation parameters

### Key Configuration Categories

#### Simulation Parameters
```yaml
simulation:
  init_CP: "PBFT"           # Initial consensus protocol
  simTime: 1800             # Simulation duration (seconds)
  stop_after_blocks: -1     # Stop after N blocks (-1 = disabled)
  debugging_mode: False     # Enable debug logging
```

#### Application Settings
```yaml
application:
  Nn: 16                    # Number of nodes
  workload: 'generate'      # Workload type
  Tn: 180                   # Transactions per second
  TI_dur: 10                # Transaction interval duration
```

#### Network Configuration
```yaml
network:
  gossip: True              # Enable gossip protocol
  num_neighbours: 6         # Number of neighbors per node
  use_latency: "measured"   # Latency model
  bandwidth:
    mean: 5                 # Mean bandwidth (Mbps)
    dev: 2                  # Standard deviation
```

## Supported Consensus Protocols

- PBFT (Practical Byzantine Fault Tolerance)
- Tendermint
- BigFoot

## Troubleshooting & Notes

**1. Gossip and number of peers**

When Gossip is False the network is fully connected regardless of number of peers. However the peers defined by number of peers are used for detecting desync and requesting missing states. 

When changing the number of nodes change the number of peers accordingly!