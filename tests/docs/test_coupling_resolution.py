"""`docs/coupling_resolution.md` must describe exactly the couplings the map generates.

Why this is a test and not a review note
----------------------------------------
`docs/step_sim_dataflow.md` is regenerated from V1's source by `tools/analyse_step_sim.py`.
`docs/coupling_resolution.md` is written by hand. The two can drift in either direction:

  * V1's source changes, the map picks up a new coupling, and nobody resolves it — a value
    that will be silently recomputed from the wrong state once the units are split;
  * a row is dropped while editing the resolution table, and the omission is invisible
    because both files are long.

Neither failure announces itself. So the pairing is asserted rather than trusted, which is
the same standard the code is held to.

This file tests documents, not behaviour. It lives here because it is the only mechanism
that keeps a hand-written gate honest against a generated one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[2] / "docs"
MAP = DOCS / "step_sim_dataflow.md"
RESOLUTION = DOCS / "coupling_resolution.md"

#: The vocabulary the resolution table is allowed to use. A new disposition has to be
#: added here deliberately, with its meaning documented in the file it appears in.
DISPOSITIONS = {"ARTEFACT", "TEAR", "PACKET", "PROPERTY", "CONTROL", "RESULT", "ARG"}

_ROW = re.compile(r"^\| `([^`]+)` \| ([\d,+]+) \| ([\d,+]+) \|", re.M)
_RESOLVED = re.compile(
    r"^\| `([^`]+)` \| ([\d,+]+) \| ([\d,+]+) \| ([A-Z]+) \| (.+?) \|$", re.M)

pytestmark = pytest.mark.skipif(
    not (MAP.is_file() and RESOLUTION.is_file()),
    reason="the data-flow map or its resolution has not been generated on this machine",
)


def _process_couplings() -> dict[str, tuple[str, str]]:
    """`{name: (written_in, read_in)}` from section 3a of the generated map."""
    text = MAP.read_text(encoding="utf-8")
    section = text.split("### 3a. Process couplings")[1].split("### 3b.")[0]
    return {name: (wr, rd) for name, wr, rd in _ROW.findall(section)}


def _resolutions() -> dict[str, tuple[str, str, str, str]]:
    """`{name: (written_in, read_in, disposition, becomes)}` from the resolution table."""
    text = RESOLUTION.read_text(encoding="utf-8")
    section = text.split("## The resolution")[1]
    return {name: (wr, rd, disp, becomes)
            for name, wr, rd, disp, becomes in _RESOLVED.findall(section)}


def test_every_process_coupling_has_a_resolution():
    missing = sorted(set(_process_couplings()) - set(_resolutions()))
    assert not missing, (
        "these couplings appear in the generated map and are not resolved: "
        + ", ".join(missing)
    )


def test_no_resolution_describes_a_coupling_that_no_longer_exists():
    stale = sorted(set(_resolutions()) - set(_process_couplings()))
    assert not stale, (
        "these rows are resolved but are no longer process couplings: " + ", ".join(stale)
    )


def test_the_sections_quoted_in_the_resolution_match_the_map():
    """A resolution that quotes the wrong sections is a resolution of the wrong value."""
    couplings = _process_couplings()
    for name, (wr, rd, _, _) in _resolutions().items():
        assert (wr, rd) == couplings[name], name


def test_every_disposition_is_one_of_the_declared_seven():
    used = {disp for _, _, disp, _ in _resolutions().values()}
    assert used <= DISPOSITIONS, f"undeclared disposition(s): {sorted(used - DISPOSITIONS)}"


def test_every_resolution_says_what_the_value_becomes():
    """A disposition alone is a label. The sentence after it is the actual decision."""
    thin = sorted(name for name, (_, _, _, becomes) in _resolutions().items()
                  if len(becomes.strip()) < 30)
    assert not thin, f"these resolutions state a disposition but not an outcome: {thin}"


def test_the_disposition_counts_in_the_summary_match_the_table():
    """The summary is read far more often than the 125-row table under it."""
    text = RESOLUTION.read_text(encoding="utf-8")
    summary = text.split("| disposition | rows |")[1].split("## The resolution")[0]
    stated = {m.group(1): int(m.group(2))
              for m in re.finditer(r"^\| (\w+) \| (\d+) \|$", summary, re.M)}
    actual: dict[str, int] = {}
    for _, _, disp, _ in _resolutions().values():
        actual[disp] = actual.get(disp, 0) + 1
    assert stated == actual

    total = int(re.search(r"\*\*total\*\* \| \*\*(\d+)\*\*", summary).group(1))
    assert total == sum(actual.values()) == len(_process_couplings())


def test_the_tear_rows_are_flagged_as_the_maps_own_blind_spot():
    """The most valuable finding of the pass must not be quietly demoted to an ARG.

    Eleven `*_prev` names read last tick's flow out of `s.tlag` with a design default. The
    parser cannot see through a `.get()`, so it reports them as same-tick couplings. If a
    future edit reclassified one, the one-tick delay would disappear from the model
    without anything failing — hence this assertion.
    """
    resolutions = _resolutions()
    prev_names = sorted(n for n in _process_couplings() if n.endswith("_prev"))
    assert len(prev_names) == 11, prev_names
    for name in prev_names:
        assert resolutions[name][2] == "TEAR", name
