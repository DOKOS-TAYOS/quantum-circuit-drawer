# Managed Additional Shortcuts Design

Date: 2026-04-27
Status: Approved in conversation, pending final spec review

## Goal

Extend the existing managed keyboard shortcut support with additional navigation and selection shortcuts for managed Matplotlib circuit figures.

This change builds on the already approved managed shortcut feature and should:

- keep using the existing `keyboard_shortcuts: bool = True` public option
- avoid adding new public configuration fields
- work only in managed `pages_controls` and `slider` modes
- support both 2D and 3D managed views where the action makes sense
- preserve current click, drag, and text-input behavior

## Public API

No new public API is added.

The new shortcuts are controlled by the existing typed field in [src/quantum_circuit_drawer/config.py](C:/Users/alejandro.mata/Documents/quantum-circuit-drawer/src/quantum_circuit_drawer/config.py):

- `keyboard_shortcuts: bool = True`

If `keyboard_shortcuts=False`, both the previously added shortcuts and the new shortcuts in this document must stay disabled.

## Scope

### Included

- 2D `pages_controls`
- 2D `slider`
- 3D `pages_controls`
- 3D `slider`

### Not included now

- `pages`
- `full`
- caller-owned axes
- configurable custom keymaps
- camera-specific 3D shortcuts

## Interaction Rules

### Shared rules

- `Tab` selects the next visible expandable block.
- `Shift+Tab` selects the previous visible expandable block.
- If the current selection is not visible, `Tab` starts from the first visible expandable block and `Shift+Tab` starts from the last visible expandable block.
- If no visible expandable block exists, `Tab` and `Shift+Tab` do nothing.
- `Esc` clears the current selection.
- If focus is inside a managed `TextBox`, all keyboard shortcuts should be ignored.
- Selection traversal should follow the current visual order of the rendered view rather than a hidden global ordering.

### 2D and 3D `pages_controls`

- `Home`: jump to the first page
- `End`: jump to the last valid page
- `PageUp`: move backward by a large page step
- `PageDown`: move forward by a large page step
- `+`: show one more visible page
- `-`: show one fewer visible page
- `Tab` / `Shift+Tab`: traverse visible expandable blocks
- `Esc`: clear selection

Large page steps should use `max(1, visible_page_count)` pages so the shortcut feels proportional to the current view.

### 2D `slider`

- `Home`: jump to the first horizontal window
- `End`: jump to the last horizontal window
- `PageUp`: move backward by a large horizontal step
- `PageDown`: move forward by a large horizontal step
- `+`: increase the number of visible wires
- `-`: decrease the number of visible wires
- `Tab` / `Shift+Tab`: traverse visible expandable blocks in the current scene
- `Esc`: clear selection

Large horizontal steps should move by approximately one visible window while keeping a small overlap, so repeated jumps remain readable.

### 3D `slider`

- `Home`: jump to the first horizontal window
- `End`: jump to the last horizontal window
- `PageUp`: move backward by a large horizontal step
- `PageDown`: move forward by a large horizontal step
- `+`: no action
- `-`: no action
- `Tab` / `Shift+Tab`: traverse visible expandable blocks in the current scene
- `Esc`: clear selection

## Internal Design

Extend the shared keyboard interaction helpers in [src/quantum_circuit_drawer/managed/interaction.py](C:/Users/alejandro.mata/Documents/quantum-circuit-drawer/src/quantum_circuit_drawer/managed/interaction.py) instead of scattering new key handling into each controller.

Recommended additions:

- helpers to normalize `Tab`, `Shift+Tab`, `Esc`, `Home`, `End`, `PageUp`, `PageDown`, `+`, and `-`
- helpers to clear managed selection without changing expansion state
- helpers to jump to absolute start and end for page windows and sliders
- helpers to compute and apply large navigation steps
- helpers to traverse visible expandable operations in visual order
- helpers to adjust visible-page count or visible-wire count where supported

The managed controllers should stay thin and continue delegating behavior from:

- [src/quantum_circuit_drawer/managed/page_window.py](C:/Users/alejandro.mata/Documents/quantum-circuit-drawer/src/quantum_circuit_drawer/managed/page_window.py)
- [src/quantum_circuit_drawer/managed/slider_2d.py](C:/Users/alejandro.mata/Documents/quantum-circuit-drawer/src/quantum_circuit_drawer/managed/slider_2d.py)
- [src/quantum_circuit_drawer/managed/page_window_3d.py](C:/Users/alejandro.mata/Documents/quantum-circuit-drawer/src/quantum_circuit_drawer/managed/page_window_3d.py)
- [src/quantum_circuit_drawer/managed/slider_3d.py](C:/Users/alejandro.mata/Documents/quantum-circuit-drawer/src/quantum_circuit_drawer/managed/slider_3d.py)

## Error Handling And Compatibility

- Unsupported shortcuts in a given mode should do nothing.
- Unknown keys should do nothing.
- `+` and `-` must remain no-ops in 3D `slider`.
- `Esc` should clear selection only, without expanding or collapsing anything.
- Existing double-click toggle behavior must remain unchanged.
- Existing arrow-key behavior must remain unchanged.
- Existing 3D drag protection must remain unchanged.

## Testing

Add focused tests for:

- `Tab` and `Shift+Tab` traversal in `pages_controls` and `slider`
- traversal fallback when the current selection is no longer visible
- `Esc` clearing the current selection
- `Home` and `End` jumping to the absolute beginning and end
- `PageUp` and `PageDown` using large navigation steps
- `+` and `-` changing visible pages in `pages_controls`
- `+` and `-` changing visible wires in 2D `slider`
- `+` and `-` staying as no-ops in 3D `slider`
- keyboard shortcuts still ignored while a managed text input is active
- existing arrow shortcuts and double-click toggles still behaving as before

Tests should extend the current managed interaction test style rather than introducing a new test harness.

## Documentation Notes

- Update the user-facing docs that describe managed interaction behavior.
- Update `CHANGELOG.md` when the implementation lands.
- Keep the documentation wording clear that these shortcuts are available by default through `keyboard_shortcuts=True`.
