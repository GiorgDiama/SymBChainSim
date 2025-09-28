from Parameters import Parameters
from Engine.Event import SystemEvent

from Chain.Reconfiguration.ConfigurationBlock import ConfigurationBlock

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Manager.Manager import Manager

def schedule_reconfiguration_event(manager: "Manager", time:float) -> None:
    """ Schedules a reconfiguration event of Parameters.reconfiguration['reconfiguration_method'] type
    at time + reconfiguration_interval

    Args:
        manager (Manager): the simulation manager
        time (float): the current time
    """
    schedule_at = time + Parameters.reconfiguration['reconfiguration_interval']

    event = SystemEvent(
        time = schedule_at,
        payload= {
            "type": Parameters.reconfiguration['reconfiguration_method']
        }
    )
    manager.sim.q.add_event(event)

def handle_random_centralised_reconfiguration_event(manager: "Manager", event: SystemEvent) -> None:    
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
        size= Parameters.reconfiguration['conf_block_size'],
        consensus="PBFT",
    )
    configuration_block.time_created = event.time
    configuration_block.extra_data = {}
    configuration_block.configuration = configuration

    Parameters.global_configuration_chain.append(configuration_block)
    
    if Parameters.reconfiguration['print_updates']:
        print("RECONFIGURATION:", configuration)
    
    if Parameters.reconfiguration['propagation']['model']:
        percent_receivers = Parameters.reconfiguration['propagation']['per_cent_nodes']
        num_initial_receivers = int(len(manager.sim.nodes) * percent_receivers)
        receivers = random.sample(manager.sim.nodes, k=num_initial_receivers)

        delay_range = Parameters.reconfiguration['propagation']['delay']

        for node in receivers:
            receive_at = event.time + random.uniform(*delay_range)
            
            if Parameters.reconfiguration['print_updates']:
                print(f"node {node} will receive configuration block at {receive_at}")

            node.schedule_future_receive_configuration(
                block=configuration_block.copy(),
                time= receive_at
            )

    else:
        for node in manager.sim.nodes:
            node.confchain.append(configuration_block)

    schedule_reconfiguration_event(manager, manager.sim.clock)    
