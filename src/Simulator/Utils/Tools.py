from Parameters import Parameters

from Engine.Event import MessageEvent, SystemEvent

from Utils import Serialise

import os
import yaml
import json
import logging

""" A collection of useful utility functions and tools for SBS """

LOG_PATH = "../Outputs/Logs/log.txt"


def set_up_logging():
    LOGGER_FORMAT = "%(name)s:%(funcName)s || %(message)s"
    formatter = logging.Formatter(LOGGER_FORMAT)

    handlers = []
    try:
        file_handler = logging.FileHandler(LOG_PATH, mode="w")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except FileNotFoundError:
        print("WARNING: logs directory not found, skipping writing logs...")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    match Parameters.simulation.get("logging_level", "INFO"):
        case "INFO":
            LEVEL = logging.INFO
        case "DEBUG":
            LEVEL = logging.DEBUG
        case _:
            LEVEL = logging.INFO

    if Parameters.simulation["debugging_mode"]:
        LEVEL = logging.DEBUG

    logging.basicConfig(level=LEVEL, handlers=handlers, force=True)


####################### Simulation Results Analysis #############################


def save_simulation_results(sim, name="results"):
    blockchains = {}
    for node in sim.nodes:
        blockchains[node.id] = []
        for block in node.blockchain[1:]:
            blockchains[node.id].append(
                {
                    "size": block.size,
                    "timestamp": block.time_added,
                    "tx": [(x.id, x.timestamp) for x in block.transactions],
                }
            )

    with open(f"output/{name}.json", "w") as f:
        json.dump(blockchains, f, indent=4)


def dump_reconfiguration_chain(manager):
    if "Metrics" in Parameters.reconfiguration.keys():
        conf_block_ids = Parameters.reconfiguration["Metrics"]["blocks"] = {}
        for block in Parameters.global_configuration_chain:
            assert block.id not in conf_block_ids
            print(
                block.depth,
                f"{str(block.configuration):40}",
                round(block.extra_data.get("requested", -1), 2),
                round(block.extra_data.get("agreed", -1), 2),
            )
            conf_block_ids[block.id] = {}

        for node in manager.sim.nodes:
            for block in node.reconfiguration_state.confchain:
                conf_block_ids[block.id][node.id] = Serialise.serialisable_configuration_block(block)

        Parameters.reconfiguration["Metrics"]["global_chain"] = [Serialise.serialisable_block(block, transactions=False) for block in Parameters.simulation["blockchain"].values()]
        with open("Results/Sensitivity/data.json", "w") as f:
            json.dump(Parameters.reconfiguration["Metrics"], f, indent=2)


############################ DEBUGGER ###########################


def debug_logs(msg, **kwargs):
    """
    Calling debug_logs allows logging messages and stopping simulation and executing commands when the simulation runs in debug mode!
        - calls are ignored during normal execution

    Debug mode can be set from the config or by passing the -d command line argument

    You can use the following colours using the color()  function
        color codes: 40:black | 41:red | 42:green | 43:yellow | 44:light_blue | 45:purple | 46:cyan | 47:white

    Supported **kwargs:
        col: prints the messages with the specified color
        input and in_col: prints the message + an additional message using the input() method essentially stopping the execution until enter is pressed
            - the input is ignored!
            example: debug_logs("Hello", input="another message that will stop execution until enter is pressed")
        command: allows for stopping execution and executing commands
            - when using the command argument the simulation instance must be passed using the simulation kwarg
            list of commands can be seen in exec_cmd()
    """

    if Parameters.simulation["debugging_mode"]:
        if "col" in kwargs:
            msg = color(msg, kwargs["col"])

        print(msg, end=kwargs["end"] if "end" in kwargs else "\n")

        if "input" in kwargs:
            if "in_col" in kwargs:
                kwargs["input"] = color(kwargs["input"], kwargs["in_col"])
            input(kwargs["input"])

        if "command" in kwargs:
            if "simulator" not in kwargs:
                raise ValueError("Simulator must be given in order to use commands")
            else:
                if "cmd_col" in kwargs:
                    kwargs["command"] = color(kwargs["command"], kwargs["cmd_col"])

                cmd = input(kwargs["command"])
                ret = exec_cmd(kwargs["simulator"], cmd)
                print(ret)
                print("=" * 100 + "\n")
        if "clear" in kwargs and kwargs["clear"]:
            os.system("cls" if os.name == "nt" else "clear")

        if "command" in kwargs:
            return cmd


