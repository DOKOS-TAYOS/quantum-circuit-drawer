from __future__ import annotations

from types import SimpleNamespace

import pytest

from quantum_circuit_drawer import HardwareTopology


class _FakeCouplingMap:
    def __init__(
        self,
        edges: tuple[tuple[int, int], ...],
        *,
        physical_qubits: tuple[int, ...] | None = None,
    ) -> None:
        self._edges = edges
        self.physical_qubits = physical_qubits

    def get_edges(self) -> tuple[tuple[int, int], ...]:
        return self._edges


def test_hardware_topology_from_qiskit_backend_uses_backend_v2_coupling_map() -> None:
    backend = SimpleNamespace(
        coupling_map=_FakeCouplingMap(
            ((0, 1), (1, 0), (1, 2)),
            physical_qubits=(0, 1, 2, 3),
        ),
        name="fake_backend",
        num_qubits=4,
    )

    topology = HardwareTopology.from_qiskit_backend(backend)

    assert topology.name == "fake_backend"
    assert topology.node_ids == (0, 1, 2, 3)
    assert topology.edges == ((0, 1), (1, 2))


def test_hardware_topology_from_qiskit_backend_builds_from_target_coupling_map() -> None:
    calls: list[tuple[str | None, bool]] = []

    class _FakeTarget:
        def build_coupling_map(
            self,
            two_q_gate: str | None = None,
            *,
            filter_idle_qubits: bool = False,
        ) -> _FakeCouplingMap:
            calls.append((two_q_gate, filter_idle_qubits))
            return _FakeCouplingMap(((0, 2),), physical_qubits=(0, 2))

    backend = SimpleNamespace(
        target=_FakeTarget(),
        name=lambda: "target_backend",
        num_qubits=3,
    )

    topology = HardwareTopology.from_qiskit_backend(
        backend,
        two_q_gate="cz",
        filter_idle_qubits=True,
    )

    assert calls == [("cz", True)]
    assert topology.name == "target_backend"
    assert topology.node_ids == (0, 1, 2)
    assert topology.edges == ((0, 2),)


def test_hardware_topology_from_qiskit_backend_uses_legacy_configuration() -> None:
    configuration = SimpleNamespace(
        coupling_map=((0, 1), (2, 3)),
        n_qubits=5,
        backend_name="legacy_backend",
    )
    backend = SimpleNamespace(configuration=lambda: configuration)

    topology = HardwareTopology.from_qiskit_backend(
        backend,
        coordinates={
            0: (0.0, 0.0),
            1: (1.0, 0.0),
            2: (0.0, -1.0),
            3: (1.0, -1.0),
            4: (2.0, -1.0),
        },
    )

    assert topology.name == "legacy_backend"
    assert topology.node_ids == (0, 1, 2, 3, 4)
    assert topology.edges == ((0, 1), (2, 3))
    assert topology.coordinates is not None
    assert topology.coordinates[4] == (2.0, -1.0)


def test_hardware_topology_from_qiskit_backend_raises_for_unconstrained_multi_qubit_backend() -> (
    None
):
    backend = SimpleNamespace(
        coupling_map=None,
        name="ideal_backend",
        num_qubits=3,
    )

    with pytest.raises(ValueError, match="could not infer a finite Qiskit backend coupling map"):
        HardwareTopology.from_qiskit_backend(backend)
