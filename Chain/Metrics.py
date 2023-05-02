import json
import statistics as st

def blockchain_to_JSON(nodes):
    blockchains_dict = {}
    for n in nodes:
        blockchain = []
        for b in n.blockchain[1:]:
            blockchain.append({
                "depth": b.depth,
                "previous": b.previous,
                "time_created": b.time_created,
                "time_added": b.time_added,
                "miner": b.miner,
                "consensus": b.consensus.NAME,
                "size": b.size,
                "round": b.extra_data["round"]
            })
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



