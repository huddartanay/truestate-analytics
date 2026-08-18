# Architecture & Conflict Assessment

> **v1.1** — the platform now has **three** environments: Abu Dhabi, Dubai
> (a new regional dashboard) and Experimental Analysis (the existing
> version-based work). §17–§20 at the end cover the additions; §1–§16 are the
> original assessment and still hold.

Produced **before** any integration work, from a full read of both codebases.
This is the Phase-2 deliverable; Phase 3 onwards implements what is described here.

---

## 1. Abu Dhabi entry point

| | |
|---|---|
| Original repo | `abu-dhabi-real-estate-dashboard-main/` |
| Real application | `abu dhabi dashboard/app.py` (1,114 lines) |
| Root shims | `app.py` and `streamlit_app.py` at the repo root, both `runpy.run_path()` the real app |
| Structure | Genuinely modular — `config/`, `utils/`, `styles/`, `components/`, `charts/` |
| Data | `Abu_Dhabi_Sales_Cleaned (1).csv` (~20 MB, 109k rows) resolved via `Path(__file__).parent.parent / DATA_FILE` |
| Caching | `@st.cache_data` on `load_data`, `get_apartments_df`, `get_cleaned_apartments_df` |
| UI | Hero → 12 KPI cards → 12 tabs |

**Assessment:** clean, cache-aware, and path-safe. Preserve wholesale.

## 2. Dubai entry point

| | |
|---|---|
| Original repo | `adding_modified--main/` |
| Real application | `trial.py` (4,857 lines) — confirmed by `.devcontainer/devcontainer.json`, which runs `streamlit run trial.py` |
| Structure | Monolithic. Top-level `st.sidebar.radio("Versions", [...])` at line 33, then six top-level `if page == ...` blocks |
| Not entry points | `FC_st.py` (551 lines) and `testing.py` (727 lines) are earlier standalone drafts of the `FC` and `V2.1` blocks. **Nothing imports them.** Kept, not wired in |
| Data | ~130 assets in the repo root, all referenced by **bare relative filename** (`"target_df.csv"`, `"dt_model_Burj_Khalifa.pkl"`, …) |
| Caching | None. Every rerun re-reads from disk |

**Version blocks in `trial.py`:**

| Line | Branch | Presented in the platform as |
|---|---|---|
| 35 | `V1` | 📊 Market Data Explorer |
| 897 | `V2` | 🔎 Refined Market Analysis |
| 1321 | `V2.1` | 🤖 Modelling & Prediction Lab |
| 4269 | `FC` | 📈 Time-Series Forecasting |
| 4760 | `area_combination` | 📍 Area Proxy Map |
| 4852 | `V_2.2` | 🔮 Price Predictor (external link) |

**Assessment:** the branching is the only structural seam. Take it; leave the 4,800 lines inside the branches alone.

## 3. Shared dependencies

`streamlit`, `pandas`, `numpy`, `plotly`, `statsmodels`, `openpyxl` — required by both, no version disagreement beyond the minimums.

## 4. Conflicting dependencies

| Package | Abu Dhabi | Dubai | Resolution |
|---|---|---|---|
| `streamlit` | `>=1.35.0` | `>=1.40.0` | `>=1.45` — highest wins, and the shell's keyed-container navigation styling needs it |
| `pandas` | `>=2.0.0` | unpinned | `>=2.0,<3` — both codebases are written against the pandas 2.x API; the ceiling is a compatibility guard, not an analytical change |

**Undeclared imports found by tracing** (both were latent bugs in the originals, fixed in the unified requirements):

- `scipy` — used in `abu_dhabi/charts/plotly_charts.py` (`stats`, `gaussian_kde`), absent from the Abu Dhabi requirements.
- `pillow` — used in `dubai/trial.py` (`PIL.Image`, correlation views), absent from the Dubai requirements.

