"""
The Forecast PDF.

Built from the forecast response that is **already in session state** — the one
the chart on screen is drawn from. No second request is made, so the PDF and the
screen cannot disagree and the API is not called twice for one answer.

Every figure in this document is a value the API returned. Nothing is smoothed,
extended, averaged or re-modelled on the way in.
"""

from __future__ import annotations

import pandas as pd

from platform_core import pdf_report as R


def _aed(v) -> str:
    try:
        return f"AED {float(v):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _pct(v) -> str:
    try:
        return f"{float(v):+.1f}%"
    except (TypeError, ValueError):
        return "—"


def _month(ts) -> str:
    try:
        return pd.Timestamp(ts).strftime("%B %Y")
    except Exception:
        return "—"


# The profile is listed in full inside the report. The cover carries only a
# short form of it, because the cover's value column is one line wide and a long
# string would run past the page edge.
PROFILE_FIELDS = (
    ("rooms_en", "Rooms"), ("floor_bin", "Floor"),
    ("reg_type_en", "Registration"), ("Grade", "Building grade"),
    ("project_grade", "Project grade"), ("Developer_grade", "Developer grade"),
    ("has_parking", "Parking"), ("swimming_pool", "Pool"),
    ("balcony", "Balcony"), ("elevators", "Elevators"), ("metro", "Metro"),
)
TYPICAL = "this area's typical value"


def _profile_value(key, val) -> str:
    if val is None or val == "Any":
        return TYPICAL
    if key in ("has_parking", "swimming_pool", "balcony", "metro"):
        try:
            return {0.0: "No", 1.0: "Yes"}.get(float(val), str(val))
        except (TypeError, ValueError):
            return str(val)
    if key == "elevators":
        try:
            return f"{float(val):g}"
        except (TypeError, ValueError):
            return str(val)
    return str(val)


