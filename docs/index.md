# quantum-circuit-drawer documentation

This documentation is organized around what a user normally wants to do first: install the package, get one successful render, choose the right workflow, and only then go deeper into framework-specific details or extension points.

## Start Here

| If you need to... | Read this |
| --- | --- |
| Install the package in a local `.venv` | [Installation](installation.md) |
| Get the first circuit render working | [Getting started](getting-started.md) |
| Understand the normal day-to-day workflows | [User guide](user-guide.md) |
| See exact public types, fields, and return values | [API reference](api.md) |
| Check framework support and differences | [Frameworks](frameworks.md) |
| Draw OpenQASM 2/3 text or `.qasm` / `.qasm3` files | [Recipes](recipes.md#draw-openqasm-2-or-3-text-or-a-qasm-qasm3-file) and [Frameworks](frameworks.md#openqasm-2-and-3) |
| Copy-paste common tasks | [Recipes](recipes.md) |
| Diagnose a failure quickly | [Troubleshooting](troubleshooting.md) |
| Run or copy example scripts | [Examples](../examples/README.md) with `qiskit-2d-exploration-showcase` for managed 2D and `qiskit-3d-exploration-showcase` for managed 3D |
| Extend the library with adapters or layouts | [Extension API](extensions.md) |
| Contribute to the repository | [Development](development.md) |

## Reading Paths

### I am new to the library

1. [Installation](installation.md)
2. [Getting started](getting-started.md)
3. [Recipes](recipes.md)
4. [Examples](../examples/README.md)

### I already installed it and want to use it well

1. [User guide](user-guide.md)
2. [Frameworks](frameworks.md)
3. [API reference](api.md)

### I have OpenQASM 2 or 3 text or a `.qasm` / `.qasm3` file

1. Install the Qiskit or `qasm3` extra from [Installation](installation.md#install-optional-framework-extras)
2. Use [Getting started](getting-started.md#draw-openqasm-2-or-3-text-or-a-qasm-qasm3-file) for the smallest example
3. Copy the [OpenQASM recipe](recipes.md#draw-openqasm-2-or-3-text-or-a-qasm-qasm3-file)

### I want to explore wide circuits interactively

1. [User guide](user-guide.md#when-to-choose-each-draw-mode)
2. [Recipes](recipes.md#2d-slider-for-wide-circuits)
3. [Examples](../examples/README.md)
   Start with `qiskit-2d-exploration-showcase` for 2D or `qiskit-3d-exploration-showcase` for 3D

### I mainly care about histograms and result analysis

1. [Getting started](getting-started.md#plot-your-first-histogram)
2. [User guide](user-guide.md#histogram-workflows)
3. [API reference](api.md#histogram-apis)
4. [Examples](../examples/README.md#i-want-to-see-histogram-workflows)

### I want to compare outputs

1. [Getting started](getting-started.md#compare-two-circuits)
2. [User guide](user-guide.md#comparison-workflows)
3. [API reference](api.md#comparison-apis)

### I need to debug a problem

1. [Troubleshooting](troubleshooting.md)
2. [Frameworks](frameworks.md)
3. [API reference](api.md)

## Documentation Map

| Page | What it covers |
| --- | --- |
| [Installation](installation.md) | Python version, extras, Jupyter setup, editable installs, and platform notes |
| [Getting started](getting-started.md) | The quickest path to a first render, save, histogram, and comparison |
| [User guide](user-guide.md) | Practical advice for scripts, notebooks, 3D views, hover, presets, histograms, and compare workflows |
| [API reference](api.md) | The exact public functions, configs, enums, result objects, and extension-facing modules |
| [Frameworks](frameworks.md) | What changes across Qiskit, Cirq, PennyLane, MyQLM, CUDA-Q, and the internal IR |
| [Recipes](recipes.md) | Small copy-paste snippets for common tasks |
| [Troubleshooting](troubleshooting.md) | Fast diagnosis for install, backend, framework, and rendering issues |
| [Extension API](extensions.md) | The stable contract for adapters and custom layouts |
| [Development](development.md) | Local setup, tests, examples, packaging, and benchmark commands |
| [Benchmarking results](benchmarking-results.md) | A small dated benchmark report for context, not a public performance guarantee |

## Support Matrix

This is the release support contract repeated here so it stays easy to find.

| Input path | Support level | Platform notes |
| --- | --- | --- |
| Internal IR | Strong support | Core built-in path on Windows and Linux |
| Qiskit | Strong support | Primary external backend on Windows and Linux |
| OpenQASM 2 text and `.qasm` files | Strong support through the Qiskit extra | Install `quantum-circuit-drawer[qiskit]`; works on Windows and Linux |
| OpenQASM 3 text and `.qasm3` files | Strong support through Qiskit plus `qiskit-qasm3-import` | Install `quantum-circuit-drawer[qasm3]`; works on Windows and Linux when Qiskit's importer is available |
| Cirq | Best-effort on native Windows | Prefer Linux or WSL for the most reliable repeated runs |
| PennyLane | Best-effort on native Windows | Prefer Linux or WSL for the most reliable repeated runs |
| MyQLM | Scoped adapter + contract support | Adapter contract is covered, but it is not a first-class multiplatform CI backend |
| CUDA-Q | Linux/WSL2 only | Supports closed kernels plus scalar `cudaq_args`; not intended for native Windows installs |