**Declared but unused:** `matplotlib`, `seaborn`, `mlxtend` appear in the Dubai requirements but are imported by no runtime `.py`. `matplotlib` and `seaborn` are retained (notebook environment); `mlxtend` is retained as an optional comment rather than silently dropped.

## 5. Streamlit configuration conflicts

Neither project shipped a `.streamlit/config.toml`. The platform adds one and owns it.

## 6. `st.set_page_config` conflicts

Two competing calls:

- `abu_dhabi/app.py:72` → title "Abu Dhabi Real Estate Intelligence", icon 🏙️
- `dubai/trial.py:14` → title "FlipOse-RE-Analytics"

Streamlit permits exactly one per script run. **Resolution:** the platform owns the single call; both regional calls are routed through `region_bridge.page_config()`, which no-ops when embedded and behaves exactly as before when the region is run standalone.

## 7. Sidebar / navigation conflicts

Three competing navigations existed:

1. Dubai's top-level `Versions` radio (raw `V1 / V2 / V2.1 / FC / area_combination / V_2.2`).
2. Dubai's per-version `Choose View` / `Choose Section` radios.
3. Abu Dhabi's filter stack plus its own sidebar logo and theme toggle.

**Resolution:** one global rail at the top (brand → Overview → Locations → Platform → appearance). Dubai's version radio is replaced by the rail's Dubai sub-items. Everything else the regions put in the sidebar is preserved and appears below a **Region controls** divider, so it reads as a second level of one hierarchy rather than a competing menu.

## 8. Session-state conflicts

Surprisingly few keys in play:

| Key | Owner | Handling |
|---|---|---|
| `dark_mode` | Abu Dhabi | **Deliberately shared.** The platform's appearance toggle writes the same key, so Abu Dhabi's existing dark theme keeps working and the shell follows it |
| `area_models`, `ohe` | Dubai (`trial.py:2660`) | Untouched — no collision |
| `theme_toggle`, widget keys | Abu Dhabi | Untouched |
| `uae.route`, `uae.dubai_section` | Platform (new) | Namespaced `uae.` — cannot collide with anything in either region |

No renaming was necessary; namespacing the new keys was sufficient.

## 9. CSS conflicts

Both regions inject full-page stylesheets:

- `abu_dhabi/styles/theme.py` — 961 lines, dual light/dark, styles `[data-testid="stSidebar"]` with `!important`, hides `header`/`footer`/`#MainMenu`.
- `dubai/trial.py:18` and `:901` — small blocks repositioning the collapse control and adjusting `.block-container` padding.

