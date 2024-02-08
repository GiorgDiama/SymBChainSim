from Chain.Parameters import Parameters
from Chain.Network import Network

import numpy as np

from collections import namedtuple
from bisect import insort

from collections import deque

import random

##############################   MODELS TRANSACTION  ##########################################
Transaction = namedtuple("Transaction", "creator id timestamp size")


class TransactionFactory:
    '''
        Handles the generation and execution of transactions
    '''

    def __init__(self, nodes) -> None:
        self.nodes = nodes
        # FOR GLOBAL TXION POOL
        self.global_mempool = []
        self.depth_removed = -1

    def transaction_prop(self, tx):
        if Parameters.application["transaction_model"] == "global":
            if Parameters.application["use_tx_prop_model"]:
                # model transaction propagation based on creators bandwidth
                prop_delay = Network.calculate_message_propagation_delay(
                    self.nodes[tx.creator], self.nodes[tx.creator], tx.size)
                new_timestamp = tx.timestamp + prop_delay
                tx = Transaction(tx.creator, tx.id, new_timestamp, tx.size)
                self.global_mempool.append(tx)
            else:
                self.global_mempool.append(tx)

        elif Parameters.application["transaction_model"] == "local":
            for node in self.nodes:
                if node.id == tx.creator:
                    node.pool.append(tx)
                else:
                    prop_delay = Network.calculate_message_propagation_delay(
                        self.nodes[tx.creator], node, tx.size)
                    new_timestamp = tx.timestamp + prop_delay
                    tx = Transaction(tx.creator, tx.id, new_timestamp, tx.size)
                    node.pool.append(tx)
        else:
            raise (ValueError(
                f"Uknown transaction model: '{Parameters.application['transaction_model']}'"))

    def add_scenario_transactions(self, txion_list):
        for creator, id, timestamp, size in txion_list:
            t = Transaction(creator, id, timestamp, size/1000)
            self.transaction_prop(t)

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

                creator = random.choice(self.nodes)

                self.transaction_prop(Transaction(
                    creator.id, id, timestamp, size))

    def execute_transactions(self, pool, time):
        match Parameters.application["transaction_model"]:
            case "local":
                # local pool: execute transactions for the local pool of the node
                return self.get_transactions_from_pool(pool, time)
            case "global":
                # global pool: execute transaction for the "global pool" shared amongst the nodes
                return self.get_transactions_from_pool(self.global_mempool, time)
            case _:
                raise (ValueError(
                    f"Uknown transaction model: '{Parameters.application['transaction_model']}'"))

    @staticmethod
    def get_transactions_from_pool(pool, time):
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

    @staticmethod
    def remove_transactions_from_pool(txions, pool):
        t_idx, p_idx = 0, 0
        # for each transactions in txions go over pool: look for it and remove it
        while t_idx < len(txions) and p_idx < len(pool)-1:
            if txions[t_idx].id == pool[p_idx].id:
                pool.pop(p_idx)
                t_idx += 1
                # start over looking for the next transaction in txions
                p_idx = 0
            else:
                p_idx += 1

        return pool
