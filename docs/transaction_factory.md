## TransactionFactory overview

`TransactionFactory` is responsible for producing, propagating, selecting, and finalising transactions across nodes. It supports two mempool models (local and global) and uses the Network module to estimate propagation timing. A minimal `Transaction` data class captures the attributes required by selection and block assembly.

### Transaction model
- `creator` (int): ID of the node that created the transaction
- `id` (int): Unique transaction identifier
- `timestamp` (float): Creation (or arrival) time used for eligibility
- `size` (float): Transaction size (bytes); used in propagation and block size checks
- `processed` (bool): Set to True once included in a committed block

### Mempool models
- **Local pool (default)**: Each node keeps its own deque of transactions. Propagation copies the transaction (with delayed timestamp) into other nodes’ pools.
- **Global pool**: A single global deque is shared by all nodes to reduce simulation overhead. Propagation appends a single delayed copy into the global pool. Removal of processed transactions is coordinated using `depth_removed` so work is done once per depth.

The model is determined via `Parameters.application["transaction_model"]` with values `local` or `global`.

### Propagation
`transaction_prop(tx)` models network propagation delay using `Network.calculate_message_propagation_delay(...)`:
- Local model: For every other node, compute creator→node delay and push a timestamp-shifted copy into that node’s pool
- Global model: Approximate with a creator→creator delay and push one timestamp-shifted copy into the global pool

The delayed copy preserves `creator`, `id`, and `size`, and sets `timestamp = original_timestamp + propagation_delay`.

### Adding scenario-provided transactions
`add_scenario_transactions(txion_list)` ingests tuples `(creator, id, timestamp, size)` and forwards each through `transaction_prop`. 

Note: sizes provided are divided by `1e6` before use (treating the input as bytes and converting to MB for the network model).

### Interval-based generation
`generate_interval_txions(start)` produces transactions for the window `[start, start + TI_dur]`:
- For each second in the interval, create `Tn` transactions unless `stop_after_tx` is reached
- `id` comes from and updates `Parameters.application["txIDS"]`
- `timestamp = second`
- `size` is drawn from an exponential distribution with mean `Tsize`, then increased by `base_transaction_size`
- `creator` is uniformly sampled from the registered nodes
- Each transaction is sent to `transaction_prop` and `produced_tx` is incremented

### Execution (selection for blocks)
`execute_transactions(configuration, pool, time)` chooses the source pool based on the mempool model and delegates to `_get_transactions_from_pool(...)`:
- Greedy selection in timestamp order from the deque
- A transaction is eligible if `tx.timestamp <= time` and adding it does not exceed `configuration.block_size`
- Stops when the next tx is in the future or would exceed the block size
- Returns `(transactions, total_size)`; if none are eligible, returns `([], -1)`

### Finalisation and cleanup
- `mark_transactions_as_processed(block, pool)` sets `processed=True` on included transactions
  - Local: marks in the local pool
  - Global: marks in the global pool once per `block.depth` (controlled by `depth_removed`)
- `removed_processed(pool)` returns a new deque without processed transactions (utility)
- `_mark_pool(txions, pool)` marks matching IDs in-place

### Class state
- `nodes`: List of registered nodes (used for propagation and creator lookup)
- `produced_tx`: Counter of generated transactions
- `global_mempool`: Deque used in global model
- `depth_removed`: Last depth finalised in the global model

### Configuration Parameters
- `application.transaction_model`: `local` or `global`
- `application.Tn`: transactions per second
- `application.TI_dur`: interval duration for generation
- `application.Tsize`: mean for exponential tx size
- `application.base_transaction_size`: minimum/offset size
- `application.txIDS`: running counter for tx IDs
- `simulation.stop_after_tx`: optional cap on total generated

