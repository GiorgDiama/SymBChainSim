from datetime import datetime
from Chain.Parameters import Parameters
from Chain.Manager import Manager

import random
import numpy

from Chain.Consensus.PBFT.PBFT import PBFT
from Chain.Consensus.BigFoot.BigFoot import BigFoot

from Chain.Metrics import Metrics
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

    print(
        tools.color(f"Simulated the blockchain network for {'%.2f'%manager.sim.clock} seconds!", 45))

    Metrics.measure_all(manager.sim)
    Metrics.print_metrics()

    s = f"{'-'*30} EVENTS {'-'*30}"
    print(tools.color(s, 41))
    print(Parameters.simulation['events'])

    print(tools.color(f"SIMULATION EXECUTION TIME: {runtime}", 44))


run()
