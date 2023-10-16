import yaml


def read_yaml(path):
    with open(path, 'rb') as f:
        data = yaml.safe_load(f)
    return data


class Parameters:
    '''
        Contains all the parameters defining the simulator
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

    CPs = {}

    tx_factory = None

    @staticmethod
    def load_params_from_config(config="base"):
        params = read_yaml(f"Configs/{config}")

        Parameters.dynamic_sim = params["dynamic_sim"]

        Parameters.simulation = params["simulation"]
        Parameters.simulation["events"] = {}  # cnt events of each type

        Parameters.behaiviour = params["behaviour"]

        Parameters.network = params["network"]

        Parameters.application = params["application"]
        Parameters.application["txIDS"] = 0
        Parameters.calculate_fault_tolerance()

        Parameters.execution = params["execution"]

        Parameters.data = params["data"]

        Parameters.BigFoot = read_yaml(params['consensus']['BigFoot'])
        Parameters.PBFT = read_yaml(params['consensus']['PBFT'])

    @staticmethod
    def calculate_fault_tolerance():
        Parameters.application["f"] = int((1/3) * Parameters.application["Nn"])

        Parameters.application["required_messages"] = (
            2 * Parameters.application["f"]) + 1
