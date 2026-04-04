# Third-party software (declared dependencies)

Este documento reconoce el software de terceros **declarado explícitamente** en `pyproject.toml` como dependencia de construcción, de ejecución o extra opcional. **No** sustituye la lectura de las licencias publicadas por cada proyecto upstream ni cumple por sí solo todas las obligaciones legales que puedan aplicarte al redistribuir o combinar software; si necesitas cumplimiento formal (producto comercial, redistribución empaquetada, etc.), consulta con un abogado.

La licencia de **este** repositorio está en `LICENSE` (MIT).

## Dependencias de ejecución (`[project] dependencies`)

| Paquete (PyPI) | Licencia (metadatos / uso habitual del proyecto) | Dónde ver el texto legal |
|----------------|--------------------------------------------------|---------------------------|
| `matplotlib` | Python Software Foundation License | [matplotlib/LICENSE](https://github.com/matplotlib/matplotlib/tree/main/LICENSE) |
| `numpy` | BSD-3-Clause (el proyecto NumPy documenta también otras condiciones en su `LICENSE`; revísalo en la versión que instales) | [numpy/LICENSE.txt](https://github.com/numpy/numpy/blob/main/LICENSE.txt) |

## Extras opcionales (`[project.optional-dependencies]`)

Solo aplican si instalas el paquete con el extra correspondiente (por ejemplo `pip install quantum-circuit-drawer[qiskit]`).

| Extra | Paquete (PyPI) | Licencia (metadatos / uso habitual) | Dónde ver el texto legal |
|-------|----------------|--------------------------------------|---------------------------|
| `qiskit` | `qiskit` | Apache-2.0 | [Qiskit LICENSE](https://github.com/Qiskit/qiskit/blob/main/LICENSE.txt) |
| `cirq` | `cirq-core` | Apache-2.0 | [Cirq LICENSE](https://github.com/quantumlib/Cirq/blob/main/LICENSE) |
| `pennylane` | `pennylane` | Apache-2.0 | [PennyLane LICENSE](https://github.com/PennyLaneAI/pennylane/blob/master/LICENSE) |
| `cudaq` | `cudaq` | Apache-2.0 (según metadatos del paquete en PyPI; confirma en la versión instalada) | Documentación y fuentes del proyecto [NVIDIA/cuda-quantum](https://github.com/NVIDIA/cuda-quantum) |

## Herramientas de desarrollo y publicación (`dev`)

Usadas al contribuir o al ejecutar CI; no son dependencias del wheel publicado para usuarios finales que solo hacen `pip install quantum-circuit-drawer`.

| Paquete (PyPI) | Licencia (metadatos / uso habitual) |
|----------------|-------------------------------------|
| `pytest` | MIT |
| `pytest-cov` | MIT |
| `ruff` | MIT |
| `mypy` | MIT |
| `build` | MIT |
| `twine` | Apache-2.0 |

## Cadena de construcción (`[build-system] requires`)

Necesaria para construir el paquete a partir del código fuente (sdist/wheel), no para usar la librería ya instalada.

| Paquete (PyPI) | Licencia (metadatos / uso habitual) |
|----------------|-------------------------------------|
| `setuptools` | MIT |
| `wheel` | MIT |

---

Al instalar con `pip`, se pueden resolver **dependencias transitivas** adicionales (paquetes que traen `matplotlib`, `qiskit`, etc.). Esas no están listadas aquí porque **no** están declaradas en nuestro `pyproject.toml`. Para un inventario completo del entorno, usa las herramientas que prefieras (`pip-licenses`, exportación de SBOM, etc.) sobre el entorno concreto que vayas a distribuir o auditar.
