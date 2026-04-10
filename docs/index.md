# quantum-circuit-drawer documentation

This folder contains the user documentation for `quantum-circuit-drawer`.

The library gives you one main entry point, `draw_quantum_circuit(...)`, to render supported quantum circuits with a consistent Matplotlib-based style. These docs are written for people who want to use the library in scripts, notebooks, reports, or small tools.

## Start here

- If you have not installed the package yet, read [Installation](installation.md).
- If you want your first working example, go to [Getting started](getting-started.md).
- If you want to understand the API and options in more depth, read the [User guide](user-guide.md).
- If you need framework-specific notes, check [Frameworks](frameworks.md).
- If you prefer copy-paste examples for common tasks, use [Recipes](recipes.md).

## Documentation map

### [Installation](installation.md)

Python requirements, virtual environment setup, package extras, and platform notes.

### [Getting started](getting-started.md)

The shortest path from installation to a rendered circuit.

### [User guide](user-guide.md)

How `draw_quantum_circuit(...)` behaves, what it returns, how styling works, and what the main options do, including wide-circuit sliders and the topology-aware 3D view.

### [Frameworks](frameworks.md)

How to use the library with Qiskit, Cirq, PennyLane, MyQLM, CUDA-Q, or the internal IR.

### [Recipes](recipes.md)

Task-oriented examples such as saving images, drawing on existing axes, changing themes, and handling wide circuits.

## What this library is good at

- Keeping one visual style across multiple quantum frameworks
- Working naturally with Matplotlib figures and axes
- Saving circuit diagrams for documentation, reports, or notebooks
- Exploring wide or topology-aware views without changing the core drawing call
- Offering a small typed public API instead of many framework-specific drawing calls

## What this library does not try to do

- Replace the full native visualization stack of every quantum framework
- Support multiple rendering backends today
- Cover every advanced classical-control or framework-specific visualization feature

## Suggested reading path

Most users will get the best experience with this order:

1. [Installation](installation.md)
2. [Getting started](getting-started.md)
3. [User guide](user-guide.md)
4. [Frameworks](frameworks.md) or [Recipes](recipes.md), depending on what you need next
