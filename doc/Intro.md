# Introduction to SymbChainSim

**SymbChainSim (SBS)** is a blockchain simulation tool written in Python supporting dynamic updates to the workload and the simulated blockchain network and dynamic adaptation (reconfiguration) of the consensus process (consensus protocol and relevant parameters) **during runtime**. SBS is designed to be modular, allowing for easy extension of the 'solution space' (new protocols, new network models, new parameters etc...). Additionally, SBS takes a low/no abstraction approach to modelling consensus protocols to accurately capture their dynamics. Protocols in SBS are modelled at the 'message' level, i.e., every message required by the protocols specification should be modelled as an event. 

SymbChainSim takes a Discrete Event Simulation (DES) approach to simulation blockchain. A quick introduction to DES for anyone unfamiliar with the topic can be found here (https://softwaresim.com/blog/a-gentle-introduction-to-discrete-event-simulation/). In general, working with SBS does not require a deep understanding of the concepts behind DES - an intuitive idea of DES is enough to start using and event extending SBS.

<!-- ## Walkthrough of SBS's blockchain model

This guide aims to provide the general idea and implementation details of SBS's to be used as a starting place for extending SBS to fit your use case. -->
