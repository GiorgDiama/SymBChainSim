import pickle
import statistics as st
from Chain.Parameters import Parameters
import Chain.tools as tools

import matplotlib.pyplot as plt
import numpy as np


class Metrics:
    latency = {}
    throughput = {}
    blocktime = {}

    decentralisation = {}

    @staticmethod
    def measure_all(sim):
        Metrics.measure_latency(sim)
        Metrics.measure_throughput(sim)
        Metrics.measure_interblock_time(sim)
        Metrics.measure_decentralisation_nodes(sim)

    @staticmethod
    def print_metrics():
        averages = {n: {} for n in Metrics.latency.keys()}
        val = "{v:.3f}"

        # latency
        for key, value in Metrics.latency.items():
            averages[key]["Latency"] = val.format(v=value["AVG"])

        # throughput
        for key, value in Metrics.throughput.items():
            averages[key]["Throughput"] = val.format(v=value)

        # blockctime
        for key, value in Metrics.blocktime.items():
            averages[key]["Blocktime"] = val.format(v=value["AVG"])

        # decentralisation
        for key, value in Metrics.decentralisation.items():
            val = "{v:.6f}"
            averages[key]["Decentralisation"] = val.format(v=value)

        print(tools.color(f'{"-"*30} METRICS {"-"*30}', 41))

        for key, value in averages.items():
            print(f"Node: {key} -> {value}")

    @staticmethod
    def measure_latency(sim):
        for node in sim.nodes:
            Metrics.latency[node.id] = {"values": {}}
            for b in node.blockchain[1:]:
                Metrics.latency[node.id]["values"][b.id] = st.mean(
                    [b.time_added - t.timestamp for t in b.transactions]
                )

            Metrics.latency[node.id]["AVG"] = st.mean(
                [b_lat for _, b_lat in Metrics.latency[node.id]["values"].items()]
            )

    @staticmethod
    def measure_throughput(sim):
        """
            Measured as:  sum_processed_txions / simTime

            TODO: Measure in intervals (possibly missleading??)
        """
        for node in sim.nodes:
            sum_tx = sum([len(b.transactions) for b in node.blockchain[1:]])
            Metrics.throughput[node.id] = sum_tx / sim.clock

    @staticmethod
    def measure_interblock_time(sim):
        for node in sim.nodes:
            # for each pair of blocks create the key valie pair "curr -> next": next.time_added - curre.time_added
            diffs = {f"{curr.id} -> {next.id}": next.time_added - curr.time_added
                     for curr, next in zip(node.blockchain[1:-1], node.blockchain[2:])}

            Metrics.blocktime[node.id] = {
                "values": diffs, "AVG": st.mean(diffs.values())}

    @staticmethod
    def gini_coeficient(cumulative_dist):
        lorenz_curve = [(x+1)/len(cumulative_dist)
                        for x in range(len(cumulative_dist))]
        x_axis = [x for x in range(len(lorenz_curve))]
        '''
            TODO: Validate that this is indeed correct
            NOTE: seems kind of correct
        '''

        # calculate the area of the lorenze curve
        lor_area = np.trapz(lorenz_curve, x_axis)
        # calculate the area of the actual cumulatice distribution
        act_area = np.trapz(cumulative_dist, x_axis)
        # calculate what percentage is the area between the lorenze cruve and the actual curve
        return 1 - act_area / lor_area

    @staticmethod
    def measure_decentralisation_nodes(sim):
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

        nodes = [node.id for node in sim.nodes]

        for node in sim.nodes:
            block_distribution = {x: 0 for x in nodes}
            total_blocks = node.blockchain_length()

            for b in node.blockchain[1:]:
                block_distribution[b.miner] += 1

            dist = sorted(
                [(key, value) for key, value in block_distribution.items()], key=lambda x: x[1])

            dist = [(x[0], x[1]/total_blocks) for x in dist]

            cumulative_dist = [sum([x[1] for x in dist[:i+1]])
                               for i in range(len(dist))]

            gini = Metrics.gini_coeficient(cumulative_dist)

            Metrics.decentralisation[node.id] = gini
