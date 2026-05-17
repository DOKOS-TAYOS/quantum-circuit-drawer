from __future__ import annotations

import pytest

import quantum_circuit_drawer
from quantum_circuit_drawer import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    LatexBackend,
    LatexMode,
    LatexResult,
    circuit_to_latex,
)
from quantum_circuit_drawer.api import circuit_to_latex as api_circuit_to_latex
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from tests.support import build_public_draw_config, build_sample_ir, build_wrapped_ir


def test_circuit_to_latex_exports_public_api() -> None:
    assert quantum_circuit_drawer.circuit_to_latex is not None
    assert api_circuit_to_latex is not None
    assert quantum_circuit_drawer.LatexBackend is LatexBackend
    assert quantum_circuit_drawer.LatexMode is LatexMode
    assert quantum_circuit_drawer.LatexResult is LatexResult


def test_latex_result_normalizes_public_strings_for_to_dict() -> None:
    result = LatexResult(
        source="",
        pages=("",),
        backend="tikz",  # type: ignore[arg-type]
        mode="pages",  # type: ignore[arg-type]
        page_count=1,
    )

    assert result.backend is LatexBackend.TIKZ
    assert result.mode is LatexMode.PAGES
    assert result.to_dict()["backend"] == "tikz"
    assert result.to_dict()["mode"] == "pages"


def test_circuit_to_latex_returns_quantikz_full_source_for_basic_circuit() -> None:
    result = circuit_to_latex(build_sample_ir(), mode=LatexMode.FULL)

    assert result.backend is LatexBackend.QUANTIKZ
    assert result.mode is LatexMode.FULL
    assert result.page_count == 1
    assert result.pages == (result.source,)
    assert r"\begin{adjustbox}{width=\linewidth,center}" in result.source
    assert r"\end{adjustbox}" in result.source
    assert "\\begin{quantikz}" in result.source
    assert "\\lstick{q0}" in result.source
    assert "\\gate{H}" in result.source
    assert "\\ctrl{1}" in result.source
    assert "\\targ{}" in result.source
    assert "\\meter{}" in result.source
    assert "\\cw" in result.source
    assert "\\begin{figure}" not in result.source
    assert result.detected_framework == "ir"
    assert result.to_dict()["backend"] == "quantikz"


def test_circuit_to_latex_accepts_flat_common_kwargs() -> None:
    result = circuit_to_latex(
        build_sample_ir(),
        backend="quantikz",
        mode="full",
        framework="ir",
        composite_mode="compact",
    )

    assert result.backend is LatexBackend.QUANTIKZ
    assert result.mode is LatexMode.FULL
    assert result.detected_framework == "ir"
    assert "\\begin{quantikz}" in result.source


def test_circuit_to_latex_flat_kwargs_override_config() -> None:
    config = DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(
                framework="ir",
                mode=DrawMode.PAGES,
                composite_mode="expand",
            )
        )
    )

    result = circuit_to_latex(
        build_sample_ir(),
        mode="full",
        composite_mode="compact",
        config=config,
    )

    assert result.mode is LatexMode.FULL
    assert result.page_count == 1
    assert "% Page 1" not in result.source


def test_circuit_to_latex_flat_strings_and_enums_match() -> None:
    enum_result = circuit_to_latex(
        build_sample_ir(),
        backend=LatexBackend.QUANTIKZ,
        mode=LatexMode.FULL,
        framework="ir",
        composite_mode="compact",
    )
    string_result = circuit_to_latex(
        build_sample_ir(),
        backend="quantikz",
        mode="full",
        framework="ir",
        composite_mode="compact",
    )

    assert enum_result.backend is string_result.backend
    assert enum_result.mode is string_result.mode
    assert enum_result.source == string_result.source


def test_package_level_circuit_to_latex_forwards_flat_common_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    expected_result = LatexResult(
        source="",
        pages=("",),
        backend=LatexBackend.QUANTIKZ,
        mode=LatexMode.FULL,
        page_count=1,
    )

    def fake_circuit_to_latex(
        circuit: object,
        *,
        config: DrawConfig | None = None,
        backend: object = LatexBackend.QUANTIKZ,
        mode: object = None,
        framework: str | None = None,
        composite_mode: str | None = None,
    ) -> LatexResult:
        captured["circuit"] = circuit
        captured["config"] = config
        captured["backend"] = backend
        captured["mode"] = mode
        captured["framework"] = framework
        captured["composite_mode"] = composite_mode
        return expected_result

    monkeypatch.setattr(
        "quantum_circuit_drawer.api.circuit_to_latex",
        fake_circuit_to_latex,
    )
    config = DrawConfig()

    result = quantum_circuit_drawer.circuit_to_latex(
        build_sample_ir(),
        config=config,
        backend="tikz",
        mode="full",
        framework="ir",
        composite_mode="expand",
    )

    assert result is expected_result
    assert captured["config"] is config
    assert captured["backend"] == "tikz"
    assert captured["mode"] == "full"
    assert captured["framework"] == "ir"
    assert captured["composite_mode"] == "expand"


