
import os
import sys
import yaml

from Chain.Parameters import Parameters
from Chain.Event import SystemEvent, MessageEvent, Event


def debug_logs(msg, **kwargs):
    '''
        must set enviroment variable 'debug' to true (env_vars.yaml)] (can overwrite with nd as cmd arg)
        colors: 
            40:black
            41:red
            42:green
            43:yellow
            44:light_blue
            45:purple
            46:green
            47:white
    '''

    if os.environ['debug'] == "True" and "nd" not in sys.argv:
        if 'col' in kwargs:
            msg = color(msg, kwargs["col"])

        print(msg, end=kwargs['end'] if 'end' in kwargs else '\n')

        if 'input' in kwargs:
            if "in_col" in kwargs:
                kwargs['input'] = color(kwargs['input'], kwargs['in_col'])

            input(kwargs['input'])
        if "command" in kwargs:
            if "simulator" not in kwargs:
                raise ValueError(
                    "Simulator must be given inorder to use commands")
            else:
                if "cmd_col" in kwargs:
                    kwargs['command'] = color(
                        kwargs['command'], kwargs['cmd_col'])

                cmd = input(kwargs['command'])
                ret = exec_cmd(kwargs["simulator"], cmd)
                print(ret)
        if 'clear' in kwargs and kwargs['clear']:
            os.system('cls' if os.name == 'nt' else 'clear')

        if "command" in kwargs:
            return cmd


def get_named_cmd_arg(name):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name)+1]
    else:
        return None


def set_env_vars_from_config(name="env_vars.yaml"):
    '''
        Sets enviroment variables based on env_vars (cmd_args can overwrite)
    '''
    with open(name, 'rb') as f:
        data = yaml.safe_load(f)

    # YAML file contained ref to other YAML file (dict named config_files)
    for name, d in data.items():
        if name == "config_files":
            for file_name in d:
                set_env_vars_from_config(name=file_name)

        os.environ[name] = str(d)

    # enable/disable debug from cmd ("True"/"False")
    if debug := get_named_cmd_arg("--debug"):
        os.environ["debug"] = debug

    if '--debug_at' in sys.argv:
        os.environ["start_debug"] = get_named_cmd_arg('--debug_at')
        os.environ["debug"] = "False"


def exec_cmd(simulator, cmd):
    ''' When debug mode is on - a command can be given as input (this handles the execution)'''
    if cmd == '':
        return ""

    cmd = cmd.split(" ")
    if cmd[0] == "kill":
        kill = int(cmd[1])
        time = int(cmd[2])
        simulator.nodes[kill].kill()
        simulator.nodes[kill].behaviour.recover_at = simulator.sim_clock + time
        return f"Killing node {kill}"
    elif cmd[0] == "res":
        res = int(cmd[1])
        simulator.nodes[res].resurect()
        return f"Resurecting node {res}"
    elif cmd[0] == "round":
        node = int(cmd[1])
        round = int(cmd[2])
        simulator.nodes[node].state.cp_state.round.round = round
        simulator.nodes[node].state.cp_state.timeout.payload['round'] = round
        return f"Set nodes {node} round to {round}"
    elif cmd[0] == "stop":
        exit()
    elif cmd[0] == "CP":
        if cmd[1] == "PBFT":
            simulator.manager.change_cp(
                sys.modules["Chain.Consensus.PBFT.PBFT"])
        elif cmd[1] == "BigFoot":
            simulator.manager.change_cp(
                sys.modules["Chain.Consensus.BigFoot.BigFoot"])

    elif cmd[0] == "add_node":
        simulator.manager.add_node()
    elif cmd[0] == "remove_node":
        simulator.manager.remove_node()
    else:
        return f"No such command: {cmd}"


def sim_info(simulator, print_event_queues=True):
    if os.environ['debug'] == "True" and "nd" not in sys.argv:
        s = ""
        s += color('-'*30 + 'NODES' + '-'*30, 44) + '\n'
        for n in simulator.nodes:
            s += n.__str__(full=True) + '\n'
        s += color('-'*30 + 'NODES' + '-'*30, 44) + '\n'

        if print_event_queues:
            events_per_node = {-1: ""}
            for e in sorted(simulator.q.prio_queue.pq, key=lambda x: x[0], reverse=True):
                event = e[1]
                if isinstance(event, MessageEvent) or isinstance(event, Event):
                    if event.actor.id in events_per_node:
                        events_per_node[event.actor.id] += str(e[1]) + '\n'
                    else:
                        events_per_node[event.actor.id] = str(e[1]) + '\n'
                else:
                    events_per_node[-1] += str(e[1]) + "\n"

            sort_nodes = sorted(list(events_per_node.keys()))

            for key in sort_nodes:
                if key != -1:
                    s += color(("-"*30 + "NODE " +
                               str(key) + '-'*30), 41) + '\n'
                else:
                    s += color(("-"*30 + "SYSTEM" + '-'*30), 42) + '\n'

                for e in events_per_node[key]:
                    s += e
                s += "\n"

        return s


####################### YAML ######################


def read_yaml(path):
    with open(path, 'rb') as f:
        data = yaml.safe_load(f)
    return data


def write_yaml(data, path):
    with open(path, 'w+') as f:
        yaml.dump(data, f)

###################### COLOR #####################


def color(string, c=44):
    return f'\x1b[1;37;{c}m' + string + '\x1b[0m'

###################### Distriburions #############
