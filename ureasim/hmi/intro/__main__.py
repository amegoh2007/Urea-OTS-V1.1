"""Play the intro on its own: ``python -m ureasim.hmi.intro [--fullscreen]``.

For reviewing the animation without starting the engine. Any key or a click skips ahead to the
"100% LOAD" and "LOAD" buttons; pressing one prints the start request (its key) and closes the window,
as the application's own slot would start the simulator.
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from ureasim.hmi.intro.splash import IntroSplash


def main(argv: list[str]) -> int:
    app = QApplication(argv)
    splash = IntroSplash(fullscreen="--fullscreen" in argv)

    def on_start(key: str) -> None:
        print(f"start requested: {key}")
        splash.mark_ready()

    splash.start_requested.connect(on_start)
    splash.finished.connect(app.quit)
    splash.play()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
