from ...Parameters import Parameters
from ...Event import SystemEvent
from ...Metrics import Metrics

##################### network ##################

def schedule_scenario_update_network_event(manager, info, time):
    event = SystemEvent(
        time=time,
        payload={
            "type": "scenario_update_network",
            "network_info": info
        }
    )

    manager.sim.q.add_event(event)


def handle_scenario_update_network_event(manager, event):
    network_info = event.payload['network_info']

    for id, bw in network_info:
        manager.sim.nodes[id].bandwidth = bw

##################### transactions ##################

def schedule_scenario_transactions_event(manager, txion_list, time):
    event = SystemEvent(
        time=time,
        payload={
            "type": "scenario_generate_txions",
            'txion_list': txion_list
        }
    )

    manager.sim.q.add_event(event)


def handle_scenario_transactions_event(manager, event):
    Parameters.tx_factory.add_scenario_transactions(
        event.payload['txion_list'])


##################### fault and recovery ##################

def schedule_scenario_fault_and_recovery_events(manager, fault_list):
    for entry in fault_list:
        fail_at = entry[1]
        node = manager.sim.nodes[entry[0]]

        event = SystemEvent(
            time=fail_at,
            payload={
                "type": "scenario_fault",
                "node": node
            }
        )
        node.behaviour.fault_event = event
        manager.sim.q.add_event(event)

        recover_at = entry[1] + entry[2]
        event = SystemEvent(
            time=recover_at,
            payload={
                "type": "scenario_recovery",
                'node': node
            }
        )
        node.behaviour.recovery_event = event
        manager.sim.q.add_event(event)


def handle_scenario_fault_event(manager, event):
    event.payload['node'].kill()


def handle_scenario_recovery_event(manager, event):
    node = event.payload['node']
    time = event.time

    node.resurrect(time)


def schedule_scenario_snapshot_event(manager):
    time = manager.sim.clock + \
        Parameters.simulation["snapshot_interval"] - 0.01

    event = SystemEvent(
        time=time,
        payload={
            "type": "scenario_snapshot",
            'time_last': manager.sim.clock
        }
    )

    manager.sim.q.add_event(event)


def handle_scenario_snapshot_event(manager, event):
    Metrics.take_snapshot(manager.sim, event.payload['time_last'])
    schedule_scenario_snapshot_event(manager)
