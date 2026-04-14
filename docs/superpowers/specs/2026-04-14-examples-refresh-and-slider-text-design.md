# Examples Refresh And Slider Text Design

## Summary

Refresh the `examples` directory so it is much smaller, easier to use, and better at showing the rendering engine. At the same time, fix the current 2D slider regression where text becomes excessively large.

The new examples experience stays centered on `examples/run_demo.py`. Instead of many fixed scripts per framework and scenario, each framework exposes a compact set of parameterized demos:

- one `random` demo per framework
- one `qaoa` demo only for frameworks that already support it today: Qiskit, Cirq, and PennyLane

The new CLI must let the user choose qubit count, column count, pages vs slider, 2D vs 3D, and 3D topology. In 2D, `topology` is accepted but has no effect.

## Goals

- Fix the slider text regression so slider demos are readable again.
- Reduce the number of example files substantially.
- Make examples configurable enough that one demo can show multiple rendering situations.
- Keep the examples approachable from `run_demo.py` rather than asking the user to discover many standalone scripts.
- Update the examples README so the command list highlights the most useful showcase combinations instead of enumerating every legacy demo.

## Non-Goals

- Do not redesign the public drawing API.
- Do not add QAOA examples for MyQLM or CUDA-Q.
- Do not preserve the current one-file-per-scenario catalog layout.

## Target Example Structure

Keep `examples/run_demo.py` as the main entrypoint and reduce framework scripts to:

- `examples/qiskit_random.py`
- `examples/qiskit_qaoa.py`
- `examples/cirq_random.py`
- `examples/cirq_qaoa.py`
- `examples/pennylane_random.py`
- `examples/pennylane_qaoa.py`
- `examples/myqlm_random.py`
- `examples/cudaq_random.py`

Shared helpers should continue living in `_shared.py`, but they should be expanded so the framework-specific files stay thin and only contain builder logic.

## Demo Behavior

### Random demos

Each random demo builds a reproducible circuit from:

- `qubits`
- `columns`
- `seed`

Default seed is fixed so repeated runs generate the same circuit unless the user overrides it.

The random circuit should visibly exercise the renderer instead of feeling arbitrary. It should include:

- a balanced mix of 1-qubit and 2-qubit operations
- a small amount of parameterized gates
- measurements near the end
- enough structure to look good in both 2D and 3D

The exact random recipe does not need to match across frameworks gate-for-gate, but the visual intent should be consistent.

### QAOA demos

Each QAOA demo builds a scalable QAOA-style circuit from:

- `qubits`
- `columns`

For QAOA, `columns` means the number of QAOA layers `p`.

The QAOA builders should stay recognizable as QAOA circuits:

- initial mixer preparation
- repeated cost and mixer layers
- measurements at the end when the framework representation supports them in the current example style

## CLI Design

`examples/run_demo.py` should expose compact demo ids:

- `qiskit-random`
- `qiskit-qaoa`
- `cirq-random`
- `cirq-qaoa`
- `pennylane-random`
- `pennylane-qaoa`
- `myqlm-random`
- `cudaq-random`

Supported runtime options:

- `--demo`
- `--qubits`
- `--columns`
- `--mode pages|slider`
- `--view 2d|3d`
- `--topology line|grid|star|star_tree|honeycomb`
- `--seed`
- `--output`
- `--show` / `--no-show`
- `--list`

Behavior rules:

- In 2D, `topology` is ignored without error.
- `mode=slider` is only meaningful in 2D.
- If the user combines `--view 3d` with `--mode slider`, the runner should fail early with a clear message rather than relying on a lower-level traceback.
- QAOA demos accept `--columns` as QAOA depth.
- Random demos accept `--columns` as random circuit column count.

## Catalog And Runner Changes

`demo_catalog.py` should move from a long flat list of many fixed scenarios to a compact list of parameterized demos. Each catalog entry should describe:

- demo id
- description
- module name
- builder kind
- optional framework dependency
- whether QAOA is available
- sensible per-demo defaults for `qubits`, `columns`, `mode`, `view`, `topology`, and `seed`

`run_demo.py` should:

- parse the new CLI arguments
- load the builder from the compact catalog
- pass the chosen runtime options through to the builder and renderer
- keep `--list` as the source of truth for available demos

## README Refresh

`examples/README.md` should stop listing every old fixed demo. Instead it should explain the new parameterized model and include command blocks grouped by framework and scenario.

The command list must include, for each framework and for both `pages` and `slider` where relevant:

- many qubits, few columns
- few qubits, many columns
- many qubits, many columns
- QAOA slider with many columns for frameworks that support QAOA

The README should also include 3D commands using the same random/QAOA demos with `--view 3d` and sample topologies, so users can see that the same examples work in both views.

## Slider Regression Fix

The current zoom-responsive text scaling must not make slider-mode text enormous.

Desired behavior:

- slider mode remains readable and stable while scrolling
- text may still respond appropriately to 2D zoom interactions, but ordinary slider movement must not be treated like a zoom event
- the fix should preserve the recent 2D zoom-rescaling behavior for non-slider views, unless the implementation shows that a narrower scope is needed for correctness

## Testing And Acceptance

Add or update tests for:

- slider text stays within a readable size range in page-slider mode
- random demos can be built and rendered through the runner with the new CLI options
- QAOA demos can be built and rendered through the runner where supported
- invalid combinations such as `--view 3d --mode slider` fail with a clear message
- `topology` is accepted in 2D without changing 2D execution
- README/catalog expectations match the new compact demo ids

Acceptance is:

- the slider text regression is gone
- examples directory is materially smaller and easier to scan
- `run_demo.py` is the primary user path
- the README commands showcase the engine clearly without a huge repetitive list
