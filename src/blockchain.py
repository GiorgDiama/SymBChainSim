from datetime import datetime
from Chain.Parameters import Parameters
from Chain.Manager.Manager import Manager
from Chain.Metrics import Metrics

from Chain.Utils import tools

import os
import sys
import json
import random
import numpy as np

############### SEEDS ############
seed = 5
random.seed(seed)
np.random.seed(seed)
############## SEEDS ############

def save_simulation_results(sim, name='results'):
    blockchains = {}
    for node in sim.nodes:
        blockchains[node.id] = []
        for block in node.blockchain[1:]:
            blockchains[node.id].append({
                'size': block.size,
                'timestamp': block.time_added,
                'tx': [(x.id, x.timestamp) for x in block.transactions]
            })

    with open(Parameters.path_to_src + '/' + f"output/{name}.json",'w') as f:
        json.dump(blockchains, f, indent=4)
    
def get_blocks_by_cp(manager, simple=True):
    if simple:
        for n in manager.sim.nodes:
            bc = n.blockchain[1:]
            total_blocks = len(bc)
            CP_blocks = {}
            for key in Parameters.CPs:
                CP_blocks[key] = len(
                    [x for x in bc if x.consensus.NAME == key])
            print(f'{f"node {n.id}":8}', 'TOTAL BLOCKS:', total_blocks, '--- BLOCKS PER CP:', CP_blocks)
        return
    
    for n in manager.sim.nodes:
        bc = n.blockchain[1:]
        blocks = ''
        for cur, next in zip(bc[:-1], bc[1:]):
            blocks += cur.consensus.NAME + ' '
            if cur.consensus != next.consensus:
                blocks += 'SW'

        blocks_by_cp = blocks.split('SW')

        print(n, '->'.join([f"{x.split(' ')[0]}:{len(x.split(' '))}"for x in blocks_by_cp]), f'| TOTAL: {len(bc)}')

def run():
    manager = Manager()

    if (conf := tools.get_named_cmd_arg('--conf')) == None:
        conf = 'base.yaml'

    manager.load_params(conf)
    manager.set_up()
    t = datetime.now()
    manager.run()
    runtime = datetime.now() - t

    for node in manager.sim.nodes:
        # node.pool = Parameters.tx_factory.removed_processed(node.pool)
        tx_idx = {}
        pool_set = set(node.pool)
        print(node, len(pool_set), len(node.pool))
        for block in node.blockchain:
            for tx in block.transactions:
                tx_idx[tx.id] = tx_idx.get(tx.id, 0)+1

        repetitions = {}
        for value in tx_idx.values():
            repetitions[value] = repetitions.get(value, 0) + 1
        print(node, repetitions)
        

    s = f"{'-'*30} BLOCKS {'-'*30}"
    print(tools.color(s, 42))
    get_blocks_by_cp(manager)
    Metrics.measure_all(manager.sim)
    Metrics.print_metrics()

    s = f"{'-'*30} EVENTS {'-'*30}"
    print(tools.color(s, 43))

    for key, value in Parameters.simulation['events'].items():
        if isinstance(value, dict):
            events_to_list = ((node, num) for node, num in value.items())
            events_to_list = sorted(events_to_list, key=lambda x:x[0])
            s = ' | '.join(f'{node}:{num:<5}' for node, num in events_to_list)
            print(f'{key:<18}: {sum([num for num in value.values()]):<5} --> {s}')
        else:
            print(f'{key:<18}: {value}')

    # save_blockchain(manager.sim)

    # for block in manager.sim.nodes[0].blockchain[1:]:
    #     print(st.mean([block.time_added - x.timestamp for x in block.transactions]))

    print(tools.color(
        f"SIMULATED TIME: {'%.2f'%manager.sim.clock} seconds", 45))
    print(tools.color(f"EXECUTION TIME: {runtime} seconds", 45))

def run_scenario(scenario):
    manager = Manager()
    manager.set_up_scenario(scenario)
    t = datetime.now()
    manager.run()
    runtime = datetime.now() - t

    get_blocks_by_cp(manager)
    Metrics.measure_all(manager.sim)
    Metrics.print_metrics()

    s = f"{'-'*30} EVENTS {'-'*30}"
    print(tools.color(s, 43))

    for key, value in Parameters.simulation['events'].items():
        if isinstance(value, dict):
            s = ' | '.join(f'{node}:{num}' for node, num in value.items())
            print(f'{key}: {s}')
        else:
            print(f'{key}: {value}')

    print(tools.color(
        f"SIMULATED TIME {'%.2f'%manager.sim.clock} seconds", 45))
    print(tools.color(f"EXECUTION TIME: {runtime} seconds", 45))


if __name__ == "__main__":
    os.environ['SBS_SRC'] = '.'
    if '--sc' in sys.argv:
        scenario = sys.argv[sys.argv.index('--sc') + 1]
        run_scenario(f"Scenarios/{scenario}.json")
    else:
        run()
