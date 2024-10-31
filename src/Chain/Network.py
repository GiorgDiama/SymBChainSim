from Chain.Event import MessageEvent
from Chain.Parameters import Parameters
import Chain.tools as tools

from sys import getsizeof
import numpy as np
import random
import json


class Network:
    '''
        Models the blockchain p2p network
            nodes: list of BP's
            locations: list of various locations node can be in
            latency_map: map of propagation latencies between locations
            distance_map: map of distance between locations
    '''
    nodes = None
    locations = None
    latency_map = None
    distance_map = None

    received = None

    avg_transmission_delay = None

    @staticmethod
    def size(msg):
        '''
            Calculates the size of a message. When the payload contains the key 'block' uses the block.size otherwise uses getsizeof.
            Event payloads can define net_msg_size to bypass this check using that value instead
        '''
        # if message defines its own size - simply use that
        if 'net_msg_size' in msg.payload:
            return msg.payload['net_msg_size']
        
        # starting size == base_msg_size
        size = Parameters.network["base_msg_size"]

        for key in msg.payload:
            if key == "block":
                size += msg.payload[key].size + Parameters.data["base_block_size"]
            else:
                size += float(getsizeof(msg.payload[key])/1000000)

        return size

    @staticmethod
    def send_message(creator, event):
        '''
            Schedule a broadcast message to the network - abstract broadcasting approach from the rest of the system
        '''
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
            Network._message(node, n, msg)

    @staticmethod
    def broadcast(node, event):
        for n in Network.nodes:
            if n != node:
                msg = MessageEvent.from_Event(event, n)
                Network._message(node, n, msg)

    @staticmethod
    def _message(sender, receiver, msg, delay=True):
        delay = Network.calculate_message_propagation_delay(
            sender, receiver, Network.size(msg))
        
        msg.time += delay

        receiver.add_event(msg)
        
    @staticmethod
    def on_receive(node, msg):
        '''
            Handles logic of receiving a network message on a node. Returns 'process' if message should be  processed
            otherwise returns the reason the message should not be processed e.g., 'gossiped'
        '''
        if not Parameters.network['gossip']:
            return 'process' 
                
        if msg.id in Network.received[node]:
            return 'gossiped'
        
        Network.received[node].add(msg.id) # mark this message as received

        # only forward the message to peers that have not received the messages yet (saves loads of useless events!)
        # this is fast due to hash_maps 
        # short resembles a mechanism where nodes ask nodes if they have some data before bother sending it over although we dont model the delay of that
        # If measuring the network traffic is important you can remove this
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

            Network._message(node, n, new_msg)

        return 'process'
            
    @staticmethod
    def calculate_message_propagation_delay(sender, receiver, message_size):
        '''
            Calculates the message propagation delay as:
                transmission delay + propagation delay + queueing delay + processing_delay
            supports 4 latency models: 
                'measured': based collected latency data
                'distance': formula based on distance
                'local': based on set value in config
                'off': latency = 0                
        '''

        # transmission delay
        delay = message_size / Network.get_bandwidth(sender, receiver)
        match Parameters.network["use_latency"]:
            case "measured":
                delay += Network.latency_map[sender.location][receiver.location][0] / 1000
            case "distance":
                dist = Network.distance_map[sender.location][receiver.location]
                # conversion to miles (regression fitted on miles)
                dist = dist * 0.621371
                '''
                    y = 0.022x + 4.862 is fitted to match the round trip latency given a distance
                    source: Goonatilake, Rohitha, and Rafic A. Bachnak. "Modeling latency in a network distribution." Network and Communication Technologies 1.2 (2012): 1

                    / 2: get the single trip latency
                    / 1000: convert to seconds (regression fitted on data in ms)
                '''
                delay += ((0.022 * dist + 4.862) / 2) / 1000
            case "local":
                delay += Parameters.network["same_city_latency_ms"] / 1000
            case "off":
                delay += 0
            case _:
                raise ValueError(
                    f"no such latency type '{Parameters.network['use_latency']}'")

        delay += Parameters.network["queueing_delay"] + Parameters.network["processing_delay"]

        if Parameters.network['measure_avg_transmission_delay']:
            Network.avg_transmission_delay[sender.id, receiver.id] += delay
            Network.no_messages[sender.id, receiver.id] += 1

        return delay

    @staticmethod
    def get_bandwidth(sender, receiver):
        '''
            Calculates the bandwidth between the nodes
        '''
        return min(sender.bandwidth, receiver.bandwidth)

    ########################## SET UP ############################

    @staticmethod
    def init_network(nodes, speeds=None):
        ''' 
            Initialise the Network modules
                - Gets a reference to the node list
                - parses latency_map and distance_map and extracts locations
                - Assigns locations and bandwidth to nodes
                - Assigns neighbour peers to nodes (used for Gossip, Sync etc...)
        '''
        Network.avg_transmission_delay = np.zeros((len(nodes), len(nodes)))
        Network.no_messages = np.zeros((len(nodes), len(nodes)))

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
        '''
            Set the bandwidth for a node (if node is given) otherwise set the bandwidth for all nodes
            Bandwidth is set  based on the values specified in config
        '''
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
            Randomly assign neighbours to all nodes (based on the config)
            if node is provided assign to just that node
        '''
        if node is None:
            for n in Network.nodes:
                Network.assign_neighbours(n)
        else:
            num_neighbours = min(Parameters.network["num_neighbours"], Parameters.application['Nn']-1)
            node.neighbours = random.sample(
                [x for x in Network.nodes if x != node], num_neighbours)

    @staticmethod
    def assign_location_to_nodes(node=None, location=None):
        '''
            node->None (default)
            Assigns random locations to nodes by default
            if node is provided assign a random location to just this node
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
            Initialise the Network.locations list and the Network.latency_map from the JSON dataset
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
            Initialise the Network.locations list and the Network.distance_map from the JSON dataset
        '''
        Network.locations = []
        Network.distance_map = {}

        with open("NetworkLatencies/distance_map.json", "rb") as f:
            Network.distance_map = json.load(f)

        Network.locations = list(Network.distance_map.keys())
