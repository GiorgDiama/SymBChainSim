from Parameters import Parameters

from Chain.Reconfiguration.ConfigurationBlock import ConfigurationBlock

import random

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Manager.Manager import Manager


def create_random_configuration_block(time) -> ConfigurationBlock:
    """
    Generates a configuration block containing a random configuration
    based on the options defined in Parameters.reconfiguration["random_configuration"]
    """
    CPS = Parameters.reconfiguration["random_configuration"]["protocols"]
    BLOCK_SIZES = Parameters.reconfiguration["random_configuration"]["block_sizes"]
    BLOCK_TIMES = Parameters.reconfiguration["random_configuration"]["block_times"]

    configuration = {
        "CP": random.choice(CPS),
        "block_size": random.choice(BLOCK_SIZES),
        "block_time": random.choice(BLOCK_TIMES),
    }

    latest_configuration_block: ConfigurationBlock = Parameters.global_configuration_chain[-1]

    configuration_block = ConfigurationBlock(
        depth=latest_configuration_block.depth + 1,
        id=random.randint(0, 1_000_000),
        previous=latest_configuration_block.id,
        proposer="manager",
        size=Parameters.reconfiguration["conf_block_size"],
        consensus="centralised",
    )
    configuration_block.time_created = time
    configuration_block.extra_data = {}
    configuration_block.configuration = configuration

    Parameters.global_configuration_chain.append(configuration_block)

    return configuration_block


def propagate_configuration_block(manager: "Manager", configuration_block: ConfigurationBlock, time: float) -> None:
    """
    Models the propagation of the given configuration block based on the propagation
    model specific in Parameters.reconfiguration['propagation']

    Options:
        - Model==True: picks a percentage of the nodes to receive the block after a small delay; these gossip the block
        - Model==False: append the block to the configuration chains of all nodes directly and immediately
    """
    if Parameters.reconfiguration["print_updates"]:
        print("RECONFIGURATION:", configuration_block.configuration)

    if Parameters.reconfiguration["propagation"]["model"]:
        percent_receivers = Parameters.reconfiguration["propagation"]["per_cent_nodes"]
        num_initial_receivers = int(len(manager.sim.nodes) * percent_receivers)
        receivers = random.sample(manager.sim.nodes, k=num_initial_receivers)

        delay_range = Parameters.reconfiguration["propagation"]["delay"]

        for node in receivers:
            receive_at = time + random.uniform(*delay_range)

            if Parameters.reconfiguration["print_updates"]:
                print(f"node {node} will receive configuration block at {receive_at}")

            node.reconfiguration_state.schedule_future_receive_configuration(block=configuration_block.copy(), time=receive_at)
    else:
        for node in manager.sim.nodes:
            node.reconfiguration_state.confchain.append(configuration_block)
