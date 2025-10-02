from Parameters import Parameters

from Chain.TransactionFactory import TransactionFactory

from Utils.Metrics import Metrics
from Utils import Serialise

from copy import copy
import json

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Engine.Simulation import Simulation


SNAPSHOT_PATH = "../Outputs/Snapshots/"


def take_snapshot(sim: "Simulation", start_from: float = 0) -> None:
    """Takes a snapshot of the current simulation state and metrics.

    Args:
        sim (Simulation): The simulation instance to snapshot.
        start_from (float): Only considers blocks added after this timestamp.
    """
    # start_from functions the same in measure_all so no need to include conditionals
    Metrics.measure_all(sim, start_from=start_from)

    snapshot = {
        "time": sim.clock,
        "time_last": start_from,
        "metrics": {
            "latency": copy(Metrics.latency),
            "throughput": copy(Metrics.throughput),
            "block_time": copy(Metrics.blocktime),
            "decentralisation": copy(Metrics.decentralisation),
        },
        "nodes": {},
    }

    for node in sim.nodes:
        state = Serialise.serialisable_node(node)

        if Parameters.application["transaction_model"] == "global":
            current_transactions = [tx.size for tx in TransactionFactory.global_mempool if tx.timestamp <= sim.clock]
            state["tx_pool_len"] = len(current_transactions)
            state["tx_pool_size"] = sum(current_transactions)
        elif Parameters.application["transaction_model"] == "local":
            current_transactions = [tx.size for tx in node.pool if tx.timestamp <= sim.clock]
            state["tx_pool_len"] = len(current_transactions)
            state["tx_pool_size"] = sum(current_transactions)
        else:
            raise ValueError(f"transaction model '{Parameters.application['transaction_model']}' is not valid")

        state["new_blocks"] = []
        for b in node.blockchain[1:]:
            block = Serialise.serialisable_block(b, transactions=False)

            if block["time_added"] >= start_from:
                state["new_blocks"].append(block)

        snapshot["nodes"][node.id] = state

    Metrics.snapshots[Metrics.snapshot_count] = snapshot
    Metrics.snapshot_count += 1


def calculate_snapshot_metrics(final_sim: "Simulation") -> None:
    """Calculates metrics for stored snapshots.

    Args:
        final_sim (Simulation): The final simulation state.
    """
    for snapshot in Metrics.snapshots:
        start, end = snapshot["time_last"], snapshot["time"]

        for node in final_sim.nodes:
            blocks = []

            for b in node.blockchain:
                if b.time_added >= end:
                    break
                if b.time_added >= start:
                    blocks.append(b)


def save_snapshots(name: str = "snapshot") -> None:
    """Saves snapshots to a JSON file.

    Args:
        name (str): Name of the output file.
    """
    with open(SNAPSHOT_PATH + f"{name}.json", "w") as f:
        json.dump(Metrics.snapshots, f, indent=2)
