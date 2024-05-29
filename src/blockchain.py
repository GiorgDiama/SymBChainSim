from datetime import datetime
from Chain.Parameters import Parameters
from Chain.Manager.Manager import Manager
from Chain.Metrics import Metrics
import Chain.tools as tools

import random
import numpy
import sys
import statistics as st
import json

############### SEEDS ############
seed = 5
random.seed(seed)
numpy.random.seed(seed)
############## SEEDS ############

def save_blockchain(sim):
    blockchains = {}
    for node in sim.nodes:
        blockchains[node.id] = []
        for block in node.blockchain[1:]:
            blockchains[node.id].append({
                'size': block.size,
                'timestamp': block.time_added,
                'tx': [(x.id, x.timestamp) for x in block.transactions]
            })

    with open("output/blockchain.json",'w') as f:
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
            print(n, total_blocks, CP_blocks)
    else:
        for n in manager.sim.nodes:
            bc = n.blockchain[1:]
            blocks = ''
            for cur, next in zip(bc[:-1], bc[1:]):
                blocks += cur.consensus.NAME + ' '
                if cur.consensus != next.consensus:
                    blocks += 'SW'

            blocks_by_cp = blocks.split('SW')

            print(n, '->'.join([f"{x.split(' ')[0]}:{len(x.split(' '))}"
                                for x in blocks_by_cp]), f'| TOTAL: {len(bc)}')


def run():
    manager = Manager()
    manager.load_params()
    manager.set_up()
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

    save_blockchain(manager.sim)

    print(tools.color(f"SIMULATED TIME {'%.2f'%manager.sim.clock}", 45))
    print(tools.color(f"EXECUTION TIME: {runtime}", 45))

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
        f"SIMULATED TIME {'%.2f'%manager.sim.clock}", 45))
    print(tools.color(f"EXECUTION TIME: {runtime}", 45))


if __name__ == "__main__":
    if '--sc' in sys.argv:
        scenario = sys.argv[sys.argv.index('--sc') + 1]
        run_scenario(f"Scenarios/{scenario}.json")
    else:
        run()
