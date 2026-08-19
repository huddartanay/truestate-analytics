"""
The Forecast section, rendered on the 🔮 **Forecast** page.

THE AREA RULE
─────────────
There is exactly ONE area control in this application: the global 📍 Area.
This subsection **reads** it and shows it read-only. It does not offer a second
selector, and it cannot be used to override the selection. When the global Area
changes, this subsection:

    1. detects the change,
    2. reloads the valid input configuration for the new area from
       `input_ranges.csv`,
    3. revalidates every input the user had already chosen,
    4. resets any value the new area does not accept, and says which,
    5. discards any forecast held for the previous area before drawing anything.

Step 5 is what makes a stale result impossible: the response is stored together
with the area and the exact inputs that produced it, and it is only ever drawn
when that signature still matches the current state.

WHAT IS NOT DONE HERE
─────────────────────
No second forecasting model runs on the response — no Random Forest, no
XGBoost, no LOWESS, no moving average. No months are invented to fill a longer
horizon. No confidence interval is constructed. The chart shows the API's own
numbers and stops where the API stops.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core.chart_theme import PLOTLY_CONFIG

from . import chart_info as ci
from . import charts as ch
from . import forecast_api as fapi
from .data import COL

# Session keys. All namespaced `dxb_fc_` so they cannot collide with the
# dashboard's own state or with the report keys already in use.
K_AREA = "dxb_fc_area"          # the area the current inputs belong to
K_INPUTS = "dxb_fc_inputs"      # the profile the user has chosen
K_RESULT = "dxb_fc_result"      # the parsed response
K_SIG = "dxb_fc_sig"            # (area, inputs) that produced K_RESULT
K_ERROR = "dxb_fc_error"        # last failure, with its signature
K_RESET = "dxb_fc_reset_note"   # fields reset by the last area change

#: The historical window. `None` means "everything the response contains" —
#: which is genuinely more than the written guide suggests: the live API returns
#: several years of `before_prediction`, not the "up to 6 months" the document
#: describes. The window governs HISTORY only. The forecast is always drawn in
#: full, for exactly as many months as the response carries.
WINDOWS = {"1Y": 12, "2Y": 24, "3Y+": None}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def _signature(area: str, inputs: dict) -> tuple:
    """Identity of one forecast: the area plus every value that was sent."""
    return (str(area), tuple(sorted((k, str(v)) for k, v in inputs.items())))


def _flag_label(param: str, value) -> str:
    """Read `0`/`1` as No/Yes; leave genuine counts as counts."""
    if value == fapi.ANY:
        return "Any"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if param == "elevators":
        return f"{num:g}"
    return {0.0: "No", 1.0: "Yes"}.get(num, f"{num:g}")


def _window_start(until, months, api_first=None):
    """
    The first month the chart shows.

    `months=None` is the "3Y+" setting: show everything the API returned, and
    no further back than that. Both series — the API's history and the local
    context median — are trimmed to this one boundary, so the chart never puts
    fifteen years of local history behind six years of model history.
    """
    if until is None:
        return None
    if months is None:
        return pd.Timestamp(api_first) if api_first is not None else None
    return pd.Timestamp(until) - pd.DateOffset(months=int(months) - 1)


def _local_history(df_area: pd.DataFrame, until, start) -> pd.DataFrame:
    """
    The area's genuine recorded monthly median rate per m², from the cleaned
    dataset.

    This is a real, separately-labelled series. It is what gives the historical
    window control something to show — it is never spliced onto the API's own
    history, and it is never used to extend the forecast.
    """
    if df_area is None or df_area.empty or until is None:
        return pd.DataFrame(columns=["timestamp", "value"])
    rate, date = COL["rate"], COL["date"]
    if rate not in df_area.columns or date not in df_area.columns:
        return pd.DataFrame(columns=["timestamp", "value"])

    work = df_area[[date, rate]].dropna()
    if work.empty:
        return pd.DataFrame(columns=["timestamp", "value"])

    grouped = (
        work.assign(_m=pd.to_datetime(work[date]).dt.to_period("M").dt.to_timestamp("M"))
        .groupby("_m", observed=True)[rate].median()
        .reset_index()
        .rename(columns={"_m": "timestamp", rate: "value"})
    )
    window = grouped[grouped["timestamp"] <= pd.Timestamp(until)]
    if start is not None:
        window = window[window["timestamp"] >= pd.Timestamp(start)]
    return window.sort_values("timestamp").reset_index(drop=True)


def _narrative_md(text: str) -> str:
    """
    Prepare the API's narrative for Markdown rendering.

    The only change made is to line breaks: a single newline is invisible in
    Markdown, so each line is given a hard break and blank lines are preserved
    as paragraph splits. No word, figure or piece of punctuation is altered,
    added or removed.
    """
    paragraphs = [p.strip() for p in str(text).replace("\r\n", "\n").split("\n\n")]
    rendered = []
    for para in paragraphs:
        if not para:
            continue
        rendered.append("  \n".join(line.strip() for line in para.split("\n") if line.strip()))
    return "\n\n".join(rendered)


def _clear_result() -> None:
    for key in (K_RESULT, K_SIG, K_ERROR):
        st.session_state.pop(key, None)


# ─────────────────────────────────────────────────────────────────────────────
# THE SUBSECTION
# ─────────────────────────────────────────────────────────────────────────────


def render(area: str, df_area: pd.DataFrame | None = None, dark: bool = False) -> None:
    """
    `area` is the global 📍 Area — passed in, never re-chosen here.
    `df_area` is the dashboard's already-filtered frame for that area.
    """
    ui.section("Forecast",
               "Price per m² for one property profile, from the TruEstate Forecast API.",
               "🔮")

    # ── the input configuration ─────────────────────────────────────────────
    try:
        cfg = fapi.area_config(area) if area != C.ALL_AREAS else None
    except fapi.ForecastConfigMissing as exc:
        st.error(
            f"**The forecast input ranges are not available.**\n\n{exc}", icon="⚠️")
        return

    # ── the area, read-only ─────────────────────────────────────────────────
    _read_only_area(area, cfg)

    if area == C.ALL_AREAS:
        st.info(
            "The forecast is produced for **one area at a time**, because the model is "
            "fitted per area. Choose an area under 📍 **Area** and this section will "
            "prepare a forecast for it.", icon="📍")
        _clear_result()
        st.session_state[K_AREA] = area
        return

    # ── AREA CHANGE: reload config, revalidate, reset, drop stale results ───
    previous_area = st.session_state.get(K_AREA)
    if previous_area != area:
        carried = st.session_state.get(K_INPUTS, {})
        inputs, reset = fapi.revalidate(carried, cfg)
        st.session_state[K_INPUTS] = inputs
        st.session_state[K_AREA] = area
        st.session_state[K_RESET] = reset if previous_area is not None else []
        _clear_result()

    if not st.session_state.get(K_INPUTS):
        st.session_state[K_INPUTS], _ = fapi.revalidate({}, cfg)

    reset_note = st.session_state.get(K_RESET) or []
    if reset_note:
        st.caption(
            f"**Adjusted for {area}.** {', '.join(reset_note)} — the previous value is not "
            f"among the values recorded for this area, so each has been set to one that is.")

    if not cfg.exact:
        st.caption(
            f"**{area}** does not have its own row in `input_ranges.csv`, so the options "
            f"below are the values published across all listed areas. The API applies its "
            f"own per-area handling to whatever is sent — if it has a grouped or proxy "
            f"model for this area it will use it, and if it does not recognise the area at "
            f"all it will say so, and that answer is shown here as it arrives.")

    # ── the profile ─────────────────────────────────────────────────────────
    inputs = _profile_controls(cfg, st.session_state[K_INPUTS])
    st.session_state[K_INPUTS] = inputs

    signature = _signature(area, inputs)

    # ── fetch ───────────────────────────────────────────────────────────────
    left, right = st.columns([1, 2], gap="large")
    with left:
        run = st.button("📊  Market Pulse", type="primary",
                        use_container_width=True, key="dxb_fc_run")
    with right:
        stored_sig = st.session_state.get(K_SIG)
        if stored_sig == signature:
            st.caption("Showing the forecast for exactly these inputs.")
        elif stored_sig is not None:
            st.caption("The inputs have changed since the last forecast — press "
                       "**Market Pulse** to request one for the current profile.")
        else:
            st.caption("Press **Market Pulse** to request the forecast for this profile.")

    if run:
        _fetch(area, inputs, signature)

    # ── STALE PROTECTION ────────────────────────────────────────────────────
    # A result is drawn only when the signature that produced it still matches
    # the area and inputs on screen. Area A's forecast can never be shown while
    # Area B is selected.
    error = st.session_state.get(K_ERROR)
    if error and error.get("sig") == signature:
        _render_error(error, area)
        return

    result = st.session_state.get(K_RESULT)
    if result is None or st.session_state.get(K_SIG) != signature:
        if result is not None:
            st.info("The forecast below was requested for a different set of inputs, so it "
                    "is held back until you press **Market Pulse** again.", icon="🔄")
        return

    _render_result(result, area, inputs, df_area, dark)


# ─────────────────────────────────────────────────────────────────────────────
# PIECES
# ─────────────────────────────────────────────────────────────────────────────


def _read_only_area(area: str, cfg) -> None:
    """
    The area, shown and disabled.

    This is deliberately a disabled control rather than a second selector: it
    displays the one global value and cannot change it.
    """
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.selectbox(
            "📍  Area — set under 📍 Area, shown here read-only",
            [area], index=0, disabled=True, key="dxb_fc_area_readonly",
            help="The forecast always follows the global Area. To change it, use "
                 "📍 Area — there is no second area control anywhere in this section.")
    with right:
        st.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
        if area == C.ALL_AREAS:
            st.caption("Choose a single area under 📍 **Area** to enable the forecast.")
        elif cfg is not None and cfg.exact:
            st.caption(f"**{area}** is listed in `input_ranges.csv`, so the options below "
                       f"are that area's own recorded values.")
        else:
            st.caption(f"**{area}** — options below come from the published ranges.")


def _profile_controls(cfg, current: dict) -> dict:
    """
    "Refine area profile".

    No widget carries a `key`, and every one is given an explicit `index` /
    `value` from the revalidated state. That is what makes an area change safe:
    the control is rebuilt from values already proven valid for the new area,
    so a stale selection cannot survive into a request.
    """
    st.markdown("")
    ui.block("Refine area profile",
             "Only values recorded for this area are offered. Leave anything as "
             "*Any* and the model uses this area's own typical value.", "🎛️")

    out: dict = {}

    row1 = st.columns(4, gap="medium")

    with row1[0]:
        opts = cfg.options("rooms_en") or [fapi.ANY]
        val = current.get("rooms_en", cfg.default("rooms_en"))
        out["rooms_en"] = st.selectbox(
            "Rooms", opts, index=opts.index(val) if val in opts else 0,
            help="Bedroom configuration. Sent as `rooms_en`.")

    with row1[1]:
        opts = cfg.options("floor_bin") or [fapi.ANY]
        val = current.get("floor_bin", cfg.default("floor_bin"))
        out["floor_bin"] = st.selectbox(
            "Floor", opts, index=opts.index(val) if val in opts else 0,
            help="Floor band. Sent as `floor_bin`.")

    with row1[2]:
        opts = cfg.options("reg_type_en") or [fapi.ANY]
        val = current.get("reg_type_en", cfg.default("reg_type_en"))
        out["reg_type_en"] = st.selectbox(
            "Registration type", opts, index=opts.index(val) if val in opts else 0,
            help="Off-plan or existing. Sent as `reg_type_en`.")

    with row1[3]:
        lo = float(cfg.size_min if cfg.size_min is not None else 25.0)
        hi = float(cfg.size_max if cfg.size_max is not None else 1000.0)
        val = float(current.get("procedure_area", cfg.size_default()))
        val = min(max(val, lo), hi)
        out["procedure_area"] = st.number_input(
            "Unit size (m²)", min_value=lo, max_value=hi, value=val, step=5.0,
            help=f"Sent as `procedure_area`, in square metres. This area's recorded range "
                 f"is {lo:,.1f} – {hi:,.1f} m²; the API clamps anything outside it.")

    row2 = st.columns(3, gap="medium")
    for col, param, label in zip(
            row2,
            ("Grade", "project_grade", "Developer_grade"),
            ("Building grade", "Project grade", "Developer grade")):
        with col:
            opts = cfg.options(param) or [fapi.ANY]
            val = current.get(param, cfg.default(param))
            out[param] = st.selectbox(
                label, opts, index=opts.index(val) if val in opts else 0,
                help=f"Sent as `{param}`.")

    row3 = st.columns(5, gap="medium")
    for col, param, label in zip(
            row3, fapi.FLAG_PARAMS,
            ("Parking", "Pool", "Balcony", "Elevators", "Metro")):
        with col:
            opts = [fapi.ANY] + cfg.options(param)
            val = current.get(param, fapi.ANY)
            help_text = f"Sent as `{param}`. *Any* omits it and the model uses this " \
                        f"area's typical value."
            if param == "elevators":
                help_text += (" The values offered are the elevator **counts** recorded for "
                              "this area in `input_ranges.csv`.")
            out[param] = st.selectbox(
                label, opts, index=opts.index(val) if val in opts else 0,
                format_func=lambda v, p=param: _flag_label(p, v), help=help_text)

    # This toggle does two jobs, and both matter. It is sent as `news_available`
    # so the API is not asked for news when it is off, AND it is read at render
    # time, so switching it off removes the red line, its legend entry and the
    # narrative immediately — without waiting for another request — and the PDF
    # follows the same state.
    out["news_available"] = st.toggle(
        "Include the news-adjusted forecast and market narrative",
        value=bool(current.get("news_available", True)),
        help="On: the news-adjusted forecast and the market narrative are shown and "
             "included in the report. Off: both are removed from the chart, the legend "
             "and the report.")

    return out


def _fetch(area: str, inputs: dict, signature: tuple) -> None:
    _clear_result()
    try:
        with st.spinner(f"Requesting the {area} forecast…"):
            data = fapi.fetch(area, inputs)
        st.session_state[K_RESULT] = fapi.parse(data)
        st.session_state[K_SIG] = signature
    except fapi.ForecastAreaUnsupported as exc:
        st.session_state[K_ERROR] = {"sig": signature, "kind": "area", "msg": str(exc)}
    except fapi.ForecastUnreachable as exc:
        st.session_state[K_ERROR] = {"sig": signature, "kind": "network", "msg": str(exc)}
    except fapi.ForecastBadResponse as exc:
        st.session_state[K_ERROR] = {"sig": signature, "kind": "shape", "msg": str(exc)}
    except fapi.ForecastError as exc:  # pragma: no cover
        st.session_state[K_ERROR] = {"sig": signature, "kind": "other", "msg": str(exc)}


def _render_error(error: dict, area: str) -> None:
    kind, msg = error.get("kind"), error.get("msg", "")
    if kind == "area":
        st.warning(
            f"**{msg}**\n\nThe forecast model does not cover **{area}**. The rest of this "
            f"page — every figure, chart and the PDF report — is unaffected and still "
            f"describes {area}. Choose another area under 📍 **Area** to forecast it.",
            icon="📍")
    elif kind == "network":
        st.error(
            f"**The forecast service could not be reached.**\n\n`{msg}`\n\n"
            f"The request was not answered, so there is nothing to show — no figure is "
            f"estimated or carried over from a previous request. Check that "
            f"`{fapi.BASE_URL}` is reachable from this machine, then press "
            f"**Market Pulse** again.", icon="🔌")
    elif kind == "shape":
        st.error(
            f"**The forecast service answered, but not in the documented format.**\n\n"
            f"`{msg}`\n\nNothing is inferred from a response that cannot be read.",
            icon="⚠️")
    else:
        st.error(f"**The forecast request failed.**\n\n`{msg}`", icon="⚠️")


def _render_result(result, area: str, inputs: dict, df_area, dark: bool) -> None:
    now_ts = result.now_timestamp
    horizon = result.horizon_months
    # The toggle as it stands right now — the source of truth for what is
    # drawn and for what goes into the report.
    show_news = bool(inputs.get("news_available", True))

    # ── headline figures ────────────────────────────────────────────────────
    cards = []
    if result.now_value is not None:
        cards.append(dict(label=f"Valuation point · {pd.Timestamp(now_ts):%b %Y}",
                          value=f"AED {result.now_value:,.0f}/m²", icon="📍", color="blue"))
    if not result.macro.empty:
        last = result.macro.iloc[-1]
        cards.append(dict(label=f"Macro forecast · {pd.Timestamp(last['timestamp']):%b %Y}",
                          value=f"AED {float(last['value']):,.0f}/m²",
                          icon="📈", color="green"))
    if show_news and result.has_news:
        lastn = result.news.iloc[-1]
        cards.append(dict(label=f"News-adjusted · {pd.Timestamp(lastn['timestamp']):%b %Y}",
                          value=f"AED {float(lastn['value']):,.0f}/m²",
                          icon="📰", color="amber"))
    cards.append(dict(label="Forecast months returned", value=f"{horizon}",
                      icon="🗓️", color="violet"))
    ui.kpi_grid(cards, per_row=4)

    # ── narrative ───────────────────────────────────────────────────────────
    # The API writes this field in Markdown (**Baseline Trend**: …). Streamlit
    # does not render Markdown inside an unsafe_allow_html block, so the text
    # goes through st.markdown on its own — otherwise the bold markers show up
    # as literal asterisks. The wording itself is untouched.
    if result.narrative and show_news:
        with st.container(border=True):
            st.markdown("#### 🧠  Market context")
            st.markdown(_narrative_md(result.narrative))
    elif show_news and not result.news_available:
        st.caption("The API reports that no matched news data was available for this area "
                   "on this request, so it returned the macro forecast on its own.")

    # ── chart ───────────────────────────────────────────────────────────────
    head, ctrl = st.columns([3, 2], vertical_alignment="bottom")
    with head:
        ci.header("api_forecast")
    with ctrl:
        window = st.radio("Historical window", list(WINDOWS), index=0, horizontal=True,
                          key="dxb_fc_window", label_visibility="visible",
                          help="How much recorded market history to show behind the "
                               "forecast. It changes the history shown, not the forecast — "
                               "the projection is exactly as long as the API's response.")
    api_first = (result.history["timestamp"].min() if not result.history.empty else None)
    start = _window_start(now_ts, WINDOWS[window], api_first=api_first)
    fig = ch.api_forecast_chart(result, dark=dark, window_start=start,
                                show_news=show_news)
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG,
                    key="dxb_fc_chart")

    hist_months = len(result.history)
    shown = len(result.history[result.history["timestamp"] >= start]) if start is not None \
        else hist_months
    st.caption(
        f"**Reading the chart.** *Model history* and both forecast lines are the API's own "
        f"values — history arrives already smoothed by the API and is not smoothed again "
        f"here. *Recorded market history* is a separate series: the median rate per m² "
        f"across all recorded transactions in {area}, from the cleaned dataset. The "
        f"vertical marker sits on the valuation point the API returned. The **{window}** "
        f"window shows **{shown} of the {hist_months} history months** the response "
        f"carries; it does not change the forecast, which runs **{horizon} month(s)** — "
        f"exactly the horizon the response contains."
    )

    if show_news and result.has_news:
        st.caption(
            "The shaded region is the distance between the macro and news-adjusted "
            "trajectories. Both are returned by the API; the region is the gap between "
            "them, and is not a confidence interval — the response does not include one, "
            "so none is drawn.")

    # ── the months ──────────────────────────────────────────────────────────
    table = result.table(include_news=show_news)
    if not table.empty:
        with st.expander("📋  The forecast month by month", expanded=False):
            fmt = {c: "{:,.0f}" for c in table.columns
                   if c != "Month" and not c.endswith("%")}
            fmt.update({c: "{:+.1f}%" for c in table.columns if c.endswith("%")})
            st.dataframe(table.style.format(fmt), use_container_width=True,
                         hide_index=True)
            st.caption(f"{len(table)} month(s) — every row is a value the API returned. "
                       f"All figures are AED per m² except **Difference %**.")

    # The forecast is NOT downloadable from this page. 📄 Download Detailed
    # Report is the one place reports are produced, and it packages this exact
    # result — so there is a single, predictable route to every document rather
    # than a download button on each page that produces one.
    st.caption("To download this forecast — on its own or combined with the area "
               "analysis — use 📄 **Download Detailed Report** in the rail.")

    with st.expander("🔎  The exact request that produced this"):
        st.caption("Open this URL in a browser and you get the same numbers back — it is "
                   "the request the figures above came from.")
        st.code(result.request_url or "—", language="text")


