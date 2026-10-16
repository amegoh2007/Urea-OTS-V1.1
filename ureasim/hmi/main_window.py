"""The console window: tab bar, ten process screens, status bar.

Layout parity with V1
---------------------
    top     a tab bar, one button per screen, in the order `screen_layout.SCREENS` gives
    middle  the active screen, scaled to fit
    bottom  a status bar carrying the health LED, the engine state and the plant clock

Screen navigation works three ways, as it does on the real console and in V1: the tab bar,
a nav hotspot drawn on the graphic, and a right-click screen menu.

Multi-station
-------------
This window is one console among several attached to the same plant. It owns no state: it
renders whatever snapshot arrives and sends operator actions back. Three consequences are
visible to the user:

  * the **role** the server granted is shown in the status bar, because a trainee who
    believes they are an operator but was granted observer will read every refusal as a
    plant fault;
  * every accepted command from **any** station appears in the audit line, so an instructor
    watches trainees work without looking over a shoulder;
  * a refused command says why, in the status bar, rather than doing nothing.

Faceplates and the instructor's panel
-------------------------------------
A left-click opens the element's faceplate (`ureasim.hmi.faceplates`), one per instrument: a
second click raises the one already open. An instructor console has an Instructor menu that opens
the exercise panel (`ureasim.hmi.instructor`). Both render the packet and send commands through the
bridge; neither holds plant state.

The trend window
----------------
View > Trend window (Ctrl+T) opens the multi-pen trend (`ureasim.hmi.trend`), a separate
top-level window, one per console. A trendable element's menu adds its tag ("Trend"), and so does
dragging the element onto the window's plot or one of its rows; the window plots the engine
historian's answer and keeps no samples of its own.

Layout persistence
------------------
An operator may drag an overlay in edit-layout mode. Positions are stored per machine in
`QSettings`, keyed by screen id and element key, and re-applied on start. They are never
written back into `ureasim/data/screen_layout.py`: that file is generated from the drawing
and owns the seed geometry.
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QMimeData, QPoint, QSettings, Qt, pyqtSlot
from PyQt6.QtGui import QAction, QDrag, QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ureasim import __version__
from ureasim.data.screen_layout import OVERLAYS, SCREENS
from ureasim.data.trend import TRENDABLE
from ureasim.hmi.bridge import EngineBridge
from ureasim.hmi import theme
from ureasim.hmi.faceplates import faceplate_for, faceplate_key
from ureasim.hmi.instructor import InstructorPanel
from ureasim.hmi.screen_view import ScreenView
from ureasim.hmi.state_access import BindMap
from ureasim.hmi.trend import TAG_MIME, TrendWindow, trend_sources
from ureasim.net.protocol import EXERCISE_ROLES

#: QSettings scope. Layout is per user, per machine.
SETTINGS_ORG = "UreaSimulator"
SETTINGS_APP = "OTS"
LAYOUT_KEY = "hmi/overlay_positions"


class HealthLed(QLabel):
    """A coloured dot mirroring engine health, as the V1 header LED did."""

    _COLOURS = {
        "ok": theme.HEALTH_OK,
        "warn": theme.HEALTH_WARN,
        "fault": theme.HEALTH_FAULT,
        "idle": theme.HEALTH_IDLE,
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self.set_level("idle")

    def set_level(self, level: str) -> None:
        colour = self._COLOURS.get(level, theme.HEALTH_IDLE)
        self.setStyleSheet(
            f"background:{colour}; border-radius:6px; "
            f"border:1px solid rgba(0,0,0,0.4);")


class MainWindow(QMainWindow):
    """Operator console."""

    def __init__(self, bridge: EngineBridge, parent: QWidget | None = None):
        super().__init__(parent)
        self.bridge = bridge
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

        self.setWindowTitle(f"Urea Plant OTS  —  V{__version__}")
        self.setStyleSheet(f"QMainWindow {{ background:{theme.PAGE_BG}; }}")

        # One bind map across ALL screens, so a tag printed on two drawings reads the same
        # value on both. Built once; every screen consults it as it builds its widgets.
        self._bind_map = BindMap(OVERLAYS)
        # What each tag trends, V1's trend map over the same table.
        self._trend_sources = trend_sources(OVERLAYS)

        self._views: dict[str, ScreenView] = {}
        self._tabs: dict[str, QPushButton] = {}
        self._editing = False
        self._faceplates: dict[str, QWidget] = {}
        self._instructor: InstructorPanel | None = None
        self._trend: TrendWindow | None = None

        self._build_ui()
        self._restore_layout()

        bridge.snapshot.connect(self.on_snapshot)
        bridge.status.connect(self.on_status)
        bridge.audit_event.connect(self.on_audit_event)
        bridge.command_result.connect(self.on_command_result)
        bridge.role_changed.connect(self.on_role_changed)
        bridge.assignment_changed.connect(self.on_assignment_changed)

        self._activate(SCREENS[0][0])

    # ----------------------------------------------------------------------------------
    # Construction
    # ----------------------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget(self)
        column = QVBoxLayout(central)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        column.addWidget(self._build_tab_bar())

        self._stack = QStackedWidget(central)
        for screen_id, _title in SCREENS:
            view = ScreenView(screen_id, OVERLAYS.get(screen_id, []), self._bind_map)
            view.navigate.connect(self._activate)
            view.element_activated.connect(self.on_element_activated)
            view.element_context.connect(self.on_element_context)
            view.element_moved.connect(self.on_element_moved)
            view.element_dragged.connect(self.on_element_dragged)
            self._views[screen_id] = view
            self._stack.addWidget(view)
        column.addWidget(self._stack, 1)

        self.setCentralWidget(central)
        self._build_status_bar()
        self._build_menus()

    def _build_tab_bar(self) -> QWidget:
        bar = QWidget(self)
        bar.setStyleSheet(f"background:{theme.TAB_BAR_BG};")
        row = QHBoxLayout(bar)
        row.setContentsMargins(4, 4, 4, 0)
        row.setSpacing(2)

        font = QFont()
        font.setFamilies(theme.UI_FONT_FAMILIES)
        font.setPixelSize(theme.UI_FONT_PX)
        font.setBold(True)

        for screen_id, title in SCREENS:
            # The tab shows the short screen number; the full title is the tooltip and the
            # status-bar caption. A ten-tab bar with full titles does not fit the stage.
            label = title.split(" ", 1)[0]
            button = QPushButton(label, bar)
            button.setFont(font)
            button.setToolTip(title)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setCheckable(True)
            button.clicked.connect(lambda _checked, sid=screen_id: self._activate(sid))
            self._tabs[screen_id] = button
            row.addWidget(button)
        row.addStretch(1)
        self._style_tabs(SCREENS[0][0])
        return bar

    def _style_tabs(self, active_id: str) -> None:
        for screen_id, button in self._tabs.items():
            active = screen_id == active_id
            button.setChecked(active)
            button.setStyleSheet(
                f"QPushButton {{ padding:6px 12px; border:1px solid "
                f"{theme.TAB_ACTIVE_BORDER if active else theme.TAB_BORDER}; "
                f"border-bottom:none; border-top-left-radius:4px; "
                f"border-top-right-radius:4px; "
                f"background:{theme.BG if active else theme.TAB_BG}; "
                f"color:{theme.TAB_ACTIVE_TEXT if active else theme.TAB_TEXT}; }}"
                f"QPushButton:hover {{ background:{theme.TAB_HOVER_BG}; color:#fff; }}"
            )

    def _build_status_bar(self) -> None:
        bar = QStatusBar(self)
        bar.setStyleSheet(
            f"QStatusBar {{ background:{theme.TAB_BAR_BG}; color:{theme.TAB_TEXT}; }}")

        self._led = HealthLed(bar)
        self._engine_label = QLabel("disconnected", bar)
        self._audit_label = QLabel("", bar)
        self._scope_label = QLabel("", bar)
        self._role_label = QLabel("", bar)
        self._screen_label = QLabel("", bar)

        for w in (self._engine_label, self._audit_label, self._scope_label,
                  self._role_label, self._screen_label):
            f = QFont()
            f.setFamilies(theme.UI_FONT_FAMILIES)
            f.setPixelSize(theme.UI_FONT_PX)
            w.setFont(f)
            w.setStyleSheet(f"color:{theme.TAB_TEXT};")
        # The audit line is the quietest thing on the bar: it is glanceable context about
        # what other stations are doing, not a message this operator has to act on.
        self._audit_label.setStyleSheet(f"color:{theme.SIGNAL};")

        bar.addWidget(self._led)
        bar.addWidget(self._engine_label, 1)
        bar.addWidget(self._audit_label, 2)
        bar.addPermanentWidget(self._scope_label)
        bar.addPermanentWidget(self._role_label)
        bar.addPermanentWidget(self._screen_label)
        self.setStatusBar(bar)

    def _build_menus(self) -> None:
        view_menu = self.menuBar().addMenu("&View")

        edit_action = QAction("&Edit layout", self, checkable=True)
        edit_action.setShortcut("Ctrl+E")
        edit_action.toggled.connect(self._set_editing)
        view_menu.addAction(edit_action)

        reset_action = QAction("&Reset layout to drawing", self)
        reset_action.triggered.connect(self._reset_layout)
        view_menu.addAction(reset_action)

        trend_action = QAction("&Trend window", self)
        trend_action.setShortcut("Ctrl+T")
        trend_action.triggered.connect(lambda: self.open_trend())
        view_menu.addAction(trend_action)

        view_menu.addSeparator()
        screens_menu = view_menu.addMenu("&Screens")
        for screen_id, title in SCREENS:
            action = QAction(title, self)
            action.triggered.connect(lambda _c, sid=screen_id: self._activate(sid))
            screens_menu.addAction(action)

        # The instructor's menu, shown once the server has granted the instructor role.
        self._instructor_menu = self.menuBar().addMenu("&Instructor")
        panel_action = QAction("&Exercise panel", self)
        panel_action.setShortcut("Ctrl+I")
        panel_action.triggered.connect(self.open_instructor_panel)
        self._instructor_menu.addAction(panel_action)
        self._instructor_menu.menuAction().setVisible(False)

    # ----------------------------------------------------------------------------------
    # Navigation
    # ----------------------------------------------------------------------------------

    def _activate(self, screen_id: str) -> None:
        view = self._views.get(screen_id)
        if view is None:
            return
        self._stack.setCurrentWidget(view)
        self._style_tabs(screen_id)
        title = dict(SCREENS).get(screen_id, screen_id)
        self._screen_label.setText(title)
        # Push the latest snapshot into the newly shown screen immediately, so it is not
        # blank for up to one refresh period.
        view.update_from(self.bridge.latest)

    # ----------------------------------------------------------------------------------
    # Engine
    # ----------------------------------------------------------------------------------

    @pyqtSlot(object)
    def on_snapshot(self, state: Mapping[str, Any]) -> None:
        """Refresh only the visible screen.

        Updating all ten would cost ten times the work for nine screens nobody is looking
        at. A screen refreshes from `bridge.latest` the moment it is shown.
        """
        current = self._stack.currentWidget()
        if isinstance(current, ScreenView):
            current.update_from(state)

    @pyqtSlot(str, str)
    def on_status(self, text: str, level: str) -> None:
        self._led.set_level(level)
        self._engine_label.setText(text)

    @pyqtSlot(str)
    def on_audit_event(self, text: str) -> None:
        """An accepted command from any station, including this one.

        Kept to a single line: an instructor wants to see that something happened and who
        did it, not to read a log while supervising an exercise.
        """
        self._audit_label.setText(text)

    @pyqtSlot(int, bool, str)
    def on_command_result(self, cmd_id: int, ok: bool, reason: str) -> None:
        """Outcome of a command this console sent.

        A refusal is always shown with its reason - a latched trip, a process interlock, or
        a role that does not allow the action. V1 dropped unknown commands silently, which
        teaches a trainee that the plant ignored them.
        """
        if ok:
            return
        self.statusBar().showMessage(f"REFUSED: {reason}", 6000)

    @pyqtSlot(str)
    def on_assignment_changed(self, text: str) -> None:
        """Show the plant this station holds.

        Blank when unrestricted. A trainee assigned nothing sees it in red: every command
        refused with no visible reason is the worst possible training experience.
        """
        self._scope_label.setText(text)
        colour = theme.HEALTH_FAULT if text == "NO PLANT ASSIGNED" else theme.SIGNAL
        self._scope_label.setStyleSheet(f"color:{colour}; font-weight:bold;")

    @pyqtSlot(str)
    def on_role_changed(self, role: str) -> None:
        """Show the role the SERVER granted, which may not be the one requested."""
        self._role_label.setText(role.upper())
        self._instructor_menu.menuAction().setVisible(
            role in (r.value for r in EXERCISE_ROLES))
        colour = {"superuser": theme.TAB_ACTIVE_TEXT,
                  "instructor": theme.TAB_ACTIVE_TEXT,
                  "operator": theme.HEALTH_OK,
                  "observer": theme.SIGNAL}.get(role, theme.TAB_TEXT)
        self._role_label.setStyleSheet(f"color:{colour}; font-weight:bold;")

    # ----------------------------------------------------------------------------------
    # Element interaction
    # ----------------------------------------------------------------------------------

    @pyqtSlot(object)
    def on_element_activated(self, element: Mapping[str, Any]) -> None:
        """Route a left-click to the element's faceplate, one per instrument.

        Any role may open a faceplate to read it; a command an observer sends is refused by
        the server, with the reason, as any other refusal. A stream hotspot or an analyser opens
        the stream inspector, unless the packet does not publish its stream.
        """
        tag = element.get("tag", "")
        key = faceplate_key(element)
        open_one = self._faceplates.get(key)
        if open_one is not None:
            open_one.raise_()
            open_one.activateWindow()
            return
        face = faceplate_for(element, self.bridge, self)
        if face is None:
            what = ("stream not published"
                    if element.get("t") in ("ae", "strm") else "no faceplate")
            self.statusBar().showMessage(f"{tag}: {what}", 4000)
            return
        self._faceplates[key] = face
        face.destroyed.connect(lambda _o=None, k=key: self._faceplates.pop(k, None))
        face.show()

    def open_instructor_panel(self) -> None:
        """The instructor's exercise panel; the server refuses its commands to any other role."""
        if self._instructor is None:
            self._instructor = InstructorPanel(self.bridge, self)
        self._instructor.show()
        self._instructor.raise_()
        self.bridge.request_exercises()

    def open_trend(self, tag: str | None = None) -> TrendWindow:
        """Open (or raise) this console's trend window, and trend ``tag`` in its first free pen."""
        if self._trend is None:
            self._trend = TrendWindow(self.bridge, self._trend_sources, self.settings)
            self._trend.destroyed.connect(lambda _o=None: setattr(self, "_trend", None))
            self._trend.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._trend.show()
        self._trend.raise_()
        if tag:
            self._trend.add_tag(tag)
        return self._trend

    def trendable(self, element: Mapping[str, Any]) -> bool:
        """True for an element whose tag carries a pen (V1's ``TRENDABLE`` and trend map)."""
        return (element.get("t") in TRENDABLE
                and str(element.get("tag", "")) in self._trend_sources)

    @pyqtSlot(object)
    def on_element_dragged(self, element: Mapping[str, Any]) -> None:
        """A trendable element dragged: open the trend window so the drop lands somewhere, and
        drag the element's tag to it."""
        if not self.trendable(element):
            return
        self.open_trend()
        mime = QMimeData()
        mime.setData(TAG_MIME, str(element["tag"]).encode("utf-8"))
        mime.setText(str(element["tag"]))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

    @pyqtSlot(object, QPoint)
    def on_element_context(self, element: Mapping[str, Any], pos: QPoint) -> None:
        """Element context menu: trend, and the screen jump list."""
        menu = QMenu(self)
        tag = str(element.get("tag", ""))
        menu.addAction(f"{tag}").setEnabled(False)
        menu.addSeparator()
        if element.get("t") in TRENDABLE:
            bound = self.trendable(element)
            trend = menu.addAction("Trend ↗" if bound else "Trend — not bound")
            trend.setEnabled(bound)
            trend.triggered.connect(lambda _c=False, t=tag: self.open_trend(t))
            menu.addSeparator()
        for screen_id, title in SCREENS:
            action = menu.addAction(title)
            action.triggered.connect(lambda _c, sid=screen_id: self._activate(sid))
        menu.exec(pos)

    @pyqtSlot(str, str, float, float)
    def on_element_moved(self, screen_id: str, key: str, x: float, y: float) -> None:
        """Persist a dragged overlay position to this machine's settings."""
        stored = dict(self.settings.value(LAYOUT_KEY, {}) or {})
        stored[f"{screen_id}|{key}"] = [x, y]
        self.settings.setValue(LAYOUT_KEY, stored)

    # ----------------------------------------------------------------------------------
    # Edit-layout mode
    # ----------------------------------------------------------------------------------

    def _set_editing(self, editing: bool) -> None:
        self._editing = editing
        for view in self._views.values():
            view.set_editing(editing)
        self.statusBar().showMessage(
            "Edit layout: drag an element to reposition it" if editing else "", 4000)

    def _restore_layout(self) -> None:
        """Re-apply stored overlay positions on top of the drawing's seed geometry."""
        stored = self.settings.value(LAYOUT_KEY, {}) or {}
        if not stored:
            return
        for view in self._views.values():
            for widget in view.stage.overlays:
                pos = stored.get(f"{view.screen_id}|{widget.element.get('k')}")
                if pos and len(pos) == 2:
                    widget.set_centre(float(pos[0]), float(pos[1]))

    def _reset_layout(self) -> None:
        """Discard stored positions and return every overlay to its drawn centre."""
        answer = QMessageBox.question(
            self, "Reset layout",
            "Return every overlay on every screen to the position the drawing gives it?\n"
            "Stored positions on this machine are discarded.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.settings.remove(LAYOUT_KEY)
        for view in self._views.values():
            for widget in view.stage.overlays:
                el = widget.element
                widget.set_centre(float(el["x"]), float(el["y"]))
        self.statusBar().showMessage("Layout reset to the drawing geometry", 4000)

    # ----------------------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._trend is not None:
            self._trend.close()          # a separate top-level window: close it with the console
        self.bridge.shutdown()
        super().closeEvent(event)


__all__ = ["MainWindow", "HealthLed"]
