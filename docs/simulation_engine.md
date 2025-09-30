# Simulation Engine (DES core)

SymBChainSim uses a minimal Discrete Event Simulation (DES) engine to drive the blockchain models. The engine is intentionally simple and model-agnostic: it advances a virtual clock by processing timestamped events, and leaves protocol logic, networking behavior, and reconfiguration mechanics to the `Chain/` and `Manager/` modules.

## Core components

- `Engine.Event` (`src/Simulator/Engine/Event.py`): Lightweight container for a scheduled action with fields such as `time`, `type`, `payload`, and a `handler` reference.
- `Engine.EventQueue` (`src/Simulator/Engine/EventQueue.py`): Min-heap priority queue ordered by event time; supports push/pop and basic stats.
- `Engine.Scheduler` (`src/Simulator/Engine/Scheduler.py`): Convenience layer for creating and scheduling future events from within models.
- `Engine.Handler` (`src/Simulator/Engine/Handler.py`): Dispatches events to the appropriate model logic (nodes, network, manager, etc.).
- `Engine.Simulation` (`src/Simulator/Engine/Simulation.py`): Owns the main loop, event queue, and simulation clock.

## At a glance

2. The queue pops the earliest event; the simulation clock jumps to that event's `time`.
3. `Handler` executes the event, allowing models to mutate state and schedule new future events.
4. Repeat until termination conditions (simulation time limit, block limit, etc...).

## What lives outside the engine
- Everything that is not directly relevant to the DES aspect of the simulation.

## Extending the simulation
- Add a new event type by defining its handling in `Handler` and scheduling it from your model.
- Keep events small: pass identifiers in `payload` and fetch heavy state from the owning model when executing.
- Prefer a few coarse-grained events (e.g., high-level sync completions) over simulating every micro-step when appropriate.

In short, the engine provides the DES backbone; the blockchain-specific behavior is largely modeled in the surrounding components. Try to keep as much of the blockchain logic as possible outside of `Engine/`.