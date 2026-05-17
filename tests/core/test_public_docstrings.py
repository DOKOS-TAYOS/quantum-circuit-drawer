from __future__ import annotations

import inspect
import pydoc

import quantum_circuit_drawer as qcd
import quantum_circuit_drawer.api as public_api
import quantum_circuit_drawer.histogram as histogram_api
import quantum_circuit_drawer.ir as qir

_PUBLIC_METHODS: dict[str, tuple[str, ...]] = {
    "CircuitBuilder": (
        "gate",
        "i",
        "h",
        "x",
        "y",
        "z",
        "s",
        "sdg",
        "t",
        "tdg",
        "sx",
        "sxdg",
        "p",
        "rx",
        "ry",
        "rz",
        "rxx",
        "ryy",
        "rzz",
        "rzx",
        "u",
        "u2",
        "cx",
        "cy",
        "cz",
        "ch",
        "cp",
        "crx",
        "cry",
        "crz",
        "cu",
        "swap",
        "barrier",
        "reset",
        "measure",
        "measure_all",
        "build",
    ),
    "CircuitAnalysisResult": ("to_dict",),
    "CircuitCompareResult": ("save", "to_dict"),
    "DrawResult": ("save", "save_all_pages", "to_dict"),
    "HardwareTopology": ("from_coupling_map", "from_qiskit_backend", "from_graph"),
    "HistogramCompareResult": ("save", "to_dict", "to_csv"),
    "HistogramResult": ("save", "to_dict", "to_csv"),
    "HoverOptions": ("to_mapping",),
    "LatexResult": ("to_dict",),
    "LogCapture": ("to_dicts",),
}

_MAIN_PUBLIC_API_DOCS: dict[str, tuple[object, tuple[str, ...], tuple[str, ...]]] = {
    "draw_quantum_circuit": (
        public_api.draw_quantum_circuit,
        (
            "mode",
            "show",
            "framework",
            "view",
            "topology_qubits",
            "config",
            "ax",
        ),
        ("Direct kwargs are the small, common API", "styling"),
    ),
    "analyze_quantum_circuit": (
        public_api.analyze_quantum_circuit,
        (
            "mode",
            "framework",
            "view",
            "composite_mode",
            "topology",
            "config",
        ),
        ("Direct kwargs are the small, common API", "does not render"),
    ),
    "circuit_to_latex": (
        public_api.circuit_to_latex,
        (
            "backend",
            "mode",
            "framework",
            "composite_mode",
            "config",
        ),
        ("Direct kwargs are the small, common API", "always prepares a 2D"),
    ),
    "compare_circuits": (
        public_api.compare_circuits,
        (
            "mode",
            "show",
            "framework",
            "left_title",
            "show_summary",
            "config",
            "axes",
        ),
        ("Direct kwargs are the small, common API", "Per-side"),
    ),
    "plot_histogram": (
        histogram_api.plot_histogram,
        (
            "kind",
            "mode",
            "sort",
            "state_label_mode",
            "reverse_bits",
            "top_k",
            "config",
            "ax",
        ),
        ("Direct kwargs are the small, common API", "Advanced appearance"),
    ),
    "compare_histograms": (
        histogram_api.compare_histograms,
        (
            "kind",
            "sort",
            "top_k",
            "left_label",
            "series_labels",
            "config",
            "ax",
        ),
        ("Direct kwargs are the small, common API", "Hover"),
    ),
}


def test_public_api_docstrings_explain_user_facing_objects() -> None:
    failures: list[str] = []

    for module in (qcd, qir):
        _collect_public_docstring_failures(module, failures)

    assert failures == []


def _collect_public_docstring_failures(module: object, failures: list[str]) -> None:
    module_name = getattr(module, "__name__", repr(module))
    for name in getattr(module, "__all__"):
        if name == "__version__":
            continue
        obj = getattr(module, name)
        if inspect.isfunction(obj):
            min_length = 180
            markers = ("Args:", "Returns:")
        elif inspect.isclass(obj):
            min_length = 140
            markers = ("Attributes:", "Values:", "Raised when")
        else:
            continue
        doc = inspect.getdoc(obj) or ""
        if len(doc) < min_length:
            failures.append(f"{module_name}.{name}: docstring is too short")
        if not any(marker in doc for marker in markers):
            failures.append(f"{module_name}.{name}: docstring lacks one of {markers}")


def test_public_methods_have_useful_docstrings() -> None:
    failures: list[str] = []

    for class_name, method_names in _PUBLIC_METHODS.items():
        class_obj = getattr(qcd, class_name)
        for method_name in method_names:
            method = getattr(class_obj, method_name)
            doc = inspect.getdoc(method) or ""
            if len(doc) < 80:
                failures.append(f"{class_name}.{method_name}: docstring is too short")
            if method_name.startswith(("to_", "save")) and "Returns:" not in doc:
                failures.append(f"{class_name}.{method_name}: docstring lacks Returns")

    assert failures == []


def test_installed_style_help_for_main_public_apis_is_complete() -> None:
    failures: list[str] = []

    for name, (
        facade_function,
        expected_kwargs,
        expected_snippets,
    ) in _MAIN_PUBLIC_API_DOCS.items():
        root_function = getattr(qcd, name)
        root_signature = inspect.signature(root_function)
        facade_signature = inspect.signature(facade_function)
        rendered = pydoc.render_doc(root_function, renderer=pydoc.plaintext)

        if root_signature != facade_signature:
            failures.append(f"{name}: root and facade signatures differ")
        if "Args:" not in rendered or "Returns:" not in rendered:
            failures.append(f"{name}: help output lacks Args/Returns sections")
        for kwarg in expected_kwargs:
            if kwarg not in rendered:
                failures.append(f"{name}: help output does not mention {kwarg!r}")
        for snippet in expected_snippets:
            if snippet not in rendered:
                failures.append(f"{name}: help output lacks snippet {snippet!r}")

    assert failures == []