def _profile_rows(inputs: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    size = inputs.get("procedure_area")
    if size:
        rows.append(("Unit size", f"{float(size):,.0f} m²"))
    for key, label in PROFILE_FIELDS:
        rows.append((label, _profile_value(key, inputs.get(key))))
    return rows


def build(result, area: str, inputs: dict, window_start=None,
          show_news: bool = True) -> bytes:
    """
    `result` is a `regions.dubai_market.forecast_api.ForecastResult` that has
    already been fetched. `inputs` is the property profile that produced it.
    `window_start` is the historical window the screen was showing, so the PDF
    covers the same months. It trims history only — never the forecast.

    `show_news` is the news toggle exactly as it stood when the user pressed
    download. With it off the news-adjusted series, its legend entry, the
    headline figures derived from it and the narrative are all absent from the
    document — the PDF says what the screen said.
    """
    rep, buf = R.new_document(
        title="Dubai Forecast Report",
        subtitle=f"{area} · price per m²",
        footer_note="TruEstates Forecast API",
    )

    now_ts = result.now_timestamp
    horizon = result.horizon_months
    with_news = bool(show_news) and result.has_news

    profile_rows = _profile_rows(inputs)
    short = " · ".join(
        f"{lbl} {val}" for lbl, val in profile_rows[:3] if val != TYPICAL)

    rep.title_page(
        meta=[
            ("Area", area),
            ("Property profile", short or "Area defaults applied by the model"),
            ("Valuation point", _month(now_ts) if now_ts is not None else "—"),
            ("Forecast months returned", f"{horizon}"),
            ("News-adjusted series", "included" if with_news else "not included"),
            ("Generated", R.stamp()),
        ],
        lede=(
            "A forecast of price per square metre for the property profile above, "
            "produced by the TruEstates Forecast API. The figures in this report are "
            "the values the API returned for this request — they are reproduced here "
            "without smoothing, rescaling or extension."
        ),
    )

    rep.new_page()
    write_sections(rep, result, area, inputs, window_start=window_start,
                   show_news=show_news)
    return R.finish(rep, buf)


def profile_rows_for(inputs: dict) -> list[tuple[str, str]]:
    """The property profile as label/value pairs — shared by both documents."""
    return _profile_rows(inputs)


def write_sections(rep, result, area: str, inputs: dict, window_start=None,
                   show_news: bool = True, closing: bool = True) -> None:
    """
    Write the forecast analysis into an existing report.

    Split out of `build()` so the combined Area + Forecast document can carry
    this analysis as its second section without a second PDF or a merge step.

    `closing=False` writes the analysis ONLY — the figures, the chart, the
    profile and the month table — and leaves the market narrative and the
    "how this was produced" notes for `write_closing()`. The combined document
    uses that to gather all the methodology at the end, after both analyses,
    instead of interrupting the report in the middle.
    """
    now_ts = result.now_timestamp
    horizon = result.horizon_months
    with_news = bool(show_news) and result.has_news
    profile_rows = _profile_rows(inputs)

    # ── 1. What the forecast says ───────────────────────────────────────────
    rep.h1("The forecast", needs=2.2)

    cards: list[tuple[str, str]] = []
    if result.now_value is not None:
        cards.append((f"Valuation point · {_month(now_ts)}", _aed(result.now_value)))
    if not result.macro.empty:
        last = result.macro.iloc[-1]
        cards.append((f"Macro forecast · {_month(last['timestamp'])}", _aed(last["value"])))
        if result.now_value:
            change = (float(last["value"]) - result.now_value) / result.now_value * 100
            cards.append(("Macro change over the horizon", _pct(change)))
    if with_news:
        lastn = result.news.iloc[-1]
        cards.append((f"News-adjusted · {_month(lastn['timestamp'])}", _aed(lastn["value"])))
        if result.now_value:
            changen = (float(lastn["value"]) - result.now_value) / result.now_value * 100
            cards.append(("News-adjusted change", _pct(changen)))
            gap = float(lastn["value"]) - float(result.macro.iloc[-1]["value"])
            cards.append(("Gap between the two at the end", _aed(gap)))
    if cards:
        rep.kpis(cards, per_row=3)

    rep.body(
        f"The API returned {len(result.history)} month(s) of smoothed history, one "
        f"valuation point at {_month(now_ts)}, and {horizon} forecast month(s). "
        f"That is the full extent of the projection available for this profile, and "
        f"the chart below shows all of it."
    )

    # ── 2. The chart ────────────────────────────────────────────────────────
    # The report shows the same history window the screen was showing, so the
    # PDF and the chart it was downloaded from cover the same months.
    api_history = result.history
    if window_start is not None and not api_history.empty:
        api_history = api_history[api_history["timestamp"] >= pd.Timestamp(window_start)]

    def draw(ax):
        import matplotlib.dates as mdates

        # History runs through to the valuation point so the line into the
        # forecast is continuous — the same point the marker sits on, not an
        # interpolated bridge.
        hist_line = api_history
        if not result.now.empty:
            hist_line = (pd.concat([api_history, result.now], ignore_index=True)
                           .drop_duplicates(subset="timestamp")
                           .sort_values("timestamp"))
        if not hist_line.empty:
            ax.plot(hist_line["timestamp"], hist_line["value"],
                    color="#475569", linewidth=1.8, marker="o", markersize=2.6,
                    label="Historical")
        macro = result.anchored("macro")
        news = result.anchored("news")
        if with_news and not macro.empty and not news.empty:
            j = macro.merge(news, on="timestamp", suffixes=("_m", "_n"))
            if not j.empty:
                ax.fill_between(j["timestamp"],
                                j[["value_m", "value_n"]].min(axis=1),
                                j[["value_m", "value_n"]].max(axis=1),
                                color="#10B981", alpha=0.13, linewidth=0,
                                label="Range between the two forecasts")
        if not macro.empty:
            ax.plot(macro["timestamp"], macro["value"], color="#0E9F6E",
                    linewidth=1.8, linestyle="--", marker="o", markersize=3,
                    label="Macro forecast")
        if with_news and not news.empty:
            ax.plot(news["timestamp"], news["value"], color="#E05252",
                    linewidth=1.8, marker="o", markersize=3,
                    label="News-adjusted forecast")
        if now_ts is not None:
            ax.axvline(now_ts, color="#B8731B", linewidth=1.0, linestyle=":")
            if result.now_value is not None:
                ax.plot([now_ts], [result.now_value], marker="o", markersize=6,
                        color="#B8731B", markeredgecolor="white", markeredgewidth=1.1,
                        linestyle="None", label="Valuation point (now)")
        ax.set_ylabel("AED per m²", fontsize=7.4)
        # Headroom so the legend sits in empty space rather than over the lines.
        # This changes the visible extent of the axis, not a single value on it.
        top = 0.0
        for frame in (hist_line, result.macro, result.news if with_news else None):
            if frame is not None and not frame.empty:
                top = max(top, float(frame["value"].max()))
        if top > 0:
            ax.set_ylim(bottom=0, top=top * 1.34)
        ax.legend(fontsize=6.0, ncol=2, loc="upper left", frameon=True,
                  facecolor="white", edgecolor="none", framealpha=0.9,
                  borderpad=0.5, labelspacing=0.42, handlelength=1.9)

        # Months on the axis, spaced so every tick stays legible.
        xs = []
        for frame in (hist_line, result.macro, result.news if with_news else None, result.now):
            if frame is not None and not frame.empty:
                xs += list(pd.to_datetime(frame["timestamp"]))
        if xs:
            span = (max(xs).year - min(xs).year) * 12 + (max(xs).month - min(xs).month) + 1
            step = 1 if span <= 16 else 2 if span <= 30 else 3 if span <= 54 else 6
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=step))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(45)
            lbl.set_ha("right")
            lbl.set_fontsize(6.2)

    rep.chart(
        draw, height=3.0, title="Price per m² — history, valuation point and forecast",
        caption=(
            "The dotted vertical line is the valuation point the API returned; it is read "
            "from the response, not from today's date. History runs through to that point, "
            "so the line into the forecast is continuous. " + (
                "The macro and news-adjusted lines both begin there because the API "
                "propagates both from the same baseline, and the shaded region is the span "
                "between those two returned trajectories — it is not a confidence interval, "
                "and none is drawn, because the response does not carry one."
                if with_news else
                "The forecast line begins there because the API propagates it from that "
                "baseline."
            )
        ),
    )

    # ── 2b. The property this describes ─────────────────────────────────────
    rep.h1("The property profile", needs=2.0)
    rep.body(
        "The forecast above is for this specific property. Where an attribute reads "
        "“this area's typical value”, it was left open and the model used the value "
        "most common in this area — which is what its documentation describes it doing.",
        size=8.4)
    rep.table(
        ["Attribute", "Value"],
        [[lbl, val] for lbl, val in profile_rows],
        widths=[R.CONTENT_W * 0.42, R.CONTENT_W * 0.58],
        align_right_from=99,
    )

    # ── 3. The months, as figures ───────────────────────────────────────────
    # The two derived comparison columns are deliberately left out of the
    # printed report; the months and the two trajectories are what it carries.
    table = result.table(include_news=with_news, include_difference=False)
    if not table.empty:
        rep.h1("Forecast months", needs=2.0)
        headers = list(table.columns)
        rows: list[list[str]] = []
        for _, r in table.iterrows():
            row = [str(r["Month"])]
            for col in headers[1:]:
                val = r[col]
                row.append(f"{float(val):,.0f}")
            rows.append(row)
        first = 1.35
        widths = [first] + [(R.CONTENT_W - first) / max(len(headers) - 1, 1)] * (
            len(headers) - 1)
        rep.table(headers, rows, widths=widths)
        rep.body(
            "All figures are AED per square metre. Each row is one month the API "
            "returned — no row is repeated, interpolated or projected further out than "
            "the response reaches.", size=8.0)

    if closing:
        write_closing(rep, result, area, show_news=show_news)


