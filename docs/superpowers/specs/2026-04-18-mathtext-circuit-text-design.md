# MathText Circuit Text Design

## Summary

Add an opt-in style flag for Matplotlib MathText in the visible circuit text, with the default enabled:

- `DrawStyle(use_mathtext=True)`
- affects only text drawn on the circuit view
- does not affect hover text

The goal is to improve figure quality for papers without requiring a full external LaTeX installation.

## Goals

- Render gate names, parameters, wire labels, measurement labels, annotations, and visible classical labels with MathText when enabled.
- Keep hover content unchanged and in plain text.
- Preserve cross-platform behavior on Windows and Linux.
- Avoid introducing external `usetex=True` dependencies.

## Non-goals

- No change to hover formatting.
- No change to operation metadata or hover payload contents.
- No promise that arbitrary user strings become mathematically semantic LaTeX; the feature is for nicer circuit rendering, not a general formula engine.

## Options Considered

### 1. Render-only MathText conversion

Convert plain internal labels to MathText only at the final rendering stage.

Pros:

- keeps hover and internal logic untouched
- minimizes risk in adapters and layout code
- easier to disable or refine later

Cons:

- layout width estimation remains heuristic unless adjusted separately

Recommendation: choose this option.

### 2. Store MathText strings in the scene model

Pros:

- scene data directly matches rendered text

Cons:

- leaks render-specific syntax into layout and hover
- increases risk of escaped-text bugs and cache misses

### 3. Enable full LaTeX via Matplotlib `usetex`

Pros:

- highest typographic fidelity

Cons:

- external dependency
- slower
- less robust on Windows

Rejected.

## Chosen Design

### Public API

Add `use_mathtext: bool = True` to `DrawStyle`.

This flag controls only visible circuit text. When `False`, rendering stays in the current plain-text mode.

### Rendering scope

When `use_mathtext=True`, the renderer converts visible labels into MathText-safe strings immediately before drawing:

- gate labels
- gate subtitles / parameters
- wire labels
- measurement labels
- gate annotations
- visible classical connection labels
- equivalent visible text in 3D when shown on the circuit

Hover strings remain plain text in both 2D and 3D.

### Formatting rules

- gate names such as `RZZ`, `CX`, `H` render in upright math text, for example `$\mathrm{RZZ}$`
- parameter text renders in math mode
- arbitrary visible labels such as `q0` or `c[0]` are escaped so MathText does not misinterpret them
- formatting stays lightweight and deterministic; no external LaTeX packages or custom macros

### Conversion boundary

The internal operation text and scene models remain plain strings.

MathText conversion happens in renderer-facing helpers so that:

- hover continues to use plain text
- adapters keep returning simple labels
- existing caches and operation identity stay easier to reason about

## Layout and Performance

### Layout

Current 2D layout width estimation is character-count based. That is acceptable for the first version, but MathText-aware rendering may make some labels slightly wider or narrower than the heuristic predicts.

For the implementation phase, adjust width estimation conservatively so circuit boxes do not become too tight when MathText is enabled.

### Performance

Expected outcome:

- somewhat slower visible-text rendering than plain text
- still acceptable for normal usage and paper export
- hover performance unchanged

Avoid regressions by preserving the current fast paths where practical and by keeping hover text plain.

## 3D Considerations

3D rendering also shows visible circuit text when hover is off. The same `use_mathtext` flag should apply there so 2D and 3D stay consistent.

Hover text in 3D remains plain text.

## Testing

Add focused tests for:

- `DrawStyle(use_mathtext=True)` default behavior
- `DrawStyle(use_mathtext=False)` preserving current plain rendering
- hover text remaining plain
- visible circuit text conversion for 2D
- visible circuit text conversion for 3D
- basic layout safety for representative labels such as `RZZ`, `R_{ZZ}`, `theta`, `q0`, and `c[0]`

## Open Decisions Resolved

- The feature is activable, but the default is `True`.
- Hover text is explicitly excluded.
- MathText is preferred over Matplotlib `usetex`.
