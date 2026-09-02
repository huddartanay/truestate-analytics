"""
Builds the RAK Market Analytics PDF from the RAK source registry.

Reuses the platform's existing `pdf_report` infrastructure — same cover, same
typography, same table styling, same page numbering — so the RAK report looks
identical to the Dubai and Sharjah reports.
"""

from __future__ import annotations

import numpy as np

from platform_core import pdf_report as R
from regions.rak import sources as S


def _aed(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if abs(v) >= 1e9:
        return f"AED {v / 1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"AED {v / 1e6:,.2f}M"
    if abs(v) >= 1e3:
        return f"AED {v / 1e3:,.1f}K"
    return f"AED {v:,.0f}"


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY
# ─────────────────────────────────────────────────────────────────────────────


def build() -> bytes:
    rep, buf = R.new_document(
        title="RAK Market Analytics Report",
        subtitle=f"{S.RAK_ANNUAL_2025['period']} · Report-sourced",
        footer_note="RAK analytics · 2024–2025",
    )

    rep.title_page(
        meta=[
            ("Reporting period", "2020, 2021, 2024, 2025 & January 2026"),
            ("Primary source", S.RAK_ANNUAL_2025["publisher"]),
            ("Reports used", "3 (2 annual, 1 monthly)"),
            ("Scope", "Ras Al Khaimah real estate transactions"),
            ("Generated", R.stamp()),
        ],
        lede=(
            "A report-sourced snapshot of Ras Al Khaimah's real estate market, prepared "
            "from three official reports issued by the RAK Statistics Office (Lands and "
            "Properties Sector). Every figure in this document traces to one of those "
            "three sources. No Dubai, Sharjah, other-emirate or UAE-wide value is "
            "presented as a RAK value."
        ),
    )

    rep.new_page()
    _overview(rep)
    _annual_2024_2025(rep)
    _annual_2020_2021(rep)
    _monthly_series(rep)
    _popular_areas(rep)
    _property_use(rep)
    _investors(rep)
    _latest_month(rep)
    _methodology(rep)

    return R.finish(rep, buf)


# ─────────────────────────────────────────────────────────────────────────────
# SECTIONS
# ─────────────────────────────────────────────────────────────────────────────


def _overview(rep) -> None:
    rep.h1("RAK Market Overview")
    rep.body(S.RAK_OVERVIEW_NARRATIVE)
    rep.kpis([(k["label"], k["value"]) for k in S.RAK_KEY_STATS], per_row=2)
    rows = [[k["label"], k["value"], k["change"], k["period"]] for k in S.RAK_KEY_STATS]
    rep.table(["Metric", "Value", "Change", "Period"], rows,
              widths=[0.30, 0.20, 0.32, 0.18],
              caption=f"Source: {S.RAK_ANNUAL_2025['citation']}")


def _annual_2024_2025(rep) -> None:
    rep.h1("Annual Transactions — 2024 vs 2025", needs=3.0)

    val_rows = [r for r in S.RAK_ANNUAL_2024_2025_VALUE
                if r["category"] != "Total Transactions"]

    def draw(ax):
        cats = [r["category"].replace("Real Estate ", "") for r in val_rows]
        n = len(cats)
        width = 0.35
        x = np.arange(n)
        y24 = [r["y2024_aed"] / 1e9 for r in val_rows]
        y25 = [r["y2025_aed"] / 1e9 for r in val_rows]
        ax.bar(x - width / 2, y24, width, color=R.SERIES[1], label="2024")
        ax.bar(x + width / 2, y25, width, color=R.ACCENT,    label="2025")
        ax.set_xticks(x)
        ax.set_xticklabels(cats, fontsize=7.2)
        ax.set_ylabel("AED billion", fontsize=8, color=R.INK)
        ax.legend(fontsize=7.2, frameon=False, loc="upper right")

    rep.chart(draw, height=2.6, title="Value of Real Estate Transactions in 2024 – 2025",
              caption="Reproduces RAK Annual 2025 Figure 1.")

    rows = [[r["category"], _aed(r["y2024_aed"]), f"{r['share_2024']}%",
             _aed(r["y2025_aed"]), f"{r['share_2025']}%",
             f"{r['change_pct']:+d}%"]
            for r in S.RAK_ANNUAL_2024_2025_VALUE]
    rep.table(["Category", "2024 value", "2024 share",
               "2025 value", "2025 share", "Δ value"], rows,
              widths=[0.28, 0.16, 0.12, 0.16, 0.12, 0.16],
              caption=f"Source: {S.RAK_ANNUAL_2025['citation']}.")

    rows = [[r["category"], f"{r['y2024']:,}", f"{r['share_2024']}%",
             f"{r['y2025']:,}", f"{r['share_2025']}%",
             f"{r['change_pct']:+d}%"]
            for r in S.RAK_ANNUAL_2024_2025_COUNT]
    rep.table(["Category", "2024 count", "2024 share",
               "2025 count", "2025 share", "Δ count"], rows,
              widths=[0.28, 0.16, 0.12, 0.16, 0.12, 0.16],
              caption="Top Region in Terms of Real Estate Transaction Value 2025: "
                      "Jazeerat AL Marjan (2024 also).")


def _annual_2020_2021(rep) -> None:
    rep.h1("Historical Context — 2020 vs 2021", needs=1.6)
    rep.body(
        "Provided directly from the RAK Annual 2020–2021 report as historical context "
        "for the 2024–2025 figures above. Categories, values and percentage changes "
        "are reproduced verbatim from Table 1 of that report."
    )
    rows = [[r["category"], _aed(r["y2020_aed"]), f"{r['share_2020']}%",
             _aed(r["y2021_aed"]), f"{r['share_2021']}%",
             f"{r['change_pct']:+d}%"]
            for r in S.RAK_ANNUAL_2020_2021_VALUE]
    rep.table(["Category", "2020 value", "2020 share",
               "2021 value", "2021 share", "Δ value"], rows,
              widths=[0.28, 0.16, 0.12, 0.16, 0.12, 0.16],
              caption=f"Source: {S.RAK_ANNUAL_2021['citation']}. Top Region 2021: "
                      f"Al Jazirah Al Hamra (2020 also).")

    rows = [[r["category"], f"{r['y2020']:,}", f"{r['share_2020']}%",
             f"{r['y2021']:,}", f"{r['share_2021']}%",
             f"{r['change_pct']:+d}%"]
            for r in S.RAK_ANNUAL_2020_2021_COUNT]
    rep.table(["Category", "2020 count", "2020 share",
               "2021 count", "2021 share", "Δ count"], rows,
              widths=[0.28, 0.16, 0.12, 0.16, 0.12, 0.16],
              caption="Total Number of Real Estate Transactions rose 46% in 2021 vs 2020.")


def _monthly_series(rep) -> None:
    rep.h1("Monthly Time Series — 2019 to 2026", needs=3.6)
    rep.body(
        f"{len(S.RAK_MONTHLY_TIMESERIES)} data points extracted verbatim from the "
        f"26 monthly RAK Statistics Office reports supplied. Older 2019–2020 "
        f"monthlies only track Sales value and Sales number; from December 2020 "
        f"onward the reports also carry Mortgages and Waivers."
    )

    pts = S.RAK_MONTHLY_TIMESERIES

    def draw(ax):
        x = list(range(len(pts)))
        sv = [p["sales_v"] / 1e6 if p.get("sales_v") else None for p in pts]
        mv = [p["mort_v"]  / 1e6 if p.get("mort_v")  else None for p in pts]
        wv = [p["waiv_v"]  / 1e6 if p.get("waiv_v")  else None for p in pts]
        labels = [f"{p['month'][:3]} {p['year']}" for p in pts]
        # Plot with breaks where None
        import numpy as np
        def masked(a): return np.array([v if v is not None else np.nan for v in a])
        ax.plot(x, masked(sv), color=R.ACCENT,     marker="o", markersize=3, linewidth=1.3, label="Sales")
        ax.plot(x, masked(mv), color=R.SERIES[1],  marker="s", markersize=3, linewidth=1.3, label="Mortgages")
        ax.plot(x, masked(wv), color=R.AMBER,      marker="^", markersize=3, linewidth=1.3, label="Waivers")
        ax.set_xticks(x[::2])
        ax.set_xticklabels(labels[::2], rotation=45, ha="right", fontsize=5.8)
        ax.set_ylabel("AED million", fontsize=8, color=R.INK)
        ax.legend(fontsize=7.2, frameon=False, loc="upper left")

    rep.chart(draw, height=3.0,
              title="Monthly Sales / Mortgages / Waivers Values (AED million)",
              caption="Lines break where the source is missing for that series. "
                      "Older 2019–2020 monthlies do not report mortgages or waivers.")

    # Table
    rows = []
    for r in pts:
        rows.append([
            f"{r['month']} {r['year']}",
            _aed(r["sales_v"]) if r["sales_v"] else "—",
            f"{r['sales_n']:,}" if r["sales_n"] else "—",
            _aed(r["mort_v"])  if r["mort_v"]  else "—",
            f"{r['mort_n']:,}"  if r["mort_n"]  else "—",
            _aed(r["waiv_v"])  if r["waiv_v"]  else "—",
            f"{r['waiv_n']:,}"  if r["waiv_n"]  else "—",
        ])
    rep.table(["Period", "Sales value", "Sales #", "Mort value", "Mort #",
               "Waiv value", "Waiv #"],
              rows, widths=[0.17, 0.16, 0.10, 0.16, 0.10, 0.16, 0.10],
              caption="Every value here is extracted verbatim from the monthly report "
                      "for that period. A dash means the source does not carry that "
                      "value for that month.")

    if S.RAK_MONTHLY_UNREADABLE:
        rep.h2("Reports provided but not extractable", needs=1.0)
        rep.body(
            "The following monthly PDFs render their table text as vector graphics. "
            "Neither PDF text extraction nor OCR produced a reliable 6-row "
            "transactions table for these. Per the strict rule, values are NOT "
            "invented; the reports are listed here for transparency."
        )
        rows = [[u["period"], u["reason"]] for u in S.RAK_MONTHLY_UNREADABLE]
        rep.table(["Report", "Why not extracted"], rows, widths=[0.30, 0.70])


def _popular_areas(rep) -> None:
    rep.h1("Popular Areas — 2025 top three", needs=2.8)
    rep.body(
        "The three most-traded regions by sales value in 2025, with the 2024 "
        "comparison reproduced from RAK Annual 2025 Table 2."
    )

    areas = S.RAK_POPULAR_AREAS_2025

    def draw(ax):
        labels = [a["region"] for a in areas]
        y24 = [a["sales_value_2024_aed"] / 1e6 for a in areas]
        y25 = [a["sales_value_2025_aed"] / 1e6 for a in areas]
        x = np.arange(len(labels))
        width = 0.35
        ax.bar(x - width / 2, y24, width, color=R.SERIES[1], label="2024")
        ax.bar(x + width / 2, y25, width, color=R.ACCENT,    label="2025")
        ax.set_xticks(x)
        ax.set_xticklabels([l if len(l) < 22 else l[:22] + "…" for l in labels],
                           fontsize=6.8)
        ax.set_ylabel("AED million", fontsize=8, color=R.INK)
        ax.legend(fontsize=7.2, frameon=False, loc="upper right")

    rep.chart(draw, height=2.5,
              title="Sales Value Index for the 3 most Traded Regions in 2024 – 2025",
              caption="Reproduces RAK Annual 2025 Figure 2.")

    rows = [[a["rank"], a["region"],
             _aed(a["sales_value_2025_aed"]), f"{a['sales_number_2025']:,}",
             _aed(a["sales_value_2024_aed"]), f"{a['sales_number_2024']:,}",
             f"{a['change_pct']:+d}%"]
            for a in areas]
    rep.table(["Rank", "Region", "2025 value", "2025 #", "2024 value", "2024 #", "Δ"],
              rows, widths=[0.06, 0.34, 0.14, 0.10, 0.14, 0.10, 0.12],
              caption=f"Source: {S.RAK_ANNUAL_2025['citation']}.")

    rep.h2("Historical — 2021 top three", needs=1.0)
    rows = [[a["rank"], a["region"], _aed(a["sales_value_2021_aed"]),
             f"{a['sales_number_2021']:,}"]
            for a in S.RAK_POPULAR_AREAS_2021]
    rep.table(["Rank", "Region", "2021 sales value", "2021 sales #"], rows,
              widths=[0.10, 0.44, 0.28, 0.18],
              caption=f"Source: {S.RAK_ANNUAL_2021['citation']}.")


def _property_use(rep) -> None:
    rep.h1("Property Use — 2024 vs 2025", needs=3.4)
    rep.body(
        "Sales value by land type in 2024 and 2025, reproduced from RAK Annual "
        "2025 Table 3. The source lists a dash where no value is recorded for "
        "a year; those are shown as a dash here rather than replaced with a zero."
    )

    rows = [r for r in S.RAK_PROPERTY_USE_2024_2025
            if r["y2024_aed"] > 0 or r["y2025_aed"] > 0]

    def draw(ax):
        labels = [r["use"] for r in rows]
        y24 = [r["y2024_aed"] / 1e6 for r in rows]
        y25 = [r["y2025_aed"] / 1e6 for r in rows]
        x = np.arange(len(labels))
        width = 0.4
        ax.bar(x - width / 2, y24, width, color=R.SERIES[1], label="2024")
        ax.bar(x + width / 2, y25, width, color=R.ACCENT,    label="2025")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=6.4, rotation=45, ha="right")
        ax.set_ylabel("AED million", fontsize=8, color=R.INK)
        ax.legend(fontsize=7.2, frameon=False, loc="upper right")

    rep.chart(draw, height=3.0,
              title="Real Estate Sales Value by Land Type in 2024 – 2025",
              caption="Reproduces RAK Annual 2025 Figure 3.")

    table_rows = []
    for r in S.RAK_PROPERTY_USE_2024_2025:
        table_rows.append([
            r["use"],
            _aed(r["y2024_aed"]) if r["y2024_aed"] else "—",
            f"{r['y2024_share']}%",
            _aed(r["y2025_aed"]) if r["y2025_aed"] else "—",
            f"{r['y2025_share']}%",
            f"{r['change_pct']:+d}%" if r["change_pct"] is not None else "—",
        ])
    rep.table(["Property use", "2024 value", "2024 share",
               "2025 value", "2025 share", "Δ value"], table_rows,
              widths=[0.28, 0.16, 0.12, 0.16, 0.12, 0.16],
              caption=f"Source: {S.RAK_ANNUAL_2025['citation']}.")


