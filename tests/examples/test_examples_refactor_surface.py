from __future__ import annotations

from pathlib import Path

EXAMPLES_DIR = Path("examples")
DIRECT_EXAMPLE_FILES = (
    "caller_managed_axes_showcase.py",
    "cirq_native_controls_showcase.py",
    "cirq_qaoa.py",
    "cirq_random.py",
    "cli_export_showcase.py",
    "compare_circuits_composite_modes.py",
    "compare_circuits_multi_transpile.py",
    "compare_circuits_qiskit_transpile.py",
    "compare_histograms_ideal_vs_sampled.py",
    "compare_histograms_multi_series.py",
    "cudaq_kernel_showcase.py",
    "cudaq_random.py",
    "diagnostics_showcase.py",
    "histogram_binary_order.py",
    "histogram_cirq_result.py",
    "histogram_count_order.py",
    "histogram_cudaq_sample.py",
    "histogram_interactive_large.py",
    "histogram_marginal.py",
    "histogram_multi_register.py",
    "histogram_myqlm_result.py",
    "histogram_pennylane_probs.py",
    "histogram_quasi.py",
    "histogram_quasi_nonnegative.py",
    "histogram_result_index.py",
    "histogram_top_k.py",
    "histogram_uniform_reference.py",
    "ir_basic_workflow.py",
    "myqlm_random.py",
    "myqlm_structural_showcase.py",
    "openqasm_showcase.py",
    "pennylane_qaoa.py",
    "pennylane_random.py",
    "pennylane_terminal_outputs_showcase.py",
    "public_api_utilities_showcase.py",
    "qiskit_2d_exploration_showcase.py",
    "qiskit_3d_exploration_showcase.py",
    "qiskit_backend_topology_showcase.py",
    "qiskit_composite_modes_showcase.py",
    "qiskit_control_flow_showcase.py",
    "qiskit_qaoa.py",
    "qiskit_random.py",
    "style_accessible_showcase.py",
)
HELPER_PATTERNS = (
    "examples._shared",
    "examples._histogram_shared",
    "examples._compare_shared",
    "from _shared import",
    "from _histogram_shared import",
    "from _compare_shared import",
    "from examples._families import",
    "from _families import",
    "run_example(",
    "run_histogram_example(",
    "run_compare_example(",
)


def test_direct_example_scripts_do_not_depend_on_legacy_demo_helpers() -> None:
    for module_name in DIRECT_EXAMPLE_FILES:
        source = (EXAMPLES_DIR / module_name).read_text(encoding="utf-8")
        for pattern in HELPER_PATTERNS:
            assert pattern not in source, (
                f"{module_name} still depends on legacy helper pattern {pattern!r}"
            )


def test_runner_entrypoints_do_not_import_legacy_demo_helper_layers() -> None:
    for module_name in ("run_demo.py", "run_histogram_demo.py", "run_compare_demo.py"):
        source = (EXAMPLES_DIR / module_name).read_text(encoding="utf-8")
        assert "examples._shared" not in source
        assert "examples._histogram_shared" not in source
        assert "examples._compare_shared" not in source


def test_primary_docs_surface_latex_export_and_direct_examples() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    getting_started = Path("docs/getting-started.md").read_text(encoding="utf-8")
    user_guide = Path("docs/user-guide.md").read_text(encoding="utf-8")
    examples_readme = Path("examples/README.md").read_text(encoding="utf-8")

    assert "circuit_to_latex" in readme
    assert "circuit_to_latex" in getting_started
    assert "circuit_to_latex" in user_guide
    assert "direct scripts" in examples_readme.lower()
    assert "runners are still handy" in examples_readme.lower()
