from Chain.Simulation import Simulation
from Chain.Parameters import Parameters
from Chain.Network import Network
from Chain.Metrics import Metrics

import Chain.Manager.SimulationUpdates as updates

import Chain.tools as tools

from Chain.Consensus.PBFT.PBFT_state import PBFT
from Chain.Consensus.BigFoot.BigFoot_state import BigFoot
from Chain.Consensus.Tendermint.TM_state import Tendermint

import Chain.Manager.SystemEvents.GenerateTransactions as generate_txionsSE
import Chain.Manager.SystemEvents.DynamicSimulation as dynamic_simulationSE
import Chain.Manager.SystemEvents.BehaviourEvents as behaviourSE
import Chain.Manager.SystemEvents.ScenarioEvents as scenarioSE

import json
import sys


class Manager:
    '''
        The manager module controls the 'flow' of the simulation. Through system events
            - The state of the system can be updated during runtime
            - transactions are generated
            - nodes are added and removed
            - node behaviour is applied and managed
    '''

    def __init__(self) -> None:
        self.sim = None

    def load_params(self, config="base.yaml"):
        # load params
        Parameters.load_params_from_config(config)
        tools.parse_cmd_args()

        Parameters.CPs = {
            PBFT.NAME: PBFT,
            BigFoot.NAME: BigFoot,
            Tendermint.NAME: Tendermint
        }

        Parameters.application["CP"] = Parameters.CPs[Parameters.simulation["init_CP"]]

    def set_up_scenario(self, scenario, config='scenario.yaml'):
        self.load_params(config)

        with open(scenario, 'r') as f:
            scenario = json.load(f)

        Parameters.application['Nn'] = scenario['set_up']["num_nodes"]
        Parameters.calculate_fault_tolerance()

        Parameters.simulation['simTime'] = scenario['set_up']["duration"]
        Parameters.simulation['stop_after_blocks'] = -1

        self.sim = Simulation()
        self.sim.manager = self

        # set up network
        Network.nodes = self.sim.nodes
        Network.parse_latencies()
        Network.parse_distances()
        Network.assign_location_to_nodes()
        Network.assign_neighbours()

        '''
            SC Schema
                'set_up': 
                    num_nodes
                    duration
                'intervals:
                    '1':
                        'network':[(node, BW)...]
                        'behaviour':[(node, fail_at, duration)]
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
                            self, value, start)
                    case 'network':
                        scenarioSE.schedule_scenario_update_network_event(
                            self, value, start-0.01)
                    case 'faults':
                        if Parameters.simulation['simulate_faults']:
                            scenarioSE.schedule_scenario_fault_and_recovery_events(
                                self, value)

        # schedule snapshot events if we have those in the config
        if Parameters.simulation["snapshot_interval"] != -1:
            scenarioSE.schedule_scenario_snapshot_event(self)

        self.sim.init_simulation()

    def load_workload(self):
        with open(Parameters.simulation['workload'],'r') as f:
            data = json.load(f)
        
        Parameters.simulation['stop_after_tx'] = len(data)
        Parameters.simulation['simTime'] = -1
        Parameters.simulation['stop_after_blocks'] = -1
        

        Parameters.tx_factory.add_scenario_transactions([x.values() for x in data])

    def set_up(self, num_nodes=-1):
        '''
            Initial tasks required for the simulation to start
        '''
        if num_nodes != -1:
            Parameters.application['Nn'] = num_nodes
            Parameters.calculate_fault_tolerance()

        # create simulator
        self.sim = Simulation()
        self.sim.manager = self

        # initialise network
        Network.init_network(self.sim.nodes)

        # schedule the first system events
        self.init_system_events()

        # initialise simulation
        self.sim.init_simulation()

        if Parameters.simulation['workload'] != 'generate':
            self.load_workload()

        if Parameters.simulation['print_info']:
            print(self.simulation_details())

    def finished(self):
        # check if we have reached desired simulation duration
        if Parameters.simulation["simTime"] != -1:
            times_out = self.sim.clock >= Parameters.simulation["simTime"]
        else:
            times_out = False

        # check if the desired amount blocks have been confirmed
        if Parameters.simulation["stop_after_blocks"] != -1:
            reached_blocks = Metrics.confirmed_blocks(self.sim) >= Parameters.simulation["stop_after_blocks"]
        else:
            reached_blocks = False

        # check if we confirmed the desired amount of txs
        if Parameters.simulation['stop_after_tx'] != -1:
            curr_processed = [sum([len(block.transactions) for block in node.blockchain]) for node in self.sim.nodes]
            processed_all = all(map(lambda x: x >= Parameters.simulation['stop_after_tx'], curr_processed))
        else:
            processed_all = False

        finish_conditions = [times_out, reached_blocks, processed_all]

        # if any finish condition is true, return true else false
        return any(finish_conditions)

    def run(self):
        ''' Managed simulation loop'''

        while not self.finished():
            self.sim.sim_next_event()
            self.update_sim()

        self.finalise()

    def update_sim(self):
        '''
            Time based updates that are not controlled by system events can be triggered here
        '''
        updates.print_progress(self.sim)
        updates.start_debug(self.sim)
        updates.interval_switch(self.sim)

    def finalise(self):
        if Parameters.simulation.get('snapshots', False) or \
                Parameters.simulation.get('snapshot_interval', -1) != -1:

            if '-n' in sys.argv:
                idx = sys.argv.index('-n') + 1
                name = sys.argv[idx]

            Metrics.save_snapshots(name)

    def init_system_events(self):
        '''
            Sets up initial events 
        '''
        
        if Parameters.simulation['workload'] == 'generate':
            # generates the transactions every time interval
            generate_txionsSE.schedule_event(self, init=True)

        if Parameters.dynamic_sim["use"]:
            # if we are using dynamic simulation: load events that handle the dynamic updates
            dynamic_simulationSE.DynamicParameters.init_parameters()
            dynamic_simulationSE.schedule_update_network_event(self, init=True)
            dynamic_simulationSE.schedule_update_workload_event(
                self, init=True)

        if Parameters.simulation["snapshots"]:
            # if snapshots is true, add the event that periodically takes the snapshots
            dynamic_simulationSE.schedule_snapshot_event(self)

        if Parameters.behaviour['use']:
            behaviourSE.Behaviour.init(self)
            behaviourSE.schedule_random_fault_event(self, self.sim.clock)

    def handle_system_event(self, event):
        match event.payload["type"]:
            ################## TRANSACTION GENERATION EVENTS ##################
            case "generate_txions":
                generate_txionsSE.handle_event(self, event)
            ################## DYNAMIC SIMULATION EVENTS ##################
            case "update_network":
                dynamic_simulationSE.handle_update_network_event(self, event)
            case "update_workload":
                dynamic_simulationSE.handle_update_workload_event(self, event)
            case "snapshot":
                dynamic_simulationSE.handle_snapshot_event(self, event)
            ################## BEHAVIOUR EVENTS ##################
            case "random_fault":
                behaviourSE.handle_random_fault_event(self, event)
            case "recovery":
                behaviourSE.handle_recover_event(self, event)
            ################## SCENARIO EVENTS ##################
            case 'scenario_generate_txions':
                scenarioSE.handle_scenario_transactions_event(self, event)
            case 'scenario_update_network':
                scenarioSE.handle_scenario_update_network_event(self, event)
            case 'scenario_fault':
                scenarioSE.handle_scenario_fault_event(self, event)
            case 'scenario_recovery':
                scenarioSE.handle_scenario_recovery_event(self, event)
            case 'scenario_snapshot':
                scenarioSE.handle_scenario_snapshot_event(self, event)
            ################## DEFAULT ##################
            case _:
                raise ValueError(
                    f"Event '{event.payload['type']}'was not handled by its own handler...")

    def simulation_details(self):
        s = tools.color("-"*28 + "NODE INFO" + '-'*28) + '\n'
        s += ("NODE\tLOCATION\tBANDWIDTH\tCP\tNEIGHBOURS") + '\n'
        for n in self.sim.nodes:
            neigh_list = ','.join([str(n.id) for n in n.neighbours])
            s += f"{'%3d'%n.id} {'%13s'%n.location}\t{'%.2f' % n.bandwidth}\t{'%10s'%n.cp.NAME}\t{'%12s'%neigh_list}" + '\n'

        s += tools.color("-"*25 + "SIM PARAMETERS" + '-'*25) + '\n'
        s += Parameters.parameters_to_string()

        return s