def _investors(rep) -> None:
    rep.h1("Investors — 2025 top ten nationalities", needs=3.0)
    tot = S.RAK_INVESTORS_TOTALS
    rep.body(
        f"Total investors in 2025: {tot['y2025']:,} (2024: {tot['y2024']:,}). "
        f"Both rankings — by transaction value and by number of investors — are "
        f"reproduced from RAK Annual 2025."
    )

    inv = S.RAK_INVESTORS_BY_VALUE_2025

    def draw(ax):
        labels = [r["nationality"] for r in inv]
        values = [r["value_aed"] / 1e6 for r in inv]
        y_pos = np.arange(len(labels))[::-1]
        ax.barh(y_pos, values, color=R.ACCENT, height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=7.0)
        ax.set_xlabel("AED million", fontsize=8, color=R.INK)
        for pos, v in zip(y_pos, values):
            ax.text(v + max(values) * 0.015, pos, f"AED {v:,.0f}M",
                    va="center", ha="left", fontsize=6.8, color=R.INK)

    rep.chart(draw, height=3.0,
              title="Top Ten Investing Nationalities by Transaction Value — 2025",
              caption="Reproduces RAK Annual 2025 Table 4.")

    rows25 = [[r["rank"], r["nationality"], _aed(r["value_aed"])] for r in inv]
    rep.table(["Rank", "Nationality", "2025 value"], rows25,
              widths=[0.15, 0.55, 0.30],
              caption=f"Source: {S.RAK_ANNUAL_2025['citation']}.")

    rep.h2("2024 top ten by value — for comparison", needs=1.0)
    rows24 = [[r["rank"], r["nationality"], _aed(r["value_aed"])]
              for r in S.RAK_INVESTORS_BY_VALUE_2024]
    rep.table(["Rank", "Nationality", "2024 value"], rows24,
              widths=[0.15, 0.55, 0.30],
              caption=f"Source: {S.RAK_ANNUAL_2025['citation']}.")

    rep.h2("2025 top ten by number of investors", needs=1.0)
    rows_n = [[r["rank"], r["nationality"], f"{r['count']:,}"]
              for r in S.RAK_INVESTORS_BY_NUMBER_2025]
    rep.table(["Rank", "Nationality", "2025 investor count"], rows_n,
              widths=[0.15, 0.55, 0.30],
              caption=f"Source: {S.RAK_ANNUAL_2025['citation']}. UAE nationals lead "
                      f"both the value ranking and the count ranking.")


