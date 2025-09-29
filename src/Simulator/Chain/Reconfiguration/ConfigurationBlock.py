from Parameters import Parameters

from copy import deepcopy
from typing import Dict, Any


class ConfigurationBlock:
    """Defines a configuration block used to define and updated the blockchains configuration.

    Attributes:
        depth (int): The depth of the block in the blockchain.
        id (int): Unique identifier of the block.
        previous (int): ID of the previous block in the chain.
        time_created (float): Timestamp when the block was created.
        time_added (float): Timestamp when the block was added to the chain.
        proposer (int): ID of the proposer who created the block.
        size (float): Size of the block.
        consensus (str): Consensus mechanism used for the block.
        configuration (Dict[str, Any]): Configuration data stored in the block.
        extra_data (Dict[str, Any]): Additional metadata associated with the block.
    """

    def __init__(self, depth: int = 0, id: int = 0, previous: int = -1, proposer: int = None, size: float = 0, consensus: str = None) -> None:
        self.depth: int = depth
        self.id: int = id
        self.previous: int = previous
        self.time_created: float = 0
        self.time_added: float = 0
        self.proposer: int = proposer
        self.size: float = size
        self.consensus: str = consensus
        self.configuration: Dict[str, Any] = {}
        self.extra_data: Dict[str, Any] = {}

    def copy(self) -> "ConfigurationBlock":
        """Returns a deep copy of the configuration block.

        Returns:
            ConfigurationBlock: A new ConfigurationBlock instance with the same attributes as the original.
        """
        new_block = ConfigurationBlock(self.depth, self.id, self.previous, self.proposer, self.size, self.consensus)
        new_block.time_added = self.time_added
        new_block.time_created = self.time_created
        new_block.extra_data = deepcopy(self.extra_data)
        new_block.configuration = deepcopy(self.configuration)
        new_block.time_added = self.time_added
        return new_block

    @staticmethod
    def from_json(data: Dict[str, Any]) -> "ConfigurationBlock":
        """Creates a ConfigurationBlock instance from JSON data.

        Args:
            data (Dict[str, Any]): Dictionary containing block data.

        Returns:
            ConfigurationBlock: A new ConfigurationBlock instance created from the JSON data.
        """
        block = ConfigurationBlock(
            depth=data["depth"],
            id=data["id"],
            previous=data["previous"],
            proposer=data["proposer"],
            size=data["size"],
            consensus="PBFT",
        )
        block.time_created = data["time_created"]
        block.extra_data = data["extra_data"]
        block.configuration = data["configuration"]
        return block

    @staticmethod
    def genesis_block() -> "ConfigurationBlock":
        """Generates the genesis configuration block with the initial configuration.

        The initial configuration is read from the config file.

        Returns:
            ConfigurationBlock: A new ConfigurationBlock instance representing the genesis block.
        """
        genesis_block = ConfigurationBlock()
        genesis_block.extra_data["round"] = -1
        genesis_block.size = 0.1
        genesis_block.configuration = {
            "CP": Parameters.simulation["init_CP"],
            "block_size": Parameters.data["Bsize"],
            "block_time": Parameters.data["block_time"],
        }
        Parameters.global_configuration_chain = [genesis_block]
        return genesis_block

    def __str__(self) -> str:
        return (
            f"[block: {self.id} | depth: {self.depth} | created:{self.time_created:.2f}"
            + f"| added: {round(self.time_added, 2)} | size: {round(self.size, 2)}"
            + f"| prev {self.previous} | {self.extra_data.keys()} | {self.consensus}]"
            + f"\n|=====> Configuration: {self.configuration}"
        )

    def __repr__(self) -> str:
        return f"|block:{self.id} time:{self.time_created:.2f}-{self.time_added:.2f}|"
