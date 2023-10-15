from Chain.Parameters import Parameters

import numpy as np

from collections import namedtuple
from bisect import insort

##############################   MODELS TRANSACTION  ##########################################
Transaction = namedtuple("Transaction", "id timestamp size")


class TransactionFactory:
    '''
        Handles the generation and execution of transactions
    '''

    def __init__(self, nodes) -> None:
        self.nodes = nodes
        self.global_mempool = []

    def transaction_prop(self, tx):
        if Parameters.application["transaction_model"] == "global":
            self.global_mempool.append(tx)
        elif Parameters.application["transaction_model"] == "local":
            for node in self.nodes:
                node.pool.append(tx)
        else:
            raise (ValueError(
                f"Uknown transaction model: '{Parameters.application['transaction_model']}'"))

    def generate_interval_txions(self, start):
        for second in range(round(start), round(start + Parameters.application["TI_dur"])):
            for _ in range(Parameters.application["Tn"]):
                id = Parameters.application["txIDS"]
                Parameters.application["txIDS"] += 1

                # timestamp = second + random.random()
                timestamp = second

                # size = random.expovariate(1/Parameters.application["Tsize"])
                size = Parameters.application["Tsize"] + \
                    Parameters.application["base_transation_size"]

                self.transaction_prop(Transaction(id, timestamp, size))

    def get_transactions(self, pool, time):
        transactions = []
        size = 0

        for tx in pool:
            if tx.timestamp <= time and size + tx.size <= Parameters.data["Bsize"]:
                transactions.append(tx)
                size += tx.size
            else:
                break

        if transactions:
            return transactions, size
        else:
            # if we did not find any transactions return an empty list
            return [], -1

    def execute_transactions(self, pool, time):
        if Parameters.application["transaction_model"] == "local":
            return self.get_transactions(pool, time)
        elif Parameters.application["transaction_model"] == "global":
            return self.get_transactions(self.global_mempool, time)
        else:
            raise (ValueError(
                f"Uknown transaction model: '{Parameters.application['transaction_model']}'"))
