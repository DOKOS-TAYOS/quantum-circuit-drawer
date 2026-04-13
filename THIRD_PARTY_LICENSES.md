# Third-party software (declared dependencies)

This document lists third-party software declared directly in
`pyproject.toml` as build, runtime, or optional extra dependencies.

It is a practical inventory, not legal advice. If you need formal compliance
for a commercial or redistributed product, review the upstream license texts
and seek legal review if needed.

The license for this repository is in `LICENSE` (MIT).

## Runtime dependencies (`[project] dependencies`)

| Package (PyPI) | License | Primary source |
|----------------|---------|----------------|
| `matplotlib` | Python Software Foundation License | [PyPI metadata](https://pypi.org/project/matplotlib/) and [upstream license](https://github.com/matplotlib/matplotlib/tree/main/LICENSE) |
| `numpy` | PyPI currently publishes the license expression `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | [PyPI metadata](https://pypi.org/project/numpy/) and [upstream license](https://github.com/numpy/numpy/blob/main/LICENSE.txt) |

## Optional extras (`[project.optional-dependencies]`)

These only apply if you install the corresponding extra, for example
`pip install "quantum-circuit-drawer[qiskit]"`.

| Extra | Package (PyPI) | License | Primary source |
|-------|----------------|---------|----------------|
| `qiskit` | `qiskit` | Apache-2.0 | [PyPI metadata](https://pypi.org/project/qiskit/) and [upstream license](https://github.com/Qiskit/qiskit/blob/main/LICENSE.txt) |
| `cirq` | `cirq-core` | Apache-2.0 | [PyPI metadata](https://pypi.org/project/cirq-core/) and [upstream license](https://github.com/quantumlib/Cirq/blob/main/LICENSE) |
| `pennylane` | `pennylane` | Apache-2.0 | [PyPI metadata](https://pypi.org/project/pennylane/) and [upstream license](https://github.com/PennyLaneAI/pennylane/blob/master/LICENSE) |
| `cudaq` | `cudaq` | Apache-2.0. CUDA-Q also indicates that it uses the NVIDIA cuQuantum SDK under its own license. Review that separately if your release process redistributes or directly depends on that stack. | [PyPI metadata](https://pypi.org/project/cudaq/) and [upstream license](https://github.com/NVIDIA/cuda-quantum/blob/main/LICENSE) |

## Review required before release

| Extra | Package (PyPI) | Status | Primary source |
|-------|----------------|--------|----------------|
| `myqlm` | `myqlm` | Review required for the PyPI/GitHub release checklist. The official myQLM documentation describes a mixed model: proprietary runtime under an EULA and open-source components under Apache-2.0. Do not treat this extra as a standard permissive dependency until this is reviewed. | [myQLM license documentation](https://myqlm.github.io/01_getting_started/%3Amyqlm%3Alicense.html) |

## Development and publishing tools (`dev`)

These are used for local development, CI, and publishing. They are not runtime
dependencies of the wheel published for end users.

| Package (PyPI) | License |
|----------------|---------|
| `pytest` | MIT |
| `pytest-cov` | MIT |
| `ruff` | MIT |
| `mypy` | MIT |
| `build` | MIT |
| `twine` | Apache-2.0 |

## Build toolchain (`[build-system] requires`)

These are needed to build the project from source code, not to use the library
once it is installed.

| Package (PyPI) | License |
|----------------|---------|
| `setuptools` | MIT |
| `wheel` | MIT |

---

Installing with `pip` may pull in additional transitive dependencies. They are
not listed here because they are not declared directly in our
`pyproject.toml`. For a complete inventory of the environment, use whichever
tool you prefer (`pip-licenses`, SBOM export, etc.) against the exact
environment you plan to distribute or audit.
