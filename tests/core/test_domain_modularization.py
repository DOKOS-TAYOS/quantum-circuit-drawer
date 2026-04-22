from __future__ import annotations

import ast
from importlib import import_module
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

from quantum_circuit_drawer.api import draw_quantum_circuit
from quantum_circuit_drawer.exceptions import RenderingError
from quantum_circuit_drawer.export import save_matplotlib_figure
from quantum_circuit_drawer.histogram import plot_histogram

_ROOT_COMPATIBILITY_FACADE_TARGETS: tuple[tuple[str, str], ...] = (
    (
        "quantum_circuit_drawer._draw_managed",
        "quantum_circuit_drawer.managed.drawing",
    ),
    (
        "quantum_circuit_drawer._draw_managed_page_window",
        "quantum_circuit_drawer.managed.page_window",
    ),
    (
        "quantum_circuit_drawer._draw_managed_page_window_3d",
        "quantum_circuit_drawer.managed.page_window_3d",
    ),
    (
        "quantum_circuit_drawer._draw_managed_slider",
        "quantum_circuit_drawer.managed.slider",
    ),
    (
        "quantum_circuit_drawer._draw_managed_topology_menu",
        "quantum_circuit_drawer.managed.topology_menu",
    ),
    (
        "quantum_circuit_drawer._draw_managed_viewport",
        "quantum_circuit_drawer.managed.viewport",
    ),
    (
        "quantum_circuit_drawer._draw_managed_zoom",
        "quantum_circuit_drawer.managed.zoom",
    ),
    (
        "quantum_circuit_drawer._draw_request",
        "quantum_circuit_drawer.drawing.request",
    ),
    (
        "quantum_circuit_drawer._managed_3d_view_state",
        "quantum_circuit_drawer.managed.view_state_3d",
    ),
    (
        "quantum_circuit_drawer._managed_ui_palette",
        "quantum_circuit_drawer.managed.ui_palette",
    ),
    (
        "quantum_circuit_drawer._matrix_support",
        "quantum_circuit_drawer.utils.matrix_support",
    ),
    (
        "quantum_circuit_drawer._runtime_context",
        "quantum_circuit_drawer.drawing.runtime",
    ),
    (
        "quantum_circuit_drawer._scene_pages",
        "quantum_circuit_drawer.drawing.pages",
    ),
)

_ROOT_COMPATIBILITY_IMPORT_NAMES: tuple[str, ...] = tuple(
    module_name.rsplit(".", maxsplit=1)[-1] for module_name, _ in _ROOT_COMPATIBILITY_FACADE_TARGETS
)
_MANAGED_DRAWING_ALLOWED_IMPORTERS: tuple[str, ...] = (
    "src/quantum_circuit_drawer/managed/__init__.py",
    "src/quantum_circuit_drawer/managed/drawing.py",
)
_TEST_MANAGED_DRAWING_ALLOWED_IMPORTERS: tuple[str, ...] = (
    "tests/core/test_domain_modularization.py",
    "tests/drawing/test_drawing_refactor_boundaries.py",
)


def _module_source_path(repo_root: Path, module_name: str) -> Path:
    return repo_root / "src" / Path(*module_name.split(".")).with_suffix(".py")


def _imported_names(node: ast.Import | ast.ImportFrom) -> set[str]:
    return {alias.name for alias in node.names}


def _imports_managed_drawing_facade(
    node: ast.AST,
    *,
    relative_import_base: str | None = None,
) -> bool:
    managed_drawing_module_names = {
        "quantum_circuit_drawer.managed.drawing",
        "managed.drawing",
    }
    managed_parent_module_names = {
        "quantum_circuit_drawer.managed",
        "managed",
    }

    if isinstance(node, ast.Import):
        return bool(_imported_names(node) & {"quantum_circuit_drawer.managed.drawing"})

    if not isinstance(node, ast.ImportFrom):
        return False

    if node.module in managed_drawing_module_names:
        return True

    if node.module in managed_parent_module_names and "drawing" in _imported_names(node):
        return True

    if relative_import_base == "managed":
        if node.level == 1 and node.module == "drawing":
            return True
        if node.level == 1 and node.module is None and "drawing" in _imported_names(node):
            return True

    if relative_import_base == "renderers":
        if node.level == 2 and node.module == "managed.drawing":
            return True
        if node.level == 2 and node.module == "managed" and "drawing" in _imported_names(node):
            return True

    return False


