# The Manager

The manager module is SBSs solution to dynamic simulation. The manager, through `SystemEvents` can control all aspects of the simulation (models, state, parameters etc..). The manager is also the interface of the blockchain simulation to the physical world allowing injection of events during runtime to affect the state of the simulation.

## Core Functionality

The manager is in charge of setting up the simulation environment, running and dynamically controlling the simulation during runtime. Specifically for the set up:

- `load_params`: loads the simulation parameters from the configuration file
- `set_up`: 
    - initialises the nodes and network
    - loads the workload (if a trace is provided)
    - initialises `SystemEvents`
- `run`: executes the managed simulation and executes


## SystemEvents

`SystemEvents` are what allow the simulation to be updated during runtime. In essence system events are like any other event in the simulation but instead of modelling the behaviour of the system model they dynamically updated  the simulation state and or parameters. Currently there are four types of SystemEvents:

- Behaviour Events:
    - These events control the behaviour of the blockchain nodes.
    - The `Behaviour` class is defined to keep track of number of Byzantine and faulty nodes as defined by the `behaviour_config.yaml` file.
        - To enable behaviour the relevant parameters in `base.yaml` parameters must be set to `True`
    - At it's current state the behaviour system events control nodes failing and recovering
    - However, in a similar fashion they can control a plethora of other node behaviours that are specific to the modelled protocols
        - Examples include dropping messages, sending conflicting messages, artificially delaying messages etc...
- Dynamic Simulation Events:
    - These events dynamically control the blockchain network and workload during runtime.
    - Specifically, they do so as defined by the parameters in `dynamic_config.yaml`
        - To enable dynamic simulation the relevant parameters in `base.yaml` parameters must be set to `True`
- Generate Transaction Events:
    - These system events control the generation of transactions
    - Currently, they utilise the transaction factory to do so
- Reconfiguration Events:
    - These system events control the reconfiguration of the system
    - Details on this can be found in `reconfiguration.md`
- Scenario Events:
    - These events orchestrate the simulation of specific scenarios
    - They are scheduled by `Manager\ScenariosAndWorkload.py` to change simulation parameters according to the scenario
- Snapshot Events:
    - Snapshot events take a snapshot of the simulation state when triggered.
    - At the end of the simulation that snapshots are gathered and stored in `Outputs/Snapshots/`


## Simulation Updates 

Finally, `SimulationUpdates.py` contains very basic logic to be triggered periodically. Using this for anything more complicated is not recommended as it offers very little control over timing. Currently, these updates print the simulation progress and allow to start debugging mode at a specific simulated time.
