#!/usr/bin/env python3
"""
Live check of the TruEstates Forecast API.

RUN THIS ON A MACHINE THAT CAN REACH THE ENDPOINT.

    cd ~/Downloads/uae-real-estate-analytics
    source .venv/bin/activate
    python tests/verify_forecast_api.py

What it does: sends the documented request, prints exactly what comes back, and
checks the response against the contract in `api_documentation_guide.docx`. It
asserts nothing about the *values* — only about the shape — because the values
are the model's and are not this script's to judge.

Two of its checks matter more than the rest:

  * how many forecast months actually arrive. The interface is built to draw
    however many there are. If this prints 5 or 6, the 1Y / 2Y / 3Y+ control is
    correctly a *historical window* control and not a forecast-length control.
  * whether any uncertainty / confidence field is present. If this prints
    "none", then the interface is right not to draw a confidence band, and any
    band it did draw would have been invented.

Pass an area as the first argument to test a different one:

    python tests/verify_forecast_api.py "Palm Jumeirah"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from regions.dubai_market import forecast_api as fapi  # noqa: E402

GREEN, RED, YELLOW, DIM, BOLD, OFF = (
    "\033[32m", "\033[1;31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m")

PASSED = 0
FAILED = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  [{GREEN}PASS{OFF}] {label}" + (f"  {DIM}{detail}{OFF}" if detail else ""))
    else:
        FAILED += 1
        print(f"  [{RED}FAIL{OFF}] {label}" + (f"  {DIM}{detail}{OFF}" if detail else ""))


def section(title: str) -> None:
    print(f"\n{BOLD}{title}{OFF}")
    print("─" * 66)


def main() -> int:
    area = sys.argv[1] if len(sys.argv) > 1 else "Al Barsha South Fourth"

    section("1. input_ranges.csv")
    print(f"  looking for: {fapi.INPUT_RANGES_FILE}")
    try:
        areas = fapi.published_areas()
    except fapi.ForecastConfigMissing as exc:
        print(f"  {RED}{exc}{OFF}")
        return 1
    check("input_ranges.csv is present and readable", True, f"{len(areas)} areas published")
    check(f"'{area}' has its own row", area in areas,
          "yes" if area in areas else "no — the union of published ranges would be offered")

    cfg = fapi.area_config(area)
    print(f"  {DIM}rooms_en   : {cfg.options('rooms_en')}{OFF}")
    print(f"  {DIM}floor_bin  : {cfg.options('floor_bin')}{OFF}")
    print(f"  {DIM}size range : {cfg.size_min} – {cfg.size_max} m²{OFF}")

    section("2. The request")
    inputs, _ = fapi.revalidate({}, cfg)
    query = fapi.build_query(area, inputs)
    url = fapi.request_url(query)
    print(f"  {url}")
    check("every parameter name is one the API documents",
          set(query) <= set(fapi.API_PARAMS),
          f"{len(query)} parameters")
    check("lat/lon are not sent", "lat" not in query and "lon" not in query,
          "area_name is always supplied, so coordinates are not needed and none are invented")

    section("3. The call")
    try:
        data = fapi.fetch(area, inputs)
    except fapi.ForecastAreaUnsupported as exc:
        print(f"  {YELLOW}404 — {exc}{OFF}")
        print(f"  {DIM}This is a documented outcome, handled in the interface. Try another "
              f"area.{OFF}")
        return 1
    except fapi.ForecastUnreachable as exc:
        print(f"  {RED}Could not reach {fapi.BASE_URL} — {exc}{OFF}")
        print(f"  {DIM}Run this on a machine with access to that host.{OFF}")
        return 1
    except fapi.ForecastError as exc:
        print(f"  {RED}{type(exc).__name__}: {exc}{OFF}")
        return 1

    check("HTTP 200 with a JSON object", isinstance(data, dict))
    payload = {k: v for k, v in data.items() if not k.startswith("_")}
    print(f"  {DIM}keys returned: {', '.join(sorted(payload))}{OFF}")

    section("4. The documented response contract")
    for key in fapi.RESPONSE_KEYS:
        check(f"`{key}` present", key in payload,
              type(payload.get(key)).__name__ if key in payload else "missing")

    unexpected = sorted(set(payload) - set(fapi.RESPONSE_KEYS))
    if unexpected:
        print(f"  {YELLOW}extra fields not in the guide: {unexpected}{OFF}")
        print(f"  {DIM}Nothing in the interface reads these. If one of them carries an "
              f"uncertainty range, say so and a real band can be drawn.{OFF}")

    section("5. What actually arrived")
    result = fapi.parse(data)
    print(f"  history months        : {len(result.history)}")
    print(f"  prediction points     : {len(result.now)}")
    print(f"  forecast months       : {result.horizon_months}")
    print(f"  news-adjusted months  : {len(result.news)}")
    print(f"  narrative             : {len(result.narrative)} characters")
    print(f"  news_available        : {result.news_available}")

    check("there is exactly one prediction point", len(result.now) == 1,
          str(result.now_timestamp))
    check("the forecast has at least one month", result.horizon_months >= 1)
    check("every timestamp parsed as a date",
          not result.history["timestamp"].isna().any()
          and not result.macro["timestamp"].isna().any())
    if result.has_news:
        check("the news-adjusted series aligns with the macro series month for month",
              list(result.news["timestamp"]) == list(result.macro["timestamp"]),
              f"{len(result.news)} vs {result.horizon_months}")

    section("6. The two questions that decide what may be drawn")
    horizon = result.horizon_months
    print(f"  {BOLD}Forecast horizon: {horizon} month(s).{OFF}")
    if horizon <= 8:
        print(f"  {GREEN}→ Under a year. The 1Y / 2Y / 3Y+ control is therefore a "
              f"HISTORICAL WINDOW control{OFF}")
        print(f"  {GREEN}  in the interface, and the forecast lines stop after "
              f"{horizon} months. Correct.{OFF}")
    else:
        print(f"  {YELLOW}→ Longer than expected. The interface will draw all {horizon} "
              f"months.{OFF}")

    ci_fields = [k for k in payload
                 if any(w in k.lower() for w in
                        ("conf", "interval", "lower", "upper", "ci", "std", "sigma",
                         "error", "band", "quantile", "percentile"))]
    print(f"  {BOLD}Uncertainty fields in the response: "
          f"{', '.join(ci_fields) if ci_fields else 'none'}.{OFF}")
    if ci_fields:
        print(f"  {YELLOW}→ A real confidence band could be drawn from {ci_fields}. Tell "
              f"me and I will add it.{OFF}")
    else:
        print(f"  {GREEN}→ No uncertainty is returned, so the interface draws no "
              f"confidence interval.{OFF}")
        print(f"  {GREEN}  The shaded region on the chart is the gap between the two "
              f"returned forecasts.{OFF}")

    section("7. A 404 is handled, not guessed at")
    try:
        fapi.fetch("Definitely Not A Dubai Area 12345", inputs)
        check("an unknown area is rejected by the API", False, "it returned 200")
    except fapi.ForecastAreaUnsupported as exc:
        check("an unknown area raises ForecastAreaUnsupported", True, str(exc))
    except fapi.ForecastError as exc:
        check("an unknown area fails cleanly", True, f"{type(exc).__name__}: {exc}")

    section("Raw response")
    print(json.dumps(payload, indent=2, default=str)[:2400])

    print()
    print("═" * 66)
    colour = GREEN if FAILED == 0 else RED
    print(f"  {colour}{PASSED}/{PASSED + FAILED} checks passed{OFF}")
    print("═" * 66)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
