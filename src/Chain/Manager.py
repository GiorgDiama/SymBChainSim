from Chain.Simulation import Simulation
from Chain.Parameters import Parameters
from Chain.Network import Network
from Chain.Node import Node
from Chain.Event import SystemEvent

from Chain.Consensus.PBFT.PBFT import PBFT
from Chain.Consensus.BigFoot.BigFoot import BigFoot

import Chain.tools as tools

import Chain.Consensus.HighLevelSync as Sync

from random import randint, sample, choice, expovariate, normalvariate

import math
import sys
import os

CPs = {
    PBFT.NAME: PBFT,
    BigFoot.NAME: BigFoot
}


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
        self.behaviour = None

    def set_up(self):
        '''
            Initial tasks required for the simulation to start
        '''
        # load params (cmd and env)
        tools.set_env_vars_from_config()
        Parameters.load_params_from_config()

        Parameters.application["CP"] = CPs[Parameters.simulation["init_CP"]]

        # create simulator
        self.sim = Simulation()
        self.sim.manager = self

        # initialise network
        Network.init_network(self.sim.nodes)

        # initialise behaviour module
        self.behaviour = Behaiviour(self.sim)

        # initialise simulation
        self.sim.init_simulation()

        # schedule the first system events
        self.init_system_events()

    def init_system_events(self):
        '''
            Sets up initial events 
            (most system events are recurring meaning its only necessary to manually schedule the first one )
        '''
        self.schedule_apply_behavior_event()

        self.schedule_generate_txions_event()

        if Parameters.simulation["interval_switch"]:
            self.schedule_change_cp_event()

    def change_cp(self, cp):
        '''
            changes the CP of the system (cp can be either a reference to a cp protocol or a string)
        '''
        if isinstance(cp, str):
            cp = CPs[cp]

        tools.debug_logs(
            msg=f"WILL CHANGE CP TO {cp.NAME}", input="RETURN TO CONFIRM...", col=42)

        Parameters.application["CP"] = cp

    def add_node(self):
        '''
            Adds a node taking part in the consensus process
        '''
        # change number of nodes in the parameters and recalculate fault tolerance
        Parameters.application["Nn"] += 1
        Parameters.calculate_fault_tolerance()

        # create node and gensis block
        node = Node(self.sim.nodes[-1].id+1)
        node.add_block(self.sim.nodes[0].blockchain[0].copy(), self.sim.clock)

        # assign a location and neighbours to node
        Network.assign_location_to_nodes(node)
        Network.assign_neighbours(node)

        for n in node.neighbours:
            n.neighbours.append(node)

        Network.set_bandwidths(node)

        # also appends txion factory since the nodes there are a reference to the sim nodes
        self.sim.nodes.append(node)
        Network.nodes = self.sim.nodes

        # bring the new node up to date and begin the syncing process
        node.update(self.sim.clock)

        node.state.synced = False
        Sync.create_local_sync_event(
            node, choice(node.neighbours), self.sim.clock)

    def remove_node(self):
        '''
            removes a node taking part in the consensus process
        '''
        # update fault tolerance and remove node
        Parameters.application["Nn"] -= 1
        Parameters.calculate_fault_tolerance()

        rem_node = self.sim.nodes.pop()

        '''
            TODO / BUG:
                Removing a node will not update the neighbours of nodes!
            
            TEMP WORKAROUND: 
                reassign the neibhours of nodes that had the removed node in their neighbour list

            ideally, they would do that once they realised that the node is not there anymore
        '''

        for node in self.sim.nodes:
            if rem_node in node.neighbours:
                Network.assign_neighbours(node)

    def update_sim(self):
        '''
            Time based updates that are not controlled by system events can be triggered here
        '''
        ################ Start debug at time #################
        if 'start_debug' in os.environ and int(os.environ['start_debug']) <= self.sim.clock:
            os.environ['debug'] = "True"

    def finished(self):
        # TODO: Move this to metrics
        def confirmed_blocks(simulation):
            return min([n.blockchain_length() for n in simulation.nodes])

        # check if we have reached desired time
        times_out = (Parameters.simulation["simTime"] != -1 and
                     self.sim.clock >= Parameters.simulation["simTime"])

        # check if desired amount blocks have been confirmed
        reached_blocks = (Parameters.simulation["stop_after_blocks"] != -1 and
                          confirmed_blocks(self.sim) >= Parameters.simulation["stop_after_blocks"])

        finish_conditions = [times_out, reached_blocks]

        return any(finish_conditions)

    def run(self):
        ''' Managed simulation loop'''
        self.behaviour.update_behaviour()

        # while self.sim.clock <= Parameters.simulation['simTime']:
        while not self.finished():
            self.sim.sim_next_event()
            self.update_sim()

    ################################################################################################
            ################ SYSTEM EVENTS #################
    ################################################################################################

    def handle_next_event(self, event):
        match event.payload["type"]:
            case "apply_behavior":
                self.handle_apply_behavior_event(event)
            case "node fault":
                self.handle_node_fault_event(event)
            case "node recovery":
                self.handle_node_recovery_event(event)
            case "generate_txions":
                self.handle_generate_txions_event(event)
            case "change_cp":
                self.handle_change_cp_event(event)

    ################################################################################################
            ################ APPLY BEHAVIOUR #################
    ################################################################################################

    def schedule_apply_behavior_event(self):
        event = SystemEvent(
            time=self.sim.clock + Parameters.behaiviour["behaviour_interval"],
            payload={"type": "apply_behavior"}
        )

        self.sim.q.add_event(event)

    def handle_apply_behavior_event(self, event):
        # Random CP Change
        if "rand-cp" in sys.argv:
            if randint(0, 100) < 10:
                self.change_cp(choice(list(CPs.values())))

        # apply behaviour
        self.behaviour.apply_behavior()
        self.schedule_apply_behavior_event()

    ################################################################################################
        ################ CHANGE CP #################
    ################################################################################################

    def schedule_change_cp_event(self):
        if Parameters.simulation["interval_switch"]:
            time = self.sim.clock + normalvariate(30, 5)
            cp = PBFT if Parameters.application["CP"] == BigFoot else BigFoot

        event = SystemEvent(
            time=time,
            payload={
                "type": "change_cp",
                "cp": cp
            }
        )

        self.sim.q.add_event(event)

    def handle_change_cp_event(self, event):
        self.change_cp(event.payload["cp"])
        self.schedule_change_cp_event()

    ################################################################################################
        ################ GENERATE TXIONS #################
    ################################################################################################

    def schedule_generate_txions_event(self):
        time = self.sim.clock + Parameters.application["TI_dur"]

        event = SystemEvent(
            time=time,
            payload={
                "type": "generate_txions",
            }
        )
        self.sim.q.add_event(event)

    def handle_generate_txions_event(self, event):
        Parameters.simulation['txion_model'].generate_interval_txions(
            event.time)

        # schedule txion generation for next interval
        self.schedule_generate_txions_event()

    def handle_node_fault_event(self, event):
        event.payload["node"].kill()
        recovery_time = event.time + \
            expovariate(1/event.payload["node"].behaviour.mean_recovery_time)
        event = SystemEvent(
            time=recovery_time,
            payload={"type": "node recovery",
                     "node": event.payload["node"]
                     }
        )
        event.payload["node"].behaviour.recovery_event = event
        self.sim.q.add_event(event)

    def handle_node_recovery_event(self, event):
        event.payload["node"].resurect()
        event.payload["node"].behaviour.recovery_event = None
        event.payload["node"].behaviour.fault_event = None


