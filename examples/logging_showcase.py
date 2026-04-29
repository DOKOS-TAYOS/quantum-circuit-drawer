"""Show practical logging profiles for day-to-day debugging."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    CircuitBuilder,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    HistogramConfig,
    HistogramMode,
    HistogramViewOptions,
    LogCapture,
    LogFormat,
    LogProfile,
    OutputOptions,
    capture_logs,
    configure_logging,
    draw_quantum_circuit,
    plot_histogram,
)

DEFAULT_CIRCUIT_FIGSIZE: tuple[float, float] = (11.0, 6.0)
DEFAULT_HISTOGRAM_FIGSIZE: tuple[float, float] = (10.5, 5.4)


def build_circuit(*, qubit_count: int, motif_count: int) -> object:
    """Build a deterministic circuit large enough to exercise managed modes."""

    builder = CircuitBuilder(qubit_count, qubit_count, name="logging_showcase")
    builder.h(0).cx(0, 1).barrier(0, 1, 2)
    for step in range(motif_count):
        target = step % qubit_count
        partner = (target + 1) % qubit_count
        builder.rx(0.12 * float(step + 1), target)
        builder.cz(target, partner)
    builder.measure_all()
    return builder.build()


def build_counts(*, bit_width: int) -> dict[str, int]:
    """Return deterministic counts with enough bins to trigger histogram controls."""

    return {
        format(index, f"0{bit_width}b"): ((index * 11) % 37) + ((index * 3) % 9) + 2
        for index in range(2**bit_width)
    }


def main() -> None:
    """Configure logging, draw one circuit, and plot one histogram."""

    args = _parse_args()
    configure_logging(
        level=args.level,
        format=args.format,
        profile=args.profile,
    )
    print(
        f"Logging configured with profile={args.profile}, level={args.level}, format={args.format}."
    )

    circuit = build_circuit(qubit_count=args.qubits, motif_count=args.motifs)
    draw_result = None
    histogram_result = None
    try:
        with capture_logs(
            level=args.level,
            profile=args.profile,
        ) as capture:
            draw_result = draw_quantum_circuit(
                circuit,
                config=DrawConfig(
                    side=DrawSideConfig(
                        render=CircuitRenderOptions(
                            mode=DrawMode.PAGES_CONTROLS,
                            view="2d",
                        )
                    ),
                    output=OutputOptions(
                        show=args.show,
                        figsize=DEFAULT_CIRCUIT_FIGSIZE,
                    ),
                ),
            )
            histogram_result = plot_histogram(
                build_counts(bit_width=args.histogram_bits),
                config=HistogramConfig(
                    view=HistogramViewOptions(mode=HistogramMode.INTERACTIVE),
                    output=OutputOptions(
                        show=args.show,
                        figsize=DEFAULT_HISTOGRAM_FIGSIZE,
                    ),
                ),
            )
        _print_capture_summary(capture)
        if args.show:
            print(
                "Interact with the circuit and histogram windows to see "
                "`interactive.*` events in real time."
            )
        else:
            print(
                "Run again with --show on an interactive Matplotlib backend "
                "to see `interactive.*` events while you explore the figures."
            )
    finally:
        if draw_result is not None:
            release_rendered_result(draw_result)
        if histogram_result is not None:
            release_rendered_result(histogram_result)


def _print_capture_summary(capture: LogCapture) -> None:
    entry_count = len(capture.entries)
    record_count = len(capture.records)
    if not capture.entries:
        print(f"Captured {record_count} raw record(s) and 0 structured event(s).")
        return
    first_entry = capture.entries[0]
    print(
        f"Captured {record_count} raw record(s) and {entry_count} structured event(s). "
        f"First event={first_entry.event}, request_id={first_entry.request_id}."
    )
    first_payload = capture.to_dicts()[0]
    print("First structured payload keys: " + ", ".join(sorted(first_payload.keys())))


def _parse_args() -> Namespace:
    parser = ArgumentParser(description="Show practical logging profiles for daily debugging.")
    parser.add_argument(
        "--profile",
        choices=tuple(profile.value for profile in LogProfile),
        default=LogProfile.INTERACTIVE.value,
        help="Logging profile to use.",
    )
    parser.add_argument(
        "--level",
        default="INFO",
        help="Standard logging level such as INFO or DEBUG.",
    )
    parser.add_argument(
        "--format",
        choices=tuple(log_format.value for log_format in LogFormat),
        default=LogFormat.HUMAN.value,
        help="Log output format.",
    )
    parser.add_argument(
        "--qubits", type=int, default=6, help="Number of qubits in the demo circuit."
    )
    parser.add_argument(
        "--motifs",
        type=int,
        default=10,
        help="Extra motifs to append before the final measurements.",
    )
    parser.add_argument(
        "--histogram-bits",
        type=int,
        default=7,
        help="Bit width of the histogram demo data.",
    )
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
