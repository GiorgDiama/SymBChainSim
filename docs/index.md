# SymBChainSim

SymBChainSim (SBS) is a discrete-event blockchain simulator written in Python, built for blockchain digital twins.
Data-driven: supports updating the simulated system (network, nodes, etc.) from data while the simulation runs.
Reconfiguration: supports changes to the blockchain's configuration (the consensus protocol, block size, etc) during runtime and models the effects.

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

    How SBS models a blockchain and its consensus.

-   :material-robot: **[Use SBS with an agent](reference/agents.md)**

    Give your coding agent a guide to SBS.

</div>

## Why SBS exists

SBS was built to support blockchain digital twins.
A digital twin is a virtual model of a real system, kept in sync with it by a stream of data.
It gives insight into the state of the modelled system, and lets you test a change there before applying it to the real system.
Keeping a twin in sync means following changes in the real system as they happen, which is why SBS supports runtime updates to the simulated system.
SBS also models and analyses the effects of reconfiguration, so you can predict the outcome of a change before making it.
However, you can use SBS as an extensible general-purpose blockchain simulator.

## Cite SBS

If you use SymBChainSim, please cite:

> Diamantopoulos, G., Bahsoon, R., Tziritas, N., & Theodoropoulos, G. (2023). SymBChainSim: A novel simulation tool for dynamic and adaptive blockchain management and its trilemma tradeoff. In *Proceedings of the 2023 ACM SIGSIM Conference on Principles of Advanced Discrete Simulation* (pp. 118–127). https://doi.org/10.1145/3573900.3591121

> Diamantopoulos, G., Bahsoon, R., Tziritas, N., & Theodoropoulos, G. (2025). SymBChainSim: A novel simulation system for info-symbiotic blockchain management. *ACM Transactions on Modeling and Computer Simulation*, 35(2), 1–25. https://doi.org/10.1145/3704917
