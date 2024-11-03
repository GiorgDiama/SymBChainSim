import yaml


def read_yaml(path):
    '''
        Reads a yaml file - assumes path is relevant to SBS_SRC
    '''
    with open(Parameters.path_to_src + '/' + path, 'rb') as f:
        data = yaml.safe_load(f)
    return data


class Parameters:
    '''
        Contains all the parameters defined for the simulator and the simulation
    '''
    dynamic_sim = {}
    simulation = {}
    application = {}
    execution = {}
    data = {}
    consensus = {}
    network = {}

    BigFoot = {}
    PBFT = {}
    Tendermint = {}

    behaviour = {}

    CPs = {}

    tx_factory = None

    path_to_src = '.'

    @staticmethod
    def reset_params():
        Parameters.dynamic_sim = {}
        Parameters.simulation = {}
        Parameters.application = {}
        Parameters.execution = {}
        Parameters.data = {}
        Parameters.consensus = {}
        Parameters.network = {}
        Parameters.behaviour = {}
        Parameters.CPs = {}
        Parameters.tx_factory = None

        Parameters.BigFoot = {}
        Parameters.PBFT = {}
        Parameters.Tendermint = {}


    @staticmethod
    def load_params_from_config(config):
        '''
            Parses config yaml file and initialises parameter dictionaries
        '''
        params = read_yaml(f"/Configs/{config}")

        try:
            Parameters.dynamic_sim = params["dynamic_sim"]
        except KeyError:
            print("NO 'dynamic_sim' Parameters")

        try:
            Parameters.simulation = params["simulation"]
        except KeyError:
            print("NO 'simulation' Parameters")

        Parameters.simulation["events"] = {}  # cnt events of each type

        try:
            Parameters.behaviour = params["behaviour"]
        except KeyError:
            print("NO 'behaviour' Parameters")

        try:
            Parameters.network = params["network"]
        except KeyError:
            print("NO 'network' Parameters")

        try:
            Parameters.application = params["application"]
            Parameters.calculate_fault_tolerance()
        except KeyError:
            print("NO 'application' Parameters")

        Parameters.application["txIDS"] = 0

        try:
            Parameters.execution = params["execution"]
        except KeyError:
            print("NO 'execution' Parameters")

        try:
            Parameters.data = params["data"]
        except KeyError:
            print("NO 'data' Parameters")

        Parameters.BigFoot = read_yaml(params['consensus']['BigFoot'])
        Parameters.PBFT = read_yaml(params['consensus']['PBFT'])
        Parameters.Tendermint = read_yaml(params['consensus']['Tendermint'])

    @staticmethod
    def calculate_fault_tolerance():
        '''
            Calculates f and 2f+1 using number of nodes in the simulation
        '''
        Parameters.application["f"] = int((1/3) * Parameters.application["Nn"])

        Parameters.application["required_messages"] = (
            2 * Parameters.application["f"]) + 1

    @staticmethod
    def parameters_to_string():
        '''
            Returns a formatted string of all simulation parameters
        '''
        p_name_size = 30

        def dict_to_str(x):
            return '\n'.join([f'{f"%{p_name_size}s"%key}: {value}' for key, value in x.items()])

        s = '-'*20 + "DYNAMIC" + "-"*20 + '\n'
        s += dict_to_str(Parameters.dynamic_sim) + '\n'

        s += '-'*20 + "SIMULATION" + "-"*20 + '\n'
        s += dict_to_str(Parameters.simulation) + '\n'

        s += '-'*20 + "APPLICATION" + "-"*20 + '\n'
        s += dict_to_str(Parameters.application) + '\n'

        s += '-'*20 + "EXECUTION" + "-"*20 + '\n'
        s += dict_to_str(Parameters.execution) + '\n'

        s += '-'*20 + "DATA" + "-"*20 + '\n'
        s += dict_to_str(Parameters.data) + '\n'

        s += '-'*20 + "NETWORK" + "-"*20 + '\n'
        s += dict_to_str(Parameters.network) + '\n'

        s += '-'*20 + "BEHAVIOUR" + "-"*20 + '\n'
        s += dict_to_str(Parameters.behaviour) + '\n'

        return s
