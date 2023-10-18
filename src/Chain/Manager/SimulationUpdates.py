from Chain.Parameters import Parameters
from Chain.Network import Network
import Chain.tools as tools
from Chain.Node import Node
from Chain.Metrics import Metrics

import Chain.Consensus.HighLevelSync as Sync

from random import choice


def print_progress(sim):
    if "print_next" not in Parameters.simulation:
        Parameters.simulation["print_next"] = 0

    if sim.clock >= Parameters.simulation["print_next"]:
        Parameters.simulation['print_next'] += Parameters.simulation["print_every"]

        s = f'Clock: {"%.2f"%sim.clock} \t Confirmed blocks: {Metrics.confirmed_blocks(sim)}'
        print(tools.color(s, 44))


def start_debug(sim):
    if 'start_debugging_at' in Parameters.simulation and sim.clock >= Parameters.simulation['start_debugging_at']:
        Parameters.simulation["debugging_mode"] = True


def change_cp(cp):
    '''
        changes the CP of the system (cp can be either a reference to a cp protocol or a string)
    '''
    if isinstance(cp, str):
        cp = Parameters.CPs[cp]

    tools.debug_logs(
        msg=f"WILL CHANGE CP TO {cp.NAME}", input="RETURN TO CONFIRM...", col=42)

    Parameters.application["CP"] = cp


def add_node(sim):
    '''
        Adds a node taking part in the consensus process
    '''
    # change number of nodes in the parameters and recalculate fault tolerance
    Parameters.application["Nn"] += 1
    Parameters.calculate_fault_tolerance()

    # create node and gensis block
    node = Node(sim.nodes[-1].id+1)
    node.add_block(sim.nodes[0].blockchain[0].copy(), sim.clock)

    # assign a location and neighbours to node
    Network.assign_location_to_nodes(node)
    Network.assign_neighbours(node)

    for n in node.neighbours:
        n.neighbours.append(node)

    Network.set_bandwidths(node)

    # also appends txion factory since the nodes there are a reference to the sim nodes
    sim.nodes.append(node)
    Network.nodes = sim.nodes

    # bring the new node up to date and begin the syncing process
    node.update(sim.clock)

    node.state.synced = False
    Sync.create_local_sync_event(
        node, choice(node.neighbours), sim.clock)


def remove_node(sim):
    '''
        removes a node taking part in the consensus process
    '''
    # update fault tolerance and remove node
    Parameters.application["Nn"] -= 1
    Parameters.calculate_fault_tolerance()

    rem_node = sim.nodes.pop()

    '''
        TODO / BUG:
            Removing a node will not update the neighbours.
        
        TEMP WORKAROUND: 
            reassign the neighbours of nodes that had the removed node in their neighbour list

        ideally, they would do that once they realised that the node is not there anymore
    '''

    for node in sim.nodes:
        if rem_node in node.neighbours:
            Network.assign_neighbours(node)
