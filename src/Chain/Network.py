from Chain.Event import MessageEvent
from Chain.Parameters import Parameters

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

    @staticmethod
    def size(msg):
        size = Parameters.network["base_msg_size"]

        for key in msg.payload:
            if key == "block":
                size += msg.payload[key].size
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
        for n in node.neighbours:
            msg = MessageEvent.from_Event(event, n)
            Network.gossip_message(node, n, msg)

    @staticmethod
    def gossip_message(sender, receiver, msg):
        # if the receiver has received this event (ignore) or the receiver created the message
        if receiver.queue.contains_event_message(msg) or msg.creator == receiver:
            return 0

        Network.message(sender, receiver, msg)

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
    def init_network(nodes, speeds=None):
        ''' 
            Initialises the Netowrk modules
                - Gets a refenrence to the node list
                - Calculates latency_map and locations
                - Assigns locations and bandwidth to nodes
                - Assigns neibhours to nodes (Gossip, Sync etc...)
        '''
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
            if Parameters.network["bandwidth"]["debug"]:
                node.bandwidth = 1
            else:
                node.bandwidth = random.normalvariate(
                    Parameters.network["bandwidth"]["mean"], Parameters.network["bandwidth"]["dev"])

            tools.debug_logs(msg=f"Node {node.id}: {node.bandwidth}MB/s")

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
            node.neighbours = random.sample(
                [x for x in Network.nodes if x != node],
                Parameters.network["num_neighbours"])

    @staticmethod
    def calculate_message_propagation_delay(sender, receiver, message_size):
        '''
            Calculates the message propagation delay as
            transmission delay + propagation delay + queueing delay + processing_delay
        '''
        # transmission delay
        delay = message_size / Network.get_bandwidth(sender, receiver)

        if Parameters.network["use_latency"] == "measured":
            delay += Network.latency_map[sender.location][receiver.location][0] / 1000
        elif Parameters.network["use_latency"] == "distance":
            dist = Network.distance_map[sender.location][receiver.location]
            dist = dist * 0.621371  # conversion to miles since formula is based on miles
            '''
                y = 0.022x + 4.862 is fitted to match the round trip latency between 2
                locations based on distance source: 
                Goonatilake, Rohitha, and Rafic A. Bachnak. "Modeling latency in a network distribution." Network and Communication Technologies 1.2 (2012): 1
                
                / 2 to get the single trip latency
                / 1000 to get seconds (formula fitted on ms)
            '''
            delay += ((0.022 * dist + 4.862) / 2) / 1000

        delay += Parameters.network["queueing_delay"] + \
            Parameters.network["processing_delay"]

        return delay

    @staticmethod
    def assign_location_to_nodes(node=None, location=None):
        '''
            node->Node (default)
            Assings random locations to nodes by default
            if node is provided assing a random location to just this node
        '''
        if node is None:
            for n in Network.nodes:
                n.location = random.choice(Network.locations)
                tools.debug_logs(msg=f"Node {n.id}: {n.location}")
        else:
            if location is None:
                node.location = random.choice(Network.locations)
            else:
                node.location = location

    @staticmethod
    def get_bandwidth(sender, receiver):
        return min(sender.bandwidth, receiver.bandwidth)

    @staticmethod
    def parse_latencies():
        '''
            Initialised the Network.locations list the Network.latency map from the JSON dataset
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
        Network.locations = []
        Network.distance_map = {}

        with open("NetworkLatencies/distance_map.json", "rb") as f:
            Network.distance_map = json.load(f)

        # overwritting the locations is fine to gurantee that they exists
        # (this is the case if we laoded latencied before and prevents an error if we dont want to use latencies)
        Network.locations = list(Network.distance_map.keys())
