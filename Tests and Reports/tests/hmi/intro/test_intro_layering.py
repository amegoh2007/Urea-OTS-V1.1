"""CLAUDE.md section 1 rule 3 for the intro: the scene, the sequencer and the data import no Qt.

Only ``painter.py``, ``canvas.py``, ``splash.py`` and ``__main__.py`` may import PyQt6; the rest of the intro must
stay drivable with no display. The asset the painter loads must also be present and intact.
"""

from __future__ import annotations

import ast
import struct
from pathlib import Path

import pytest

import ureasim.data.intro as data_module
import ureasim.data.intro_flyby as flyby_data_module
import ureasim.data.intro_plant as plant_data_module
from ureasim.data.intro import LOGO

_INTRO_DIR = Path(__file__).resolve().parents[4] / "ureasim" / "hmi" / "intro"
_QT_FREE = ("ops.py", "timeline.py", "camera.py", "model3d.py", "flyby.py", "scene.py", "sequencer.py")
_DATA_MODULES = (data_module, flyby_data_module, plant_data_module)
_QT_ALLOWED = ("painter.py", "canvas.py", "splash.py", "__main__.py")


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("name", _QT_FREE)
def test_pure_modules_import_no_qt(name: str) -> None:
    assert "PyQt6" not in _imports(_INTRO_DIR / name)


@pytest.mark.parametrize("module", _DATA_MODULES, ids=lambda m: m.__name__)
def test_data_modules_import_no_qt(module) -> None:
    assert "PyQt6" not in _imports(Path(module.__file__))


def test_package_init_does_not_import_qt_at_import_time() -> None:
    tree = ast.parse((_INTRO_DIR / "__init__.py").read_text(encoding="utf-8"))
    top_level = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    for node in top_level:
        mod = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
        assert not (mod or "").startswith(("PyQt6", "ureasim.hmi.intro.splash", "ureasim.hmi.intro.painter"))


def test_every_module_is_inside_the_size_target() -> None:
    for path in list(_INTRO_DIR.glob("*.py")) + [Path(m.__file__) for m in _DATA_MODULES]:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 600, path.name


def test_no_module_is_unaccounted_for() -> None:
    present = {p.name for p in _INTRO_DIR.glob("*.py")}
    assert present == set(_QT_FREE) | set(_QT_ALLOWED) | {"__init__.py"}


def test_logo_asset_is_present_and_matches_the_regions_in_the_data_module() -> None:
    png = _INTRO_DIR / "assets" / f"{LOGO.name}.png"
    header = png.read_bytes()[:26]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", header[16:24])
    assert (width, height) == (LOGO.atlas_width, LOGO.atlas_height)
    for x, y, w, h in (LOGO.emblem, LOGO.letters, LOGO.name_en, LOGO.name_ar):
        assert x >= 0 and y >= 0 and x + w <= width and y + h <= height
