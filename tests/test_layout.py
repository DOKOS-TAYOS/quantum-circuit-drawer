from __future__ import annotations

from quantum_circuit_drawer.ir import ClassicalConditionIR
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout._layering import normalize_draw_layers
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.layout.spacing import estimate_text_width, operation_width
from quantum_circuit_drawer.style import DrawStyle


def test_draw_style_defaults_to_denser_horizontal_spacing() -> None:
    assert DrawStyle().layer_spacing == 0.45


def build_layout_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
            WireIR(id="q2", index=2, kind=WireKind.QUANTUM, label="q2"),
        ],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c0")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",)),
                    OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q2",)),
                ]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q2",),
                        control_wires=("q0",),
                    )
                ]
            ),
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q2",),
                        classical_target="c0",
                    )
                ]
            ),
        ],
    )


def test_layout_engine_assigns_columns_and_geometry() -> None:
    scene = LayoutEngine().compute(build_layout_ir(), DrawStyle())

    assert scene.width > scene.style.margin_left
    assert scene.height > scene.style.margin_top
    assert len(scene.gates) == 3
    assert len(scene.measurements) == 1
    assert len(scene.controls) == 1
    assert scene.gates[0].column == 0
    assert scene.gates[1].column == 0
    assert scene.gates[2].column == 1


def test_layout_engine_keeps_late_measurements_after_swap_and_barrier() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
            WireIR(id="q2", index=2, kind=WireKind.QUANTUM, label="q2"),
        ],
        classical_wires=[
            WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c0"),
            WireIR(id="c1", index=1, kind=WireKind.CLASSICAL, label="c1"),
        ],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                    )
                ]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="Z",
                        target_wires=("q2",),
                        control_wires=("q1",),
                    )
                ]
            ),
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=("q0", "q2"))
                ]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.BARRIER, name="BARRIER", target_wires=("q0", "q1", "q2")
                    )
                ]
            ),
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q1",),
                        classical_target="c0",
                    ),
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q2",),
                        classical_target="c1",
                    ),
                ]
            ),
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle())

    assert [gate.column for gate in scene.gates] == [0, 1]
    assert [control.column for control in scene.controls] == [1, 2, 2]
    assert [swap.column for swap in scene.swaps] == [3]
    assert [barrier.column for barrier in scene.barriers] == [4]
    assert [measurement.column for measurement in scene.measurements] == [5, 6]

    first_measurement = scene.measurements[0]
    classical_connection = next(
        connection for connection in scene.connections if connection.is_classical
    )

    assert first_measurement.connector_x > first_measurement.x
    assert first_measurement.connector_y > first_measurement.quantum_y
    assert classical_connection.x == first_measurement.connector_x
    assert classical_connection.y_start == first_measurement.connector_y
    assert classical_connection.arrow_at_end is True
    assert classical_connection.label == "c0"


def test_normalize_draw_layers_splits_operations_that_share_wire_span() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c")],
        layers=[
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q0",),
                        classical_target="c0",
                    ),
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q1",),
                        classical_conditions=(
                            ClassicalConditionIR(wire_ids=("c0",), expression="if c[0]=1"),
                        ),
                    ),
                ]
            )
        ],
    )

    normalized_layers = normalize_draw_layers(circuit)

    assert len(normalized_layers) == 2
    assert isinstance(normalized_layers[0].operations[0], MeasurementIR)
    assert normalized_layers[1].operations[0].name == "X"


def test_layout_engine_wraps_long_circuits_into_vertical_pages() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q1",))]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                    )
                ]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="Z", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="Y", target_wires=("q1",))]
            ),
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))

    assert [(page.start_column, page.end_column) for page in scene.pages] == [(0, 2), (3, 4)]
    assert scene.page_height < scene.height
    assert scene.width <= 6.5


def test_layout_engine_places_classical_condition_connection_from_classical_wire() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q0",),
                        classical_conditions=(
                            ClassicalConditionIR(wire_ids=("c0",), expression="if c[0]=1"),
                        ),
                    )
                ]
            )
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle())

    classical_connection = next(
        connection
        for connection in scene.connections
        if connection.is_classical and connection.label == "if c[0]=1"
    )

    assert classical_connection.y_start == scene.wire_y_positions["c0"]
    assert classical_connection.y_end == scene.gates[0].y + (scene.gates[0].height / 2)
    assert classical_connection.double_line is True
    assert classical_connection.linestyle == "solid"
    assert classical_connection.arrow_at_end is True


def test_layout_engine_separates_independent_operations_with_overlapping_vertical_spans() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
            WireIR(id="q2", index=2, kind=WireKind.QUANTUM, label="q2"),
            WireIR(id="q3", index=3, kind=WireKind.QUANTUM, label="q3"),
            WireIR(id="q4", index=4, kind=WireKind.QUANTUM, label="q4"),
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q3",),
                        control_wires=("q0", "q2"),
                    ),
                    OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=("q1", "q4")),
                ]
            )
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle())

    assert [gate.column for gate in scene.gates] == [0]
    assert [swap.column for swap in scene.swaps] == [1]


def test_layout_engine_keeps_barrier_columns_compact() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.BARRIER, name="BARRIER", target_wires=("q0", "q1")
                    )
                ]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q1",))]
            ),
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle())

    assert scene.width < 6.0


def test_operation_width_keeps_parametric_rotation_gates_compact() -> None:
    style = DrawStyle()
    operation = OperationIR(
        kind=OperationKind.GATE,
        name="RX",
        target_wires=("q0",),
        parameters=(3.1415926535,),
    )

    assert operation_width(operation, style) == style.gate_width


