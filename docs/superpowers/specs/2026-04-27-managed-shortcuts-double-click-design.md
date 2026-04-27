# Managed Shortcuts And Double Click Design

Date: 2026-04-27
Status: Approved in conversation, pending final spec review

## Goal

Add configurable interactive shortcuts and double-click block toggling for managed Matplotlib circuit figures.

The feature should:

- work in both 2D and 3D managed figures
- apply keyboard shortcuts only to `pages_controls` and `slider`
- apply double-click block toggling now to `pages_controls` and `slider`
- keep both capabilities enabled by default
- allow callers to disable them explicitly from the public API

## Public API

Add two typed fields to `CircuitRenderOptions` in [src/quantum_circuit_drawer/config.py](C:/Users/alejandro.mata/Documents/quantum-circuit-drawer/src/quantum_circuit_drawer/config.py):

- `keyboard_shortcuts: bool = True`
- `double_click_toggle: bool = True`

Validation should follow the existing `bool` validation pattern used by other render options.

These options are accepted for every draw request, but their runtime effect is limited to managed figures where interactive state exists.

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
- non-managed static rendering paths

The internal design should keep the double-click logic reusable so it can be extended to other modes later without rewriting the interaction rules.

## Interaction Rules

### Shared rules

- `Enter` and `Space` toggle the currently selected expandable block.
- If there is no selected operation, `Enter` and `Space` do nothing.
- Double click on an expandable operation toggles the owning block.
- If the clicked operation is not expandable, double click does nothing.
- Double click should first resolve the clicked operation and then apply the toggle for that operation.
- If focus is inside a managed `TextBox`, keyboard shortcuts should be ignored.

### 2D `pages_controls`

- `Left`: previous page
- `Right`: next page
- `Up`: one fewer visible page
- `Down`: one more visible page
- `Enter` / `Space`: toggle selected block
- Double click: toggle clicked block

### 2D `slider`

- `Left`: move the horizontal viewport backward
- `Right`: move the horizontal viewport forward
- `Up`: move the vertical viewport upward when vertical overflow exists
- `Down`: move the vertical viewport downward when vertical overflow exists
- `Enter` / `Space`: toggle selected block
- Double click: toggle clicked block

### 3D `pages_controls`

- `Left`: previous page
- `Right`: next page
- `Up`: one fewer visible page
- `Down`: one more visible page
- `Enter` / `Space`: toggle selected block
- Double click: toggle clicked block

### 3D `slider`

- `Left`: move the horizontal window backward
- `Right`: move the horizontal window forward
- `Up`: no action
- `Down`: no action
- `Enter` / `Space`: toggle selected block
- Double click: toggle clicked block

## 3D Safety Rules

3D views already distinguish between a click and a camera drag. The new double-click behavior must preserve that safety boundary:

- camera rotation or drag must not trigger selection changes by accident
- double click should only act on a clean click target
- existing press/release drag thresholds should remain the source of truth for 3D click validity

## Internal Design

Use small shared managed-interaction helpers instead of duplicating event logic across the four managed controllers.

Recommended structure:

- one helper layer to resolve whether a key should trigger an action
- one helper layer to apply navigation actions to a specific managed state type
- one helper layer to resolve double-click toggle behavior from a clicked or selected operation

The helpers should be used from:

- [src/quantum_circuit_drawer/managed/page_window.py](C:/Users/alejandro.mata/Documents/quantum-circuit-drawer/src/quantum_circuit_drawer/managed/page_window.py)
- [src/quantum_circuit_drawer/managed/slider_2d.py](C:/Users/alejandro.mata/Documents/quantum-circuit-drawer/src/quantum_circuit_drawer/managed/slider_2d.py)
- [src/quantum_circuit_drawer/managed/page_window_3d.py](C:/Users/alejandro.mata/Documents/quantum-circuit-drawer/src/quantum_circuit_drawer/managed/page_window_3d.py)
- [src/quantum_circuit_drawer/managed/slider_3d.py](C:/Users/alejandro.mata/Documents/quantum-circuit-drawer/src/quantum_circuit_drawer/managed/slider_3d.py)

The implementation should reuse existing state methods whenever possible:

- page stepping helpers already used by button controls
- viewport movement helpers already used by sliders
- `toggle_selected_block()`
- `select_operation(...)`

## Configuration Flow

The new public options should be resolved through the normal draw config path and propagated into the managed rendering setup so each managed controller knows whether to register:

- `key_press_event`
- double-click handling on the existing click path

If an option is disabled, the corresponding callback should either not be registered or should early-return with no effect.

## Testing

Add focused tests for:

- public config validation for `keyboard_shortcuts` and `double_click_toggle`
- 2D `pages_controls` key navigation
- 2D `slider` key navigation, including vertical movement only when relevant
- 3D `pages_controls` key navigation
- 3D `slider` key navigation
- `Enter` / `Space` toggle behavior with and without selection
- double-click toggle behavior in 2D and 3D
- disabled-option behavior for both flags
- keyboard shortcuts ignored while a managed text input is active
- 3D drag safety preserved when double-click support is enabled

Tests should stay mode-specific and reuse existing managed-event test patterns instead of introducing a separate testing style.

## Error Handling And Compatibility

- Unknown keys should do nothing.
- Unsupported actions for a given mode should do nothing.
- Static modes should ignore the new features without failing.
- Existing managed button and click behavior should remain unchanged when the new options are left at their default values.

## Implementation Notes

- Prefer helper reuse over a new large abstraction layer.
- Keep the public API small and explicit.
- Preserve typed function signatures and existing repo style.
- Update user-facing docs and `CHANGELOG.md` when implementation lands.
