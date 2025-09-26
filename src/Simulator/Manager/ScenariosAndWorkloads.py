from Parameters import Parameters

from Chain.Network import Network
from Chain.TransactionFactory import TransactionFactory

from Engine.Simulation import Simulation

from Manager.SystemEvents import ScenarioEvents as scenarioSE
from Manager.SystemEvents import SnapshotEvents as snapshotSE

import json

PATH_TO_SCENARIOS = "../Resources/Scenarios/"

def set_up_scenario(manager, scenario, config="scenario.yaml"):
    manager.load_params(config)
    
    with open(PATH_TO_SCENARIOS + scenario +'.json', "r") as f:
        scenario = json.load(f)

    Parameters.application["Nn"] = scenario["set_up"]["num_nodes"]
    Parameters.calculate_fault_tolerance()

    Parameters.simulation["simTime"] = scenario["set_up"]["duration"]
    Parameters.simulation["stop_after_blocks"] = -1
    Parameters.simulation["stop_after_tx"] = -1

    manager.sim = Simulation()
    manager.sim.manager = manager

    # set up network
    Network.init_network(manager.sim.nodes)

    """
        Scenario JSON Schema
            'set_up':
                num_nodes
                duration
            'intervals:
                '1':
                    'start: start_time,
                    'end': end_time
                    'network' : [(node, BW)...]
                    'behaviour': [(node, fail_at, duration)]
                    'transactions': [(creator, id, timestamp, size)...]
                '2':  ...
    """

    for key in scenario["intervals"].keys():
        interval = scenario["intervals"][key]
        start, end = interval["start"], interval["end"]
        for key, value in interval.items():
            # schedule system events for each update interval
            match key:
                case "transactions":
                    scenarioSE.schedule_scenario_transactions_event(
                        manager, value, start
                    )
                case "network":
                    scenarioSE.schedule_scenario_update_network_event(
                        manager, value, start
                    )
                case "faults":
                    if Parameters.simulation["simulate_faults"]:
                        scenarioSE.schedule_scenario_fault_and_recovery_events(
                            manager, value
                        )

    if Parameters.simulation["snapshot_interval"] != -1:
        snapshotSE.schedule_snapshot_event(manager)

    manager.sim.init_simulation()


def load_workload():
    with open(Parameters.simulation["workload"], "r") as f:
        data = json.load(f)

    Parameters.simulation["stop_after_tx"] = len(data)
    Parameters.simulation["simTime"] = -1
    Parameters.simulation["stop_after_blocks"] = -1

    TransactionFactory.add_scenario_transactions([x.values() for x in data])
