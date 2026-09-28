# Extending SBS

SBS is built to be changed.
This page shows how to make the most common changes.
Each recipe points to the concept page that explains the part you change.

## A map of the code

All the simulator code is in `src/Simulator`:

| Folder or file | What it holds |
|---|---|
| `Blockchain.py` | The entry point and the command-line flags. |
| `Parameters.py` | The loaded config, as global dictionaries such as `Parameters.network`. |
| `Engine` | The event queue, the events and the main loop (see [The simulation engine](../concepts/simulation_engine.md)). |
| `Chain` | The node, blocks, transactions and the network model (see [Nodes, blocks and transactions](../concepts/nodes_blocks_transactions.md) and [The network](../concepts/network.md)). |
| `Chain/Consensus` | The consensus protocols, one folder each (see [Consensus](../concepts/consensus.md)). |
| `Chain/Reconfiguration` | The configuration chain and the centralised method (see [Reconfiguration](../concepts/reconfiguration.md)). |
| `Manager` | The Manager and its system events (see [The Manager](../concepts/manager.md)). |
| `Utils` | Metrics, snapshots, the printed output and other helpers. |

Run all commands from `src/Simulator`.

## Add a parameter

1. Add the parameter, with a comment, to a group in [`base.yaml`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Configs/base.yaml).
2. If scenario runs need it too, add it to [`scenario.yaml`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Configs/scenario.yaml).
3. Read it in the code through its group, such as `Parameters.application["my_parameter"]`.

`--set` works for the new parameter straight away.
See [Configuration](../reference/configuration.md).

## Add a consensus protocol

The easiest way to start is to copy PBFT, which is the simplest protocol.
In this example, the new protocol is called `MyPBFT`.

**1. Copy the folder.**
Copy `Chain/Consensus/PBFT` to `Chain/Consensus/MyPBFT`.
Rename each file from `PBFT_*` to `MyPBFT_*`.
Then replace `PBFT` with `MyPBFT` in every file of the new folder.
This renames the class, its `NAME`, its imports and its settings in `Parameters`.

**2. Register the protocol.**
Four places outside the folder need to know about it.

In [`Chain/Consensus/Protocols.py`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Simulator/Chain/Consensus/Protocols.py), add it to `PROTOCOLS`:

```python
from Chain.Consensus.MyPBFT.MyPBFT_state import MyPBFT

PROTOCOLS = {
    PBFT.NAME: PBFT,
    BigFoot.NAME: BigFoot,
    Tendermint.NAME: Tendermint,
    MyPBFT.NAME: MyPBFT,
}
```

In [`Parameters.py`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Simulator/Parameters.py), add a place for its settings, and load them in `load_params_from_config`:

```python
    MyPBFT = {}
```

```python
        Parameters.MyPBFT = read_yaml(params["consensus"]["MyPBFT"])
```

In `base.yaml` and `scenario.yaml`, add the path to its config file to the `consensus` group:

```yaml
consensus:
  MyPBFT: Chain/Consensus/MyPBFT/MyPBFT_config.yaml
```

**3. Run it.**

```console
uv run Blockchain.py --cp MyPBFT --set simulation.sim_time=300 --set MyPBFT.timeout=5
```

```text
  Blocks                   198  (MyPBFT 198)
```

The results count the blocks of each protocol, so the new name shows up at once.
To let the random reconfiguration pick it too, add it to `reconfiguration.random_configuration.protocols`.

**4. Change the logic.**
Now you can change the copy into your own protocol.
Each file has one job:

| File | What to change |
|---|---|
| `MyPBFT_state.py` | The protocol's data on a node, how a round starts, and how the proposer is chosen. `handle_event` sends each event type to its handler. |
| `MyPBFT_transition.py` | What the node does when it gets each type of message. |
| `MyPBFT_messages.py` | How the node builds and sends each type of message. |
| `MyPBFT_timeouts.py` | What happens when a round times out. |
| `MyPBFT_config.yaml` | The protocol's own settings. |

Keep these rules from PBFT:

