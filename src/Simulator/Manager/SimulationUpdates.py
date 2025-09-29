from Parameters import Parameters

from Chain.Network import Network
from Chain.Node import Node
from Chain.Consensus import HighLevelSync

from Utils.Metrics import Metrics
from Utils import Tools


import random

"""
    Simulation Updates are a less dynamic method of updating the simulation.
    These are less powerful than SystemEvent based updates but can be useful
    for simple functions like periodically printing some information etc...
    THESE ARE NOT EVENTS! Simulation Update logic is ONLY triggered after
    an event. Thus logic that needs to be trigger periodically cannot have a
    static period using simulation updates - it will trigger alongside the
    first event that takes place after a period is completed.

    If doing the desired action at a specific time is important use SystemEvents!
"""


def print_progress(sim):
    if "print_next" not in Parameters.simulation:
        Parameters.simulation["print_next"] = 0

    if sim.clock >= Parameters.simulation["print_next"] and Parameters.simulation["print_every"] != -1:
        Parameters.simulation["print_next"] += Parameters.simulation["print_every"]

        sim_time = f"Simulation time: {'%.2f' % sim.clock:>10} out of {Parameters.simulation['simTime']}"
        blocks = f"Confirmed blocks: {Metrics.confirmed_blocks(sim):>5} out of {Parameters.simulation['stop_after_blocks']}"
        tx = f"Confirmed Transactions {Metrics.processed_tx_system(sim):>10} out of {Parameters.simulation['stop_after_tx']}"

        s = f"{sim_time}\t{blocks}\t{tx}"

        print(Tools.color(s, 44))


def start_debug(sim):
    """
    Starts the built-in debugger at a specific time
    """
    if "start_debugging_at" in Parameters.simulation and sim.clock >= Parameters.simulation["start_debugging_at"]:
        Parameters.simulation["debugging_mode"] = True


# def add_node(sim):
#     """
#     Adds a node taking part in the consensus process
#     This a centralised approach where a single entity
#     can control the membership
#     """
#     print(
#         f"WARNING: 'add_node' has some shortcomings in its current \
#           implementation! ensure these do not affect your results!"
#     )

#     Parameters.application["Nn"] += 1
#     Parameters.calculate_fault_tolerance()

#     node = Node(sim.nodes[-1].id + 1)
#     node.add_block(sim.nodes[0].blockchain[0].copy(), sim.clock)

#     Network.assign_location_to_nodes(node)

#     Network.assign_neighbours(node)
#     for n in node.neighbours:
#         n.neighbours.append(node)

#     Network.set_bandwidths(node)

#     sim.nodes.append(node)
#     Network.nodes = sim.nodes

#     node.update(sim.clock)

#     node.state.synced = False
#     HighLevelSync.create_local_sync_event(
#         node, random.choice(node.neighbours), sim.clock
#     )


# def remove_node(sim):
#     """
#     removes a node taking part in the consensus process
#     This is not a realistic implementation as it assumes a fully centralised
#     approach where a single entity can control all the nodes

#     PROBLEM:
#         Removing a node will not update its peers.
#         TEMP WORKAROUND:
#             reassign the peers of nodes that had the removed node in their neighbour list
# TODO: ideally, they would do that once they realised that the node is
# not there any more

#     TODO: implement logic to allow removing a node by index
#     """

#     print(
#         f"WARNING: 'remove_node' has some shortcomings in its current \
#            implementation! ensure these do not affect your results!"
#     )

#     # update fault tolerance and remove node
#     Parameters.application["Nn"] -= 1
#     Parameters.calculate_fault_tolerance()

#     rem_node = sim.nodes.pop()

#     for node in sim.nodes:
#         if rem_node in node.neighbours:
#             Network.assign_neighbours(node)
