import Chain.tools as tools
from Chain.Parameters import Parameters
from Chain.Network import Network

from datetime import datetime

from Chain.Manager import Manager

import random, numpy

import Chain.Consensus.BigFoot.BigFoot as BigFoot
import Chain.Consensus.PBFT.PBFT as PBFT

from Chain.Metrics import SimulationState, Metrics

############### SEEDS ############
seed = 5
random.seed(seed)
numpy.random.seed(seed)
############### SEEDS ############

def test_simulation():
    manager = Manager()

    t = datetime.now()
    manager.set_up()

    manager.run()

    for n in manager.sim.nodes:
        print(n, '| Total_blocks:', n.blockchain_length(),
            '| pbft:',len([x for x in n.blockchain if x.consensus == PBFT]),
            '| bf:',len([x for x in n.blockchain if x.consensus == BigFoot]),
            )

    # for b in manager.sim.nodes[0].blockchain:
    #     print(b.id)
    #     print(b.transactions)

    SimulationState.store_state(manager.sim)
    Metrics.measure_latency(SimulationState.blockchain_state)
    Metrics.measure_throughput(SimulationState.blockchain_state)
    Metrics.measure_interblock_time(SimulationState.blockchain_state)
    Metrics.measure_decentralisation_nodes(SimulationState.blockchain_state)
    Metrics.measure_decentralisation_location(SimulationState.blockchain_state)

    print(Metrics.decentralisation)

def test_metrics():
    manager = Manager()

    t = datetime.now()
    manager.set_up()
    manager.run()
    for n in manager.sim.nodes:
        print(n, '| Total_blocks:', n.blockchain_length(),
            '| pbft:',len([x for x in n.blockchain if x.consensus == PBFT]),
            '| bf:',len([x for x in n.blockchain if x.consensus == BigFoot]),
            )
    

test_simulation()
