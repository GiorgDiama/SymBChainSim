from Chain.Parameters import Parameters

import random, sys, numpy as np

from collections import namedtuple
from bisect import insort


##############################   MODELS TRANSACTION  ##########################################
Transaction = namedtuple("Transaction", "id timestamp size")


class FullTransaction():
    '''
        Handles the generation and execution of transactions
    '''
    def __init__(self, nodes, bps) -> None:
        self.nodes = nodes
        self.bps = bps

    def transaction_prop(self, tx):
        for node in self.bps:
            node.pool.append(tx)

    def generate_interval_txions(self, start):
        for second in range(round(start), round(start + Parameters.application["TI_dur"])):
            for _ in range(Parameters.application["Tn"]):
                id =  Parameters.application["txIDS"]
                Parameters.application["txIDS"] += 1
                            
                timestamp = second
                
                #size = random.expovariate(1/Parameters.simulation["Tsize"])
                size = Parameters.application["Tsize"]

                self.transaction_prop(Transaction(id, timestamp, size))

    def execute_transactions(self, pool):
        transactions = []
        size = 0

        for tx in pool:
            if size + tx.size <= Parameters.data["Bsize"]:
                transactions.append(tx)
                size += tx.size
            else:
                break

        return transactions, size
