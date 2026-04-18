# Demo 3D Topology Menu And Smaller Figure Defaults Design

## Summary

Adjust the bundled demos so they are more usable on a normal screen and automatically showcase the new 3D topology selector:

- reduce the default demo `figsize`
- keep `--figsize` as a manual override
- enable `topology_menu=True` automatically whenever a demo runs with `--view 3d`

The goal is to make the demos fit better on screen while making the new 3D feature visible by default.

## Goals

- Make demo windows open at a more compact default size.
- Keep the demo command line simple.
- Ensure 3D demos expose the topology menu automatically.
- Reuse the shared example plumbing instead of patching individual demo files.
- Keep saved-output and non-interactive demo behavior unchanged.

## Non-goals

- No new dedicated CLI flag for the topology menu in the first version.
- No per-demo custom size presets.
- No different default `figsize` values for each framework.
- No change to the current rule that 3D demos use page mode rather than slider mode.

## Options Considered

### 1. Enable the menu automatically in 3D and shrink the shared default `figsize`

Update the shared example helpers so all 3D demos pass `topology_menu=True`, and reduce the shared default figure size for demos.

Pros:

- one central change point
- minimal API surface for the demos
- makes the new 3D feature visible immediately
- fixes the oversized default window in the simplest possible way

Cons:

- 2D demos also inherit the smaller default size

Recommendation: choose this option.

### 2. Use different default sizes for 2D and 3D demos

Pros:

- more tailored default sizing

Cons:

- more branching in the shared demo code
- more test cases and docs complexity
- unnecessary for the current goal

Rejected for now.

### 3. Add explicit `--topology-menu` and `--no-topology-menu` flags

Pros:

- maximum flexibility

Cons:

- more CLI surface for a demo feature that should already "do the right thing"
- more documentation and validation for little practical gain

Rejected for now.

## Chosen Design

### Shared demo defaults

Lower `DEFAULT_DEMO_FIGSIZE` in `examples/_shared.py` from the current large default to a more compact one.

The first implementation should use:

- `DEFAULT_DEMO_FIGSIZE = (10.0, 5.5)`

This is small enough to fit more comfortably on common laptop screens while still leaving room for labels and hover interaction.

### CLI behavior

Keep the current CLI contract:

- `--figsize WIDTH HEIGHT` still overrides the default
- `--view 2d|3d` still controls the renderer
- `--topology` still matters only in 3D

No new menu-specific flag is added in this change.

### Render options for 3D demos

When `request.view == "3d"`, the shared render options should include:

- `view="3d"`
- `topology=request.topology`
- `direct=False`
- `topology_menu=True`

When `request.view == "2d"`, demo behavior stays unchanged and should not pass `topology_menu`.

### Saved and non-interactive runs

Do not add special handling in the example code for `--output` or non-interactive usage.

The demos should rely on the library's existing behavior:

- interactive managed 3D demo windows show the menu
- saved-output and non-interactive runs still render correctly, without trying to force a menu into unsuitable contexts

## Code Organization

### Primary change point

Make the behavior change in `examples/_shared.py`, because that is the single place that:

- defines the shared demo defaults
- parses the common render arguments
- builds the render options passed to `draw_quantum_circuit(...)`

This keeps the change small and avoids duplicating logic across:

- `examples/run_demo.py`
- individual framework demo files

### Tests

Update the shared demo-support and runner tests so they assert:

- the new default `figsize`
- `topology_menu=True` appears in 3D demo draw options
- 2D demo options remain unchanged apart from the smaller default size

## Documentation

Update `examples/README.md` to reflect:

- the smaller default demo window size
- that 3D demos now show the topology selector automatically
- that `--figsize` remains available if the user wants a larger or smaller window

## Testing

Add or update focused tests for:

- `DEFAULT_DEMO_FIGSIZE == (10.0, 5.5)`
- `build_render_options(...)` including `topology_menu=True` in 3D
- `render_example(...)` forwarding `topology_menu=True` for 3D demos
- demo runner defaults and namespace normalization using the new default size
- existing smoke tests continuing to work for saved 3D runs

## Open Decisions Resolved

- The menu is enabled automatically in demo 3D mode.
- There is no new CLI flag for the menu.
- The demos use one smaller shared default figure size.
- Manual `--figsize` overrides remain supported.
