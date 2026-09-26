import yaml
import logging

logger = logging.getLogger(__name__.split(".")[-1])


def read_yaml(path: str):
    """Reads a yaml file - assumes path is relevant to SBS_SRC"""
    with open(path, "rb") as f:
        data = yaml.safe_load(f)
    return data


class Parameters:
    """Contains all the parameters defined for the simulator and the simulation"""

    dynamic_sim = {}
    simulation = {}
    application = {}
    execution = {}
    data = {}
    consensus = {}
    network = {}
    reconfiguration = {}

    BigFoot = {}
    PBFT = {}
    Tendermint = {}

    behaviour = {}

    CPs = {}

    tx_factory = None

    global_configuration_chain = []

    @staticmethod
    def reset_params():
        """resets all dictionaries storing the parameters of the system"""
        Parameters.dynamic_sim = {}
        Parameters.simulation = {}
        Parameters.application = {}
        Parameters.execution = {}
        Parameters.data = {}
        Parameters.consensus = {}
        Parameters.network = {}
        Parameters.behaviour = {}
        Parameters.CPs = {}

        Parameters.BigFoot = {}
        Parameters.PBFT = {}
        Parameters.Tendermint = {}

        Parameters.reconfiguration = {}

        Parameters.global_configuration_chain = []

    @staticmethod
    def load_params_from_config(config):
        """Parses config yaml file and initialises parameter dictionaries"""
        params = read_yaml(f"../Configs/{config}")

        try:
            Parameters.dynamic_sim = params["dynamic_sim"]
        except KeyError:
            logger.debug("NO 'dynamic_sim' Parameters")

        try:
            Parameters.simulation = params["simulation"]
        except KeyError:
            logger.debug("NO 'simulation' Parameters")

        Parameters.simulation["events"] = {}  # cnt events of each type

        try:
            Parameters.behaviour = params["behaviour"]
        except KeyError:
            logger.debug("NO 'behaviour' Parameters")

        try:
            Parameters.network = params["network"]
        except KeyError:
            logger.debug("NO 'network' Parameters")

        try:
            Parameters.application = params["application"]
            Parameters.calculate_fault_tolerance()
        except KeyError:
            logger.debug("NO 'application' Parameters")

        Parameters.application["txIDS"] = 0

        try:
            Parameters.execution = params["execution"]
        except KeyError:
            logger.debug("NO 'execution' Parameters")

        try:
            Parameters.data = params["data"]
        except KeyError:
            logger.debug("NO 'data' Parameters")

        Parameters.BigFoot = read_yaml(params["consensus"]["BigFoot"])
        Parameters.PBFT = read_yaml(params["consensus"]["PBFT"])
        Parameters.Tendermint = read_yaml(params["consensus"]["Tendermint"])

        try:
            Parameters.reconfiguration = params["reconfiguration"]
        except KeyError:
            logger.debug("NO 'reconfiguration' Parameters")

    @staticmethod
    def apply_overrides(overrides):
        """
        Overrides loaded parameters using dotted keys, e.g. {"network.num_neighbours": 4}

        The first part of the key is the parameter group (simulation, network, PBFT, ...),
        the rest is the path to the value inside it. The key must already exist in the
        loaded config, which catches typos.
        """
        for key, value in overrides.items():
            group, *path = key.split(".")
            params = getattr(Parameters, group, None)

            if not isinstance(params, dict) or not path:
                raise ValueError(f"'{key}' is not a valid parameter (expected <group>.<name>, e.g. network.num_neighbours)")

            for name in path[:-1]:
                if not isinstance(params.get(name), dict):
                    raise ValueError(f"'{key}' is not a valid parameter ('{name}' is not a parameter group)")
                params = params[name]

            if path[-1] not in params:
                raise ValueError(f"'{key}' is not a valid parameter ('{path[-1]}' not found in the loaded config)")

            params[path[-1]] = value

        if "application.Nn" in overrides:
            Parameters.calculate_fault_tolerance()

    @staticmethod
    def calculate_fault_tolerance():
        """Calculates f and 2f+1 using number of nodes in the simulation"""
        Parameters.application["f"] = (Parameters.application["Nn"] - 1) // 3

        Parameters.application["required_messages"] = (2 * Parameters.application["f"]) + 1
