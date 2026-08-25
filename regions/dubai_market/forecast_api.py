"""
Client for the TruEstates Forecast API.

    GET http://51.38.112.237:9500/forecast

Two responsibilities, and nothing else:

  1. **Input configuration.** Which values are actually valid for a given Dubai
     area, read from `data/dubai/input_ranges.csv`. This file is the only
     source of allowed values — if it is missing, this module says so and
     offers nothing, rather than substituting a guess.

  2. **The call itself.** Exactly the parameter names the API documents, no
     renaming, no invention, no second model applied to what comes back.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
─────────────────────────────────────────
* It does not smooth, resample, extrapolate or re-fit the response. The API
  states that `before_prediction` is already LOWESS-smoothed (frac = 0.10);
  applying a second smoother on top of that would misrepresent it.
* It does not manufacture future months. The API returns 5–6 forecast months;
  that is what is available and that is what is shown.
* It does not compute a confidence interval. The documented response carries
  no uncertainty field, so none is drawn. The documented ±7.5% figures are
  *model step constraints*, not an uncertainty band, and are not plotted as
  one.
* It does not send `lat`/`lon`. Those exist only so the API can resolve an
  area when `area_name` is absent; here `area_name` is always supplied from
  the global Area selector, and the dataset carries no coordinates. Inventing
  them would be inventing data.

Reference: `api_documentation_guide.docx` — "TruEstates Forecast API:
Complete Reference & Integration Guide", §2 request parameters, §4 response
structure, §5 error handling.
"""

from __future__ import annotations

import ast
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "dubai"

#: The supplied input-range table. Located by inspection, not assumption — see
#: the module docstring in `forecast_ui.py` for what happens when it is absent.
INPUT_RANGES_FILE = DATA_DIR / "input_ranges.csv"

BASE_URL = "http://51.38.112.237:9500"
ENDPOINT = "/forecast"
DEFAULT_TIMEOUT = 45.0


# ─────────────────────────────────────────────────────────────────────────────
# THE PARAMETER CONTRACT
#
# These names are the API's, transcribed from the documentation. They are not
# renamed to match local column names anywhere in this codebase, and no name
# outside this tuple is ever sent.
# ─────────────────────────────────────────────────────────────────────────────

API_PARAMS = (
    "area_name",
    "lat",
    "lon",
    "procedure_area",
    "rooms_en",
    "reg_type_en",
    "floor_bin",
    "Grade",
    "project_grade",
    "Developer_grade",
    "has_parking",
    "swimming_pool",
    "balcony",
    "elevators",
    "metro",
    "news_available",
)

#: Response keys, transcribed from §4.2 of the guide.
RESPONSE_KEYS = (
    "news_available",
    "before_prediction",
    "prediction_point",
    "forecast",
    "news_adjusted_forecast",
    "narrative",
)

#: The categorical inputs whose allowed values `input_ranges.csv` publishes
#: per area. Column name in the CSV == parameter name in the API.
CATEGORICAL_PARAMS = (
    "rooms_en",
    "reg_type_en",
    "floor_bin",
    "Grade",
    "project_grade",
    "Developer_grade",
)

#: The flag-style inputs. `input_ranges.csv` publishes the values each area
#: actually contains. Note that for `elevators` the file holds *counts*
#: (2.0, 3.0, … 30.0) while the written guide describes a 0/1 flag; the file
#: is the model's own training range, so the file's values are what is
#: offered, and both facts are stated in the interface.
FLAG_PARAMS = (
    "has_parking",
    "swimming_pool",
    "balcony",
    "elevators",
    "metro",
)

#: Sentinel meaning "do not send this parameter at all". The API documents
#: that a missing categorical is imputed from the area's own mode/median
#: (FALLBACK_CONSTANTS, §5), which is a better answer than a value picked here.
ANY = "Any"

