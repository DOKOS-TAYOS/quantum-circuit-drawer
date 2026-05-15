"""Fluent helpers for building ``CircuitIR`` without touching framework SDKs."""

from __future__ import annotations

from collections.abc import Sequence

from .ir.circuit import CircuitIR, OperationNode
from .ir.measurements import MeasurementIR
from .ir.operations import OperationIR, OperationKind
from .ir.packing import pack_operation_nodes
from .ir.wires import WireIR, WireKind

WireReference = int | str


class CircuitBuilder:
    """Fluent helper for building a public ``CircuitIR`` in pure Python.

    Attributes:
        qubits: Constructor argument accepting either a positive qubit count or explicit
            quantum wire labels.
        cbits: Constructor argument accepting a non-negative classical-bit count or
            explicit classical wire labels.
        name: Optional circuit name stored on the final ``CircuitIR``.

    The builder is useful for tests, examples, and lightweight scripts where importing
    a framework SDK would be unnecessary. Every mutating method returns ``self`` so
    calls can be chained before ``build()`` packs operations into layers.
    """

    def __init__(
        self,
        qubits: int | Sequence[str],
        cbits: int | Sequence[str] = 0,
        *,
        name: str | None = None,
    ) -> None:
        self._quantum_wires = _build_wires(qubits, prefix="q", kind=WireKind.QUANTUM)
        self._classical_wires = _build_wires(cbits, prefix="c", kind=WireKind.CLASSICAL)
        self._quantum_wire_ids = _wire_id_lookup(self._quantum_wires)
        self._classical_wire_ids = _wire_id_lookup(self._classical_wires)
        self._operations: list[OperationNode] = []
        self._name = name

    def gate(
        self,
        name: str,
        *targets: WireReference,
        controls: Sequence[WireReference] = (),
        params: Sequence[object] = (),
        label: str | None = None,
    ) -> CircuitBuilder:
        """Append a generic gate-like operation.

        Args:
            name: Gate name displayed in the circuit, such as ``"H"``, ``"RX"``, or a
                custom operation label. It must not be empty.
            *targets: Target quantum wires as integer indices or wire ids.
            controls: Optional control quantum wires as integer indices or wire ids.
            params: Optional gate parameters stored for display and hover.
            label: Optional visible label override.

        Returns:
            This builder so calls can be chained.
        """

        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("gate name cannot be empty")
        if not targets:
            raise ValueError("gate requires at least one target")

        target_wire_ids = tuple(self._resolve_quantum_wire_id(target) for target in targets)
        control_wire_ids = tuple(self._resolve_quantum_wire_id(control) for control in controls)
        kind = OperationKind.CONTROLLED_GATE if control_wire_ids else OperationKind.GATE
        if normalized_name.upper() == "SWAP" and not control_wire_ids:
            kind = OperationKind.SWAP
        self._operations.append(
            OperationIR(
                kind=kind,
                name=normalized_name,
                target_wires=target_wire_ids,
                control_wires=control_wire_ids,
                parameters=tuple(params),
                label=label,
            )
        )
        return self

    def i(self, target: WireReference) -> CircuitBuilder:
        """Append an identity gate.

        Args:
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("I", target)

    def h(self, target: WireReference) -> CircuitBuilder:
        """Append a Hadamard gate.

        Args:
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("H", target)

    def x(self, target: WireReference) -> CircuitBuilder:
        """Append a Pauli-X gate.

        Args:
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("X", target)

    def y(self, target: WireReference) -> CircuitBuilder:
        """Append a Pauli-Y gate.

        Args:
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("Y", target)

    def z(self, target: WireReference) -> CircuitBuilder:
        """Append a Pauli-Z gate.

        Args:
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("Z", target)

    def s(self, target: WireReference) -> CircuitBuilder:
        """Append an S phase gate.

        Args:
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("S", target)

    def sdg(self, target: WireReference) -> CircuitBuilder:
        """Append an inverse S phase gate.

        Args:
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("SDG", target)

    def t(self, target: WireReference) -> CircuitBuilder:
        """Append a T phase gate.

        Args:
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("T", target)

    def tdg(self, target: WireReference) -> CircuitBuilder:
        """Append an inverse T phase gate.

        Args:
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("TDG", target)

    def sx(self, target: WireReference) -> CircuitBuilder:
        """Append a square-root-X gate.

        Args:
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("SX", target)

    def sxdg(self, target: WireReference) -> CircuitBuilder:
        """Append an inverse square-root-X gate.

        Args:
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("SXDG", target)

    def p(self, theta: object, target: WireReference) -> CircuitBuilder:
        """Append a phase gate.

        Args:
            theta: Phase angle or symbolic parameter to display.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("P", target, params=(theta,))

    def rx(self, theta: object, target: WireReference) -> CircuitBuilder:
        """Append an X-axis rotation gate.

        Args:
            theta: Rotation angle or symbolic parameter to display.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("RX", target, params=(theta,))

    def ry(self, theta: object, target: WireReference) -> CircuitBuilder:
        """Append a Y-axis rotation gate.

        Args:
            theta: Rotation angle or symbolic parameter to display.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("RY", target, params=(theta,))

    def rz(self, theta: object, target: WireReference) -> CircuitBuilder:
        """Append a Z-axis rotation gate.

        Args:
            theta: Rotation angle or symbolic parameter to display.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("RZ", target, params=(theta,))

    def rxx(self, theta: object, first: WireReference, second: WireReference) -> CircuitBuilder:
        """Append a two-qubit XX rotation gate.

        Args:
            theta: Rotation angle or symbolic parameter to display.
            first: First target quantum wire index or wire id.
            second: Second target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("RXX", first, second, params=(theta,))

    def ryy(self, theta: object, first: WireReference, second: WireReference) -> CircuitBuilder:
        """Append a two-qubit YY rotation gate.

        Args:
            theta: Rotation angle or symbolic parameter to display.
            first: First target quantum wire index or wire id.
            second: Second target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("RYY", first, second, params=(theta,))

    def rzz(self, theta: object, first: WireReference, second: WireReference) -> CircuitBuilder:
        """Append a two-qubit ZZ rotation gate.

        Args:
            theta: Rotation angle or symbolic parameter to display.
            first: First target quantum wire index or wire id.
            second: Second target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("RZZ", first, second, params=(theta,))

    def rzx(self, theta: object, first: WireReference, second: WireReference) -> CircuitBuilder:
        """Append a two-qubit ZX rotation gate.

        Args:
            theta: Rotation angle or symbolic parameter to display.
            first: First target quantum wire index or wire id.
            second: Second target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("RZX", first, second, params=(theta,))

    def u(
        self,
        theta: object,
        phi: object,
        lam: object,
        target: WireReference,
    ) -> CircuitBuilder:
        """Append a general single-qubit U gate.

        Args:
            theta: First U-gate parameter.
            phi: Second U-gate parameter.
            lam: Third U-gate parameter.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("U", target, params=(theta, phi, lam))

    def u2(self, phi: object, lam: object, target: WireReference) -> CircuitBuilder:
        """Append a two-parameter U2 gate.

        Args:
            phi: First U2 parameter.
            lam: Second U2 parameter.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("U2", target, params=(phi, lam))

    def cx(self, control: WireReference, target: WireReference) -> CircuitBuilder:
        """Append a controlled-X gate.

        Args:
            control: Control quantum wire index or wire id.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("X", target, controls=(control,))

    def cy(self, control: WireReference, target: WireReference) -> CircuitBuilder:
        """Append a controlled-Y gate.

        Args:
            control: Control quantum wire index or wire id.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("Y", target, controls=(control,))

    def cz(self, control: WireReference, target: WireReference) -> CircuitBuilder:
        """Append a controlled-Z gate.

        Args:
            control: Control quantum wire index or wire id.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("Z", target, controls=(control,))

    def ch(self, control: WireReference, target: WireReference) -> CircuitBuilder:
        """Append a controlled-Hadamard gate.

        Args:
            control: Control quantum wire index or wire id.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("H", target, controls=(control,))

    def cp(self, theta: object, control: WireReference, target: WireReference) -> CircuitBuilder:
        """Append a controlled phase gate.

        Args:
            theta: Phase angle or symbolic parameter to display.
            control: Control quantum wire index or wire id.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("P", target, controls=(control,), params=(theta,))

    def crx(
        self,
        theta: object,
        control: WireReference,
        target: WireReference,
    ) -> CircuitBuilder:
        """Append a controlled X-axis rotation gate.

        Args:
            theta: Rotation angle or symbolic parameter to display.
            control: Control quantum wire index or wire id.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("RX", target, controls=(control,), params=(theta,))

    def cry(
        self,
        theta: object,
        control: WireReference,
        target: WireReference,
    ) -> CircuitBuilder:
        """Append a controlled Y-axis rotation gate.

        Args:
            theta: Rotation angle or symbolic parameter to display.
            control: Control quantum wire index or wire id.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("RY", target, controls=(control,), params=(theta,))

    def crz(
        self,
        theta: object,
        control: WireReference,
        target: WireReference,
    ) -> CircuitBuilder:
        """Append a controlled Z-axis rotation gate.

        Args:
            theta: Rotation angle or symbolic parameter to display.
            control: Control quantum wire index or wire id.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("RZ", target, controls=(control,), params=(theta,))

    def cu(
        self,
        theta: object,
        phi: object,
        lam: object,
        gamma: object,
        control: WireReference,
        target: WireReference,
    ) -> CircuitBuilder:
        """Append a controlled general U gate.

        Args:
            theta: First U parameter.
            phi: Second U parameter.
            lam: Third U parameter.
            gamma: Global phase or fourth controlled-U parameter to display.
            control: Control quantum wire index or wire id.
            target: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("U", target, controls=(control,), params=(theta, phi, lam, gamma))

    def swap(self, first: WireReference, second: WireReference) -> CircuitBuilder:
        """Append an uncontrolled two-qubit swap operation.

        Args:
            first: First target quantum wire index or wire id.
            second: Second target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        first_wire_id = self._resolve_quantum_wire_id(first)
        second_wire_id = self._resolve_quantum_wire_id(second)
        self._operations.append(
            OperationIR(
                kind=OperationKind.SWAP,
                name="SWAP",
                target_wires=(first_wire_id, second_wire_id),
            )
        )
        return self

    def barrier(self, *qubits: WireReference) -> CircuitBuilder:
        """Append a barrier operation.

        Args:
            *qubits: Optional quantum wire indices or ids. When omitted, the barrier
                spans every quantum wire.

        Returns:
            This builder so calls can be chained.
        """

        target_wire_ids = (
            tuple(wire.id for wire in self._quantum_wires)
            if not qubits
            else tuple(self._resolve_quantum_wire_id(qubit) for qubit in qubits)
        )
        self._operations.append(
            OperationIR(
                kind=OperationKind.BARRIER,
                name="BARRIER",
                target_wires=target_wire_ids,
            )
        )
        return self

    def reset(self, qubit: WireReference) -> CircuitBuilder:
        """Append a reset operation on one quantum wire.

        Args:
            qubit: Target quantum wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        return self.gate("RESET", qubit)

    def measure(self, qubit: WireReference, cbit: WireReference) -> CircuitBuilder:
        """Append one quantum-to-classical measurement.

        Args:
            qubit: Source quantum wire index or wire id.
            cbit: Target classical wire index or wire id.

        Returns:
            This builder so calls can be chained.
        """

        quantum_wire_id = self._resolve_quantum_wire_id(qubit)
        classical_wire = self._resolve_classical_wire(cbit)
        self._operations.append(
            MeasurementIR(
                kind=OperationKind.MEASUREMENT,
                name="M",
                target_wires=(quantum_wire_id,),
                classical_target=classical_wire.id,
                metadata={"classical_bit_label": classical_wire.label or classical_wire.id},
            )
        )
        return self

    def measure_all(self) -> CircuitBuilder:
        """Append one measurement from every qubit to the matching classical bit.

        Returns:
            This builder so calls can be chained.
        """

        if len(self._classical_wires) != len(self._quantum_wires):
            raise ValueError("measure_all requires the same number of classical and quantum wires")
        for index, _wire in enumerate(self._quantum_wires):
            self.measure(index, index)
        return self

    def build(self) -> CircuitIR:
        """Build a packed ``CircuitIR`` from the appended operations.

        Returns:
            ``CircuitIR`` with resolved wires and operations packed into drawable
            layers.
        """

        return CircuitIR(
            quantum_wires=self._quantum_wires,
            classical_wires=self._classical_wires,
            layers=pack_operation_nodes(self._operations),
            name=self._name,
        )

    def _resolve_quantum_wire_id(self, reference: WireReference) -> str:
        return _resolve_wire_id(reference, lookup=self._quantum_wire_ids, kind="quantum")

    def _resolve_classical_wire(self, reference: WireReference) -> WireIR:
        wire_id = _resolve_wire_id(reference, lookup=self._classical_wire_ids, kind="classical")
        return next(wire for wire in self._classical_wires if wire.id == wire_id)