def test_domain_packages_expose_draw_and_histogram_entrypoints() -> None:
    from quantum_circuit_drawer.drawing.api import (
        draw_quantum_circuit as drawing_draw_quantum_circuit,
    )
    from quantum_circuit_drawer.plots.histogram import plot_histogram as plots_plot_histogram

    assert drawing_draw_quantum_circuit is draw_quantum_circuit
    assert plots_plot_histogram is plot_histogram


@pytest.mark.parametrize(
    ("facade_module_name", "target_module_name"),
    _ROOT_COMPATIBILITY_FACADE_TARGETS,
)
def test_root_compatibility_facades_reexport_split_modules(
    facade_module_name: str,
    target_module_name: str,
) -> None:
    facade_module = import_module(facade_module_name)
    target_module = import_module(target_module_name)

    assert hasattr(target_module, "__all__")
    expected_public_names = tuple(target_module.__all__)

    assert tuple(facade_module.__all__) == expected_public_names
    assert expected_public_names
    assert getattr(facade_module, expected_public_names[0]) == getattr(
        target_module,
        expected_public_names[0],
    )
    assert getattr(facade_module, expected_public_names[-1]) == getattr(
        target_module,
        expected_public_names[-1],
    )


def test_compatibility_facades_do_not_use_reflective_export_helpers() -> None:
    repo_root = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "src").is_dir()
    )
    compatibility_modules = (
        *(module_name for module_name, _ in _ROOT_COMPATIBILITY_FACADE_TARGETS),
        "quantum_circuit_drawer.managed.drawing",
    )

    violations: list[str] = []
    for module_name in compatibility_modules:
        source_file = _module_source_path(repo_root, module_name)
        module = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        for node in ast.walk(module):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"dir", "globals"}:
                    violations.append(str(source_file.relative_to(repo_root)).replace("\\", "/"))
                    break

    assert sorted(set(violations)) == []


def test_internal_modules_import_real_owners_not_root_compatibility_shims() -> None:
    repo_root = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "src").is_dir()
    )
    source_roots = (
        repo_root / "src" / "quantum_circuit_drawer",
        repo_root / "scripts",
    )
    shim_files = {
        (repo_root / "src" / "quantum_circuit_drawer" / f"{module_name}.py")
        for module_name in _ROOT_COMPATIBILITY_IMPORT_NAMES
    }
    shim_module_names = set(_ROOT_COMPATIBILITY_IMPORT_NAMES)
    shim_qualified_names = {
        f"quantum_circuit_drawer.{module_name}" for module_name in _ROOT_COMPATIBILITY_IMPORT_NAMES
    }

    violations: list[str] = []
    for source_root in source_roots:
        for source_file in source_root.rglob("*.py"):
            if source_file in shim_files:
                continue
            module = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
            for node in ast.walk(module):
                if isinstance(node, ast.Import):
                    imported_names = {alias.name for alias in node.names}
                    if imported_names & shim_qualified_names:
                        violations.append(str(source_file.relative_to(repo_root)))
                elif isinstance(node, ast.ImportFrom) and node.module is not None:
                    if node.module in shim_module_names or node.module in shim_qualified_names:
                        violations.append(str(source_file.relative_to(repo_root)))

    assert sorted(set(violations)) == []


def test_managed_modules_import_owner_modules_not_managed_drawing_facade() -> None:
    repo_root = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "src").is_dir()
    )
    managed_root = repo_root / "src" / "quantum_circuit_drawer" / "managed"
    allowed_importers = set(_MANAGED_DRAWING_ALLOWED_IMPORTERS)

    violations: list[str] = []
    for source_file in managed_root.rglob("*.py"):
        relative_path = str(source_file.relative_to(repo_root)).replace("\\", "/")
        if relative_path in allowed_importers:
            continue
        module = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        for node in ast.walk(module):
            if _imports_managed_drawing_facade(node, relative_import_base="managed"):
                violations.append(relative_path)

    assert sorted(set(violations)) == []


