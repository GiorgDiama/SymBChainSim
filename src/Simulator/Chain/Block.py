from Parameters import Parameters

import random
from copy import deepcopy
from typing import List, Dict, Any, Optional


class Block:
    """Defines the block - the building block of the blockchain data structure.

    Attributes:
        depth (int): The depth of the block in the blockchain.
        id (int): Unique identifier of the block.
        previous (int): ID of the previous block in the chain.
        time_created (float): Timestamp when the block was created.
        time_added (float): Timestamp when the block was added to the chain.
        miner (int): ID of the miner who created the block.
        transactions (List[Any]): List of transactions included in the block.
        size (float): Size of the block.
        consensus (Optional[str]): Consensus mechanism used for the block.
        extra_data (Dict[str, Any]): Additional metadata associated with the block.
    """

    def __init__(
        self,
        depth: int = 0,
        id: int = 0,
        previous: int = -1,
        time_created: float = 0,
        miner: int = None,
        transactions: List[Any] = [],
        size: float = 0,
        consensus: str = None,
    ) -> None:
        self.depth: int = depth
        self.id: int = id
        self.previous: int = previous
        self.time_created: float = time_created
        self.time_added: float = 0
        self.miner: int = miner
        self.transactions: List[Any] = transactions if transactions is not None else []
        self.size: float = size
        self.consensus: str = consensus
        self.extra_data: Dict[str, Any] = {}

    def __str__(self) -> str:
        return f"~block: {self.id:5} | depth: {self.depth:4} | proposer: {
            self.miner:2} | {self.time_created:5.2f} {self.time_added:5.2f} | size: {
            self.size:5.2f}| prev {self.previous:5} | {self.consensus}~"

    def __repr__(self) -> str:
        return f"~block: {self.id}~"

    def copy(self) -> "Block":
        """Returns a deep copy of the block.

        Returns:
            Block: A new Block instance with the same attributes as the original.
        """
        new_block = Block(
            self.depth,
            self.id,
            self.previous,
            self.time_created,
            self.miner,
            self.transactions,
            self.size,
            self.consensus,
        )
        new_block.extra_data = deepcopy(self.extra_data)
        new_block.time_added = self.time_added
        return new_block

    @staticmethod
    def genesis_block() -> "Block":
        """Generates the genesis block at round -1.

        Returns:
            Block: A new Block instance representing the genesis block.
        """
        genesis_block = Block(0, random.randint(0, 10_000), size=0)
        # nodes that rejoin consensus set round to last_block_round + 1
        # setting round to -1 allows nodes who fail and join at round 0 to start at the correct round
        genesis_block.extra_data["round"] = -1
        return genesis_block


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

    def __init__(
        self,
        depth: int = 0,
        id: int = 0,
        previous: int = -1,
        proposer: int = None,
        size: float = 0,
        consensus: str = None,
    ) -> None:
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
        new_block = ConfigurationBlock(
            self.depth, self.id, self.previous, self.proposer, self.size, self.consensus
        )
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
            "block_interval": Parameters.data["block_interval"],
        }
        return genesis_block

    def __str__(self) -> str:
        return f"[block: {self.id} | depth: {self.depth} | created:{
            self.time_created:.2f} | added: {round(self.time_added, 2)} | size: {
            round(self.size, 2)
        } | prev {self.previous} | {self.extra_data.keys()} | {self.consensus}]"

    def __repr__(self) -> str:
        return f"|block:{self.id} time:{self.time_created:.2f}-{self.time_added:.2f}|"
