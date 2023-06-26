import pickle
import statistics as st
from Chain.Parameters import Parameters

import matplotlib.pyplot as plt
import numpy as np
class SimulationState:
    '''
        Stores the state of the simulation.
    '''
    blockchain_state = {}
    events = {"consensus":{}, "other": {}}

    @staticmethod
    def store_state(sim):
        '''
            store_state can be called given a simulator object.
            store_state serializes and stores the simulator state
        ''' 
        for n in sim.nodes:
            SimulationState.blockchain_state[n.id] = n.to_serializable()
    
    @staticmethod
    def load_state(sim):
        pass

    @staticmethod
    def store_event(event):
        if 'block' in event.payload.keys():
            block_id = event.payload['block'].id
            if block_id in SimulationState.events["consensus"].keys():
                SimulationState.events["consensus"][block_id].append(event.to_serializable())
            else:
                SimulationState.events["consensus"][block_id] = [event.to_serializable()] 
        else:
            type = event.payload['type']
            if type in SimulationState.events["other"].keys():
                SimulationState.events[type].append(event.to_serializable())
            else:
                SimulationState.events[type] = [event.to_serializable()]
            

class Metrics:
    latency = {}
    throughput = {}
    blocktime = {}

    decentralisation = {}
    
    @staticmethod
    def measure_latency(bc_state):
        for node_id, node_state in bc_state.items():
            Metrics.latency[node_id] = {"values": {}}
            for b in node_state["blockchain"]:
                Metrics.latency[node_id]["values"][b["id"]] = st.mean(
                    [b["time_added"] - t.timestamp for t in b["transactions"]]
                )
            
            Metrics.latency[node_id]["AVG"] = st.mean(
                [b_lat for _, b_lat in Metrics.latency[node_id]["values"].items()]
            )
    
    @staticmethod
    def measure_throughput(bc_state):
        for node_id, node_state in bc_state.items():
            sum_tx = sum([len(x["transactions"]) for x in node_state["blockchain"]])
            Metrics.throughput[node_id] = sum_tx/Parameters.simulation["simTime"]


    @staticmethod
    def measure_interblock_time(bc_state):
        for node_id, node_state in bc_state.items():
            # for each pair of blocks create the key valie pair "curr -> next": next.time_added - curre.time_added
            diffs = { f"{curr['id']} -> {next['id']}" : next["time_added"] - curr["time_added"] 
                     for curr, next in zip(node_state["blockchain"][:-1], node_state["blockchain"][1:]) }
            
            Metrics.blocktime[node_id] = {"values": diffs, "AVG": st.mean(diffs.values())}
    
    @staticmethod
    def gini_coeficient(cumulative_dist):
        lorenz_curve = [(x+1)/len(cumulative_dist) for x in range(len(cumulative_dist))]
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
    def measure_decentralisation_nodes(bc_state):
        '''
            TODO: 
                Consider how nodes leaving and exiting the consensus can be taken into account
            NOTE: 
                This method assumes all nodes are accounted for in the final system state 
                and no later added nodes produced blocks and left

                !IF NODES THAT HAVE PRODUCED BLOCKS ARE NOT IN THE GIVEN SYSTEM STATE THIS BREAKS!

                if an extra node joins later this skews the decentralisaion since
                the node did not have equal proposing chances as the other nodes

                NOTE: possible solution:
                    Note when nodes enter and left (might be (probably is) hard to know when a node leaves)
                    calculating decentralisaion seperatatly for each interval where nodes are "stable"
                    average the decentralisations out
        '''        
        nodes = [int(x) for x in bc_state.keys()]
        Metrics.decentralisation['node'] = {}
        for node_id, node_state in bc_state.items():
            block_distribution = {x:0 for x in nodes}
            total_blocks = len(node_state["blockchain"])

            for b in node_state["blockchain"]:
                block_distribution[b["miner"]] += 1

            dist = sorted([(key, value) for key, value in block_distribution.items()], key=lambda x:x[1])
            dist = [(x[0], x[1]/total_blocks) for x in dist]        
            cumulative_dist = [sum([x[1] for x in dist[:i+1]]) for i in range(len(dist))]
                
            gini = Metrics.gini_coeficient(cumulative_dist)

            Metrics.decentralisation['node'][node_id] = gini
    
    @staticmethod
    def measure_decentralisation_location(bc_state):
        '''
            TODO: 
                Consider how nodes leaving and exiting the consensus can be taken into account
            NOTE: 
                This method assumes all nodes are accounted for in the final system state 
                and no later added nodes produced blocks and left

                !IF NODES THAT HAVE PRODUCED BLOCKS ARE NOT IN THE GIVEN SYSTEM STATE THIS BREAKS!

                if an extra node joins later this skews the decentralisaion since
                the node did not have equal proposing chances as the other nodes

                NOTE: possible solution:
                    Note when nodes enter and left (might be (probably is) hard to know when a node leaves)
                    calculating decentralisaion seperatatly for each interval where nodes are "stable"
                    average the decentralisations out
        '''        
        location_map = {x: bc_state[x]["location"] for x in bc_state.keys()}
        Metrics.decentralisation['loc'] = {}
        for node_id, node_state in bc_state.items():
            block_distribution = {x : 0 for x in location_map.values()}
            total_blocks = len(node_state["blockchain"])

            for b in node_state["blockchain"]:
                block_distribution[location_map[b["miner"]]] += 1

            dist = sorted([(key, value) for key, value in block_distribution.items()], key=lambda x:x[1])
            dist = [(x[0], x[1]/total_blocks) for x in dist]        
            cumulative_dist = [sum([x[1] for x in dist[:i+1]]) for i in range(len(dist))]

            gini = Metrics.gini_coeficient(cumulative_dist)

            Metrics.decentralisation['loc'][node_id] = gini


