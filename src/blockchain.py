from datetime import datetime

from Chain.Manager import Manager

import random, numpy

from Chain.Consensus.PBFT.PBFT import PBFT
from Chain.Consensus.BigFoot.BigFoot import BigFoot

from Chain.Metrics import SimulationState, Metrics

############### SEEDS ############
seed = 5
random.seed(seed)
numpy.random.seed(seed)
############### SEEDS ############

def run():
    manager = Manager()

    manager.set_up()

    t = datetime.now()
    manager.run()
    runtime = datetime.now() - t

    for n in manager.sim.nodes:
        print(n, '| Total_blocks:', n.blockchain_length(),
            '| pbft:',len([x for x in n.blockchain[1:] if x.consensus.NAME == PBFT.NAME]),
            '| bf:',len([x for x in n.blockchain[1:] if x.consensus.NAME == BigFoot.NAME]),
            )
    
    SimulationState.store_state(manager.sim)

    Metrics.measure_all(SimulationState.blockchain_state)
    Metrics.print_metrics()

    print(f"\nSIMULATION EXECUTION TIME: {runtime}")

CPs = {
    PBFT.NAME: PBFT,
    BigFoot.NAME: BigFoot
}

def simple_simulation():
    from Chain.Simulation import Simulation
    from Chain.Network import Network

    sim = Simulation()

    Network.init_network(sim.nodes)

    sim.init_simulation()

    t = datetime.now()
    sim.run_simulation()
    runtime = datetime.now() - t

    for n in sim.nodes:
        print(n, '| Total_blocks:', n.blockchain_length(),
            '| pbft:',len([x for x in n.blockchain[1:] if x.consensus.NAME == PBFT.NAME]),
            '| bf:',len([x for x in n.blockchain[1:] if x.consensus.NAME == BigFoot.NAME]),
                )
    
    SimulationState.store_state(sim)

    Metrics.measure_all(SimulationState.blockchain_state)
    Metrics.print_metrics()

    print(f"\nSIMULATION EXECUTION TIME: {runtime}")


simple_simulation()

