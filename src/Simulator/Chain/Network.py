from Parameters import Parameters

from Engine.Event import MessageEvent, Event
from Utils import Tools

from sys import getsizeof
import random
import json

from typing import List, Dict, Set, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .Node import Node


class Network:
    """Models the blockchain p2p network.

    This class handles network-related operations including message propagation,
    latency calculations, and node connectivity.

    Attributes:
        nodes (List['Node']): List of blockchain nodes.
        locations (List[str]): List of possible node locations.
        latency_map (Dict[str, Dict[str, tuple]]): Map of propagation latencies between locations.
        distance_map (Dict[str, Dict[str, float]]): Map of distances between locations.
        received (Dict['Node', Set[int]]): Tracks received message IDs for gossip protocol.
    """

    nodes: List["Node"]
    locations: List[str]
    latency_map: Dict[str, Dict[str, tuple]]
    distance_map: Dict[str, Dict[str, float]]
    received: Dict["Node", Set[int]]

    track_messages: Dict[int, list]

    @staticmethod
    def size(msg: Event) -> float:
        """Calculates the size of a message in megabytes.

        Args:
            msg (MessageEvent): The message to calculate size for.

        Returns:
            float: Size of the message in megabytes.
        """
        if "net_msg_size" in msg.payload:
            return msg.payload["net_msg_size"]

        size = Parameters.network["base_msg_size"]

        for key in msg.payload:
            if key == "block":
                size += msg.payload[key].size + Parameters.data["base_block_size"]
            else:
                size += float(getsizeof(msg.payload[key]) / 1_000_000)
        return size

    @staticmethod
    def send_message(creator: "Node", event: Event) -> None:
        """Schedules a broadcast message to the network.

        Args:
            creator (Node): The node creating the message.
            event (MessageEvent): The message event to send.
        """
        if Parameters.network["gossip"]:
            Network.multicast(creator, event)
        else:
            Network.broadcast(creator, event)

    @staticmethod
    def multicast(node: "Node", event: Event) -> None:
        """Sends a message to a subset of nodes using gossip protocol.

        Args:
            node (Node): The sending node.
            event (MessageEvent): The message to send.
        """
        Network.received[node].add(event.id)

        for n in node.neighbours:
            msg = MessageEvent.from_Event(event, n)
            msg.forwarded_by = str(node.id) + " (creator)"
            Network._message(node, n, msg)

    @staticmethod
    def broadcast(node: "Node", event: Event) -> None:
        """Sends a message to all nodes in the network.

        Args:
            node (Node): The sending node.
            event (MessageEvent): The message to send.
        """
        for n in Network.nodes:
            if n != node:
                msg = MessageEvent.from_Event(event, n)
                Network._message(node, n, msg)

    @staticmethod
    def _message(
        sender: "Node", receiver: "Node", msg: MessageEvent, delay: bool = True
    ) -> None:
        """Internal method to send a message with propagation delay.

        Args:
            sender (Node): The sending node.
            receiver (Node): The receiving node.
            msg (MessageEvent): The message to send.
            delay (bool): Whether to apply propagation delay.
        """

        delay = Network.calculate_message_propagation_delay(
            sender, receiver, Network.size(msg)
        )

        # message_info = [receiver.id, msg.time, msg.time+delay, Network.size(msg)]
        # Network.track_messages[sender.id] = Network.track_messages.get(sender.id, []) + [message_info]

        msg.time += delay
        receiver.add_event(msg)

    @staticmethod
    def on_receive(node: "Node", msg: MessageEvent) -> str:
        """Handles logic for receiving a network message.

        Args:
            node (Node): The receiving node.
            msg (MessageEvent): The received message.

        Returns:
            str: 'process' if message should be processed, otherwise reason for not processing.
        """
        if not Parameters.network["gossip"]:
            return "process"
        if msg.id in Network.received[node]:
            return "previously_gossiped"
        Network.received[node].add(msg.id)  # mark this message as received

        # only forward the message to peers that have not received the messages
        # yet to save on useless events
        for n in node.neighbours:
            if msg.id in Network.received[n]:
                continue

            new_msg = MessageEvent(
                handler=msg.handler,
                creator=msg.creator,
                time=msg.time,
                payload=msg.payload,
                id=msg.id,
                receiver=n,
            )
            new_msg.forwarded_by = str(node.id) + " (gossip)"
            Network._message(node, n, new_msg)
        return "process"

    @staticmethod
    def calculate_message_propagation_delay(sender, receiver, message_size):
        """
            Calculates the message propagation delay as:
                transmission delay + propagation delay + queueing delay + processing_delay
            supports 4 latency models:
                'measured': based collected latency data
                'distance': formula based on distance
                'local'   : based on set value in config
                'off'     : latency = 0

            y = 0.022x + 4.862 is fitted to match the round trip latency given a distance
            source:
                Goonatilake, Rohitha, and Rafic A. Bachnak. "Modeling latency in a network distribution."
            Magic Numbers:
            / 2: get the single trip latency
            / 1000: convert to seconds (regression fitted on data in ms)


        Args:
            sender (Node): The sending node.
            receiver (Node): The receiving node.
            message_size (float): Size of the message in megabytes.

        Returns:
            float: Total propagation delay in seconds.
        """
        # transmission delay
        delay = message_size / Network.get_bandwidth(sender, receiver)
        match Parameters.network["use_latency"]:
            case "measured":
                delay += (
                    Network.latency_map[sender.location][receiver.location][0] / 1000
                )
            case "distance":
                dist = Network.distance_map[sender.location][receiver.location]
                # conversion to miles (regression fitted on miles)
                dist = dist * 0.621371
                delay += ((0.022 * dist + 4.862) / 2) / 1000
            case "local":
                delay += Parameters.network["same_city_latency_ms"] / 1000
            case "off":
                delay += 0
            case _:
                raise ValueError(
                    f"no such latency type '{Parameters.network['use_latency']}'"
                )

        delay += (
            Parameters.network["queueing_delay"]
            + Parameters.network["processing_delay"]
        )

        return delay

    @staticmethod
    def get_bandwidth(
        sender: "Node",
        receiver: "Node",
    ) -> float:
        """Calculates the effective bandwidth between two nodes.

        Args:
            sender (Node): The sending node.
            receiver (Node): The receiving node.

        Returns:
            float: Effective bandwidth in Mbps.
        """
        if isinstance(sender.bandwidth, tuple):
            sender_bw = random.normalvariate(*sender.bandwidth)
            sender_bw = max(sender_bw, Parameters.network["bandwidth"]["min"])
        else:
            sender_bw = sender.bandwidth

        if isinstance(receiver.bandwidth, tuple):
            receiver_bw = random.normalvariate(*receiver.bandwidth)
            receiver_bw = max(receiver_bw, Parameters.network["bandwidth"]["min"])
        else:
            receiver_bw = receiver.bandwidth

        if sender_bw is None or receiver_bw is None:
            raise ValueError("Bandwidth not set for one of the nodes")

        return min(sender_bw, receiver_bw)

    ########################## SET UP ############################

    @staticmethod
    def init_network(nodes: List["Node"]) -> None:
        """Initializes the Network module.

        Args:
            nodes (List[Node]): List of nodes to initialize the network with.
        """
        Network.nodes = nodes

        if Parameters.network["gossip"]:
            Network.received = {node: set() for node in nodes}

        # Network.track_messages = {node.id:[] for node in Network.nodes}

        Network.parse_latencies()
        Network.parse_distances()
        Network.assign_location_to_nodes()
        Network.set_bandwidths()
        Network.assign_neighbours()

    @staticmethod
    def set_bandwidths(node: Optional["Node"] = None) -> None:
        """Sets bandwidth for nodes based on configuration.

        Args:
            node (Optional[Node]): Specific node to set bandwidth for, or None for all nodes.
        """
        # scenarios have separate logic to set up the bandwidths 
        if Parameters.network['bandwidth'].get("sample", "always") == "scenario":
            return

        if node is None:
            for n in Network.nodes:
                Network.set_bandwidths(n)
        else:
            if Parameters.network["bandwidth"].get("sample", "always") == "always":
                node.bandwidth = (
                    Parameters.network["bandwidth"]["mean"],
                    Parameters.network["bandwidth"]["dev"],
                )
            elif Parameters.network["bandwidth"].get("sample", "always") == "once" :
                node.bandwidth = random.normalvariate(
                    mu=Parameters.network["bandwidth"]["mean"],
                    sigma=Parameters.network["bandwidth"]["dev"],
                )
                node.bandwidth = max(
                    node.bandwidth, Parameters.network["bandwidth"]["min"]
                )
            else:
                raise ValueError(f"Bandwidth sample strategy: '{Parameters.network['bandwidth']['sample']}' is not valid.")

    @staticmethod
    def assign_neighbours(node: Optional["Node"] = None) -> None:
        """Assigns random neighbors to nodes for gossip protocol.

        Args:
            node (Optional[Node]): Specific node to assign neighbors to, or None for all nodes.
        """
        if node is None:
            for n in Network.nodes:
                Network.assign_neighbours(n)
        else:
            num_neighbours = min(
                Parameters.network["num_neighbours"], Parameters.application["Nn"] - 1
            )
            node.neighbours = random.sample(
                [x for x in Network.nodes if x != node], num_neighbours
            )

    @staticmethod
    def assign_location_to_nodes(
        node: Optional["Node"] = None, location: Optional[str] = None
    ) -> None:
        """Assigns locations to nodes.

        Args:
            node (Optional[Node]): Specific node to assign location to, or None for all nodes.
            location (Optional[str]): Specific location to assign, or None for random assignment.
        """
        if node is None:
            for n in Network.nodes:
                Network.assign_location_to_nodes(n)
                Tools.debug_logs(msg=f"Node {n.id}: {n.location}")
        else:
            if location is None:
                node.location = random.choice(Network.locations)
            else:
                node.location = location

    @staticmethod
    def parse_latencies() -> None:
        """Initializes network locations and latency map from JSON dataset."""
        Network.locations = []
        Network.latency_map = {}

        with open("../Resources/NetworkLatencies/latency_map.json", "rb") as f:
            Network.latency_map = json.load(f)

        Network.locations = list(Network.latency_map.keys())

        for loc in Network.locations:
            Network.latency_map[loc][loc] = (
                Parameters.network["same_city_latency_ms"],
                Parameters.network["same_city_dev_ms"],
            )

    @staticmethod
    def parse_distances() -> None:
        """Initializes network locations and distance map from JSON dataset."""
        Network.locations = []
        Network.distance_map = {}

        with open("../Resources/NetworkLatencies/distance_map.json", "rb") as f:
            Network.distance_map = json.load(f)

        Network.locations = list(Network.distance_map.keys())
