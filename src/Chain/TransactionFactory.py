from .Parameters import Parameters
from .Network import Network

from collections import namedtuple, deque
import random

class Transaction:
    def __init__(self, creator, id, timestamp, size):
        self.creator = creator
        self.id = id
        self.timestamp = timestamp
        self.size = size
        self.processed = False

    def __str__(self) -> str:
        return f'TX({self.timestamp},{self.size})'
    
    def __repr__(self) -> str:
        return self.__str__()

class TransactionFactory:
    '''
        Handles the generation and execution of transactions and manages the memory pools of nodes

        nodes: the list of the simulated nodes

        supports two types of transaction pool models
            1) Local pool: 
                each node maintains its local transaction pool
            2) Global pool: 
                - a single transaction pool is maintained to improve the efficiency of the simulation
                - the pool is managed by the current block producer in each round
                - an approximate transaction propagation model is utilised to model transaction propagation delay
                    - The model is explained and evaluated in detail in: 
                        TODO: add TOMACS reference when available online

        global_mempool: stores uncommitted transactions when the global mempool option is utilised
        depth_removed: latest block depth (height) for which committed transactions have been removed from the global_mempool
        produced_tx: counts transactions produced by the transaction factory
    '''

    def __init__(self, nodes) -> None:
        self.nodes = nodes

        # FOR GLOBAL TXION POOL
        self.global_mempool = deque([])
        self.depth_removed = -1
        self.produced_tx = 0

    def transaction_prop(self, tx):
        '''
            Models transaction propagation delays
                - currently: local pools utilise the point-to-point delay between the receiver and transaction producer
                    TODO: Utilise topology to calculate propagation delay for gossip
                - Global pool: utilises an approximation of the above model
        '''
        match Parameters.application.get('transaction_model', 'local'):
            case 'local':
                for node in self.nodes:
                    if node.id == tx.creator:
                        continue
                    prop_delay = Network.calculate_message_propagation_delay(
                        self.nodes[tx.creator], node, tx.size)
                    new_timestamp = tx.timestamp + prop_delay
                    tx = Transaction(tx.creator, tx.id, new_timestamp, tx.size)
                    node.pool.append(tx)
            case 'global':
                # model transaction propagation based on creators bandwidth
                prop_delay = Network.calculate_message_propagation_delay(
                    self.nodes[tx.creator], self.nodes[tx.creator], tx.size)
                new_timestamp = tx.timestamp + prop_delay
                tx = Transaction(tx.creator, tx.id, new_timestamp, tx.size)
                self.global_mempool.append(tx)
            case _:
                raise (ValueError(
                    f"Unknown transaction model: '{Parameters.application['transaction_model']}'"))

    def add_scenario_transactions(self, txion_list):
        '''
            Adds transactions from a list to the simulation
        '''
        for creator, id, timestamp, size in txion_list:
            t = Transaction(creator, id, timestamp, size / 1e6)
            self.transaction_prop(t)

    def generate_interval_txions(self, start):
        '''
            Generates transactions for the interval [start, start+TI_dur] based on the parameters defined in the configuration
        '''
        for second in range(round(start), round(start + Parameters.application["TI_dur"])):
            for _ in range(Parameters.application["Tn"]):
                if Parameters.simulation['stop_after_tx'] != -1 and self.produced_tx == Parameters.simulation['stop_after_tx']:
                    return
                
                id = Parameters.application["txIDS"]
                Parameters.application["txIDS"] += 1

                timestamp = second

                size = random.expovariate(1/Parameters.application["Tsize"])
                size += Parameters.application["base_transaction_size"]

                creator = random.choice(self.nodes)

                self.transaction_prop(Transaction(
                    creator.id, id, timestamp, size))
                
                self.produced_tx += 1

    def execute_transactions(self, pool, time):
        '''
            Abstracts transaction execution (picking transactions to be included in the next block) form transaction pool model
            calls the appropriate methods to execute transactions based on the transaction pool model 
        '''
        match Parameters.application.get('transaction_model', 'local'):
            case "local":
                # local pool: execute transactions for the local pool of the node
                return self._get_transactions_from_pool(pool, time)
            case "global":
                # global pool: execute transaction for the "global pool" shared amongst the nodes
                return self._get_transactions_from_pool(self.global_mempool, time)
            case _:
                raise (ValueError(
                    f"Unknown transaction model: '{Parameters.application['transaction_model']}'"))

    @staticmethod
    def _get_transactions_from_pool(pool:deque, time):    
        '''
            Gets transaction from the provided memory pool (either global or local) and returns the appropriate transactions for the next block
            While doing so removes already processed transactions
            Nodes should NOT call this explicitly! Use TransactionFactory.execute_transactions() which makes the appropriate call based on the model 
        '''  
        transactions, size = [], 0
    
        while pool:
            tx = pool[0]
            if tx.processed:
                pool.popleft()
                continue

            if tx.timestamp <= time and size + tx.size <= Parameters.data["Bsize"]:
                transactions.append(tx)
                size += tx.size
                pool.popleft()
            else:
                break

        if transactions:
            return transactions, size
        else:
            # if we did not find any transactions return an empty list
            return [], -1
          
    @staticmethod
    def mark_transactions_as_processed(block, pool):
        '''
            Entry point into transaction pool marking logic -
            calls _mark_pool on the correct data based on the  transaction pool mode
        '''
        if Parameters.application["transaction_model"] == "local":
            Parameters.tx_factory._mark_pool(
                block.transactions, pool)
        elif Parameters.application["transaction_model"] == "global":
            # only one node needs to remove the transactions
            if Parameters.tx_factory.depth_removed < block.depth:
                Parameters.tx_factory.global_mempool = Parameters.tx_factory._mark_pool(
                    block.transactions, Parameters.tx_factory.global_mempool)

                Parameters.tx_factory.depth_removed = block.depth

    @staticmethod
    def _mark_pool(txions, pool):
        '''
            Marks transactions in the pool as processed - 
            these transactions will be removed next time the nodes tried to include them in a block
        '''
        txions = set(txions) # HashMap: 'in' operation is O(1) (assuming no collisions)
        marked = 0

        for tx in pool:
            if tx in txions:
                tx.processed = True
                marked += 1
            if marked == len(txions):
                break

        return pool