Because regions run *after* the shell, their rules would otherwise win on ordering. **Resolution:** two-part strategy —
1. every shell-chrome rule is written at higher specificity (`.stApp [data-testid="stSidebar"] …` vs the regions' `[data-testid="stSidebar"] …`), so it wins regardless of order;
2. the shell-lock payload is emitted twice — once up front (no unstyled flash during a slow region load) and once at the end of the run (ordering safety net).

Region *content* styling is left entirely alone.

## 10. Asset / path conflicts

Abu Dhabi resolves its CSV relative to `__file__` — safe anywhere. Dubai uses ~90 bare relative filenames — safe only when the process working directory is the Dubai folder.

**Resolution:** `platform_core/runtime.py` runs each region from its own directory (restored in a `finally`, serialised by a lock). Zero path literals were rewritten, so no data reference can drift.

## 11. Data-file dependencies

All 88 distinct data files referenced by `trial.py` were traced and verified present. Two apparent misses are false positives: `dubai_real_estate_predictions.csv` is a *download filename*, and `your_dataset.csv` appears only in a comment.

Abu Dhabi depends on exactly one file: `Abu_Dhabi_Sales_Cleaned (1).csv`.

## 12. Model-file dependencies

20 × `dt_model_<Area>.pkl` (per-area decision trees) + `onehot_encoder.pkl` + `train_columns.pkl`, all loaded lazily by the V2.1 prediction console. All present; none regenerated.

## 13. Naming conflicts

Abu Dhabi imports top-level packages named `config`, `utils`, `styles`, `components`, `charts` — generic enough to shadow. Mitigated by adding the region directory to `sys.path` only for the duration of its run and removing it afterwards. The platform's own package is `platform_core`, which cannot collide.

## 14. Files that remain untouched

Everything except the six lines listed in `INTEGRATION_CHANGES.md`. Specifically: all of `abu_dhabi/{charts,components,config,styles,utils}`, all Dubai data/model/HTML assets, `FC_st.py`, `testing.py`, and all analytical logic in both `app.py` and `trial.py`.

## 15. Files needing integration changes

`regions/abu_dhabi/app.py` (4 edits) and `regions/dubai/trial.py` (4 edits) — enumerated in `INTEGRATION_CHANGES.md`. Every edit is a redirect to `platform_core.region_bridge`, and every one is a no-op when the region is run standalone.

## 16. New files required

```
streamlit_app.py            single entry point
requirements.txt            unified dependencies
.streamlit/config.toml      global Streamlit config
platform_core/              config · design_system · navigation ·
                            components · region_bridge · runtime
platform_pages/             overview · explore · about ·
                            region_abu_dhabi · region_dubai
docs/                       this file · INTEGRATION_CHANGES · CHECKLIST
```

---

## Execution model

```
streamlit run streamlit_app.py
   │
   ├─ st.set_page_config()                  ← the only one in the repository
   ├─ inject platform CSS + shell lock
   ├─ render global sidebar  → route
   │
   ├─ route == overview / explore / about   → platform_pages/*.py
   │
   └─ route == abu_dhabi / dubai
        ├─ breadcrumb + region banner + explainer      (new)
        ├─ "Region controls" divider in the sidebar    (new)
        └─ runtime.run_region(...)
             ├─ acquire lock, chdir(region), extend sys.path
             ├─ region_bridge._set_embedded(True)
             ├─ runpy.run_path(entry, run_name="__main__")   ← unmodified logic
             └─ finally: restore cwd, sys.path, embed flag
   │
   └─ finally: re-inject shell lock, render rail footer
```

**Why `runpy` rather than importing:** Streamlit scripts are top-level statements, not functions. `runpy.run_path(..., run_name="__main__")` executes them exactly as `streamlit run` would, every rerun, with no import caching to invalidate — which is what keeps the regional behaviour identical.


---
---

# v1.1 — Dubai regional dashboard & Experimental Analysis

## 17. The three-environment split

The Dubai *experiments* and the Dubai *market* are now different things:

| Rail item | Route | Code | Data |
|---|---|---|---|
| 🇦🇪 Abu Dhabi | `abu_dhabi` | `regions/abu_dhabi/app.py` (embedded) | `Abu_Dhabi_Sales_Cleaned (1).csv` |
| 🇦🇪 Dubai | `dubai` | `regions/dubai_market/` (imported) | `data/dubai/latest_combined_data.parquet` |
| 🧪 Experimental Analysis | `experimental` | `regions/dubai/trial.py` (embedded) | the project's pre-computed artefacts |

**Why Dubai is imported rather than embedded.** The regional dashboard is new
platform-authored code, so it is an ordinary Python package with a `render()`
function — no `runpy`, no `chdir`, no bridge. Only the two pre-existing
applications need the embedding runtime.

## 18. Dubai datasets — what was found

Both supplied files were profiled before any code was written.

| | `transactions.parquet` (RAW) | `latest_combined_data.parquet` (CLEANED) |
|---|---|---|
| Rows | 1,762,262 | 818,838 |
| Columns | 47 | 85 |
| Date range | 1966-01-18 → 2026-08-06 | 2010-01-01 → 2026-08-06 |
| Areas | 258 | 69 |
| Scope | Sales + Mortgages + Gifts; Unit, Villa, Land, Building; all usages | Sales only · Unit only · Residential only |

The cleaned file is the **residential-unit sales slice** of the registry
(928,489 such rows exist in the raw file; 818,838 — 88.2% — carry through,
2010 onwards), enriched with 38 engineered columns: time parts, unit
attributes, amenity flags and building / developer scoring.

**Decision: the cleaned file powers every Dubai section.** It is the only one
of the two with amenity flags, locality zones, unit sizes and quality tiers,
and it is already restricted to a single comparable segment. The raw file is
retained and is compared against the cleaned file in the *Where this data comes
from* panel; that comparison is precomputed by `tools/build_dubai_provenance.py`
into `data/dubai/provenance.json`, so the 81 MB raw file is never read to draw
a page.

**Fields actually used** (verified against the schema — nothing assumed):

| Purpose | Column |
|---|---|
| Sale price | `actual_worth` |
| Rate per m² | `meter_sale_price` |
| Unit size | `procedure_area` |
| Time | `instance_date`, `year`, `month`, `quarter`, `year_month` |
| Geography | `area_name_en`, `master_project_en`, `project_name_en`, `building_name_en`, `Locality Zone`, `nearest_metro_en`, `nearest_mall_en` |
| Property | `property_sub_type_en`, `rooms_en`, `reg_type_en`, `procedure_name_en`, `unit_balcony_area` |
| **Amenities** | `has_parking`, `swimming_pool`, `balcony`, `elevator`, `metro` |
| Quality | `Grade`, `Price Tier`, `Reputation`, `project_grade`, `Developer Tier`, `developer_name_en`, `Est. Gross Rental Yield (%)`, `Composite Score (0-100)` |

**Fields deliberately not used.** `floor_bin` holds only `Unknown`/null and
carries no information. `Price/sqft (AED)` is populated for 21% of rows. Raw
`elevators` is null for 52% of rows (the binary `elevator` flag is complete and
is used instead). Arabic mirror columns duplicate their English counterparts.

**Memory.** Loading all 85 columns costs 1.26 GB. The dashboard loads the 34 it
needs and downcasts to category / float32 / int8 — **55 MB**, cached with
`st.cache_resource` so it is loaded once per process, never per rerun. Row
values are unchanged; only their storage width is.

## 19. The API endpoint question

**Finding: there is no HTTP API in the supplied Dubai codebase.** Every `.py`
file was searched for `http`, `requests`, `urllib`, `httpx` and `socket`. The
only external URL anywhere is
`https://flipose-re-price-prediction.streamlit.app/`, used twice with
`st.link_button` — a link to a separately deployed Streamlit app, not a
callable endpoint.

No endpoint was invented. Forecasting in the Dubai *Price* section therefore
reads the forecast artefacts the modelling pipeline already produced and stored
with the project:

| File | Used for |
|---|---|
| `arima_forecast_quarterly_all_areas.csv` | fitted + forecast path with confidence band |
| `quarterly_forecasts_with_CI.csv` | forward quarters and growth factors |
| `metrics_lowess_all_areas1.csv` | published test MAPE / MAE and SARIMA orders |
| `arima_areas_growth_6M.csv` | six-month growth outlook |

Nothing is refitted at runtime. If a real prediction API exists elsewhere in
the company, point it out and it can be wired into the same section — the
loader is isolated in `regions/dubai_market/data.py::load_forecast_artifacts`.

## 20. Session state — updated

| Key | Owner | Note |
|---|---|---|
| `uae.route`, `uae.experiment` | platform | namespaced; cannot collide |
| `dxb_*` (7 keys) | Dubai dashboard | namespaced filter widgets |
| `dark_mode` | Abu Dhabi | shared with the platform toggle, on purpose |
| `area_models`, `ohe` | Experimental (`trial.py:2660`) | untouched |

Three environments, three disjoint key spaces.
