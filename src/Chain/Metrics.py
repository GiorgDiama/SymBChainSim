import json
import statistics as st
from Chain.Parameters import Parameters
import Chain.tools as tools

import matplotlib.pyplot as plt
import numpy as np

from copy import copy


class Metrics:
    latency = {}
    throughput = {}
    blocktime = {}
    decentralisation = {}

    blocks = {}
    nodes = {}

    time_last_snapshot = 0
    snapshot_count = 0
    snapshots = {}

    @staticmethod
    def confirmed_blocks(sim):
        return min([n.blockchain_length() for n in sim.nodes])

    @staticmethod
    def measure_all(sim, start_from=-1, blocks=None):
        Metrics.measure_latency(sim, start_from, blocks)
        Metrics.measure_throughput(sim, start_from, blocks)
        Metrics.measure_interblock_time(sim, start_from, blocks)
        Metrics.measure_decentralisation_nodes(sim, start_from, blocks)

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
    def measure_latency(sim, start_from=-1, blocks=None):
        for node in sim.nodes:
            if blocks is None:
                if start_from != -1:
                    blocks = [b for b in node.blockchain[1:]
                              if b.time_added >= start_from]
                else:
                    blocks = node.blockchain[1:]

            if not blocks:
                return -1

            Metrics.latency[node.id] = {"values": {}}

            for b in blocks:
                Metrics.latency[node.id]["values"][b.id] = st.mean(
                    [b.time_added - t.timestamp for t in b.transactions]
                )

            Metrics.latency[node.id]["AVG"] = st.mean(
                [b_lat for _, b_lat in Metrics.latency[node.id]["values"].items()]
            )

    @staticmethod
    def measure_throughput(sim, start_from=-1, blocks=None):

        for node in sim.nodes:
            # getting the correct amount of blocks
            if blocks is None:
                if start_from != -1:
                    blocks = [b for b in node.blockchain[1:]
                              if b.time_added >= start_from]
                else:
                    blocks = node.blockchain[1:]

            if not blocks:
                return -1

            time = blocks[-1].time_added - blocks[0].time_created

            sum_tx = sum([len(b.transactions) for b in blocks])

            Metrics.throughput[node.id] = sum_tx / time

    @staticmethod
    def measure_interblock_time(sim, start_from=-1, blocks=None):
        for node in sim.nodes:
            # getting the correct amount of blocks
            if blocks is None:
                if start_from != -1:
                    blocks = [b for b in node.blockchain[1:]
                              if b.time_added >= start_from]
                else:
                    blocks = node.blockchain[1:]

            if not blocks:
                return -1

            # for each pair of blocks create the key valie pair "curr -> next": next.time_added - curre.time_added
            diffs = {f"{curr.id} -> {next.id}": next.time_added - curr.time_added
                     for curr, next in zip(blocks[:-1], blocks[1:])}

            Metrics.blocktime[node.id] = {
                "values": diffs, "AVG": st.mean(diffs.values())}

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
    def measure_decentralisation_nodes(sim, start_from=-1, blocks=None):
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

            if blocks is None:
                if start_from != -1:
                    blocks = [b for b in node.blockchain[1:]
                              if b.time_added >= start_from]
                else:
                    blocks = node.blockchain[1:]

            if not blocks:
                return -1

            total_blocks = len(blocks)

            for b in blocks:
                block_distribution[b.miner] += 1

            dist = sorted(
                [(key, value) for key, value in block_distribution.items()], key=lambda x: x[1])

            dist = [(x[0], x[1]/total_blocks) for x in dist]

            cumulative_dist = [sum([x[1] for x in dist[:i+1]])
                               for i in range(len(dist))]

            gini = Metrics.gini_coeficient(cumulative_dist)

            Metrics.decentralisation[node.id] = gini

    @staticmethod
    def serialisable_node(node):
        state = {}

        state["bandwidth"] = node.bandwidth
        state["location"] = node.location
        state["neighbours"] = [n.id for n in node.neighbours]
        state["current_cp"] = node.cp.NAME
        state["pool"] = [str((t.id, t.timestamp, t.size))
                         for t in node.pool]

        return state

    @staticmethod
    def serialisable_block(block):
        block_info = {}
        block_info["id"] = block.id
        block_info["previous"] = block.previous
        block_info["time_created"] = block.time_created
        block_info["time_added"] = block.time_added
        block_info["miner"] = block.miner
        block_info["transactions"] = [str((t.id, t.timestamp, t.size))
                                      for t in block.transactions]
        block_info["size"] = block.size

        return block_info

    @staticmethod
    def take_snapshot(sim, entire_state: bool):
        if not entire_state:
            Metrics.measure_all(sim, start_from=Metrics.time_last_snapshot)
        else:
            Metrics.measure_all(sim)

        snapshot = {
            'time': sim.clock,
            'time_last': Metrics.time_last_snapshot,
            'metrics': {
                'latency': copy(Metrics.latency),
                'throughput': copy(Metrics.throughput),
                'block_time': copy(Metrics.blocktime),
                'decentralisation': copy(Metrics.decentralisation),
            },
            'nodes': {},
            'global_pool': [
                str((t.id, t.timestamp, t.size))
                for t in Parameters.simulation['txion_model'].global_mempool
                if t.timestamp <= sim.clock
            ]

        }

        for node in sim.nodes:
            state = Metrics.serialisable_node(node)
            state["pool"] = [t for t in state["pool"]
                             if t[1] <= sim.time]

            state["blocks"], state["new_blocks"] = [], []
            for b in node.blockchain[1:]:
                block = Metrics.serialisable_block(b)

                if block["time_added"] >= Metrics.time_last_snapshot:
                    state['new_blocks'].append(block)

                state["blocks"].append(block)

            snapshot['nodes'][node.id] = state

        Metrics.snapshots[Metrics.snapshot_count] = snapshot

        Metrics.time_last_snapshot = sim.clock
        Metrics.snapshot_count += 1

    @staticmethod
    def calculate_snapshot_metricts(final_sim):
        '''
            TODO: instead of calculating the metrics during simulation
            do it after
        '''
        for snapshot in Metrics.snapshots:
            start, end = snapshot['time_last'], snapshot['time']

            for node in final_sim.nodes:
                blocks = []

                for b in node.blockchain:
                    if b.time_added >= end:
                        break
                    if b.time_added >= start:
                        blocks.append(b)

    @staticmethod
    def save_snapshots(name="snapsot"):
        with open(f"results/{name}.json", "w") as f:
            json.dump(Metrics.snapshots, f, indent=2)
