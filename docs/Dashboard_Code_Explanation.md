# Dashboard Code Explanation

How the Dubai section of the unified platform is built, and how each remaining
visualisation is calculated. Only visualisations **currently present** are
documented; removed ones are not.

---

## Code layout

| File | Responsibility |
|---|---|
| `streamlit_app.py` | The only entry point: page config, design system, navigation, routing |
| `platform_pages/region_dubai.py` | Region banner, then renders the Dubai dashboard |
| `regions/dubai_market/data.py` | **Data loading only** — both datasets, filters, formatting helpers |
| `regions/dubai_market/metrics.py` | **Analytical calculations** — no Streamlit, no Plotly |
| `regions/dubai_market/charts.py` | **Visualisation** — Plotly builders, no data access |
| `regions/dubai_market/dashboard.py` | **UI and filter logic** — lays out sections, calls the three layers above |
| `regions/dubai_market/chart_info.py` | One documentation registry driving every ⓘ and the Word guide |

The separation is strict: `metrics.py` never imports Streamlit, `charts.py` never
reads a file, and `dashboard.py` performs no arithmetic beyond formatting.

### Data loading

```python
load_market()                   # CLEANED, @st.cache_resource, 34 cols, ~55 MB
load_raw_transaction_counts()   # RAW, @st.cache_data, counts per (year, month)
raw_coverage()                  # latest year/month and totals from RAW
load_provenance()               # precomputed raw-vs-cleaned comparison
```

`load_raw_transaction_counts` reads **four columns** from the 81 MB raw file and
returns only counts, so the raw registry is never held in memory by the page.
Both loaders are cached, so no dataset is read twice per session.

**Raw vs cleaned, stated once:** counts come from RAW because preprocessing
removes 668–7,369 rows per year from the cleaned file; every price and rate
figure comes from CLEANED because that is where the engineered columns live and
it is the validated price basis.

---

## Trends

### Transactions recorded each year

- **Implemented by:** `dashboard._raw_volume_panel` → `metrics.raw_transaction_years`,
  `metrics.partial_year_growth` → `charts.raw_transaction_volume`
- **Dataset:** **RAW** (`data/dubai/transactions.parquet`)
- **Columns:** `instance_date`, `trans_group_en`, `property_type_en`, `property_usage_en`
- **Filtering:** restricted to `Sales` + `Unit` + `Residential` — the same
  population the rest of the page uses. **The sidebar filters do not apply**, by
  design: the chart reports what was registered, not what matches a selection.
  This is stated on the chart and in its ⓘ.
- **Metric:** count of rows per year, from 2011.
- **Aggregation:** `groupby(year, month).size()`, then summed to years.
- **Complete-year growth:** `transactions / transactions.shift() - 1`, ×100 —
  chained, so every year is measured against the row directly above it. The first
  row (2011) is set to `NaN`: it is the base year.
- **2026 handling:** a year is `complete` only when the registry covers 12 of its
  months. For an incomplete year `yoy_pct` is set to `NaN`, so no full-year style
  figure can reach the chart. `partial_year_growth` then computes the like-for-like
  position against **the same months of the previous year** and exposes
  `display_growth`, which is populated **only if growth is strictly positive**:

  ```python
  "display_growth": growth if (pd.notna(growth) and growth > 0) else None
  ```

- **Why negative 2026 growth is suppressed:** comparing 8 months against 12
  produces a decline caused by the calendar, not the market. The like-for-like
  figure (−21.9%) is a real comparison but still describes a part year, so the
  chart shows the count and no percentage.
- **Visualisation:** `make_subplots(secondary_y=True)`. Two bar series — completed
  years in blue, the incomplete year in amber as its own series so it gets its own
  legend entry and hover — plus a dotted scatter on the secondary axis for growth.
- **Axes:** X = year (category). Left Y = transactions recorded. Right Y = growth %.
- **Legend:** *Transactions recorded* · *2026 — January–August only (in progress)*
  (period generated from the data) · *Year-over-year growth (%)*.
- **Tooltip:** completed years show year, transactions recorded and the
  whole-registry count; the incomplete year additionally shows the period and
  "Part year — not comparable with a full year"; the growth line shows the
  percentage against the previous year.
- **Special handling:** `add_annotation` is **not** used — anchoring an annotation
  to a value on a category axis collapses the axis in this Plotly build. The
  warning lives in the second series' name and hover instead.
- **Why appropriate:** it counts what was recorded, chains growth correctly, and
  refuses to present an incomplete period as an annual outcome.

### Monthly market activity · Annual volume · Quarterly pattern · Seasonality

Unchanged. `charts.monthly_volume_value`, `annual_volume`, `quarterly_heatmap`,
`seasonality`, all on the **cleaned** filtered frame via `metrics.monthly_series`
and `metrics.yoy_table`. Monthly activity carries a three-entry legend
(Transactions, Total value, 3-month average); the other three are single-series
and use titles and axis labels instead.