PARAM_LABELS = {
    "rooms_en": "Rooms",
    "reg_type_en": "Registration type",
    "floor_bin": "Floor",
    "Grade": "Building grade",
    "project_grade": "Project grade",
    "Developer_grade": "Developer grade",
    "has_parking": "Parking",
    "swimming_pool": "Pool",
    "balcony": "Balcony",
    "elevators": "Elevators",
    "metro": "Metro",
    "procedure_area": "Unit size (m²)",
}


# ─────────────────────────────────────────────────────────────────────────────
# ERRORS
# ─────────────────────────────────────────────────────────────────────────────


class ForecastError(RuntimeError):
    """Base class — every failure below is surfaced, never swallowed."""


class ForecastConfigMissing(ForecastError):
    """`input_ranges.csv` is not present, so no input ranges can be offered."""


class ForecastAreaUnsupported(ForecastError):
    """HTTP 404 — the API does not recognise this area."""


class ForecastUnreachable(ForecastError):
    """The endpoint could not be contacted (network, DNS, timeout, refused)."""


class ForecastBadResponse(ForecastError):
    """A response arrived but is not the documented shape."""


# ─────────────────────────────────────────────────────────────────────────────
# INPUT CONFIGURATION — read from input_ranges.csv, never guessed
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AreaConfig:
    """
    What the model will accept for one area.

    `exact` is True when this area has its own row in `input_ranges.csv`.
    When it is False the area is not published in that file; the union of every
    published area is offered instead, and the interface says so. The API's own
    documented behaviour then applies — it either routes the area through its
    internal proxy map or answers 404, and both outcomes are reported as they
    happen rather than predicted here.
    """

    area: str
    exact: bool
    values: dict[str, list] = field(default_factory=dict)
    size_min: float | None = None
    size_max: float | None = None

    def options(self, param: str) -> list:
        return list(self.values.get(param, []))

    def is_valid(self, param: str, value) -> bool:
        if value is None or value == ANY:
            return True
        opts = self.values.get(param)
        if not opts:
            return True
        return value in opts

    def default(self, param: str):
        """A value that is always valid for this area."""
        opts = self.values.get(param, [])
        if not opts:
            return ANY
        if param in FLAG_PARAMS:
            return ANY
        preferred = {
            "rooms_en": ["1 B/R", "2 B/R", "Studio"],
            "reg_type_en": ["Existing Properties", "Off-Plan Properties"],
            "floor_bin": ["1-10", "11-20"],
            "Grade": ["B", "A", "B+"],
            "project_grade": ["B", "A", "B+"],
            "Developer_grade": ["B", "A", "B+"],
        }.get(param, [])
        for p in preferred:
            if p in opts:
                return p
        return opts[0]

    def size_default(self) -> float:
        """
        The documented API default is 45 m². It is used when it sits inside
        this area's published range; otherwise the midpoint of the range is
        used, because sending a value the API would only clamp is pointless.
        """
        lo, hi = self.size_min, self.size_max
        if lo is None or hi is None:
            return 45.0
        if lo <= 45.0 <= hi:
            return 45.0
        return round((lo + hi) / 2, 1)


def _parse_cell(raw) -> list:
    """`input_ranges.csv` stores Python list literals in each cell."""
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    try:
        parsed = ast.literal_eval(str(raw))
    except (ValueError, SyntaxError):
        return []
    if isinstance(parsed, (list, tuple)):
        return list(parsed)
    return [parsed]


def _sort_key(param: str, values: list) -> list:
    """Human ordering where there is an obvious one; otherwise as published."""
    if param == "rooms_en":
        order = ["Studio", "1 B/R", "2 B/R", "3 B/R", "4 B/R", "5 B/R",
                 "6 B/R", "7 B/R", "PENTHOUSE"]
        known = [v for v in order if v in values]
        return known + sorted(v for v in values if v not in order)
    if param == "floor_bin":
        def bin_key(v: str):
            head = str(v).split("-")[0]
            try:
                return (0, int(head))
            except ValueError:
                return (1, str(v))
        return sorted(values, key=bin_key)
    if param in FLAG_PARAMS:
        return sorted(values, key=float)
    return sorted(values, key=str)


