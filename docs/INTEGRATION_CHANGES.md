# Integration Changes — complete log

Every modification made to the two existing codebases, in full.

**Ten edits in total. Zero analytical changes.**

No data processing, cleaning, feature engineering, statistical calculation,
machine-learning calculation, model output, forecast, KPI, filter, chart or
table logic was altered. Every edit below replaces a Streamlit *chrome* call
with a call into `platform_core/region_bridge.py`, and every bridge function
falls back to the original behaviour when the region is run standalone.

Both regional apps therefore still run on their own, unchanged:

```bash
streamlit run regions/abu_dhabi/app.py
streamlit run regions/dubai/trial.py
```

---

## Abu Dhabi — `regions/abu_dhabi/app.py`

### AD-1 · bridge import (after the existing path setup, ~line 18)

Added — nothing removed.

```python
_PLATFORM_ROOT = BASE_DIR.parent.parent
if str(_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_ROOT))
from platform_core.region_bridge import (
    page_config as _platform_page_config,
    render_region_brand as _platform_region_brand,
    render_theme_toggle as _platform_theme_toggle,
)
```

**Why:** makes `region_bridge` importable in both execution modes.

### AD-2 · page configuration (was line 72)

```diff
-st.set_page_config(
+_platform_page_config(
     page_title="Abu Dhabi Real Estate Intelligence",
     page_icon="🏙️",
     layout="wide",
     initial_sidebar_state="expanded",
 )
```

**Why:** Streamlit allows one `set_page_config` per run and the platform owns it.
**Standalone:** identical to before — the bridge calls `st.set_page_config` verbatim.

### AD-3 · sidebar logo (was line 118)

```diff
-st.markdown(
-    '<div class="sidebar-logo">…</div>',
-    unsafe_allow_html=True,
-)
+_platform_region_brand('<div class="sidebar-logo">…</div>')
```

**Why:** the rail already carries the product brand; a second logo directly beneath it is confusing nested branding.
**Standalone:** the original markup renders unchanged.

### AD-4 · theme toggle (was lines 125–130)

```diff
-icon = "🌙 Dark Mode" if not DARK else "☀️ Light Mode"
-if st.button(icon, key="theme_toggle", use_container_width=True):
-    st.session_state.dark_mode = not st.session_state.dark_mode
-    st.rerun()
-st.markdown("---")
+_platform_theme_toggle(DARK)
```

**Why:** appearance becomes a single platform-level control. It writes the **same `dark_mode` session key**, so Abu Dhabi's existing dual-mode theme keeps working untouched.
**Standalone:** the original button, with the same key and the same behaviour.

---

## Dubai — `regions/dubai/trial.py`

### DXB-1 · bridge import (after the existing imports, ~line 13)

Added — nothing removed.

```python
import sys as _sys
from pathlib import Path as _Path
_PLATFORM_ROOT = _Path(__file__).resolve().parent.parent.parent
if str(_PLATFORM_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PLATFORM_ROOT))
from platform_core.region_bridge import (
    page_config as _platform_page_config,
    experiment_selection as _platform_experiment,
    experiment_views as _platform_views,
    render_region_sidebar_title as _platform_sidebar_title,
)
```

Aliased with leading underscores so the names cannot collide with any of the
~4,800 lines of analytical code below.

### DXB-2 · page configuration (was line 14)

```diff
-st.set_page_config(initial_sidebar_state="expanded", layout="wide", page_title="FlipOse-RE-Analytics")
+_platform_page_config(initial_sidebar_state="expanded", layout="wide", page_title="FlipOse-RE-Analytics")
```

### DXB-3 · experiment selection (was line 33) — **the key seam**

```diff
-page = st.sidebar.radio("Versions", ["V1", "V2","V2.1", "FC","area_combination","V_2.2"])
+page = _platform_experiment(["V1", "V2","V2.1", "FC","area_combination","V_2.2"])
```

**Why:** the raw version switch is replaced by named experiment generations in the global rail.

**Critical property:** the bridge returns **exactly the same six legacy strings**.
Every `if page == "V1"` / `elif page == "V2"` / … branch below is byte-for-byte
unchanged and receives exactly the value it always received. The bridge also
guards against an unknown value ever reaching the branches.

**Standalone:** the original `st.sidebar.radio("Versions", …)` renders.

### DXB-4 · region sidebar titles (lines 56, 933, 1342)

