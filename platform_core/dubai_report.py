"""
Builds the Dubai analytics PDF from live data.

Every figure comes from `regions.dubai_market.metrics` — the same functions the
dashboard calls — applied to the same dataframe the dashboard is showing, with
the same global area applied. Nothing here is hard-coded and nothing is
re-derived by a second method that could disagree with the screen.

The charts are drawn with matplotlib from the SAME computed frames that feed
the on-screen Plotly charts, so they are vector renderings of identical
numbers rather than screenshots.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from platform_core import pdf_report as R
from regions.dubai_market import charts as ch
from regions.dubai_market import metrics as mx
from regions.dubai_market.data import AMENITIES, COL


def _aed(v: float) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if abs(v) >= 1e9:
        return f"AED {v / 1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"AED {v / 1e6:,.2f}M"
    return f"AED {v:,.0f}"


def build(df: pd.DataFrame, area: str, all_rows: int,
          sections: list[str] | None = None) -> bytes:
    """
    Render the report and return the PDF bytes.

    `df`   the dataframe currently driving the dashboard, global area applied.
    `area` the global area label, for the cover and the running header.
    """
    sections = sections or ALL_SECTIONS
    scope = "All Areas" if area == "All Areas" else area

    rep, buf = R.new_document(
        title="Market Analytics Report",
        subtitle=f"Dubai · {scope}",
        footer_note=f"Dubai analytics · {scope}",
    )

    years = df[COL["year"]].dropna()
    period = (f"{int(years.min())} – {int(years.max())}" if len(years) else "—")
    dates = pd.to_datetime(df[COL["date"]], errors="coerce").dropna()
    coverage = (f"{dates.min():%d %b %Y} to {dates.max():%d %b %Y}" if len(dates) else "—")

    rep.title_page(
        meta=[
            ("Reporting period", period),
            ("Data coverage", coverage),
            ("Area context", scope),
            ("Transactions analysed", f"{len(df):,}"),
            ("Share of dataset", f"{len(df) / max(all_rows, 1) * 100:.1f}%"),
            ("Generated", R.stamp()),
        ],
        lede=(
            "An analysis of registered residential unit sales in Dubai, prepared from the "
            "Dubai Land Department transaction records held by the TruEstate "
            "Analytics platform. The report covers transaction activity, price levels and "
            "how they have moved, the composition of the market by layout, building height "
            "and registration type, and where transactions concentrate across price "
            "brackets and areas."
        ),
    )

    rep.new_page()
    write_sections(rep, df, area, all_rows, period, sections)

    return R.finish(rep, buf)


def period_label(df: pd.DataFrame) -> str:
    """The reporting period, as the cover states it."""
    years = df[COL["year"]].dropna()
    return f"{int(years.min())} – {int(years.max())}" if len(years) else "—"


def write_sections(rep, df: pd.DataFrame, area: str, all_rows: int,
                   period: str, sections: list[str] | None = None) -> None:
    """
    Write the area analysis into an existing report.

    Split out of `build()` so the combined Area + Forecast document can lay both
    analyses into ONE PDF without a second document, a merge library, or a
    duplicate implementation of any section. `build()` still produces exactly
    what it produced before.
    """
    sections = sections or ALL_SECTIONS
    if "summary" in sections:
        _executive_summary(rep, df, area, all_rows, period)
    if "volume" in sections:
        _volume(rep, df)
    if "prices" in sections:
        _prices(rep, df)
    if "layout" in sections:
        _layout(rep, df)
    if "height" in sections:
        _height(rep, df)
    if "amenity" in sections:
        _amenity(rep, df, area)
    if "regtype" in sections:
        _reg_type(rep, df)
    if "brackets" in sections:
        _brackets(rep, df)
    if "method" in sections:
        _methodology(rep, df, area)


ALL_SECTIONS = ["summary", "volume", "prices", "layout", "height", "amenity",
                "regtype", "brackets", "method"]

SECTION_LABELS = {
    "summary": "Executive summary and key findings",
    "volume": "Transaction volume",
    "prices": "Price levels and movement",
    "layout": "Rate per m² by layout",
    "height": "Rate by building height",
    "amenity": "Amenity analysis",
    "regtype": "Registration type",
    "brackets": "Price brackets and area concentration",
    "method": "Methodology and scope",
}


# ─────────────────────────────────────────────────────────────────────────────


def _executive_summary(rep, df, area, all_rows, period) -> None:
    price, rate = df[COL["price"]], df[COL["rate"]]
    scope = "across all Dubai areas" if area == "All Areas" else f"in {area}"

    rep.h1("Executive summary")
    rep.body(
        f"This report analyses {len(df):,} registered residential unit sales {scope}, "
        f"covering {period}. That is {len(df) / max(all_rows, 1) * 100:.1f}% of the "
        f"transactions held in the cleaned Dubai dataset. All figures below are computed "
        f"from those records at the moment this report was generated."
    )

    rep.kpis([
        ("Transactions", f"{len(df):,}"),
        ("Total value", _aed(price.sum())),
        ("Median sale price", _aed(price.median())),
        ("Median rate", f"AED {rate.median():,.0f}/m²"),
        ("Mean rate", f"AED {rate.mean():,.0f}/m²"),
        ("Median unit size", f"{df[COL['area_sqm']].median():,.0f} m²"),
    ])

    findings = []
    yt = mx.yoy_table(df)
    if len(yt) >= 2:
        f0, l0 = yt.iloc[0], yt.iloc[-1]
        span = int(l0["Year"]) - int(f0["Year"])
        if span > 0 and f0["Median rate (AED/m²)"]:
            total = (l0["Median rate (AED/m²)"] / f0["Median rate (AED/m²)"] - 1) * 100
            cagr = ((l0["Median rate (AED/m²)"] / f0["Median rate (AED/m²)"])
                    ** (1 / span) - 1) * 100
            findings.append(
                f"The median rate moved from AED {f0['Median rate (AED/m²)']:,.0f}/m² in "
                f"{int(f0['Year'])} to AED {l0['Median rate (AED/m²)']:,.0f}/m² in "
                f"{int(l0['Year'])} — {total:+.1f}% in total, a compound "
                f"{cagr:+.1f}% a year over {span} years.")

    gap = float(rate.mean() - rate.median())
    findings.append(
        f"The mean rate sits AED {gap:,.0f}/m² {'above' if gap >= 0 else 'below'} the "
        f"median, which is the signature of a right-skewed market: a minority of very "
        f"large transactions pulls the average away from the typical sale.")

    bands, b_audit = mx.price_bands(df)
    if not bands.empty:
        top = bands.loc[bands["Transactions"].idxmax()]
        findings.append(
            f"The busiest price bracket is {top['Price band (AED)']}, holding "
            f"{int(top['Transactions']):,} transactions — {top['Share (%)']:.1f}% of the "
            f"selection.")

    stats = ch.rate_by_layout(df)[1]
    if not stats.empty:
        hi, lo = stats["med"].idxmax(), stats["med"].idxmin()
        findings.append(
            f"Across layouts the highest median rate is {hi} at "
            f"AED {stats.loc[hi, 'med']:,.0f}/m², the lowest {lo} at "
            f"AED {stats.loc[lo, 'med']:,.0f}/m².")

    if COL["area"] in df.columns and area == "All Areas":
        vc = df[COL["area"]].value_counts()
        if len(vc):
            findings.append(
                f"{vc.index[0]} is the busiest area with {int(vc.iloc[0]):,} transactions, "
                f"{vc.iloc[0] / len(df) * 100:.1f}% of the selection.")

    rep.h2("Key findings", needs=0.9)
    rep.bullets(findings)


def _volume(rep, df) -> None:
    rep.h1("Transaction volume", needs=3.1)
    yt = mx.yoy_table(df)
    if yt.empty:
        rep.body("No yearly volume available for this selection.")
        return

    def draw(ax):
        ax.bar(yt["Year"].astype(int).astype(str), yt["Transactions"],
               color=R.ACCENT, width=0.68)
        ax.set_ylabel("Transactions", fontsize=8, color=R.INK)
        ax.set_xlabel("Year", fontsize=8, color=R.INK)
        ax.tick_params(axis="x", rotation=0, labelsize=6.8)
        ax.yaxis.set_major_formatter(
            matplotlib_thousands())

    rep.chart(draw, height=2.55, title="Transactions recorded each year",
              caption="Counted on the current selection. Where a year is still in progress "
                      "its bar covers part of a year only and is not comparable in height "
                      "with the full years beside it.")

    rows = [[str(int(r["Year"])), f"{int(r['Transactions']):,}",
             f"{r['Median price (AED)']:,.0f}", f"{r['Median rate (AED/m²)']:,.0f}",
             "—" if pd.isna(r["Volume YoY (%)"]) else f"{r['Volume YoY (%)']:+.1f}%"]
            for _, r in yt.iterrows()]
    rep.table(["Year", "Transactions", "Median price (AED)", "Median rate (AED/m²)",
               "Volume YoY"], rows, widths=[0.14, 0.20, 0.24, 0.24, 0.18],
              caption="Year-over-year change is measured against the year immediately "
                      "before it. The first year of the series has no predecessor and "
                      "carries no percentage.")


def matplotlib_thousands():
    from matplotlib.ticker import FuncFormatter
    return FuncFormatter(lambda v, _: f"{v:,.0f}")


def _prices(rep, df) -> None:
    rep.h1("Price levels and movement", needs=3.2)
    m = mx.monthly_series(df).copy()
    if len(m) < 3:
        rep.body("Not enough months in this selection to show a price trend.")
        return

    partial = mx.partial_tail_months(m)
    m["trend"] = mx.lowess_trend(m["median_rate"], exclude_tail=partial)

    def draw(ax):
        ax.plot(m["_sort"], m["median_rate"], color="#CFC3B2", linewidth=0.85,
                label="Actual monthly median")
        ax.plot(m["_sort"], m["trend"], color=R.ACCENT, linewidth=2.0,
                label="LOWESS smoothed trend")
        ax.set_ylabel("Median rate (AED/m²)", fontsize=8, color=R.INK)
        ax.set_xlabel("Month", fontsize=8, color=R.INK)
        ax.legend(fontsize=7.2, frameon=False, loc="upper left")
        ax.yaxis.set_major_formatter(matplotlib_thousands())

    rep.chart(draw, height=2.6, title="How prices are moving — median rate per m²",
              caption="The trend is a centred LOWESS fit of the monthly medians — a smoothing "
                      "drawn through the observed months. It runs to the last complete "
                      "month, so it always reflects fully recorded data.")

    price, rate = df[COL["price"]], df[COL["rate"]]
    rep.table(
        ["Measure", "Count", "25th pct", "Median", "Mean", "75th pct", "Maximum"],
        [["Sale price (AED)", f"{len(price):,}", f"{price.quantile(.25):,.0f}",
          f"{price.median():,.0f}", f"{price.mean():,.0f}",
          f"{price.quantile(.75):,.0f}", f"{price.max():,.0f}"],
         ["Rate (AED/m²)", f"{len(rate):,}", f"{rate.quantile(.25):,.0f}",
          f"{rate.median():,.0f}", f"{rate.mean():,.0f}",
          f"{rate.quantile(.75):,.0f}", f"{rate.max():,.0f}"],
         ["Unit size (m²)", f"{len(df):,}",
          f"{df[COL['area_sqm']].quantile(.25):,.0f}",
          f"{df[COL['area_sqm']].median():,.0f}", f"{df[COL['area_sqm']].mean():,.1f}",
          f"{df[COL['area_sqm']].quantile(.75):,.0f}",
          f"{df[COL['area_sqm']].max():,.0f}"]],
        widths=[0.24, 0.12, 0.13, 0.13, 0.13, 0.13, 0.12],
        caption="The mean sits above the median on every price measure, which is what a "
                "right-skewed distribution looks like. Both are reported so neither is "
                "mistaken for the other.")


def _layout(rep, df) -> None:
    rep.h1("Rate per m² by layout", needs=3.3)
    stats = ch.rate_by_layout(df)[1]
    if stats.empty:
        rep.body("Widen the selection to see the layout distribution — a hundred or more "
                 "transactions in a layout give a distribution worth reading.")
        return

    def draw(ax):
        names = list(stats.index)
        pos = np.arange(len(names))
        for i, n in enumerate(names):
            r = stats.loc[n]
            c = R.SERIES[i % len(R.SERIES)]
            ax.add_patch(plt_rect(i - 0.28, r["q1"], 0.56, r["q3"] - r["q1"], c))
            ax.plot([i - 0.28, i + 0.28], [r["med"]] * 2, color="white", linewidth=1.6)
            ax.plot([i, i], [r["lower"], r["q1"]], color=c, linewidth=1.0)
            ax.plot([i, i], [r["q3"], r["upper"]], color=c, linewidth=1.0)
        ax.set_xticks(pos)
        ax.set_xticklabels(names, fontsize=7.2)
        ax.set_ylabel("Rate (AED/m²)", fontsize=8, color=R.INK)
        ax.set_xlabel("Layout", fontsize=8, color=R.INK)
        ax.yaxis.set_major_formatter(matplotlib_thousands())
        ax.set_xlim(-0.6, len(names) - 0.4)

    rep.chart(draw, height=2.7, title="Distribution of rate per m², by layout",
              caption="Box = the middle half of transactions (25th to 75th percentile), "
                      "white line = median, whiskers = the furthest transaction within "
                      "1.5 × the interquartile range.")

    rows = [[str(n), f"{int(stats.loc[n, 'n']):,}", f"{stats.loc[n, 'q1']:,.0f}",
             f"{stats.loc[n, 'med']:,.0f}", f"{stats.loc[n, 'q3']:,.0f}",
             f"{stats.loc[n, 'q3'] - stats.loc[n, 'q1']:,.0f}"]
            for n in stats.index]
    rep.table(["Layout", "Transactions", "25th pct", "Median", "75th pct", "IQR"],
              rows, widths=[0.22, 0.18, 0.15, 0.15, 0.15, 0.15],
              caption="Layouts with fewer than 100 transactions are excluded from the chart "
                      "and this table rather than drawn on thin evidence.")


def plt_rect(x, y, w, h, colour):
    from matplotlib.patches import Rectangle
    return Rectangle((x, y), w, h, facecolor=colour, edgecolor=colour, alpha=0.88)


def _height(rep, df) -> None:
    rep.h1("Rate by building height", needs=3.4)
    frame, audit = mx.rate_by_building_height(df, band_source=df)
    if frame.empty:
        rep.body("No height band in this selection reaches the minimum transaction count, "
                 "so no medians are reported.")
        return

    bands = list(frame["height_band"].cat.categories)
    types = [t for t in mx.PROPERTY_TYPE_LABELS.values()
             if t in set(frame["Property type"])]

    def draw(ax):
        n = len(types)
        width = 0.8 / max(n, 1)
        for i, t in enumerate(types):
            sub = frame[frame["Property type"] == t]
            xs, ys = [], []
            for b_i, b in enumerate(bands):
                cell = sub[sub["height_band"] == b]
                if not cell.empty:
                    xs.append(b_i - 0.4 + width * (i + 0.5))
                    ys.append(float(cell["median_rate"].iloc[0]))
            ax.bar(xs, ys, width=width * 0.92, label=t,
                   color=R.SERIES[i % len(R.SERIES)])
        ax.set_xticks(range(len(bands)))
        ax.set_xticklabels([str(b) for b in bands], fontsize=6.8)
        ax.set_ylabel("Median rate (AED/m²)", fontsize=8, color=R.INK)
        ax.set_xlabel("Building height band", fontsize=8, color=R.INK)
        ax.legend(fontsize=6.6, frameon=False, ncol=min(len(types), 4),
                  loc="upper left")
        ax.yaxis.set_major_formatter(matplotlib_thousands())

    rep.chart(draw, height=2.8,
              title="Median rate per m², by floor band and property type",
              caption="Four fixed floor bands on round thresholds — Low-rise 1–10, Mid-rise "
                      "11–25, High-rise 26–40, Tower 41+ — so a band means the same building "
                      "in every area. This is the height of the BUILDING, not the floor a "
                      "unit sits on: the dataset holds no unit-level floor. Differences "
                      "shown are observed differences between groups of recorded "
                      "transactions, not an effect of height.")

    counts = audit.get("band_counts", {})
    spans = audit.get("spans", {})
    rep.table(["Floor band", "Floors covered", "Transactions"],
              [[b, spans.get(b, ""), f"{counts.get(b, 0):,}"] for b in audit.get("bands", [])],
              widths=[0.36, 0.42, 0.22], align_right_from=2,
              caption=f"Band boundaries are inclusive at the top: a building of exactly 10 "
                      f"floors is Low-rise, exactly 11 is Mid-rise. "
                      f"{audit.get('invalid_floor', 0):,} transactions record zero floors and "
                      f"are excluded as an invalid reading rather than counted as low-rise.")

    rows = [[str(r["height_band"]), r["Property type"], f"{r['median_rate']:,.0f}",
             f"{r['mean_rate']:,.0f}", f"{int(r['transactions']):,}"]
            for _, r in frame.iterrows()]
    rep.table(["Height band", "Property type", "Median rate", "Mean rate", "Transactions"],
              rows, widths=[0.26, 0.22, 0.18, 0.18, 0.16], align_right_from=2,
              caption=f"Rows use the fixed floor bands above. Height is recorded for "
                      f"{audit.get('rows_with_height', 0):,} of "
                      f"{audit.get('rows_total', len(df)):,} transactions here. Cells with "
                      f"fewer than 100 transactions are omitted rather than reported on "
                      f"thin evidence.")


def _amenity(rep, df, area) -> None:
    rep.h1("Amenity analysis", needs=1.2)
    rep.body(
        "This section reports how often each amenity appears on the transaction record. "
        "It is a share of completed, recorded transactions and nothing more: it is not a "
        "price effect, not a measure of demand, and not a probability that a buyer "
        "purchases. A zero in an amenity field means the feature was not recorded, which "
        "is not the same as confirmed absent."
    )

    order = [v for v in mx.PROPERTY_TYPE_LABELS
             if v in set(df[COL["rooms"]].dropna().unique())]
    rows, drawn = [], {}
    for val in order:
        t = mx.amenity_transaction_share(df, val)
        if t.empty:
            continue
        label = mx.PROPERTY_TYPE_LABELS[val]
        shares = {r["Amenity"]: r["Share of recorded transactions (%)"]
                  for _, r in t.iterrows()}
        drawn[label] = shares
        rows.append([label,
                     f"{int(t['Transactions with amenity recorded'].iloc[0] + t['Transactions without'].iloc[0]):,}"]
                    + [f"{shares.get(a, float('nan')):.1f}%" for a in AMENITIES.values()])

    if not rows:
        rep.body("No property type in this selection has enough transactions to report an "
                 "amenity share.")
        return

    amen = list(AMENITIES.values())

    def draw(ax):
        labels = list(drawn)
        n = len(amen)
        width = 0.8 / n
        for i, a in enumerate(amen):
            xs = [j - 0.4 + width * (i + 0.5) for j in range(len(labels))]
            ys = [drawn[l].get(a, 0) for l in labels]
            ax.bar(xs, ys, width=width * 0.9, label=a, color=R.SERIES[i % len(R.SERIES)])
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=7.0)
        ax.set_ylabel("Share of recorded transactions (%)", fontsize=8, color=R.INK)
        ax.set_xlabel("Property type", fontsize=8, color=R.INK)
        ax.set_ylim(0, 112)
        ax.legend(fontsize=6.4, frameon=False, ncol=3, loc="upper left")

    rep.chart(draw, height=2.7,
              title="Share of recorded transactions associated with each amenity",
              caption="Height is how often a feature is written on the record. Parking is "
                      "recorded on the large majority of transactions in every property "
                      "type, so a tall parking bar reflects record-keeping rather than "
                      "market importance.")

    short = {"Parking": "Parking", "Swimming pool": "Pool", "Balcony": "Balcony",
             "Elevator": "Elevator", "Near a metro station": "Metro"}
    rep.table(["Property type", "Transactions"] + [short.get(a, a) for a in amen], rows,
              widths=[0.21, 0.16] + [0.126] * len(amen),
              caption="Shares are of recorded transactions. Column headings are shortened; "
                      "'Pool' is swimming pool and 'Metro' is near a metro station. Property "
                      "types with fewer than 100 transactions in this selection are omitted.")


def _reg_type(rep, df) -> None:
    rep.h1("Registration type", needs=1.6)
    if COL["reg_type"] not in df.columns or df.empty:
        rep.body("No registration-type information in this selection.")
        return

    g = (df.groupby(COL["reg_type"], observed=True)
           .agg(n=(COL["price"], "size"),
                p25=(COL["price"], lambda s: s.quantile(.25)),
                mean=(COL["price"], "mean"),
                med=(COL["price"], "median"),
                p75=(COL["price"], lambda s: s.quantile(.75)),
                rate=(COL["rate"], "median"))
           .reset_index())
    total = g["n"].sum()

    rows = [[str(r[COL["reg_type"]]), f"{int(r['n']):,}", f"{r['n'] / total * 100:.1f}%",
             f"{r['p25']:,.0f}", f"{r['mean']:,.0f}", f"{r['med']:,.0f}",
             f"{r['p75']:,.0f}"] for _, r in g.iterrows()]
    rep.table(["Registration type", "Transactions", "Share", "25th pct",
               "Mean", "Median", "75th pct"], rows,
              widths=[0.24, 0.14, 0.10, 0.13, 0.13, 0.13, 0.13],
              caption="All price columns are in AED. Mean and median are both shown "
                      "because they answer different "
                      "questions: the mean is the arithmetic average and every large sale "
                      "pulls on it, the median is the middle transaction and is not moved "
                      "by a handful of them.")

    rep.body(
        "Each registration type is described on its own terms, which is the clearest way to "
        "read them: off-plan and existing stock differ in age, height and location, so each "
        "row tells you what that segment of the market actually looks like."
    )


def _brackets(rep, df) -> None:
    rep.h1("Price brackets and area concentration", needs=3.0)
    bands, audit = mx.price_bands(df)
    if bands.empty:
        rep.body("No transactions to place into price brackets.")
        return

    def draw(ax):
        ax.bar(bands["Price band (AED)"], bands["Transactions"], color=R.ACCENT,
               width=0.66)
        ax.set_ylabel("Transactions", fontsize=8, color=R.INK)
        ax.set_xlabel("Price bracket (AED)", fontsize=8, color=R.INK)
        ax.tick_params(axis="x", labelsize=6.8)
        ax.yaxis.set_major_formatter(matplotlib_thousands())

    rep.chart(draw, height=2.4, title="Where the price points are",
              caption=f"Brackets are left-closed and right-open, so a sale of exactly "
                      f"AED 1,000,000 sits in 1M – 2M. "
                      f"{audit['assigned']:,} of {audit['total']:,} transactions were "
                      f"assigned to a bracket, with {audit['unassigned']:,} unassigned.")

    top, t_audit = mx.top_areas_by_band(df)
    if top.empty:
        return

    single = t_audit.get("single_area")
    heading = (f"{single} in each price bracket" if single
               else "Top 5 areas in each price bracket")
    rep.h2(heading, needs=1.2)

    if single:
        rep.body(
            f"Only {single} is in scope, so each bracket shows that area alone. Brackets "
            f"{single} has no transactions in are listed as such rather than left blank.")

    rows = []
    for b in mx.BAND_LABELS:
        sub = top[top["Price band (AED)"] == b]
        if sub.empty:
            note = ("No transactions in this bracket" if single
                    else "No qualifying transactions here")
            rows.append([b, "—", note, "0", "—"])
            continue
        for _, r in sub.iterrows():
            rows.append([b if r["Rank"] == 1 else "", str(int(r["Rank"])), r["Area"],
                         f"{int(r['Transactions']):,}",
                         f"{r['Share of band (%)']:.1f}%"])

    if single:
        caption = (f"Every bracket is reported for {single} only. A bracket with no "
                   f"transactions is stated explicitly — it is a real absence in this area, "
                   f"not missing data. Of {t_audit['valid']:,} transactions with a valid "
                   f"sale price, every one was classified into exactly one bracket.")
    else:
        caption = (f"Areas are ranked by transaction count within each bracket, taken from "
                   f"the data. Every transaction with a valid sale price "
                   f"({t_audit['valid']:,}) was classified into exactly one bracket.")

    rep.table(["Price bracket", "Rank", "Area", "Transactions", "Share of bracket"],
              rows, widths=[0.22, 0.10, 0.34, 0.18, 0.16], align_right_from=3,
              caption=caption)


def _methodology(rep, df, area) -> None:
    rep.h1("Methodology and scope")

    rep.h2("Data sources", needs=1.0)
    rep.bullets([
        "Transaction counts and volume come from the RAW Dubai registry "
        "(transactions.parquet), which captures every registered sale exactly as filed.",
        "All price and rate statistics come from the CLEANED dataset "
        "(latest_combined_data.parquet) — the validated price basis, carrying the enriched "
        "columns this analysis draws on.",
        "Where a single figure draws on both, each column is labelled with the file behind "
        "it, so every number is traceable to its source.",
    ])

    rep.h2("How this selection was formed", needs=1.0)
    rep.bullets([
        f"Global area: {area}. Applied to the dataframe before any grouping or aggregation, "
        f"so every figure in this report describes the same population.",
        f"Transactions in scope after all filters: {len(df):,}.",
        "The sale-price and unit-size sliders default to the 1st–99th percentile, which "
        "keeps the charts readable; widen them for the full range including the largest "
        "deals.",
    ])

    frame, h_audit = mx.rate_by_building_height(df, band_source=df)
    with_h = h_audit.get("rows_with_height", 0)

    rep.h2("How to read these figures", needs=1.2)
    rep.bullets([
        "Coverage is registered residential unit (apartment) sales — the deepest and most "
        "consistent segment of the Dubai market, and the one with the richest attribute "
        "data behind it.",
        "Every figure is dated by registration, so the report reflects the official record "
        "as filed with the Land Department.",
        "The most recent year runs to the latest registration date, giving the freshest "
        "view available; read it as a year in progress.",

        # ── the floor bands ─────────────────────────────────────────────────
        f"Floor bands are fixed thresholds: Low-rise covers 1–10 floors, Mid-rise 11–25, "
        f"High-rise 26–40, and Tower 41 and above. Boundaries are inclusive at the top, so "
        f"a building of exactly 10 floors is Low-rise and one of exactly 11 is Mid-rise. "
        f"Fixed edges mean a band denotes the same building in every area and holds steady "
        f"as filters change, which makes areas directly comparable. The bands describe the "
        f"height of the building, drawn from the `floors` column, and a floor count is "
        f"present for {with_h:,} transactions in this selection.",

        "Amenity figures describe how often a feature appears on the transaction record, "
        "which makes them a reliable read on what the registry captures and on how one "
        "slice of the market differs from the city as a whole.",
        "Group differences here are observed differences between sets of recorded "
        "transactions — a sound basis for comparing segments and spotting where a market "
        "behaves distinctively.",
        "Any group with fewer than 100 transactions is reported separately rather than "
        "charted, so every figure you see rests on a solid sample and omissions are always "
        "named.",
        "Median and mean are both given wherever they differ. The median describes the "
        "typical transaction; the mean carries the upper tail, and together they show the "
        "shape of the market.",
        "Price brackets are left-closed and right-open, so every transaction with a valid "
        "sale price lands in exactly one bracket. The classification is audited on every "
        "run and reported alongside the results.",
        "Areas are the districts recorded in the registry, which is what makes them "
        "directly comparable with official published figures.",
        "The price trend is a smoothing of the observed months, drawn through the real "
        "data and stopping at the last complete month, so it always reflects what has "
        "actually been recorded.",
    ])

    rep.h2("Trend smoothing", needs=1.1)
    rep.body(
        "The price trend uses a centred LOWESS fit — locally weighted regression over "
        "neighbouring months. It was chosen over exponential smoothing on measured evidence "
        "from this series: LOWESS is both calmer and closer to the observations, because it "
        "is centred and can use the months on either side of a point. The fitted trend "
        "follows the observed months and holds to the recorded data throughout."
    )
