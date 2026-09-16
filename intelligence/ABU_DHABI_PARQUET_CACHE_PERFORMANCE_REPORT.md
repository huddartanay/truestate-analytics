# Abu Dhabi Parquet, Cache and Page-Performance Report

## 1. Requirement

The Abu Dhabi optimization is strictly scoped to the existing Abu Dhabi data
path and safe shared page timing. The existing dashboard, formulas, filters,
charts, exports, intelligence layer, other regional datasets and deployment
architecture remain in place.

## 2. Baseline

The original runtime path read `regions/abu_dhabi/Abu_Dhabi_Sales_Cleaned (1).csv`
and then repeated deterministic preparation in `load_data()`. A fresh local
Streamlit AppTest measured an Abu Dhabi navigation preparation time of 31.31s.
This local number includes Python application preparation and is not a browser
paint or Streamlit Cloud provisioning measurement.

The isolated baseline profile found:

| Operation | Observation |
|---|---:|
| `pd.read_csv` itself | 0.14s |
| `YearMonth`/temporal feature construction | 5.94s |
| uncached original `load_data()` samples | 6.49s, 6.15s, 6.16s; median 6.16s |
| first Abu Dhabi report-module import | 11.56s |
| eager Excel workbook construction during a page run | 20.48s in cProfile |
| cold Abu Dhabi route, full original path | 31.31s |

The report module imported Matplotlib even when no PDF was requested. The
Download tab also passed a newly generated 109k-row workbook directly into
`st.download_button`; Streamlit evaluates that expression during every run,
including runs where another tab is visible.

## 3. Attached workbook

The attached `recent_sales.xlsx` workbook was profiled only after the current
runtime source was traced. It contains one sheet (`recent_sales`), 117,888 rows,
14 columns, 6,260 duplicate rows, 9,569,132 bytes on disk, and registrations
from 2019-01-02 through 2026-07-21.

The current repository CSV contains 109,097 rows, 17 columns, no duplicate
rows, 17,489,850 bytes, and dates from 2019-01-02 through 2026-06-08. After
canonical column mapping and conservative normalization, 109,094 of the
109,097 current rows share the `(date, price)` key with the workbook, while the
workbook has 8,794 additional `(date, price)` rows. Non-key fields also differ.
The evidence classifies the workbook as `UPDATED_VERSION_OF_CURRENT_SOURCE`,
not an exact current-source copy.

It was not substituted into production because doing so would change existing
business outputs and would fail the data-fidelity gate. The workbook remains
untouched and is not committed. The prepared Parquet is built from the current
repository source whose existing outputs are preserved exactly.

## 4. Original dataset profile

The current source has 109,097 rows and these 17 source columns:

`Asset Class`, `Property Type`, `Sale Application Date`, `Property Sold Area
(SQM)`, `Land Plot Ground Area (SQM)`, `Property Layout`, `District`,
`Community`, `Project Name`, `Property Sale Price (AED)`, `Property Sold Share`,
`Rate (AED per SQM)`, `Sale Application Type`, `Sale Sequence`, `Year`, `Month`,
`Quarter`.

The original CSV has no duplicate rows. Its raw in-memory footprint is
70,077,460 bytes (66.83 MiB). The existing loader's prepared 20-column frame is
76,296,069 bytes (72.72 MiB); this is the relevant memory baseline for the
dashboard because the derived temporal columns are used by the page.

## 5. Abu Dhabi code audit and lineage

The unified route is:

`streamlit_app.py` → `platform_pages/region_abu_dhabi.py` →
`platform_core/runtime.py::run_region()` → `regions/abu_dhabi/app.py` →
`regions/abu_dhabi/utils/data_loader.py::load_data()` → prepared Abu Dhabi
Parquet.

The Abu Dhabi report route is:

`platform_pages/report.py::_abu_dhabi_block()` →
`platform_core/abu_dhabi_report.py` → the same Abu Dhabi loader for full report
generation. Its district picker reads only three Parquet columns.

All 25 existing Plotly render slots were traced in `regions/abu_dhabi/app.py`:

