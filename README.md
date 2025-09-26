# Introduction to SymbChainSim

**SymbChainSim (SBS)** is a blockchain simulation tool written in Python that supports dynamic updates **during runtime**. The motivation behind SymbChainSim is dynamic blockchain optimisation / management while the ultimate goal is the creation of blockchain digital twins. SymbChainSim is designed to be modular and takes a low abstraction approach to modelling consensus protocols to accurately capture their dynamics. 

SymbChainSim is a Discrete Event Simulation (DES) tool. A quick introduction to DES can be found [here](https://softwaresim.com/blog/a-gentle-introduction-to-discrete-event-simulation/). In general, working with SymbChainSim does not require deep understanding of the concepts behind DES; an intuitive idea of DES is enough to start using and even extending SBS.

### Running the simulation

SymbChainSim uses [UV](https://docs.astral.sh/uv/) for environment / dependency management. After installing UV simply navigate to \<project_root\>/src/Simulator and execute
```console
uv run blockchain.py
```

This will install all dependencies and create a local virtual environment that will be automatically used by UV in the future. If no changes are made, the above command executes a simulation with the default configuration parameters that are defined in  \<project_root\>/src/Simulator/Configs/base.yaml

### Using the UV environment in VScode

If you are working with VScode you should set the python interpreter as the one created by UV inside the .venv directory. Specifically, for Unix based operating systems the interpreter is .venv/bin/python and for Windows inside .venv/Scripts/python. Sometimes VScode detects the environment and may prompt you to set the interpreter automatically.

### Learn more

For more detailed documentation and information about the inner working of SymbChainSim check the docs directory. You may also find the following publication useful as they discuss the higher level ideas behind the simulator and motivate the design choices. 

If you use SymbChainSim please cite the following:

>*Diamantopoulos, G., Bahsoon, R., Tziritas, N., & Theodoropoulos, G. (2023, June). Symbchainsim: A novel simulation tool for dynamic and adaptive blockchain management and its trilemma tradeoff. In Proceedings of the 2023 ACM SIGSIM Conference on Principles of Advanced Discrete Simulation (pp. 118-127).*
>
>*Diamantopoulos, G., Bahsoon, R., Tziritas, N., & Theodoropoulos, G. (2025). SymBChainSim: A novel simulation system for info-symbiotic blockchain management. ACM Transactions on Modeling and Computer Simulation, 35(2), 1-25.* 
