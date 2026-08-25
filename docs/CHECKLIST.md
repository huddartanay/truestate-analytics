# Development Checklist — local build v1.1.0

Status: **complete and ready for company review. Not deployed.**

---

## Architecture

Three environments behind one shell:

```
                        TruEstates analytics
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ↓                           ↓                           ↓
   🇦🇪 ABU DHABI               🇦🇪 DUBAI              🧪 EXPERIMENTAL
   existing dashboard        NEW regional dashboard   existing experiments
   (embedded, untouched)     (platform-authored)      (embedded, untouched)
        │                           │                           │
   12 analytical tabs        Executive KPIs              V1 · V2 · V2.1
                             Smart Business Insights     FC · Area Combination
                             Market Snapshot             V2.2
                             ───────────────
                             Insights   Trends
                             Geography  Property
                             Price      Distribution
```

**Final folder structure**

```
uae-real-estate-analytics/
├── streamlit_app.py              ← THE entry point
├── requirements.txt · README.md · .streamlit/config.toml
│
├── platform_core/                the shell (no analytics)
│   ├── config.py                 branding · routes · section & experiment model
│   ├── design_system.py          tokens · CSS · animations · shell lock
│   ├── chart_theme.py            Abu Dhabi palette, restated for platform charts
│   ├── navigation.py             sidebar rail · routing state
│   ├── components.py             hero · cards · KPI grid · insights · map
│   ├── region_bridge.py          compatibility shims used BY the embedded apps
│   └── runtime.py                safe execution of an embedded app
│
├── platform_pages/
│   ├── overview.py · explore.py · about.py
│   ├── region_abu_dhabi.py       banner → runs the AD dashboard
│   ├── region_dubai.py           banner → renders the Dubai dashboard
│   └── region_experimental.py    banner → runs the experiments
│
├── regions/
│   ├── abu_dhabi/                PRESERVED (16 files)
│   ├── dubai_market/             NEW — data · metrics · charts · dashboard
│   └── dubai/                    PRESERVED (139 files) — the experiments
│
├── data/dubai/                   raw + cleaned parquet + provenance.json
├── tools/build_dubai_provenance.py
└── docs/                         ARCHITECTURE · INTEGRATION_CHANGES · CHECKLIST
```

**Entry point** — `streamlit run streamlit_app.py`; the only `st.set_page_config()` in the repository.

**Navigation** — one rail: Overview → LOCATIONS (Abu Dhabi, Dubai, Experimental Analysis + its six generations, expanded only while it is active) → PLATFORM (Explore, About) → appearance. Each environment's own controls render below a labelled divider.

**Isolation** — routing state `uae.*`; Dubai filters `dxb_*`; Abu Dhabi and the experiments keep their original keys. Each embedded app runs from its own working directory under a lock, with `sys.path` restored and all exceptions caught into an error card.

---

## Files

**Added (v1.1)** — `regions/dubai_market/` (4 modules), `platform_core/chart_theme.py`, `platform_pages/region_experimental.py`, `data/dubai/` (2 parquet + provenance), `tools/build_dubai_provenance.py`, `tests/verify_dubai_numbers.py`.

**Modified** — 2 existing files, **10 edits**, all chrome-only, all in `INTEGRATION_CHANGES.md`:

| File | Edits |
|---|---|
| `regions/abu_dhabi/app.py` | AD-1 bridge import · AD-2 page config · AD-3 sidebar logo · AD-4 theme toggle |
| `regions/dubai/trial.py` | DXB-1 bridge import · DXB-2 page config · DXB-3 experiment selection · DXB-4 sidebar titles (×3) · DXB-5 hide Data Summary (×2) |

**Preserved** — everything else. All Abu Dhabi modules; all 139 experiment files including every CSV, XLSX, PKL, PNG, HTML, parquet, `FC_st.py`, `testing.py` and both notebooks. Both supplied Dubai parquet files copied in byte-for-byte and never written to.

