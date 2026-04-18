# Benchmarking quick report

Date: 2026-04-18 (UTC).

## Commands used

```bash
python - <<'PY'
import enum, runpy, sys
if not hasattr(enum, 'StrEnum'):
    class StrEnum(str, enum.Enum):
        pass
    enum.StrEnum = StrEnum
sys.argv = [
    'scripts/benchmark_render.py',
    '--benchmark', 'synthetic',
    '--wires', '16',
    '--layers', '120',
    '--repeats', '2',
    '--json',
]
runpy.run_path('scripts/benchmark_render.py', run_name='__main__')
PY
```

```bash
python - <<'PY'
import enum, runpy, sys
if not hasattr(enum, 'StrEnum'):
    class StrEnum(str, enum.Enum):
        pass
    enum.StrEnum = StrEnum
sys.argv = ['scripts/benchmark_render.py', '--benchmark', 'demo-suite', '--repeats', '1', '--json']
runpy.run_path('scripts/benchmark_render.py', run_name='__main__')
PY
```

## Results

- Synthetic (`16 wires`, `120 layers`, `2 repeats`):
  - `prepare_seconds`: `0.051631`
  - `layout_seconds`: `0.050947`
  - `render_seconds`: `0.560968`
  - `full_draw_seconds`: `0.755692`
- Synthetic (post render-loop cleanup, same parameters):
  - `prepare_seconds`: `0.042781`
  - `layout_seconds`: `0.051780`
  - `render_seconds`: `0.543077`
  - `full_draw_seconds`: `0.785808`
- Synthetic (post IR fast-path in pipeline, same parameters):
  - `prepare_seconds`: `0.041082`
  - `layout_seconds`: `0.050105`
  - `render_seconds`: `0.545838`
  - `full_draw_seconds`: `0.735114`
- Demo suite:
  - Framework demo runs were discovered correctly, but all entries failed in this environment due to missing optional dependencies (`qiskit`, `cirq`, `pennylane`, `qat`).

## Notes

- The benchmark CLI now supports:
  - `--benchmark synthetic` (default)
  - `--benchmark demo --demo-id ...`
  - `--benchmark demo-suite`
- `demo-suite` continues running even when one demo fails, and returns per-demo error payloads.
