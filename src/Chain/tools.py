
import os
import sys
import yaml

from Chain.Parameters import Parameters


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


def global_event_queue(simulator):
    queue = []
    for n in simulator.bps:
        for e in reversed(n.queue.event_list):
            queue.append(e)

    return sorted(queue)


def print_global_eq(simulator, ret=False, indiv=True):
    s = ""
    s += color('-'*30 + 'NODES' + '-'*30, 44) + '\n'
    for n in simulator.nodes:
        s += n.__str__(full=True) + '\n'
    s += color('-'*30 + 'NODES' + '-'*30, 44) + '\n'

    if indiv:
        s += color('-'*30 + 'EVENTS' + '-'*30, 45) + '\n'
        for n in simulator.nodes:
            if n.state.alive:
                s += color(n.__str__(), 42) + '\n'
            else:
                s += color(n.__str__(), 41) + '\n'
            for e in reversed(n.queue.event_list):
                s += "\t" + e.__str__() + '\n'
            s += color("syncMSG", 44) + '\n'
            for e in reversed(n.sync_queue.event_list):
                s += "\t" + e.__str__() + '\n'
            s += color("backlog", 43) + '\n'
            for e in reversed(n.backlog):
                s += color("\t" + e.__str__(), 43) + '\n'
        s += color("----------SYSTEM EVENTS------------", 44) + '\n'
        for e in reversed(simulator.system_queue.event_list):
            s += "\t" + e.__str__() + '\n'

        s += color('-'*30 + 'EVENTS' + '-'*30, 45) + '\n'
    else:
        s += '-'*10 + 'EVENTS' + '-'*10 + '\n'
        for e in reversed(global_event_queue(simulator)[1:]):
            if ret:
                s += e.__str__() + '\n'
    if ret:
        return s
    else:
        print(s)


def print_indiv_eqs(simulator):
    for n in simulator.nodes:
        print(n)
        for e in reversed(n.queue.event_list):
            print(e)


def print_node_state(simulator):
    for n in simulator.nodes:
        print(n)
        for k in n.state.cp_state.__dict__:
            if k != 'timeout':
                print(k, n.state.cp_state.__dict__[k])
        print()

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