class Behaiviour:
    def __init__(self, sim) -> None:
        self.sim = sim
        self.faulty = []
        self.byzantine = []

    def update_behaviour(self):
        self.set_faulty_nodes()
        self.set_byzantine_nodes()

    def set_byzantine_nodes(self):
        byzantine_params = Parameters.behaiviour["byzantine_nodes"]
        sync_params = Parameters.behaiviour["sync"]

        self.byzantine = sample(
            self.sim.nodes, byzantine_params["num_byzantine"])

        for node in self.byzantine:
            node.behaviour.byzantine = True
            node.behaviour.sync_fault_chance = randint(sync_params["probs"]["low"],
                                                       sync_params["probs"]["high"])

    def set_faulty_nodes(self, node=None):
        fault_params = Parameters.behaiviour["crash_probs"]

        self.faulty = sample(self.sim.nodes, fault_params["faulty_nodes"])

        for node in self.faulty:
            node.behaviour.faulty = True

            node.behaviour.mean_fault_time = randint(
                fault_params["mean_fault_time"]['low'],
                fault_params["mean_fault_time"]["high"]
            )

            node.behaviour.mean_recovery_time = randint(
                fault_params["mean_recovery_time"]['low'],
                fault_params["mean_recovery_time"]["high"]
            )

    def apply_behavior(self):
        if "behaviour-off" in sys.argv:
            return 0

        ################ FAULT LOGIC ########################
        for fnode in self.faulty:
            if fnode.state.alive and (fnode.behaviour.fault_event is None or fnode.behaviour.fault_event.time > Parameters.simulation["simTime"]):
                next_fault_time = self.sim.clock + \
                    expovariate(1/fnode.behaviour.mean_fault_time)

                event = SystemEvent(
                    time=next_fault_time,
                    payload={"type": "node fault",
                             "node": fnode
                             }
                )

                if fnode.behaviour.fault_event is not None:
                    self.sim.q.remove_event(fnode.behaviour.fault_event)

                fnode.behaviour.fault_event = event
                self.sim.q.add_event(event)