```diff
-st.sidebar.title("🔍 FlipOse-RE-Analytics-V1")
+_platform_sidebar_title("🔍 FlipOse-RE-Analytics-V1")  # DXB-4
```

(and the same for `-V2` and `-V2.1`)

**Why:** embedded, the rail already names the active workspace in plain language and shows its generation badge; repeating the raw version string one line below it is redundant navigation noise.
**Standalone:** the original `st.sidebar.title(...)` renders.

### DXB-5 · remove "Data Summary" from the Experimental interface (lines 95, 965)

```diff
-sidebar_option = st.sidebar.radio("Choose View", [
+sidebar_option = st.sidebar.radio("Choose View", _platform_views([
     "Data Summary",
     "Pareto Analysis",
     ...
-])
+]))
```

(the same change in the V2 block)

**Why:** requested — `Data Summary` should not appear as a button, radio option,
tab, selector or section inside Experimental Analysis.

**What was NOT done:** the underlying code was not deleted. Every
`if sidebar_option == "Data Summary":` block in `trial.py` is still present,
byte for byte; it is simply no longer reachable from the interface. The
bridge's `experiment_views()` filters the list against
`config.EXPERIMENT_HIDDEN_VIEWS`, and falls back to the unfiltered list if
filtering would leave no navigation at all.

**Standalone:** the original list is returned unchanged, so
`streamlit run regions/dubai/trial.py` still shows Data Summary exactly as before.

**Renamed in the same edit (DXB-1/DXB-3):** the bridge functions
`dubai_section` → `experiment_selection` and the new `experiment_views`, to
match the fact that `trial.py` is now the *Experimental Analysis* environment
rather than the Dubai region. No behavioural change — the same six legacy
strings are still returned.

---

## Files moved (path only — no content change)

| From | To |
|---|---|
| `abu-dhabi-real-estate-dashboard-main/abu dhabi dashboard/` | `regions/abu_dhabi/` |
| `adding_modified--main/` | `regions/dubai/` |

The Abu Dhabi folder was renamed to remove the spaces in `abu dhabi dashboard`.
Internal structure, filenames (including `Abu_Dhabi_Sales_Cleaned (1).csv`) and
all relative paths are unchanged.

## Files removed

| File | Reason |
|---|---|
| `abu-dhabi-real-estate-dashboard-main/app.py`, `streamlit_app.py` | Root-level `runpy` shims whose only job was to launch `abu dhabi dashboard/app.py`. Superseded by the platform entry point. The real application was **not** touched |
| `**/__pycache__/` | Compiled bytecode |
| `adding_modified--main/.devcontainer/` | Codespaces config that hard-codes `streamlit run trial.py` as the app entry point — wrong for the unified repo |

**Nothing else was deleted.** Every CSV, XLSX, PKL, PNG, HTML, parquet, notebook
and script from both projects is present, including `FC_st.py`, `testing.py`,
`Required updats/` and the empty `plots_for_streamlit/` directory.

## Files added

See `ARCHITECTURE.md §16`.

---

## Behavioural differences, stated plainly

| Behaviour | Original | Unified | Analytical impact |
|---|---|---|---|
| Page title / icon | Per app | One global | None |
| Dubai version switch | Sidebar radio | Named rail items | None — same six values reach the same branches |
| Abu Dhabi theme toggle | In its sidebar | In the platform rail, same session key | None |
| Abu Dhabi sidebar logo | Shown | Hidden when embedded | None |
| Dubai `FlipOse-…-Vx` sidebar titles | Shown | Hidden when embedded | None |
| Working directory | Repo root | The active region's own directory | None — this is what keeps the relative paths valid |
| Regional errors | Raw traceback | Error card + collapsible traceback | None |


---
---

# v1.1 additions

## New code (no existing file touched)

| Path | Purpose |
|---|---|
| `regions/dubai_market/` | The Dubai regional dashboard — `data.py`, `metrics.py`, `charts.py`, `dashboard.py` |
| `platform_core/chart_theme.py` | Restates the Abu Dhabi Plotly palette / layout so platform-drawn charts match |
| `platform_pages/region_experimental.py` | Hosts `regions/dubai/trial.py` under 🧪 Experimental Analysis |
| `data/dubai/*.parquet` | The supplied raw and cleaned Dubai datasets, copied in unmodified |
| `data/dubai/provenance.json` | Precomputed raw-vs-cleaned comparison |
| `tools/build_dubai_provenance.py` | Regenerates that JSON |
| `tests/verify_dubai_numbers.py` | Independently recomputes every Dubai headline figure from the parquet |

