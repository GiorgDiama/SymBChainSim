from Parameters import Parameters

from Utils.Metrics import Metrics
from Utils import Tools

import statistics as st

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Engine.Simulation import Simulation

""" Everything the simulator prints to the terminal at the start and end of a run """

# parameters used internally by the simulator (not set in the configs)
INTERNAL_PARAMETERS = {"events", "event_id", "print_next", "CP", "txIDS"}


def title(text: str) -> str:
    return Tools.color(f" {text} ", 44)


def number(value: float) -> str:
    return f"{round(value):,}"


def mean(values: list[float]) -> float | None:
    """Mean of the values, ignoring -1 (used by metrics that could not be measured e.g., latency with no blocks)"""
    values = [v for v in values if v != -1]
    return st.mean(values) if values else None


def stop_condition() -> str:
    conditions = []
    if Parameters.simulation["sim_time"] != -1:
        conditions.append(f"{Parameters.simulation['sim_time']} s")
    if Parameters.simulation["stop_after_blocks"] != -1:
        conditions.append(f"{Parameters.simulation['stop_after_blocks']} blocks")
    if Parameters.simulation["stop_after_tx"] != -1:
        conditions.append(f"{Parameters.simulation['stop_after_tx']} tx")
    return " or ".join(conditions)


def print_header(seed: int, scenario: str | None = None) -> None:
    parts = ["SymBChainSim"]
    if scenario:
        parts.append(f"scenario {scenario}")
    parts += [Parameters.simulation["init_CP"], f"{Parameters.application['num_nodes']} nodes", stop_condition(), f"seed {seed}"]
    print(" | ".join(parts) + "\n")


def print_setup(sim: "Simulation") -> None:
    """Prints the nodes and the loaded parameters (shown with --verbose)"""
    print(title("NODES"))
    print(f"  {'node':>4}  {'location':<14}{'bandwidth':<11}{'CP':<12}neighbours")
    for n in sim.nodes:
        cp = n.cp.NAME if n.cp is not None else "None"
        neighbours = ",".join(str(x.id) for x in n.neighbours)
        print(f"  {n.id:>4}  {n.location:<14}{str(n.bandwidth):<11}{cp:<12}{neighbours}")

    print("\n" + title("PARAMETERS"))
    groups = {
        "simulation": Parameters.simulation,
        "application": Parameters.application,
        "execution": Parameters.execution,
        "data": Parameters.data,
        "network": Parameters.network,
        "dynamic_sim": Parameters.dynamic_sim,
        "behaviour": Parameters.behaviour,
        "reconfiguration": Parameters.reconfiguration,
    }
    for name, params in groups.items():
        if not isinstance(params, dict) or not params:
            continue
        items = [f"{key}: {value}" for key, value in params.items() if key not in INTERNAL_PARAMETERS]
        print(f"  {name:<17}" + "\n".ljust(20).join(wrap_items(items, width=100)))
    print()


def wrap_items(items: list[str], width: int) -> list[str]:
    """Joins items into lines of at most `width` characters without splitting an item"""
    lines = [""]
    for item in items:
        if lines[-1] and len(lines[-1]) + len(item) + 2 > width:
            lines.append("")
        lines[-1] += ("  " if lines[-1] else "") + item
    return lines


def print_progress(sim: "Simulation") -> None:
    """Prints one line of progress e.g., [ 100 / 300 s]   41 blocks   16,361 tx"""
    clock = f"{sim.clock:5.0f}"
    if Parameters.simulation["sim_time"] != -1:
        clock += f" / {Parameters.simulation['sim_time']}"

    blocks = number(Metrics.confirmed_blocks(sim))
    if Parameters.simulation["stop_after_blocks"] != -1:
        blocks += f" / {Parameters.simulation['stop_after_blocks']:,}"

    tx = number(Metrics.processed_tx_system(sim))
    if Parameters.simulation["stop_after_tx"] != -1:
        tx += f" / {Parameters.simulation['stop_after_tx']:,}"

    print(f"[{clock} s]  {blocks:>5} blocks  {tx:>8} tx")