@st.cache_data(show_spinner=False)
def _load_ranges() -> pd.DataFrame:
    if not INPUT_RANGES_FILE.exists():
        raise ForecastConfigMissing(
            f"`input_ranges.csv` was not found at `{INPUT_RANGES_FILE}`. "
            f"This file is the only published source of the valid forecast "
            f"inputs for each area — without it no input ranges can be offered, "
            f"and none are invented here. Place the supplied `input_ranges.csv` "
            f"in `data/dubai/` and reload."
        )
    return pd.read_csv(INPUT_RANGES_FILE)


def config_available() -> bool:
    try:
        _load_ranges()
        return True
    except ForecastConfigMissing:
        return False


@st.cache_data(show_spinner=False)
def published_areas() -> list[str]:
    """Areas that have their own row in `input_ranges.csv`."""
    return [str(a) for a in _load_ranges()["area_name_en"].dropna().unique()]


@st.cache_data(show_spinner=False)
def _union_config() -> dict:
    """Union of every published area — used only for areas the file omits."""
    frame = _load_ranges()
    out: dict[str, list] = {}
    for param in CATEGORICAL_PARAMS + FLAG_PARAMS:
        if param not in frame.columns:
            out[param] = []
            continue
        seen: set = set()
        for cell in frame[param]:
            seen.update(_parse_cell(cell))
        out[param] = _sort_key(param, list(seen))
    return {
        "values": out,
        "size_min": float(frame["procedure_area_min"].min()),
        "size_max": float(frame["procedure_area_max"].max()),
    }


@st.cache_data(show_spinner=False)
def area_config(area: str) -> AreaConfig:
    """
    The valid input configuration for one area.

    Raises `ForecastConfigMissing` when `input_ranges.csv` is absent. Never
    returns fabricated ranges.
    """
    frame = _load_ranges()
    row = frame[frame["area_name_en"].astype(str) == str(area)]

    if row.empty:
        union = _union_config()
        return AreaConfig(area=str(area), exact=False, values=dict(union["values"]),
                          size_min=union["size_min"], size_max=union["size_max"])

    r = row.iloc[0]
    values: dict[str, list] = {}
    for param in CATEGORICAL_PARAMS + FLAG_PARAMS:
        if param in frame.columns:
            values[param] = _sort_key(param, _parse_cell(r[param]))
        else:
            values[param] = []

    def _num(col):
        try:
            v = float(r[col])
            return None if math.isnan(v) else v
        except (TypeError, ValueError, KeyError):
            return None

    return AreaConfig(area=str(area), exact=True, values=values,
                      size_min=_num("procedure_area_min"),
                      size_max=_num("procedure_area_max"))


# ─────────────────────────────────────────────────────────────────────────────
# REVALIDATION — what happens when the global Area changes
# ─────────────────────────────────────────────────────────────────────────────


def revalidate(previous: dict, cfg: AreaConfig) -> tuple[dict, list[str]]:
    """
    Carry the previous inputs into a new area, resetting anything that area
    does not accept.

    Returns `(inputs, reset_labels)`. Every value in the returned dict is valid
    for `cfg`, so an invalid combination can never reach the API.
    """
    inputs: dict = {}
    reset: list[str] = []

    for param in CATEGORICAL_PARAMS + FLAG_PARAMS:
        old = previous.get(param, None)
        if old is None:
            inputs[param] = cfg.default(param)
            continue
        if cfg.is_valid(param, old):
            inputs[param] = old
        else:
            inputs[param] = cfg.default(param)
            reset.append(PARAM_LABELS.get(param, param))

    size = previous.get("procedure_area")
    lo, hi = cfg.size_min, cfg.size_max
    if size is None:
        inputs["procedure_area"] = cfg.size_default()
    elif lo is not None and hi is not None and not (lo <= float(size) <= hi):
        inputs["procedure_area"] = cfg.size_default()
        reset.append(PARAM_LABELS["procedure_area"])
    else:
        inputs["procedure_area"] = float(size)

    inputs["news_available"] = bool(previous.get("news_available", True))
    return inputs, reset