**Removed** — nothing beyond the two root `runpy` shims, `__pycache__/` and `.devcontainer/` noted in v1.0.

---

## Dependencies

`pyarrow>=14` was already in the unified requirements (the experiments carry a parquet asset) and now also serves the Dubai datasets — **no new dependency was needed for v1.1**.

Verified working set: Python 3.11.15 · streamlit 1.61.1 · pandas 2.3.3 · numpy 2.4.4 · plotly 6.9.0 · scikit-learn 1.8.0 · pyarrow.

---

## The Dubai datasets

| | `transactions.parquet` (RAW) | `latest_combined_data.parquet` (CLEANED) |
|---|---|---|
| Rows | 1,762,262 | 818,838 |
| Columns | 47 | 85 |
| Range | 1966 → 2026 | 2010 → 2026 |
| Areas | 258 | 69 |
| Scope | Sales + Mortgages + Gifts; Unit, Villa, Land, Building | Sales · Unit · Residential only |

The cleaned file is the residential-unit sales slice of the registry (88.2% of the 928,489 such rows), plus 38 engineered columns. **It powers every Dubai section** — it is the only one with amenity flags, locality zones and quality tiers, and it is already a single comparable segment. The raw file is retained and compared against it in the *Where this data comes from* panel; that comparison is precomputed into `provenance.json`, so the 81 MB raw file is never read to draw a page.

34 of the 85 columns are loaded and downcast — 1.26 GB → **55 MB**, cached once per process. Row count and every value are unchanged.

**Fields deliberately not used:** `floor_bin` (only `Unknown`/null), `Price/sqft (AED)` (21% populated), raw `elevators` (48% populated — the complete binary `elevator` flag is used instead), Arabic mirror columns.

---

## The API endpoint

**There is no HTTP API in the supplied Dubai codebase.** Every `.py` was searched for `http`, `requests`, `urllib`, `httpx`, `socket`. The only external URL is `https://flipose-re-price-prediction.streamlit.app/`, used twice with `st.link_button` — a link to a deployed app, not a callable endpoint.

No endpoint was invented. The Dubai **Price → Published price forecast** section instead reads the forecast artefacts the modelling pipeline already produced: `arima_forecast_quarterly_all_areas.csv` (fit + forecast + confidence band), `quarterly_forecasts_with_CI.csv` (forward quarters and growth factors), `metrics_lowess_all_areas1.csv` (test MAPE/MAE and SARIMA orders). Nothing is refitted at runtime.

**If a real prediction API exists elsewhere, say so** — the loader is isolated in one function (`regions/dubai_market/data.py::load_forecast_artifacts`) and can be swapped without touching any section.

---

## Functionality

**Abu Dhabi — working, unchanged.** All 12 tabs, both dataset scopes, all filters, 25 charts, KPI band, download centre, light and dark.

**Dubai — working.** Executive KPIs (12), Smart Business Insights (8, all data-derived), Market Snapshot (6), then Insights, Trends, Geography, Property, Price and Distribution — 31 charts and 11 tables, plus 7 sidebar filters.

**Experimental Analysis — working, unchanged.** All 6 generations and their 24 views. `Data Summary` is not present anywhere in the interface.

---

## Testing

**Startup** — clean boot, health 200, no exceptions on any route.

**Navigation** — every route driven in a real browser: Overview, Explore, About, Abu Dhabi, Dubai (all six tabs), Experimental (all six generations), appearance toggle, and the deep links from the Overview cards and the Explore directory.

**Strict visibility rule — verified.**

| Environment | Shows | Confirmed absent |
|---|---|---|
| 🇦🇪 Abu Dhabi | its own 12 tabs | — |
| 🇦🇪 Dubai | KPIs, Smart Insights, Snapshot, 6 sections | any V1–V2.2 experiment |
| 🧪 Experimental | V1, V2, V2.1, FC, Area Combination, V2.2 | Dubai KPIs / Insights / Snapshot / Insights / Trends / Geography / Property / Price / Distribution **and Data Summary** |