def blocks_per_cp(node) -> dict[str, int]:
    return {cp: len([b for b in node.blockchain[1:] if b.consensus == cp]) for cp in Parameters.CPs}


def print_summary(sim: "Simulation") -> None:
    """Prints the metrics averaged over all nodes (call Metrics.measure_all first)"""
    nodes = [n.id for n in sim.nodes]

    blocks = st.mean(n.blockchain_length() for n in sim.nodes)
    per_cp = {cp: st.mean(blocks_per_cp(n)[cp] for n in sim.nodes) for cp in Parameters.CPs}
    per_cp = ", ".join(f"{cp} {number(num)}" for cp, num in per_cp.items() if num > 0)

    confirmed = st.mean(Metrics.transaction_info[n]["processed_tx"] for n in nodes)
    pending = st.mean(Metrics.transaction_info[n]["pool"] for n in nodes)

    def fmt(value, unit, digits=2):
        return "n/a (no blocks)" if value is None else f"{value:.{digits}f} {unit}"

    rows = [
        ("Blocks", f"{number(blocks)}" + (f"  ({per_cp})" if per_cp else "")),
        ("Transactions", f"{number(confirmed)} confirmed, {number(pending)} pending"),
        ("Throughput", fmt(mean([Metrics.throughput[n] for n in nodes]), "tx/s", 1)),
        ("Mean latency", fmt(mean([Metrics.latency[n]["AVG"] for n in nodes]), "s")),
        ("Mean block time", fmt(mean([Metrics.blocktime[n]["AVG"] for n in nodes]), "s")),
        ("Mean block size", fmt(mean([Metrics.block_info[n]["AVG"] for n in nodes]), "MB")),
        ("Decentralisation (Gini)", fmt(mean([Metrics.decentralisation[n] for n in nodes]), "(0 = perfectly decentralised)")),
    ]

    print("\n" + title(f"RESULTS (mean over {len(nodes)} nodes)"))
    for name, value in rows:
        print(f"  {name:<25}{value}")
    print()


def print_per_node(sim: "Simulation") -> None:
    """Prints the metrics of each node (shown with --verbose)"""
    print(title("PER NODE"))
    header = ["node", "blocks", "synced", "mean latency", "throughput", "mean block time", "mean block size", "Gini", "mempool", "confirmed"]
    widths = [max(len(h), 6) + 2 for h in header]
    print("  " + "".join(f"{h:>{w}}" for h, w in zip(header, widths)))

    for n in sim.nodes:
        synced = len([b for b in n.blockchain[1:] if b.extra_data.get("synced", False)])
        row = [
            n.id,
            n.blockchain_length(),
            synced,
            f"{Metrics.latency[n.id]['AVG']:.2f}",
            f"{Metrics.throughput[n.id]:.1f}",
            f"{Metrics.blocktime[n.id]['AVG']:.2f}",
            f"{Metrics.block_info[n.id]['AVG']:.2f}",
            f"{Metrics.decentralisation[n.id]:.2f}",
            Metrics.transaction_info[n.id]["pool"],
            Metrics.transaction_info[n.id]["processed_tx"],
        ]
        print("  " + "".join(f"{str(v):>{w}}" for v, w in zip(row, widths)))
    print()


def print_events() -> None:
    """Prints how many events of each type were executed (shown with --verbose)"""
    print(title("EVENTS (total, then per node)"))
    for name, count in Parameters.simulation["events"].items():
        if isinstance(count, dict):
            per_node = " | ".join(f"{node}:{num}" for node, num in sorted(count.items()))
            print(f"  {name:<26}{sum(count.values()):>9,}   {per_node}")
        else:
            print(f"  {name:<26}{count:>9,}")
    print()
