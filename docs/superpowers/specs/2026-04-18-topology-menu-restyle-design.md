# Topology Menu Restyle Design

## Goal

Restyle the managed 3D topology menu so it feels integrated with the existing dark viewer while matching the simpler radio-list layout requested by the user.

## Scope

This change only affects the managed interactive 3D topology menu shown when `topology_menu=True`. It does not change topology validation, redraw behavior, or the public API.

## UI design

- Move the topology menu to the lower-left corner of the managed figure.
- Replace the current stacked button look with a compact radio-style option list.
- Keep the current dark visual language:
  - dark panel background
  - light labels
  - current blue accent for the selected topology
- Remove the extra title so the panel is visually quieter.
- Keep all supported topologies visible at once.

## Interaction behavior

- Selecting a valid topology immediately redraws the same managed 3D axes.
- Invalid topologies remain visible but look disabled.
- Clicking a disabled topology does nothing.
- Clicking the already active topology leaves the view unchanged.

## Implementation notes

- Rework `src/quantum_circuit_drawer/_draw_managed_topology_menu.py`.
- Prefer Matplotlib's radio-button style interaction over the current button column.
- Keep the menu state object and redraw flow unchanged where possible.
- Update tests to check the new placement and styling at a state level instead of pixel-perfect rendering.

## Verification

- Add or update tests for menu placement and interactive behavior.
- Run `ruff check . --fix`.
- Run `ruff format .`.
- Run `pytest -q`.
