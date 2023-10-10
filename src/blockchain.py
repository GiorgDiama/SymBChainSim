from datetime import datetime

from Chain.Manager import Manager

import random
import numpy

from Chain.Consensus.PBFT.PBFT import PBFT
from Chain.Consensus.BigFoot.BigFoot import BigFoot

from Chain.Metrics import SimulationState, Metrics
import Chain.tools as tools

############### SEEDS ############
seed = 5
random.seed(seed)
numpy.random.seed(seed)
############### SEEDS ############

CPs = {
    PBFT.NAME: PBFT,
    BigFoot.NAME: BigFoot
}


def run():
    manager = Manager()

    manager.set_up()

    t = datetime.now()
    manager.run()
    runtime = datetime.now() - t
    print()
    for n in manager.sim.nodes:
        print(n.__str__(full=True),
              '\tPBFT blocks in BC:\t', len(
                  [x for x in n.blockchain[1:]if x.consensus.NAME == PBFT.NAME]),
              '\n\tBigFoot blocks in BC:\t', len(
                  [x for x in n.blockchain[1:] if x.consensus.NAME == BigFoot.NAME]))

    SimulationState.store_state(manager.sim)

    Metrics.measure_all(SimulationState.blockchain_state)
    Metrics.print_metrics()

    print(tools.color(f"\n SIMULATION EXECUTION TIME: {runtime}", 44))


run()