1. `monthly_trend_chart`
2. `yearly_trend_chart`
3. `quarterly_trend_chart`
4. `district_treemap`
5. `top_communities_bar` or `premium_vs_affordable_communities_chart`
6. `district_bubble_chart`
7. `top_areas_price`
8. `property_type_donut`
9. `layout_bar_chart`
10. `sale_type_pie`
11. `sale_sequence_pie`
12. `price_trend_line`
13. `price_distribution_chart`
14. `price_box_by_layout`
15. `price_scatter`
16. `violin_plot`
17. `density_plot` for price
18. `density_plot` for rate when the existing guard permits it
19. `monthly_seasonality_chart`
20. `apt_yoy_growth_chart`
21. `apt_rate_volume_chart`
22. `yoy_growth_chart`
23. `correlation_heatmap`
24. `outlier_boxplot` for price
25. `outlier_boxplot` for rate when the existing guard permits it.

The existing KPI band, insight calculations, data-quality report, filtered
CSV/Excel/Summary exports, and Abu Dhabi area-wise PDF report were also traced.
All continue to consume the same prepared frame and existing functions.

## 6. KPI and filter inventory

The executive KPI band uses row count, total/mean/median price, mean/median rate,
maximum/minimum price, district/community/project/property-type cardinality,
and the current year range. Insight calculations additionally use year, sale
type, layout, community and sale sequence. The data-quality tab inspects every
column and the export tab emits all retained columns.

The unchanged filters are dataset scope, years, property type, layout, district,
sale type, sale sequence, sale-price range and sold-area range. Their option
generation and ordering remain in `app.py`; only the source read beneath them
changed.

## 7. Column dependency analysis

| Column group | Dependency evidence | Decision |
|---|---|---|
| Date | temporal features, time charts, report coverage, export | KEEP |
| Price | KPIs, every value/price aggregation, charts, summaries, export | KEEP |
| Sold area | range filter, scatter/distribution/statistics/report/export | KEEP |
| Rate | KPIs, price/rate charts, apartment cleaning, report/export | KEEP |
| Asset class | apartment-scope filter and cleaning | KEEP |
| Property type | filter, KPI, donut, apartment scope, export | KEEP |
| Layout | filter, layout charts, report, export | KEEP |
| District | filter, KPI, geographic charts, report, export | KEEP |
| Community | KPI, geographic charts, report, export | KEEP |
| Project name | project KPI and export/data contract | KEEP |
| Sale type | filter, insight, chart, report, export | KEEP |
| Sale sequence | filter, insight, chart, export | KEEP |
| Sold share | retained in all filtered exports and source contract | KEEP |
| Land plot area | retained in all filtered exports and source contract | KEEP |
| Year / Month / Quarter | temporal filter/chart/export fields; source values are reconciled by the existing loader | KEEP |
| Month_Num / YearMonth / YearQuarter | deterministic runtime feature columns used by time charts/export; now prepared at build time | KEEP |

No column met the standard for safe removal. Removing the apparently unused
land-area or sold-share fields would change the existing all-column exports and
data-quality report. Removing temporal fields would change the prepared-frame
contract and export column behavior. Therefore columns removed: **none**.

## 8. Cleaning and preparation

`tools/build_abu_dhabi_parquet.py` applies the existing loader's deterministic
operations once: duplicate removal, date parsing, temporal feature creation,
numeric coercion and lower-case/trim normalization for the existing string
fields. No values are imputed, rounded for business purposes, or otherwise
invented. The runtime does not convert CSV to Parquet and does not repeat this
preparation on each rerun.

## 9. Data fidelity validation

The build-time prepared DataFrame was compared to the original loader contract
with exact row, column, value and dtype equality. The focused test passed for
all 109,097 rows and all 20 prepared columns. Existing RAK, intelligence and
platform regression tests also passed in the full suite.

## 10. Parquet schema and artifact

The runtime artifact is `regions/abu_dhabi/Abu_Dhabi_Sales_Optimized.parquet`,
written with the already-declared `pyarrow` dependency and Snappy compression.
It contains 109,097 rows and 20 columns, including a `datetime64` sale-date
column, numeric price/area/rate fields, source string fields and the existing
temporal features. It is 2,502,540 bytes (2.39 MiB).

