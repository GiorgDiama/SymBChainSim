from ..Parameters import Parameters
from ..Event import MessageEvent, Event

import os
import sys
import yaml
import subprocess

'''
    A collection of useful utility functions and tools for SBS
'''
def get_named_cmd_arg(name):
    '''
        Searches argv for a patterns of type "--opt_name value" and returns value if opt_name==name
    '''
    if name in sys.argv:
        return sys.argv[sys.argv.index(name)+1]
    else:
        return None

def parse_cmd_args():
    '''
        Modifies simulation parameters based on cmd arguments
    '''
    if "nd" in sys.argv:
        Parameters.simulation["debugging_mode"] = False

    if "d" in sys.argv:
        Parameters.simulation["debugging_mode"] = True

    if param := get_named_cmd_arg('da'):
        Parameters.simulation['start_debugging_at'] = float(param)

    if param := get_named_cmd_arg('--gossip'):
        Parameters.network['gossip'] = bool(param)

    if param := get_named_cmd_arg('--peers'):
        Parameters.network['num_neighbours'] = int(param)
    
    if param := get_named_cmd_arg('--cp'):
        Parameters.simulation['init_CP'] = param

def parse_env_vars():
    if sbs_src := os.environ.get('SBS_SRC'):
        Parameters.path_to_src = sbs_src
    else:
        print('WARNING: "SBS_SRC" defaulted to CWD! If you are seeing path errors, export SBS_SRC="path/to/SymbChainSim/src"')
        

def debug_logs(msg, **kwargs):
    '''
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
                    "Simulator must be given in order to use commands")
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

def exec_cmd(simulator, cmd):
    '''
        Implementation of commands for debug_logs
    '''
    if cmd == '':
        return ""

    cmd = cmd.split(" ")
    if cmd[0] == "kill":
        kill = int(cmd[1])
        simulator.nodes[kill].kill()
        return f"Killing node {kill}"
    elif cmd[0] == "res":
        res = int(cmd[1])
        simulator.nodes[res].resurrect()
        return f"Resurrecting node {res}"
    elif cmd[0] == "stop":
        exit()
    else:
        return f"No such command: {cmd}"


def sim_info(simulator, print_event_queues=True):
    '''
        Prints a detailed state of the simulation state
    '''
    if Parameters.simulation["debugging_mode"]:
        try:
            subprocess.run("clear")
        except:
            subprocess.run(['cmd.exe', '/c', 'cls'])

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

            node_cp_states = ''
            for key in sort_nodes:
                if key != -1:
                    s += color(("-"*30 + "NODE " +
                               str(key) + '-'*30), 41) + '\n'
                    s += f"({simulator.nodes[key].state.alive}) CP_STATE:" + simulator.nodes[key].cp.state_to_string()+'\n\n'
                    node_cp_states += f"({simulator.nodes[key]} alive:{simulator.nodes[key].state.alive}) -" + simulator.nodes[key].cp.state_to_string() + " BW:" + str(simulator.nodes[key].bandwidth) + '\n'
                else:
                    s += color(("-"*30 + "SYSTEM" + '-'*30), 42) + '\n'

                for e in events_per_node[key]:
                    s += e

                s += color(("-"*30 + "backlog " + '-'*30), 42) + '\n'

                for e in simulator.nodes[key].backlog:
                    s += ' ' + str(e) + '\n'

                s += "\n"
            
        s += node_cp_states
        return s

####################### YAML ######################

def read_yaml(path):
    '''
        Reads a yaml file - assumes path is relevant to SBS_SRC
    '''
    with open(Parameters.path_to_src + '/' + path, 'rb') as f:
        data = yaml.safe_load(f)
    return data


def write_yaml(data, path):
    '''
        Write a yaml file - assumes path is relevant to SBS_SRC
    '''
    with open(Parameters.path_to_src + '/' + path, 'w+') as f:
        yaml.dump(data, f)

###################### COLOR #####################

def color(string, c=44):
    '''
        returns 'string' with a specific color
        color codes: 40:black | 41:red | 42:green | 43:yellow | 44:light_blue | 45:purple | 46:cyan | 47:white
    '''
    return f'\x1b[1;37;{c}m' + string + '\x1b[0m'

###################### Distributions #############