# ─────────────────────────────────────────────────────────────────────────────
# THE REQUEST
# ─────────────────────────────────────────────────────────────────────────────


def build_query(area: str, inputs: dict) -> dict:
    """
    Turn the interface's state into the API's query parameters.

    `ANY` values are omitted entirely, which is what makes the API apply its
    own documented per-area imputation instead of a value chosen here.
    `lat`/`lon` are never sent — see the module docstring.
    """
    query: dict = {"area_name": str(area)}

    for param in CATEGORICAL_PARAMS:
        value = inputs.get(param)
        if value is not None and value != ANY:
            query[param] = str(value)

    for param in FLAG_PARAMS:
        value = inputs.get(param)
        if value is None or value == ANY:
            continue
        num = float(value)
        query[param] = int(num) if num.is_integer() else num

    size = inputs.get("procedure_area")
    if size is not None:
        query["procedure_area"] = float(size)

    query["news_available"] = bool(inputs.get("news_available", True))

    unknown = set(query) - set(API_PARAMS)
    if unknown:  # pragma: no cover — a guard against future drift
        raise ForecastError(f"Refusing to send undocumented parameters: {sorted(unknown)}")
    return query


def request_url(query: dict) -> str:
    """The exact URL that will be requested — shown in the interface."""
    encoded = urllib.parse.urlencode(
        {k: (str(v) if not isinstance(v, bool) else ("True" if v else "False"))
         for k, v in query.items()},
        quote_via=urllib.parse.quote,
    )
    return f"{BASE_URL}{ENDPOINT}?{encoded}"


def _http_get(url: str, timeout: float) -> tuple[int, str]:
    """
    Plain stdlib GET.

    `requests` is a hard dependency of Streamlit so it is always present, but
    urllib removes even that assumption and behaves identically for a GET with
    no authentication.
    """
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover
            pass
        return exc.code, body
    except urllib.error.URLError as exc:
        raise ForecastUnreachable(str(getattr(exc, "reason", exc))) from exc
    except (TimeoutError, OSError) as exc:
        raise ForecastUnreachable(str(exc)) from exc


