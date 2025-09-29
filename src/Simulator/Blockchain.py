from Parameters import Parameters

from Manager.Manager import Manager
import Manager.ScenariosAndWorkloads as Scenario

from Utils.Metrics import Metrics
from Utils import Tools

import pprint
import sys
import random
import numpy as np
from datetime import datetime

############### SEEDS ############
seed = 1837413
random.seed(seed)
np.random.seed(seed)
############## SEEDS ############


def run():
    manager = Manager()

    if (conf := Tools.get_named_cmd_arg("--conf")) is None:
        conf = "base.yaml"

    manager.load_params(conf)
    manager.set_up()
    t = datetime.now()
    manager.run()
    runtime = datetime.now() - t

    print(Tools.color(f"{'-' * 30} BLOCKS {'-' * 30}", 42))
    Tools.get_blocks_by_cp(manager.sim)

    Metrics.measure_all(manager.sim)
    Metrics.print_metrics()

    print(Tools.color(f"{'-' * 30} EVENTS {'-' * 30}", 43))
    Tools.print_events()

    print(Tools.color(f"SIMULATED TIME: {manager.sim.clock:0.2f} seconds", 45))
    print(Tools.color(f"EXECUTION TIME: {runtime} seconds", 45))


def run_scenario(scenario_name):
    manager = Manager()
    Scenario.set_up_scenario(manager, scenario_name, config="scenario.yaml")

    t = datetime.now()
    manager.run()
    runtime = datetime.now() - t

    Tools.get_blocks_by_cp(manager.sim)

    Metrics.measure_all(manager.sim)
    Metrics.print_metrics()

    print(Tools.color(f"{'-' * 30} EVENTS {'-' * 30}", 43))
    Tools.print_events()

    print(Tools.color(f"SIMULATED TIME: {manager.sim.clock:0.1f} seconds", 45))
    print(Tools.color(f"EXECUTION TIME: {runtime} seconds", 45))


if __name__ == "__main__":
    if "--sc" in sys.argv:
        name = Tools.get_named_cmd_arg("--sc")
        run_scenario(scenario_name=name)
    else:
        run()
