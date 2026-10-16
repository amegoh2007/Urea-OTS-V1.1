"""Map the data flow across V1's `step_sim()` so it can be split into unit modules.

Why this exists
---------------
V1's `step_sim()` is ~4,100 lines of straight-line code with heavy cross-talk: later
sections read locals computed hundreds of lines earlier, and the recycle tears are written
at the bottom for the *next* tick to read. Splitting it into unit-operation modules
requires naming **every value that crosses a section boundary** — which ones are same-tick
couplings (a real process connection that becomes a function argument) and which ones are
one-tick tears (a recycle that becomes engine state).

Reading 4,100 lines by eye to find them is how a coupling gets missed. This does it by
parsing.

Method
------
1. Locate `step_sim` in `backend/main.py` and take its source.
2. Split it into sections on the banner comments the author already wrote
   (``# ----- ... -----`` / ``# ===== ... =====``).
3. Walk the AST once, recording for every local name and every ``s.<attr>`` the sections
   that WRITE it and the sections that READ it.
4. Classify each:

       local, written in section i, read in section j > i     forward coupling, split
                                                              into PROCESS and TELEMETRY
                                                              by whether every reader is a
                                                              publishing section
       local, written in section i, read in section j <= i    backward read (a tear, or a
                                                              loop-carried local)
       s.<attr> written late, read early                      ONE-TICK TEAR — the recycle
       s.<attr> written and read in one section               that unit's own state
       s.<attr> read but never written                        a design constant or input

Limits, stated
--------------
This is a *static* map, so it over-reports: a name written on both sides of a branch looks
like a coupling from each. It never under-reports a plain assignment, which is what matters
— the table is a checklist to work through, not a specification to trust blindly. Anything
it flags must be resolved by reading that code; anything it does not flag is not a plain
cross-section assignment.

Usage
-----
    python tools/analyse_step_sim.py [--out docs/step_sim_dataflow.md]
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_SOURCE = Path(r"D:\Work\Urea Simulation\backend\main.py")
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "docs" / "step_sim_dataflow.md"

#: Banner comments the author used to mark a new unit or stage. Four or more rule
#: characters: the file also uses a two-dash `# -- ` prefix for continuation lines inside a
#: comment block, and those are prose, not section headings.
_BANNER = re.compile(r"^\s*#\s*[-=]{4,}\s*(.*?)\s*[-=]*\s*$")

#: A banner must carry at least this much text to count as a section title; the file also
#: uses bare rules as visual separators.
_MIN_TITLE = 12

#: Names that cross every boundary by nature and say nothing about the flowsheet.
_NOISE = {"s", "dt", "math", "out", "i", "j", "k", "n", "x", "y", "t", "v", "w"}


#: Sections that PUBLISH rather than compute: they consume converged values and feed
#: nothing back into the plant. A value read only by these is telemetry, so it becomes a
#: field on the state snapshot, NOT an argument between two unit modules. Identified by a
#: distinctive substring of the author's own banner text so the classification survives
#: sections being renumbered, and asserted present so it cannot silently match nothing.
_PUBLICATION_TITLES = (
    "uniform process-stream registry",       # the stream inspector
    "auxiliary faceplate trims",             # explicitly "off the network"
    "ENERGY-CLOSURE DIAGNOSTIC",             # an audit readout
)


def publication_sections(sections: list[tuple[int, str]]) -> set[int]:
    """Indices of the sections in `_PUBLICATION_TITLES`, failing loudly on a miss."""
    found: dict[str, int] = {}
    for i, (_, title) in enumerate(sections):
        for needle in _PUBLICATION_TITLES:
            if needle in title:
                found[needle] = i
    missing = [n for n in _PUBLICATION_TITLES if n not in found]
    if missing:
        raise SystemExit(
            "publication section(s) not found in the source banners: "
            + "; ".join(missing)
            + " -- the classification in section 3 would be wrong, so this is fatal"
        )
    return set(found.values())


def find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise SystemExit(f"{name}() not found")


def split_sections(lines: list[str], start: int, end: int) -> list[tuple[int, str]]:
    """Return ``(line_no, title)`` for each banner inside ``[start, end]``, 1-indexed."""
    sections: list[tuple[int, str]] = []
    for ln in range(start, end + 1):
        m = _BANNER.match(lines[ln - 1])
        if not m:
            continue
        title = m.group(1).strip(" -=")
        if len(title) >= _MIN_TITLE:
            sections.append((ln, title))
    if not sections or sections[0][0] > start:
        sections.insert(0, (start, "function preamble"))
    return sections


def section_of(line: int, sections: list[tuple[int, str]]) -> int:
    lo, hi = 0, len(sections) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sections[mid][0] <= line:
            lo = mid
        else:
            hi = mid - 1
    return lo


class Collector(ast.NodeVisitor):
    """Record which sections write and read each local name and each ``s.<attr>``."""

    def __init__(self, sections):
        self.sections = sections
        self.local_writes = defaultdict(set)
        self.local_reads = defaultdict(set)
        self.state_writes = defaultdict(set)
        self.state_reads = defaultdict(set)

    def _sec(self, node) -> int:
        return section_of(getattr(node, "lineno", 1), self.sections)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in _NOISE:
            return
        target = self.local_writes if isinstance(node.ctx, ast.Store) else self.local_reads
        target[node.id].add(self._sec(node))

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Only `s.<attr>` — the plant state object.
        if isinstance(node.value, ast.Name) and node.value.id == "s":
            target = (self.state_writes if isinstance(node.ctx, ast.Store)
                      else self.state_reads)
            target[node.attr].add(self._sec(node))
        self.generic_visit(node)


def classify(collector: Collector, publication: set[int]) -> dict:
    """Bucket every name by how it crosses a boundary."""
    process, telemetry, backward, tears, owned, inputs = [], [], [], [], [], []

    for name, writes in collector.local_writes.items():
        reads = collector.local_reads.get(name, set())
        if not reads:
            continue
        first_write = min(writes)
        later = sorted(r for r in reads if r > first_write)
        earlier = sorted(r for r in reads if r < min(writes))
        if later:
            # Read ONLY by a publishing section -> telemetry, not a process coupling.
            bucket = telemetry if set(later) <= publication else process
            bucket.append((name, sorted(writes), later))
        if earlier:
            backward.append((name, sorted(writes), earlier))

    for attr, writes in collector.state_writes.items():
        reads = collector.state_reads.get(attr, set())
        if reads and min(reads) < max(writes):
            tears.append((attr, sorted(writes), sorted(reads)))
        elif reads:
            owned.append((attr, sorted(writes | reads)))
        else:
            owned.append((attr, sorted(writes)))

    for attr, reads in collector.state_reads.items():
        if attr not in collector.state_writes:
            inputs.append((attr, sorted(reads)))

    return {"process": process, "telemetry": telemetry, "backward": backward,
            "tears": tears, "owned": owned, "inputs": inputs}


def _sec_list(sections, indices, limit=6):
    names = [f"{i}" for i in indices[:limit]]
    if len(indices) > limit:
        names.append(f"+{len(indices) - limit}")
    return ",".join(names)


def emit(sections, buckets, total_lines, publication) -> str:
    out = []
    w = out.append
    w("# step_sim() data flow — the boundary-crossing map\n")
    w("**GENERATED FILE** — produced by `tools/analyse_step_sim.py` from\n"
      "`D:\\Work\\Urea Simulation\\backend\\main.py`. Re-run it rather than editing it.\n")
    w("## Why this exists\n")
    w("V1's `step_sim()` is one straight-line function of "
      f"**{total_lines} lines** covering **{len(sections)} sections**. Splitting it into\n"
      "unit-operation modules means turning every value that crosses a section boundary into\n"
      "either a function argument (a same-tick process coupling) or engine state (a one-tick\n"
      "recycle tear). This table is the checklist of those values.\n")
    w("`handoff.md` A-4 gates Phase 4 on this document existing.\n")
    w("## How to read it, and what it does NOT promise\n")
    w("This is a **static** map, so it over-reports: a name written on both sides of a branch\n"
      "looks like a coupling from each. It never under-reports a plain assignment, which is\n"
      "what matters — work through it as a checklist, resolving each entry by reading that\n"
      "code. Anything it does not flag is not a plain cross-section assignment.\n")
    w("Section numbers below index the table in §1.\n")

    w("\n## 1. Sections\n")
    w("| # | line | section |")
    w("|---|---|---|")
    for i, (ln, title) in enumerate(sections):
        w(f"| {i} | {ln} | {title} |")

    w("\n## 2. One-tick recycle tears — `s.<attr>` read before it is written\n")
    w("These are the recycles. V1 writes them at the end of a tick for the **next** tick to\n"
      "read, so each becomes an explicit piece of engine state with a documented one-tick\n"
      "delay — not a hidden ordering dependency.\n")
    w(f"**{len(buckets['tears'])} tears.**\n")
    w("| state attribute | written in | read in |")
    w("|---|---|---|")
    for attr, wr, rd in sorted(buckets["tears"]):
        w(f"| `s.{attr}` | {_sec_list(sections, wr)} | {_sec_list(sections, rd)} |")

    total_fwd = len(buckets["process"]) + len(buckets["telemetry"])
    pub_list = ", ".join(str(i) for i in sorted(publication))
    w("\n## 3. Same-tick couplings — locals written in one section, read in a later one\n")
    w(f"**{total_fwd} in total**, split by WHO READS THEM, because the two halves become\n"
      "different things and only one of them constrains the port.\n")
    w(f"Sections {pub_list} publish rather than compute: they consume converged values and\n"
      "feed nothing back into the plant. A value read only by those is **telemetry** — it\n"
      "becomes a field on the state snapshot, not an argument between two unit modules, and\n"
      "it can be wired at the end of Phase 4 without blocking any unit port.\n")

    w(f"\n### 3a. Process couplings — {len(buckets['process'])}\n")
    w("These are the ones that constrain the port. Each becomes an argument, or a field on\n"
      "a small result object, when the producing section becomes a unit module.\n")
    w("`docs/coupling_resolution.md` carries the row-by-row resolution.\n")
    w("| value | written in | read in |")
    w("|---|---|---|")
    for name, wr, rd in sorted(buckets["process"]):
        w(f"| `{name}` | {_sec_list(sections, wr)} | {_sec_list(sections, rd)} |")

    w(f"\n### 3b. Telemetry only — {len(buckets['telemetry'])}\n")
    w("Read exclusively by a publishing section, so each becomes a snapshot field.\n")
    w("<details><summary>list</summary>\n")
    w("| value | written in | read in |")
    w("|---|---|---|")
    for name, wr, rd in sorted(buckets["telemetry"]):
        w(f"| `{name}` | {_sec_list(sections, wr)} | {_sec_list(sections, rd)} |")
    w("\n</details>\n")

    w("\n## 4. Backward local reads — read before any write in this tick\n")
    w("Usually a loop-carried local or a name shadowed by a branch. Each needs a decision:\n"
      "it is either a genuine tear that happens to live in a local rather than on `s`, or it\n"
      "is an artefact of the flat layout that disappears when the section becomes a function.\n")
    w(f"**{len(buckets['backward'])} names.**\n")
    w("| value | written in | read earlier in |")
    w("|---|---|---|")
    for name, wr, rd in sorted(buckets["backward"]):
        w(f"| `{name}` | {_sec_list(sections, wr)} | {_sec_list(sections, rd)} |")

    w("\n## 5. Plant state that is read but never written here\n")
    w("Design constants, operator inputs and values other modules own. They become\n"
      "constructor arguments or design-basis constants, not state.\n")
    w(f"**{len(buckets['inputs'])} attributes.**\n")
    w("| state attribute | read in |")
    w("|---|---|")
    for attr, rd in sorted(buckets["inputs"]):
        w(f"| `s.{attr}` | {_sec_list(sections, rd)} |")

    w("\n## 6. State owned within one section\n")
    w(f"**{len(buckets['owned'])} attributes** are written and read inside a single section,\n"
      "so they move with that unit and need no boundary at all.\n")
    w("<details><summary>list</summary>\n")
    w(", ".join(f"`s.{a}`" for a, _ in sorted(buckets["owned"])))
    w("\n</details>\n")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--function", default="step_sim")
    args = ap.parse_args(argv)

    if not args.source.is_file():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 2

    text = args.source.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    tree = ast.parse(text)
    fn = find_function(tree, args.function)
    start, end = fn.lineno, fn.end_lineno

    sections = split_sections(lines, start, end)
    publication = publication_sections(sections)
    collector = Collector(sections)
    collector.visit(fn)
    buckets = classify(collector, publication)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(emit(sections, buckets, end - start + 1, publication),
                        encoding="utf-8")

    print(f"wrote {args.out}")
    print(f"  {end - start + 1} lines, {len(sections)} sections")
    print(f"  {len(buckets['tears'])} one-tick tears")
    print(f"  {len(buckets['process'])} same-tick PROCESS couplings")
    print(f"  {len(buckets['telemetry'])} same-tick telemetry-only couplings")
    print(f"  {len(buckets['backward'])} backward local reads")
    print(f"  {len(buckets['inputs'])} read-only state attributes")
    print(f"  {len(buckets['owned'])} section-owned state attributes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
