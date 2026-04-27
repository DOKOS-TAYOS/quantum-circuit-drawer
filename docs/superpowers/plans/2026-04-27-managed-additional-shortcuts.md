# Managed Additional Shortcuts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend managed keyboard shortcuts with `Tab`, `Shift+Tab`, `Esc`, `Home`, `End`, `PageUp`, `PageDown`, and `+/-` across managed `pages_controls` and `slider` views without adding new public API.

**Architecture:** Keep the existing public `keyboard_shortcuts` flag unchanged and expand the shared managed interaction helpers in `managed/interaction.py`. Controllers in `page_window.py`, `slider_2d.py`, `page_window_3d.py`, and `slider_3d.py` stay thin: they normalize keys, delegate to shared helpers, and keep their mode-specific navigation logic local.

**Tech Stack:** Python, Matplotlib managed events, pytest, ruff

---

## File Structure

- Modify: `src/quantum_circuit_drawer/managed/interaction.py`
  - Extend shared key normalization and helper functions for traversal, clear-selection, home/end, large-step navigation, and `+/-`.
- Modify: `src/quantum_circuit_drawer/managed/page_window.py`
  - Hook extra managed page-window keyboard actions for 2D `pages_controls`.
- Modify: `src/quantum_circuit_drawer/managed/slider_2d.py`
  - Hook extra managed slider keyboard actions for 2D `slider`, including visible-wire adjustments.
- Modify: `src/quantum_circuit_drawer/managed/page_window_3d.py`
  - Hook extra managed page-window keyboard actions for 3D `pages_controls`.
- Modify: `src/quantum_circuit_drawer/managed/slider_3d.py`
  - Hook extra managed slider keyboard actions for 3D `slider`.
- Modify: `tests/managed/test_2d_exploration.py`
  - Add regression tests for the new 2D keyboard behaviors.
- Modify: `tests/managed/test_3d_exploration.py`
  - Add regression tests for the new 3D keyboard behaviors.
- Modify: `README.md`
  - Mention the expanded managed keyboard shortcut set.
- Modify: `docs/api.md`
  - Document that the extra shortcuts are part of `keyboard_shortcuts=True`.
- Modify: `docs/extended_guide.md`
  - Update managed interaction guidance.
- Modify: `CHANGELOG.md`
  - Add a user-facing entry for the shortcut expansion.

### Task 1: Add failing 2D shortcut tests

**Files:**
- Modify: `tests/managed/test_2d_exploration.py`
- Test: `tests/managed/test_2d_exploration.py`

- [ ] **Step 1: Write the failing tests for `pages_controls` extra shortcuts**

```python
def test_page_window_shortcuts_support_home_end_page_jump_tab_and_escape() -> None:
    result = public_draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        config=build_public_draw_config(
            mode=DrawMode.PAGES_CONTROLS,
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    try:
        page_window = get_page_window(result.primary_figure)
        assert page_window is not None

        _dispatch_key_press(result.primary_figure, "end")
        assert page_window.start_page == page_window.total_pages - 1

        _dispatch_key_press(result.primary_figure, "home")
        assert page_window.start_page == 0

        _dispatch_key_press(result.primary_figure, "pagedown")
        assert page_window.start_page == min(
            page_window.total_pages - 1,
            max(1, page_window.visible_page_count),
        )

        page_window.select_operation("op:0")
        _dispatch_key_press(result.primary_figure, "escape")
        assert page_window.exploration is not None
        assert page_window.exploration.selected_operation_id is None
    finally:
        plt.close(result.primary_figure)
```

