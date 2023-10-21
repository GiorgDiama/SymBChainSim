from datetime import datetime
from Chain.Parameters import Parameters
from Chain.Manager.Manager import Manager
import tracemalloc

import random
import numpy
import json

from Chain.Metrics import Metrics
import Chain.tools as tools

import statistics as st

# ############### SEEDS ############
# seed = 5
# random.seed(seed)
# numpy.random.seed(seed)
# ############## SEEDS ############


def profile_memeory(num_nodes, num_repeats):
    manager = Manager()

    mem = []
    for _ in range(num_repeats):
        tracemalloc.start()

        manager.load_params()
        manager.set_up(num_nodes)
        manager.run()

        mem.append(tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()

    return st.mean(mem)


def profile_runtime(num_nodes, num_repeats):
    manager = Manager()

    runtimes = []
    simulated_clock = []
    for _ in range(num_repeats):
        manager.load_params()
        manager.set_up(num_nodes)
        t = datetime.now()
        manager.run()
        runtime = datetime.now() - t
        runtimes.append(runtime.total_seconds())
        simulated_clock.append(manager.sim.clock)

    return st.mean(runtimes), st.mean(simulated_clock)


def run_profile_experiment(name=''):
    data = {}
    for num_nodes in range(5, 105, 5):
        wall_clock, simulation_time = profile_runtime(num_nodes, 3)
        peak_memory = profile_memeory(num_nodes, 1)
        print(f'{num_nodes}\t{wall_clock}\t{peak_memory}')
        data[num_nodes] = {
            'wall_clock': wall_clock,
            'peak_memory': peak_memory,
            'simulated_time': simulation_time
        }

    with open(f"Results/profiling_results_{name}.json", 'w+') as f:
        json.dump(data, f, indent=4)


run_profile_experiment(name='parametersA_local_with_prop')