`platform_pages/region_dubai.py` was rewritten (it previously hosted the
experiments; it now hosts the regional dashboard). `platform_core/config.py`,
`navigation.py`, `components.py`, `design_system.py`, `overview.py`,
`explore.py`, `about.py` and `streamlit_app.py` were extended for the third
environment.

## Datasets

Both supplied parquet files were copied into `data/dubai/` **byte-for-byte**.
Neither is written to at any point. The dashboard reads a 34-column subset of
the cleaned file and narrows dtypes for memory; row count and every value are
unchanged (verified by `tests/verify_dubai_numbers.py`).

## Behavioural differences, stated plainly (v1.1)

| Behaviour | Before | Now | Analytical impact |
|---|---|---|---|
| 🇦🇪 Dubai in the rail | the experiments | the new regional dashboard | none — the experiments moved, they did not change |
| The experiments | under 🇦🇪 Dubai | under 🧪 Experimental Analysis | none |
| `Data Summary` in V1 / V2 | visible | hidden when embedded, code retained | none — every other view is byte-identical |
| Default V1 / V2 view | Data Summary | Pareto Analysis / Univariate Analysis | none — just the first remaining item |

---
---

# v1.2 — Dubai chart validation and documentation

An **edit / validation** pass over the Dubai dashboard only. No page was
rebuilt, no unrelated section was redesigned, and nothing was deployed.

`regions/abu_dhabi/**` and `regions/dubai/trial.py` were **not touched in this
pass** — the four and five documented edits from v1.0 / v1.1 remain the only
changes to those files, and `tests/regression.py all` still reports 27 of 27
views identical to the original applications.

## What each of the six charts was checked against, and what changed

| Chart | Verdict | Change made |
|---|---|---|
| Year-over-year growth | arithmetic correct | Added a partial-year warning and a like-for-like year-to-date panel. Negative years verified and **kept**. |
| Rate per m² by layout | unreadable | Rebuilt as small multiples — one panel per layout on a shared scale, with counts and a full quartile table. A false caption was removed. |
| How prices are moving | correct, jagged | Added a 3-month centred rolling median as an optional view. Actual monthly observations remain selectable and tabulated. |
| Off-plan vs existing | classification correct | Added an explicit premium/discount chart and per-year table so the gap is stated, not eyeballed. |
| Amenities vs price | **headline misleading** | Recalculated. Headline and like-for-like are now shown side by side, with a composition explorer and quoting rules. |
| Where the price points are | correct | Reconciled against the raw registry; an empty top band is now explained as a filter effect. |

## New files

| Path | Purpose |
|---|---|
| `regions/dubai_market/chart_info.py` | The single chart-documentation registry. Powers every ⓘ popover **and** the DOCX. |
| `tools/build_chart_reference_docx.py` | Computes every figure in the guide from the parquets, writes `build/chart_reference_payload.json`. |
| `tools/build_chart_reference_docx.js` | Renders that payload to `docs/Dubai_Analytics_Chart_Reference_Guide.docx`. |
| `tests/verify_dubai_changes.py` | 87 independent checks over the six reworked analyses. |
| `docs/Dubai_Analytics_Chart_Reference_Guide.docx` | The company-facing guide — 31 charts, 53 pages. |

## Changed files

| Path | Change |
|---|---|
| `regions/dubai_market/dashboard.py` | Every chart now calls `ci.header(<key>)`; smoothing selector; YoY validation panel; off-plan premium; amenity panels and composition explorer; price-band filter warning. |
| `regions/dubai_market/charts.py` | `rate_by_layout` rebuilt as small multiples; `price_rate_trend` gained smoothing and a partial-month marker; `offplan_premium` added. |
| `regions/dubai_market/metrics.py` | Added `amenity_effects_like_for_like`, `amenity_composition`, `price_bands`, `yoy_validation`, `offplan_premium_table`. Existing functions unchanged. |
| `platform_core/design_system.py` | Styling for the source badge and the ⓘ popover. Additive only. |

## The one analytical correction

The amenity headline figures describe two different groups of properties, not
the value of a feature. Held inside a single **area × layout × year ×
registration type** cell:

