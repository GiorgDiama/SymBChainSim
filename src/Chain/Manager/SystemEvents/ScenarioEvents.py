from Chain.Parameters import Parameters, read_yaml
from Chain.Event import SystemEvent
from Chain.Network import Network
from Chain.Metrics import Metrics

from random import normalvariate

from Chain.Consensus.HighLevelSync import create_local_sync_event

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


def handle_scnario_recovery_event(manager, event):
    node = event.payload['node']
    time = event.time

    node.resurect()

    # after the node is online, attempt to resync
    synced, synced_neighbour = node.synced_with_neighbours()

    if not synced:
        node.state.synced = False
        create_local_sync_event(node, synced_neighbour, time)
