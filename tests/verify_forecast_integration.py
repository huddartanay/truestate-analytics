#!/usr/bin/env python3
"""
Offline checks on the Forecast integration.

    python tests/verify_forecast_integration.py

Nothing here contacts the network. The response used to drive the chart, the
table and the PDF is the **example response printed in §4.1 of
`api_documentation_guide.docx`** — it is a documentation fixture, it is labelled
as one everywhere it appears, and it exists only so the drawing code can be
exercised without a live endpoint. It is never loaded by the application and is
never shown to a user as a real forecast. For real values, run
`tests/verify_forecast_api.py` against the live API.

What is checked:

  * `input_ranges.csv` is present and drives the offered inputs
  * an invalid value for a new area is reset, not sent
  * only documented parameter names are ever sent, and lat/lon never are
  * the chart is drawn from the response and adds no series of its own
  * no confidence interval is constructed from a response that has none
  * the "now" marker comes from `prediction_point`, not from today's date
  * the forecast is not extended beyond the months returned
  * the PDF builds from the response already held, without a second request
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from regions.dubai_market import charts as ch  # noqa: E402
from regions.dubai_market import forecast_api as fapi  # noqa: E402

GREEN, RED, DIM, BOLD, OFF = "\033[32m", "\033[1;31m", "\033[2m", "\033[1m", "\033[0m"
PASSED = FAILED = 0


def check(label: str, expected, actual) -> None:
    global PASSED, FAILED
    if expected == actual:
        PASSED += 1
        print(f"  [{GREEN}PASS{OFF}] {label}  {DIM}{actual}{OFF}")
    else:
        FAILED += 1
        print(f"  [{RED}FAIL{OFF}] {label}  {DIM}expected={expected}  got={actual}{OFF}")


def section(title: str) -> None:
    print(f"\n{BOLD}{title}{OFF}")
    print("─" * 70)


# ── The documentation fixture ────────────────────────────────────────────────
# Transcribed from api_documentation_guide.docx §4.1 "Example JSON Response
# (200 OK)". These are the guide's own illustrative numbers. They are not a
# forecast, not a measurement, and are used here only to drive the code paths.
DOC_FIXTURE = {
    "news_available": True,
    "before_prediction": [
        {"timestamp": "2026-03-31", "value": 14650.00},
        {"timestamp": "2026-04-30", "value": 14780.50},
        {"timestamp": "2026-05-31", "value": 14820.00},
        {"timestamp": "2026-06-30", "value": 14850.10},
        {"timestamp": "2026-07-31", "value": 14865.12},
    ],
    "prediction_point": [{"timestamp": "2026-08-31", "value": 14865.12}],
    "forecast": [
        {"timestamp": "2026-09-30", "value": 14865.12},
        {"timestamp": "2026-10-31", "value": 14899.78},
        {"timestamp": "2026-11-30", "value": 14748.63},
        {"timestamp": "2026-12-31", "value": 14710.20},
        {"timestamp": "2027-01-31", "value": 14795.40},
    ],
    "news_adjusted_forecast": [
        {"timestamp": "2026-09-30", "value": 13305.28},
        {"timestamp": "2026-10-31", "value": 12002.61},
        {"timestamp": "2026-11-30", "value": 11262.32},
        {"timestamp": "2026-12-31", "value": 11150.80},
        {"timestamp": "2027-01-31", "value": 11320.15},
    ],
    "narrative": "Documentation example narrative — not a real market statement.",
    "_request_url": "http://51.38.112.237:9500/forecast?area_name=Al%20Barsha%20South%20Fourth",
    "_request_query": {"area_name": "Al Barsha South Fourth"},
    "_request_area": "Al Barsha South Fourth",
}


def main() -> int:
    # Comments and docstrings are stripped before these scans, so a module that
    # *says* "no XGBoost is applied" is not flagged for saying so.
    import io as _io
    import tokenize as _tok

    def _code_only(text: str) -> str:
        kept = []
        try:
            for tok in _tok.generate_tokens(_io.StringIO(text).readline):
                if tok.type in (_tok.COMMENT, _tok.STRING):
                    continue
                kept.append(tok.string)
        except (_tok.TokenError, IndentationError):  # pragma: no cover
            return text
        return " ".join(kept)

    # ── 1. input_ranges.csv ─────────────────────────────────────────────────
    section("1. The input configuration comes from input_ranges.csv, not from guesses")

    check("input_ranges.csv is present", True, fapi.INPUT_RANGES_FILE.exists())
    areas = fapi.published_areas()
    check("areas published in the file", 35, len(areas))

    cfg = fapi.area_config("Al Warsan First")
    check("Al Warsan First has its own row", True, cfg.exact)
    check("its rooms come from the file", True,
          cfg.options("rooms_en") == sorted(
              cfg.options("rooms_en"),
              key=lambda v: ["Studio", "1 B/R", "2 B/R", "3 B/R", "4 B/R", "5 B/R",
                             "6 B/R", "7 B/R", "PENTHOUSE"].index(v)))
    check("an area absent from the file is marked as such", False,
          fapi.area_config("Mirdif").exact)

    # ── 2. Revalidation on area change ──────────────────────────────────────
    section("2. Changing the area revalidates every input and resets what does not fit")

    palm = fapi.area_config("Palm Jumeirah")
    wide = {"rooms_en": "7 B/R", "floor_bin": "1-10", "Grade": "A",
            "project_grade": "A", "Developer_grade": "A",
            "procedure_area": 2500.0, "news_available": True,
            "has_parking": fapi.ANY, "swimming_pool": fapi.ANY,
            "balcony": fapi.ANY, "elevators": fapi.ANY, "metro": fapi.ANY}
    check("7 B/R is valid in Palm Jumeirah", True, palm.is_valid("rooms_en", "7 B/R"))
    check("2,500 m² is inside Palm Jumeirah's range", True,
          palm.size_min <= 2500.0 <= palm.size_max)

    warsan = fapi.area_config("Al Warsan First")
    moved, reset = fapi.revalidate(wide, warsan)
    check("7 B/R is NOT valid in Al Warsan First", False,
          warsan.is_valid("rooms_en", "7 B/R"))
    check("rooms were reset", True, "Rooms" in reset)
    check("unit size was reset", True, "Unit size (m²)" in reset)
    check("every value carried over is valid for the new area", True,
          all(warsan.is_valid(p, moved[p])
              for p in fapi.CATEGORICAL_PARAMS + fapi.FLAG_PARAMS))
    check("the size now sits inside the new area's range", True,
          warsan.size_min <= moved["procedure_area"] <= warsan.size_max)
    print(f"  {DIM}reset: {reset}{OFF}")

    # ── 3. The request ──────────────────────────────────────────────────────
    section("3. Only documented parameter names are sent")

    query = fapi.build_query("Al Warsan First", moved)
    check("no undocumented parameter", set(), set(query) - set(fapi.API_PARAMS))
    check("lat is never sent", False, "lat" in query)
    check("lon is never sent", False, "lon" in query)
    check("area_name is always sent", True, "area_name" in query)

    anyd = dict(moved)
    anyd["has_parking"] = fapi.ANY
    check("an 'Any' value is omitted rather than guessed", False,
          "has_parking" in fapi.build_query("Al Warsan First", anyd))

    explicit = dict(moved)
    explicit["has_parking"] = 1
    check("an explicit flag IS sent", 1,
          fapi.build_query("Al Warsan First", explicit).get("has_parking"))

    # ── 4. Parsing ──────────────────────────────────────────────────────────
    section("4. The response is read exactly as documented")
    print(f"  {DIM}fixture: the example response in api_documentation_guide.docx §4.1 — "
          f"a documentation sample, not a forecast{OFF}")

    result = fapi.parse(DOC_FIXTURE)
    check("history months read", 5, len(result.history))
    check("one prediction point", 1, len(result.now))
    check("forecast months read", 5, result.horizon_months)
    check("news-adjusted months read", 5, len(result.news))
    check("history values are untouched", 14650.00, float(result.history["value"].iloc[0]))
    check("the last forecast value is untouched", 14795.40,
          float(result.macro["value"].iloc[-1]))

    # ── 5. The "now" marker ─────────────────────────────────────────────────
    section("5. 'Now' comes from prediction_point, never from today's date")

    check("the marker sits on the returned timestamp",
          pd.Timestamp("2026-08-31"), pd.Timestamp(result.now_timestamp))
    check("the marker is not today", False,
          pd.Timestamp(result.now_timestamp).date() == pd.Timestamp.today().date())

    src = (ROOT / "regions" / "dubai_market" / "charts.py").read_text()
    fc_src = "def api_forecast_chart" + src.split("def api_forecast_chart", 1)[1]
    fc_code = _code_only(fc_src)
    for banned in ("datetime.now", "date.today", "Timestamp.now", "pd.Timestamp.today"):
        check(f"the chart never calls {banned}", False, banned in fc_code)

    # ── 6. No second model, no invented months, no invented interval ────────
    section("6. Nothing is added on this side of the API")

    ui_src = (ROOT / "regions" / "dubai_market" / "forecast_ui.py").read_text()
    api_src = (ROOT / "regions" / "dubai_market" / "forecast_api.py").read_text()

    joined = _code_only(fc_src) + _code_only(ui_src) + _code_only(api_src)

    for banned in ("RandomForest", "XGB", "xgboost", "lowess(", "ExponentialSmoothing",
                   "ARIMA", "SARIMAX", "rolling(", "ewm(", "interpolate(",
                   "polyfit", "LinearRegression"):
        check(f"no second model or smoother: {banned}", False, banned in joined)

    for banned in ("1.05", "0.95", "1.10", "0.90", "* 1.075", "* 0.925"):
        check(f"no fabricated interval multiplier: {banned}", False, banned in joined)

    for banned in ("date_range", "resample(", "reindex(", "ffill(", "bfill(",
                   "fillna(method", "pd.concat([self.macro, self.macro"):
        check(f"no manufactured future months: {banned}", False, banned in joined)

    # ── 7. The chart draws the response and nothing else ────────────────────
    section("7. The chart's traces all trace back to the response")

    fig = ch.api_forecast_chart(result, dark=False)
    ys = {name: list(tr.y) for name, tr in
          ((tr.name or f"_{i}", tr) for i, tr in enumerate(fig.data))}

    macro_trace = ys.get("Macro forecast", [])
    check("the macro line has the 5 forecast months plus the anchor", 6, len(macro_trace))
    check("it starts at the prediction point", 14865.12, macro_trace[0])
    check("it ends at the last returned value", 14795.40, macro_trace[-1])

    news_trace = ys.get("News-adjusted forecast", [])
    check("the news line has the same length", 6, len(news_trace))
    check("it starts at the same anchor", 14865.12, news_trace[0])

    # The history line now runs through to the valuation point, so it carries the
    # 5 returned history months plus that anchor — this is the Jul→Aug fix.
    check("the history line is the 5 history months plus the valuation point", 6,
          len(ys.get("Historical", [])))
    check("it ends on the valuation point", 14865.12, ys.get("Historical", [])[-1])
    check("the recorded-median context series is gone", False,
          any("Recorded market history" in n for n in ys))

    band_names = [n for n in ys if "Range between" in n]
    check("one shaded region, and it is named as a range not a confidence band",
          1, len(band_names))
    check("the word 'confidence' appears nowhere in the chart code", False,
          "confidence" in fc_src.lower())

    # ── 8. news_available = False ───────────────────────────────────────────
    section("8. With no news data, the news series and the band simply are not drawn")

    quiet = dict(DOC_FIXTURE)
    quiet["news_available"] = False
    quiet["news_adjusted_forecast"] = []
    quiet["narrative"] = None
    qres = fapi.parse(quiet)
    check("has_news is False", False, qres.has_news)
    check("the narrative is empty", "", qres.narrative)
    qfig = ch.api_forecast_chart(qres, dark=False)
    qnames = [tr.name for tr in qfig.data if tr.name]
    check("no news-adjusted trace", False, "News-adjusted forecast" in qnames)
    check("no shaded region", 0, len([n for n in qnames if "Range between" in n]))
    check("the macro line is still drawn", True, "Macro forecast" in qnames)
    check("the table has no news columns", False,
          any("News" in c for c in qres.table().columns))

    # ── 9. The table ────────────────────────────────────────────────────────
    section("9. The table is the returned months, one row each")

    table = result.table()
    check("one row per returned forecast month", 5, len(table))
    check("months are labelled from the response", "Sep 2026", table["Month"].iloc[0])
    check("macro values are unchanged", 14899.78,
          float(table[fapi.ForecastResult.TABLE_MACRO].iloc[1]))
    printed = result.table(include_news=True, include_difference=False)
    check("the printed table carries no Difference column", False,
          fapi.ForecastResult.TABLE_DIFF in printed.columns)
    check("the printed table carries no Difference % column", False,
          fapi.ForecastResult.TABLE_DIFF_PCT in printed.columns)
    check("with the news toggle off there is no news column", False,
          fapi.ForecastResult.TABLE_NEWS in result.table(include_news=False).columns)

    # ── 10. The report reuses the response ──────────────────────────────────
    section("10. The PDF is built from the response already held")

    import matplotlib
    matplotlib.use("Agg")
    from platform_core import forecast_report as fr

    report_src = (ROOT / "platform_core" / "forecast_report.py").read_text()
    check("the report module never calls the API", False,
          any(t in report_src for t in ("fetch(", "urlopen", "requests.get")))

    pdf = fr.build(result, "Al Barsha South Fourth",
                   {"rooms_en": "1 B/R", "floor_bin": "1-10",
                    "reg_type_en": "Off-Plan Properties", "procedure_area": 45.0})
    check("the PDF is produced", True, isinstance(pdf, bytes) and len(pdf) > 10_000)
    check("it is a PDF", b"%PDF", pdf[:4])
    print(f"  {DIM}{len(pdf) / 1024:,.0f} KB{OFF}")

    # ── 11. The area rule ───────────────────────────────────────────────────
    section("11. There is no second area control, and stale results cannot appear")

    check("the forecast section creates exactly one disabled control", 1,
          ui_src.count("disabled=True"))
    check("the read-only area control is disabled", True,
          'disabled=True, key="dxb_fc_area_readonly"' in ui_src)
    check("the area is read from the platform state, never chosen here", False,
          "nav.set_area" in ui_src)
    check("a result is stored with the signature that produced it", True,
          "K_SIG" in ui_src and "_signature(area, inputs)" in ui_src)
    check("changing the area clears any held result", True,
          "_clear_result()" in ui_src.split("previous_area != area", 1)[1][:400])

    sig_a = None
    sig_b = None
    from regions.dubai_market import forecast_ui as fui
    sig_a = fui._signature("Palm Jumeirah", moved)
    sig_b = fui._signature("Al Warsan First", moved)
    check("the same inputs under two areas produce different signatures", True,
          sig_a != sig_b)

    print()
    print("═" * 70)
    colour = GREEN if FAILED == 0 else RED
    print(f"  {colour}{PASSED}/{PASSED + FAILED} checks passed{OFF}")
    print("═" * 70)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
