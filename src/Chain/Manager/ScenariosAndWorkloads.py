from ..Parameters import Parameters
from ..Network import Network
from .SystemEvents import ScenarioEvents as scenarioSE
from ..Simulation import Simulation

import json

def set_up_scenario(manager, scenario, config='scenario.yaml'):
    manager.load_params(config)

    with open(scenario, 'r') as f:
        scenario = json.load(f)

    Parameters.application['Nn'] = scenario['set_up']["num_nodes"]
    Parameters.calculate_fault_tolerance()

    Parameters.simulation['simTime'] = scenario['set_up']["duration"]
    Parameters.simulation['stop_after_blocks'] = -1
    Parameters.simulation['stop_after_tx'] = -1

    manager.sim = Simulation()
    manager.sim.manager = manager

    # set up network
    Network.nodes = manager.sim.nodes
    Network.parse_latencies()
    Network.parse_distances()
    Network.assign_location_to_nodes()
    Network.assign_neighbours()

    '''
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
    '''

    for key in scenario['intervals'].keys():
        interval = scenario['intervals'][key]
        start, end = interval['start'], interval['end']
        for key, value in interval.items():
            # schedule system events for each update interval
            match key:
                case 'transactions':
                    scenarioSE.schedule_scenario_transactions_event(
                        manager, value, start)
                case 'network':
                    scenarioSE.schedule_scenario_update_network_event(
                        manager, value, start-0.01)
                case 'faults':
                    if Parameters.simulation['simulate_faults']:
                        scenarioSE.schedule_scenario_fault_and_recovery_events(
                            manager, value)

    # schedule snapshot events if we have those in the config
    if Parameters.simulation["snapshot_interval"] != -1:
        scenarioSE.schedule_scenario_snapshot_event(manager)

    manager.sim.init_simulation()

def load_workload():
    with open(Parameters.simulation['workload'], 'r') as f:
        data = json.load(f)
    
    Parameters.simulation['stop_after_tx'] = len(data)
    Parameters.simulation['simTime'] = -1
    Parameters.simulation['stop_after_blocks'] = -1
    
    Parameters.tx_factory.add_scenario_transactions([x.values() for x in data])