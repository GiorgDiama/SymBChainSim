# Introduction to SymbChainSim

**SymbChainSim (SBS)** is a blockchain simulation tool written in Python that supports dynamic updates **during runtime**. The motivation behind SymbChainSim is dynamic blockchain management / optimisation. This simulation is developed to support the endeavour of creating blockchain digital twins. However, it remains a general blockchain simulation with novel features such as reconfiguration and dynamic adaptation of blockchain conditions during runtime. This make SBS a useful tool for protocol modelling and evaluation as well as for the development of dynamic blockchain optimisation mechanisms. 

SymbChainSim is designed to be modular and takes a low abstraction approach to modelling consensus protocols to accurately capture their dynamics. 

SymbChainSim is a Discrete Event Simulation (DES) tool. A quick introduction to DES can be found [here](https://softwaresim.com/blog/a-gentle-introduction-to-discrete-event-simulation/). In general, working with SymbChainSim does not require deep understanding of the concepts behind DES; an intuitive idea of DES is enough to start using and even extending SBS.

### Installation and Set-Up

SymbChainSim uses [UV](https://docs.astral.sh/uv/) for environment / dependency management. 

After installing UV simply navigate to `src/Simulator/` and execute
```console
uv run Blockchain.py
```

This will install all dependencies and create a local virtual environment that will be automatically used by UV.

The above command executes a simulation with the default configuration parameters defined in `/src/Simulator/Configs/base.yaml`

### Learn more

For more detailed documentation and information about the inner working of SymbChainSim check out the [documentation website](https://giorgdiama.github.io/SymBChainSim/). A [quick start guide](https://giorgdiama.github.io/SymBChainSim/quick_start/) can be found there (or in `docs/quick_start.md`). You may also find the following publication useful as they discuss the higher level ideas behind the simulator and motivate the design choices. 

If you use SymbChainSim please also cite the following:

>*Diamantopoulos, G., Bahsoon, R., Tziritas, N., & Theodoropoulos, G. (2023, June). Symbchainsim: A novel simulation tool for dynamic and adaptive blockchain management and its trilemma tradeoff. In Proceedings of the 2023 ACM SIGSIM Conference on Principles of Advanced Discrete Simulation (pp. 118-127).*
>
>*Diamantopoulos, G., Bahsoon, R., Tziritas, N., & Theodoropoulos, G. (2025). SymBChainSim: A novel simulation system for info-symbiotic blockchain management. ACM Transactions on Modeling and Computer Simulation, 35(2), 1-25.* 
