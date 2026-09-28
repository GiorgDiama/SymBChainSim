from Chain.Consensus.PBFT.PBFT_state import PBFT
from Chain.Consensus.BigFoot.BigFoot_state import BigFoot
from Chain.Consensus.Tendermint.TM_state import Tendermint

# every consensus protocol available in SBS, by name
PROTOCOLS = {
    PBFT.NAME: PBFT,
    BigFoot.NAME: BigFoot,
    Tendermint.NAME: Tendermint,
}