| Measure | CSV source | Prepared Parquet |
|---|---:|---:|
| Rows | 109,097 | 109,097 |
| Columns on disk | 17 | 20 prepared runtime columns |
| Disk size | 17,489,850 bytes | 2,502,540 bytes |
| Disk reduction | — | 85.69% |
| Loaded frame memory | 70,077,460 bytes raw / 76,296,069 prepared | 76,296,069 bytes |
| Memory reduction | — | 0% versus prepared runtime frame |

The artifact reduces disk and preparation cost; it does not falsely claim a
Pandas object-memory reduction. Caching trades a bounded amount of process
memory for faster reuse.

## 11. Abu Dhabi loader change

`load_data()` now resolves the prepared Parquet and validates the complete
prepared-column contract. A cheap `(path, size, mtime_ns)` identity is passed
to the cached reader, so a rebuilt artifact naturally invalidates its cache.
There is no runtime CSV fallback and no runtime CSV→Parquet conversion. A
missing or incomplete artifact raises a handled load error rather than showing
incorrect analytics.

The Abu Dhabi report district list also reads three columns from the Parquet.
Matplotlib/PDF report code is imported only when the user presses the existing
report-preparation action.

## 12. Streamlit cache architecture

| Function | Page | Cache | Input key / invalidation | Why |
|---|---|---|---|---|
| `_read_prepared_parquet` | Abu Dhabi/report | `st.cache_data`, max 2 | absolute artifact path, size, mtime | avoid repeated full reads |
| `get_apartments_df` | Abu Dhabi | existing `st.cache_data` | prepared DataFrame hash | reuse scope filter |
| `get_cleaned_apartments_df` | Abu Dhabi | existing `st.cache_data` | prepared DataFrame hash | reuse sequential percentile cleaning |
| `_load` in `app.py` | Abu Dhabi | existing `st.cache_data` | prepared-artifact fingerprint | reuse the three page frames while invalidating after rebuild |
| `_district_counts` | Reports | `st.cache_data`, max 2 | artifact path, size, mtime | avoid full-frame report picker load |
| `_to_excel` | Abu Dhabi | on-demand only | current filter signature | avoid building an unrequested workbook |

No user-specific filters or chat state are globally cached. Cached DataFrames
remain read-only inputs; downstream existing code continues to use its own
copies where it mutates data. The current RSS cache and intelligence cache are
untouched.

## 13. Website-wide cache audit

| Area | Decision |
|---|---|
| Overview / Explore / About | no large dataset; no new data cache needed |
| Abu Dhabi | prepared Parquet and deterministic frames cached |
| Dubai | existing Parquet/resource and deterministic caches retained |
| Sharjah | report-source module is lightweight; no new cache needed |
| RAK | existing source/analytics caches retained |
| Area Analysis | existing Dubai cache retained |
| Market Outlook / Forecast | existing caches and session-specific result state retained |
| Experimental Analysis | saved artifacts and existing behavior retained |
| Current intelligence / RSS / Qwen / OpenRouter | frozen; no changes |

## 14. Page timing architecture

`platform_core/performance.py::page_timer()` uses `time.perf_counter()` around
the active route in `streamlit_app.py`. It reports a single unobtrusive
`Page prepared in X.XXs` caption and logs only the page label and duration.
This is server-side page preparation from route execution start through the
active renderer's completion. It excludes browser paint, network transfer and
Streamlit Cloud container wake-up time.

Timing is wired through the shared route wrapper for Overview, Abu Dhabi, Dubai,
Sharjah, RAK, Area Analysis, Download Reports, Forecast, Experimental Analysis,
Explore Platform and About. No page duplicates timer logic.

## 15. After measurements

