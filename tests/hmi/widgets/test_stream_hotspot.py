"""The stream inspector — `ureasim.hmi.widgets.stream_hotspot`.

The rows are proved against V1's own renderer: ``frontend/app.js``'s ``COMP_LBL``, ``fStrm`` and
``renderStream`` are executed by node on every stream the design packet publishes, whole and
composition only, and the port's rows must be the same strings. That test skips on a machine with
no node or no V1 tree. The rest pin what a trainee sees: the record's own fields, nothing computed,
a missing field as a dash, a stream the packet does not carry not opened, and the inspector redrawn
from every packet.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from ureasim.hmi.faceplates import faceplate_for
from ureasim.hmi.widgets.stream_hotspot import (
    MISSING,
    StreamInspector,
    published_stream,
    stream_rows,
)
from tests.equivalence.v1_loader import V1_ROOT

APP_JS = V1_ROOT / "frontend" / "app.js"


def _v1_rows(cases):
    """V1's ``renderStream`` run by node on each (record, composition_only) case."""
    src = APP_JS.read_text(encoding="utf-8")
    body = src[src.index("const COMP_LBL"):src.index("function openStreamPopup")]
    script = (body + "\nconst cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n"
              "process.stdout.write(JSON.stringify(cases.map(c => renderStream(c[0], c[1]))));\n")
    out = subprocess.run([shutil.which("node"), "-e", script], input=json.dumps(cases),
                         capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


@pytest.mark.skipif(shutil.which("node") is None or not APP_JS.exists(),
                    reason="node or the V1 tree is not on this machine")
def test_every_published_stream_reads_as_v1_renders_it(packet):
    streams = packet["STREAMS"]
    cases = [[rec, comp] for rec in streams.values() for comp in (False, True)]
    theirs = _v1_rows(cases)
    assert len(theirs) == 2 * len(streams) > 40
    for (rec, comp), want in zip(cases, theirs):
        assert [list(r) for r in stream_rows(rec, comp)] == want, (rec["name"], comp)


def test_the_rows_are_the_records_fields(packet):
    rec = packet["STREAMS"]["SCRUB_OFFGAS"]
    rows = dict(stream_rows(rec))
    assert rows["Route"] == f"{rec['src']} \u2192 {rec['dst']}"
    assert rows["Mass flow"] == f"{rec['mass_th']:.2f} t/h ({rec['mass_kgh']:.0f} kg/h)"
    assert rows["Temperature"] == f"{rec['T_C']:.1f} \u00b0C"
    comp = stream_rows(rec, composition_only=True)
    assert comp[0] == ("Composition", "mol %  |  mass %")
    shown = [label for label, _ in comp[1:]]
    assert "N\u2082" in shown and "Urea" not in shown


def test_a_field_the_engine_leaves_out_reads_as_a_dash():
    rows = dict(stream_rows({"name": "x", "src": "a", "dst": "b", "phase": "liquid",
                             "T_C": None, "rho": None, "vol_m3h": None,
                             "enthalpy_kJkg": None, "enthalpy_basis": None}))
    assert rows["Temperature"] == f"{MISSING} \u00b0C"
    assert rows["Density"] == rows["Volum. flow"] == rows["Enthalpy basis"] == MISSING
    assert rows["Specific enthalpy"] == f"{MISSING} (not modelled)"


def test_a_stream_the_packet_does_not_carry_opens_nothing(bridge):
    assert published_stream(bridge.latest, "S0305") is None
    assert faceplate_for({"t": "strm", "tag": "S0305", "stream": "S0305"}, bridge) is None


def test_the_inspector_redraws_from_every_packet(qapp, bridge, packet):
    element = {"t": "strm", "tag": "SCRUBBER OFF-GAS -> HV-322604", "stream": "SCRUB_OFFGAS"}
    face = faceplate_for(element, bridge)
    assert isinstance(face, StreamInspector) and not face.composition_only
    face.show()
    rec = packet["STREAMS"]["SCRUB_OFFGAS"]
    assert face.title_label.text() == rec["name"]
    assert face.table.rowCount() == len(stream_rows(rec))
    assert face.table.item(0, 1).text() == f"{rec['src']} \u2192 {rec['dst']}"
    hotter = dict(packet, STREAMS=dict(packet["STREAMS"],
                                       SCRUB_OFFGAS=dict(rec, T_C=rec["T_C"] + 10.0)))
    bridge.publish(hotter)
    assert face.table.item(2, 1).text() == f"{rec['T_C'] + 10.0:.1f} \u00b0C"
    bridge.publish({})
    assert face.status.text() == "NOT PUBLISHED" and face.table.rowCount() == 0
    face.close()


def test_an_analyser_opens_the_composition_alone(qapp, bridge, packet):
    face = faceplate_for({"t": "ae", "tag": "AE-322801", "stream": "REACT_OVERFLOW"}, bridge)
    assert face.composition_only
    face.show()
    assert face.table.item(0, 0).text() == "Composition"
    assert face.table.rowCount() == len(stream_rows(packet["STREAMS"]["REACT_OVERFLOW"], True))
    face.close()
