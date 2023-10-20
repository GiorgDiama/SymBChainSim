from datetime import datetime
from Chain.Parameters import Parameters
from Chain.Manager.Manager import Manager

import random
import numpy

from Chain.Metrics import Metrics
import Chain.tools as tools

import statistics as st

############### SEEDS ############
seed = 5
random.seed(seed)
numpy.random.seed(seed)
############## SEEDS ############


def run():
    manager = Manager()

    manager.set_up()
    t = datetime.now()
    manager.run()
    runtime = datetime.now() - t

    print(tools.color(
        f"Simulated time {'%.2f'%manager.sim.clock} seconds!", 45))

    Metrics.measure_all(manager.sim)
    Metrics.print_metrics()

    s = f"{'-'*30} EVENTS {'-'*30}"
    print(tools.color(s, 41))

    for key, value in Parameters.simulation['events'].items():
        if isinstance(value, dict):
            print(key)

            # gourp by value
            s = ' '.join(f'{node}:{num}' for node, num in value.items())
            print(s)
        else:
            print(key, value)

    print(tools.color(f"SIMULATION EXECUTION TIME: {runtime}", 45))


run()
