import random
import copy

class Block:
    '''
        Defines the block - a basic component of the blockchain
    '''
    def __init__(self, depth=0, id=0, previous=-1,
                 time_created=0, miner=None, transactions=[], size=1.0, consensus=None):
        
        self.depth = depth
        self.id = id
        self.previous = previous
        self.time_created = time_created
        self.time_added = 0
        self.miner = miner
        self.transactions = transactions
        self.size = size

        self.consensus = consensus

        self.extra_data = {}

    def __str__(self) -> str:
        return f"~block: {self.id} | depth: {self.depth} | created/added: {round(self.time_created,2)}/{round(self.time_added,2)} | size: {round(self.size,2)} | prev {self.previous} | {self.extra_data}~"

    def __repr__(self) -> str:
        return f"~block: {self.id}~"

    def copy(self):
        '''
            Returns a copy of the block
        '''
        new_block = Block(self.depth, self.id, self.previous, self.time_created,
                          self.miner, self.transactions, self.size, self.consensus)
                          
        new_block.extra_data = copy.copy(self.extra_data)

        return new_block

    def to_serializable(self):
        return {
            "id": self.id,
            "depth": self.depth,
            "previous": self.previous,
            "time_created": self.time_created,
            "time_added": self.time_added,
            "miner": self.miner,
            "consensus": self.consensus.NAME,
            "size": self.size,
            "round": self.extra_data["round"],
            "transactions": [x for x in self.transactions]
        }
    
    @staticmethod
    def genesis_block():
        '''
            Generates the gensis block
        '''
        return Block(0, random.randint(0, 10_000), size=0)