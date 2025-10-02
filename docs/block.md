## Block model overview

The Block class is a lightweight container for data blocks in SBS. It holds basic metadata, a list of transactions, and optional fields used by higher layers (e.g., consensus name, extra metadata). The model is intentionally simple and avoids protocol-specific logic.

### Key fields
- `depth` (int): Height of the block in the local chain (genesis at 0)
- `id` (int): Unique block identifier
- `previous` (int): ID of the parent block
- `time_created` (float): Creation time
- `time_added` (float): Time the block is appended to the local chain
- `miner` (int): ID of the block proposer/creator
- `transactions` (list): Included transactions
- `size` (float): Serialized size used by the network layer
- `consensus` (str|None): Consensus protocol label for provenance
- `extra_data` (dict): Free-form metadata (e.g., `round`, `configuration_depth`)

### Constructors and helpers
- `copy()`: Returns a deep copy of the block, including `extra_data` and `time_added`.
- `genesis_block()`: Creates the genesis block at depth 0 with a random ID and sets `extra_data["round"] = -1` so nodes starting at round 0 initialise correctly.

### String forms
- `__str__`: Human-readable summary with id, depth, proposer, times, size, parent, and consensus name
- `__repr__`: Compact representation `~block: {id}~`

In summary, `Block` provides a clear, minimal data structure for chain operations and network sizing.

