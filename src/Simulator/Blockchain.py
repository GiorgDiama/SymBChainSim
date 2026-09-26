from Manager.Manager import Manager
import Manager.ScenariosAndWorkloads as Scenario

from Utils.Metrics import Metrics
from Utils import Tools

import argparse
import random
import sys
import yaml
import numpy as np
from datetime import datetime

DEFAULT_SEED = 1837413


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a SymBChainSim simulation.",
        epilog="examples:\n"
        "  uv run Blockchain.py\n"
        "  uv run Blockchain.py --cp Tendermint --name tendermint\n"
        "  uv run Blockchain.py --scenario light_scenario\n"
        "  uv run Blockchain.py --set application.Nn=8 --set network.num_neighbours=4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )

    parser.add_argument("--config", help="config file in src/Configs (default: base.yaml, or scenario.yaml with --scenario)")
    parser.add_argument("--scenario", help="run the named scenario from src/Resources/Scenarios")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"random seed (default: {DEFAULT_SEED})")
    parser.add_argument("--name", help="snapshots are saved to src/Outputs/Snapshots/<name>.json (default: snapshot)")
    parser.add_argument("--cp", choices=["PBFT", "Tendermint", "BigFoot"], help="consensus protocol to start with")
    parser.add_argument(
        "--reconfig", action=argparse.BooleanOptionalAction, help="enable/disable random reconfiguration (not available with --scenario)"
    )
    parser.add_argument("--debug", action=argparse.BooleanOptionalAction, help="enable/disable step-by-step debugging mode")
    parser.add_argument("--debug-at", type=float, metavar="TIME", help="switch to debugging mode at this simulation time")
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="GROUP.NAME=VALUE",
        help="override any config value, e.g. --set network.num_neighbours=4 (can be repeated)",
    )

    args = parser.parse_args()

    if args.scenario and args.reconfig is not None:
        parser.error("--reconfig/--no-reconfig are not available with --scenario")

    for item in args.set:
        if "=" not in item:
            parser.error(f"--set expects GROUP.NAME=VALUE, got '{item}'")

    return args


def get_overrides(args: argparse.Namespace) -> dict:
    """Collects the parameter overrides requested on the command line as {"group.name": value}"""
    overrides = {}

    for item in args.set:
        key, value = item.split("=", 1)
        # parse values like YAML so numbers, booleans and lists get their proper type
        overrides[key.strip()] = yaml.safe_load(value)

    named = {
        "simulation.run_name": args.name,
        "simulation.init_CP": args.cp,
        "simulation.debugging_mode": args.debug,
        "simulation.start_debugging_at": args.debug_at,
        "reconfiguration.reconfigure": args.reconfig,
    }
    overrides.update({key: value for key, value in named.items() if value is not None})

    return overrides


def run(args: argparse.Namespace) -> None:
    random.seed(args.seed)
    np.random.seed(args.seed)

    manager = Manager()
    overrides = get_overrides(args)

    try:
        if args.scenario:
            Scenario.set_up_scenario(manager, args.scenario, config=args.config or "scenario.yaml", overrides=overrides)
        else:
            manager.load_params(args.config or "base.yaml", overrides)
            manager.set_up()
    except ValueError as e:
        # invalid --set keys
        sys.exit(f"error: {e}")

    t = datetime.now()
    manager.run()
    runtime = datetime.now() - t

    print(Tools.color(f"{'-' * 30} BLOCKS {'-' * 30}", 42))
    Tools.get_blocks_by_cp(manager.sim)

    Metrics.measure_all(manager.sim)
    Metrics.print_metrics()

    print(Tools.color(f"{'-' * 30} EVENTS {'-' * 30}", 43))
    Tools.print_events()

    print(Tools.color(f"SIMULATED TIME: {manager.sim.clock:0.2f} seconds", 45))
    print(Tools.color(f"EXECUTION TIME: {runtime} seconds", 45))


if __name__ == "__main__":
    run(parse_args())