---

## Insights · Geography · Property

Unchanged from the previous build. Each chart reads the **cleaned** filtered
frame, aggregates with a `groupby` + `median`/`sum`/`size`, and is drawn by the
matching builder in `charts.py`: `pareto`, `tier_rate_bar`, `top_areas_volume`,
`top_areas_rate`, `area_treemap`, `area_bubble`, `zone_comparison`,
`metro_effect`, `layout_mix`, `size_by_layout`, `rate_by_layout`,
`reg_type_split`, `procedure_split`, `size_vs_price`.

`rate_by_layout` draws small multiples from quartiles computed in pandas
(`_box_stats`) rather than shipping raw values to the browser; layouts under 100
transactions are listed in a table rather than dropped silently.

---

## Price

### How prices are moving

- **Implemented by:** `dashboard._section_price` → `charts.price_rate_trend`
- **Dataset:** CLEANED, filtered. **Columns:** `year_month`, `actual_worth`, `meter_sale_price`
- **Metric:** per month, `median(actual_worth)` and `median(meter_sale_price)`.
- **Smoothing:** a **centred 3-month rolling median** of those monthly medians
  (`SMOOTH_WINDOW = 3`). A median, not a mean, so one unusual month cannot drag
  the line. The actual observations are never replaced — a radio switches between
  *Both*, *Smoothed trend* and *Actual monthly*, and every actual value is listed
  in the table beneath.
- **X-axis:** month (timestamp). **Left Y:** median sale price. **Right Y:** median rate/m².
- **Legend:** four entries when both views are shown — actual and 3-month trend
  for each of price and rate.
- **Hover:** month, and the value of the hovered series.
- **Special handling:** the final month is shaded when it holds materially fewer
  transactions than the one before it, because the dataset ends mid-month.

### Year-by-year summary

- **Implemented by:** `dashboard._yearly_summary_panel` → `metrics.yearly_summary`
- **Datasets — two, labelled per column:** transaction counts from **RAW**;
  `mean` and `median` of `meter_sale_price` from **CLEANED**, filtered.
- **Columns:** Year · Number of transactions (raw) · Mean rate/m² · Median rate/m² ·
  Priced transactions used (cleaned).
- **Aggregation:** `groupby(year)` on each side, merged on year, from 2011.
- **Special handling:** the incomplete year's label carries "(January–August, in
  progress)", generated from the data.
- **Why appropriate:** it uses the specified source for each metric, shows the
  count actually behind the rate columns so the two are never confused, and makes
  no off-plan claim.

### Price with and without an amenity, by property type

- **Implemented by:** `dashboard._amenity_by_type_panel` →
  `metrics.amenity_by_property_type` (+ `..._table`) → `charts.amenity_within_property_type`
- **Dataset:** CLEANED, filtered. **Columns:** `rooms_en`, one amenity flag,
  `meter_sale_price`, `procedure_area`, `actual_worth`
- **Property-type filtering:** `df[df[rooms_en] == selected]` — every subsequent
  calculation happens inside that subset, so no other property type can enter.
  Labels map through `PROPERTY_TYPE_LABELS` (`1 B/R` → `1 BHK`); the filter lists
  only types present in the current selection.
- **Amenity filtering:** the chosen flag splits that subset into `== 1` (recorded
  with) and `== 0` (recorded without). Nothing is imputed.
- **Present vs absent grouping:** two groups, each requiring **≥100 transactions**
  (`MIN_CELL`); otherwise a warning replaces the result.
- **Price calculation:** `median(meter_sale_price)` per side, with the 25th and
  75th percentiles for the range bars, plus median size and median price.
- **Comparison methodology:** `(median_with ÷ median_without − 1) × 100`, expressed
  against the without group and described as an **observed difference**.
- **Axes:** X = recorded amenity status within the selected type. Y = median rate/m².
- **Legend:** two entries, named from the selected amenity.
- **Tooltip:** median rate, transaction count, the middle-half range, median unit size.
- **Filters:** the seven sidebar filters plus the two on the chart.
- **Why appropriate:** holding the property type fixed removes the dominant
  confounder of the old market-wide comparison, the range bars show how much the
  groups overlap, and the wording claims description, never causation.

### Rate by building height and property type

- **Implemented by:** `dashboard._building_height_panel` →
  `metrics.building_height_bands`, `metrics.rate_by_building_height` →
  `charts.rate_by_building_height`
- **Dataset:** CLEANED, filtered. **Columns:** `floors`, `building_name_en`,
  `rooms_en`, `meter_sale_price`
- **Floor field:** `floors`. It is **not** the unit's floor — it is constant within
  `property_id_bld` for 100% of buildings, i.e. the building's height. `floor_bin`
  is the string `Unknown` wherever populated and is unusable. The panel is labelled
  as building height and carries a warning saying a floor-level analysis is not
  possible with this data.