#######################################################################################################################################
#######################################################################################################################################
#######################################################################################################################################


def blockchains_to_json(sim):
    blockchains_dict = {}

    for n in sim.nodes:
        blockchain = []

        for b in n.blockchain[1:]:
            blockchain.append(b.to_serializable())
        blockchains_dict[n.id] = blockchain

    return blockchains_dict

def calculate_pairs_switch_overhead(blockchains_dict):
    gen_mean, trans_mean = [], []
    for id, bc in blockchains_dict.items():
        try:
            g, t = idle_time_method(bc)
            gen_mean.append(g)
            trans_mean.append(t)
        except Exception as e:
            pass
    
    return st.mean(gen_mean), st.mean(trans_mean)

def triplet_method(bc):
    def get_trainsition_blocks(bc):
        triplets = []
        for idx, block in enumerate(bc[:-1]):
            if block["consensus"] != bc[idx+1]["consensus"]:
                triplets.append((bc[idx-1], bc[idx], bc[idx+1]))
        return triplets
    
    def get_triplets_every(bc):
        triplets = []
        for idx, block in enumerate(bc[1:-1]):
            triplets.append((bc[idx-1], bc[idx], bc[idx+1]))
        return triplets

    def calc_dt_triplets(triplet):
        last_old, first_new, sec_new = triplet[0], triplet[1], triplet[2]
        time_with_switch = first_new["time_added"] - last_old["time_added"]
        time_right_after_switch = sec_new["time_added"] - last_old["time_added"]
        return time_with_switch - time_right_after_switch
    

    triplets_gen = get_triplets_every(bc)
    meam_dt = st.mean([calc_dt_triplets(x) for x in triplets_gen])
    triplets_trans = get_trainsition_blocks(bc)

    for triplet in triplets_trans:
        print(triplet[0]["depth"], triplet[1]["depth"],triplet[2]["depth"], end=" -> ")
        print(calc_dt_triplets(triplet), meam_dt)

def avg_round_between_blocks(bc):
    means = []
    for id, b in bc.items():
        round_diff = []
        for idx, block in enumerate(b[:-1]):
            round_diff.append(b[idx+1]["round"] - b[idx]["round"])
        means.append(st.mean(round_diff))
    return means

def idle_time_method(bc):
    def get_trainsition_pairs(bc):
        pairs = []
        for idx, block in enumerate(bc[:-1]):
            if block["consensus"] != bc[idx+1]["consensus"]:
                pairs.append((bc[idx], bc[idx+1]))
        return pairs

    def get_every_pair(bc):
        return [(x,y) for x,y in zip(bc[:-1], bc[1:])]
    
    def calc_idle_time(pair):
        return pair[1]["time_created"] - pair[0]["time_added"]
    
    gen_pairs = get_every_pair(bc)
    mean_idle = st.mean([calc_idle_time(x) for x in gen_pairs])

    pairs_tran = get_trainsition_pairs(bc)

    mean_tran = st.mean([calc_idle_time(x) for x in pairs_tran])
    # for pair in pairs_tran:
    #     print(pair[0]["depth"], pair[1]["depth"], end=" -> ")
    #     print(calc_idle_time(pair), mean_idle)
    
    return mean_idle, mean_tran

def  l(bc):
    def get_num_block(blocks):
        return len(blocks)

    def get_b_times(blocks):
        b_time = [b["time_added"] - b["time_created"] for b in blocks]
        return st.mean(b_time)
    
    def get_inter_block_time(blocks):
        ib_times = [blocks[0]["time_added"]]
        b0 = blocks[0:-1]
        b1 = blocks[1:]
        
        for cur, nxt in zip(b0, b1):
            ib_times.append(nxt["time_added"] - cur["time_added"])

        return st.mean(ib_times)

    def get_idle_time(blocks):
        idle_time = []
        b0 = blocks[0:-1]
        b1 = blocks[1:]
        
        for cur, nxt in zip(b0, b1):
            idle_time.append(nxt["time_created"] - cur["time_added"])

        return st.mean(idle_time)

    PBFT_blocks = [b for b in bc if b["consensus"] == "PBFT"]
    BigFoot_blocks = [b for b in bc if b["consensus"] == "BigFoot"]
    
    # print("-"*10, "block times", "-"*10)
    # print(get_b_times(PBFT_blocks))
    # print(get_b_times(BigFoot_blocks))
    # print("-"*10, "inter block times", "-"*10)
    # print(get_inter_block_time(PBFT_blocks))
    # print(get_inter_block_time(BigFoot_blocks))
    # print("-"*10, "idle time", "-"*10)
    # print(get_idle_time(PBFT_blocks))
    # print(get_idle_time(BigFoot_blocks))



