from datetime import datetime
from Chain.Parameters import Parameters
from Chain.Manager.Manager import Manager
import tracemalloc

import random
import numpy
import json
import sys

from Chain.Metrics import Metrics
import Chain.tools as tools

import statistics as st

############### SEEDS ############
if 'no_seed' not in sys.argv:
    seed = 10
    random.seed(seed)
    numpy.random.seed(seed)
############## SEEDS ############


def profile_memeory(num_nodes, num_repeats, cp, mempool):
    manager = Manager()

    mem = []
    for _ in range(num_repeats):
        tracemalloc.start()

        manager.load_params()
        Parameters.application['Nn'] = num_nodes
        Parameters.simulation['init_CP'] = cp
        Parameters.application['transaction_model'] = mempool

        manager.set_up(num_nodes)
        manager.run()

        mem.append(tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()

    return st.mean(mem)


def profile_runtime_NODES(num_nodes, num_repeats, cp, mempool):
    manager = Manager()

    runtimes = []
    simulated_clock = []
    for _ in range(num_repeats):
        manager.load_params()
        Parameters.application['Nn'] = num_nodes
        Parameters.simulation['init_CP'] = cp
        Parameters.application['transaction_model'] = mempool
        manager.set_up(num_nodes)
        t = datetime.now()
        manager.run()
        runtime = datetime.now() - t
        runtimes.append(runtime.total_seconds())
        simulated_clock.append(manager.sim.clock)

    return st.mean(runtimes), st.mean(simulated_clock)


def profile_runtime_TPS(TPS, num_nodes, num_repeats, cp, mempool):
    manager = Manager()

    runtimes = []
    simulated_clock = []
    for _ in range(num_repeats):
        manager.load_params('profiling.yaml')
        Parameters.simulation['init_CP'] = cp
        Parameters.application['transaction_model'] = mempool
        Parameters.application['Tn'] = TPS
        manager.set_up(num_nodes=num_nodes)

        t = datetime.now()
        manager.run()
        runtime = datetime.now() - t
        runtimes.append(runtime.total_seconds())
        simulated_clock.append(manager.sim.clock)

    return st.mean(runtimes), st.mean(simulated_clock)


def profile_memeory_TPS(TPS, num_nodes, num_repeats, cp, mempool):
    manager = Manager()

    mem = []
    for _ in range(num_repeats):
        tracemalloc.start()

        manager.load_params('profiling.yaml')
        Parameters.simulation['init_CP'] = cp
        Parameters.application['transaction_model'] = mempool
        Parameters.application['Tn'] = TPS
        manager.set_up(num_nodes=num_nodes)

        manager.set_up(num_nodes)
        manager.run()

        mem.append(tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()

    return st.mean(mem)


def profile_events(num_nodes, cp, mempool):
    # events produced are not affected by system processes so no need to repeat
    manager = Manager()

    events = {}
    manager.load_params()
    Parameters.application['Nn'] = num_nodes
    Parameters.simulation['init_CP'] = cp
    Parameters.application['transaction_model'] = mempool
    manager.set_up()
    manager.run()

    for key, value in Parameters.simulation['events'].items():
        if isinstance(value, int):
            events[key] = value
        else:
            events[key] = sum([v for v in value.values()])

    return events


def run_profile_experiment_NODES(name, cp, mempool):
    data = {}
    for num_nodes in range(5, 105, 5):
        wall_clock, simulation_time = profile_runtime_NODES(
            num_nodes, 3, cp, mempool)
        peak_memory = profile_memeory(num_nodes, -1, cp, mempool)
        print(f'{num_nodes}\t{wall_clock}\t{peak_memory}')
        data[num_nodes] = {
            'wall_clock': wall_clock,
            'peak_memory': peak_memory,
            'simulated_time': simulation_time
        }

    with open(f"Results/profiling_results_{name}.json", 'w+') as f:
        json.dump(data, f, indent=4)


def run_profile_events_experiment(name=''):
    data = {}
    for num_nodes in range(5, 105, 5):
        events = profile_events(num_nodes)

        print(f'{num_nodes}\t{events}')
        data[num_nodes] = {
            'events': events
        }

    with open(f"Results/profiling_events_{name}.json", 'w+') as f:
        json.dump(data, f, indent=4)


def run_profile_experiment_TPS(name, cp, mempool):
    data = {}
    num_nodes = 16
    for TPS in range(8_000, 20_000, 500):
        wall_clock = -1
        # wall_clock, simulation_time = profile_runtime_TPS(
        #     TPS, num_nodes, 3, cp, mempool)

        peak_memory = -1
        peak_memory = profile_memeory_TPS(TPS, num_nodes, 1, cp, mempool)
        print(f'{TPS}\t{wall_clock} - {peak_memory}')

        data[TPS] = {
            # 'wall_clock': wall_clock,
            'peak_memory': peak_memory,
            # 'simulated_time': simulation_time
        }

        with open(f"Results/profiling_results_{name}.json", 'w') as f:
            json.dump(data, f, indent=4)

# run_profile_experiment(name='final_parametersA_global(3avg_PBFT)',
#                        cp='PBFT',
#                        mempool='global')

# run_profile_experiment(name='final_parametersA_local(3avg_PBFT)',
#                        cp='PBFT',
#                        mempool='local')


# run_profile_events_experiment(name='parametersA(BigFoot)')


run_profile_experiment_TPS(name='local_TPS_3avg_PBFT_mem_8',
                           cp='PBFT',
                           mempool='local')


def profile_switch_overhead(TPS, num_nodes, mempool, name, name_extra):
    data = {}

    manager = Manager()

    manager.load_params('profiling_overhead.yaml')
    Parameters.application['transaction_model'] = mempool
    Parameters.application['Tn'] = TPS
    manager.set_up(num_nodes=num_nodes)

    if name == 'faults':
        manager.sim.nodes[1].kill()
        data['dead'] = [2]

    manager.run()

    for node in manager.sim.nodes:
        blocktimes = {'switch': [], 'normal': []}
        for b, nb in zip(node.blockchain[1:-1], node.blockchain[2:]):
            if b.consensus != nb.consensus:
                blocktimes['switch'].append(nb.time_added - b.time_added)
            else:
                blocktimes['normal'].append(nb.time_added - b.time_added)

        blocktimes['switch'] = blocktimes['switch']
        blocktimes['normal'] = blocktimes['normal']

        data[node.id] = blocktimes

    with open(f'Results/overhead_static_{name+name_extra}.json', 'w') as f:
        json.dump(data, f, indent=4)


def profile_switch_overhead_scenario(sc, mempool, name):
    manager = Manager()

    manager.set_up_scenario(
        f'Scenarios/{sc}.json', config='scenario_profiling_overhead.yaml')

    if name == 'no_fauts':
        Parameters.simulation['simulate_faults'] = False
    elif name == 'fauts':
        Parameters.simulation['simulate_faults'] = True

    Parameters.application['transaction_model'] = mempool

    manager.run()

    data = {}
    for node in manager.sim.nodes:
        blocktimes = {'switch': [], 'normal': []}
        for b, nb in zip(node.blockchain[1:-1], node.blockchain[2:]):
            if nb.time_added < b.time_added:
                print('problem')

            if b.consensus != nb.consensus:
                blocktimes['switch'].append(nb.time_added - b.time_added)
            else:
                blocktimes['normal'].append(nb.time_added - b.time_added)

        data[node.id] = blocktimes

    with open(f'Results/overhead_scenario_{sc}_{name}.json', 'w') as f:
        json.dump(data, f)


# profile_switch_overhead(1_000, 7, 'global', sys.argv[1], sys.argv[2])
# profile_switch_overhead_scenario(sys.argv[1], 'global', sys.argv[2])


def profile_mempool_latency(num_nodes, mempool, name=''):
    data = {}

    manager = Manager()

    manager.load_params('profiling_overhead.yaml')

    Parameters.application['use_tx_prop_model'] = '+' in mempool
    print(mempool, 'using prop model:',
          Parameters.application['use_tx_prop_model'])

    Parameters.application['transaction_model'] = mempool.strip('+')

    manager.set_up(num_nodes=num_nodes)

    manager.run()

    for node in manager.sim.nodes:
        node_data = {'tx_timestamps': [], 'avg_latency': []}
        for b in node.blockchain[1:]:
            sum_late = 0
            for tx in b.transactions:
                sum_late = b.time_added - tx.timestamp
                node_data['tx_timestamps'].append((tx.id, tx.timestamp))
            node_data['avg_latency'].append(sum_late / len(b.transactions))

        data[node.id] = node_data

    name = mempool if name == '' else mempool + '_' + name
    with open(f'Results/mempool_{name}.json', 'w') as f:
        json.dump(data, f, indent=4)


# if sys.argv[1] == 'all':
#     name = sys.argv[2]
#     profile_mempool_latency(8, 'global', name)
#     profile_mempool_latency(8, 'global+', name)
#     profile_mempool_latency(8, 'local', name)
# else:
#     name = '' if len(sys.argv) != 3 else sys.argv[2]
#     profile_mempool_latency(8, 'global', name)
