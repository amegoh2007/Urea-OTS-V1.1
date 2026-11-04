"""Start-up intro of the OTS console.

The scene, sequencer and timeline are pure Python and import without Qt; ``IntroSplash`` (the
window) is loaded on first use so that tests and tools can use the pure parts on a machine with no
display and no PyQt6.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ureasim.hmi.intro.splash import IntroSplash

__all__ = ["IntroSplash"]


def __getattr__(name: str):  # noqa: ANN202 - lazy re-export
    if name == "IntroSplash":
        from ureasim.hmi.intro.splash import IntroSplash

        return IntroSplash
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
