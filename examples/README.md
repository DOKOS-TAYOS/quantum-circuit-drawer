# Examples

The example scripts now follow the public `DrawConfig` / `DrawMode` API.

## Main modes

Example CLI mode names match the public draw modes:

- `pages`
- `pages_controls`
- `slider`
- `full`

## Useful commands

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --list
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology grid
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --list
.venv/bin/python examples/run_demo.py --demo qiskit-random --mode pages
.venv/bin/python examples/run_demo.py --demo qiskit-random --mode pages_controls
.venv/bin/python examples/run_demo.py --demo qiskit-random --mode slider
.venv/bin/python examples/run_demo.py --demo qiskit-random --mode full
.venv/bin/python examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology grid
```

## Notes

- `pages` is the notebook-friendly mode
- `pages_controls` is the script-friendly managed viewer
- `slider` stays available in 2D and 3D
- `full` renders the whole circuit without paging
- in 3D, `pages_controls` can also expose the topology selector