```python
def test_page_window_shortcuts_support_visible_page_plus_minus_and_tab_traversal() -> None:
    figure, axes = draw_quantum_circuit(
        _semantic_controls_circuits()[0],
        expanded_semantic_ir=_semantic_controls_circuits()[1],
        style={"max_page_width": 3.0},
        page_window=True,
        show=False,
    )

    try:
        page_window = cast(Managed2DPageWindowState | None, get_page_window(figure))
        assert page_window is not None

        _dispatch_key_press(figure, "down")
        _dispatch_key_press(figure, "+")
        assert page_window.visible_page_count >= 2

        _dispatch_key_press(figure, "-")
        assert page_window.visible_page_count >= 1

        _dispatch_key_press(figure, "tab")
        assert page_window.exploration is not None
        assert page_window.exploration.selected_operation_id is not None

        current_selection = page_window.exploration.selected_operation_id
        _dispatch_key_press(figure, "shift+tab")
        assert page_window.exploration.selected_operation_id is not None
        assert page_window.exploration.selected_operation_id != current_selection
    finally:
        plt.close(figure)
```

- [ ] **Step 2: Write the failing tests for `slider` extra shortcuts**

```python
def test_slider_shortcuts_support_home_end_page_jump_and_visible_qubits() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=20, wire_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    try:
        page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None
        assert page_slider.max_start_column > 0

        _dispatch_key_press(figure, "end")
        assert page_slider.start_column == page_slider.max_start_column

        _dispatch_key_press(figure, "home")
        assert page_slider.start_column == 0

        before_visible_qubits = page_slider.visible_qubits
        _dispatch_key_press(figure, "+")
        assert page_slider.visible_qubits >= before_visible_qubits

        _dispatch_key_press(figure, "-")
        assert page_slider.visible_qubits >= 1
    finally:
        plt.close(figure)
```

```python
def test_slider_shortcuts_support_tab_traversal_and_escape() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_controls_circuits()
    figure, axes = draw_quantum_circuit(
        current_semantic_ir,
        expanded_semantic_ir=expanded_semantic_ir,
        style={"max_page_width": 3.0},
        page_slider=True,
        show=False,
    )

    try:
        page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None

        _dispatch_key_press(figure, "tab")
        assert page_slider.exploration is not None
        assert page_slider.exploration.selected_operation_id is not None

        _dispatch_key_press(figure, "escape")
        assert page_slider.exploration.selected_operation_id is None
    finally:
        plt.close(figure)
```

- [ ] **Step 3: Run the focused 2D tests to verify they fail**

Run: `C:\Users\alejandro.mata\Documents\quantum-circuit-drawer\.venv\Scripts\python.exe -m pytest tests\managed\test_2d_exploration.py -q`

Expected: FAIL in the new `home`, `end`, `pagedown`, `tab`, `escape`, `+`, or `-` assertions because those shortcuts are not implemented yet.

- [ ] **Step 4: Commit the red tests**

```bash
git add tests/managed/test_2d_exploration.py
git commit -m "test: cover additional managed 2d shortcuts"
```

### Task 2: Implement shared helpers and 2D shortcut behavior

**Files:**
- Modify: `src/quantum_circuit_drawer/managed/interaction.py`
- Modify: `src/quantum_circuit_drawer/managed/page_window.py`
- Modify: `src/quantum_circuit_drawer/managed/slider_2d.py`
- Test: `tests/managed/test_2d_exploration.py`

- [ ] **Step 1: Extend the shared interaction helper with named predicates and traversal helpers**

```python
def is_clear_selection_key(event: KeyEvent) -> bool:
    return managed_key_name(event) == "escape"


def is_next_selection_key(event: KeyEvent) -> bool:
    return managed_key_name(event) == "tab"


def is_previous_selection_key(event: KeyEvent) -> bool:
    return managed_key_name(event) == "shift+tab"


def is_home_key(event: KeyEvent) -> bool:
    return managed_key_name(event) == "home"


def is_end_key(event: KeyEvent) -> bool:
    return managed_key_name(event) == "end"


def is_page_up_key(event: KeyEvent) -> bool:
    return managed_key_name(event) == "pageup"


def is_page_down_key(event: KeyEvent) -> bool:
    return managed_key_name(event) == "pagedown"


def is_plus_key(event: KeyEvent) -> bool:
    return managed_key_name(event) in {"+", "plus"}


def is_minus_key(event: KeyEvent) -> bool:
    return managed_key_name(event) in {"-", "minus"}
```

