from Parameters import Parameters

from Utils.Metrics import Metrics
from Utils import Tools


"""
Simulation Updates are a less dynamic method of updating the simulation.
These are less powerful than SystemEvent based updates but can be useful
for simple functions like periodically printing some information etc...
THESE ARE NOT EVENTS! Simulation Update logic is ONLY triggered after
an event. Thus logic that needs to be trigger periodically cannot have a
static period using simulation updates - it will trigger alongside the
first event that takes place after a period is completed.

If doing the desired action at a specific time is important use SystemEvents!
"""


def print_progress(sim):
    """Prints the progress of the simulation every `Parameters.simulation.print_every`"""
    if "print_next" not in Parameters.simulation:
        Parameters.simulation["print_next"] = 0

    if sim.clock >= Parameters.simulation["print_next"] and Parameters.simulation["print_every"] != -1:
        Parameters.simulation["print_next"] += Parameters.simulation["print_every"]

        sim_time = f"Simulation time: {'%.2f' % sim.clock:>10} out of {Parameters.simulation['simTime']}"
        blocks = f"Confirmed blocks: {Metrics.confirmed_blocks(sim):>5} out of {Parameters.simulation['stop_after_blocks']}"
        tx = f"Confirmed Transactions {Metrics.processed_tx_system(sim):>10} out of {Parameters.simulation['stop_after_tx']}"

        s = f"{sim_time}\t{blocks}\t{tx}"

        print(Tools.color(s, 44))


def start_debug(sim):
    """Starts the built-in debugger `Parameters.simulation.start_debugging_at`"""
    if "start_debugging_at" in Parameters.simulation and sim.clock >= Parameters.simulation["start_debugging_at"]:
        Parameters.simulation["debugging_mode"] = True