| Path | Samples / result |
|---|---:|
| Parquet uncached read | 0.160s, 0.059s, 0.067s; median 0.067s |
| Parquet cached read | 0.032s, 0.027s, 0.029s; median 0.029s |
| Abu Dhabi cold route after change | 4.45s and 3.70s; observed median 4.07s |
| Abu Dhabi warm Year(s) filter rerun | 1.91s |
| Abu Dhabi district picker | 0.19s |
| Abu Dhabi Excel preparation, on demand | 11.99s; no longer on page load |

Representative sequential warm navigation in one local Streamlit AppTest run:

| Route | Preparation time |
|---|---:|
| Overview | 0.30s |
| Abu Dhabi | 3.70s |
| Dubai | 16.77s |
| Area Analysis | 0.51s |
| Forecast | 0.19s |
| Download Reports | 0.01s |
| Sharjah | 0.83s |
| RAK | 1.09s |
| Experimental Analysis | 1.11s |
| Explore Platform | 0.02s |
| About | 0.01s |

The Dubai first navigation remains governed by its existing large-dataset
behavior and was not changed by this Abu Dhabi-only migration. Streamlit Cloud
cold-container startup, dependency installation and browser/network latency
remain outside Python route-preparation control.

## 16. Regression and visual smoke

Focused Abu Dhabi Parquet/schema/fidelity/timing tests pass. The local
Streamlit smoke had zero exceptions on Overview and Abu Dhabi, rendered all 25
existing Plotly slots and showed the timing caption. The Excel preparation
action rendered the existing workbook download after explicit preparation with
zero exceptions. Full repository tests and compile checks are required before
deployment; no test permits a data-value change or a missing graph.

## 17. Files created

- `regions/abu_dhabi/Abu_Dhabi_Sales_Optimized.parquet`
- `tools/build_abu_dhabi_parquet.py`
- `platform_core/performance.py`
- `tests/test_abu_dhabi_performance.py`
- this report.

## 18. Files modified

- `regions/abu_dhabi/config/settings.py` — artifact and schema contract.
- `regions/abu_dhabi/utils/data_loader.py` — Parquet-only fingerprinted loader.
- `regions/abu_dhabi/app.py` — on-demand Excel generation only.
- `platform_core/abu_dhabi_report.py` — Parquet district list and lazy PDF import.
- `streamlit_app.py` — shared route timing wrapper.
- `docs/ARCHITECTURE.md` — runtime data-path documentation.

No Dubai, Sharjah, RAK, forecast, intelligence, RSS, Qwen, OpenRouter,
navigation, styling or business-calculation source was changed.

## 19. Data artifact deployment

The Parquet artifact is 2.4 MB, below normal repository/deployment limits, and
uses the already-declared `pyarrow` dependency. The original CSV remains in
the repository unchanged for provenance but is not read during production
runtime. No Git LFS, secrets, scheduler or new Streamlit application is used.

## 20. Security

The UI exposes only the friendly duration. It does not expose local paths,
cache internals, library details, secrets, user questions or stack traces.
Artifact errors are handled through existing platform error cards.

## 21. Remaining limitations

The prepared frame has the same Pandas memory footprint as the original
prepared frame; the measurable gain is disk/read/preparation time. The attached
workbook contains newer/different records and was deliberately not adopted in
this preservation-scoped change. Browser paint and Streamlit Cloud cold starts
need hosted observation beyond local server-side timings.

## 22. Final acceptance checklist

- [x] Current Abu Dhabi source discovered before attachment comparison.
- [x] Attached workbook profiled and left unchanged.
- [x] All current columns and indirect dependencies audited.
- [x] No required columns removed; no unjustified columns removed.
- [x] Parquet generated with valid typed schema.
- [x] Runtime reads Parquet only; no runtime conversion or silent CSV fallback.
- [x] Existing Abu Dhabi graph/KPI/filter/export contracts preserved.
- [x] Parquet loading and report district list are fingerprint-cached.
- [x] Current RSS/intelligence/Qwen/OpenRouter architecture untouched.
- [x] Shared server-side timing covers every platform route.
- [x] Cold, warm and representative route timings measured.
- [x] On-demand Excel generation prevents unrequested workbook work on reruns.
- [x] Focused tests, full tests, compile and security checks passed before push;
      deployment verification is recorded in the handoff after deployment.
