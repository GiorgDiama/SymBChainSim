# SymBChainSim (SBS): guide for coding agents

This file tells a coding agent how to run, read and change SymBChainSim (SBS) correctly.
The full documentation is in `docs/`. The pages named below are in `docs/concepts`, `docs/reference` and `docs/how_to`.

## What SBS is for

SBS is a discrete-event simulator of permissioned blockchains.
It models consensus at the message level: every proposal, vote and timeout is a separate event.
It has three vote-based protocols (PBFT, Tendermint, BigFoot), and it can switch between them while it runs (reconfiguration).

How far to trust the results:

- Where a part is modelled in detail, the results should be close to reality. The more abstract a part is, the less you can rely on it.
- Hardware, transaction validation and other application-specific delays are abstracted as fixed times (the `execution` group).
- The network is a simple model (latency, bandwidth, gossip). For a detailed network study, a dedicated network simulator such as ns-3 is a better tool.
- Relative results are the most trustworthy. If configuration A beats configuration B in SBS, this is likely true, because the abstractions affect both runs in the same way. Absolute numbers (such as the exact throughput) are much harder to get right.

When a user asks a question that depends on an abstracted part, say so.

## Running it

Run everything from `src/Simulator`, with `uv`:

```console
uv run Blockchain.py                                   # default run: PBFT, 16 nodes, 1800 s
uv run Blockchain.py --set simulation.sim_time=300     # a quick check
uv run Blockchain.py --cp Tendermint --name tm         # another protocol; snapshots go to tm.json
uv run Blockchain.py --scenario light_scenario         # a scenario from src/Resources/Scenarios
uv run Blockchain.py --help                            # all flags
```

- `--set group.name=value` changes any value in the config file (`src/Configs/base.yaml`). You can repeat it. The key must already exist, so a typo stops the run with an error.
- Protocol settings use the protocol as the group, such as `--set PBFT.timeout=5`.
- `--set` cannot reach `behaviour_config.yaml` or `dynamic_config.yaml`. Edit those files, or point `behaviour.config` / `dynamic_sim.config` to a copy.
- `--seed N` sets the random seed. The default seed is fixed, so two runs of the same command give the same results.
- Units: times in seconds, sizes in MB, bandwidth in MB/s, `tx_per_sec` in transactions per second.

Scenario mode (`--scenario`) is different:

- It uses `src/Configs/scenario.yaml`. The scenario file sets the run length, the number of nodes and the workload, so `simulation.sim_time` and the workload keys cannot be set.
- `--reconfig` is not available.
- The node failures in a scenario run only with `--set simulation.simulate_faults=True`.

A custom config file (`--config my.yaml`, in `src/Configs`) must contain every key the code reads. Start from a copy of `base.yaml`.

### Run time

Run time depends mostly on the number of nodes and the number of transactions.

- Every node talks to every other node, so the number of messages grows fast with the number of nodes. Large networks are slow.
- For many transactions, keep `application.transaction_model: "global"`. It scales linearly with the number of transactions. The `local` model is much slower.
- Keep `network.bandwidth.min` at a sensible value. Very low bandwidth gives unrealistic delays.

The run prints its progress every `simulation.print_every` simulated seconds.
Only stop a run if the progress lines stop for a long time. That means it has hung.

## Designing experiments

- No warm-up period is needed.
- Faults (`behaviour.use`), dynamic networks and workloads (`dynamic_sim.use`) and random reconfiguration (`--reconfig`) add a lot of randomness. Run many seeds, and average the results.
- To compare configurations under exactly the same conditions, use a scenario. A scenario fixes the workload, the bandwidth and the failures, which removes most of the randomness.
- To profile one configuration under many possible conditions, use the random dynamic and behaviour settings with many seeds.
- `Parameters` and `Metrics` are global class state, so there is one simulation per process. To run several seeds at once, start separate processes, each with its own `--name`.
- The run length, the number of seeds and how to present the results depend on the question. Pick them for the experiment, and say what you picked.

## Reading results

Every run ends with the results, the mean over all nodes:

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

- The definitions of every metric are in `docs/reference/metrics.md`.
- `-v` adds the metrics of each node and the number of events of each type.
- Snapshots are saved to `src/Outputs/Snapshots/<name>.json` every `simulation.snapshot_interval` seconds. Each snapshot covers only the blocks since the last one. `src/ScenarioGenerationAndVisualisation/snapshot_visualisation.ipynb` plots them.
- The Gini coefficient needs many blocks to be accurate. Average it over long periods. The Gini of a single snapshot interval is noisy.

Check for signs of a broken run:

- Look at the `blocks` column of `-v`. A node that is far behind the others may be fine when faults are frequent. But it can also be a node stuck in a state it cannot recover from, which is a bug.
- No new blocks for a long time. With `n` nodes, a decision needs `2f + 1` votes, where `f = (n - 1) / 3` rounded down. If more than `f` nodes are offline at once, the chain stops until they come back. This is expected. If the chain stops without this, something is wrong.

## Where things live

All the simulator code is in `src/Simulator`:

| Path | What it holds |
|---|---|
| `Blockchain.py` | The entry point and the flags. |
| `Parameters.py` | The loaded config, as global dictionaries. |
| `Engine` | The event queue, the events, the main loop and the default event handler. |
| `Chain/Node.py` | The node: its chain, its pool, sync and configuration updates. |
| `Chain/Consensus` | One folder per protocol, the shared round change (`Rounds.py`), sync (`HighLevelSync.py`) and the list of protocols (`Protocols.py`). |
| `Chain/Reconfiguration` | The configuration chain and the centralised decision method. |
| `Chain/Network.py` | The network model. |
| `Manager` | Setting up a run, and the system events (`Manager/SystemEvents`). |
| `Utils` | Metrics, snapshots, the printed output and the debugger. |

The concept pages in `docs/concepts` explain each part.

## Changing the code

The recipes are in `docs/how_to/extending.md`: add a parameter, a protocol, a system event, a reconfiguration option, a decision method or a metric.

Rules:

- **Leave the engine alone.** `Engine` is blockchain-agnostic, and it must stay that way. Put blockchain logic in `Chain` or `Manager`. The default event handler (`Engine/Handler.py`) is the exception.
- **Tag protocol events.** Every event of a protocol carries `"CP": <protocol name>` in its payload. SBS uses it to drop the events of the old protocol after a switch.
- **Keep runs reproducible.** The same seed and config must give the same results. Use the `random` and `numpy.random` generators that `Blockchain.py` seeds. Do not iterate over sets or other unordered collections where the order affects the results.
- **Think through message orders.** A blockchain is a distributed state machine. Messages can arrive late, early, twice or not at all, and nodes can fail and recover at any time. Before you change consensus, sync or reconfiguration logic, go through the possible sequences of messages and check that no node can reach a state it cannot leave.

## Good practice

These are suggestions. They help most with the consensus logic, which is hard to debug.

- **Crash rather than continue.** SBS is research code. A crash is much better than a wrong result, and it points to the bug. Use assertions for things that must hold. Do not catch errors to keep a run going, and do not fill in missing values with defaults.
- **Keep the code simple.** Plain functions and direct code hide less than layers of abstraction. This matters when you trace a message through the protocol.
- **Compare before and after.** Run the same command with the same seed before and after a change. If the change should not affect the results, the outputs must be identical.
- **Debug with the tools.** `--debug-at TIME` switches to step-by-step mode at that time. `--set simulation.logging_level=DEBUG` logs every step of every node, also to `src/Outputs/Logs/log.txt`.