def test_renderer_modules_do_not_import_managed_drawing_facade() -> None:
    repo_root = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "src").is_dir()
    )
    renderers_root = repo_root / "src" / "quantum_circuit_drawer" / "renderers"

    violations: list[str] = []
    for source_file in renderers_root.rglob("*.py"):
        relative_path = str(source_file.relative_to(repo_root)).replace("\\", "/")
        module = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        for node in ast.walk(module):
            if _imports_managed_drawing_facade(node, relative_import_base="renderers"):
                violations.append(relative_path)

    assert sorted(set(violations)) == []


def test_tests_do_not_import_managed_drawing_facade_outside_compatibility_allowlist() -> None:
    repo_root = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "src").is_dir()
    )
    tests_root = repo_root / "tests"
    allowed_importers = set(_TEST_MANAGED_DRAWING_ALLOWED_IMPORTERS)

    violations: list[str] = []
    for source_file in tests_root.rglob("*.py"):
        relative_path = str(source_file.relative_to(repo_root)).replace("\\", "/")
        if relative_path in allowed_importers:
            continue
        module = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        for node in ast.walk(module):
            if _imports_managed_drawing_facade(node):
                violations.append(relative_path)

    assert sorted(set(violations)) == []


def test_lazy_managed_and_renderer_packages_reexport_split_modules() -> None:
    import quantum_circuit_drawer.managed as managed_facade
    import quantum_circuit_drawer.renderers as renderer_facade
    from quantum_circuit_drawer.managed.drawing import (
        render_draw_pipeline_on_axes,
        render_managed_draw_pipeline,
    )
    from quantum_circuit_drawer.renderers.base import BaseRenderer
    from quantum_circuit_drawer.renderers.matplotlib_renderer import MatplotlibRenderer
    from quantum_circuit_drawer.renderers.matplotlib_renderer_3d import MatplotlibRenderer3D

    assert managed_facade.render_draw_pipeline_on_axes is render_draw_pipeline_on_axes
    assert managed_facade.render_managed_draw_pipeline is render_managed_draw_pipeline
    assert renderer_facade.BaseRenderer is BaseRenderer
    assert renderer_facade.MatplotlibRenderer is MatplotlibRenderer
    assert renderer_facade.MatplotlibRenderer3D is MatplotlibRenderer3D

    with pytest.raises(AttributeError):
        getattr(managed_facade, "missing_managed_export")
    with pytest.raises(AttributeError):
        getattr(renderer_facade, "missing_renderer_export")


def test_second_pass_managed_facades_reexport_split_helpers() -> None:
    from quantum_circuit_drawer.managed.controls import managed_3d_axes_bounds
    from quantum_circuit_drawer.managed.page_window_3d import (
        windowed_3d_page_ranges as facade_windowed_3d_page_ranges,
    )
    from quantum_circuit_drawer.managed.page_window_3d_ranges import windowed_3d_page_ranges
    from quantum_circuit_drawer.managed.slider import (
        _horizontal_scene_for_start_column as facade_horizontal_scene_for_start_column,
    )
    from quantum_circuit_drawer.managed.slider import (
        configure_3d_page_slider as facade_configure_3d_page_slider,
    )
    from quantum_circuit_drawer.managed.slider import (
        managed_3d_axes_bounds as facade_managed_3d_axes_bounds,
    )
    from quantum_circuit_drawer.managed.slider_2d_windowing import (
        _horizontal_scene_for_start_column,
    )
    from quantum_circuit_drawer.managed.slider_3d import configure_3d_page_slider

    assert facade_managed_3d_axes_bounds is managed_3d_axes_bounds
    assert facade_horizontal_scene_for_start_column is _horizontal_scene_for_start_column
    assert facade_configure_3d_page_slider is configure_3d_page_slider
    assert facade_windowed_3d_page_ranges is windowed_3d_page_ranges


def test_third_pass_2d_managed_facades_reexport_split_helpers() -> None:
    from quantum_circuit_drawer.managed.page_window import (
        configure_page_window as facade_configure_page_window,
    )
    from quantum_circuit_drawer.managed.slider import (
        Managed2DPageSliderState as facade_managed_2d_page_slider_state,
    )
    from quantum_circuit_drawer.managed.slider import (
        configure_page_slider as facade_configure_page_slider,
    )
    from quantum_circuit_drawer.managed.slider_2d import (
        Managed2DPageSliderState,
        configure_page_slider,
    )

    assert facade_managed_2d_page_slider_state is Managed2DPageSliderState
    assert facade_configure_page_slider is configure_page_slider
    assert facade_configure_page_window.__name__ == "configure_page_window"