Data Summary absence is asserted programmatically across all six generations, not just eyeballed.

**Regression — ORIGINAL vs UNIFIED: 27 / 27 identical.**

Both the original standalone apps and the unified platform were executed for every view and compared on every `st.metric` value, every dataframe's shape and content hash, and every Plotly figure's per-trace data hash.

```
── ABU DHABI ───────────────────────────────────────────
  [PASS] scope = All Properties                m= 14 df= 2 fig=25
  [PASS] scope = Residential Apartments Only   m= 13 df= 2 fig=25
── EXPERIMENTAL ANALYSIS (vs the original Dubai app) ───
  [PASS] V1  · 5 views      [PASS] V2  · 4 views
  [PASS] V2.1· 5 views      [PASS] FC  · 2 views
  [PASS] area_combination · 8 proxy datasets
  [PASS] V_2.2 · default
════════════════════════════════════════════════════════
  27/27 views identical to the original applications
```

One nuance, investigated rather than accepted: V2.1 → Data Understanding renders `df_train.sample(10)` and `df_forecast_raw.sample(10)` **without a random seed** (trial.py lines 1451, 1557). Running the *original* twice produces different values there too, so it is inherent non-determinism, not a regression. Those two previews are excluded and the exclusion is recorded in the harness.

**Dubai numbers — 31 / 31 verified.** `tests/verify_dubai_numbers.py` recomputes every headline figure straight from the parquet with plain pandas — no platform code in the path — and compares:

```
  row count · median & max sale price · median rate · active areas ·
  master projects · projects · developers · total market value ·
  median unit size · most active area (+count) · busiest year ·
  off-plan share · dominant layout · premium area (volume-guarded) ·
  median rate with/without each of the 5 amenities · filtered row count
  ───────────────────────────────────────────────────────────────────
  31/31 checks passed
```

**Performance**

| Action | Time |
|---|---|
| Overview / Explore / About | < 0.5 s (environments are imported lazily) |
| Dubai, first load | ~8 s (parquet read + all six sections) |
| Dubai, rerun | ~4.6 s full dataset · ~2.5 s filtered |
| Abu Dhabi, first load | ~45 s (20 MB CSV), ~1–2 s thereafter |
| Experimental, per generation | 0.3 – 4 s |

Two optimisations were applied while building the Dubai page, both purely presentational: histograms are binned in numpy instead of shipping 800k raw values per chart to the browser (13 MB → 30 KB), and box plots are drawn from quartiles computed in pandas. The drawn statistics are identical either way.

---

## UI

**Sidebar** — one rail, dark navy in both themes. Brand, grouped sections, active state with cyan inset bar and slide-in transition, hover lift, visible focus rings, experiment generations indented one level, environment controls under a labelled divider, version footer pinned beneath them.

**Dubai matches Abu Dhabi by construction** — same KPI card language (accent bar, icon chip, uppercase label, 800-weight value), same section-header pattern, same insight-row pattern, same chart palette and Plotly layout (`platform_core/chart_theme.py` restates the Abu Dhabi values), same tab convention. Different numbers, same product.

**Comprehension** — breadcrumb on every page; persistent region banner with context chips; *"What am I looking at?"* on both regional dashboards defining rate per m² and median; a one-line plain-English reading under every Dubai chart; a *Where this data comes from* panel; an experiment explainer card plus a table of how the six generations relate; a research-environment warning so experimental figures are never mistaken for the current market.

**Animations** — staggered fade-up on cards and KPIs, hover lift, slide-in on the active nav item, arrow travel on CTAs, row nudge on directory rows, growing connector on the platform tree. CSS-only, all under 550 ms, all disabled under `prefers-reduced-motion`.

**Responsive** — verified at 1600 px and 900 px; fluid display type, auto-fit grids, padding steps at 1180 px and 820 px, charts and tables constrained to their container.