def _build_wires(
    values: int | Sequence[str],
    *,
    prefix: str,
    kind: WireKind,
) -> tuple[WireIR, ...]:
    if isinstance(values, bool):
        raise ValueError(f"{kind.value} wire count must be an integer or a sequence of names")
    if isinstance(values, int):
        if values < 0:
            raise ValueError(f"{kind.value} wire count cannot be negative")
        labels = tuple(f"{prefix}{index}" for index in range(values))
    else:
        if isinstance(values, str):
            raise ValueError(f"{kind.value} wire names must be provided as a sequence of strings")
        labels = tuple(str(value).strip() for value in values)
        if any(not label for label in labels):
            raise ValueError(f"{kind.value} wire names cannot be empty")
        if len(set(labels)) != len(labels):
            raise ValueError(f"{kind.value} wire names must be unique")

    return tuple(
        WireIR(
            id=f"{prefix}{index}",
            index=index,
            kind=kind,
            label=label,
            metadata={"bundle_size": 1} if kind is WireKind.CLASSICAL else {},
        )
        for index, label in enumerate(labels)
    )


def _wire_id_lookup(wires: Sequence[WireIR]) -> dict[int | str, str]:
    lookup: dict[int | str, str] = {}
    for wire in wires:
        lookup[wire.index] = wire.id
        lookup[wire.id] = wire.id
        if wire.label is not None:
            lookup[wire.label] = wire.id
    return lookup


def _resolve_wire_id(
    reference: WireReference,
    *,
    lookup: dict[int | str, str],
    kind: str,
) -> str:
    if isinstance(reference, bool) or not isinstance(reference, int | str):
        raise ValueError(f"{kind} wire references must be integers or strings")
    try:
        return lookup[reference]
    except KeyError as exc:
        raise ValueError(f"unknown {kind} wire reference {reference!r}") from exc