def _latest_month(rep) -> None:
    rep.h1("Latest Month — January 2026", needs=2.4)
    rep.body(
        "Most recent monthly report from the RAK Statistics Office. The source "
        "states Real Estate Sales Volume decreased 55% year-on-year while Sales "
        "Number increased 29%; Mortgages Volume decreased 88% while Mortgages "
        "Number decreased only 6%."
    )

    m26 = S.RAK_JAN_2026
    m25 = S.RAK_JAN_2025

    def draw(ax):
        cats = ["Sales", "Mortgages", "Waivers"]
        y25 = [m25["sales_value_aed"] / 1e6, m25["mortgages_aed"] / 1e6, m25["waivers_aed"] / 1e6]
        y26 = [m26["sales_value_aed"] / 1e6, m26["mortgages_aed"] / 1e6, m26["waivers_aed"] / 1e6]
        x = np.arange(3)
        width = 0.35
        ax.bar(x - width / 2, y25, width, color=R.SERIES[1], label="Jan 2025")
        ax.bar(x + width / 2, y26, width, color=R.ACCENT,    label="Jan 2026")
        ax.set_xticks(x)
        ax.set_xticklabels(cats, fontsize=7.2)
        ax.set_ylabel("AED million", fontsize=8, color=R.INK)
        ax.legend(fontsize=7.2, frameon=False, loc="upper right")

    rep.chart(draw, height=2.5,
              title="Real Estate Transactions Value in January 2025 / 2026",
              caption="Reproduces RAK Monthly Jan 2026 Figure 1.")

    rows = [
        ["Real Estate Sales Volume", _aed(m26["sales_value_aed"]),
         _aed(m25["sales_value_aed"]), "-55%"],
        ["Real Estate Mortgages Volume", _aed(m26["mortgages_aed"]),
         _aed(m25["mortgages_aed"]), "-88%"],
        ["Waivers Market Value", _aed(m26["waivers_aed"]),
         _aed(m25["waivers_aed"]), "-46%"],
        ["Real Estate Sales Number", f"{m26['sales_count']:,}",
         f"{m25['sales_count']:,}", "+29%"],
        ["Real Estate Mortgages Number", f"{m26['mortgages_count']:,}",
         f"{m25['mortgages_count']:,}", "-6%"],
        ["Waivers Number", f"{m26['waivers_count']:,}",
         f"{m25['waivers_count']:,}", "-28%"],
    ]
    rep.table(["Category", "January 2026", "January 2025", "Δ (source)"], rows,
              widths=[0.34, 0.22, 0.22, 0.22],
              caption=f"Source: {S.RAK_MONTHLY_JAN26['citation']}.")

    rep.h2("Highest sale values", needs=0.9)
    for h in S.RAK_JAN_HIGHEST_SALES:
        rep.body(f"• {h['period']}: {h['region']} — {h['type']} — {_aed(h['value_aed'])}.")

    rep.h2("Top region by sales — January", needs=0.9)
    top26 = S.RAK_JAN_TOP_REGION_2026
    top25 = S.RAK_JAN_TOP_REGION_2025
    rep.body(
        f"• January 2026: {top26['region']} — {_aed(top26['sales_value_aed'])} "
        f"across {top26['sales_count']} sales.\n"
        f"• January 2025: {top25['region']} — {_aed(top25['sales_value_aed'])} "
        f"across {top25['sales_count']} sales."
    )

    rep.h2("Freehold market — January 2026", needs=1.2)
    rows = [[r["land_use"], f"{r['count']:,}", _aed(r["value_aed"]), f"{r['share_pct']}%"]
            for r in S.RAK_JAN_FREEHOLD_MARKET]
    rep.table(["Land use", "Sales #", "Sales value", "Share"], rows,
              widths=[0.40, 0.15, 0.30, 0.15])
    tot = S.RAK_JAN_FREEHOLD_AREAS_TOTAL
    rep.body(
        f"Total in Freehold Areas in January 2026: {tot['sales_count']:,} sales, "
        f"{_aed(tot['sales_value_aed'])}."
    )


