"""
🧪 Experimental Analysis — the research environment.

Hosts the existing Dubai version-based experiments (regions/dubai/trial.py)
unchanged. This is deliberately separate from the 🇦🇪 Dubai regional dashboard:
none of Dubai's Executive KPIs, Smart Business Insights, Market Snapshot,
Insights, Trends, Geography, Property, Price or Distribution appear here.

`Data Summary` is removed from this interface (see docs/INTEGRATION_CHANGES.md,
edit DXB-5). The underlying code is untouched — it is simply not reachable from
the UI any more.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav
from platform_core import runtime


def render() -> None:
    env = C.REGIONS[C.ROUTE_EXPERIMENTAL]
    exp = C.EXPERIMENT_BY_ID.get(nav.experiment_id(), C.EXPERIMENTS[0])

    ui.breadcrumb("TruEstates analytics", "Experimental Analysis", exp["short"])
    ui.region_header(
        env,
        chips=[f"{exp['icon']} {exp['label']}", "Original logic preserved"],
    )

    st.warning(
        "**Research environment.** These are the project's analytical experiments, kept "
        "exactly as they were built. Figures here come from earlier datasets and modelling "
        "runs and will not always agree with the Dubai regional dashboard — that is expected. "
        "For the current market view, use 🇦🇪 **Dubai**.",
        icon="🧪",
    )

    # Experiment explainer
    views = "".join(f'<span class="uae-rc-tag">{v}</span>' for v in exp["views"])
    st.markdown(
        " ".join(
            f"""
            <div class="uae-card uae-d1" style="animation:uae-fade-up .45s var(--uae-ease) both;
                 margin-bottom:1.15rem">
              <p class="uae-h3">{exp['icon']} {exp['label']}
                 <span class="uae-row-badge" style="--rc:{env['accent']}">{exp['short']}</span>
              </p>
              <p class="uae-sub" style="max-width:96ch">{exp['detail']}</p>
              <div class="uae-rc-tags" style="margin:.8rem 0 0 0">{views}</div>
            </div>
            """.split()
        ),
        unsafe_allow_html=True,
    )

    if exp["id"] == "v21":
        ui.note(
            "<b>Heads up:</b> this experiment loads large training files and 20 saved area "
            "models. The first view may take a few seconds.",
            icon="⏱️",
        )
    elif exp["id"] == "v22":
        ui.note(
            "This generation links to a separately deployed prediction app rather than an "
            "embedded model.",
            icon="🔗",
        )

    with st.expander("🧭  How the experiments relate to each other", expanded=False):
        rows = "\n".join(
            f"| {'**→ ' + e['label'] + '**' if e['id'] == exp['id'] else e['label']} "
            f"| {e['short']} | {e['blurb']} |"
            for e in C.EXPERIMENTS
        )
        st.markdown(
            "The Dubai analysis was built in generations, each re-examining the market with a "
            "different dataset or modelling approach. All of them are preserved:\n\n"
            "| Experiment | Generation | What it is |\n|---|---|---|\n" + rows +
            "\n\nSwitch between them from the sidebar. Each keeps its own views, controls and "
            "published results."
        )

    # ── the NEW experiment ───────────────────────────────────────────────────
    # It is a generation of its own, so selecting it renders its own view and
    # the six original generations are never touched: none of them gains,
    # loses or moves a single element because of this addition.
    if exp["id"] == "smoothing":
        _smoothing_experiment()
        ui.footer(C.PLATFORM_VERSION, f"Experimental Analysis · {exp['label']}")
        return

    # The experiment's own sidebar widgets appear below this divider.
    nav.region_controls_divider(f"Experiment · {exp['short']}")

    runtime.run_region(
        entry=C.EXPERIMENTAL_ENTRY,
        working_dir=C.EXPERIMENTAL_DIR,
        region_label="Experimental Analysis",
    )

    ui.footer(C.PLATFORM_VERSION, f"Experimental Analysis · {exp['label']}")


def _smoothing_experiment() -> None:
    """
    NEW experiment — LOWESS against exponential smoothing on the Dubai monthly
    rate series.

    Added to this environment rather than the Dubai dashboard because it is
    methodology research, not a client-facing metric. The live Dubai price
    chart already uses LOWESS; nothing here changes it.

    Both methods are fed ONE series from ONE call to `monthly_series` on ONE
    dataframe: same dataset, same monthly aggregation, same statistic, same
    period. The only difference between Version A and Version B is the
    smoother itself.
    """
    ui.section("Trend smoothing — LOWESS against exponential smoothing",
               "New experiment. Method comparison for the Dubai monthly rate series.", "📉")

    st.caption(
        "A new experiment, added alongside the existing generations. None of the original "
        "experimental content was modified, moved or renamed to make room for it — the six "
        "earlier generations render exactly as they always have."
    )

    try:
        from regions.dubai_market import charts as dch
        from regions.dubai_market import metrics as dmx
        from regions.dubai_market.data import load_market
    except Exception as exc:  # pragma: no cover
        st.error(f"Dubai market data could not be loaded for this experiment.\n\n{exc}",
                 icon="⚠️")
        return

    with st.spinner("Fitting both smoothers…"):
        df = load_market()
        frame, rep = dmx.smoothing_experiment(df, "median_rate")

    if not rep.get("ok"):
        st.info(rep.get("reason", "Not enough months to compare smoothing methods."),
                icon="ℹ️")
        return

    lo, es = rep["lowess"], rep["exponential"]

    st.markdown(
        f"**Common source series.** Median rate per m² per calendar month, "
        f"**{rep['months']} months** ({rep['period']}), from the cleaned Dubai dataset "
        f"(`latest_combined_data.parquet`, `year_month` × `meter_sale_price`). "
        f"Both versions below are fitted to this one series — the dataset, the aggregation, "
        f"the statistic and the period are identical, and only the smoother differs. "
        f"The unsmoothed series moves **{rep['actual_sd_pct']:.2f}%** month to month; the "
        f"thinnest month carries **{rep['thinnest_month']:,}** transactions."
    )

    view = st.radio("View", ["Both", "Version A — LOWESS",
                             "Version B — Exponential smoothing"],
                    horizontal=True, key="exp_smoothing_view")
    st.plotly_chart(dch.smoothing_experiment_chart(frame, rep, view, dark=nav.is_dark()),
                    use_container_width=True,
                    config={"displaylogo": False})

    st.markdown("#### Measured comparison")
    diag = pd.DataFrame([
        {"Criterion": "Local trend capture — how closely the trend tracks the months",
         "Version A · LOWESS": f"{lo['fidelity_median_dev_pct']:.2f}% median deviation",
         "Version B · Exponential": f"{es['fidelity_median_dev_pct']:.2f}% median deviation",
         "Better": "A" if lo["fidelity_median_dev_pct"] < es["fidelity_median_dev_pct"] else "B"},
        {"Criterion": "Smoothness — month-on-month movement of the trend itself",
         "Version A · LOWESS": f"{lo['smoothness_sd_pct']:.2f}%",
         "Version B · Exponential": f"{es['smoothness_sd_pct']:.2f}%",
         "Better": "A" if lo["smoothness_sd_pct"] < es["smoothness_sd_pct"] else "B"},
        {"Criterion": "Response to fluctuations — worst single-month departure",
         "Version A · LOWESS": f"{lo['max_dev_pct']:.1f}%",
         "Version B · Exponential": f"{es['max_dev_pct']:.1f}%",
         "Better": "A" if lo["max_dev_pct"] < es["max_dev_pct"] else "B"},
        {"Criterion": "Noise handling — trend shift when the most extreme month is removed",
         "Version A · LOWESS": f"{lo['outlier_shift_pct']:.2f}%",
         "Version B · Exponential": f"{es['outlier_shift_pct']:.2f}%",
         "Better": "A" if lo["outlier_shift_pct"] < es["outlier_shift_pct"] else "B"},
        {"Criterion": "Boundary behaviour — edge error ÷ interior error",
         "Version A · LOWESS": f"{lo['edge_vs_core']:.2f}×",
         "Version B · Exponential": f"{es['edge_vs_core']:.2f}×",
         "Better": "A" if lo["edge_vs_core"] < es["edge_vs_core"] else "B"},
        {"Criterion": "Responsiveness — months the trend trails a turning point",
         "Version A · LOWESS": f"{lo['lag_months']}",
         "Version B · Exponential": f"{es['lag_months']}",
         "Better": "A" if lo["lag_months"] <= es["lag_months"] else "B"},
        {"Criterion": "Computational cost on this series",
         "Version A · LOWESS": f"{lo['runtime_ms']:.1f} ms",
         "Version B · Exponential": f"{es['runtime_ms']:.1f} ms",
         "Better": "A" if lo["runtime_ms"] < es["runtime_ms"] else "B"},
    ])
    st.dataframe(diag, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(
            f"**Version A — LOWESS**\n\n"
            f"Locally weighted regression, `statsmodels` `lowess`, span "
            f"{lo['frac']:.2f} of the series (≈{lo['window_months']:.0f} months), "
            f"{lo['iterations']} robustifying iterations.\n\n"
            f"*Advantages.* Centred, so it uses the months on both sides of a point and "
            f"does not trail a turning point. Robustifying iterations limit the pull of an "
            f"unusual month. It is defined only over observed data, so it cannot "
            f"extrapolate.\n\n"
            f"*Limitations.* Both ends are fitted from fewer neighbours "
            f"({lo['edge_vs_core']:.2f}× the interior error here), and the span has to be "
            f"chosen rather than estimated.")
    with c2:
        st.markdown(
            f"**Version B — Exponential smoothing**\n\n"
            f"Holt linear trend, additive, no seasonality, `statsmodels` "
            f"`ExponentialSmoothing`, in-sample fitted values. Fitted α = "
            f"{es['alpha']:.3f}, β = {es['beta']:.3f}.\n\n"
            f"*Advantages.* Weights recent observations most heavily, so it reacts quickly "
            f"to a genuine change in level, and its parameters are estimated rather than "
            f"chosen. Cheap and incremental.\n\n"
            f"*Limitations.* One-sided — it only ever looks backwards, so it necessarily "
            f"trails every turning point, and it leaves more month-to-month movement in the "
            f"trend than LOWESS does here.")

    if abs(es["beta"]) < 1e-6:
        st.warning(
            f"**Finding worth recording.** The Holt fit drove its trend weight to "
            f"β = {es['beta']:.3f} — effectively zero. On this series Holt's method has "
            f"collapsed to simple exponential smoothing: the trend component contributes "
            f"nothing, and Version B is a backward-looking weighted average of past months.",
            icon="⚠️")

    better_both = (lo["smoothness_sd_pct"] < es["smoothness_sd_pct"]
                   and lo["fidelity_median_dev_pct"] < es["fidelity_median_dev_pct"])
    if better_both:
        st.success(
            f"**Recommendation for team review: Version A, LOWESS.** It is better on both "
            f"axes at once, which is unusual — a smoother normally buys calmness by drifting "
            f"away from the data. Here LOWESS is calmer "
            f"({lo['smoothness_sd_pct']:.2f}% against {es['smoothness_sd_pct']:.2f}%) *and* "
            f"closer to the observations ({lo['fidelity_median_dev_pct']:.2f}% against "
            f"{es['fidelity_median_dev_pct']:.2f}%). The reason is structural: LOWESS is "
            f"centred and can use the months on either side of a point, while exponential "
            f"smoothing only looks backwards and must trail. Version B's one advantage is "
            f"absorbing a single freak month "
            f"({es['outlier_shift_pct']:.2f}% against {lo['outlier_shift_pct']:.2f}%), which "
            f"matters less here because the thinnest month still carries "
            f"{rep['thinnest_month']:,} transactions — the jaggedness is real market "
            f"movement, not sampling noise.", icon="✅")
    else:
        st.info("**No clean winner on this series.** Neither version is better on both "
                "smoothness and fidelity, so the choice is a judgement about which matters "
                "more for the audience.", icon="ℹ️")

    st.caption(
        "**Both are smoothing methods, not forecasts.** Each line stops at the last observed "
        "month and neither predicts the next one. This comparison is research for method "
        "selection and changes no figure on the Dubai dashboard."
    )

    with st.expander("📊  Span scan behind the LOWESS parameter"):
        scan = pd.DataFrame(rep["frac_scan"])[
            ["frac", "months_in_window", "smoothness_sd_pct",
             "fidelity_median_dev_pct", "edge_vs_core"]]
        scan.columns = ["Span (fraction)", "≈ months in window", "Trend movement (sd %)",
                        "Distance from actual (%)", "Edge ÷ interior error"]
        st.dataframe(
            scan.style.format({"Span (fraction)": "{:.2f}", "≈ months in window": "{:.0f}",
                               "Trend movement (sd %)": "{:.2f}",
                               "Distance from actual (%)": "{:.2f}",
                               "Edge ÷ interior error": "{:.2f}"}),
            use_container_width=True, hide_index=True)
        st.caption("A wider span is always calmer and always further from the data. The span "
                   "in use is the narrowest that still reads as a trend rather than noise.")