---

## Known issues

1. **Amenity gaps are composition, not causation — and the platform says so.** *Revised in v1.2.* The headline comparison shows parking **+117.1%** and balcony **−30.4%** across the full cleaned dataset. Held inside a single **area × layout × year × registration type** cell those become **+5.2%** and **−2.1%**, and three of the five amenities change sign. Registration type is the driver: building attributes are recorded for 88.8% of existing-property sales but only 32.9% of off-plan sales, and off-plan trades at 17,879 AED/m² against 11,264 — so "no balcony recorded" is largely a proxy for "off-plan". Inside existing property the balcony gap is **+16.5%**; inside off-plan it is **−20.5%**. Headline and like-for-like are now shown side by side with a composition explorer, and the like-for-like figure is the one to quote. Still associative: the cells control for four characteristics, not for floor, view, finish or developer. Appendix A of the chart reference guide sets this out in full.

2. **Pre-existing defect in the experiments — the interactive prediction console is unreachable.** `regions/dubai/trial.py` has two `if sidebar_option == "🤖 Model Input / Prediction":` blocks. The first (line 3588) renders a link. The second (line 3985) holds the full interactive console but sits inside `if ohe is None or train_columns is None:` (line 3978), so it only runs when the encoder *fails* to load. Identical in the original. **Not fixed** — it is analytical code and repairing it is a behaviour change that needs your decision. One-line fix available.

3. **`Data Summary` code is retained, not deleted.** Hidden from the Experimental interface as requested; the blocks remain in `trial.py` and still render when that file is run standalone. Confirm before any deletion.

4. **Dark appearance is optimised for Abu Dhabi.** Abu Dhabi ships its own dark chart theme; the Dubai dashboard and the experiments get chrome and text restyled, but Plotly figures and Streamlit's canvas data grid keep their light rendering.

5. **The experiments have no data caching.** Inherited; the code mutates the frames it loads, so caching needs review before it is safe.

6. **Abu Dhabi's first load takes ~45 s** on a cold cache. Converting its CSV to Parquet would fix it but changes a data artefact.

7. **`FC_st.py` and `testing.py` are not wired into the navigation** — earlier standalone drafts of the FC and V2.1 blocks; nothing imports them. Preserved unmodified.

8. **`use_container_width` deprecation warnings** in the console, from both codebases and the shell. Harmless on Streamlit 1.61; worth a sweep before a future major upgrade.

9. **Repository size is now 447 MB** because the two Dubai parquet files (135 MB) ship with it. Fine locally; worth a decision before any git history is created.

10. **Concurrency** — embedded-app execution is serialised by a lock because the working directory is process-global. Fine for local review.

---

## Deployment

**Not performed, by instruction.** Nothing pushed, no Streamlit Cloud connection, no existing deployment touched, both original repositories untouched on disk.

---
---

# v1.2 — Dubai chart validation and documentation

Scope: the Dubai dashboard only. Nothing rebuilt, nothing redesigned outside it,
nothing deployed.

## The six requested items

| # | Item | Status |
|---|---|---|
| 1 | Year-over-year compares with the previous year | ✅ verified — chained, no gaps 2010–2026; 2026 partial-year artefact explained; negative years kept |
| 2 | Rate per m² by layout readable | ✅ rebuilt as small multiples; excluded layouts listed, not deleted |
| 3 | Price movement smoothed | ✅ 3-month centred rolling median as an optional view; actuals retained |
| 4 | Off-plan vs existing validated | ✅ classification checked on the raw registry; premium chart + table added |
| 5 | Amenities recalculated from raw | ✅ headline decomposed; like-for-like added; parking cross-checked on the registry |
| 6 | Price points validated and reconciled | ✅ exhaustive and mutually exclusive on all three views; filter effect explained |
| 7 | ⓘ on every Dubai chart, one component | ✅ `regions/dubai_market/chart_info.py` — 31 entries, one renderer |
| 8 | Company-facing DOCX | ✅ `docs/Dubai_Analytics_Chart_Reference_Guide.docx` — 53 pages, generated from the datasets |

