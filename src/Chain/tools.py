
import os
import sys
import yaml
import subprocess


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

    if Parameters.simulation["debugging_mode"]:
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


def parse_cmd_args():
    if "nd" in sys.argv:
        Parameters.simulation["debugging_mode"] = False

    if "d" in sys.argv:
        Parameters.simulation["debugging_mode"] = True
        Parameters.simulation['remove_timeouts'] = True

    if param := get_named_cmd_arg('da'):
        Parameters.simulation['start_debugging_at'] = float(param)


def exec_cmd(simulator, cmd):
    ''' When debug mode is on - a command can be given as input (this handles the execution)'''
    if cmd == '':
        return ""

    cmd = cmd.split(" ")
    if cmd[0] == "kill":
        kill = int(cmd[1])
        simulator.nodes[kill].kill()
        return f"Killing node {kill}"
    elif cmd[0] == "res":
        res = int(cmd[1])
        simulator.nodes[res].resurect()
        return f"Resurecting node {res}"
    elif cmd[0] == "stop":
        exit()
    else:
        return f"No such command: {cmd}"


def sim_info(simulator, print_event_queues=True):
    if Parameters.simulation["debugging_mode"]:
        try:
            subprocess.run("clear")
        except:
            # this does not work in windows and its not important enough to fix atm..
            pass


        s = ""
        s += color('-'*30 + 'NODES' + '-'*30, 44) + '\n'
        for n in simulator.nodes:
            s += n.__str__(full=True) + '\n'
        s += color('-'*30 + 'NODES' + '-'*30, 44) + '\n'

        if print_event_queues:
            # system events are set to -1 to allow for sorting based on node if later
            events_per_node = {-1: ""}

            for e in sorted(simulator.q.prio_queue.pq, key=lambda x: x[0], reverse=True):
                # get the event (prio_queue stores (priority, event))
                event = e[1]
                # decide what todo based on type
                if isinstance(event, MessageEvent) or isinstance(event, Event):
                    # simulation events
                    if isinstance(event, MessageEvent):
                        event_string = str(e[1]) + " from: " + str(e[1].forwarded_by) + '\n'
                    else:
                         event_string = str(e[1]) + '\n'

                    if event.actor.id in events_per_node:
                        events_per_node[event.actor.id] += event_string
                    else:
                        events_per_node[event.actor.id] = event_string
                else:
                    # system events
                    events_per_node[-1] += str(e[1]) + "\n"

            # sort the list of nodes to print events in order
            sort_nodes = sorted(list(events_per_node.keys()))

            for key in sort_nodes:
                if key != -1:
                    s += color(("-"*30 + "NODE " +
                               str(key) + '-'*30), 41) + '\n'
                    s += simulator.nodes[key].cp.state_to_string()+'\n\n'
                else:
                    s += color(("-"*30 + "SYSTEM" + '-'*30), 42) + '\n'

                for e in events_per_node[key]:
                    s += e

                s += color(("-"*30 + "backlog " + '-'*30), 42) + '\n'

                for e in simulator.nodes[key].backlog:
                    s += ' ' + str(e) + '\n'

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
