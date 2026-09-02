"""
Builds the Sharjah Market Analytics PDF from the report-source registry.

Every value in this document comes from `regions.sharjah.sources` — the same
registry the dashboard reads. Nothing is hard-coded, recomputed, or drawn
from Dubai / Abu Dhabi.

The report uses the platform's existing `pdf_report` infrastructure so it
looks identical to the Dubai report — same cover, same typography, same table
styling, same page numbering.
"""

from __future__ import annotations

import numpy as np

from platform_core import pdf_report as R
from regions.sharjah import sources as S


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY
# ─────────────────────────────────────────────────────────────────────────────


def build() -> bytes:
    """Render the Sharjah PDF and return the bytes."""
    rep, buf = R.new_document(
        title="Sharjah Market Analytics Report",
        subtitle=f"{S.SAVILLS_Q1_2026['period']} · Report-sourced",
        footer_note=f"Sharjah analytics · {S.SAVILLS_Q1_2026['period']}",
    )

    rep.title_page(
        meta=[
            ("Reporting period", S.SAVILLS_Q1_2026["period"]),
            ("Primary source", S.SAVILLS_Q1_2026["publisher"]),
            ("Secondary sources", "Marmore / Markaz (2 reports)"),
            ("Scope", "Sharjah residential market"),
            ("Generated", R.stamp()),
        ],
        lede=(
            "A report-sourced snapshot of Sharjah's residential market, prepared from "
            "three published research reports. Nothing in this document is invented, "
            "inferred from Dubai or Abu Dhabi, or presented as a Sharjah value when it "
            "is not. Where a source chart is represented visually without numeric "
            "labels, only the values the source states in numbers are reproduced."
        ),
    )

    rep.new_page()
    _executive_summary(rep)
    _key_stats(rep)
    _monthly_dynamics(rep)
    _transaction_value(rep)
    _transaction_volume(rep)
    _investors(rep)
    _property_type(rep)
    _top_areas(rep)
    _notable_transactions(rep)
    _new_projects(rep)
    _regulatory(rep)
    _infrastructure(rep)
    _near_term(rep)
    _fundamentals(rep)
    _outlook(rep)
    _methodology(rep)

    return R.finish(rep, buf)


# ─────────────────────────────────────────────────────────────────────────────
# SECTIONS
# ─────────────────────────────────────────────────────────────────────────────


def _executive_summary(rep) -> None:
    rep.h1("Sharjah Market Overview")
    rep.body(S.SHARJAH_OVERVIEW_NARRATIVE)
    rep.body(f"Source: {S.SAVILLS_Q1_2026['citation']}", size=7.4, colour=R.MUTED)


def _key_stats(rep) -> None:
    rep.h1("Key Stats — Q1 2026", needs=1.4)
    rep.kpis([(k["label"], k["value"]) for k in S.SHARJAH_KEY_STATS], per_row=2)
    rows = [[k["label"], k["value"], k["change"], k["period"]] for k in S.SHARJAH_KEY_STATS]
    rep.table(
        ["Metric", "Value", "Change", "Period"], rows,
        widths=[0.32, 0.20, 0.30, 0.18],
        caption=f"Source: {S.SAVILLS_Q1_2026['citation']}",
    )


def _monthly_dynamics(rep) -> None:
    rep.h1("Monthly Dynamics — Q1 2026", needs=1.2)
    for m in S.SHARJAH_MONTHLY_DYNAMICS:
        rep.h2(m["month"], needs=0.6)
        rep.body(f"{m['headline']} {m['note']}")
    rep.body(f"Source: {S.SAVILLS_Q1_2026['citation']}", size=7.4, colour=R.MUTED)


