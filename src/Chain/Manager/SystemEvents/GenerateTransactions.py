from Chain.Parameters import Parameters
from Chain.Event import SystemEvent


def schedule_event(manager, init=False):
    time = manager.sim.clock if init else (
        manager.sim.clock + Parameters.application["TI_dur"])

    event = SystemEvent(
        time=time,
        payload={
            "type": "generate_txions",
        }
    )

    manager.sim.q.add_event(event)


def handle_event(manager, event):
    Parameters.tx_factory.generate_interval_txions(event.time)

    schedule_event(manager)