## Tests

| Suite | Result |
|---|---|
| `python tests/regression.py all` (from `/mnt/user-data/working`) | **27 / 27** views identical to the original applications |
| `python tests/verify_dubai_numbers.py` | **31 / 31** headline figures recomputed and matched |
| `python tests/verify_dubai_changes.py` | **87 / 87** checks over the six reworked analyses |
| Dubai route, headless | 17 metrics · 19 dataframes · 32 figures · **0 exceptions** · 9.1 s cold / 5.6 s warm |
| Browser pass at 1600 px | all six charts, the smoothing selector, the ⓘ popovers, Plotly hover / zoom / reset / fullscreen, the forecast selector |

## What the validation found

**Year-over-year.** Arithmetically correct — each year against the one before,
no gaps. 2026's −52.9% volume bar is a calendar artefact: the data ends
2026-08-06, so eight months are being compared with twelve. Like-for-like over
the same eight months it is −23.8% volume and **+1.13%** rate. The chart now
carries that warning and three like-for-like metrics. The negative years
(2011 −24.9%, 2014, 2015 −26.2%, 2016, 2018 −30.4%, 2020 −14.0%) were each
traced to their own counts and medians, found genuine, and kept.

**Layouts.** All nine layouts were being drawn at one x-position, so the chart
was a single smear. Rebuilt as one panel per layout on a shared y-scale. The
caption claiming smaller units cost more per m² was tested and is false —
Studio 14,845 rising to 4 B/R 19,943 — so it was removed and replaced with what
the data shows. Layouts below 100 transactions are listed in a note, not
silently dropped.