def _transaction_value(rep) -> None:
    rep.h1("Transaction Value", needs=3.1)
    rep.body(
        "The Savills report presents a quarterly transaction-value chart across 2024, "
        "2025 and Q1 2026, with Q4 2025 explicitly marked as an estimate derived from "
        "the official full-year figure (AED 65.6 billion). Only values the source "
        "states in numbers are reproduced here."
    )
    pts = S.SHARJAH_TRANSACTION_VALUE_POINTS

    def draw(ax):
        labels = [p["period"] for p in pts]
        values = [p["value_aed_billion"] for p in pts]
        colours = [R.AMBER if "post-Q1" in p["status"]
                   else (R.MUTED if p["status"] == "derived" else R.ACCENT)
                   for p in pts]
        ax.bar(labels, values, color=colours, width=0.62)
        ax.set_ylabel("AED billion", fontsize=8, color=R.INK)
        ax.tick_params(axis="x", labelsize=7.2)
        for i, v in enumerate(values):
            ax.text(i, v + max(values) * 0.02, f"{v:.1f}",
                    ha="center", va="bottom", fontsize=7.5, color=R.INK)

    rep.chart(draw, height=2.6, title="Published transaction-value reference points",
              caption=S.SHARJAH_TRANSACTION_VALUE_CHART_NOTE)

    rows = [[p["period"], f"AED {p['value_aed_billion']:.1f}B", p["status"], p["note"]]
            for p in pts]
    rep.table(["Period", "Value", "Status", "Note"], rows,
              widths=[0.15, 0.14, 0.20, 0.51],
              caption=f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _transaction_volume(rep) -> None:
    rep.h1("Transaction Volume", needs=3.1)
    rep.body(
        "The Savills report presents a quarterly transaction-count chart across the "
        "same period as the value chart, with certain quarters estimated from official "
        "H1, 9M and full-year cumulative releases. Only values the source states in "
        "numbers are reproduced here."
    )
    pts = S.SHARJAH_TRANSACTION_VOLUME_POINTS

    def draw(ax):
        labels = [p["period"] for p in pts]
        values = [p["transactions"] for p in pts]
        colours = [R.AMBER if "post-Q1" in p["status"]
                   else (R.MUTED if p["status"] == "derived" else R.ACCENT_2)
                   for p in pts]
        ax.bar(labels, values, color=colours, width=0.62)
        ax.set_ylabel("Transactions", fontsize=8, color=R.INK)
        ax.tick_params(axis="x", labelsize=7.2)
        for i, v in enumerate(values):
            ax.text(i, v + max(values) * 0.02, f"{v:,}",
                    ha="center", va="bottom", fontsize=7.5, color=R.INK)

    rep.chart(draw, height=2.6, title="Published transaction-volume reference points",
              caption=S.SHARJAH_TRANSACTION_VOLUME_CHART_NOTE)

    rows = [[p["period"], f"{p['transactions']:,}", p["status"], p["note"]]
            for p in pts]
    rep.table(["Period", "Transactions", "Status", "Note"], rows,
              widths=[0.15, 0.14, 0.20, 0.51],
              caption=f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _investors(rep) -> None:
    rep.h1("Investment by Nationality — Q1 2026", needs=3.0)
    rep.body(
        "The composition of investment in Sharjah in Q1 2026 by buyer origin, "
        "as reported by Savills, in AED billion."
    )
    items = S.SHARJAH_INVESTOR_NATIONALITY

    def draw(ax):
        labels = [d["label"] for d in items]
        values = [d["value_aed_billion"] for d in items]
        y_pos = np.arange(len(labels))[::-1]
        ax.barh(y_pos, values, color=R.SERIES[: len(items)], height=0.62)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=7.5)
        ax.set_xlabel("AED billion", fontsize=8, color=R.INK)
        for pos, v in zip(y_pos, values):
            ax.text(v + max(values) * 0.015, pos, f"AED {v:.1f}B",
                    va="center", ha="left", fontsize=7.5, color=R.INK)

    rep.chart(draw, height=2.4, title="Investment by nationality (AED billion)",
              caption=f"Source: {S.SAVILLS_Q1_2026['citation']}")

    rows = [[d["label"], f"AED {d['value_aed_billion']:.1f}B"] for d in items]
    rep.table(["Nationality", "Trading value"], rows, widths=[0.55, 0.45],
              caption="Values are shown in the order the Savills report presents them.")


def _property_type(rep) -> None:
    rep.h1("Sales by Property Type — Q1 2026", needs=2.8)
    rep.body(S.SHARJAH_PROPERTY_TYPE_NOTE)
    items = S.SHARJAH_PROPERTY_TYPE_SHARE

    def draw(ax):
        labels = [d["label"] for d in items]
        values = [d["share_pct"] for d in items]
        ax.bar(labels, values, color=R.SERIES[: len(items)], width=0.58)
        ax.set_ylabel("Share of transactions (%)", fontsize=8, color=R.INK)
        ax.set_ylim(0, max(values) * 1.25)
        for i, v in enumerate(values):
            ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", va="bottom",
                    fontsize=7.5, color=R.INK)

    rep.chart(draw, height=2.4, title="Share of residential sales transactions (%)",
              caption=f"Source: {S.SAVILLS_Q1_2026['citation']}. Percentages do not "
                      f"sum to 100% and are not normalised.")