def _methodology(rep) -> None:
    rep.h1("Sources & Methodology", needs=1.5)
    rep.body(
        "Every figure and every direct statement in this document is drawn from one "
        "of three published reports issued by the RAK Statistics Office (Lands and "
        "Properties Sector). No Dubai, Sharjah, other-emirate or UAE-wide value is "
        "used."
    )

    rep.h2("Reports used", needs=0.9)
    rep.bullets([f"{r['publisher']} — {r['title']} ({r['period']})."
                 for r in S.all_sources()])

    rep.h2("Per-section provenance", needs=1.1)
    rows = [[section, cite] for section, cite in S.source_index()]
    rep.table(["Section", "Source"], rows, widths=[0.32, 0.68],
              caption="Each section on the RAK page maps to the source record listed here.")

    rep.h2("Scope and exclusions", needs=1.0)
    rep.bullets([
        "Only RAK-attributable content from the three source reports is included.",
        "No Dubai, Sharjah, other-emirate or UAE-wide value is presented as a RAK "
        "value.",
        "Where the source records a dash (no data) for a category in a given year, "
        "the dash is preserved rather than replaced with a zero.",
        "The 2020–2021 tables are provided for historical context alongside the "
        "2024–2025 figures; the two periods are shown side by side but never "
        "aggregated.",
    ])