| Amenity | Headline | Same area, layout & year | …and same registration type |
|---|---|---|---|
| Parking | +117.1% | +21.1% | **+5.2%** |
| Swimming pool | −6.7% | −0.7% | **+7.6%** |
| Balcony | −30.4% | −15.6% | **−2.1%** |
| Elevator | −13.7% | −3.5% | **+6.1%** |
| Near a metro station | −10.0% | −12.1% | **−8.2%** |

Cause: building attributes are recorded for 88.8% of existing-property sales but
only 32.9% of off-plan sales, and off-plan trades at 17,879 AED/m² against
11,264. So "no balcony recorded" is largely a proxy for "off-plan". The balcony
gap is **+16.5% inside existing property and −20.5% inside off-plan** — a
reversal in both subgroups, which is a composition effect, not a property of
balconies.

Both figures are shown. The dashboard never says an amenity *causes* a price.

## Behavioural differences (v1.2)

| Behaviour | Before | Now | Analytical impact |
|---|---|---|---|
| Dubai chart headers | title + subtitle | title + source badge + ⓘ | none — presentation only |
| Layout rate chart | one stacked box plot | one panel per layout | none — same quartiles, drawn legibly |
| Price/rate trend | actual monthly only | Both / Smoothed / Actual | none — smoothing is an added view, never a replacement |
| Amenity chart | one headline chart | headline **and** like-for-like | the headline is unchanged; a corrected comparison sits beside it |
| Empty `> 10M` band | silent | explained as a filter effect | none |

---
---

# v1.2.1 — Making the amenity result and the ⓘ readable without a data background

Feedback after v1.2: the amenity charts were *correct* but did not explain
themselves — a reader still had to be told why parking showed +102% — and the
ⓘ popovers were written for an analyst, not for the person who has to present
the number.

## The amenity section was reordered and given a bridge chart

Before, the raw comparison came first and the fair one second, with a warning
between them. Now:

1. A lead-in that states the problem in one paragraph, using the concrete
   property mix rather than the phrase "composition effect".
2. **The fair comparison first** — it is the number to quote, so it leads.
3. **A new chart: “Why the raw amenity number is so much bigger.”** One bar per
   comparison, read top to bottom: everything-against-everything, then same
   area, then same area and layout, then same year, then same off-plan status.
   The gap visibly collapses. For parking: **+117.1% → +10.2% → +21.5% →
   +21.1% → +5.2%**.
4. **A generated plain-English description of the two groups**, written from the
   selection actually on screen — sizes, off-plan share, studio share and the
   busiest area on each side. Nothing in that paragraph is hard-coded.
5. **The raw comparison last**, labelled as shown for transparency, not for
   quoting.
6. The deep composition tables moved into a collapsed *full working* expander.

The section also states when an amenity is **not** distorted: for “near a metro
station” the raw figure is −9.7% and the fair one −8.1%, and the dashboard says
so rather than implying every raw number is wrong.

## The ⓘ was rewritten for a non-technical reader

`ChartInfo` gained three fields — `one_liner`, `steps` and `terms` — and the
popover was reordered to lead with them:

| Order | Before | Now |
|---|---|---|
| 1 | What is this? | **In one sentence** (plain, no jargon) |
| 2 | Why is it used? | What you are looking at |
| 3 | Where the numbers come from | Why it is here |
| 4 | Data preparation | **What happens inside this chart, step by step** |
| 5 | Calculation | How to read it · what it tells you · what it does not |
| 6 | Axes and legend | **Words used on this chart** (glossary, in plain English) |
| 7 | … | How to put it to a client |
| 8 | | — divider — **TECHNICAL DETAIL**: source, columns, preparation, calculation, axes, filters, limitations, validation |

A 28-entry `GLOSSARY` defines every non-everyday word once — median, rate per
m², off-plan, quartile, whisker, rolling median, MAPE and the rest. Each chart
lists only the terms it uses, so nobody reads a definition they do not need.
All **32 charts** carry a one-liner and step-by-step explanation; a module-level
guard raises at import time if one is missing.

## Files

| Path | Change |
|---|---|
| `regions/dubai_market/metrics.py` | Added `_like_for_like_one`, `CONTROL_LEVELS`, `amenity_control_ladder`, `amenity_plain_reason`. `amenity_effects_like_for_like` now delegates to the shared helper — same output. |
| `regions/dubai_market/charts.py` | Added `amenity_ladder`. |
| `regions/dubai_market/dashboard.py` | `_amenities_panel` reordered; new `_amenity_why` and `_amenity_group_story`; `_amenity_investigation` collapsed and now follows the selector above it. |
| `regions/dubai_market/chart_info.py` | New `one_liner` / `steps` / `terms` fields, the `GLOSSARY`, a rewritten `_render_body`, and a 32nd entry for the ladder chart. |
| `tools/build_chart_reference_docx.{py,js}` | The plain-English layer is carried into the Word guide, plus a new **Appendix F — every word, in plain English**. |
| `tests/verify_dubai_changes.py` | Extended to 126 checks: every ladder rung, the plain-language figures, and the completeness of the documentation registry. |

