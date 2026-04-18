# 3D Topology Menu Design

## Summary

Add an optional public API flag that shows a topology selector inside managed 3D Matplotlib figures:

- `draw_quantum_circuit(..., view="3d", topology_menu=True)`
- the selector is visible only when the library owns the figure
- invalid topologies stay visible but disabled
- selecting a valid topology updates the 3D view immediately in the same figure

The goal is to let users explore chip layouts interactively without rebuilding the plot by hand.

## Goals

- Add a simple public API switch for an embedded topology menu in 3D.
- Keep the current default behavior unchanged when the menu is not requested.
- Reuse the existing topology and 3D layout engine rather than inventing a second rendering path.
- Make topology availability clear for the current qubit count.
- Keep behavior robust on Windows and Linux with Matplotlib-managed figures.

## Non-goals

- No topology menu in 2D.
- No support for caller-managed axes (`ax=...`) in the first version.
- No support for saved static output (`output=...`) in the first version.
- No new public configuration object beyond the boolean flag for the first version.
- No custom topology authoring UI.

## Options Considered

### 1. Public boolean flag with embedded managed-figure menu

Expose a simple `topology_menu: bool = False` parameter on `draw_quantum_circuit`.

Pros:

- smallest public API change
- matches the existing managed-feature pattern used by `page_slider`
- easy to explain to users
- easy to leave off by default

Cons:

- limited room for future menu customization without adding more API later

Recommendation: choose this option.

### 2. Rich public config object for the topology menu

Expose something like `topology_menu={"visible": True, ...}` or a dataclass.

Pros:

- future flexibility

Cons:

- more API surface now than the feature needs
- adds validation and documentation cost before there is real demand

Rejected for the first version.

### 3. Separate helper API that enhances an existing figure

Expose a second public function that attaches the menu after rendering.

Pros:

- powerful for advanced users

Cons:

- awkward for normal usage
- harder to align with the current draw pipeline
- increases surface area and state management complexity

Rejected for the first version.

## Chosen Design

### Public API

Add `topology_menu: bool = False` to `draw_quantum_circuit`.

This flag is only meaningful for `view="3d"`. When `False`, rendering behavior stays as it is today.

### Runtime rules

- `topology_menu=True` is only valid with `view="3d"`.
- If `view!="3d"` and `topology_menu=True`, raise `ValueError`.
- If `ax is not None`, do not show the menu.
- If `output is not None`, do not show the menu.
- If the active backend is not interactive, do not show the menu.

For the first version, those unsupported runtime combinations should not fail the draw. The circuit should still render normally, just without the menu.

### Menu behavior

The menu lives inside the managed Matplotlib figure in a narrow side panel next to the 3D axes.

The selector lists all currently supported public topologies:

- `line`
- `grid`
- `star`
- `star_tree`
- `honeycomb`

For the current circuit:

- valid topologies are clickable
- invalid topologies are visible but disabled
- the currently active topology is visually selected

When the user selects a valid topology:

- recompute the 3D scene using the same circuit, style, `direct`, and hover settings
- clear and redraw the same `Axes3D`
- preserve the same managed figure rather than creating a new window

## Internal Architecture

### Validation and request flow

Extend the normalized draw request so `topology_menu` is a first-class public option with typed validation.

Validation responsibilities:

- public type validation in `_draw_request.py`
- runtime combination checks in the same place as other draw-time compatibility rules

### Managed rendering integration

Attach the menu only in the managed 3D rendering path in `_draw_managed.py`.

This keeps the behavior aligned with current managed-only features and avoids special cases in caller-owned axes.

The managed 3D path should:

1. create the figure and 3D axes
2. reserve a small figure region for the menu when the menu is active
3. render the initial topology
4. attach callbacks that rebuild the prepared 3D pipeline for a new topology and redraw the existing axes

### Topology availability

Do not duplicate topology constraints in the UI layer.

Instead, the menu logic should determine validity by reusing the existing topology builder rules from `layout/topology_3d.py`. A topology is enabled only if the current circuit quantum-wire count satisfies those rules.

### State ownership

Keep menu state attached to the managed figure, similar to how page-slider metadata is stored today.

Minimum state:

- current topology
- list of valid and invalid topologies for the current circuit
- callback references needed by the widget
- enough pipeline context to rebuild the 3D scene without asking the user for new inputs

### Code organization

The widget and callback logic should live in a small internal helper module rather than making `_draw_managed.py` carry all menu code inline.

That helper owns:

- menu layout
- enabled and disabled visual states
- selection callbacks
- redraw orchestration for topology changes

## UX Notes

- The menu should be opt-in and unobtrusive.
- Disabled topologies should look unavailable without disappearing.
- The feature should feel immediate: click, redraw, updated topology.
- The active selection should stay obvious after each redraw.

## Testing

Add focused tests for:

- public validation of `topology_menu`
- `ValueError` when `topology_menu=True` with `view="2d"`
- managed 3D figures attaching the menu when interactive
- caller-managed axes not attaching the menu
- saved-output and non-interactive cases rendering normally without the menu
- invalid topologies appearing disabled for a given wire count
- selecting a valid topology causing the active scene topology to change
- preserving the same figure and axes objects across topology changes

## Open Decisions Resolved

- The feature is part of the public API.
- Visibility is controlled by a simple boolean flag.
- The first version is managed-figure only.
- Invalid topologies remain visible but disabled.
- Changing topology updates the current 3D view in place.
