from Parameters import Parameters

from Utils import Report


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
        Report.print_progress(sim)


def start_debug(sim):
    """Starts the built-in debugger `Parameters.simulation.start_debugging_at`"""
    if Parameters.simulation["start_debugging_at"] != -1 and sim.clock >= Parameters.simulation["start_debugging_at"]:
        Parameters.simulation["debugging_mode"] = True