Nothing outside `regions/dubai_market/` and `tools/` changed. Abu Dhabi and the
Experimental environment are untouched — `tests/regression.py all` still reports
27 of 27 views identical.

---
---

# v1.2.2 — The off-plan premium, explained

Review question: *"practically thinking, the properties that are already built and
in front of the client's eyes should be worth more — justify the off-plan premium
against the dataset."*

The question was right, and testing it found that **the dashboard's off-plan
section had the same defect the amenity section had**: a correct number with a
misleading implication.

## What the data says

Tightening the comparison one step at a time, exactly as the amenity ladder does:

| Comparison | Premium | Matched groups | Transactions |
|---|---|---|---|
| Everything against everything | **+58.7%** | 1 | 818,838 |
| Same year | +40.7% | 17 | 818,838 |
| Same area and year | +37.3% | 402 | 710,314 |
| Same master development and year | +31.7% | 407 | 631,901 |
| Same project and year | **−8.3%** | 106 | 42,841 |
| Same building and year | **−1.5%** | 83 | 14,911 |

Pooled across all years, over **896 buildings and 298,269 transactions (36% of
the dataset)**, the same-building figure is **−7.5%**, and off-plan is dearer in
only **30%** of those buildings.

**The stock test settles it.** Value every building at its own median rate and
ask what the average building is worth on each side: off-plan buyers transact in
buildings worth **AED 19,468/m²**, existing buyers in buildings worth **AED
12,472/m²** — a gap of **+56.1%** against a headline premium of **+58.7%**. The
difference in stock alone accounts for effectively the whole premium.

The two sides are not the same product: off-plan is 29.8% Luxury and 7.9%
Ultra-Luxury against 13.0% and 2.3%; 4.0% Affordable against 29.0%; Grade A/A+/B
60.6% against 32.3%.

**The label itself is sound** — this is not a data error. On the 50.8% of rows
carrying a completion date, **84.3%** of off-plan sales happen before the
building is finished (median **1.6 years** before), while existing sales happen a
median **2.9 years** after. Off-plan really is unbuilt property.

**Conclusion: a finished apartment does hold its value against an unbuilt one.**
The premium is a statement about which buildings are sold off-plan, not about
buying before completion. The reviewer's intuition was correct.

## Changes

| Path | Change |
|---|---|
| `regions/dubai_market/metrics.py` | New `paired_gap` — one implementation now behind both the amenity and off-plan comparisons. `_like_for_like_one` is a thin wrapper over it, so the amenity figures are unchanged (asserted by test). New `OFFPLAN_LEVELS`, `offplan_control_ladder`, `offplan_composition`. |
| `regions/dubai_market/charts.py` | `amenity_ladder` renamed `control_ladder` — it now serves both sections, so the two make the same argument in the same shape. |
| `regions/dubai_market/dashboard.py` | New `_offplan_why` panel after the premium chart: the ladder, the stock test, the tier and grade mix, the completion-date validation and the wording rules. The old "a premium is not the same as being overpriced" note was replaced with a warning that points at it. |
| `regions/dubai_market/chart_info.py` | New 33rd entry `offplan_ladder`. The existing `offplan_vs_existing` entry was **corrected** — its limitations and client wording previously implied the premium was a real product premium. |
| `tools/build_dubai_provenance.py` | Records the completion-date timing evidence and the building-rate weighting, so the app can quote them without loading those columns at run time. |
| `tools/build_chart_reference_docx.{py,js}` | Appendix C rewritten: C.1 does the label mean what it says · C.2 why unbuilt looks dearer · C.3 the stock test · C.4 the two sides are not the same product · C.5 how to quote this. |
| `tests/verify_dubai_changes.py` | 139 checks — every ladder rung recomputed by hand, the stock test, the pooled cross-check, the completion-date evidence, and a guard that `paired_gap` reproduces the amenity figures exactly. |

Abu Dhabi and the Experimental environment remain untouched: **27 of 27**.
