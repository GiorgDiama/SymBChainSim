from datetime import datetime

from Chain.Manager import Manager

import random, numpy

import Chain.Consensus.BigFoot.BigFoot as BigFoot
import Chain.Consensus.PBFT.PBFT as PBFT

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
            '| pbft:',len([x for x in n.blockchain if x.consensus == PBFT]),
            '| bf:',len([x for x in n.blockchain if x.consensus == BigFoot]),
            )
    
    SimulationState.store_state(manager.sim)

    Metrics.measure_all(SimulationState.blockchain_state)
    Metrics.print_metrics()

    print(f"\nSIMULATION EXECUTION TIME: {runtime}")

    
    

run()
