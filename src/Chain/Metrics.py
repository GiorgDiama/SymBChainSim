import json
import statistics as st
from Chain.Parameters import Parameters
import Chain.tools as tools

import numpy as np

from copy import copy


class Metrics:
    latency = {}
    throughput = {}
    blocktime = {}
    decentralisation = {}

    blocks = {}
    nodes = {}

    snapshot_count = 0
    snapshots = {}

    @staticmethod
    def confirmed_blocks(sim):
        return min([n.blockchain_length() for n in sim.nodes])

    @staticmethod
    def measure_all(sim, start_from=0):
        for node in sim.nodes:
            # get all blocks added to the chain after the 'start_from'
            BC = [b for b in node.blockchain[1:] if b.time_added >= start_from]

            ###### CALCULATE METRICS ########
            values, avg = Metrics.measure_latency(BC)
            Metrics.latency[node.id] = {"vlues": values, 'AVG': avg}

            TPS = Metrics.measure_throughput(BC)
            Metrics.throughput[node.id] = TPS

            values, avg = Metrics.measure_interblock_time(BC)
            Metrics.blocktime[node.id] = {"values": values, 'AVG': avg}

            gini = Metrics.measure_decentralisation_nodes(sim, BC)
            Metrics.decentralisation[node.id] = gini

    @staticmethod
    def print_metrics():
        averages = {n: {} for n in Metrics.latency.keys()}
        val = "{v:.3f}"

        # latency
        for key, value in Metrics.latency.items():
            averages[key]["Latency"] = "%.3f" % value["AVG"]

        # throughput
        for key, value in Metrics.throughput.items():
            averages[key]["Throughput"] = "%.3f" % value

        # blockctime
        for key, value in Metrics.blocktime.items():
            averages[key]["Blocktime"] = "%.3f" % value["AVG"]

        # decentralisation
        for key, value in Metrics.decentralisation.items():
            averages[key]["Decentralisation"] = "%.6f" % value

        print(tools.color(f'{"-"*30} METRICS {"-"*30}', 41))

        for key, value in averages.items():
            print(f"Node: {key} -> {value}")

    @staticmethod
    def measure_latency(blocks):
        if not blocks:
            return [], -1

        per_block = []

        for b in blocks:
            per_block.append(st.mean(
                [b.time_added - t.timestamp for t in b.transactions])
            )
        return per_block, st.mean(per_block)

    @staticmethod
    def measure_throughput(blocks):
        if not blocks:
            return 0

        time = blocks[-1].time_added - blocks[0].time_created
        sum_tx = sum([len(b.transactions) for b in blocks])
        return sum_tx / time

    @staticmethod
    def measure_interblock_time(blocks):
        if len(blocks) < 2:
            return [], 0

        # for each pair of blocks create the key valie pair "curr -> next": next.time_added - curre.time_added
        diffs = {f"{curr.id} -> {next.id}": next.time_added - curr.time_added
                 for curr, next in zip(blocks[:-1], blocks[1:])}

        return diffs, st.mean(diffs.values())

    @staticmethod
    def gini_coeficient(lorenz_curve):
        # calculating the perfect equality for the given population
        perfect_equality = [(x+1)/len(lorenz_curve)
                            for x in range(len(lorenz_curve))]

        x_axis = [x for x in range(len(perfect_equality))]

        # calculate the area of the perfect equaility curve
        perfect_equality_area = np.trapz(perfect_equality, x_axis)

        # calculate the area of the lorenz curve
        lorenz_area = np.trapz(lorenz_curve, x_axis)

        # gini coeficient
        return 1 - lorenz_area / perfect_equality_area

    @staticmethod
    def measure_decentralisation_nodes(sim, blocks):
        '''
            TODO: 
                Consider how nodes entering and exiting the consensus can be taken into account

            NOTE: 
                This method assumes all nodes are accounted for in the final system state 

                !IF NODES THAT HAVE PRODUCED BLOCKS ARE NOT IN THE GIVEN SYSTEM STATE THIS BREAKS!

                if an extra node joins later this skews the decentralisaion since
                the node did not have equal proposing chances as the other nodes 

                    -- dont know if this is considered when measuring decentralisation
                       but seems like it should not be since the node was not there so 
                       its not the algorithms faults that the system is "less decentralised"
        '''

        if not blocks:
            return -1

        nodes = [node.id for node in sim.nodes]

        block_distribution = {x: 0 for x in nodes}

        total_blocks = len(blocks)

        for b in blocks:
            block_distribution[b.miner] += 1

        dist = sorted(
            [(key, value) for key, value in block_distribution.items()], key=lambda x: x[1])

        dist = [(x[0], x[1]/total_blocks) for x in dist]

        cumulative_dist = [sum([x[1] for x in dist[:i+1]])
                           for i in range(len(dist))]

        return Metrics.gini_coeficient(cumulative_dist)
