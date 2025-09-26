from Parameters import Parameters

from Chain.Node import Node
from Chain.Block import Block, ConfigurationBlock
from Chain.TransactionFactory import TransactionFactory

from Utils import Tools

from Engine.EventQueue import Queue
from Engine.Handler import handle_event
from Engine.Event import SystemEvent

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from Manager.Manager import Manager

import logging

logger = logging.getLogger(__name__.split(".")[-1])


class Simulation:
    """Basic blockchain simulation instance (must be managed by a Manager object).

    This class manages the core simulation logic including the event queue, clock,
    and keeps track of the nodes and transaction factory modeled.

    Attributes:
        q (Queue): The event queue storing simulation events.
        clock (float): The event-driven simulation clock.
        nodes (List[Node]): The list of blockchain nodes.
        manager: A reference to the Manager instance for this simulation.
    """

    def __init__(self) -> None:
        """Initializes a new simulation instance."""
        self.q = Queue()
        self.clock = 0.0

        self.nodes: List[Node] = [
            Node(x, self.q) for x in range(Parameters.application["Nn"])
        ]

        self.manager: "Manager"

        TransactionFactory.nodes = self.nodes

    def init_simulation(self) -> None:
        """Initializes the blockchains with the genesis block and starts the consensus protocol on the nodes.

        This method:
        1. Creates genesis blocks for both the main blockchain and configuration chain
        2. Adds these blocks to each node's respective chains
        3. Updates each node to initialize the consensus protocol
        """
        genesis = Block.genesis_block()
        configuration_genesis = ConfigurationBlock.genesis_block()

        logger.debug("Initialised Genesis and ConfigurationGenesis Blocks")

        for n in self.nodes:
            n.blockchain.append(genesis)
            n.confchain.append(configuration_genesis)
            # applies the configuration in the genesis configuration block
            n.update(0)

    def sim_next_event(self) -> None:
        """Retrieves and executes the next event in the event queue, updating the simulation clock.

        This method:
            1. Logs debug information about the simulation state
            2. Retrieves the next event from the queue
            3. Updates the simulation clock
            4. Handles the event based on its type (system event or regular event)

        Raises:
            AssertionError: If the simulation clock is ahead of the next event's time.
            ValueError: If SystemEvent is found without a manager session set
        """
        Tools.debug_logs(msg=Tools.sim_info(self, print_event_queues=True))

        # get next event
        next_event = self.q.pop_next_event()

        logger.debug(
            f"NEXT EVENT: {next_event.payload['type']} "
            f"creator:{'' if next_event.creator is None else next_event.creator.id} "
            f"actor:{'' if next_event.actor is None else next_event.actor.id} "
            f"time:{next_event.time}"
        )

        # the bug catcher!
        assert self.clock <= next_event.time, (
            f"Current clock is at {self.clock} but next event is {next_event}!"
        )

        # update sim clock
        self.clock = next_event.time

        Tools.debug_logs(msg=f"Next:{next_event}", command="Command:", simulator=self)

        # call appropriate handler based on event type
        if isinstance(next_event, SystemEvent):
            self.manager.handle_system_event(next_event)
        else:
            handle_event(next_event)
