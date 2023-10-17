from datetime import datetime
from Chain.Parameters import Parameters
from Chain.Manager.Manager import Manager

import random
import numpy

from Chain.Consensus.PBFT.PBFT_state import PBFT
from Chain.Consensus.BigFoot.BigFoot_state import BigFoot

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

    print(tools.color(
        f"Simulated time {'%.2f'%manager.sim.clock} seconds!", 45))

    # Metrics.save_snapshots("snapshot")
    Metrics.measure_all(manager.sim)
    Metrics.print_metrics()

    s = f"{'-'*30} EVENTS {'-'*30}"
    print(tools.color(s, 41))
    print(Parameters.simulation['events'])

    print(tools.color(f"SIMULATION EXECUTION TIME: {runtime}", 45))


# def test_plot():
#     import json
#     import matplotlib.pyplot as plt

#     with open(f"results/snapshot.json", "r") as f:
#         data = json.load(f)

#     times = []
#     throughputs = []

#     for key, value in data.items():
#         times.append(value['time'])
#         throughputs.append(value["metrics"]['throughput']['0'])
#         bws = [value['nodes'][key]['bandwidth'] for key in value['nodes']]

#     import matplotlib.pyplot as plt
#     import matplotlib as mpl

#     mpl.use("pgf")

#     plt.plot(range(10))
#     plt.savefig("test.pdf")


run()
# test_plot()