def test_third_pass_2d_private_helper_modules_are_importable() -> None:
    page_window_controls = import_module("quantum_circuit_drawer.managed.page_window_controls")
    page_window_windowing = import_module("quantum_circuit_drawer.managed.page_window_windowing")
    page_window_render = import_module("quantum_circuit_drawer.managed.page_window_render")
    matplotlib_axes = import_module("quantum_circuit_drawer.renderers._matplotlib_axes")
    matplotlib_text = import_module("quantum_circuit_drawer.renderers._matplotlib_text")
    matplotlib_connections = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_connections"
    )
    matplotlib_gates = import_module("quantum_circuit_drawer.renderers._matplotlib_gates")

    assert page_window_controls.__name__.endswith("_controls")
    assert page_window_windowing.__name__.endswith("_windowing")
    assert page_window_render.__name__.endswith("_render")
    assert matplotlib_axes.__name__.endswith("_axes")
    assert matplotlib_text.__name__.endswith("_text")
    assert matplotlib_connections.__name__.endswith("_connections")
    assert matplotlib_gates.__name__.endswith("_gates")


def test_fourth_pass_adapter_and_viewport_private_helpers_are_importable() -> None:
    myqlm_conversion = import_module("quantum_circuit_drawer.adapters._myqlm_conversion")
    myqlm_resolver = import_module("quantum_circuit_drawer.adapters._myqlm_resolver")
    qiskit_classical = import_module("quantum_circuit_drawer.adapters._qiskit_classical")
    qiskit_control_flow = import_module("quantum_circuit_drawer.adapters._qiskit_control_flow")
    adaptive_paging = import_module("quantum_circuit_drawer.managed._adaptive_paging")

    assert myqlm_conversion.__name__.endswith("_conversion")
    assert myqlm_resolver.__name__.endswith("_resolver")
    assert qiskit_classical.__name__.endswith("_classical")
    assert qiskit_control_flow.__name__.endswith("_control_flow")
    assert adaptive_paging.__name__.endswith("_adaptive_paging")


def test_third_pass_matplotlib_primitives_facade_reexports_split_helpers() -> None:
    from quantum_circuit_drawer.renderers._matplotlib_axes import (
        _add_patch_artist,
        _add_text_artist,
        finalize_axes,
        prepare_axes,
    )
    from quantum_circuit_drawer.renderers._matplotlib_connections import (
        draw_barriers,
        draw_connections,
        draw_wires,
    )
    from quantum_circuit_drawer.renderers._matplotlib_gates import (
        draw_controls,
        draw_gate_annotation,
        draw_gate_box,
        draw_gate_label,
        draw_measurement_box,
        draw_measurement_symbol,
        draw_swaps,
        draw_text,
        draw_x_target_circles,
        draw_x_target_segments,
    )
    from quantum_circuit_drawer.renderers._matplotlib_text import (
        _build_gate_text_fitting_context,
        _fit_gate_text_font_size_with_context,
        _GateTextCache,
        trim_gate_text_fit_cache,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        _add_patch_artist as facade_add_patch_artist,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        _add_text_artist as facade_add_text_artist,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        _build_gate_text_fitting_context as facade_build_gate_text_fitting_context,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        _fit_gate_text_font_size_with_context as facade_fit_gate_text_font_size_with_context,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        _GateTextCache as facade_gate_text_cache,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_barriers as facade_draw_barriers,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_connections as facade_draw_connections,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_controls as facade_draw_controls,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_gate_annotation as facade_draw_gate_annotation,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_gate_box as facade_draw_gate_box,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_gate_label as facade_draw_gate_label,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_measurement_box as facade_draw_measurement_box,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_measurement_symbol as facade_draw_measurement_symbol,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_swaps as facade_draw_swaps,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_text as facade_draw_text,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_wires as facade_draw_wires,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_x_target_circles as facade_draw_x_target_circles,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        draw_x_target_segments as facade_draw_x_target_segments,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        finalize_axes as facade_finalize_axes,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        prepare_axes as facade_prepare_axes,
    )
    from quantum_circuit_drawer.renderers.matplotlib_primitives import (
        trim_gate_text_fit_cache as facade_trim_gate_text_fit_cache,
    )

    assert facade_gate_text_cache is _GateTextCache
    assert facade_add_patch_artist is _add_patch_artist
    assert facade_add_text_artist is _add_text_artist
    assert facade_prepare_axes is prepare_axes
    assert facade_finalize_axes is finalize_axes
    assert facade_trim_gate_text_fit_cache is trim_gate_text_fit_cache
    assert facade_build_gate_text_fitting_context is _build_gate_text_fitting_context
    assert facade_fit_gate_text_font_size_with_context is _fit_gate_text_font_size_with_context
    assert facade_draw_wires is draw_wires
    assert facade_draw_connections is draw_connections
    assert facade_draw_barriers is draw_barriers
    assert facade_draw_gate_box is draw_gate_box
    assert facade_draw_gate_label is draw_gate_label
    assert facade_draw_controls is draw_controls
    assert facade_draw_swaps is draw_swaps
    assert facade_draw_measurement_box is draw_measurement_box
    assert facade_draw_measurement_symbol is draw_measurement_symbol
    assert facade_draw_text is draw_text
    assert facade_draw_gate_annotation is draw_gate_annotation
    assert facade_draw_x_target_circles is draw_x_target_circles
    assert facade_draw_x_target_segments is draw_x_target_segments