def write_closing(rep, result, area: str, show_news: bool = True) -> None:
    """
    The market narrative and the production notes — the closing matter.

    Kept separate so the combined document can place it where it belongs: at
    the very end, after both analyses and after the area methodology, rather
    than between the forecast and whatever follows it.
    """
    horizon = result.horizon_months
    with_news = bool(show_news) and result.has_news

    # ── The narrative ────────────────────────────────────────────────────
    if with_news and result.narrative:
        rep.h1("Market context", needs=1.6)
        rep.body(result.narrative)

    # ── 5. How this was produced ────────────────────────────────────────────
    rep.h1("How this forecast was produced", needs=2.4)

    rep.h2("What the API does")
    rep.bullets([
        "History is smoothed by the API with a LOWESS filter (frac = 0.10) before it is "
        "returned. It is plotted here exactly as received.",
        "The valuation point is produced by CatBoost and anchored within ±7.5% of the "
        "latest smoothed history point.",
        "The macro forecast is propagated from that anchor using Chronos month-over-month "
        "growth, capped at ±7.5% per step.",
    ] + ([
        "The news-adjusted forecast starts from the same anchor and uses uncapped "
        "news-derived growth, which is why the two lines separate.",
    ] if with_news else []))

    rep.h2("How to read these figures")
    rep.bullets([
        f"The projection extends {horizon} month(s) from the valuation point. That is the "
        "horizon the API provides for this profile, and the chart and table stop there.",
        ("The shaded region shows the distance between the two returned trajectories. It "
         "is a range that exists in the response, not an uncertainty estimate."
         if with_news else
         "The news-adjusted trajectory was not included in this report, so the chart and "
         "table carry the macro forecast only."),
        "Values are price per square metre in AED for the stated property profile — not a "
        "whole-unit price, and not an area-wide average.",
        "Where an attribute was left as “Any”, the API applied that area's own typical "
        "value, as its documentation describes.",
    ])
