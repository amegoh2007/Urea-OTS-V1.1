"""What the console tests share: a Qt application, a bridge that records what a console sends, the
plant's packet after ten design ticks, and console settings of each test's own."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtWidgets import QApplication

from ureasim.hmi import main_window
from ureasim.net.protocol import Role


class FakeBridge(QObject):
    """The console's bridge as a faceplate sees it: its signals, its latest packet, and every
    command and request sent, with the ids the server would answer. A history request is filed
    in ``history``; `answer` replies to it as the server would."""

    snapshot = pyqtSignal(object)
    command_result = pyqtSignal(int, bool, str)
    roster_changed = pyqtSignal(object)
    exercises_received = pyqtSignal(object, str)
    history_received = pyqtSignal(int, bool, str, object)

    def __init__(self, latest=None, connected: bool = True) -> None:
        super().__init__()
        self.latest = latest or {}
        self.connected = connected
        self.role = Role.INSTRUCTOR
        self.sent: list[dict] = []
        self.requests = 0
        self.history: list[dict] = []

    def send_command(self, cmd) -> int:
        if not self.connected:
            return 0
        self.sent.append(dict(cmd))
        return len(self.sent)

    def request_exercises(self) -> bool:
        self.requests += 1
        return self.connected

    def request_history(self, paths, span_s, max_points=800, end_sim=None) -> int:
        if not self.connected:
            return 0
        self.history.append({"id": 100 + len(self.history), "paths": list(paths),
                             "span": span_s, "max_points": max_points, "end": end_sim})
        return self.history[-1]["id"]

    def answer(self, result, ok: bool = True, reason: str = "", req_id=None) -> None:
        """Reply to the latest history request (or to ``req_id``)."""
        self.history_received.emit(self.history[-1]["id"] if req_id is None else req_id, ok,
                                   reason, result)

    def publish(self, state) -> None:
        self.latest = state
        self.snapshot.emit(state)


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def console_settings(tmp_path, monkeypatch):
    """The console's settings in an INI file of the test's own (handoff A-23): a test never reads
    the layout or the trend view an operator saved on this machine, and never writes one."""
    path = str(tmp_path / "console.ini")
    monkeypatch.setattr(main_window, "QSettings",
                        lambda *_: QSettings(path, QSettings.Format.IniFormat))
    return path


@pytest.fixture(scope="session")
def packet():
    """The design plant's packet after ten ticks."""
    from tests.engine.packet.conftest import run
    return run().packet


@pytest.fixture()
def bridge(qapp, packet):
    return FakeBridge(packet)
