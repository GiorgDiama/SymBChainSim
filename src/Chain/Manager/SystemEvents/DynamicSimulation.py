from Chain.Parameters import Parameters, read_yaml
from Chain.Event import SystemEvent
from Chain.Network import Network
from Chain.Metrics import Metrics

from random import normalvariate


class DynamicParameters:
    netwrok = {}
    workload = {}

    @staticmethod
    def init_parameters():
        parms = read_yaml(Parameters.dynamic_sim["config"])

        DynamicParameters.netwrok = parms["network"]
        DynamicParameters.workload = parms["workload"]

###########################################################################
#######################     NETWORK    ####################################
###########################################################################


def schedule_update_network_event(manager, init=False):
    time = manager.sim.clock if init else (
        manager.sim.clock + Parameters.application["TI_dur"])

    event = SystemEvent(
        time=time,
        payload={
            "type": "update_network",
        }
    )

    manager.sim.q.add_event(event)


def handle_update_network_event(manager, event):
    Parameters.network["bandwidth"]["mean"] = normalvariate(
        *DynamicParameters.netwrok["mu_dist"])

    Parameters.network["bandwidth"]["dev"] = normalvariate(
        *DynamicParameters.netwrok["sigma_dist"])

    Network.set_bandwidths()

    schedule_update_network_event(manager)


###########################################################################
######################     WORKLOAD    ####################################
###########################################################################

def schedule_update_workload_event(manager, init=False):
    time = manager.sim.clock - 0.01 if init else (
        manager.sim.clock + Parameters.application["TI_dur"] - 0.01)

    event = SystemEvent(
        time=time,
        payload={
            "type": "update_workload",
        }
    )

    manager.sim.q.add_event(event)


def handle_update_workload_event(manager, event):
    # generation aglrithim requires an int
    Parameters.application["Tn"] = int(normalvariate(
        *DynamicParameters.workload["Tn_norm_dist"]))
    # since transaction sizes are quire small abs to ensure no negative value transactions
    Parameters.application["Tsize"] = abs(normalvariate(
        *DynamicParameters.workload["Tsize_norm_dist"]))

    schedule_update_workload_event(manager)

###########################################################################
######################     SNAPSHOT    ####################################
###########################################################################


def schedule_snapshot_event(manager):
    # -0.01 snap shot before transactions are generated.
    time = manager.sim.clock + Parameters.application["TI_dur"] - 0.01

    event = SystemEvent(
        time=time,
        payload={
            "type": "snapshot",
            'time_last': manager.sim.clock
        }
    )

    manager.sim.q.add_event(event)


def handle_snapshot_event(manager, event):
    Metrics.take_snapshot(manager.sim, event.payload['time_last'])
    schedule_snapshot_event(manager)
