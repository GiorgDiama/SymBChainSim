from Parameters import Parameters
from Engine.Event import SystemEvent

from Chain.Reconfiguration.ConfigurationBlock import ConfigurationBlock
import Chain.Reconfiguration.CentralisedReconfiguration  as CentralisedReconfiguration

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Manager.Manager import Manager


#-----------------------------------------------------------
#             Centralised Random Reconfiguration
#-----------------------------------------------------------

def schedule_centralised_reconfiguration_event(manager: "Manager", time:float) -> None:
    """ Schedules a reconfiguration event of Parameters.reconfiguration['reconfiguration_method'] type
    at time + reconfiguration_interval

    Args:
        manager (Manager): the simulation manager
        time (float): the current time
    """
    schedule_at = time + Parameters.reconfiguration['reconfiguration_interval']
    schedule_at += random.uniform(*Parameters.reconfiguration['reconfiguration_interval_range'])

    event = SystemEvent(
        time = schedule_at,
        payload= {
            "type": Parameters.reconfiguration['reconfiguration_method']
        }
    )
    manager.sim.q.add_event(event)

def handle_random_centralised_reconfiguration_event(manager: "Manager", event: SystemEvent) -> None:    
    """
    
    """
    block = CentralisedReconfiguration.create_random_configuration_block(event.time)

    CentralisedReconfiguration.propagate_configuration_block(manager, block, event.time)

    schedule_centralised_reconfiguration_event(manager, manager.sim.clock)    