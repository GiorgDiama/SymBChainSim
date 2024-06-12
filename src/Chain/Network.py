from Chain.Event import MessageEvent
from Chain.Parameters import Parameters
import numpy as np

import Chain.tools as tools

from sys import getsizeof

import random
import json


class Network:
    '''
        Models the blockchain p2p network
            nodes: list of BP's
            locations: list of various locations node can be in
            latency_map: map of propgation latencies between locations
    '''
    nodes = None
    locations = None
    latency_map = None
    distance_map = None

    received = None

    @staticmethod
    def size(msg):
        size = Parameters.network["base_msg_size"]

        for key in msg.payload:
            if key == "block":
                size += msg.payload[key].size + \
                    Parameters.data["base_block_size"]
            else:
                size += float(getsizeof(msg.payload[key])/1000000)

        return size

    @staticmethod
    def send_message(creator, event):
        if Parameters.network["gossip"]:
            Network.multicast(creator, event)
        else:
            Network.broadcast(creator, event)

    @staticmethod
    def multicast(node, event):
        Network.received[node].add(event.id)

        for n in node.neighbours:
            msg = MessageEvent.from_Event(event, n)
            msg.forwarded_by = str(node.id) + ' (creator)'
            Network.message(node, n, msg)

    @staticmethod
    def broadcast(node, event):
        for n in Network.nodes:
            if n != node:
                msg = MessageEvent.from_Event(event, n)
                Network.message(node, n, msg)

    @staticmethod
    def message(sender, receiver, msg, delay=True):
        delay = Network.calculate_message_propagation_delay(
            sender, receiver, Network.size(msg))

        msg.time += delay

        receiver.add_event(msg)

    @staticmethod
    def receive(node, msg):
        if Parameters.network['gossip']:
            if msg.id in Network.received[node]:
                return False
            
            Network.received[node].add(msg.id) # mark this message as received

            # only forward the message to peers that have not received the messages yet (saves loads of useless events!)
            neighbours = [n for n in node.neighbours if msg.id not in Network.received[n]]

            for n in neighbours:
                new_msg = MessageEvent(
                    handler=msg.handler,
                    creator=msg.creator,
                    time=msg.time,
                    payload=msg.payload, 
                    id=msg.id,
                    receiver=n)

                new_msg.forwarded_by = str(node.id) + ' (gossip)'

                Network.message(node, n, new_msg)

        return True

    @staticmethod
    def calculate_message_propagation_delay(sender, receiver, message_size):
        '''
            Calculates the message propagation delay as
            transmission delay + propagation delay + queueing delay + processing_delay
        '''

        # transmission delay
        delay = message_size / Network.get_bandwidth(sender, receiver)
        match Parameters.network["use_latency"]:
            case "measured":
                delay += Network.latency_map[sender.location][receiver.location][0] / 1000
            case "distance":
                dist = Network.distance_map[sender.location][receiver.location]
                # conversion to miles (formula fitted on miles)
                dist = dist * 0.621371
                '''
                    y = 0.022x + 4.862 is fitted to match the round trip latency given a distance
                    source:
                    Goonatilake, Rohitha, and Rafic A. Bachnak. "Modeling latency in a network distribution." Network and Communication Technologies 1.2 (2012): 1

                    / 2 to get the single trip latency
                    / 1000 to get seconds (regression fitted on data in ms)
                '''
                delay += ((0.022 * dist + 4.862) / 2) / 1000
            case "local":
                delay += Parameters.network["same_city_latency_ms"] / 1000
            case "off":
                delay += 0
            case _:
                raise ValueError(
                    f"no such latency type '{Parameters.network['use_latency']}'")

        delay += Parameters.network["queueing_delay"] + \
            Parameters.network["processing_delay"]

        return delay

    @staticmethod
    def get_bandwidth(sender, receiver):
        return min(sender.bandwidth, receiver.bandwidth)

    ########################## SET UP NETWORK ############################
    @staticmethod
    def init_network(nodes, speeds=None):
        ''' 
            Initialises the Netowrk modules
                - Gets a refenrence to the node list
                - Calculates latency_map and locations
                - Assigns locations and bandwidth to nodes
                - Assigns neibhours to nodes (Gossip, Sync etc...)
        '''
        if Parameters.network["gossip"]:
            Network.received = {node: set() for node in nodes}

        Network.nodes = nodes

        Network.parse_latencies()
        Network.parse_distances()

        Network.assign_location_to_nodes()

        Network.set_bandwidths()

        Network.assign_neighbours()

    @staticmethod
    def set_bandwidths(node=None):
        if node is None:
            for n in Network.nodes:
                Network.set_bandwidths(n)
        else:
            node.bandwidth = random.normalvariate(
                Parameters.network["bandwidth"]["mean"], Parameters.network["bandwidth"]["dev"])

            node.bandwidth = max(
                node.bandwidth, Parameters.network["bandwidth"]["min"])

    @staticmethod
    def assign_neighbours(node=None):
        '''
            (default) node -> None
            Randomly assing neibhours to all nodes (based on the config)
            if node is provided assign to just that node
        '''
        if node is None:
            for n in Network.nodes:
                Network.assign_neighbours(n)
        else:
            num_neigh = Parameters.network["num_neighbours"]

            # get other nodes in network in a random order
            other_nodes = [x for x in Network.nodes if x != node]
            random.shuffle(other_nodes)

            # assign neighbours
            for other_node in other_nodes:
                if len(other_node.neighbours) < num_neigh and node not in other_node.neighbours:
                    node.neighbours.append(other_node)
                    other_node.neighbours.append(node)

                if len(node.neighbours) == num_neigh:
                    break

            # if all other nodes have num_neigh neighbours and we could not assing num_neigh neighbours to current node
            # randomly pick some nodes that will have extra neighbours to ensure node has num_neigh neighbours
            if len(node.neighbours) < num_neigh:
                for other_node in other_nodes:
                    if node not in other_node.neighbours:
                        node.neighbours.append(other_node)
                        other_node.neighbours.append(node)

                    if len(node.neighbours) == num_neigh:
                        break

    @staticmethod
    def assign_location_to_nodes(node=None, location=None):
        '''
            node->Node (default)
            Assings random locations to nodes by default
            if node is provided assing a random location to just this node
        '''
        if node is None:
            for n in Network.nodes:
                Network.assign_location_to_nodes(n)
                tools.debug_logs(msg=f"Node {n.id}: {n.location}")
        else:
            if location is None:
                node.location = random.choice(Network.locations)
            else:
                node.location = location

    @staticmethod
    def parse_latencies():
        '''
            Initialised the Network.locations list and the Network.latency_map from the JSON dataset
        '''
        Network.locations = []
        Network.latency_map = {}

        with open("NetworkLatencies/latency_map.json", "rb") as f:
            Network.latency_map = json.load(f)

        Network.locations = list(Network.latency_map.keys())

        for loc in Network.locations:
            Network.latency_map[loc][loc] = (
                Parameters.network["same_city_latency_ms"],
                Parameters.network["same_city_dev_ms"]
            )

    def parse_distances():
        '''
            Initialised the Network.locations list and the Network.distance_map from the JSON dataset
        '''
        Network.locations = []
        Network.distance_map = {}

        with open("NetworkLatencies/distance_map.json", "rb") as f:
            Network.distance_map = json.load(f)

        # overwritting the locations is fine to gurantee that they exist (this is the case if we laoded latencied before)
        # prevents an error if we dont want to use latencies
        Network.locations = list(Network.distance_map.keys())