**Monthly series.** The jaggedness is real: the thinnest month carries 814
transactions and the median month 2,437, so it is mix churn, not small-sample
noise. Smoothing was therefore added as a *view*, not a fix — a 3-month centred
rolling median, which cuts the standard deviation of month-on-month change from
7.6% to 4.4% without moving the level. The right-edge drop is the partial month
(Aug 2026: 2,157 deals against July's 10,825) and is now marked on the chart.

**Off-plan.** `reg_type_en` is a clean binary on the raw registry — exactly two
values, no nulls, no reclassification needed. Off-plan traded at a premium in
**17 of 17 years**, from +4.4% (2011) to +70.9% (2019), narrowing to +25.6% in
2026.

**Price bands.** Exhaustive and mutually exclusive on the cleaned dataset
(818,838), the raw residential-unit subset (928,489) and all raw sales
(1,349,853) — counts sum exactly to the row count in each, zero unassigned, zero
duplicate transaction identifiers. The empty `> 10M` band is the default price
slider (1st–99th percentile ≈ AED 8M), not the data; unfiltered there are 5,308
such sales.

## Known issues (v1.2)

11. **The like-for-like amenity figure needs a large selection.** Each cell must
    hold at least 30 transactions on each side. Under a narrow sidebar filter
    some amenities drop out of the comparison entirely; the chart says so rather
    than reporting a thin number.

12. **Only `has_parking` exists in the raw registry.** Pool, balcony, elevator
    and metro are engineered fields present only in the cleaned dataset, so they
    cannot be re-derived from the raw file. Parking was cross-checked against
    the registry and the direction holds. Stated in the guide and in the ⓘ text.

13. **A zero in an amenity flag means "not recorded", not "confirmed absent".**
    Missing values were not silently converted to "No"; the wording throughout
    says *recorded with* / *recorded without*.

---
---

# v1.2.1 — Readability of the amenity result and the ⓘ

Triggered by review feedback: the numbers were right, the explanation was not
reaching a non-technical reader.

| Item | Status |
|---|---|
| Explain the +102% on screen, not just in a warning | ✅ new ladder chart shows the gap collapsing under four controls |
| Say what the two groups actually are, in plain words | ✅ generated from the live selection, nothing hard-coded |
| Lead with the trustworthy number | ✅ fair comparison first, raw comparison last |
| Do not overstate — say when the raw number is fine | ✅ metro (−9.7% raw vs −8.1% fair) is called out as such |
| ⓘ readable without a data background | ✅ one-liner → step-by-step → glossary → technical detail |
| Every chart covered | ✅ 32 of 32, enforced by an import-time guard and by the test suite |

## Tests after v1.2.1

| Suite | Result |
|---|---|
| `python tests/regression.py all` | **27 / 27** — Abu Dhabi and Experimental unchanged |
| `python tests/verify_dubai_numbers.py` | **31 / 31** |
| `python tests/verify_dubai_changes.py` | **126 / 126** |
| Dubai route, headless | 19 metrics · 19 dataframes · 33 figures · **0 exceptions** · 15.4 s cold / 6.2 s warm |
| Amenity selector, all five values | no exception on any; the "barely moves" branch verified on metro, the sign-flip branch on the other four |

## What the ladder shows, per amenity

| Amenity | Raw | Fair | Movement |
|---|---|---|---|
| Parking | +117.1% | +5.2% | −111.9 pts |
| Balcony | −30.4% | −2.1% | +28.4 pts |
| Elevator | −13.7% | +6.1% | +19.9 pts |
| Swimming pool | −6.7% | +7.6% | +14.3 pts |
| Near a metro station | −10.0% | −8.2% | +1.8 pts — barely moves |

The last row matters: four of five amenity headlines are composition artefacts,
one is not. The dashboard distinguishes them rather than applying one blanket
caveat.

---
---

# v1.2.2 — The off-plan premium, explained

A reviewer asked why unbuilt property shows a premium when a finished home you
can walk through ought to be worth more. Testing the question found the same
class of defect the amenity chart had.

| Item | Status |
|---|---|
| Justify the off-plan premium against the dataset | ✅ it does not survive a like-for-like comparison |
| Explain it on screen, not in a caveat | ✅ new *Why off-plan looks more expensive* ladder panel |
| Verify the classification is not a data artefact | ✅ 84.3% of off-plan sales occur before completion, median 1.6 yrs before |
| Correct the documentation that implied otherwise | ✅ `offplan_vs_existing` limitations and client wording rewritten |
| Keep one method for both investigations | ✅ `paired_gap` now serves the amenity and off-plan ladders |

## The finding

| Comparison | Premium |
|---|---|
| Everything against everything | +58.7% |
| Same area and year | +37.3% |
| Same master development and year | +31.7% |
| Same project and year | −8.3% |
| **Same building and year** | **−1.5%** |

Pooled over 896 buildings / 298,269 deals (36% of the dataset): **−7.5%**,
off-plan dearer in only 30% of them.

Stock test: off-plan buyers transact in buildings worth **AED 19,468/m²**,
existing buyers in buildings worth **AED 12,472/m²** — **+56.1%** against a
headline of **+58.7%**. The stock difference accounts for effectively all of it.

## Tests after v1.2.2

| Suite | Result |
|---|---|
| `python tests/regression.py all` | **27 / 27** — Abu Dhabi and Experimental unchanged |
| `python tests/verify_dubai_numbers.py` | **31 / 31** |
| `python tests/verify_dubai_changes.py` | **139 / 139** |
| Dubai route, headless | 22 metrics · 21 dataframes · 34 figures · **0 exceptions** · 12.6 s cold / 7.0 s warm |

## Known issue added

14. **The same-building comparison is a smaller sample than the headline.** A
    building needs 30 off-plan and 30 existing sales in the same year to
    qualify, which leaves 83 building-years. The pooled-across-years figure
    (896 buildings, 298,269 deals) is shown beside it as a cross-check and
    points the same way. Buildings with both kinds of sale in one year also
    lean towards recently completed stock — stated on screen and in the guide.
