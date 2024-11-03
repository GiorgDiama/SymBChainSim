from ..Simulation import Simulation
from ..Parameters import Parameters
from ..Network import Network
from .. import Event

from ..Utils import tools
from ..Metrics import Metrics

from .ScenariosAndWorkloads import load_workload, set_up_scenario

from ..Manager import SimulationUpdates as updates

from ..Consensus.PBFT.PBFT_state import PBFT
from ..Consensus.BigFoot.BigFoot_state import BigFoot
from ..Consensus.Tendermint.TM_state import Tendermint

from .SystemEvents import GenerateTransactions as generate_txionsSE
from .SystemEvents import DynamicSimulation as dynamic_simulationSE
from .SystemEvents import BehaviourEvents as behaviourSE
from .SystemEvents import ScenarioEvents as scenarioSE

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
        Parameters.CPs = {
            PBFT.NAME: PBFT,
            BigFoot.NAME: BigFoot,
            Tendermint.NAME: Tendermint
        }

        self.sim = None

    ############################ SET UP AND CONFIGURATION ############################

    def load_params(self, config="base.yaml"):
        # ORDER: env_vars dictate path to config & cmd_args must overwrite parameters from config file
        tools.parse_env_vars()
        Parameters.load_params_from_config(config)
        tools.parse_cmd_args()

        Parameters.application["CP"] = Parameters.CPs[Parameters.simulation["init_CP"]]
        Parameters.simulation['event_id'] = 0 # used to give events incrementing, unique ids

    def set_up(self, num_nodes=-1):
        if num_nodes != -1:
            Parameters.application['Nn'] = num_nodes
            Parameters.calculate_fault_tolerance()

        # create simulator
        self.sim = Simulation()
        self.sim.manager = self

        # initialise network
        Network.init_network(self.sim.nodes)

        # schedule the systems event that manage the simulation
        self.init_system_events()

        # initialise blockchain simulation
        self.sim.init_simulation()

        if Parameters.simulation.get('workload', 'generate') != 'generate': 
            load_workload()

        if Parameters.simulation.get('print_info', False): 
            print(self.simulation_details_to_string())
        
    ############################ MANAGING SIMULATION ############################

    def finished(self):
        '''
            Evaluates all finish conditions for simulation
        '''
        # check if we have reached desired simulation duration
        if times_out := (Parameters.simulation["simTime"] != -1):
            times_out = self.sim.clock >= Parameters.simulation["simTime"]

        # check if the desired amount blocks have been confirmed
        if reached_blocks := (Parameters.simulation["stop_after_blocks"] != -1):
            reached_blocks = Metrics.confirmed_blocks(self.sim) >= Parameters.simulation["stop_after_blocks"]

        # check if we confirmed the desired amount of txs
        if processed_all := (Parameters.simulation['stop_after_tx'] != -1):
            curr_processed = [sum([len(block.transactions) for block in node.blockchain]) for node in self.sim.nodes]
            processed_all = all(map(lambda x: x >= Parameters.simulation['stop_after_tx'], curr_processed))

        # if any finish condition is true, return true else false
        return any([times_out, reached_blocks, processed_all])

    def run(self):
        ''' Managed simulation loop '''

        while not self.finished():
            self.sim.sim_next_event()
            self.update_sim()

        self.finalise()

    def update_sim(self):
        ''' Time based updates that are controlled by system events '''
        updates.print_progress(self.sim)
        updates.start_debug(self.sim)
        updates.interval_switch(self.sim)
        
    def finalise(self):
        ''' actions to be executed after simulation is finalised '''
        pass

    def init_system_events(self):
        ''' Sets up the events that dynamically manage the simulation '''

        if Parameters.simulation.get('workload', 'generate') == 'generate': 
            generate_txionsSE.schedule_event(self, init=True)

        if Parameters.dynamic_sim["use"]:
            dynamic_simulationSE.DynamicParameters.init_parameters()
            dynamic_simulationSE.schedule_update_network_event(self, init=True)
            dynamic_simulationSE.schedule_update_workload_event(self, init=True)

        if Parameters.simulation["snapshots"]:
            dynamic_simulationSE.schedule_snapshot_event(self)

        if Parameters.behaviour['use']:
            behaviourSE.Behaviour.init(self)
            behaviourSE.schedule_random_fault_event(self, self.sim.clock)


    ############################ EVENT PROCESSING AND SCHEDULING LOGIC ############################

    def schedule_system_event(self, time, payload):
        event = Event.SystemEvent(
            time=time,
            payload=payload
        )
        self.sim.q.add_event(event)

        # some callers need a reference to the created event
        return event 
    
    def handle_system_event(self, event):
        '''
            Manager specific event handler
        '''
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


    ############################ UTILITY ############################

    def simulation_details_to_string(self):
        s = tools.color("-"*28 + "NODE INFO" + '-'*28) + '\n'
        s += ("NODE\tLOCATION\tBANDWIDTH\tCP\tNEIGHBOURS") + '\n'
        for n in self.sim.nodes:
            neigh_list = ','.join([str(n.id) for n in n.neighbours])
            s += f"{'%3d'%n.id} {'%13s'%n.location}\t{'%.2f' % n.bandwidth}\t{'%10s'%n.cp.NAME}\t{'%12s'%neigh_list}" + '\n'

        s += tools.color("-"*25 + "SIM PARAMETERS" + '-'*25) + '\n'
        s += Parameters.parameters_to_string()

        return s