- **Bucket methodology:** quartiles of the height distribution taken **one row per
  building** (`groupby(building).first()`), rounded to whole floors, giving
  `[0, q25, q50, q75, max]` → Low-rise / Mid-rise / High-rise / Tower. Computed at
  run time from the current selection, so the bands follow the data.
- **Property-type grouping:** `groupby([height_band, rooms_en])`.
- **Price calculation:** `median(meter_sale_price)` per cell, with `mean` and the
  transaction count for the hover. Cells below 100 transactions are dropped and
  **named on screen**.
- **Axes:** X = height band. Y = median rate/m².
- **Legend logic:** one entry per property type present after the threshold,
  ordered by `PROPERTY_TYPE_LABELS`, so it never lists a type that is not drawn.
- **Tooltip:** property type, band, median rate, mean rate, transactions.

### Where the price points are

Unchanged. `metrics.price_bands` cuts `actual_worth` into seven fixed bands with
`right=False` (left-closed), returning an audit proving every row lands in exactly
one band. A warning names the active price filter whenever a band is emptied by it.

### What the record shows

- **Implemented by:** `dashboard._market_history_panel`
- **Dataset:** CLEANED, filtered. **Columns:** `year`, `meter_sale_price`, `actual_worth`
- **Metric:** `median(meter_sale_price)` per year; highest, lowest and latest years;
  compound average change `((last ÷ first) ^ (1 ÷ years) − 1) × 100`.
- **Presentation:** four KPI cards, a plain-language paragraph and an expandable
  year-by-year table. **No forecast** — this occupies the position the forecast
  held and states recorded outcomes only.

---

## Distribution

### Sale price distribution · Rate per m² distribution

- **Implemented by:** `charts.price_histogram`
- **Dataset:** CLEANED, filtered. **Columns:** `actual_worth`, `meter_sale_price`
- **Method:** the display range is trimmed to the **0.5th–99.5th percentile**, that
  span is divided into **60 equal-width bins**, and `np.histogram` counts rows per
  bin. Binning happens in numpy, not the browser. The dashed line is the median of
  the **untrimmed** data.
- **Axes:** X = value. Y = transactions. **Legend:** none — single series.
- **Range explainer:** `dashboard._price_range_explainer` recomputes the minimum,
  maximum, quartiles, median and bin width from the same selection and describes
  exactly this calculation, so the text cannot drift from the chart.

### Unit size — key statistics

- **Implemented by:** `dashboard._unit_size_summary`
- **Dataset:** CLEANED, filtered. **Columns:** `rooms_en`, `procedure_area`
- **Metric:** per property type — count, min, 25th, median, 75th, max of floor area.
- **Occupies:** the position of the removed unit-size histogram; same subject.

### Sale price by registration type — summary

- **Implemented by:** `dashboard._price_by_reg_summary`
- **Dataset:** CLEANED, filtered. **Columns:** `reg_type_en`, `actual_worth`, `meter_sale_price`
- **Metric:** per registration type — count, share, 25th/median/75th sale price,
  median rate.
- **Special handling:** the two rows are reported **separately and never
  subtracted**. No premium or discount is computed or displayed.

### How the price distribution has changed

- **Implemented by:** `charts.rate_violin_by_year`
- **Dataset:** CLEANED, filtered. **Column:** `meter_sale_price`, grouped by `year`
- **Method reviewed, not changed.** A deterministic 45,000-row sample
  (`random_state=42`) keeps the chart responsive; one violin per year with an inner
  box plot. **Verified:** worst per-year median error from sampling **2.47%**,
  worst 75th-percentile error **1.66%**, smallest per-year sample **989** rows.
- **Axes:** X = year (category). Y = rate/m².
- **Legend:** none, and none is needed — colour encodes the year, which the x-axis
  already labels.
- **Why appropriate:** it answers "how has the distribution of prices changed over
  time" directly — both the centre moving and the shape widening are visible — and
  the sampling was measured rather than assumed.

### Summary statistics

Unchanged. `metrics.summary_stats` on the **full filtered selection**, not the
sample.

---

## Documentation and tests

`chart_info.py` holds one `ChartInfo` per visualisation — 31 entries — carrying the
plain-English summary, the step-by-step method, a glossary selection, the dataset
and columns, the calculation, the axes, the legend, limitations and validation.
`ci.header(key)` renders the heading, the RAW/CLEANED/DERIVED badge and the ⓘ.
A module-level guard raises at import time if any entry lacks plain-English steps,
and `tests/verify_dubai_changes.py` asserts that the set of keys used on the page
and the set in the registry are identical — so a chart can never be added or
removed without its documentation following.

| Suite | Result |
|---|---|
| `python tests/verify_dubai_changes.py` | 210 / 210 |
| `python tests/verify_dubai_numbers.py` | 31 / 31 |
| `python tests/regression.py all` | 27 / 27 views identical to the originals |
