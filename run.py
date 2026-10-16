#!/usr/bin/env python3
"""Urea Plant OTS — application entry point.

The simulator runs as **one plant with several consoles**: an engine process serving an
instructor station and one or more trainee stations. This one entry point launches either
half, or both at once on a single machine.

    python run.py                       engine + the local superuser console (default)
    python run.py server                engine only, serving the network
    python run.py station --host HOST   a console, connecting to an engine elsewhere

Typical classroom setup
-----------------------

    instructor machine      python run.py server --host 0.0.0.0 --token T
                            python run.py station --role instructor --token T
    each trainee machine    python run.py station --host 10.0.0.5 --role operator --token T
    an observer             python run.py station --host 10.0.0.5 --role observer --token T

``--token`` is the station login (handoff A-2, closed 2026-10-16): an engine started with one
admits only the stations that present it; with none, every station is admitted. The token may be
given in the ``UREASIM_TOKEN`` environment variable instead, which keeps it out of the process
list.

Roles
-----
    operator     every command V1's operator screens exposed
    instructor   the above, plus malfunction injection, reset and simulation pacing
    observer     sees the plant, commands nothing
    superuser    every command, no unit assignment; granted only on the engine's own machine

The server grants the role; a station only requests one. See `ureasim/net/protocol.py`.

Single-machine mode (decided 2026-10-07)
----------------------------------------
``python run.py`` starts the engine on the loopback interface and one console as the superuser,
which no role refuses and no unit assignment narrows. It is the default deployment; the classroom
setup above is the multi-station one, supported since A-2 and A-8 closed (2026-10-16), the
instructor's panel on an instructor station and unit assignment by section.

The engine
----------
The server runs the plant (`ureasim.engine.session`) on its own physics thread
(`ureasim.net.engine_host`): the design seed at start, stepped in fixed 0.1 s steps at the
instructor's pacing, the console packet published to every station ten times a second, each
command applied between two ticks and answered with the plant's reason when it is refused.
Exercises are saved under ``~/ureasim-exercises`` unless ``UREASIM_EXERCISES`` names another
folder.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import socket
import sys
import threading

from ureasim.net.protocol import Role
from ureasim.net.server import DEFAULT_HOST, DEFAULT_PORT, StationServer

#: Reported to every console in `welcome`, so a station can tell which build it is attached to.
ENGINE_NAME = "ureasim-1.1"


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run with no mode to start the engine and the local superuser console.",
    )
    parser.add_argument("mode", nargs="?", default="all",
                        choices=("all", "server", "station"),
                        help="what to launch (default: all)")
    parser.add_argument("--host", default=None,
                        help="server: interface to bind (default 0.0.0.0). "
                             "station: engine to connect to (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"TCP port (default {DEFAULT_PORT})")
    parser.add_argument("--role", default=None,
                        choices=[r.value for r in Role],
                        help="station: role to request "
                             "(default superuser for 'all', operator for 'station')")
    parser.add_argument("--station", default=None,
                        help="station: name shown in the audit line "
                             "(default: this machine's hostname)")
    parser.add_argument("--token", default=os.environ.get("UREASIM_TOKEN") or None,
                        help="station token. server: admit only the stations that present it. "
                             "station: present it. all: both "
                             "(default: UREASIM_TOKEN, else no token)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="log connections and refusals")
    return parser.parse_args(argv)


# ======================================================================================
# Engine / server
# ======================================================================================

async def _serve(host: str, port: int, ready: threading.Event | None = None,
                 token: str | None = None) -> None:
    """The station server with the engine attached, until cancelled. No Qt involved."""
    # Imported here: building the plant reads the thermodynamic stores, which `--help` need not.
    from ureasim.engine.session import EngineSession
    from ureasim.net.engine_host import EngineHost

    server = StationServer(token=token)
    bound = await server.start(host, port)
    engine = EngineHost(EngineSession(), server, ENGINE_NAME)
    engine.start()
    print(f"engine serving on {host}:{bound}"
          + (", station token required" if token is not None else ""))
    if ready is not None:
        ready.set()
    try:
        await asyncio.Event().wait()              # serve until cancelled
    finally:
        engine.stop()
        await server.stop()


def _serve_forever(host: str, port: int, token: str | None = None) -> None:
    """Run the engine and its station server until interrupted. Blocking."""
    try:
        asyncio.run(_serve(host, port, token=token))
    except KeyboardInterrupt:
        print("\nengine stopped")


def _serve_in_background(host: str, port: int, token: str | None = None) -> threading.Thread:
    """Start the server on its own thread, for the single-machine 'all' mode.

    The server is asyncio and the console is Qt; each needs its own event loop, so they get
    their own threads. They still talk over a real socket rather than sharing objects —
    the single-machine case is then exactly the multi-machine case with a shorter wire, and
    a bug that only appears over the network cannot hide here.
    """
    ready = threading.Event()

    def target() -> None:
        try:
            asyncio.run(_serve(host, port, ready, token))
        except (KeyboardInterrupt, SystemExit):
            pass

    thread = threading.Thread(target=target, name="station-server", daemon=True)
    thread.start()
    if not ready.wait(timeout=60.0):
        raise RuntimeError("station server failed to start within 60 s")
    return thread


# ======================================================================================
# Console / station
# ======================================================================================

def _run_station(host: str, port: int, role: Role, station: str,
                 token: str | None = None) -> int:
    """Open one operator console and connect it to an engine."""
    # Imported here, not at module scope: `run.py server` must work on a machine with no
    # display and no Qt runtime at all.
    from PyQt6.QtWidgets import QApplication

    from ureasim.hmi.bridge import EngineBridge
    from ureasim.hmi.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv[:1])
    bridge = EngineBridge(station=station, role=role, token=token)
    window = MainWindow(bridge)
    window.resize(1382, 820)
    window.show()
    bridge.connect_to(host, port)
    return app.exec()


# ======================================================================================

def main(argv=None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
    )

    station_name = args.station or socket.gethostname()
    # An empty token is no token: the server would otherwise read it as a login.
    token = args.token or None

    if args.mode == "server":
        _serve_forever(args.host or DEFAULT_HOST, args.port, token)
        return 0

    if args.mode == "station":
        role = Role(args.role or Role.OPERATOR.value)
        return _run_station(args.host or "127.0.0.1", args.port, role, station_name, token)

    # 'all': engine plus a local console. The console defaults to the superuser (decided
    # 2026-10-07): the one console of a single-machine simulator runs every command, and the
    # server grants the role to a loopback peer only. A token, if given, guards both ends.
    _serve_in_background(args.host or "127.0.0.1", args.port, token)
    role = Role(args.role or Role.SUPERUSER.value)
    return _run_station("127.0.0.1", args.port, role, station_name, token)


if __name__ == "__main__":
    sys.exit(main())