- The class must implement the interface in [`ConsensusProtocol.py`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Simulator/Chain/Consensus/ConsensusProtocol.py).
- Put `"CP": state.NAME` in the payload of every event. When a node switches protocol, SBS drops the events of the old one.
- Call `self.node.update(time)` when a new round starts and when a round times out. This is where a node applies a new configuration (see [Reconfiguration](../concepts/reconfiguration.md#spreading-and-applying-a-new-configuration)).
- Use the shared round change in [`Rounds.py`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Simulator/Chain/Consensus/Rounds.py), unless your protocol changes rounds in another way.

## Add a system event

A system event lets the Manager change the simulation at a given time.
The steps are on [The Manager](../concepts/manager.md#adding-your-own-system-event) page.
This example raises the transaction rate at a set time, to model a burst of users.

First, add two parameters to the `application` group of `base.yaml`:

```yaml
  # Raise the transaction rate to burst_tx_per_sec at this time (-1 = no burst)
  burst_at: -1
  burst_tx_per_sec: 300
```

Then write the event in a new file, `Manager/SystemEvents/BurstEvents.py`:

```python
from Parameters import Parameters
from Engine.Event import SystemEvent
from Utils import Report

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Manager.Manager import Manager


def schedule_burst_event(manager: "Manager") -> None:
    """Schedules the start of the burst"""
    time = Parameters.application["burst_at"]
    event = SystemEvent(time=time, payload={"type": "burst"})
    manager.sim.q.add_event(event)


def handle_burst_event(manager: "Manager", event: SystemEvent) -> None:
    """Raises the transaction rate for the rest of the run"""
    Parameters.application["tx_per_sec"] = Parameters.application["burst_tx_per_sec"]
    Report.print_update(event.time, "BURST", "tx rate", f"{Parameters.application['tx_per_sec']} tx/s")
```

Then connect it in [`Manager/Manager.py`](https://github.com/GiorgDiama/SymBChainSim/blob/base/src/Simulator/Manager/Manager.py).
Import the file:

```python
from Manager.SystemEvents import BurstEvents as burstSE
```

Schedule the event in `init_system_events`:

```python
        if Parameters.application["burst_at"] != -1:
            burstSE.schedule_burst_event(self)
```

And handle it in `handle_system_event`:

```python
            case "burst":
                burstSE.handle_burst_event(self, event)
```

Now run it with a burst at 150 seconds:

```console
uv run Blockchain.py --set application.burst_at=150 --set simulation.sim_time=300
```

```text
SymBChainSim | PBFT | 16 nodes | 300 s | seed 1837413

0 / 300 s                 0 blocks           0 tx
100 / 300 s              66 blocks      11,865 tx
    [BURST]      150.0 s  tx rate       300 tx/s
200 / 300 s             121 blocks      25,369 tx
300 / 300 s             160 blocks      41,619 tx

 RESULTS (mean over 16 nodes)
  Blocks                   160  (PBFT 160)
  Transactions             41,619 confirmed, 19,190 pending
  Throughput               139.9 tx/s
  Mean latency             12.77 s
  Mean block time          1.86 s
  Mean block size          0.63 MB
  Decentralisation (Gini)  0.15 (0 = perfectly decentralised)

Snapshots → Outputs/Snapshots/snapshot.json (plot with ScenarioGenerationAndVisualisation/snapshot_visualisation.ipynb)
Finished in 2.6 s
```

PBFT cannot keep up with 300 transactions per second.
So the pending transactions and the latency grow.

!!! note "When the change takes effect"
    The transactions are created every `application.tx_interval` seconds, for the next interval.
    So the new rate starts with the next batch of transactions.

This event happens once.
To repeat an event, schedule the next one at the end of its handler, as the fault events do.

## Add a reconfiguration option

SBS can reconfigure the protocol, the block size and the block time.
To add another parameter:

1. Add it to the first configuration, in `ConfigurationBlock.genesis_block`.
2. Add it to `ReconfigurationState.configuration`, the configuration a node currently uses.
3. Apply it in `ReconfigurationState.try_apply_configuration`. The node calls this only at safe points, so think about when your change is safe. If the protocol must restart after the change, return `True`.
4. In the code that uses the parameter, read it from `node.reconfiguration_state.configuration` instead of `Parameters`. Each node can then use a different value while the change spreads.
5. Add it to the decision method, for example `create_random_configuration_block`, and add its options to `reconfiguration.random_configuration`.

The code is in [`Chain/Reconfiguration`](https://github.com/GiorgDiama/SymBChainSim/tree/base/src/Simulator/Chain/Reconfiguration).

## Add a decision method

The centralised method picks each configuration at random.
You can replace it in two ways:

- **Keep the event, change the choice.** Replace the random choice in `create_random_configuration_block` with your own method, such as a heuristic or a reinforcement learning agent.
- **Write a new event.** Write a system event that creates a `ConfigurationBlock` and sends it with `propagate_configuration_block`. Use it in place of the reconfiguration event in `Manager.init_system_events`.

In both cases, the nodes spread and apply the new configuration in the same way.
See [Reconfiguration](../concepts/reconfiguration.md#the-decision-making-mechanism).

## Add a metric

See [Adding a metric](../reference/metrics.md#adding-a-metric).

## Check your change

- **Compare the output.** With the same seed and config, SBS gives the same results every time. Run the same command before and after your change, and compare the outputs. If your change should not affect the results, they must be identical.
- **Step through events.** With `--debug-at TIME`, the run switches to debugging mode at that time. It prints the event queue of every node, and it waits for you before each event.
- **Read the log.** `--set simulation.logging_level=DEBUG` prints a line for each step of each node. The log also goes to `src/Outputs/Logs/log.txt`.