def _top_areas(rep) -> None:
    rep.h1("Top Performing Areas — Q1 2026", needs=3.0)
    rep.body(
        "The top-five performing areas in Sharjah in Q1 2026, ranked by trading "
        "value, as reported by Savills."
    )
    items = S.SHARJAH_TOP_AREAS

    def draw(ax):
        areas = [d["area"] for d in items]
        values = [d["value_aed_million"] for d in items]
        y_pos = np.arange(len(areas))[::-1]
        ax.barh(y_pos, values, color=R.ACCENT, height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(areas, fontsize=7.5)
        ax.set_xlabel("Trading value (AED million)", fontsize=8, color=R.INK)
        for pos, v in zip(y_pos, values):
            ax.text(v + max(values) * 0.015, pos, f"AED {v:,}M",
                    va="center", ha="left", fontsize=7.2, color=R.INK)

    rep.chart(draw, height=2.7, title="Top performing areas by trading value (AED million)",
              caption=f"Source: {S.SAVILLS_Q1_2026['citation']}. Savills notes the "
                      f"January figure for Muwaileh Commercial was AED 1.1B; the "
                      f"chart shows the Q1 aggregate.")

    rows = [[a["rank"], a["area"], f"AED {a['value_aed_million']:,}M", a.get("note", "—")]
            for a in items]
    rep.table(["Rank", "Area", "Value", "Note"], rows,
              widths=[0.10, 0.30, 0.18, 0.42],
              caption="Rank and value are reproduced verbatim from the source.")


def _notable_transactions(rep) -> None:
    rep.h1("Notable Transactions — Q1 2026", needs=1.4)
    rows = [[t["area"], t["type"], t["transaction_type"], f"AED {t['value_aed_million']:,}M"]
            for t in S.SHARJAH_NOTABLE_TRANSACTIONS]
    rep.table(["Area", "Type", "Transaction type", "Value"], rows,
              widths=[0.28, 0.24, 0.24, 0.24],
              caption=f"Source: {S.SAVILLS_Q1_2026['citation']}. "
                      f"Individual deals reported by Savills — no additional deals "
                      f"have been added from other sources.")


def _new_projects(rep) -> None:
    rep.h1("New Project Registrations — Q1 2026", needs=1.6)
    cards = []
    for item in S.SHARJAH_NEW_PROJECTS:
        val = item["value"]
        if item["unit"].startswith("AED"):
            display = f"AED {val}B"
        else:
            display = f"{val}"
        cards.append((item["metric"], display))
    rep.kpis(cards, per_row=2)
    rows = [[i["metric"], f"{i['value']}", i["unit"], i["period"]]
            for i in S.SHARJAH_NEW_PROJECTS]
    rep.table(["Metric", "Value", "Unit", "Period"], rows,
              widths=[0.34, 0.14, 0.30, 0.22],
              caption=f"Source: {S.SAVILLS_Q1_2026['citation']}.")


def _regulatory(rep) -> None:
    rep.h1("Regulatory Landscape", needs=1.0)
    rep.body(
        "Sharjah-specific regulation drawn from the Savills Q1 2026 report and the two "
        "Marmore / Markaz UAE reports. Only items explicitly attributable to Sharjah "
        "are included; Dubai RERA rules and DIFC rules are deliberately excluded."
    )
    for reg in S.SHARJAH_REGULATORY:
        rep.h2(reg["title"], needs=1.0)
        rep.body(f"Period: {reg['period']}")
        rep.body(reg["summary"])
        rep.body(f"Market relevance. {reg['impact']}")
        rep.body(f"Source: {reg['source']['citation']}", size=7.4, colour=R.MUTED)


def _infrastructure(rep) -> None:
    rep.h1("Infrastructure", needs=1.0)
    rep.body(
        "Sharjah-specific infrastructure programmes identified in the Savills Q1 2026 "
        "report."
    )
    for item in S.SHARJAH_INFRASTRUCTURE:
        rep.h2(item["title"], needs=0.7)
        rep.body(f"{item['expected']}")
        rep.body(item["detail"])
        rep.body(f"Source: {item['source']['citation']}", size=7.4, colour=R.MUTED)


def _near_term(rep) -> None:
    rep.h1("Near-term Conditions", needs=1.0)
    rep.bullets(list(S.SHARJAH_NEAR_TERM))
    p = S.SHARJAH_APRIL_POST_Q1
    rep.h2(p["period"], needs=0.6)
    rep.body(f"{p['value']}. {p['note']}")
    rep.body(f"Source: {p['source']['citation']}", size=7.4, colour=R.MUTED)


def _fundamentals(rep) -> None:
    rep.h1("Underlying Market Fundamentals", needs=1.0)
    rep.bullets(list(S.SHARJAH_FUNDAMENTALS))
    rep.h2("Supply pipeline — masterplan developments named by Savills", needs=0.6)
    rep.body(", ".join(m["name"] for m in S.SHARJAH_MASTERPLANS) + ".")
    rep.body(f"Source: {S.SAVILLS_Q1_2026['citation']}", size=7.4, colour=R.MUTED)


def _outlook(rep) -> None:
    rep.h1("Outlook — Forward Signals", needs=1.2)
    rep.body(
        "The three forward signals Savills lists at the end of the Q1 2026 report. "
        "Conditional language such as 'expected', 'if delivered' and 'may' is "
        "preserved."
    )
    for sig in S.SHARJAH_FORWARD_SIGNALS:
        rep.h2(f"Signal 0{sig['number']}", needs=0.6)
        rep.body(sig["text"])
    rep.body(f"Source: {S.SAVILLS_Q1_2026['citation']}", size=7.4, colour=R.MUTED)


def _methodology(rep) -> None:
    rep.h1("Sources & Methodology", needs=1.5)
    rep.body(
        "Every figure and every direct statement in this document is drawn from one "
        "of three published research reports. No Dubai, Abu Dhabi, other-emirate or "
        "UAE-wide value is used. Where a source chart shows values visually without "
        "numeric labels, only the values the source states in numbers are reproduced; "
        "no value is reverse-engineered from a chart image."
    )

    rep.h2("Reports used", needs=0.9)
    rep.bullets([f"{r['publisher']} — {r['title']} ({r['period']})."
                 for r in S.all_sources()])

    rep.h2("Per-section provenance", needs=1.1)
    rows = [[section, cite] for section, cite in S.source_index()]
    rep.table(["Section", "Source"], rows, widths=[0.30, 0.70],
              caption="Each dashboard section on the Sharjah page maps to the source "
                      "record listed here.")

    rep.h2("Scope and exclusions", needs=1.0)
    rep.bullets([
        "Only Sharjah-attributable content from the three source reports is included.",
        "No Dubai-only, Abu Dhabi-only, other-emirate-only or UAE-wide value is "
        "presented as a Sharjah value.",
        "Where quarterly bars are shown visually in the source without numeric "
        "labels, the individual bar values are not tabulated in this report.",
        "Estimated quarters (e.g., Q4 2025 derived by Savills from an official "
        "full-year figure) are labelled as estimates.",
        "April 2026 is labelled as a post-Q1 early indicator and is never mixed "
        "into any Q1 2026 aggregate.",
    ])
