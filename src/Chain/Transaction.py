from Chain.Parameters import Parameters

import random
import sys
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

    def transaction_prop(self, tx):
        for node in self.nodes:
            node.pool.append(tx)

    def generate_interval_txions(self, start):
        for second in range(round(start), round(start + Parameters.application["TI_dur"])):
            for _ in range(Parameters.application["Tn"]):
                id = Parameters.application["txIDS"]
                Parameters.application["txIDS"] += 1

                # timestamp = second + random.random()
                timestamp = second

                # size = random.expovariate(1/Parameters.application["Tsize"])
                size = Parameters.application["Tsize"]

                self.transaction_prop(Transaction(id, timestamp, size))

    def block_from_pool(self, pool, time, fail_at):
        # add transactions to the block
        # get current transaction from transaction pool and timeout time
        current_pool = [t for t in pool if t.timestamp <= time]
        '''
            BUG: This might fail if we go over the interval limit
                e.g., If we are at time T and the new interval start at T+1, since that event will not be triggered,
                we wont find that were supposed to be there at T+1 

                SOLUTION:
                    instead of moving time by adding 1, reschedule event
                    a second later, this way the generation event can happen
        '''
        while not current_pool and time + 1 < fail_at:
            time += 1
            current_pool = [t for t in pool if t.timestamp <= time]

        if current_pool and time < fail_at:
            transactions = []
            size = 0

            for tx in current_pool:
                if size + tx.size <= Parameters.data["Bsize"]:
                    transactions.append(tx)
                    size += tx.size
                else:
                    break

            return transactions, size, time
        else:
            return [], -1, time

    def execute_transactions(self, pool, time, fail_at):
        if Parameters.application["use_transactions"]:
            return self.block_from_pool(pool, time, fail_at)
        else:
            raise (NotImplementedError(
                "Parameter 'use_transasctions' is set to False. Feature is not implemented yet... :("))
