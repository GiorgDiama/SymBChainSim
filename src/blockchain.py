from datetime import datetime
from Chain.Parameters import Parameters
from Chain.Manager.Manager import Manager
from Chain.Metrics import Metrics
import Chain.tools as tools

import random
import numpy
import sys
import statistics as st

############### SEEDS ############
seed = 5
random.seed(seed)
numpy.random.seed(seed)
############## SEEDS ############


def run():
    manager = Manager()
    manager.load_params()
    manager.set_up()
    t = datetime.now()
    manager.run()
    runtime = datetime.now() - t

    Metrics.measure_all(manager.sim)
    Metrics.print_metrics()

    s = f"{'-'*30} EVENTS (event_type: node_id:no_events ... ) {'-'*30}"
    print(tools.color(s, 43))

    for key, value in Parameters.simulation['events'].items():
        if isinstance(value, dict):
            s = ' | '.join(f'{node}:{num}' for node, num in value.items())
            print(f'{key}: {s}')
        else:
            print(f'{key}: {value}')

    print(tools.color(
        f"SIMULATED TIME {'%.2f'%manager.sim.clock}", 45))
    print(tools.color(f"EXECUTION TIME: {runtime}", 45))


if __name__ == "__main__":
    run()
