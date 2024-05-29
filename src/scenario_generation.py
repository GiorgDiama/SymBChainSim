import json
from bisect import insort
import random

############### SEED ############
seed = 5
random.seed(seed)
############## SEED ############


def generate(name, parameters_dict):
    dur = parameters_dict['dur']
    ti_mu, ti_sigma = parameters_dict['ti_mu'], parameters_dict['ti_sigma']
    num_nodes = parameters_dict['num_nodes']
    networks = parameters_dict['networks']
    fail_duration = parameters_dict['fail_duration']
    workloads = parameters_dict['workloads']
    sizes = parameters_dict['sizes']

    fault_tolerance = int((num_nodes - 1)/3)
    no_faulty = random.randint(0, fault_tolerance)  # Range

    time_intervals = [i for i in range(
        0, dur, int(random.normalvariate(ti_mu, ti_sigma)))]

    time_intervals += [dur]

    time_interval_pairs = [(start, end) for start, end in zip(
        time_intervals[:-1], time_intervals[1:])]

    ids = [x for x in range(num_nodes)]

    faulty = random.sample(ids, k=no_faulty)

    scenario = {
        'set_up': {
            'num_nodes': num_nodes,
            'duration': time_intervals[-1],
            'parameters': parameters_dict
        },
        'intervals': {}
    }

    # each node gets a random network model assigned to it
    node_networks = [random.choice(networks) for _ in range(num_nodes)]

    tx_id = 0
    interval = 0
    for start, end in time_interval_pairs:
        print(f'Interval: {start}:{end}...')
        scenario['intervals'][interval] = {'start': start, 'end': end}
        scenario['intervals'][interval]['faults'] = []
        scenario['intervals'][interval]['network'] = []
        scenario['intervals'][interval]['transactions'] = []

        # select faulty nodes for current interval
        f = random.sample(faulty, k=random.randint(0, no_faulty))
        # generate faults
        for node_id in f:
            # Sample fail time and fail duration
            f_dur = random.normalvariate(*random.choice(fail_duration))
            f_time = random.randint(start, end)
            # ensure entire fault is inside the interval (can be problematic if d_dur is similar to interval_dur)
            # while f_time + f_dur > end:
            #     f_dur = random.normalvariate(*random.choice(fail_duration))
            #     f_time = random.randint(start, end)

            scenario['intervals'][interval]['faults'].append(
                (node_id, f_time, f_dur))

        # for each node, generate the interval BW based on its network model
        for node_id in ids:
            node_BW = max(random.normalvariate(*node_networks[node_id]), 2)
            scenario['intervals'][interval]['network'].append(
                (node_id, node_BW))

        # get the number of transactions based on one of the workloads
        num_txions = int(random.normalvariate(*random.choice(workloads)))
        # Generate the transactions
        transactions = []
        for _ in range(start, end):
            for tx in range(num_txions):
                tx_timestamp = random.uniform(start, end)
                tx_size = random.uniform(*sizes)
                tx_from = random.choice(ids)
                tx = (tx_from, tx_id, tx_timestamp, tx_size)
                insort(transactions, tx, key=lambda x: x[2])
                tx_id += 1

        scenario['intervals'][interval]['transactions'] = transactions
        interval += 1

    with open(f'Scenarios/{name}.json', 'w+') as f:
        json.dump(scenario, f, indent=4)


# parameters_dict = {
#     'dur': 3600,
#     'ti_mu': 600,
#     'ti_sigma': 60,
#     'num_nodes': 16,
#     'networks': [
#         (100, 10),  # E.g. Fiber
#         (50, 20),  # E.g. VDSL
#         (25, 5)  # E.g. ADSL
#     ],
#     'fail_duration': (
#         (20, 5),
#         (60, 10),
#         (120, 20)
#     ),
#     'workloads': [
#         (500, 100),
#         (1_000, 200),
#         (2_000, 500)
#     ],
#     'sizes': (8, 20.5),
# }

parameters_dict = {
    'dur': 600,
    'ti_mu': 300,
    'ti_sigma': 60,
    'num_nodes': 16,
    'networks': [
        (50, 20),  # E.g. VDSL
    ],
    'fail_duration': (
        (20, 5),
        (60, 10),
        (120, 20)
    ),
    'workloads': [
        (500, 200),
    ],
    'sizes': (.5, 3),
}

generate(name='test2', parameters_dict=parameters_dict)
