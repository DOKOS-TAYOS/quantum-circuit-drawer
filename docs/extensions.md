# Extension API

This guide covers the public extension points that third-party code can rely on today.

The v1 scope is intentionally small:

- custom framework adapters
- custom 2D layouts
- custom 3D layouts

It does not include:

- plugin auto-discovery
- renderer plugins
- private hooks under `quantum_circuit_drawer.drawing`, `managed`, `plots`, or private `_...` modules

## Start with the right extension point

Use `CircuitIR` directly when:

- your input is already close to the drawer's neutral model
- you only need a preprocessing step in your own project
- you do not need autodetection or `framework="..."`

Write an adapter when:

- you want `draw_quantum_circuit(...)` to accept your framework object directly
- you want explicit `DrawConfig(framework="...")` support
- you want autodetection for your own circuit type

Use a custom layout when:

- you already have `CircuitIR`
- you want a different 2D or 3D placement strategy
- you do not need a new input framework

## Public modules you can build against

These modules are part of the extension contract:

- `quantum_circuit_drawer.adapters`
- `quantum_circuit_drawer.typing`
- `quantum_circuit_drawer.ir`
- `quantum_circuit_drawer.layout`
- `quantum_circuit_drawer.layout.scene`
- `quantum_circuit_drawer.layout.scene_3d`
- `quantum_circuit_drawer.style`

These modules are still internal implementation details:

- `quantum_circuit_drawer.drawing`
- `quantum_circuit_drawer.managed`
- `quantum_circuit_drawer.plots`
- private modules and names that start with `_`

## Writing an adapter

Adapters are explicit classes derived from `BaseAdapter`.

Rules the public API guarantees today:

- register adapters explicitly in your startup code
- autodetection uses registration order
- duplicate `framework_name` values fail by default
- replacing an existing framework requires `replace=True`
- `to_ir(..., options)` must accept `Mapping[str, object] | None`
- unknown option keys should be ignored for forward compatibility
- the stable option keys guaranteed today are `composite_mode` and `explicit_matrices`

Minimal adapter:

```python
from collections.abc import Mapping

from quantum_circuit_drawer.adapters import BaseAdapter, register_adapter
from quantum_circuit_drawer.ir import CircuitIR, LayerIR, OperationIR, OperationKind, WireIR, WireKind


class DemoCircuit:
    def __init__(self, qubit_count: int) -> None:
        self.qubit_count = qubit_count


class DemoAdapter(BaseAdapter):
    framework_name = "demo"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        return isinstance(circuit, DemoCircuit)

    def to_ir(
        self,
        circuit: object,
        options: Mapping[str, object] | None = None,
    ) -> CircuitIR:
        demo_circuit = circuit
        assert isinstance(demo_circuit, DemoCircuit)
        del options
        return CircuitIR(
            quantum_wires=[
                WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
                for index in range(demo_circuit.qubit_count)
            ],
            layers=[
                LayerIR(
                    operations=[
                        OperationIR(
                            kind=OperationKind.GATE,
                            name="H",
                            target_wires=("q0",),
                        )
                    ]
                )
            ],
            name="demo_extension",
        )


register_adapter(DemoAdapter)
```

Explicit use:

```python
from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

draw_quantum_circuit(
    DemoCircuit(qubit_count=2),
    config=DrawConfig(framework="demo", show=False),
)
```

Replacing an existing framework name:

```python
from quantum_circuit_drawer.adapters import register_adapter

register_adapter(DemoAdapter, replace=True)
```

## Writing a custom layout

Custom layouts are not registered. Pass them directly through `DrawConfig(layout=...)`.

### 2D layout contract

Use `quantum_circuit_drawer.typing.LayoutEngineLike`.

- input: `CircuitIR` and validated `DrawStyle`
- output: `LayoutScene`

Minimal example that delegates to the built-in engine:

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit
from quantum_circuit_drawer.layout import LayoutEngine
from quantum_circuit_drawer.layout.scene import LayoutScene
from quantum_circuit_drawer.style import DrawStyle
from quantum_circuit_drawer.typing import LayoutEngineLike
from quantum_circuit_drawer.ir import CircuitIR


class DemoLayout2D(LayoutEngineLike):
    def compute(self, circuit: CircuitIR, style: DrawStyle) -> LayoutScene:
        return LayoutEngine().compute(circuit, style)


draw_quantum_circuit(
    circuit_ir,
    config=DrawConfig(layout=DemoLayout2D(), mode=DrawMode.FULL, show=False),
)
```

### 3D layout contract

Use `quantum_circuit_drawer.typing.LayoutEngine3DLike`.

- input: `CircuitIR`, validated `DrawStyle`, `topology_name`, `direct`, and `hover_enabled`
- output: `LayoutScene3D`

Minimal example that delegates to the built-in 3D engine:

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit
from quantum_circuit_drawer.ir import CircuitIR
from quantum_circuit_drawer.layout import LayoutEngine3D
from quantum_circuit_drawer.layout.scene_3d import LayoutScene3D
from quantum_circuit_drawer.style import DrawStyle
from quantum_circuit_drawer.topology import TopologyInput
from quantum_circuit_drawer.typing import LayoutEngine3DLike


class DemoLayout3D(LayoutEngine3DLike):
    def compute(
        self,
        circuit: CircuitIR,
        style: DrawStyle,
        *,
        topology_name: TopologyInput,
        direct: bool,
        hover_enabled: bool,
    ) -> LayoutScene3D:
        return LayoutEngine3D().compute(
            circuit,
            style,
            topology_name=topology_name,
            direct=direct,
            hover_enabled=hover_enabled,
        )


draw_quantum_circuit(
    circuit_ir,
    config=DrawConfig(
        layout=DemoLayout3D(),
        view="3d",
        mode=DrawMode.FULL,
        show=False,
    ),
)
```

## Practical defaults

- If you only need one new input type, start with one adapter and reuse the built-in layout engines.
- If your circuit source is already converted upstream, prefer `CircuitIR` over a full adapter.
- If you want to override a built-in framework adapter, use `replace=True` and keep the original `framework_name`.