def exec_cmd(simulator, cmd):
    """
    Implementation of commands for debug_logs
    """
    if cmd == "":
        return ""

    cmd = cmd.split(" ")
    if cmd[0] == "kill":
        kill = int(cmd[1])
        simulator.nodes[kill].kill()
        return f"Killing node {kill}"
    elif cmd[0] == "res":
        res = int(cmd[1])
        simulator.nodes[res].resurrect(simulator.clock)
        return f"Resurrecting node {res}"
    elif cmd[0] == "stop":
        exit()
    else:
        return f"No such command: {cmd}"


def sim_info(simulator, print_event_queues=True):
    """
    Prints a detailed state of the simulation state
    """
    if Parameters.simulation["debugging_mode"]:
        s = ""
        # s += color("-" * 30 + "NODES" + "-" * 30, 44) + "\n"
        # for n in simulator.nodes:
        #     s += n.__str__(full=True) + "\n"
        # s += color("-" * 30 + "NODES" + "-" * 30, 44) + "\n"

        if print_event_queues:
            # system events are set to -1 to allow for sorting based on node if
            # later
            events_per_node = {-1: ""}

            for e in sorted(simulator.q.prio_queue.pq, key=lambda x: x[0], reverse=True):
                # get the event (prio_queue stores (priority, event))
                event = e[1]
                # decide what todo based on type
                if not isinstance(event, SystemEvent):
                    # simulation events
                    if isinstance(event, MessageEvent):
                        event_string = str(e[1]) + " from: " + str(e[1].forwarded_by) + "\n"
                    else:
                        event_string = str(e[1]) + "\n"

                    if event.actor.id in events_per_node:
                        events_per_node[event.actor.id] += event_string
                    else:
                        events_per_node[event.actor.id] = event_string
                else:
                    # system events
                    events_per_node[-1] += str(e[1]) + "\n"

            # sort the list of nodes to print events in order
            sort_nodes = sorted(list(events_per_node.keys()))

            node_cp_states = ""
            for key in sort_nodes:
                system = False
                if key != -1:
                    s += color(("-" * 30 + "NODE " + str(key) + "-" * 30), 41) + "\n"
                    node_cp_states += (
                        f"({simulator.nodes[key]} alive:{simulator.nodes[key].state.alive}) -" + simulator.nodes[key].cp.state_to_string() + " BW:" + str(simulator.nodes[key].bandwidth) + "\n"
                    )
                else:
                    s += color(("-" * 30 + "SYSTEM" + "-" * 30), 42) + "\n"
                    system = True

                for e in events_per_node[key]:
                    s += e

                if not system:
                    s += color(("-" * 30 + "backlog " + "-" * 30), 42) + "\n"

                    for e in simulator.nodes[key].backlog:
                        s += " " + str(e) + "\n"

        s += "\n" + node_cp_states
        return s


####################### YAML ######################


def read_yaml(path):
    """
    Reads a yaml file - assumes path is relevant to SBS_SRC
    """
    with open(Parameters.path_to_src + "/" + path, "rb") as f:
        data = yaml.safe_load(f)
    return data


def write_yaml(data, path):
    """
    Write a yaml file - assumes path is relevant to SBS_SRC
    """
    with open(Parameters.path_to_src + "/" + path, "w+") as f:
        yaml.dump(data, f)


###################### COLOR #####################


def color(string, c=44):
    """
    returns 'string' with a specific color
    color codes: 40:black | 41:red | 42:green | 43:yellow | 44:light_blue | 45:purple | 46:cyan | 47:white
    """
    return f"\x1b[1;37;{c}m" + string + "\x1b[0m"
