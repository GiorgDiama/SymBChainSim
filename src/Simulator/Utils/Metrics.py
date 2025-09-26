from Parameters import Parameters

from Chain.TransactionFactory import TransactionFactory

from Utils import Tools

import statistics as st
import numpy as np

from typing import Dict, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from Engine.Simulation import Simulation
    from Chain.Node import Node
    from Chain.Block import Block


class Metrics:
    """Handles collection and calculation of various blockchain metrics.

    This class provides static methods for measuring different aspects of the blockchain
    including latency, throughput, block times, and decentralization.

    Class Attributes:
        latency (Dict[int, Dict[str, Any]]): Per-node latency measurements.
        throughput (Dict[int, float]): Per-node transaction throughput.
        blocktime (Dict[int, Dict[str, Any]]): Per-node block time measurements.
        decentralisation (Dict[int, float]): Per-node decentralization scores.
        transaction_info (Dict[int, Dict[str, int]]): Per-node transaction statistics.
        block_info (Dict[int, Dict[str, Any]]): Per-node block size statistics.
        blocks (Dict[int, Any]): Block-related metrics.
        nodes (Dict[int, Any]): Node-related metrics.
        snapshot_count (int): Counter for snapshots taken.
        snapshots (Dict): Stored snapshots of metrics.
    """

    latency: Dict[int, Dict[str, Any]] = {}
    throughput: Dict[int, float] = {}
    blocktime: Dict[int, Dict[str, Any]] = {}
    decentralisation: Dict[int, float] = {}
    transaction_info: Dict[int, Dict[str, int]] = {}
    block_info: Dict[int, Dict[str, Any]] = {}
    blocks: Dict[int, Any] = {}
    nodes: Dict[int, Any] = {}
    snapshot_count: int = 0
    snapshots: Dict = {}

    @staticmethod
    def confirmed_blocks(sim: "Simulation") -> int:
        """Returns the number of blocks common among ALL nodes.

        Note:
            When a node is offline this metric appears stuck, but this is expected
            as other nodes can still be producing blocks that the offline node doesn't receive.
            As this measures blocks in ALL nodes the offline node is the bottle neck.

            A fix is to change this to measure the largest blockchain in the first 2f+1 nodes
            when sorted by their blockchain lenght.

        Args:
            sim (Simulation): The simulation instance to measure.

        Returns:
            int: Minimum number of blocks across all nodes.
        """
        return min([n.blockchain_length() for n in sim.nodes])

    @staticmethod
    def measure_all(sim: "Simulation", start_from: float = 0) -> None:
        """Measures all implemented metrics for a given blockchain state.

        Args:
            sim (Simulation): The simulation instance to measure.
            start_from (float): Only considers blocks added after this timestamp.
        """
        for node in sim.nodes:
            # get all blocks added to the chain after the 'start_from'
            BC = [b for b in node.blockchain[1:] if b.time_added >= start_from]

            ###### CALCULATE METRICS ########
            values, avg = Metrics.measure_latency(BC)
            Metrics.latency[node.id] = {"values": values, "AVG": avg}

            TPS = Metrics.measure_throughput(BC)
            Metrics.throughput[node.id] = TPS

            values, avg = Metrics.measure_interblock_time(BC)
            Metrics.blocktime[node.id] = {"values": values, "AVG": avg}

            gini = Metrics.measure_decentralisation_nodes(sim, BC)
            Metrics.decentralisation[node.id] = gini
            
            tx_info = Metrics.measure_transactions(node)
            Metrics.transaction_info[node.id] = tx_info

            sizes = Metrics.measure_block_sizes(BC)
            Metrics.block_info[node.id] = {"values": sizes, "AVG": st.mean(sizes) if sizes else 0}

    @staticmethod
    def print_metrics() -> None:
        """Prints all collected metrics in a formatted table."""
        averages = {n: {} for n in Metrics.latency.keys()}
        val = "{v:.3f}"

        # latency
        for key, value in Metrics.latency.items():
            averages[key]["Latency"] = "%.3f" % value["AVG"]

        # throughput
        for key, value in Metrics.throughput.items():
            averages[key]["Throughput"] = "%.3f" % value

        # blockctime
        for key, value in Metrics.blocktime.items():
            averages[key]["BlockTime"] = "%.3f" % value["AVG"]

        # decentralisation
        for key, value in Metrics.decentralisation.items():
            averages[key]["Decent."] = "%.6f" % value

        for key, value in Metrics.transaction_info.items():
            averages[key]["Mempool"] = value["pool"]
            averages[key]["Confirmed"] = value["processed_tx"]

        for key, value in Metrics.block_info.items():
            averages[key]["AVG. BlockSize"] = round(value["AVG"], 3)

        print(Tools.color(f"{'-' * 30} METRICS {'-' * 30}", 46))

        for key, metrics in averages.items():
            print(f"{f'Node: {key}':10}", end="")
            for metric, value in metrics.items():
                print(f"{metric}:{value} ", end=" | ")
            print()

    @staticmethod
    def measure_latency(blocks: List["Block"]) -> tuple[List[float], float]:
        """Measures transaction latency for a sequence of blocks.

        Args:
            blocks (List[Block]): List of blocks to measure latency for.

        Returns:
            tuple: (List of per-block latencies, average latency)
        """
        if not blocks:
            return [], -1

        per_block = []

        for b in blocks:
            latencies = [b.time_added - t.timestamp for t in b.transactions]
            per_block.append(
                st.mean(latencies) if latencies else 0
            )
        return per_block, st.mean(per_block) if per_block else 0

    @staticmethod
    def measure_throughput(blocks: List["Block"]) -> float:
        """Calculates transactions per second for a sequence of blocks.

        Args:
            blocks (List[Block]): List of blocks to measure throughput for.

        Returns:
            float: Transactions per second.
        """
        if not blocks:
            return 0

        time = blocks[-1].time_added - blocks[0].time_created
        sum_tx = sum([len(b.transactions) for b in blocks])
        return sum_tx / time

    @staticmethod
    def measure_interblock_time(
        blocks: List["Block"],
    ) -> tuple[Dict[str, float], float]:
        """Measures time between consecutive blocks.

        Args:
            blocks (List[Block]): List of blocks to measure interblock times for.

        Returns:
            tuple: (Dictionary of block pair times, average interblock time)
        """
        if len(blocks) < 2:
            return [], 0

        # for each pair of blocks create the key value pair "curr -> next":
        # next.time_added - current.time_added
        diffs = {
            f"{curr.id} -> {next.id}": next.time_added - curr.time_added
            for curr, next in zip(blocks[:-1], blocks[1:])
        }

        return diffs, st.mean(diffs.values() if diffs.values() else 0)

    @staticmethod
    def gini_coeficient(lorenz_curve: List[float]) -> float:
        """Calculates the Gini coefficient from a Lorenz curve.

        Args:
            lorenz_curve (List[float]): The Lorenz curve values.

        Returns:
            float: The Gini coefficient.
        """
        # calculating the perfect equality for the given population
        perfect_equality = [
            (x + 1) / len(lorenz_curve) for x in range(len(lorenz_curve))
        ]

        x_axis = [x for x in range(len(perfect_equality))]

        # calculate the area of the perfect equality curve
        perfect_equality_area = np.trapezoid(perfect_equality, x_axis)

        # calculate the area of the lorenz curve
        lorenz_area = np.trapezoid(lorenz_curve, x_axis)

        # gini coefficient
        return 1 - lorenz_area / perfect_equality_area

    @staticmethod
    def measure_decentralisation_nodes(
        sim: "Simulation", blocks: List["Block"]
    ) -> float:
        """Measures decentralization using Gini coefficient of block production.

        Note:
            This method assumes all nodes are accounted for in the final system state.
            If nodes that have produced blocks are not in the given system state, this does not return correct results.

        Args:
            sim (Simulation): The simulation instance.
            blocks (List[Block]): List of blocks to measure decentralization for.

        Returns:
            float: Decentralization score (Gini coefficient).
        """

        if not blocks:
            return -1

        nodes = [node.id for node in sim.nodes]

        block_distribution = {x: 0 for x in nodes}

        total_blocks = len(blocks)

        for b in blocks:
            block_distribution[b.miner] += 1

        dist = sorted(
            [(key, value) for key, value in block_distribution.items()],
            key=lambda x: x[1],
        )

        dist = [(x[0], x[1] / total_blocks) for x in dist]

        cumulative_dist = [sum([x[1] for x in dist[: i + 1]]) for i in range(len(dist))]

        return Metrics.gini_coeficient(cumulative_dist)

    @staticmethod
    def measure_transactions(node: "Node") -> Dict[str, int]:
        """Measures transaction statistics for a node.

        Args:
            node (Node): The node to measure transactions for.

        Returns:
            Dict[str, int]: Transaction statistics including pool size and processed transactions.
        """
        node_info = {}
        if Parameters.application["transaction_model"] == "local":
            node_info["pool"] = len(node.pool)
        else:
            node_info["pool"] = len(TransactionFactory.global_mempool)

        node_info["processed_tx"] = sum(len(b.transactions) for b in node.blockchain)
        return node_info

    @staticmethod
    def processed_tx_system(sim: "Simulation") -> float:
        """Calculates average number of processed transactions across all nodes.

        Args:
            sim (Simulation): The simulation instance.

        Returns:
            float: Average number of processed transactions.
        """
        processed_tx_nodes = []
        for node in sim.nodes:
            tx = []
            for block in node.blockchain:
                tx.append(len(block.transactions))
            processed_tx_nodes.append(sum(tx))

        return st.mean(processed_tx_nodes) if processed_tx_nodes else 0

    @staticmethod
    def measure_block_sizes(blocks: List["Block"]) -> List[float]:
        """Measures sizes of blocks.

        Args:
            blocks (List[Block]): List of blocks to measure sizes for.

        Returns:
            List[float]: List of block sizes.
        """
        return [b.size for b in blocks]
