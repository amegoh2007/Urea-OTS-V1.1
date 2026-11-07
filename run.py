#!/usr/bin/env python3
"""Urea Plant OTS — application entry point.

The simulator is **one plant with a single local console** (decided 2026-10-22, `project.md`
decision 149). One command starts both halves on this machine: the headless engine, served on
the loopback interface, and the console window attached to it.

    python run.py                       the intro, then the engine and its console (launch.bat
                                        does the same)
    python run.py --no-intro            no intro: the plant runs from the start, as before

The console carries the ten DCS screens and their faceplates, and an Instructor menu whose panel
holds the simulation controls — pacing, freeze, reset, malfunctions, the battery-limit CO2
demand, exercise save and restore. No command is refused for who sent it; the engine refuses what
the process refuses, with its reason.

The start-up intro
------------------
The console opens on the HFC intro (`ureasim.hmi.intro`), which ends on two buttons, 100% LOAD and
LOAD. The engine is built while the intro plays and held at its design seed, the 1750 MTPD design
basis: its plant clock does not move and it publishes nothing. Pressing 100% LOAD builds the console,
connects it and releases the hold with the engine's own ``freeze`` command
(`ureasim.hmi.startup`); the console is shown when the first packet arrives. LOAD first offers the
saved exercises, restores the one chosen, and only then releases the plant; Cancel goes back to
the two buttons (decision 171).
``--no-intro`` skips all of it and runs the plant from the start, which keeps the edit-and-run cycle
short.

The engine
----------
The engine runs the plant (`ureasim.engine.session`) on its own physics thread
(`ureasim.net.engine_host`): the design seed at start, stepped in fixed 0.1 s steps at the
instructor's pacing, the console packet published ten times a second, each command applied between
two ticks and answered with the plant's reason when it is refused. Exercises are saved under
``~/ureasim-exercises`` unless ``UREASIM_EXERCISES`` names another folder; the exercises shipped in
the repository's ``scenarios`` folder, verified steady states, are listed and restored beside them
and never written, by the intro's LOAD and the instructor's panel alike (decision 171).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import socket
import sys
import threading
from pathlib import Path

from ureasim.net.server import DEFAULT_HOST, DEFAULT_PORT, StationServer

#: Reported to the console in `welcome`, so it can tell which build it is attached to.
ENGINE_NAME = "ureasim-1.1"

#: The exercises shipped with the simulator: the repository's verified steady states, which the intro's LOAD
#: button and the instructor's panel offer beside the instructor's own folder, and which SAVE never writes
#: (decision 171; CLAUDE.md section 6 keeps training saves out of the repository).
SCENARIO_DIR = Path(__file__).resolve().parent / "scenarios"


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"loopback TCP port between the engine and the console "
                             f"(default {DEFAULT_PORT})")
    parser.add_argument("--station", default=None,
                        help="name shown in the audit line (default: this machine's hostname)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="log the console's connection and refusals")
    parser.add_argument("--no-intro", action="store_true",
                        help="skip the start-up intro: the plant runs from the start")
    parser.add_argument("--fullscreen-intro", action="store_true",
                        help="play the start-up intro full screen")
    return parser.parse_args(argv)


# ======================================================================================
# Engine
# ======================================================================================

async def _serve(port: int, ready: threading.Event | None = None, hold: bool = False) -> None:
    """The console server with the engine attached, until cancelled. No Qt involved.

    ``hold`` builds the plant with its clock held (the engine's own freeze), set before the physics
    thread exists so nothing races it: the start-up intro releases it with a ``freeze`` command.
    """
    # Imported here: building the plant reads the thermodynamic stores, which `--help` need not.
    from ureasim.engine.session import EngineSession
    from ureasim.net.engine_host import EngineHost

    server = StationServer()
    bound = await server.start(DEFAULT_HOST, port)
    session = EngineSession(shipped_dir=SCENARIO_DIR)
    session.frozen = hold
    engine = EngineHost(session, server, ENGINE_NAME)
    engine.start()
    print(f"engine serving on {DEFAULT_HOST}:{bound}")
    if ready is not None:
        ready.set()
    try:
        await asyncio.Event().wait()              # serve until cancelled
    finally:
        engine.stop()
        await server.stop()


def _start_engine(port: int, hold: bool = False) -> tuple[threading.Thread, threading.Event]:
    """Start the engine and its server on their own thread; return it with its ready flag.

    The server is asyncio and the console is Qt; each needs its own event loop, so they get
    their own threads. They still talk over a loopback socket rather than sharing objects: the
    console can only read the published packet and send commands, so no widget reaches into the
    physics, and the engine never waits on a repaint.
    """
    ready = threading.Event()

    def target() -> None:
        try:
            asyncio.run(_serve(port, ready, hold))
        except (KeyboardInterrupt, SystemExit):
            pass

    thread = threading.Thread(target=target, name="console-server", daemon=True)
    thread.start()
    return thread, ready


def _serve_in_background(port: int) -> threading.Thread:
    """Start the engine and wait until it serves."""
    thread, ready = _start_engine(port)
    if not ready.wait(timeout=60.0):
        raise RuntimeError("the engine failed to start within 60 s")
    return thread


# ======================================================================================
# Console
# ======================================================================================

def _run_console(port: int, station: str) -> int:
    """Open the console and connect it to the engine on this machine."""
    # Imported here, not at module scope, so the engine's half needs no Qt.
    from PyQt6.QtWidgets import QApplication

    from ureasim.hmi.bridge import EngineBridge
    from ureasim.hmi.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv[:1])
    bridge = EngineBridge(station=station)
    window = MainWindow(bridge)
    window.resize(1382, 820)
    window.show()
    bridge.connect_to(DEFAULT_HOST, port)
    return app.exec()


def _run_with_intro(port: int, station: str, fullscreen: bool) -> int:
    """Play the intro while the engine is built and held; the 100% LOAD press starts the plant."""
    thread, ready = _start_engine(port, hold=True)      # builds while Qt loads and the intro plays

    from PyQt6.QtWidgets import QApplication

    from ureasim.hmi.bridge import EngineBridge
    from ureasim.hmi.intro import IntroSplash
    from ureasim.hmi.main_window import MainWindow
    from ureasim.hmi.startup import StartupController

    app = QApplication.instance() or QApplication(sys.argv[:1])
    bridge = EngineBridge(station=station)

    def make_window() -> MainWindow:
        window = MainWindow(bridge)
        window.resize(1382, 820)
        return window

    splash = IntroSplash(fullscreen=fullscreen)
    startup = StartupController(splash=splash, bridge=bridge, make_window=make_window,
                                engine_ready=ready, engine_alive=thread.is_alive,
                                host=DEFAULT_HOST, port=port)

    def engine_failed(reason: str) -> None:
        print(f"run.py: {reason}", file=sys.stderr)
        app.exit(1)

    startup.failed.connect(engine_failed)
    splash.finished.connect(splash.deleteLater)
    splash.play()
    return app.exec()


# ======================================================================================

def main(argv=None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
    )
    station = args.station or socket.gethostname()
    if args.no_intro:
        _serve_in_background(args.port)
        return _run_console(args.port, station)
    return _run_with_intro(args.port, station, args.fullscreen_intro)


if __name__ == "__main__":
    sys.exit(main())