def test_circuit_to_latex_pages_mode_returns_one_source_per_wrapped_page() -> None:
    result = circuit_to_latex(
        build_wrapped_ir(),
        config=build_public_draw_config(
            mode=DrawMode.PAGES,
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    assert result.mode is LatexMode.PAGES
    assert result.page_count == 2
    assert len(result.pages) == 2
    assert "% Page 1" in result.source
    assert "% Page 2" in result.source
    assert result.source.count("\\begin{quantikz}") == 2
    assert result.source.count(r"\begin{adjustbox}{width=\linewidth,center}") == 2
    assert "\\gate{Z}" in result.pages[1]
    assert "\\gate{Y}" in result.pages[1]


def test_circuit_to_latex_escapes_special_label_characters() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q_0 & main")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="phase_gate",
                        target_wires=("q0",),
                        label="R_#%",
                    )
                ]
            )
        ],
    )

    result = circuit_to_latex(circuit, mode="full")

    assert "\\lstick{q\\_0 \\& main}" in result.source
    assert "\\gate{R\\_\\#\\%}" in result.source


def test_circuit_to_latex_wraps_parametric_gate_subtitles_safely_for_quantikz() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="RZ",
                        target_wires=("q0",),
                        parameters=(0.5,),
                    )
                ]
            )
        ],
    )

    result = circuit_to_latex(circuit, mode="full")

    assert "\\gate{RZ\\\\0.5}" not in result.source
    assert "\\gate{\\shortstack{RZ\\\\0.5}}" in result.source


@pytest.mark.parametrize("backend", ["bad", object()])
def test_circuit_to_latex_rejects_invalid_backend(backend: object) -> None:
    with pytest.raises(ValueError, match="backend must be one of"):
        circuit_to_latex(build_sample_ir(), backend=backend)


@pytest.mark.parametrize("mode", ["auto", "slider", DrawMode.SLIDER, object()])
def test_circuit_to_latex_rejects_invalid_explicit_mode(mode: object) -> None:
    with pytest.raises(ValueError, match="mode must be one of"):
        circuit_to_latex(build_sample_ir(), mode=mode)


def test_circuit_to_latex_rejects_explicit_3d_view() -> None:
    with pytest.raises(ValueError, match="LaTeX export only supports 2D circuits"):
        circuit_to_latex(
            build_sample_ir(),
            config=DrawConfig(
                side=DrawSideConfig(render=CircuitRenderOptions(view="3d")),
            ),
        )


def test_circuit_to_latex_returns_basic_tikzpicture() -> None:
    result = circuit_to_latex(build_sample_ir(), backend=LatexBackend.TIKZ, mode="full")

    assert result.backend is LatexBackend.TIKZ
    assert result.mode is LatexMode.FULL
    assert "\\begin{tikzpicture}" in result.source
    assert "\\draw" in result.source
    assert "node" in result.source
    assert "H" in result.source


def test_circuit_to_latex_quantikz_supports_open_controls_and_swap_barriers() -> None:
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
                        control_values=((0,),),
                    )
                ]
            ),
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=("q0", "q1"))
                ]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.BARRIER,
                        name="BARRIER",
                        target_wires=("q0", "q1"),
                    )
                ]
            ),
        ],
    )

    result = circuit_to_latex(
        circuit,
        config=DrawConfig(
            side=DrawSideConfig(
                appearance=CircuitAppearanceOptions(style={"show_wire_labels": False}),
            ),
        ),
        mode="full",
    )

    assert "\\octrl{1}" in result.source
    assert "\\targ{}" in result.source
    assert "\\swap{1}" in result.source
    assert "\\targX{}" in result.source
    assert "\\barrier" not in result.source
    assert "\\slice{}" in result.source

    quantikz_lines = result.source.splitlines()
    quantikz_end_index = quantikz_lines.index(r"\end{quantikz}")
    assert not quantikz_lines[quantikz_end_index - 1].endswith(r"\\")
