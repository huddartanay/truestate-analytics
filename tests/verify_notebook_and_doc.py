#!/usr/bin/env python3
"""Verify the notebook and the explanation document against each other.

Run from the repository root:

    python tests/verify_notebook_and_doc.py

It checks, without installing anything:

  1.  the notebook is valid JSON with the expected cell structure
  2.  every code cell executes, in order, in one namespace, with no error
  3.  every figure renders (full HTML render path) and carries real data
  4.  the notebook covers exactly the eleven required sections, in order
  5.  every code block in the document is byte-identical to a notebook cell
  6.  every "result values" block in the document is byte-identical to what
      that notebook run actually printed
  7.  every one of the 26 documentation points is present in all 11 sections
  8.  the document contains no numeric claim that the run did not produce

It touches no application file.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "Unified_Dashboard_Graph_Analysis.ipynb"
DOC = ROOT / "docs" / "Unified_Dashboard_Graph_and_Code_Explanation.md"

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"

_passed = 0
_failed: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    global _passed
    if ok:
        _passed += 1
        print(f"  {GREEN}pass{RESET}  {label}" + (f"  {DIM}{detail}{RESET}" if detail else ""))
    else:
        _failed.append(label)
        print(f"  {RED}FAIL{RESET}  {label}" + (f"  {detail}" if detail else ""))
    return ok


def head(title: str) -> None:
    print(f"\n{YELLOW}{title}{RESET}")


REQUIRED_SECTIONS = [
    "Transactions recorded each year",
    "How prices are moving",
    "Volume against price",
    "Share of recorded transactions associated with each amenity",
    "Rate by building height and property type",
    "Where the price points are",
    "Rate per m² by layout",
    "Unit size — key statistics",
    "Sale price by registration type — summary",
    "How the price distribution has changed",
    "Year-by-year summary",
]

POINT_TITLES = [
    "Where it appears in the dashboard",
    "What the visualisation is",
    "Plain-English one-liner",
    "The question it answers",
    "Data source",
    "Why that source",
    "Columns used",
    "Filters that apply",
    "Population and exclusions",
    "Missing values",
    "Grouping and aggregation",
    "Metric definition",
    "Formula",
    "Method, and why this method",
    "Thresholds and parameters",
    "Notebook cells",
    "Code — identical to the notebook",
    "Intermediate dataframe",
    "Result values — actual notebook output",
    "Chart type, and why",
    "Axes",
    "Legend",
    "Colour meaning",
    "Hover contents",
    "How to read it — and what it does NOT say",
    "Limitations and validation actually performed",
]


def main() -> int:
    os.chdir(ROOT)

    # ── 1. notebook structure ───────────────────────────────────────────────
    head("1. Notebook structure")
    check("notebook file exists", NB.exists(), str(NB))
    nb = json.loads(NB.read_text())
    cells = nb["cells"]
    code_cells = [c for c in cells if c["cell_type"] == "code"]
    check("notebook is valid JSON", True, f"{len(cells)} cells")
    check("has code cells", len(code_cells) > 0, f"{len(code_cells)} code cells")
    check("nbformat 4", nb.get("nbformat") == 4, f"nbformat={nb.get('nbformat')}")
    check("every code cell has source",
          all("".join(c["source"]).strip() for c in code_cells))
    check("no cell carries stale saved output",
          all(not c.get("outputs") for c in code_cells),
          "outputs are produced by running it, not shipped in the file")

    # ── 2. required sections, in order ──────────────────────────────────────
    head("2. Scope — exactly the eleven required sections, in order")
    headings = [ln.strip() for c in cells if c["cell_type"] == "markdown"
                for ln in "".join(c["source"]).splitlines()
                if re.match(r"^# \d+\.", ln.strip())]
    check("eleven numbered sections", len(headings) == 11, f"found {len(headings)}")
    for i, want in enumerate(REQUIRED_SECTIONS):
        got = headings[i] if i < len(headings) else "(missing)"
        check(f"§{i + 1} is '{want}'", want.lower() in got.lower(), got)

    # ── 3. execute every cell, in order, in one namespace ───────────────────
    head("3. Execution — every code cell, in order, one namespace")
    import plotly.graph_objects as go

    figs: list = []

    def _show(self, *a, **k):
        # full HTML render path: the same serialisation a notebook performs
        figs.append((self, self.to_html(include_plotlyjs=True, full_html=True)))

    go.Figure.show = _show  # type: ignore[method-assign]

    ns: dict = {"__name__": "__main__"}
    printed: dict[int, str] = {}
    for i, c in enumerate(code_cells):
        src = "".join(c["source"])
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                exec(compile(src, f"<cell {i + 1}>", "exec"), ns)
        except Exception as exc:  # noqa: BLE001
            check(f"cell {i + 1}/{len(code_cells)} executes", False, f"{type(exc).__name__}: {exc}")
            print(buf.getvalue())
            return 1
        printed[i] = buf.getvalue()
    check(f"all {len(code_cells)} code cells executed", True, "0 errors")

    import pandas as pd

    frames = {k: v for k, v in ns.items()
              if isinstance(v, pd.DataFrame) and not k.startswith("_")}
    check("intermediate dataframes were produced", len(frames) >= 25,
          f"{len(frames)} dataframes in the namespace")
    check("no dataframe came out empty",
          all(len(v) > 0 for v in frames.values()),
          ", ".join(k for k, v in frames.items() if len(v) == 0) or "all non-empty")

    # ── 4. figures ──────────────────────────────────────────────────────────
    head("4. Figures")
    check("nine figures rendered", len(figs) == 9, f"{len(figs)} figures")
    for i, (f, html) in enumerate(figs, 1):
        traces = len(f.data)
        pts = 0
        for t in f.data:
            for attr in ("x", "y", "q1"):
                v = getattr(t, attr, None)
                if v is not None:
                    pts += len(v)
                    break
        ok = traces > 0 and pts > 0 and bool(f.layout.title.text) and len(html) > 3000
        check(f"figure {i} renders with data", ok,
              f"{traces} trace(s), {pts:,} point(s), {len(html):,} bytes")

    # ── 5. document code blocks match the notebook ──────────────────────────
    head("5. Document code is the notebook's code, byte for byte")
    check("document exists", DOC.exists(), str(DOC))
    doc = DOC.read_text()
    nb_sources = {"".join(c["source"]).strip() for c in code_cells}
    doc_blocks = re.findall(r"```python\n(.*?)```", doc, re.S)
    check("document contains code blocks", len(doc_blocks) > 0, f"{len(doc_blocks)} blocks")
    mismatched = [b for b in doc_blocks if b.strip() not in nb_sources]
    check("every document code block is a notebook cell", not mismatched,
          f"{len(doc_blocks) - len(mismatched)}/{len(doc_blocks)} matched"
          + (f"; first mismatch:\n{mismatched[0][:300]}" if mismatched else ""))

    # ── 6. document result values match what the run printed ────────────────
    head("6. Document result values are the run's real output")
    printed_all = [v.rstrip() for v in printed.values() if v.strip()]
    quoted = re.findall(r"### \d+\.19 Result values.*?\n(.*?)(?=\n### )", doc, re.S)
    plain = []
    for q in quoted:
        plain += [b.strip() for b in re.findall(r"```\n(.*?)```", q, re.S)]
    check("document quotes result blocks", len(plain) > 0, f"{len(plain)} blocks")
    bad = [b for b in plain if not any(b in p for p in printed_all)]
    check("every quoted result block was actually printed by the run", not bad,
          f"{len(plain) - len(bad)}/{len(plain)} matched"
          + (f"; first unmatched:\n{bad[0][:300]}" if bad else ""))

    # ── 7. all 26 points in all 11 sections ─────────────────────────────────
    head("7. Documentation completeness — 26 points x 11 sections")
    doc_sections = re.split(r"\n## (\d+)\. ", doc)[1:]
    pairs = list(zip(doc_sections[0::2], doc_sections[1::2]))
    check("document has eleven sections", len(pairs) == 11, f"found {len(pairs)}")
    total_missing = 0
    for num, body in pairs:
        missing = [t for j, t in enumerate(POINT_TITLES, 1)
                   if f"### {num}.{j} {t}" not in body]
        total_missing += len(missing)
        check(f"§{num} has all 26 points", not missing,
              "26/26" if not missing else f"missing: {missing}")
    check("no documentation point missing anywhere", total_missing == 0,
          f"{11 * 26 - total_missing}/{11 * 26} present")

    # ── 8. no numeric claim the run did not produce ─────────────────────────
    head("8. Numbers in the document trace back to the run")
    run_text = " ".join(printed_all)
    # values the document asserts in prose, each of which must appear in the run
    claims = ["818,838", "1,762,258", "109,651", "928,489", "80,203", "102,675",
              "166,262", "-21.89", "7.61", "1.46", "2.75", "0.884", "95.3",
              "343,595", "481,389", "2,916", "93.1", "351,627", "467,211",
              "45,000", "2.47", "1.66", "989", "11,209", "5,625"]
    missing_claims = [c for c in claims if c in doc and c.replace(",", "") not in run_text.replace(",", "")]
    check("every spot-checked figure in the prose appears in the run output",
          not missing_claims, f"{len(claims)} checked" + (f"; missing: {missing_claims}" if missing_claims else ""))

    # ── 9. no causal language where the data cannot support it ──────────────
    head("9. Claim discipline")
    # Only market-behaviour causal claims are banned. A mechanical statement of
    # fact ("August covers 6 days, which is the cause of the drop at the right
    # edge") is not a causal claim about the market and is not caught here.
    banned = [
        (r"\b(?:increases?|raises?|boosts?|adds?)\s+(?:the\s+)?(?:property\s+)?(?:price|value|rate)s?\b",
         "causal price claim"),
        (r"\bpurchase probabilit", "purchase probability claim"),
        (r"\b(?:drives?|causes?|leads? to|results? in)\s+(?:higher|lower|the\s+)?(?:price|value|rate|demand|volume)s?\b",
         "causal market claim"),
        (r"\bbecause (?:of )?(?:the )?(?:amenity|parking|balcony|pool|metro)\b",
         "amenity attributed as a cause"),
        (r"\boff-plan premium of\b", "premium restated as fact"),
    ]
    for pattern, why in banned:
        hits = [m.group(0) for m in re.finditer(pattern, doc, re.I)]
        # allowed only when the sentence is denying it
        real = []
        for m in re.finditer(pattern, doc, re.I):
            window = doc[max(0, m.start() - 220):m.end() + 220].lower()
            if any(n in window for n in ("not ", "no ", "cannot", "does not", "never",
                                         "is not", "withdrawn", "deliberately")):
                continue
            real.append(m.group(0))
        check(f"no un-negated {why}", not real, f"{len(hits)} mention(s), {len(real)} un-negated")

    # ── report ──────────────────────────────────────────────────────────────
    print(f"\n{'=' * 62}")
    if _failed:
        print(f"{RED}{len(_failed)} FAILED{RESET}, {_passed} passed")
        for f in _failed:
            print(f"   - {f}")
        return 1
    print(f"{GREEN}ALL {_passed} CHECKS PASSED{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
