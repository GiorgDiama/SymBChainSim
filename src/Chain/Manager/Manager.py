from Chain.Simulation import Simulation
from Chain.Parameters import Parameters
from Chain.Network import Network
from Chain.Metrics import Metrics

import Chain.tools as tools

from Chain.Consensus.PBFT.PBFT_state import PBFT
from Chain.Consensus.BigFoot.BigFoot_state import BigFoot

import Chain.Manager.SystemEvents.GenerateTransactions as generate_txionsSE

import sys


class Manager:
    '''
        The manager module controlls the 'flow' of the simulation. Through system events
            e.g., transactions are generated
    '''

    def __init__(self) -> None:
        self.sim = None

    def load_params(self, config="base.yaml"):
        # load params
        Parameters.load_params_from_config(config)
        tools.parse_cmd_args()

        Parameters.CPs = {
            PBFT.NAME: PBFT,
            BigFoot.NAME: BigFoot
        }

        Parameters.application["CP"] = Parameters.CPs[Parameters.simulation["init_CP"]]

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

        if Parameters.simulation['print_info']:
            print(self.simulation_details())

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
            self.update()

    def update(self):
        # add logic here to manage the simulation during runtime
        # idealy runtime updates would be modeled by system events (e.g., transaction generation)
        # but logic can be added here for conviniance
        pass

    def init_system_events(self):
        '''
            Sets up initial events 
        '''
        # generates the transactions every time interval
        generate_txionsSE.schedule_event(self, init=True)


    def handle_system_event(self, event):
        match event.payload["type"]:
            ################## TRANSACTION GENERATION EVENTS ##################
            case "generate_txions":
                generate_txionsSE.handle_event(self, event)
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
