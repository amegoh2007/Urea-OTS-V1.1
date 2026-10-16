"""The console window's routing — `ureasim.hmi.main_window` — to faceplates and the instructor panel.

Pinned on a bridge with no server: a click opens the element's faceplate, a second click on the
same instrument raises it rather than opening another, closing it frees the instrument; a stream
hotspot says the inspector is not built; the Instructor menu shows for the instructor role only;
the trend window opens once and takes trendable tags; a click is a release without a drag.
"""

from __future__ import annotations

from ureasim.hmi.bridge import EngineBridge
from ureasim.hmi.main_window import MainWindow

LIC = {"t": "ind", "tag": "LIC-323501", "bind": "RECIRC_323.C003.LIC_323501.pv", "u": "%"}


def test_one_faceplate_per_instrument_and_the_instructor_menu(qapp):
    bridge = EngineBridge("console")
    win = MainWindow(bridge)
    win.on_element_activated(LIC)
    face = win._faceplates["LIC-323501"]
    win.on_element_activated(dict(LIC, t="bar"))
    assert list(win._faceplates) == ["LIC-323501"] and win._faceplates["LIC-323501"] is face
    face.close()
    qapp.processEvents()
    qapp.sendPostedEvents(None, 0)
    assert "LIC-323501" not in win._faceplates
    win.on_element_activated({"t": "strm", "tag": "S0305", "stream": "S0305"})
    assert "stream not published" in win.statusBar().currentMessage()
    assert not win._instructor_menu.menuAction().isVisible()
    win.on_role_changed("instructor")
    assert win._instructor_menu.menuAction().isVisible()
    # The single-machine console (decided 2026-10-07) runs the exercise too.
    win.on_role_changed("operator")
    assert not win._instructor_menu.menuAction().isVisible()
    win.on_role_changed("superuser")
    assert win._instructor_menu.menuAction().isVisible()
    win.open_instructor_panel()
    assert win._instructor is not None and win._instructor.isVisible()
    win._instructor.close()
    bridge.close()
    win.close()


def test_the_trend_window_opens_once_and_takes_trendable_tags(qapp):
    """View > Trend window: one per console, raised when open; a trendable element's tag lands in
    its first free pen; a bar (trendable, but no pen of its own) and an unbound tag are not
    trendable; the window closes with the console."""
    bridge = EngineBridge("console")
    win = MainWindow(bridge)
    trend = win.open_trend("LIC-323501")
    assert win.open_trend() is trend and trend.slots[0].source.tag == "LIC-323501"
    assert win.trendable(LIC) and not win.trendable({"t": "bar", "tag": "LI-NOPE"})
    assert not win.trendable({"t": "strm", "tag": "S0305"})
    win.on_element_dragged({"t": "strm", "tag": "S0305"})          # not trendable: no drag
    win.close()
    qapp.sendPostedEvents(None, 0)
    assert win._trend is None


def test_a_click_is_a_release_without_a_drag(qapp):
    """An overlay opens its faceplate on release, as V1's browser click did; a press that moves
    past the drag distance asks for a drag instead, and opens nothing."""
    from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtWidgets import QApplication
    from ureasim.hmi.widgets.base import OverlayWidget

    w = OverlayWidget({"t": "ind", "tag": "TI-1", "x": 10, "y": 10})
    activated, dragged = [], []
    w.activated.connect(activated.append)
    w.drag_requested.connect(dragged.append)

    def ev(kind, pos, buttons=Qt.MouseButton.LeftButton):
        p = QPointF(pos)
        return QMouseEvent(kind, p, p, Qt.MouseButton.LeftButton, buttons,
                           Qt.KeyboardModifier.NoModifier)

    w.mousePressEvent(ev(QEvent.Type.MouseButtonPress, QPoint(5, 5)))
    assert activated == []
    w.mouseReleaseEvent(ev(QEvent.Type.MouseButtonRelease, QPoint(5, 5),
                           Qt.MouseButton.NoButton))
    assert len(activated) == 1 and dragged == []
    far = QPoint(5 + QApplication.startDragDistance() + 1, 5)
    w.mousePressEvent(ev(QEvent.Type.MouseButtonPress, QPoint(5, 5)))
    w.mouseMoveEvent(ev(QEvent.Type.MouseMove, far))
    w.mouseReleaseEvent(ev(QEvent.Type.MouseButtonRelease, far, Qt.MouseButton.NoButton))
    assert len(activated) == 1 and len(dragged) == 1
