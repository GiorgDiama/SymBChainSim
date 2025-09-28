from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from Engine.Simulation import Simulation
    from Chain.Block import Block
    from Chain.Reconfiguration.ConfigurationBlock import ConfigurationBlock
    from Chain.Node import Node


def serialisable_node(node: "Node") -> Dict[str, Any]:
    """Creates a serializable representation of a node's state.

    Args:
        node (Node): The node to serialize.

    Returns:
        Dict[str, Any]: Serializable node state.
    """
    state = {}

    state["bandwidth"] = node.bandwidth
    state["location"] = node.location
    state["neighbours"] = [n.id for n in node.neighbours]
    state["current_cp"] = node.cp.NAME
    state["latest_blockchain_block"] = serialisable_block(node.last_block)
    state["latest_blockchain_block"].pop("transactions")
    state["state"] = {
        "online": node.state.alive,
        "synced_data": node.state.synced,
        "synced_config": node.configuration_synced,
    }
    state["latest_configuration_block"] = serialisable_configuration_block(
        node.confchain[-1]
    )

    return state


def serialisable_block(block: "Block", transactions: bool = True) -> Dict[str, Any]:
    """Creates a serializable representation of a block.

    Args:
        block (Block): The block to serialize.
        transactions (bool): Whether to include all transaction information.

    Returns:
        Dict[str, Any]: Serializable block information.
    """
    block_info = {}
    block_info["id"] = block.id
    block_info["previous"] = block.previous
    block_info["time_created"] = block.time_created
    block_info["time_added"] = block.time_added
    block_info["miner"] = block.miner
    
    if transactions:
        block_info["transactions"] = [
            str((t.id, t.timestamp, t.size)) for t in block.transactions
        ]
    else:
        block_info["transactions"] = {
            'total_transactions': len(block.transactions),
            'total_size': sum([t.size for t in block.transactions])
        }

    block_info["depth"] = block.depth
    block_info["size"] = block.size
    block_info["extra_data"] = block.extra_data

    return block_info


def serialisable_configuration_block(block: "ConfigurationBlock") -> Dict[str, Any]:
    """Creates a serializable representation of a configuration block.

    Args:
        block (ConfigurationBlock): The configuration block to serialize.

    Returns:
        Dict[str, Any]: Serializable configuration block information.
    """
    block_info = {}
    block_info["id"] = block.id
    block_info["previous"] = block.previous
    block_info["time_created"] = block.time_created
    block_info["time_added"] = block.time_added
    block_info["proposer"] = block.proposer
    block_info["configuration"] = block.configuration
    block_info["depth"] = block.depth
    block_info["size"] = block.size
    block_info["extra_data"] = block.extra_data
    return block_info


def serialise_sim_state(sim: "Simulation") -> Dict[int, Dict[str, Any]]:
    """Creates a serializable representation of the simulation state.

    Args:
        sim (Simulation): The simulation instance to serialize.

    Returns:
        Dict[int, Dict[str, Any]]: Serializable simulation state.
    """
    ser_state = {}
    for node in sim.nodes:
        ser_state[node.id] = serialisable_node(node)
    return ser_state