- [ ] **Step 2: Add 2D page-window helpers for absolute moves, large jumps, selection traversal, and clear-selection**

```python
def clear_selection(self) -> None:
    self.select_operation(None)


def show_first_page(self) -> None:
    self.start_page = 0
    _render_current_window(self)
    _sync_inputs(self)


def show_last_page(self) -> None:
    self.start_page = max(0, self.total_pages - 1)
    self.visible_page_count = _clamp_visible_page_count(
        self.visible_page_count,
        total_pages=self.total_pages,
        start_page=self.start_page,
    )
    _render_current_window(self)
    _sync_inputs(self)


def step_page_large(self, direction: int) -> None:
    self.step_page(direction * max(1, self.visible_page_count))
```

```python
if is_home_key(event):
    state.show_first_page()
    return
if is_end_key(event):
    state.show_last_page()
    return
if is_page_up_key(event):
    state.step_page_large(-1)
    return
if is_page_down_key(event):
    state.step_page_large(1)
    return
if is_plus_key(event):
    state.step_visible_pages(1)
    return
if is_minus_key(event):
    state.step_visible_pages(-1)
    return
if is_clear_selection_key(event):
    state.clear_selection()
    return
```

- [ ] **Step 3: Add 2D slider helpers for absolute moves, large jumps, visible-qubit changes, selection traversal, and clear-selection**

```python
def clear_selection(self) -> None:
    self.select_operation(None)


def show_first_window(self) -> None:
    self.show_start_column(0)


def show_last_window(self) -> None:
    self.show_start_column(self.max_start_column)


def step_start_column_large(self, direction: int) -> None:
    large_step = max(1, self.max_start_column // 2)
    self.show_start_column(self.start_column + (direction * large_step))
```

```python
if is_home_key(event):
    state.show_first_window()
    return
if is_end_key(event):
    state.show_last_window()
    return
if is_page_up_key(event):
    state.step_start_column_large(-1)
    return
if is_page_down_key(event):
    state.step_start_column_large(1)
    return
if is_plus_key(event):
    _set_visible_qubits(state, state.visible_qubits + 1)
    return
if is_minus_key(event):
    _set_visible_qubits(state, state.visible_qubits - 1)
    return
if is_clear_selection_key(event):
    state.clear_selection()
    return
```

- [ ] **Step 4: Run the focused 2D tests to verify they pass**

Run: `C:\Users\alejandro.mata\Documents\quantum-circuit-drawer\.venv\Scripts\python.exe -m pytest tests\managed\test_2d_exploration.py -q`

Expected: PASS for the new 2D shortcut tests and no regressions in the existing 2D exploration suite.

- [ ] **Step 5: Commit the 2D implementation**

```bash
git add src/quantum_circuit_drawer/managed/interaction.py src/quantum_circuit_drawer/managed/page_window.py src/quantum_circuit_drawer/managed/slider_2d.py tests/managed/test_2d_exploration.py
git commit -m "feat: add additional managed 2d shortcuts"
```

### Task 3: Add failing 3D shortcut tests

**Files:**
- Modify: `tests/managed/test_3d_exploration.py`
- Test: `tests/managed/test_3d_exploration.py`

- [ ] **Step 1: Write the failing tests for 3D `pages_controls`**

