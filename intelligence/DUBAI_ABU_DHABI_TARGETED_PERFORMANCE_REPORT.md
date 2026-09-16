# TruEstate targeted Abu Dhabi and Dubai performance report

Date: 2026-09-16

## Scope and baseline

This investigation was limited to the Abu Dhabi and Dubai runtime paths. The
verified Abu Dhabi Parquet artifact and all source data files were treated as
read-only. No RSS, Qwen, or OpenRouter calls were made.

Hosted baseline supplied for this investigation:

| Route | First load | Warm load |
| --- | ---: | ---: |
| Overview | 0.01 s | — |
| Abu Dhabi | 6.34 s | 4.47 s |
| Dubai | 11.49 s | 11.53 s |

Local measurements below were collected with Streamlit `AppTest` and direct
function-level timers in fresh and repeated Python processes. They measure
application execution rather than browser/network latency or Streamlit Cloud
container wake-up time, so they are used for attribution and A/B comparison,
not as replacements for the hosted timings.

## Abu Dhabi findings

The current Abu Dhabi path uses the verified artifact:

`regions/abu_dhabi/Abu_Dhabi_Sales_Optimized.parquet`

Its SHA-256 was rechecked as
`274da4ed22ca26daa65cab7c507d8ea42995f9937c081a1a23338dda7b8fead9`.
The artifact was not regenerated, rewritten, converted, or replaced.

| Function/stage | Cold | Warm | Finding |
| --- | ---: | ---: | --- |
| `utils.data_loader.load_data` | 0.132 s | cached | Parquet read is not dominant |
| `charts.price_scatter` | 1.365 s | 0.093 s | Largest cold chart stage |
| `charts.density_plot` | 0.299 s | 0.293 s | Rendering stage, not file loading |
| Complete Abu Dhabi route after Overview | 3.771 s | 1.808 s | No safe data-loader change identified |

The Abu Dhabi data load is a small fraction of route execution. Because the
requested artifact must remain unchanged and no proven safe Abu Dhabi
bottleneck was identified, no Abu Dhabi code or data optimization was made.

## Dubai findings before changes

The deployed Dubai route is `streamlit_app.py` →
`platform_pages/region_dubai.py` → `regions.dubai_market.dashboard.render()`.
Its cleaned market source is already `data/dubai/latest_combined_data.parquet`.

| Function/stage | Cold | Warm/observed | Finding |
| --- | ---: | ---: | --- |
| `data.load_market` | 0.159 s | ~0 s | Existing Parquet loading is fast |
| `data.filter_options` | 0.067 s | ~0 s | Not a bottleneck |
| `data.load_raw_transaction_counts` | 0.002 s | ~0 s | Not a bottleneck |
| `data.load_provenance` | 0.001 s | ~0 s | Not a bottleneck |
| `data.load_forecast_artifacts` | 0.005 s | ~0 s | Not a bottleneck |
| First Pandas `df.style.format` call | 10.297 s | subsequent calls ~0.001–0.006 s | Matplotlib/font-cache initialization |
| `platform_core.dubai_report` import | 11.063 s | already initialized | Heavy first-use report renderer import |
| Report `builder.build` after import | 1.578 s | — | Actual report construction |
| Complete Dubai route after Overview | 15.78 s | about 3.0 s | Cold cost was primarily first-use rendering/import work |

The first styled table was separately timed at about 10.252 s, while the
following `st.dataframe` call took about 0.010 s. Importing the report module
before rendering reduced the subsequent route to about 5.58 s, confirming that
the large cold cost came from first-use renderer initialization rather than
data loading.

Because Dubai's existing Parquet read completed in 0.159 s cold and was near
zero warm, profiling does not support a Dubai Parquet migration. No data
conversion or replacement was performed.

## Targeted changes

Only two Dubai performance paths were changed:

1. Dubai analytics tables now pass typed DataFrames to Streamlit with equivalent
   numeric column formats instead of invoking Pandas Styler. The format map
   covers every format used by the existing Dubai dashboard:
   `%,d`, `%,.0f`, `%.1f`, `%.2f`, `%+.1f`, and `%,.1f`.
2. The existing Dubai PDF builder is loaded and run only when the user selects
   `Prepare Dubai report`. The builder, inputs, report contents, styling, and
   download path remain the existing implementation; the expensive renderer is
   no longer imported during the initial analytics render. Analytics remain
   available immediately while report preparation is on demand.

The pure Dubai `smart_insights` calculation is also cached with Streamlit's
data cache. Its calculation logic and returned content were not changed.

No graph, KPI, filter, calculation, dataset, intelligence component, Abu Dhabi
artifact, or other region/page was modified.

## A/B validation

Post-change local smoke results:

| Measurement | Before | After |
| --- | ---: | ---: |
| Dubai cold route after Overview | ~15.78 s | 5.235 s |
| Dubai repeated route samples | ~3.0 s | 2.583–2.998 s (median ~2.78 s) |
| Dubai chart elements | 29 | 29 |
| Dubai dataframe elements | 20 | 20 |
| Runtime exceptions | 0 | 0 |

The explicit report-preparation path was exercised after the change: it
completed with zero runtime exceptions and retained the existing `Download the
All Areas report · PDF` download control.

Additional validation completed:

- `python3 -m unittest discover -s tests -p 'test_*.py' -q`: 43 tests passed,
  2 expected skips.
- Python compilation completed successfully.
- `git diff --check` completed successfully.
- The Abu Dhabi Parquet SHA-256 remained unchanged.
- Source data files were not modified.

Cross-page `AppTest` smoke also completed with zero exceptions for Abu Dhabi,
Dubai, Sharjah, RAK, Experimental Analysis, Explore Platform, About, and
Overview. Chart/table counts remained populated on the regional pages (25/2,
29/20, 5/5, 10/15, and 2/2 respectively), with no changes to the shell-only
pages.

These results prove a targeted local improvement on the profiled bottleneck.
Deployment verification is recorded separately after the commit is pushed.
