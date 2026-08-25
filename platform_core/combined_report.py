"""
The combined Area + Forecast PDF.

ONE document, two sections. This is not two PDFs stapled together: both analyses
are written into a single `pdf_report.Report`, using the very same section
writers that produce the standalone documents (`dubai_report.write_sections`
and `forecast_report.write_sections`). There is therefore no second
implementation of any section, no merge library, and no way for the combined
report to disagree with the two it is made of.

Both sections describe the SAME area — the one global 📍 Area — and the forecast
section is written from the forecast response already held in session state, so
the API is not called again to produce it.
"""

from __future__ import annotations

import pandas as pd

from platform_core import dubai_report
from platform_core import forecast_report
from platform_core import pdf_report as R
from regions.dubai_market.data import COL


def build(df: pd.DataFrame, area: str, all_rows: int, result, inputs: dict,
          sections: list[str] | None = None, window_start=None,
          show_news: bool = True) -> bytes:
    """
    `df` / `area` / `all_rows` / `sections` are the area report's inputs.
    `result` / `inputs` / `window_start` / `show_news` are the forecast's.
    """
    rep, buf = R.new_document(
        title="Market Analytics & Forecast Report",
        subtitle=f"Dubai · {area}",
        footer_note=f"Dubai · {area}",
    )

    years = df[COL["year"]].dropna()
    period = f"{int(years.min())} – {int(years.max())}" if len(years) else "—"
    dates = pd.to_datetime(df[COL["date"]], errors="coerce").dropna()
    coverage = f"{dates.min():%d %b %Y} to {dates.max():%d %b %Y}" if len(dates) else "—"

    now_ts = result.now_timestamp if result is not None else None
    horizon = result.horizon_months if result is not None else 0

    rep.title_page(
        meta=[
            ("Area", area),
            ("Reporting period", period),
            ("Data coverage", coverage),
            ("Transactions analysed", f"{len(df):,}"),
            ("Forecast valuation point",
             pd.Timestamp(now_ts).strftime("%B %Y") if now_ts is not None else "—"),
            ("Generated", R.stamp()),
        ],
        lede=(
            "Two analyses of the same area in one document. Section 1 is the recorded "
            "market: registered residential unit sales in Dubai, what has been "
            "transacted and at what level. Section 2 is the forecast: what the TruEstates "
            "Forecast API values one property profile at today, and where it puts that "
            "profile over the months ahead. Every figure in both sections is computed or "
            "returned at generation time — none is stored or hard-coded."
        ),
    )

    # ── THE ORDER OF THIS DOCUMENT ──────────────────────────────────────────
    # Analysis first, notes last. A reader gets the recorded market, then the
    # forecast for the same area, and only then the methodology for both. The
    # market narrative closes the document. Nothing is interleaved: the earlier
    # layout put the area methodology between the two analyses, which broke the
    # read exactly where it should have flowed.
    #
    #   Section 1  Area-wise analysis          (no methodology)
    #   Section 2  Forecast analysis           (no narrative, no production notes)
    #   Section 3  Methodology and scope       (area, through trend smoothing)
    #              Market context + how the forecast was produced
    # ────────────────────────────────────────────────────────────────────────

    analysis = [s for s in (sections or dubai_report.ALL_SECTIONS) if s != "method"]

    _divider(rep, "SECTION 1", "Area-wise analysis",
             f"What has actually been recorded in {area}: transaction activity, price "
             f"levels and how they have moved, the composition of the market, and where "
             f"activity concentrates across price brackets.")
    dubai_report.write_sections(rep, df, area, all_rows, period, analysis)

    if result is not None:
        _divider(rep, "SECTION 2", "Forecast analysis",
                 f"What the forecast service values one property profile in {area} at "
                 f"today, and the {horizon} month(s) of projection it returns. This "
                 f"section describes a single property profile, not the whole area — the "
                 f"two answer different questions about the same place.")
        forecast_report.write_sections(rep, result, area, inputs,
                                       window_start=window_start, show_news=show_news,
                                       closing=False)

    _divider(rep, "SECTION 3", "Methodology and scope",
             "Where every figure in this document comes from, how the selection was "
             "formed, and how to read the numbers in both sections above.")
    dubai_report.write_sections(rep, df, area, all_rows, period, ["method"],
                                method_heading=False)

    if result is not None:
        forecast_report.write_closing(rep, result, area, show_news=show_news)

    return R.finish(rep, buf)


def _divider(rep, eyebrow: str, title: str, lede: str) -> None:
    """
    A section opening that FLOWS.

    It used to call `new_page()`, which meant every section started at the top
    of a fresh sheet and left the previous page half empty — two nearly blank
    pages in a fourteen-page report. It now behaves like any other heading:
    it takes a new page only if there is not enough room for the heading plus
    the first block beneath it, so the document reads continuously from cover
    to close.
    """
    rep.space(2.35)
    rep.y -= 0.34
    rep.fig.text(R._fx(R.M_L), R._fy(rep.y), eyebrow, fontsize=9.5, color=R.ACCENT,
                 fontweight="bold", va="top", ha="left")
    rep.y -= 0.30
    rep.fig.add_artist(_rule(rep))
    rep.y -= 0.28
    rep.fig.text(R._fx(R.M_L), R._fy(rep.y), title, fontsize=23, color=R.INK,
                 fontweight="bold", va="top", ha="left")
    rep.y -= 0.60
    rep.body(lede, size=9.6)
    rep.y -= 0.18


def _rule(rep):
    from matplotlib.lines import Line2D
    y = R._fy(rep.y)
    return Line2D([R._fx(R.M_L), R._fx(R.M_L + 1.0)], [y, y],
                  transform=rep.fig.transFigure, color=R.ACCENT, linewidth=2.4)