```python
def test_3d_page_window_shortcuts_support_home_end_page_jump_tab_and_escape() -> None:
    result = public_draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        config=build_public_draw_config(
            mode=DrawMode.PAGES_CONTROLS,
            view="3d",
            topology="line",
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    try:
        page_window = get_page_window(result.primary_figure)
        assert page_window is not None

        _dispatch_key_press(result.primary_figure, "end")
        assert page_window.start_page == page_window.total_pages - 1

        _dispatch_key_press(result.primary_figure, "home")
        assert page_window.start_page == 0

        _dispatch_key_press(result.primary_figure, "tab")
        assert page_window.exploration is not None
        assert page_window.exploration.selected_operation_id is not None

        _dispatch_key_press(result.primary_figure, "escape")
        assert page_window.exploration.selected_operation_id is None
    finally:
        plt.close(result.primary_figure)
```

- [ ] **Step 2: Write the failing tests for 3D `slider`**

```python
def test_3d_slider_shortcuts_support_home_end_page_jump_tab_and_escape() -> None:
    figure, axes = draw_quantum_circuit(
        _semantic_controls_circuits()[0],
        expanded_semantic_ir=_semantic_controls_circuits()[1],
        view="3d",
        topology="line",
        topology_menu=True,
        page_slider=True,
        show=False,
    )

    try:
        page_slider = cast(Managed3DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None

        _dispatch_key_press(figure, "end")
        assert page_slider.start_column == page_slider.max_start_column

        _dispatch_key_press(figure, "home")
        assert page_slider.start_column == 0

        _dispatch_key_press(figure, "tab")
        assert page_slider.exploration is not None
        assert page_slider.exploration.selected_operation_id is not None

        selected_operation_id = page_slider.exploration.selected_operation_id
        _dispatch_key_press(figure, "shift+tab")
        assert page_slider.exploration.selected_operation_id is not None

        _dispatch_key_press(figure, "escape")
        assert page_slider.exploration.selected_operation_id is None

        before_column = page_slider.start_column
        _dispatch_key_press(figure, "+")
        assert page_slider.start_column == before_column
    finally:
        plt.close(figure)
```

- [ ] **Step 3: Run the focused 3D tests to verify they fail**

Run: `C:\Users\alejandro.mata\Documents\quantum-circuit-drawer\.venv\Scripts\python.exe -m pytest tests\managed\test_3d_exploration.py -q`

Expected: FAIL in the new `home`, `end`, `tab`, `escape`, or `+` no-op assertions because the new key handling does not exist yet.

- [ ] **Step 4: Commit the red tests**

```bash
git add tests/managed/test_3d_exploration.py
git commit -m "test: cover additional managed 3d shortcuts"
```

### Task 4: Implement 3D behavior and refresh docs

**Files:**
- Modify: `src/quantum_circuit_drawer/managed/page_window_3d.py`
- Modify: `src/quantum_circuit_drawer/managed/slider_3d.py`
- Modify: `README.md`
- Modify: `docs/api.md`
- Modify: `docs/extended_guide.md`
- Modify: `CHANGELOG.md`
- Test: `tests/managed/test_3d_exploration.py`

- [ ] **Step 1: Add 3D page-window helpers for absolute moves, large jumps, selection traversal, and clear-selection**

```python
def clear_selection(self) -> None:
    self.select_operation(None)


def show_first_page(self) -> None:
    self.start_page = 0
    _render_current_window(self)
    _sync_inputs(self)


def show_last_page(self) -> None:
    self.start_page = max(0, self.total_pages - 1)
    self.visible_page_count = _clamp_visible_page_count(
        self.visible_page_count,
        total_pages=self.total_pages,
        start_page=self.start_page,
    )
    _render_current_window(self)
    _sync_inputs(self)
```

```python
if is_home_key(event):
    state.show_first_page()
    return
if is_end_key(event):
    state.show_last_page()
    return
if is_page_up_key(event):
    state.step_page(-max(1, state.visible_page_count))
    return
if is_page_down_key(event):
    state.step_page(max(1, state.visible_page_count))
    return
if is_plus_key(event):
    state.step_visible_pages(1)
    return
if is_minus_key(event):
    state.step_visible_pages(-1)
    return
if is_clear_selection_key(event):
    state.clear_selection()
    return
```

