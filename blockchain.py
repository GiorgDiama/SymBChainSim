from Chain.Simulation import Simulation
import Chain.tools as tools
from Chain.Parameters import Parameters

from datetime import datetime

from Chain.Manager import Manager

import random, numpy

import cProfile

import statistics

import Chain.Consensus.BigFoot.BigFoot as BigFoot
import Chain.Consensus.PBFT.PBFT as PBFT

############### SEEDS ############
seed = 5
random.seed(seed)
numpy.random.seed(seed)
############### SEEDS ############

def test_many():
    for seed in range(1,50):
        print(seed)
        random.seed(seed)
        numpy.random.seed(seed)

        manager = Manager()

        t = datetime.now()
        manager.set_up()
        manager.run()
        
        for n in manager.sim.nodes:
            print(n, '| Total_blocks:', n.blockchain_length(),
                '| pbft:',len([x for x in n.blockchain if x.consensus == PBFT]),
                '| bf:',len([x for x in n.blockchain if x.consensus == BigFoot]),
                )
  
        time = (datetime.now() - t)
        print(f"runtime: {time} ({round(time.total_seconds() * 1000,1)}ms)")

def test_one():
    manager = Manager()

    t = datetime.now()
    manager.set_up()
    manager.run()
    for n in manager.sim.nodes:
        print(n, '| Total_blocks:', n.blockchain_length(),
            '| pbft:',len([x for x in n.blockchain if x.consensus == PBFT]),
            '| bf:',len([x for x in n.blockchain if x.consensus == BigFoot]),
            )
    print(Parameters.simulation['events'])
    total_tx = 0
    for b in manager.sim.nodes[0].blockchain:
        total_tx += len(b.transactions)
    print("total tx:", total_tx)
    time = (datetime.now() - t)
    print(f"runtime: {time} ({round(time.total_seconds(),1)})")

test_one()
