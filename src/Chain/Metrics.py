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
        return min([n.blockchain_length() for n in sim.nodes if n.state.alive])

    @staticmethod
    def measure_all(sim, start_from=1):
        for node in sim.nodes:
            BC = node.blockchain[start_from:]
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
        per_block = []
        for b in blocks:
            per_block.append(st.mean(
                [b.time_added - t.timestamp for t in b.transactions])
            )
        return per_block, st.mean(per_block)

    @staticmethod
    def measure_throughput(blocks):
        time = blocks[-1].time_added - blocks[0].time_created
        sum_tx = sum([len(b.transactions) for b in blocks])
        return sum_tx / time

    @staticmethod
    def measure_interblock_time(blocks):
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
                for t in Parameters.tx_factory.global_mempool
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
