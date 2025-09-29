from Parameters import Parameters

from Chain.Network import Network
from Chain.Consensus.PBFT.PBFT_state import PBFT
from Chain.Consensus.BigFoot.BigFoot_state import BigFoot
from Chain.Consensus.Tendermint.TM_state import Tendermint

from Engine.Event import Event, SystemEvent
from Engine.Simulation import Simulation

from Utils import Tools
from Utils.Metrics import Metrics
from Utils import Snapshots

import Manager.SimulationUpdates as updates

from Manager.ScenariosAndWorkloads import load_workload
from Manager.SystemEvents import GenerateTransactions as generate_txionsSE
from Manager.SystemEvents import DynamicSimulation as dynamic_simulationSE
from Manager.SystemEvents import BehaviourEvents as behaviourSE
from Manager.SystemEvents import ScenarioEvents as scenarioSE
from Manager.SystemEvents import ReconfigurationEvents as reconfigurationSE
from Manager.SystemEvents import SnapshotEvents as snapshotSE

import logging

logger = logging.getLogger(__name__.split(".")[-1])

class Manager:
    """
    The manager module controls the 'flow' of the simulation. Through system events
        - The state of the system can be updated during runtime
        - transactions are generated
        - nodes are added and removed
        - node behaviour is applied and managed
    """

    def __init__(self) -> None:
        """
        Initializes the Manager and sets up consensus protocols.
        """
        Parameters.CPs = {
            PBFT.NAME: PBFT,
            BigFoot.NAME: BigFoot,
            Tendermint.NAME: Tendermint,
        }

        self.sim: Simulation = None


    #-----------------------------------------------------------
    #                    Set Up and Configuration
    #-----------------------------------------------------------

    def load_params(self, config: str = "base.yaml") -> None:
        """
        Loads simulation parameters from environment variables, config file, and command line arguments.

        Args:
            config (str): The configuration file to load parameters from. Defaults to "base.yaml".
        """
        Parameters.load_params_from_config(config)
        Tools.parse_cmd_args()

        Tools.set_up_logging()

        logger.debug(f"Loaded simulation parameters from config: {config}")


        Parameters.application["CP"] = Parameters.CPs[Parameters.simulation["init_CP"]]
        Parameters.simulation["event_id"] = 0

        logger.debug(
            f"Parameters loaded. Application CP: {Parameters.application['CP']}"
        )

    def set_up(self, num_nodes: int = -1) -> None:
        """
        Sets up the simulation environment, including nodes, network, system events.

        Args:
            num_nodes (int): Number of nodes to initialize. If -1, uses value from parameters. Defaults to -1.
        """
        if num_nodes != -1:
            Parameters.application["Nn"] = num_nodes
            Parameters.calculate_fault_tolerance()
            logger.debug(
                f"Number of nodes set to {num_nodes} and fault tolerance calculated."
            )

        self.sim = Simulation()
        self.sim.manager = self
        logger.debug("Simulation instance created and manager assigned.")

        Network.init_network(self.sim.nodes)
        logger.debug("Network initialized with simulation nodes.")

        self.init_system_events()
        logger.debug("System events initialized.")

        self.sim.init_simulation()
        logger.debug("Simulation initialized.")

        if Parameters.application.get("workload", "generate") != "generate":
            logger.debug("Loading workload from file.")
            load_workload()

        if Parameters.simulation.get("print_info", False):
            print(self.simulation_details_to_string())

    
    #-----------------------------------------------------------
    #                      Managed Simulation Logic
    #-----------------------------------------------------------

    def run(self) -> None:
        """
        Runs the managed simulation loop until a finish condition is met.
        """
        logger.debug("\n\n########### STARTING SIMULATION LOOP! ###############\n")
        while not self.finished():
            self.sim.sim_next_event()
            self.update_sim()
        
        if Parameters.simulation["snapshot_interval"] != -1:
            Snapshots.save_snapshots()

    def finished(self) -> bool:
        """
        Evaluates all finish conditions for the simulation.

        Returns:
            bool: True if any finish condition is met, otherwise False.
        """
        if times_out := (Parameters.simulation["simTime"] != -1):
            times_out = self.sim.clock >= Parameters.simulation["simTime"]

        if reached_blocks := (Parameters.simulation["stop_after_blocks"] != -1):
            reached_blocks = (
                Metrics.confirmed_blocks(self.sim)
                >= Parameters.simulation["stop_after_blocks"]
            )

        if processed_all := (Parameters.simulation["stop_after_tx"] != -1):
            # TODO: Every node keeps track of processed transactions
            curr_processed = [
                sum([len(block.transactions) for block in node.blockchain])
                for node in self.sim.nodes
            ]
            processed_all = all(
                map(
                    lambda x: x >= Parameters.simulation["stop_after_tx"],
                    curr_processed,
                )
            )

        finished = any([times_out, reached_blocks, processed_all])
        return finished

    def update_sim(self) -> None:
        """
        Performs time-based updates controlled by system events.
        """
        updates.print_progress(self.sim)
        updates.start_debug(self.sim)

    def init_system_events(self) -> None:
        """
        Sets up the system events that dynamically manage the simulation, such as transaction generation, dynamic simulation, behaviour.
        """
        logger.debug("Initializing system events.")
        if Parameters.simulation.get("workload", "generate") == "generate":
            logger.debug("Scheduling transaction generation event.")
            generate_txionsSE.schedule_event(self, init=True)

        if Parameters.dynamic_sim["use"]:
            logger.debug(
                "Dynamic simulation enabled. Initializing dynamic parameters and scheduling events."
            )
            dynamic_simulationSE.DynamicParameters.init_parameters()
            dynamic_simulationSE.schedule_update_network_event(self, init=True)
            dynamic_simulationSE.schedule_update_workload_event(self, init=True)

        if Parameters.simulation["snapshot_interval"] != -1:
            logger.debug(f"Scheduling snapshot events with an interval of {Parameters.simulation["snapshot_interval"]}.")
            snapshotSE.schedule_snapshot_event(self)

        if Parameters.behaviour["use"]:
            logger.debug(
                "Behaviour events enabled. Initializing and scheduling random fault event."
            )
            behaviourSE.Behaviour.init(self)
            behaviourSE.schedule_random_fault_event(self, self.sim.clock)

        if Parameters.reconfiguration.get("reconfigure", False):
            logger.debug("Scheduling reconfiguration system events.")
            reconfigurationSE.schedule_centralised_reconfiguration_event(self, self.sim.clock)

    
    #-----------------------------------------------------------
    #                      SYSTEM EVENTS
    #-----------------------------------------------------------

    def schedule_system_event(self, time: float, payload: dict) -> SystemEvent:
        """
        Schedules a system event in the simulation event queue.

        Args:
            time (float): The simulation time at which the event should occur.
            payload (dict): The payload containing information about the event

        Returns:
            SystemEvent: The scheduled system event.
        """
        logger.debug(f"Scheduling system event at time {time} with payload: {payload}")
        event = SystemEvent(time=time, payload=payload)
        self.sim.q.add_event(event)

        return event

    def handle_system_event(self, event: Event) -> None:
        """
        Handles a system event by dispatching it to the appropriate handler based on its type.

        Args:
            event (Event): The system event to handle.
        """
        match event.payload["type"]:
            #-----------------------------------------------------------
            #                      Transactions
            #-----------------------------------------------------------
            case "generate_txions":
                generate_txionsSE.handle_event(self, event)
            #-----------------------------------------------------------
            #                      Dynamic Simulation
            #-----------------------------------------------------------
            case "update_network":
                dynamic_simulationSE.handle_update_network_event(self, event)
            case "update_workload":
                dynamic_simulationSE.handle_update_workload_event(self, event)
            #-----------------------------------------------------------
            #                      Behaviour
            #-----------------------------------------------------------
            case "random_fault":
                behaviourSE.handle_random_fault_event(self, event)
            case "recovery":
                behaviourSE.handle_recover_event(self, event)
            #-----------------------------------------------------------
            #                      Scenario Events
            #-----------------------------------------------------------
            case "scenario_generate_txions":
                scenarioSE.handle_scenario_transactions_event(self, event)
            case "scenario_update_network":
                scenarioSE.handle_scenario_update_network_event(self, event)
            case "scenario_fault":
                scenarioSE.handle_scenario_fault_event(self, event)
            case "scenario_recovery":
                scenarioSE.handle_scenario_recovery_event(self, event)
            #-----------------------------------------------------------
            #                      Reconfiguration
            #-----------------------------------------------------------
            case "random_centralised":
                reconfigurationSE.handle_random_centralised_reconfiguration_event(self, event)
            #-----------------------------------------------------------
            #                      Snapshots
            #-----------------------------------------------------------
            case "snapshot":
                snapshotSE.handle_snapshot_event(self, event)
            #-----------------------------------------------------------
            #                      Default Case
            #-----------------------------------------------------------
            case _:
                logger.error(f"Unhandled system event type: {event.payload['type']}")
                raise ValueError(
                    f"Event '{
                        event.payload['type']
                    }'was not handled by its own handler..."
                )


    #-----------------------------------------------------------
    #                      UTILITY
    #-----------------------------------------------------------

    def simulation_details_to_string(self) -> str:
        """
        Returns a string with details about the simulation, including node info and simulation parameters.

        Returns:
            str: A formatted string with simulation and node details.
        """
        s = Tools.color("-" * 28 + "NODE INFO" + "-" * 28) + "\n"
        s += ("NODE\tLOCATION\tBANDWIDTH\tCP\tNEIGHBOURS") + "\n"
        for n in self.sim.nodes:
            neigh_list = ",".join([str(n.id) for n in n.neighbours])
            cp_name = "None"
            if n.cp is not None:
                cp_name = n.cp.NAME

            s += (
                f"{n.id:3d} {n.location:12}\t{n.bandwidth}\t{cp_name:10}\t{
                    neigh_list:12}"
                + "\n"
            )

        s += Tools.color("-" * 25 + "SIM PARAMETERS" + "-" * 25) + "\n"
        s += Parameters.parameters_to_string()
        return s
