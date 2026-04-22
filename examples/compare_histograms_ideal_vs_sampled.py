"""Compare ideal and sampled histogram workflows with the public compare API."""

from __future__ import annotations

try:
    from examples._compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        parse_compare_example_args,
    )
except ImportError:
    from _compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        parse_compare_example_args,
    )

from quantum_circuit_drawer import HistogramCompareConfig, compare_histograms


def build_demo(request: CompareExampleRequest) -> CompareDemoPayload:
    """Build a compare payload for ideal versus sampled histogram data."""

    del request
    return CompareDemoPayload(
        compare_kind="histograms",
        left_data={
            "000": 0.125,
            "001": 0.125,
            "010": 0.125,
            "011": 0.125,
            "100": 0.125,
            "101": 0.125,
            "110": 0.125,
            "111": 0.125,
        },
        right_data={
            "000": 17,
            "001": 13,
            "010": 9,
            "011": 18,
            "100": 12,
            "101": 10,
            "110": 15,
            "111": 14,
        },
        config=HistogramCompareConfig(
            left_label="Ideal",
            right_label="Sampled",
            sort="delta_desc",
            show=False,
        ),
    )


def main() -> None:
    """Run the histogram compare demo as a normal user-facing script."""

    request = parse_compare_example_args(
        description="Compare an ideal distribution against sampled counts.",
    )
    payload = build_demo(request)
    base_config = payload.config
    config = HistogramCompareConfig(
        left_label=request.left_label or base_config.left_label,
        right_label=request.right_label or base_config.right_label,
        sort=base_config.sort if request.sort is None else request.sort,
        top_k=base_config.top_k if request.top_k is None else request.top_k,
        show=request.show,
        output_path=request.output,
        figsize=request.figsize,
    )
    result = compare_histograms(
        payload.left_data,
        payload.right_data,
        config=config,
    )
    if hasattr(result.figure, "set_label"):
        result.figure.set_label("compare-histograms-ideal-vs-sampled")
    if request.output is not None:
        print(f"Saved compare-histograms-ideal-vs-sampled to {request.output}")


if __name__ == "__main__":
    main()
