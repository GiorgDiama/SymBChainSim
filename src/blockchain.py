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

    # for block in manager.sim.nodes[0].blockchain[1:]:
    #     all_votes = block.extra_data['votes']
    #     time_pre_prep = block.time_created
    #     time_prep = all_votes['prepare'][-1][1]
    #     nodes = {}
    #     for type, votes in all_votes.items():
    #         for node, time, size in votes:
    #             entry = nodes.get(node, [])
    #             entry.append((type, time, size))
    #             nodes[node] = entry
    #     print(block.miner)
    #     for node_id, votes in nodes.items():
    #         for type, time, size in votes:
    #             print(node_id, '->', 0, ':', type, time, size)
    #             # if type == 'prepare':
    #             #     delay = time - time_pre_prep
    #             #     if delay != 0:
    #             #         print(
    #             #             f"{type}: It took {delay} to get {size} from node {node_id} speed {size/delay}")
    #             # elif type == 'commit':
    #             #     delay = time - time_prep
    #             #     if delay != 0:
    #             #         print(
    #             #             f"{type}: It took {delay} to get {size} from node {node_id} speed {size/delay}")

    #     exit()
    # import numpy as np
    # from Chain.Network import Network
    # res = np.divide(Network.avg_transmission_delay, Network.no_messages)
    # res = np.nan_to_num(res)

    # import matplotlib.pyplot as plt

    # plt.imshow(res)
    # # plt.show()

    # import statistics as st
    # for n in manager.sim.nodes:
    #     votes = n.cp.msgs

    #     for round, votes in votes.items():
    #         prep = votes['prepare']
    #         prep = [x[1]-min(prep, key=lambda x:x[1])[1] for x in prep]
    #         try:
    #             avg_prep = '%0.2f' % st.mean(prep)
    #         except:
    #             avg_prep = -1

    #         cnt_prep = len(prep)

    #         com = votes['commit']
    #         com = [x[1]-min(com, key=lambda x:x[1])[1] for x in com]
    #         try:
    #             avg_com = '%.2f' % st.mean(com)
    #         except:
    #             avg_com = -1

    #         cnt_com = len(com)

    #         # print(round, '\t', avg_prep, cnt_prep, '\t', avg_com, cnt_com)
    #     exit()


run()
