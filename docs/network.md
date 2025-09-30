## Network module overview

The Network module models the blockchain peer-to-peer layer used by nodes to exchange messages and blocks. It focuses on simple, explainable mechanics that are sufficient for capturing propagation costs and their effects on consensus and sync.

### What it does
- Sends messages between nodes either to all nodes (broadcast) or only selected peers (gossip), depending on configuration.
- Assigns locations to nodes and uses a latency map or a distance-based formula to estimate one-way link delays.
- Models end-to-end propagation time as the sum of transmission, latency, queueing, and processing delays.
- Accounts for heterogeneous bandwidth by taking the minimum of sender and receiver bandwidths.
- Avoids redundant gossip by remembering which messages a node has already seen.

### Propagation modes
- **Broadcast**: Every message is delivered to all other nodes.
- **Gossip**: Each node forwards messages to a fixed number of randomly chosen neighbours. Nodes keep a per-message seen set to prevent re-forwarding the same message.

### Delay model (essentials)
Total propagation delay is:

- **Transmission delay**: message_size / effective_bandwidth
- **Latency**: one of the following, chosen by configuration
  - measured latencies from a dataset (location to location)
  - distance-derived latencies via a simple linear model (single-trip)
  - fixed local latency
  - disabled (zero)
- **Queueing + processing**: small constant overheads added to every message

The module estimates message size from the message payload and treats blocks specially by adding their serialized size and a base block overhead.

### Bandwidth and sampling
Effective bandwidth for a pair is the minimum of sender and receiver bandwidths. Bandwidth can be:
- sampled once per node at setup (or subsequent network state changes)
- sampled on every use (normal distribution around mean/dev)
- provided by a scenario (in which case setup sampling is skipped)

### Topology and locations
- Node locations are drawn from the latency/distance datasets and assigned randomly unless specified.
- In gossip mode, each node connects to a configurable number of neighbours chosen uniformly from the other nodes.

### Initialization flow
On startup the module:
1) loads latency and distance maps
2) assigns locations to nodes
3) sets node bandwidths based on the configured sampling mode
4) assigns neighbours if gossip is enabled

### Configuration knobs (from base.yaml)
- `network.gossip`: enable gossip; otherwise use broadcast
- `network.num_neighbours`: how many peers each node gossips to
- `network.use_latency`: `measured`, `distance`, `local`, or `off`
- `network.bandwidth.mean`, `network.bandwidth.dev`, `network.bandwidth.min`
- `network.bandwidth.sample`: `always`, `once`, or `scenario`
- `network.same_city_latency_ms`, `network.same_city_dev_ms`
- `network.queueing_delay`, `network.processing_delay`

### Practical notes
- When disabling gossip, `num_neighbours` still matters for sync/peer selection elsewhere but does not limit broadcast.
- Changing bandwidth or latency settings directly affects throughput and the time to finality observed by higher layers.