def fetch(area: str, inputs: dict, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """
    Call the API once and return the parsed JSON exactly as received.

    Nothing here modifies a returned number.
    """
    query = build_query(area, inputs)
    url = request_url(query)
    status, body = _http_get(url, timeout)

    if status == 404:
        detail = f"Area '{area}' not found or supported."
        try:
            detail = json.loads(body).get("detail", detail)
        except Exception:
            pass
        raise ForecastAreaUnsupported(detail)

    if status != 200:
        snippet = (body or "").strip()[:400]
        raise ForecastBadResponse(f"HTTP {status} from the forecast API. {snippet}".strip())

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ForecastBadResponse(
            f"The forecast API returned a body that is not JSON ({exc})."
        ) from exc

    if not isinstance(data, dict):
        raise ForecastBadResponse("The forecast API returned JSON that is not an object.")

    missing = [k for k in ("before_prediction", "prediction_point", "forecast")
               if k not in data]
    if missing:
        raise ForecastBadResponse(
            f"The forecast response is missing required field(s): {', '.join(missing)}. "
            f"Fields received: {', '.join(sorted(data)) or 'none'}."
        )

    data["_request_url"] = url
    data["_request_query"] = query
    data["_request_area"] = str(area)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE PARSING
# ─────────────────────────────────────────────────────────────────────────────


def _series(raw) -> pd.DataFrame:
    """`[{timestamp, value}, …]` → a two-column frame, values untouched."""
    if not raw:
        return pd.DataFrame(columns=["timestamp", "value"])
    rows = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        ts = pd.to_datetime(item.get("timestamp"), errors="coerce")
        try:
            val = float(item.get("value"))
        except (TypeError, ValueError):
            continue
        if pd.isna(ts):
            continue
        rows.append({"timestamp": ts, "value": val})
    frame = pd.DataFrame(rows, columns=["timestamp", "value"])
    return frame.sort_values("timestamp").reset_index(drop=True)


@dataclass
class ForecastResult:
    """
    The response, arranged for drawing. Every number is the API's own.

    `horizon_months` is counted from what actually arrived — it is never
    assumed, rounded up, or padded to a nicer number.
    """

    area: str
    news_available: bool
    history: pd.DataFrame
    now: pd.DataFrame
    macro: pd.DataFrame
    news: pd.DataFrame
    narrative: str
    request_url: str
    request_query: dict
    raw: dict

    @property
    def now_timestamp(self):
        """The API's own `prediction_point` timestamp — never today's date."""
        if self.now.empty:
            return None
        return self.now["timestamp"].iloc[0]

    @property
    def now_value(self) -> float | None:
        if self.now.empty:
            return None
        return float(self.now["value"].iloc[0])

    @property
    def horizon_months(self) -> int:
        return int(len(self.macro))

    @property
    def has_news(self) -> bool:
        return bool(self.news_available) and not self.news.empty

    def anchored(self, which: str) -> pd.DataFrame:
        """
        A forecast series with the prediction point prepended.

        This adds no value: the documentation states both trajectories are
        "propagated from the exact same baseline", so the line genuinely starts
        at `prediction_point`. Drawing it disconnected would be the inaccuracy.
        """
        series = self.macro if which == "macro" else self.news
        if series.empty:
            return series
        if self.now.empty:
            return series
        return pd.concat([self.now, series], ignore_index=True)

    #: Column names are kept short so they fit a printed table without being
    #: shrunk; the unit is stated once in the caption instead of five times.
    TABLE_MACRO = "Macro forecast"
    TABLE_NEWS = "News-adjusted"
    TABLE_DIFF = "Difference"
    TABLE_DIFF_PCT = "Difference %"

    def table(self, include_news: bool = True,
              include_difference: bool = True) -> pd.DataFrame:
        """
        The forecast months as a table — exactly the returned values.

        `include_news` follows the interface's news toggle: with it off the
        news-adjusted column is not produced at all, so nothing downstream has
        to remember to hide it. `include_difference` controls the two derived
        comparison columns, which the PDF omits.
        """
        if self.macro.empty:
            return pd.DataFrame()
        out = self.macro.rename(columns={"value": self.TABLE_MACRO}).copy()
        if include_news and self.has_news:
            merged = self.news.rename(columns={"value": self.TABLE_NEWS})
            out = out.merge(merged, on="timestamp", how="left")
            if include_difference:
                delta = out[self.TABLE_NEWS] - out[self.TABLE_MACRO]
                out[self.TABLE_DIFF] = delta
                out[self.TABLE_DIFF_PCT] = delta / out[self.TABLE_MACRO] * 100
        out.insert(0, "Month", out["timestamp"].dt.strftime("%b %Y"))
        return out.drop(columns=["timestamp"])


def parse(data: dict) -> ForecastResult:
    narrative = data.get("narrative")
    return ForecastResult(
        area=str(data.get("_request_area", "")),
        news_available=bool(data.get("news_available", False)),
        history=_series(data.get("before_prediction")),
        now=_series(data.get("prediction_point")),
        macro=_series(data.get("forecast")),
        news=_series(data.get("news_adjusted_forecast")),
        narrative=(narrative or "").strip(),
        request_url=str(data.get("_request_url", "")),
        request_query=dict(data.get("_request_query", {})),
        raw=data,
    )
