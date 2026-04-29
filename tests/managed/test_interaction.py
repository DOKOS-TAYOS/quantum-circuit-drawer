from __future__ import annotations

from collections.abc import Callable

from matplotlib.backend_bases import KeyEvent, key_press_handler
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.cbook import CallbackRegistry
from matplotlib.figure import Figure

from quantum_circuit_drawer.managed.interaction import (
    install_managed_default_key_handler_filter,
    install_managed_tab_focus_bindings,
    is_cycle_topology_key,
    is_previous_topology_key,
    managed_key_name,
    restore_managed_canvas_focus,
)


class _DummyTkWidget:
    def __init__(self) -> None:
        self.bindings: dict[str, object] = {}
        self.focus_calls = 0

    def bind(self, sequence: str, callback: object, add: str | None = None) -> None:
        self.bindings[sequence] = callback

    def focus_set(self) -> None:
        self.focus_calls += 1


class _DummyTkCanvas:
    def __init__(self) -> None:
        self.widget = _DummyTkWidget()
        self.key_press_events: list[object] = []
        self.callbacks = CallbackRegistry()
        self.mouse_grabber = None

    def get_tk_widget(self) -> _DummyTkWidget:
        return self.widget

    def inaxes(self, xy: tuple[int, int]) -> None:
        return None

    def key_press(self, event: object) -> None:
        self.key_press_events.append(event)

    def mpl_connect(
        self,
        event_name: str,
        callback: Callable[[KeyEvent], None],
    ) -> int:
        return int(self.callbacks.connect(event_name, callback))


class _DummyQtCanvas:
    def __init__(self) -> None:
        self.focus_calls = 0

    def setFocus(self) -> None:
        self.focus_calls += 1


class _DummyToolbar:
    def __init__(self) -> None:
        self.back_calls = 0
        self.forward_calls = 0
        self.home_calls = 0
        self.save_calls = 0

    def back(self) -> None:
        self.back_calls += 1

    def forward(self) -> None:
        self.forward_calls += 1

    def home(self) -> None:
        self.home_calls += 1

    def save_figure(self) -> None:
        self.save_calls += 1


class _DummyManager:
    def __init__(self, canvas: FigureCanvasAgg, toolbar: _DummyToolbar) -> None:
        self.toolbar = toolbar
        self.key_press_handler_id = int(
            canvas.callbacks.connect(
                "key_press_event",
                lambda event: key_press_handler(event, canvas=canvas, toolbar=toolbar),
            )
        )


def test_managed_key_name_normalizes_iso_left_tab_to_shift_tab() -> None:
    canvas = FigureCanvasAgg(Figure())
    event = KeyEvent("key_press_event", canvas, key="iso_left_tab")

    assert managed_key_name(event) == "shift+tab"


def test_topology_shortcut_helpers_distinguish_t_from_shift_t() -> None:
    canvas = FigureCanvasAgg(Figure())
    next_event = KeyEvent("key_press_event", canvas, key="t")
    previous_event = KeyEvent("key_press_event", canvas, key="shift+t")
    uppercase_previous_event = KeyEvent("key_press_event", canvas, key="T")

    assert is_cycle_topology_key(next_event) is True
    assert is_previous_topology_key(next_event) is False
    assert is_cycle_topology_key(previous_event) is False
    assert is_previous_topology_key(previous_event) is True
    assert is_cycle_topology_key(uppercase_previous_event) is False
    assert is_previous_topology_key(uppercase_previous_event) is True


def test_restore_managed_canvas_focus_prefers_tk_widget_focus() -> None:
    canvas = _DummyTkCanvas()

    restore_managed_canvas_focus(canvas)

    assert canvas.widget.focus_calls == 1


def test_restore_managed_canvas_focus_falls_back_to_qt_style_canvas_focus() -> None:
    canvas = _DummyQtCanvas()

    restore_managed_canvas_focus(canvas)

    assert canvas.focus_calls == 1


def test_install_managed_tab_focus_bindings_forward_tab_keys_and_keep_focus() -> None:
    canvas = _DummyTkCanvas()
    observed_keys: list[str] = []

    canvas.mpl_connect(
        "key_press_event",
        lambda event: observed_keys.append(managed_key_name(event)),
    )

    install_managed_tab_focus_bindings(canvas)
    install_managed_tab_focus_bindings(canvas)

    assert set(canvas.widget.bindings) == {
        "<Tab>",
        "<Shift-Tab>",
        "<ISO_Left_Tab>",
        "<Control-Tab>",
        "<Control-Shift-Tab>",
        "<Control-ISO_Left_Tab>",
    }
    assert canvas.widget.bindings["<Tab>"](object()) == "break"
    assert canvas.widget.bindings["<Shift-Tab>"](object()) == "break"
    assert canvas.widget.bindings["<ISO_Left_Tab>"](object()) == "break"
    assert canvas.widget.bindings["<Control-Tab>"](object()) == "break"
    assert canvas.widget.bindings["<Control-Shift-Tab>"](object()) == "break"
    assert canvas.widget.bindings["<Control-ISO_Left_Tab>"](object()) == "break"
    assert observed_keys == [
        "tab",
        "shift+tab",
        "shift+tab",
        "ctrl+tab",
        "ctrl+shift+tab",
        "ctrl+shift+tab",
    ]
    assert canvas.widget.focus_calls == 6


def test_install_managed_default_key_handler_filter_blocks_reserved_toolbar_navigation_keys() -> (
    None
):
    figure = Figure()
    canvas = FigureCanvasAgg(figure)
    toolbar = _DummyToolbar()
    manager = _DummyManager(canvas, toolbar)
    setattr(canvas, "manager", manager)

    install_managed_default_key_handler_filter(
        canvas,
        blocked_keys={"left", "right", "home"},
    )

    canvas.callbacks.process("key_press_event", KeyEvent("key_press_event", canvas, key="left"))
    canvas.callbacks.process("key_press_event", KeyEvent("key_press_event", canvas, key="right"))
    canvas.callbacks.process("key_press_event", KeyEvent("key_press_event", canvas, key="home"))
    canvas.callbacks.process("key_press_event", KeyEvent("key_press_event", canvas, key="s"))

    assert toolbar.back_calls == 0
    assert toolbar.forward_calls == 0
    assert toolbar.home_calls == 0
    assert toolbar.save_calls == 1
