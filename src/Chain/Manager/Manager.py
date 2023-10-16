from Chain.Simulation import Simulation
from Chain.Parameters import Parameters
from Chain.Network import Network
from Chain.Metrics import Metrics

import Chain.Manager.SimulationUpdates as updates

import Chain.tools as tools

from Chain.Consensus.PBFT.PBFT import PBFT
from Chain.Consensus.BigFoot.BigFoot import BigFoot

import Chain.Manager.SystemEvents.GenerateTransactions as generate_txionsSE
import Chain.Manager.SystemEvents.DynamicSimulation as dynamic_simulationSE


class Manager:
    '''
        The manager module controlls the 'flow' of the simulation. Through system events
            - The state of the system can be updated during runtime
            - transactions are generated
            - nodes are added and removed
            - node behaviour is applied and managed
    '''

    def __init__(self) -> None:
        self.sim = None

    def set_up(self, config="base.yaml"):
        '''
            Initial tasks required for the simulation to start
        '''
        # load params
        Parameters.load_params_from_config(config)
        tools.parse_cmd_args()

        Parameters.CPs = CPs = {
            PBFT.NAME: PBFT,
            BigFoot.NAME: BigFoot
        }

        Parameters.application["CP"] = CPs[Parameters.simulation["init_CP"]]

        # create simulator
        self.sim = Simulation()
        self.sim.manager = self

        # initialise network
        Network.init_network(self.sim.nodes)

        # schedule the first system events
        self.init_system_events()

        # initialise simulation
        self.sim.init_simulation()

    def finished(self):
        # check if we have reached desired simulation duration
        times_out = (Parameters.simulation["simTime"] != -1 and
                     self.sim.clock >= Parameters.simulation["simTime"])

        # check if the desired amount blocks have been confirmed
        reached_blocks = (Parameters.simulation["stop_after_blocks"] != -1 and
                          Metrics.confirmed_blocks(self.sim) >= Parameters.simulation["stop_after_blocks"])

        finish_conditions = [times_out, reached_blocks]

        # if any finish condition is true, return true else false
        return any(finish_conditions)

    def run(self):
        ''' Managed simulation loop'''

        while not self.finished():
            self.sim.sim_next_event()
            self.update_sim()

        print()

    def update_sim(self):
        '''
            Time based updates that are not controlled by system events can be triggered here
        '''
        updates.print_progress(self.sim)

    def init_system_events(self):
        '''
            Sets up initial events 
        '''
        generate_txionsSE.schedule_event(self, init=True)

        if Parameters.dynamic_sim["use"]:
            dynamic_simulationSE.DynamicParameters.init_parameters()
            dynamic_simulationSE.schedule_update_network_event(self, init=True)
            dynamic_simulationSE.schedule_update_workload_event(
                self, init=True)

        if Parameters.simulation["snapshots"]:
            dynamic_simulationSE.schedule_snapshot_event(self)

    def handle_system_event(self, event):
        match event.payload["type"]:
            case "generate_txions":
                generate_txionsSE.handle_event(self, event)
            case "update_network":
                dynamic_simulationSE.handle_update_network_event(self, event)
            case "update_workload":
                dynamic_simulationSE.handle_update_workload_event(self, event)
            case "snapshot":
                dynamic_simulationSE.handle_snapshot_event(self, event)
            case _:
                raise ValueError("Event was not handled by its own handler...")