- [ ] **Step 2: Add 3D slider helpers for absolute moves, large jumps, selection traversal, and clear-selection while keeping `+/-` as no-ops**

```python
def clear_selection(self) -> None:
    self.select_operation(None)


def show_first_window(self) -> None:
    self.show_start_column(0)


def show_last_window(self) -> None:
    self.show_start_column(self.max_start_column)


def step_start_column_large(self, direction: int) -> None:
    self.show_start_column(self.start_column + (direction * max(1, self.window_size - 1)))
```

```python
if is_home_key(event):
    state.show_first_window()
    return
if is_end_key(event):
    state.show_last_window()
    return
if is_page_up_key(event):
    state.step_start_column_large(-1)
    return
if is_page_down_key(event):
    state.step_start_column_large(1)
    return
if is_clear_selection_key(event):
    state.clear_selection()
    return
```

- [ ] **Step 3: Update the user-facing docs and changelog**

```markdown
- `keyboard_shortcuts=True` now also enables `Tab`, `Shift+Tab`, `Esc`, `Home`, `End`, `PageUp`, `PageDown`, and `+/-` in managed `pages_controls` and `slider` views.
```

- [ ] **Step 4: Run the focused 3D tests to verify they pass**

Run: `C:\Users\alejandro.mata\Documents\quantum-circuit-drawer\.venv\Scripts\python.exe -m pytest tests\managed\test_3d_exploration.py -q`

Expected: PASS for the new 3D shortcut tests and no regressions in the existing 3D exploration suite.

- [ ] **Step 5: Commit the 3D implementation and docs**

```bash
git add src/quantum_circuit_drawer/managed/page_window_3d.py src/quantum_circuit_drawer/managed/slider_3d.py tests/managed/test_3d_exploration.py README.md docs/api.md docs/extended_guide.md CHANGELOG.md
git commit -m "feat: extend managed shortcuts"
```

### Task 5: Final verification and cleanup

**Files:**
- Modify: `docs/superpowers/plans/2026-04-27-managed-additional-shortcuts.md`

- [ ] **Step 1: Run the focused regression suite**

Run: `C:\Users\alejandro.mata\Documents\quantum-circuit-drawer\.venv\Scripts\python.exe -m pytest tests\core\test_api_v2_contracts.py tests\managed\test_2d_exploration.py tests\managed\test_3d_exploration.py -q`

Expected: PASS with the existing API contract suite and both managed exploration suites green.

- [ ] **Step 2: Run repository formatting and lint fixes**

Run: `C:\Users\alejandro.mata\Documents\quantum-circuit-drawer\.venv\Scripts\python.exe -m ruff check . --fix`

Expected: PASS with no remaining lint violations.

Run: `C:\Users\alejandro.mata\Documents\quantum-circuit-drawer\.venv\Scripts\python.exe -m ruff format .`

Expected: PASS with all touched files formatted.

- [ ] **Step 3: Run the focused regression suite again after formatting**

Run: `C:\Users\alejandro.mata\Documents\quantum-circuit-drawer\.venv\Scripts\python.exe -m pytest tests\core\test_api_v2_contracts.py tests\managed\test_2d_exploration.py tests\managed\test_3d_exploration.py -q`

Expected: PASS with no post-format regressions.

- [ ] **Step 4: Commit the verified final state**

```bash
git add src/quantum_circuit_drawer/managed/interaction.py src/quantum_circuit_drawer/managed/page_window.py src/quantum_circuit_drawer/managed/slider_2d.py src/quantum_circuit_drawer/managed/page_window_3d.py src/quantum_circuit_drawer/managed/slider_3d.py tests/managed/test_2d_exploration.py tests/managed/test_3d_exploration.py README.md docs/api.md docs/extended_guide.md CHANGELOG.md
git commit -m "chore: finalize managed shortcut expansion"
```
