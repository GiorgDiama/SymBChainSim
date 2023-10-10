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
                size = Parameters.application["Tsize"]

                self.transaction_prop(Transaction(id, timestamp, size))

    def block_from_local_pool(self, pool, time, fail_at):
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
        # while we have no transactions progress the time towards the timeout/fail period
        while not current_pool and time + 1 < fail_at:
            time += 1

        # while the block is not full and there still are txions add them to block
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
            # if we did not find any transactions return an empty list
            return [], -1, time

    def block_from_global_pool(self, time, fail_at):
        # add transactions to the block
        # get current transaction from transaction pool and timeout time
        current_pool = [t for t in self.global_mempool if t.timestamp <= time]
        '''
            BUG: This might fail if we go over the interval limit
                e.g., If we are at time T and the new interval start at T+1, since that event will not be triggered,
                we wont find that were supposed to be there at T+1 

                SOLUTION:
                    instead of moving time by adding 1, reschedule event
                    a second later, this way the generation event can happen
        '''
        # while we have no transactions progress the time towards the timeout/fail period
        while not current_pool and time + 1 < fail_at:
            time += 1

        # while the block is not full and there still are txions add them to block
        if current_pool and time < fail_at:
            transactions = []
            size = 0
            indecies = []

            for i, tx in enumerate(current_pool):
                if size + tx.size <= Parameters.data["Bsize"]:
                    transactions.append(tx)
                    indecies.append(i)
                    size += tx.size
                else:
                    break

            while indecies:
                remove = indecies.pop(0)
                indecies = [x-1 for x in indecies]
                self.global_mempool.pop(remove)

            return transactions, size, time
        else:
            # if we did not find any transactions return an empty list
            return [], -1, time

    def execute_transactions(self, pool, time, fail_at):
        if Parameters.application["transaction_model"] == "local":
            # execute transactions in the mempool
            return self.block_from_local_pool(pool, time, fail_at)
        elif Parameters.application["transaction_model"] == "global":
            return self.block_from_global_pool(time, fail_at)
        else:
            raise (ValueError(
                f"Uknown transaction model: '{Parameters.application['transaction_model']}'"))