def test_estimate_text_width_returns_zero_for_empty_labels() -> None:
    assert estimate_text_width("", font_size=12.0) == 0.0


def test_operation_width_expands_for_long_labels_and_subtitles() -> None:
    style = DrawStyle(show_params=True)
    operation = OperationIR(
        kind=OperationKind.GATE,
        name="LONGGATE",
        target_wires=("q0",),
        parameters=(3.1415926535,),
    )

    assert operation_width(operation, style) > style.gate_width


def test_layout_engine_prefers_specific_classical_bit_labels_for_measurements() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        classical_wires=[
            WireIR(
                id="c0",
                index=0,
                kind=WireKind.CLASSICAL,
                label="alpha",
                metadata={"bundle_size": 2},
            )
        ],
        layers=[
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q0",),
                        classical_target="c0",
                        metadata={"classical_bit_label": "alpha[1]"},
                    )
                ]
            )
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle())

    classical_connection = next(
        connection for connection in scene.connections if connection.is_classical
    )

    assert classical_connection.label == "alpha[1]"


def test_layout_engine_splits_measurements_and_classically_conditioned_gates_by_classical_wire() -> (
    None
):
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c")],
        layers=[
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q0",),
                        classical_target="c0",
                    ),
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q1",),
                        classical_conditions=(
                            ClassicalConditionIR(wire_ids=("c0",), expression="if c[0]=1"),
                        ),
                    ),
                ]
            )
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle())

    assert [measurement.column for measurement in scene.measurements] == [0]
    assert [gate.column for gate in scene.gates] == [1]


def test_layout_engine_draws_classical_condition_connection_and_label() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q0",),
                        classical_conditions=(
                            ClassicalConditionIR(wire_ids=("c0",), expression="if c[0]=1"),
                        ),
                    )
                ]
            )
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle())

    classical_connection = next(
        connection
        for connection in scene.connections
        if connection.is_classical and connection.label == "if c[0]=1"
    )

    assert classical_connection.arrow_at_end is True
    assert classical_connection.linestyle == "solid"


def test_layout_engine_reuses_cached_operation_metrics(monkeypatch) -> None:
    operation_width_calls = 0
    original_operation_width = operation_width

    def count_operation_width(*args, **kwargs):
        nonlocal operation_width_calls
        operation_width_calls += 1
        return original_operation_width(*args, **kwargs)

    monkeypatch.setattr(
        "quantum_circuit_drawer.layout.engine.operation_width", count_operation_width
    )

    circuit = build_layout_ir()
    LayoutEngine().compute(circuit, DrawStyle())

    operation_count = sum(len(layer.operations) for layer in circuit.layers)

    assert operation_width_calls == operation_count


def test_layout_engine_emits_debug_summary(caplog) -> None:
    caplog.set_level("DEBUG", logger="quantum_circuit_drawer.layout.engine")

    scene = LayoutEngine().compute(build_layout_ir(), DrawStyle())

    assert scene.pages
    assert any(
        "Computed layout scene" in record.getMessage() and "pages=1" in record.getMessage()
        for record in caplog.records
    )


def test_layout_engine_draws_canonical_controlled_x_as_not_target() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        canonical_family=CanonicalGateFamily.X,
                        target_wires=("q1",),
                        control_wires=("q0",),
                    )
                ]
            )
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle())

    assert len(scene.gates) == 1
    assert scene.gates[0].render_style.value == "x_target"
    assert scene.gates[0].label == "X"


def test_layout_engine_draws_canonical_cz_as_two_controls_without_box() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="Z",
                        canonical_family=CanonicalGateFamily.Z,
                        target_wires=("q1",),
                        control_wires=("q0",),
                    )
                ]
            )
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle())

    assert len(scene.gates) == 0
    assert len(scene.controls) == 2
    assert len(scene.connections) == 1


def test_layout_engine_draws_canonical_controlled_rz_with_compact_box() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="RZ",
                        canonical_family=CanonicalGateFamily.RZ,
                        target_wires=("q1",),
                        control_wires=("q0",),
                        parameters=(0.5,),
                    )
                ]
            )
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle(show_params=True))

    assert len(scene.gates) == 1
    assert scene.gates[0].render_style.value == "box"
    assert scene.gates[0].label == "RZ"
    assert scene.gates[0].subtitle == "0.5"


def test_layout_engine_adds_target_wire_order_annotations_for_multi_wire_boxes() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
            WireIR(id="q2", index=2, kind=WireKind.QUANTUM, label="q2"),
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="RZZ",
                        target_wires=("q2", "q0"),
                        parameters=(0.7,),
                    )
                ]
            )
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle())

    annotations_by_text = {annotation.text: annotation for annotation in scene.gate_annotations}

    assert set(annotations_by_text) == {"0", "1"}
    assert annotations_by_text["0"].y == scene.wire_y_positions["q2"]
    assert annotations_by_text["1"].y == scene.wire_y_positions["q0"]


def test_layout_engine_only_labels_target_wires_for_controlled_multi_wire_boxes() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
            WireIR(id="q2", index=2, kind=WireKind.QUANTUM, label="q2"),
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="RZZ",
                        target_wires=("q1", "q2"),
                        control_wires=("q0",),
                        parameters=(0.5,),
                    )
                ]
            )
        ],
    )

    scene = LayoutEngine().compute(circuit, DrawStyle())

    assert [annotation.text for annotation in scene.gate_annotations] == ["0", "1"]
    assert [annotation.y for annotation in scene.gate_annotations] == [
        scene.wire_y_positions["q1"],
        scene.wire_y_positions["q2"],
    ]
