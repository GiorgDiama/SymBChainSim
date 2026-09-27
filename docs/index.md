# SymBChainSim

SymBChainSim (SBS) is a blockchain simulator written in Python.
You can change the blockchain **while the simulation runs**.
For example, you can switch the consensus protocol, the block size or the network conditions mid-run.

## What you can do with SBS

- Measure throughput, latency and decentralisation for a blockchain setup.
- Compare consensus protocols: PBFT, Tendermint and BigFoot.
- Replay a scenario with changing network speed, workload and node failures.
- Reconfigure the blockchain during a run and see the effect.

## Try it

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). Then run:

```console
git clone https://github.com/GiorgDiama/SymBChainSim.git
cd SymBChainSim/src/Simulator
uv run Blockchain.py
```

The first run installs everything it needs. The simulation takes about 30 seconds.

Want to see the blockchain change during a run? Add `--reconfig`:

```console
uv run Blockchain.py --reconfig
```

The output shows each switch:

```text
[RECONFIG]  280.1 s  switched to   Tendermint, max block size 1 MB, block time 0.1 s
[RECONFIG]  577.3 s  switched to   PBFT, max block size 2 MB, block time 1 s
```

## Where to go next

<div class="grid cards" markdown>

-   :material-rocket-launch: **[Get started](getting_started.md)**

    Run your first simulation and learn to read the results.

-   :material-school: **[Tutorials](tutorials/compare_runs.md)**

    Compare runs, run scenarios and change the blockchain at runtime.

-   :material-lightbulb: **[Concepts](concepts/des.md)**

    Optional. How SBS models a blockchain and its consensus.

-   :material-robot: **[Use SBS with an agent](reference/agents.md)**

    Give your coding agent a guide to SBS.

</div>

## Why SBS exists

SBS was built to support **blockchain digital twins**.
A digital twin is a simulation that runs next to a real system and helps manage it.
To do this, the simulation must follow changes in the real system as they happen.
This is why SBS supports changes during a run.
SBS also works as a general blockchain simulator.

## Cite SBS

If you use SymBChainSim, please cite:

> Diamantopoulos, G., Bahsoon, R., Tziritas, N., & Theodoropoulos, G. (2023). SymBChainSim: A novel simulation tool for dynamic and adaptive blockchain management and its trilemma tradeoff. In *Proceedings of the 2023 ACM SIGSIM Conference on Principles of Advanced Discrete Simulation* (pp. 118–127). https://doi.org/10.1145/3573900.3591121

> Diamantopoulos, G., Bahsoon, R., Tziritas, N., & Theodoropoulos, G. (2025). SymBChainSim: A novel simulation system for info-symbiotic blockchain management. *ACM Transactions on Modeling and Computer Simulation*, 35(2), 1–25. https://doi.org/10.1145/3704917