def test_second_pass_3d_renderer_and_layout_helpers_are_importable() -> None:
    import quantum_circuit_drawer.layout._engine_3d_classical as engine_3d_classical
    import quantum_circuit_drawer.layout._engine_3d_metrics as engine_3d_metrics
    import quantum_circuit_drawer.layout._engine_3d_operations as engine_3d_operations
    import quantum_circuit_drawer.layout._engine_3d_topology as engine_3d_topology
    from quantum_circuit_drawer.layout.engine_3d import LayoutEngine3D
    from quantum_circuit_drawer.renderers.matplotlib_renderer_3d import (
        _MANAGED_3D_VIEWPORT_BOUNDS_ATTR,
        MatplotlibRenderer3D,
    )

    renderer_3d_viewport = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_viewport"
    )
    renderer_3d_geometry = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_geometry"
    )
    renderer_3d_text = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_text"
    )
    renderer_3d_hover = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_hover"
    )
    renderer_3d_segments = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_segments"
    )

    assert LayoutEngine3D.__name__ == "LayoutEngine3D"
    assert MatplotlibRenderer3D.__name__ == "MatplotlibRenderer3D"
    assert isinstance(_MANAGED_3D_VIEWPORT_BOUNDS_ATTR, str)
    assert renderer_3d_viewport.__name__.endswith("_viewport")
    assert renderer_3d_geometry.__name__.endswith("_geometry")
    assert renderer_3d_text.__name__.endswith("_text")
    assert renderer_3d_hover.__name__.endswith("_hover")
    assert renderer_3d_segments.__name__.endswith("_segments")
    assert engine_3d_topology.__name__.endswith("_topology")
    assert engine_3d_operations.__name__.endswith("_operations")
    assert engine_3d_metrics.__name__.endswith("_metrics")
    assert engine_3d_classical.__name__.endswith("_classical")


def test_save_matplotlib_figure_creates_parent_directories(sandbox_tmp_path: Path) -> None:
    figure = plt.figure()
    output = sandbox_tmp_path / "nested" / "exported.png"

    save_matplotlib_figure(figure, output)

    assert output.is_file()
    plt.close(figure)


def test_save_matplotlib_figure_wraps_save_errors() -> None:
    figure = plt.figure()

    def fail_savefig(self: Figure, *args: object, **kwargs: object) -> None:
        del self, args, kwargs
        raise OSError("disk full")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(Figure, "savefig", fail_savefig)
    try:
        with pytest.raises(RenderingError, match="disk full"):
            save_matplotlib_figure(figure, Path("ignored.png"))
    finally:
        monkeypatch.undo()
        plt.close(figure)
