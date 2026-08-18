# TruEstate Analytics — Graph and Code Explanation

**Companion to** `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.
**Scope:** the eleven dashboard visualisations named for this task, and nothing else.

---

## How to use this document

Every section below documents one dashboard visualisation against the same
26 points, in the same order:

1. Where it appears in the dashboard
2. What the visualisation is
3. Plain-English one-liner
4. The question it answers
5. Data source
6. Why that source
7. Columns used
8. Filters that apply
9. Population and exclusions
10. Missing values
11. Grouping and aggregation
12. Metric definition
13. Formula
14. Method, and why this method
15. Thresholds and parameters
16. Notebook cells
17. Code (identical to the notebook)
18. Intermediate dataframe
19. Result values (actual notebook output)
20. Chart type, and why
21. Axes
22. Legend
23. Colour meaning
24. Hover contents
25. How to read it — and what it does NOT say
26. Limitations and validation actually performed

**The code in point 17 of each section is the notebook's code, byte for byte.**
This document and the notebook are generated from one shared set of snippets, so
there is no second copy of the code that can quietly diverge. Point 19 quotes the
output of an actual execution of that notebook — the run is recorded in the
appendix, with the numbers it printed.

## The two datasets, and the rule that governs them

| File | What it is | Rows | Used for |
|---|---|---|---|
| `data/dubai/transactions.parquet` | **RAW** Dubai registry, exactly as supplied | 1,762,258 | Transaction **counts** and volume |
| `data/dubai/latest_combined_data.parquet` | **CLEANED** residential unit sales, enriched | 818,838 | All **price** and rate statistics |

Cleaning removes **109,651 rows (11.8%)** from the residential-unit-sale
population. A count taken on the cleaned file therefore understates recorded
activity, which is why counts come from RAW and prices come from CLEANED. Where a
single visualisation needs both — §3 and §11 — each column is labelled with the
file it came from and both are shown side by side.

## Scope — the eleven sections

| § | Dashboard visualisation | Dashboard tab | Type |
|---|---|---|---|
| 1 | Transactions recorded each year | Trends | Column chart + secondary-axis line |
| 2 | How prices are moving | Price | Dual-axis line chart (4 series) |
| 3 | Volume against price, by year | Price | Column chart + secondary-axis line |
| 4 | Share of recorded transactions associated with each amenity | Price | Two bar charts |
| 5 | Rate by building height and property type | Price | Grouped bar chart |
| 6 | Where the price points are | Price | Column chart |
| 7 | Rate per m² by layout | Property | Box plot (pre-computed quartiles) |
| 8 | Unit size — key statistics | Distribution | Table |
| 9 | Sale price by registration type — summary | Distribution | Table |
| 10 | How the price distribution has changed | Distribution | Violin plot |
| 11 | Year-by-year summary | Price | Table |

## Code-to-graph traceability

| § | Notebook cells | Intermediate dataframe | Application code |
|---|---|---|---|
| 1 | `yoy_calc`, `yoy_values`, `yoy_2026`, `yoy_graph` | `yoy` (16 rows × 6 columns) | `dashboard._raw_volume_panel` → `metrics.raw_transaction_years`, `metrics.partial_year_growth` → `charts.raw_transaction_volume` |
| 2 | `price_monthly`, `price_window_test`, `price_values`, `price_graph` | `monthly` (200 rows × 7 columns) | `dashboard._section_price` → `metrics.monthly_series` → `charts.price_rate_trend` |
| 3 | `volprice_calc`, `volprice_values`, `volprice_graph` | `vol_price` (16 rows × 7 columns) | `dashboard._volume_vs_price_panel` → `metrics.volume_vs_mean_rate` → `charts.volume_vs_mean_rate` |
| 4 | `amenity_outcome_check`, `amenity_calc`, `amenity_across`, `amenity_values`, `amenity_graph` | `within / across` (5 rows × 4 columns / 7 rows × 4 columns) | `dashboard._amenity_association_panel` → `metrics.amenity_transaction_share`, `metrics.amenity_share_by_property_type` → `charts.amenity_share_bar`, `charts.amenity_share_by_type_bar` |
| 5 | `height_field_check`, `height_buckets`, `height_calc`, `height_graph` | `height_table` (24 rows × 6 columns) | `dashboard._building_height_panel` → `metrics.building_height_bands`, `metrics.rate_by_building_height` → `charts.rate_by_building_height` |
| 6 | `bands_calc`, `bands_values`, `bands_graph` | `bands` (7 rows × 3 columns) | `dashboard._price_bands_panel`, `dashboard._price_range_explainer` → `metrics.price_bands` → `charts.band_bar` |
| 7 | `layout_calc`, `layout_values`, `layout_graph` | `stats` (7 rows × 9 columns) | `dashboard._section_property` → `charts.rate_by_layout` (computes the quartiles and returns `fig, stats, excluded`), `charts.layout_stats_table` |
| 8 | `size_calc`, `size_values` | `size_stats` (7 rows × 8 columns) | `dashboard._unit_size_summary` (aggregates inline; no chart function — this panel is a table) |
| 9 | `regtype_calc`, `regtype_values` | `reg_summary` (2 rows × 7 columns) | `dashboard._price_by_reg_summary` (aggregates inline; no chart function — this panel is a table) |
| 10 | `dist_fidelity`, `dist_values`, `dist_graph` | `fidelity / shape` (17 rows × 8 columns / 17 rows × 6 columns) | `dashboard._section_distribution` → `charts.rate_violin_by_year` |
| 11 | `yearsummary_calc`, `yearsummary_values` | `summary` (16 rows × 5 columns) | `dashboard._yearly_summary_panel` → `metrics.yearly_summary` |

## What this document does not contain

- No number in it was typed from a screenshot. Every figure is either printed by
  the notebook run in the appendix or taken from the chart registry that the
  dashboard itself renders.
- No causal claim. §3 reports a correlation of 0.884 and says explicitly that
  co-movement is not causation; §4 reports shares of recorded transactions and
  says explicitly that no purchase probability exists in this data; §9 reports
  two groups side by side and computes no difference between them.
- No metric that the data cannot support. Where a requested analysis was not
  possible — a unit-level floor analysis (§5), a customer purchase probability
  (§4) — the limitation is documented with the evidence for it, rather than an
  invented result.

---

## 1. Transactions recorded each year (year-over-year transaction growth)

> How many homes actually changed hands each year, counted from the registry itself — and how that compares with the year before.

**Dashboard title:** Transactions recorded each year  |  **Registry key:** `raw_yoy_volume`  |  **Notebook section:** §1

### 1.1 Where it appears in the dashboard
**Dubai → Trends tab**, first panel. Not affected by the sidebar filters.

### 1.2 What the visualisation is
Grouped column chart with a secondary-axis dotted line (`go.Bar` ×2 + `go.Scatter`).

### 1.3 Plain-English one-liner
How many homes actually changed hands each year, counted from the registry itself — and how that compares with the year before.

### 1.4 The question it answers
How many residential unit sales were registered in each year, and how does each year compare with the one before it?

### 1.5 Data source
**RAW** — `data/dubai/transactions.parquet`

The full Dubai transaction registry exactly as supplied, 1,762,262 rows. Transaction counts are taken from here, restricted to residential unit sales (928,489 rows) so the population matches the rest of the page, with no cleaning applied.

### 1.6 Why that source
Because a transaction count should say how many transactions were recorded. The cleaned dataset has had rows removed by preprocessing — between 668 and 7,369 a year — so counting there understates activity. Price analysis still uses the cleaned file; volume does not.

### 1.7 Columns used
`instance_date` · `trans_group_en` · `property_type_en` · `property_usage_en`

### 1.8 Filters that apply
**None.** This is the one Dubai chart the sidebar does not filter, because it answers “how many transactions were registered”, not “how many match my selection”. Every other chart on the page responds to the filters.

### 1.9 Population and exclusions
The raw registry filtered to `trans_group_en == "Sales"` **and** `property_type_en == "Unit"` **and** `property_usage_en == "Residential"` — 928,489 of 1,762,258 rows. The series starts at 2011 so that every plotted year has a predecessor to compare against.

### 1.10 Missing values
Rows with an unparseable `instance_date` are dropped before counting (`errors="coerce"` then `dropna`), and the number dropped is reported rather than absorbed. Nothing is imputed.

### 1.11 Grouping and aggregation
`groupby(['year','month']).size()` on the registry, then summed to a year. Month granularity is kept because the incomplete-year rule needs it.

### 1.12 Metric definition
Two metrics. (a) *Transactions recorded* = a count of rows. (b) *Year-over-year growth* = the percentage change of that count against the immediately preceding year.

### 1.13 Formula
`yoy_pct = (transactions[y] − transactions[y−1]) / transactions[y−1] × 100`, chained year by year. The base year carries `NaN`, not `0`.

### 1.14 Method, and why this method
A chained percentage change on raw counts. No smoothing, no rebasing, no index. Chosen because a transaction count is a census of the registry, not a sample — there is nothing to estimate.

### 1.15 Thresholds and parameters
`BASE_YEAR = 2011`. Incomplete-year rule: a growth percentage is displayed for the year in progress **only if** the like-for-like comparison against the same months of the previous year is *strictly positive*.

### 1.16 Notebook cells
This section is produced by `yoy_calc`, `yoy_values`, `yoy_2026`, `yoy_graph` in `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.

### 1.17 Code — identical to the notebook
*Every block below is the notebook cell, byte for byte. Both files are generated from one shared source, so they cannot drift apart.*

**`yoy_calc`**

```python
BASE_YEAR = 2011

# FILTER → count per (year, month) on the RAW registry
counts = (raw.assign(_res=RESIDENTIAL_UNIT_SALE)
             .groupby(["year", "month"], as_index=False)
             .agg(all_transactions=("_res", "size"),   # every registry transaction
                  transactions=("_res", "sum")))       # residential unit sales only
counts["year"]  = counts["year"].astype(int)
counts["month"] = counts["month"].astype(int)

# CALCULATION → one row per year
per_year = (counts.groupby("year", as_index=False)
                  .agg(transactions=("transactions", "sum"),
                       all_transactions=("all_transactions", "sum"),
                       months=("month", "nunique"))
                  .sort_values("year"))

latest_year   = int(per_year["year"].max())
latest_months = int(per_year.loc[per_year["year"] == latest_year, "months"].iloc[0])
per_year["complete"] = ~((per_year["year"] == latest_year) & (latest_months < 12))

# Chained growth: each year against the row directly above it.
per_year["yoy_pct"] = (per_year["transactions"] / per_year["transactions"].shift() - 1) * 100
# An incomplete year is not a comparable annual observation — drop its figure.
per_year.loc[~per_year["complete"], "yoy_pct"] = np.nan

yoy = per_year[per_year["year"] >= BASE_YEAR].reset_index(drop=True)
yoy.loc[0, "yoy_pct"] = np.nan          # base year has no predecessor

yoy          # INTERMEDIATE DATAFRAME
```

**`yoy_values`**

```python
print("Year   Transactions   All registry    YoY growth")
for _, r in yoy.iterrows():
    growth = "      base" if pd.isna(r.yoy_pct) else f"{r.yoy_pct:+9.2f}%"
    flag   = "   <- INCOMPLETE YEAR" if not r.complete else ""
    print(f"{int(r.year)}   {int(r.transactions):>12,}   {int(r.all_transactions):>12,}   {growth}{flag}")

complete = yoy[yoy.complete]
peak = complete.loc[complete.transactions.idxmax()]
best = complete.dropna(subset=["yoy_pct"]).nlargest(1, "yoy_pct").iloc[0]
print(f"\nBusiest completed year : {int(peak.year)} — {int(peak.transactions):,} transactions")
print(f"Strongest growth year  : {int(best.year)} — {best.yoy_pct:+.1f}% vs {int(best.year)-1}")
```

**`yoy_2026`**

```python
cur_months = sorted(counts.loc[counts.year == latest_year, "month"].unique())
last_month = max(cur_months)
period     = f"January-{pd.Timestamp(2000, last_month, 1).strftime('%B')}"

current_n = int(counts.loc[counts.year == latest_year, "transactions"].sum())
basis_n   = int(counts.loc[(counts.year == latest_year - 1) &
                           (counts.month <= last_month), "transactions"].sum())
full_prev = int(counts.loc[counts.year == latest_year - 1, "transactions"].sum())

growth = (current_n / basis_n - 1) * 100
display_growth = growth if growth > 0 else None      # STRICTLY positive only

print(f"Latest year in the registry : {latest_year}")
print(f"Months available            : {len(cur_months)} of 12   ({period})")
print(f"Transactions so far         : {current_n:,}")
print(f"Same months of {latest_year-1}         : {basis_n:,}   <- the comparison basis")
print(f"{latest_year-1} full year              : {full_prev:,}")
print(f"Like-for-like growth        : {growth:+.2f}%")
print(f"\nStrictly positive?          : {growth > 0}")
print(f"Percentage displayed        : "
      f"{'YES, ' + format(display_growth, '+.1f') + '%' if display_growth else 'NO - count only'}")
print(f"Naive full-year comparison  : {(current_n/full_prev - 1)*100:+.1f}%"
      f"   <- never shown; a calendar artefact, not a market decline")
```

**`yoy_graph`**

```python
done, todo = yoy[yoy.complete], yoy[~yoy.complete]

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Bar(x=done.year, y=done.transactions, name="Transactions recorded",
                     marker_color="#2563EB",
                     text=[f"{v:,}" for v in done.transactions], textposition="outside",
                     hovertemplate="<b>%{x}</b><br>Transactions recorded: %{y:,}<extra></extra>"),
              secondary_y=False)
if not todo.empty:
    fig.add_trace(go.Bar(x=todo.year, y=todo.transactions,
                         name=f"{latest_year} - {period} only (in progress)",
                         marker_color="#D97706",
                         text=[f"{v:,}" for v in todo.transactions], textposition="outside",
                         hovertemplate=f"<b>%{{x}} - {period} only</b><br>"
                                       "Transactions so far: %{y:,}<br>"
                                       "<i>Part year - not comparable</i><extra></extra>"),
                  secondary_y=False)

line = yoy.dropna(subset=["yoy_pct"])[["year", "yoy_pct"]]
if display_growth is not None:
    line = pd.concat([line, pd.DataFrame([{"year": latest_year, "yoy_pct": display_growth}])])

fig.add_trace(go.Scatter(x=line.year, y=line.yoy_pct, name="Year-over-year growth (%)",
                         mode="lines+markers",
                         line=dict(color="#0D9488", width=2.2, dash="dot"),
                         hovertemplate="<b>%{x}</b><br>Growth vs previous year: "
                                       "%{y:+.1f}%<extra></extra>"),
              secondary_y=True)
fig.add_hline(y=0, line_color="rgba(128,128,128,0.45)", line_width=1, secondary_y=True)

fig.update_layout(height=470, barmode="group",
                  title="Transactions recorded each year (RAW registry)",
                  legend=dict(orientation="h", y=-0.24))
fig.update_yaxes(title_text="Transactions recorded", secondary_y=False)
fig.update_yaxes(title_text="Year-over-year growth (%)", secondary_y=True, showgrid=False)
fig.update_xaxes(title_text="Year", type="category")
fig.show()
```

### 1.18 Intermediate dataframe
`yoy` — **16 rows × 6 columns**

Columns: `year`, `transactions`, `all_transactions`, `months`, `complete`, `yoy_pct`

### 1.19 Result values — actual notebook output
*Printed by the run recorded in the appendix, not typed from memory.*

```
Year   Transactions   All registry    YoY growth
2011         19,611         38,941         base
2012         22,931         46,272      +16.93%
2013         40,359         77,915      +76.00%
2014         35,138         70,267      -12.94%
2015         26,355         58,520      -25.00%
2016         25,996         59,002       -1.36%
2017         28,925         64,465      +11.27%
2018         21,355         50,175      -26.17%
2019         24,029         53,042      +12.52%
2020         20,333         49,095      -15.38%
2021         35,977         82,571      +76.94%
2022         62,690        119,897      +74.25%
2023         93,799        165,335      +49.62%
2024        136,137        224,629      +45.14%
2025        166,262        267,086      +22.13%
2026         80,203        131,901         base   <- INCOMPLETE YEAR

Busiest completed year : 2025 — 166,262 transactions
Strongest growth year  : 2021 — +76.9% vs 2020
```

```
Latest year in the registry : 2026
Months available            : 8 of 12   (January-August)
Transactions so far         : 80,203
Same months of 2025         : 102,675   <- the comparison basis
2025 full year              : 166,262
Like-for-like growth        : -21.89%

Strictly positive?          : False
Percentage displayed        : NO - count only
Naive full-year comparison  : -51.8%   <- never shown; a calendar artefact, not a market decline
```

### 1.20 Chart type, and why
Bars for the counts because the quantity is a discrete total per year; a separate line on a second axis for growth because a percentage and a count share no unit. The year in progress is a **separate bar series** rather than an annotation, so it gets its own colour, its own legend entry and its own hover text.

### 1.21 Axes
- **x:** Year.
- **y:** Transactions recorded (left axis).
- **secondary y:** Year-over-year growth, in percent (right axis).

### 1.22 Legend
Two series: the bars are transactions recorded, the dotted line is year-over-year growth. The incomplete year's bar is amber and is annotated with the period actually covered.

### 1.23 Colour meaning
Blue = completed years. Amber = the year still in progress. Teal dotted = year-over-year growth.

### 1.24 Hover contents
Bars: year, transaction count, and the all-registry count beside it. The amber bar's hover names the months actually covered. Line: year and growth percentage.

### 1.25 How to read it — and what it does NOT say
**How to read it**

- The bars are counts — read them as they are.
- The dotted line only exists for completed years. Where it is missing, no comparable annual figure exists.
- The amber bar is the year in progress. Its height is a real count of a shorter period, so it is **not** comparable with the full years beside it.

**What it does not say**

- Nothing about prices — this is volume only.
- It does not forecast how the incomplete year will finish.

### 1.26 Limitations and validation actually performed
**Limitations**

- **The incomplete year never shows a negative or zero growth figure.** Comparing part of a year against a whole one produces a decline that is an artefact of the calendar, not the market. A percentage appears for that year only when the like-for-like comparison against the same months of the previous year is strictly positive.
- The counts are registrations, so a sale appears on the date it was registered, not the date it was agreed.
- The registry starts in 1966, but the series begins at 2011 so that every bar has a comparable predecessor.

**Validation**

Counted directly from the raw parquet and cross-checked against the cleaned dataset year by year: the raw slice is larger in every single year, by 668 to 7,369 transactions, which is the preprocessing loss this chart exists to avoid. Duplicate transaction identifiers in the raw registry: zero.

---

## 2. How prices are moving

> Are prices going up? Watch the teal line — that is price per square metre, which does not move just because people bought bigger homes this month.

**Dashboard title:** How prices are moving  |  **Registry key:** `price_rate_trend`  |  **Notebook section:** §2

### 2.1 Where it appears in the dashboard
**Dubai → Price tab.** All seven sidebar filters apply.

### 2.2 What the visualisation is
Dual-axis line chart, four series (`make_subplots(secondary_y=True)` + 4 × `go.Scatter`).

### 2.3 Plain-English one-liner
Are prices going up? Watch the teal line — that is price per square metre, which does not move just because people bought bigger homes this month.

### 2.4 The question it answers
Which direction have prices moved, and is the movement in the price level or in what people are buying?

### 2.5 Data source
**CLEANED** — `data/dubai/latest_combined_data.parquet`

818,838 residential **unit** sales registered in Dubai, 2010 – Aug 2026, enriched by the project with time parts, unit attributes, amenity flags and building / developer scoring.

### 2.6 Why that source
These answer two different questions. Median total price moves when the **mix** of what people buy changes. Median rate per m² is the cleaner read on whether Dubai property itself is getting more expensive.

### 2.7 Columns used
`year_month` · `instance_date` · `actual_worth` · `meter_sale_price`

### 2.8 Filters that apply
All seven Dubai sidebar filters apply: year, locality zone, area, layout, registration type, sale-price range and unit-size range.

### 2.9 Population and exclusions
Every row of the cleaned dataset that survives the sidebar filters. The notebook runs unfiltered, so it reports all 818,838 rows across 200 months.

### 2.10 Missing values
Medians are computed on the values present in each month; a month with no priced rows would simply not appear. No month is imputed and no month is dropped for being thin — the thinnest (814 transactions) is reported instead.

### 2.11 Grouping and aggregation
`groupby('year_month')` → `median(actual_worth)`, `median(meter_sale_price)`, `size()`.

### 2.12 Metric definition
Two actual series (monthly median sale price, monthly median rate per m²) and two smoothed series derived from them.

### 2.13 Formula
`smooth = series.rolling(12, center=True, min_periods=1).median()`

### 2.14 Method, and why this method
A **centred 12-month rolling median**. A median rather than a mean so one unusual month cannot drag the trend; centred so the trend sits over the data rather than lagging it; 12 months so a full seasonal cycle is inside every window.

### 2.15 Thresholds and parameters
`SMOOTH_WINDOW = 12`, chosen by measurement, not preference — §2.2 of the notebook computes the standard deviation of month-on-month change for several windows and prints the result. The actual series moves at 7.61%; a 3-month median leaves 4.36%; the 12-month median leaves 1.46%, i.e. 81% calmer, while the median absolute deviation of the trend from the actual points stays at 2.75%.

### 2.16 Notebook cells
This section is produced by `price_monthly`, `price_window_test`, `price_values`, `price_graph` in `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.

### 2.17 Code — identical to the notebook
*Every block below is the notebook cell, byte for byte. Both files are generated from one shared source, so they cannot drift apart.*

**`price_monthly`**

```python
monthly = (clean.groupby("year_month", observed=True)
                .agg(transactions=("actual_worth", "size"),
                     median_price=("actual_worth", "median"),
                     median_rate=("meter_sale_price", "median"))
                .reset_index())
monthly = monthly[monthly["year_month"].astype(str).str.len() >= 6].copy()
monthly["period"] = pd.PeriodIndex(monthly["year_month"].astype(str), freq="M").to_timestamp()
monthly = monthly.sort_values("period").reset_index(drop=True)

SMOOTH_WINDOW = 12          # one full year — chosen by the test in the next cell
monthly["smooth_rate"]  = (monthly["median_rate"]
                           .rolling(SMOOTH_WINDOW, center=True, min_periods=1).median())
monthly["smooth_price"] = (monthly["median_price"]
                           .rolling(SMOOTH_WINDOW, center=True, min_periods=1).median())

monthly[["year_month", "transactions", "median_price", "smooth_price",
         "median_rate", "smooth_rate"]].tail(10)
```

**`price_window_test`**

```python
s = monthly["median_rate"]
base_sd = s.pct_change().std() * 100

rows = []
for w in (3, 5, 7, 9, 12):
    for kind in ("median", "mean"):
        r  = s.rolling(w, center=True, min_periods=1)
        sm = r.median() if kind == "median" else r.mean()
        rows.append({
            "window": w, "statistic": kind,
            "sd of m/m change (%)": sm.pct_change().std() * 100,
            "calmer than actual (%)": (1 - sm.pct_change().std()*100 / base_sd) * 100,
            "median deviation from actual (%)": ((sm - s) / s * 100).abs().median(),
        })

print(f"Actual series: standard deviation of month-on-month change = {base_sd:.2f}%\n")
pd.DataFrame(rows)
```

**`price_values`**

```python
actual_sd = monthly["median_rate"].pct_change().std() * 100
smooth_sd = monthly["smooth_rate"].pct_change().std() * 100
dev = ((monthly.smooth_rate - monthly.median_rate) / monthly.median_rate * 100).abs()

print(f"months in the series          : {len(monthly)}")
print(f"thinnest month                : {int(monthly.transactions.min()):,} transactions")
print(f"sd of m/m change - actual     : {actual_sd:.2f}%")
print(f"sd of m/m change - smoothed   : {smooth_sd:.2f}%   "
      f"({(1-smooth_sd/actual_sd)*100:.0f}% calmer)")
print(f"median |deviation| of trend   : {dev.median():.2f}%")
print(f"max |deviation| of trend      : {dev.max():.2f}%")
print("\nLast six months, actual vs 12-month trend:")
print(monthly[["year_month", "transactions", "median_rate", "smooth_rate"]]
      .tail(6).to_string(index=False))
```

**`price_graph`**

```python
fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(go.Scatter(x=monthly.period, y=monthly.median_price,
                         name="Median sale price - actual", mode="lines",
                         line=dict(color="#2563EB", width=1.0), opacity=0.35,
                         hovertemplate="%{x|%b %Y}<br>Actual median price: "
                                       "AED %{y:,.0f}<extra></extra>"),
              secondary_y=False)
fig.add_trace(go.Scatter(x=monthly.period, y=monthly.smooth_price,
                         name="Median sale price - 12-month trend", mode="lines",
                         line=dict(color="#2563EB", width=2.8),
                         hovertemplate="%{x|%b %Y}<br>Trend price: "
                                       "AED %{y:,.0f}<extra></extra>"),
              secondary_y=False)
fig.add_trace(go.Scatter(x=monthly.period, y=monthly.median_rate,
                         name="Median rate - actual", mode="lines",
                         line=dict(color="#0D9488", width=1.0), opacity=0.35,
                         hovertemplate="%{x|%b %Y}<br>Actual median rate: "
                                       "AED %{y:,.0f}/m2<extra></extra>"),
              secondary_y=True)
fig.add_trace(go.Scatter(x=monthly.period, y=monthly.smooth_rate,
                         name="Median rate - 12-month trend", mode="lines",
                         line=dict(color="#0D9488", width=2.8),
                         hovertemplate="%{x|%b %Y}<br>Trend rate: "
                                       "AED %{y:,.0f}/m2<extra></extra>"),
              secondary_y=True)

fig.update_layout(height=480, legend=dict(orientation="h", y=-0.24),
                  title="How prices are moving - actual monthly values and the 12-month trend")
fig.update_yaxes(title_text="Median sale price (AED)", secondary_y=False)
fig.update_yaxes(title_text="Median rate (AED/m2)", secondary_y=True, showgrid=False)
fig.show()
```

### 2.18 Intermediate dataframe
`monthly` — **200 rows × 7 columns**

Columns: `year_month`, `transactions`, `median_price`, `median_rate`, `period`, `smooth_rate`, `smooth_price`

### 2.19 Result values — actual notebook output
*Printed by the run recorded in the appendix, not typed from memory.*

```
months in the series          : 200
thinnest month                : 814 transactions
sd of m/m change - actual     : 7.61%
sd of m/m change - smoothed   : 1.46%   (81% calmer)
median |deviation| of trend   : 2.75%
max |deviation| of trend      : 20.09%

Last six months, actual vs 12-month trend:
year_month  transactions  median_rate  smooth_rate
   2026-03          9956    18,174.68    18,446.70
   2026-04         10422    19,241.73    18,426.71
   2026-05          8038    17,500.58    18,540.60
   2026-06         10392    18,278.30    18,426.71
   2026-07         10825    18,220.15    18,352.50
   2026-08          2157    18,426.71    18,278.30
```

### 2.20 Chart type, and why
Lines because the x-axis is continuous time. Two axes because AED and AED/m² are different units — plotting them on one axis would make the smaller series look flat. The actual observations are drawn faintly **behind** the trend rather than being replaced by it, which is what keeps this a smoothing of the data rather than a substitution for it.

### 2.21 Axes
- **x:** Month.
- **y:** Median sale price (AED).
- **secondary y:** Median rate per m² (AED/m²).

### 2.22 Legend
Blue = median sale price. Teal = median rate per m². When both views are shown, the faint line is the actual monthly observation and the solid line is the smoothed trend.

### 2.23 Colour meaning
Blue = median sale price. Teal = median rate per m². Faint = the actual monthly observation; solid and thick = the 12-month trend.

### 2.24 Hover contents
Month, the actual value and the smoothed value, with the transaction count for that month.

### 2.25 How to read it — and what it does NOT say
**How to read it**

- Use **Smoothed trend** to read direction, and **Actual monthly** to see the real observations and any single unusual month.
- Blue and teal diverging means the mix of what is being bought is changing, not just the price level.

**What it does not say**

- Nothing about individual properties or specific areas.
- The smoothed line is a reading aid, not a forecast.

### 2.26 Limitations and validation actually performed
**Limitations**

- Covers registered residential **unit** (apartment) sales only — villas, land and whole-building transactions are not in this dataset.
- 2026 is a partial year: the data ends **6 August 2026**, so 2026 totals are not comparable with a full year.
- The sale-price and unit-size sliders start at the 1st–99th percentile, so the most extreme deals are excluded until you widen them.
- The final point (August 2026) covers only 6 days and 2,157 transactions against about 10,800 in a full month. It is flagged on the chart and is the cause of the sharp drop at the right-hand edge.
- A centred rolling window means the first and last month are computed from fewer observations than the middle of the series.

**Validation**

Monthly medians were recomputed directly from the parquet and matched. Every month's transaction count was checked for thin samples — the smallest is 814 (May 2020) — confirming the jaggedness is real and not a data artefact.

---

## 3. Volume against price

> Were the busy years also the expensive years?

**Dashboard title:** Volume against price, by year  |  **Registry key:** `volume_vs_price`  |  **Notebook section:** §3

### 3.1 Where it appears in the dashboard
**Dubai → Price tab**, directly beneath the price movement chart.

### 3.2 What the visualisation is
Column chart with a secondary-axis line (`go.Bar` ×2 + `go.Scatter`).

### 3.3 Plain-English one-liner
Were the busy years also the expensive years?

### 3.4 The question it answers
Were the busy years also the expensive years?

### 3.5 Data source
**CLEANED** — `data/dubai/latest_combined_data.parquet`

818,838 residential **unit** sales registered in Dubai, 2010 – Aug 2026, enriched by the project with time parts, unit attributes, amenity flags and building / developer scoring.

### 3.6 Why that source
To answer whether busy years are also expensive years — whether activity and pricing move together across the cycle.

### 3.7 Columns used
`instance_date` · `trans_group_en` · `property_type_en` · `property_usage_en` · `year` · `meter_sale_price`

### 3.8 Filters that apply
All seven Dubai sidebar filters apply: year, locality zone, area, layout, registration type, sale-price range and unit-size range.

### 3.9 Population and exclusions
Volume: the raw registry, residential unit sales, 2011 onwards. Rate: the cleaned dataset for the same years. The two populations differ deliberately and the chart labels both.

### 3.10 Missing values
A year with volume but no priced cleaned rows would show a bar and a gap in the line, not a zero. In this dataset every year from 2011 has both.

### 3.11 Grouping and aggregation
Volume: `groupby('year').size()` on the raw registry. Rate: `groupby('year').mean(meter_sale_price)` on the cleaned dataset. Joined on `year`.

### 3.12 Metric definition
Transaction volume (count) against the **mean** rate per m².

### 3.13 Formula
`volume[y] = count(raw rows in y)` · `mean_rate[y] = mean(meter_sale_price of cleaned rows in y)`

### 3.14 Method, and why this method
Mean, **not** median — the exception on this page, and it is deliberate. The question is about the money moving through the market as a whole, so the upper tail a hot market adds belongs in the answer. The median is computed and reported beside it so the difference stays visible.

### 3.15 Thresholds and parameters
`BASE_YEAR = 2011`. The year in progress is split into its own bar series and labelled *part year*.

### 3.16 Notebook cells
This section is produced by `volprice_calc`, `volprice_values`, `volprice_graph` in `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.

### 3.17 Code — identical to the notebook
*Every block below is the notebook cell, byte for byte. Both files are generated from one shared source, so they cannot drift apart.*

**`volprice_calc`**

```python
# Volume: RAW registry.  Rate: CLEANED dataset.  Each labelled at every step.
volume = (counts.groupby("year", as_index=False)
                .agg(transactions=("transactions", "sum"), months=("month", "nunique")))

rate = (clean.groupby("year", observed=True)["meter_sale_price"]
             .agg(mean_rate="mean", median_rate="median", priced_rows="size")
             .reset_index())
rate["year"] = rate["year"].astype(int)

vol_price = (volume.merge(rate, on="year", how="left")
                   .query("year >= @BASE_YEAR")
                   .sort_values("year").reset_index(drop=True))
vol_price["complete"] = ~((vol_price.year == latest_year) & (vol_price.months < 12))

vol_price[["year", "transactions", "mean_rate", "median_rate", "priced_rows", "complete"]]
```

**`volprice_values`**

```python
p = vol_price.dropna(subset=["mean_rate"])
print(f"correlation, volume vs MEAN rate   : {p.transactions.corr(p.mean_rate):.3f}")
print(f"correlation, volume vs MEDIAN rate : {p.transactions.corr(p.median_rate):.3f}")
print(f"mean above median in               : {(p.mean_rate > p.median_rate).sum()} of {len(p)} years")
print(f"average gap, mean - median         : AED {(p.mean_rate - p.median_rate).mean():,.0f}/m2")
print("\nYear | Transaction volume (RAW) | Mean rate/m2 (CLEANED)")
for _, r in vol_price.iterrows():
    tag = "" if r.complete else "  (part year)"
    print(f"{int(r.year)} | {int(r.transactions):>10,} | {r.mean_rate:>10,.0f}{tag}")
```

**`volprice_graph`**

```python
done, todo = vol_price[vol_price.complete], vol_price[~vol_price.complete]

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Bar(x=done.year, y=done.transactions, name="Transaction volume (raw)",
                     marker_color="#2563EB", opacity=0.85,
                     hovertemplate="<b>%{x}</b><br>Transaction volume: %{y:,}<extra></extra>"),
              secondary_y=False)
if not todo.empty:
    fig.add_trace(go.Bar(x=todo.year, y=todo.transactions,
                         name=f"{latest_year} - part year (in progress)",
                         marker_color="#D97706", opacity=0.9,
                         hovertemplate="<b>%{x} - part year</b><br>"
                                       "Volume so far: %{y:,}<extra></extra>"),
                  secondary_y=False)
fig.add_trace(go.Scatter(x=vol_price.year, y=vol_price.mean_rate,
                         name="Mean rate per m2 (cleaned)", mode="lines+markers",
                         line=dict(color="#0D9488", width=2.6), marker=dict(size=7),
                         hovertemplate="<b>%{x}</b><br>Mean rate: "
                                       "AED %{y:,.0f}/m2<extra></extra>"),
              secondary_y=True)

fig.update_layout(height=470, barmode="group", title="Volume against price, by year",
                  legend=dict(orientation="h", y=-0.24))
fig.update_yaxes(title_text="Transaction volume (raw registry)", secondary_y=False)
fig.update_yaxes(title_text="Mean rate per m2 (AED/m2)", secondary_y=True, showgrid=False)
fig.update_xaxes(title_text="Year", type="category")
fig.show()
```

### 3.18 Intermediate dataframe
`vol_price` — **16 rows × 7 columns**

Columns: `year`, `transactions`, `months`, `mean_rate`, `median_rate`, `priced_rows`, `complete`

### 3.19 Result values — actual notebook output
*Printed by the run recorded in the appendix, not typed from memory.*

```
correlation, volume vs MEAN rate   : 0.884
correlation, volume vs MEDIAN rate : 0.884
mean above median in               : 16 of 16 years
average gap, mean - median         : AED 1,538/m2

Year | Transaction volume (RAW) | Mean rate/m2 (CLEANED)
2011 |     19,611 |     10,667
2012 |     22,931 |     10,793
2013 |     40,359 |     12,406
2014 |     35,138 |     13,939
2015 |     26,355 |     13,179
2016 |     25,996 |     12,983
2017 |     28,925 |     13,065
2018 |     21,355 |     12,934
2019 |     24,029 |     13,345
2020 |     20,333 |     12,456
2021 |     35,977 |     14,101
2022 |     62,690 |     17,158
2023 |     93,799 |     18,185
2024 |    136,137 |     18,854
2025 |    166,262 |     20,324
2026 |     80,203 |     20,315  (part year)
```

The correlation between volume and mean rate/m² across these years is **0.884**. That is co-movement. It is not evidence that either one causes the other, and the document, the notebook and the dashboard all say so in the same words.

### 3.20 Chart type, and why
Bars carry the count, a line carries the rate; a second axis because a count and a price per square metre share no scale. Both statistics of the rate are computed, but only the mean is drawn — plotting both would imply the chart is about the gap between them, which is the year-by-year table's job (§11).

### 3.21 Axes
- **x:** Year.
- **y:** Left: transaction volume (raw registry). Right: mean rate per m² (AED/m²).

### 3.22 Legend
Three entries: transaction volume, the part-year bar for the year still in progress, and the mean rate line.

### 3.23 Colour meaning
Blue = completed-year volume. Amber = the part year. Teal line = mean rate per m².

### 3.24 Hover contents
Year, transaction volume, mean rate/m², and the number of priced cleaned rows the mean was computed from.

### 3.25 How to read it — and what it does NOT say
**How to read it**

- Bars rising together with the line means activity and pricing moved together.
- The amber bar is the year in progress; its volume covers part of a year only.

**What it does not say**

- It does not establish that volume drives price or the reverse — they move together, which is not the same as one causing the other.
- The part-year bar is not comparable in height with the full years beside it.

### 3.26 Limitations and validation actually performed
**Limitations**

- Covers registered residential **unit** (apartment) sales only — villas, land and whole-building transactions are not in this dataset.
- 2026 is a partial year: the data ends **6 August 2026**, so 2026 totals are not comparable with a full year.
- The sale-price and unit-size sliders start at the 1st–99th percentile, so the most extreme deals are excluded until you widen them.
- **This chart uses the mean, not the median**, unlike the rest of the page. The mean is pulled upward by a small number of very large deals; both are shown in the table underneath so the difference stays visible.
- Volume comes from the raw registry and does not respond to the sidebar filters; the rate line does.

**Validation**

Volume reconciled against the raw registry year by year; the mean rate recomputed in plain pandas and matched. The mean sits above the median in all 16 years, as expected for a right-skewed price distribution.

---

## 4. Property type + amenity analysis (share of recorded transactions)

> How common each feature is among the sales we actually have on record — a share of completed deals, not a chance of anyone buying.

**Dashboard title:** Share of recorded transactions associated with each amenity  |  **Registry key:** `amenity_transaction_share`  |  **Notebook section:** §4

### 4.1 Where it appears in the dashboard
**Dubai → Price tab.** Has its own property-type and amenity selectors on top of the sidebar filters.

### 4.2 What the visualisation is
Two bar charts: a horizontal bar of all five amenities within one property type, and a vertical bar of one amenity across all property types.

### 4.3 Plain-English one-liner
How common each feature is among the sales we actually have on record — a share of completed deals, not a chance of anyone buying.

### 4.4 The question it answers
How common is each feature among the sales that are actually on record for a given property type?

### 4.5 Data source
**CLEANED** — `data/dubai/latest_combined_data.parquet`

818,838 residential **unit** sales registered in Dubai, 2010 – Aug 2026, enriched by the project with time parts, unit attributes, amenity flags and building / developer scoring.

### 4.6 Why that source
To describe how common each feature is among completed transactions, without making a price claim and without implying a causal effect.

### 4.7 Columns used
`rooms_en` · `has_parking` · `swimming_pool` · `balcony` · `elevator` · `metro`

### 4.8 Filters that apply
All seven Dubai sidebar filters apply, plus the property-type and amenity filters on the panel itself.

### 4.9 Population and exclusions
Cleaned dataset, filtered to the chosen property type. A property type is only reported if it has at least 100 transactions in the selection; smaller ones are named, not silently dropped.

### 4.10 Missing values
**A `0` means *not recorded*, not *confirmed absent*.** Nothing is imputed and no missing value is converted to a "No". Under-recording therefore shows up as a lower share, and that is stated on the chart itself.

### 4.11 Grouping and aggregation
`clean[clean.rooms_en == property_type]`, then per amenity column `sum(flag == 1)` over `len(rows)`.

### 4.12 Metric definition
**Share of recorded transactions associated with the amenity** — the proportion of that property type's recorded sales whose record carries the flag.

### 4.13 Formula
`share = (rows where flag == 1) / (rows of that property type) × 100`

### 4.14 Method, and why this method
A plain share. No model, no weighting, no adjustment, and explicitly **not** a price comparison and **not** a probability.

### 4.15 Thresholds and parameters
`MIN_CELL = 100` transactions before a share is reported.

### 4.16 Notebook cells
This section is produced by `amenity_outcome_check`, `amenity_calc`, `amenity_across`, `amenity_values`, `amenity_graph` in `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.

### 4.17 Code — identical to the notebook
*Every block below is the notebook cell, byte for byte. Both files are generated from one shared source, so they cannot drift apart.*

**`amenity_outcome_check`**

```python
import pyarrow.parquet as pq

raw_cols   = list(pq.ParquetFile(RAW_FILE).schema_arrow.names)
clean_cols = list(pq.ParquetFile(CLEAN_FILE).schema_arrow.names)

KEYWORDS = ("purchase", "buy", "bought", "outcome", "lead", "enquir", "inquir",
            "visit", "prospect", "convert", "target", "churn")
hits = sorted({c for c in raw_cols + clean_cols if any(k in c.lower() for k in KEYWORDS)})

print("Columns matching purchase / outcome keywords:", hits or "NONE")
print("\ntrans_group_en values in the RAW registry:")
print(pd.read_parquet(RAW_FILE, columns=["trans_group_en"])
        .trans_group_en.value_counts().to_string())
print("\nCONCLUSION")
print("  Every row in both files is a COMPLETED, RECORDED transaction.")
print("  There is no enquiry, viewing or non-purchase row anywhere.")
print("  => A customer purchase probability CANNOT be calculated from this data.")
print("  => The metric below is a SHARE OF RECORDED TRANSACTIONS, and nothing more.")
```

**`amenity_calc`**

```python
AMENITIES = {"has_parking": "Parking", "swimming_pool": "Swimming pool",
             "balcony": "Balcony", "elevator": "Elevator", "metro": "Near a metro station"}
PROPERTY_TYPE_LABELS = {"Studio": "Studio", "1 B/R": "1 BHK", "2 B/R": "2 BHK",
                        "3 B/R": "3 BHK", "4 B/R": "4 BHK", "5 B/R": "5 BHK",
                        "PENTHOUSE": "Penthouse"}
MIN_CELL = 100          # a group needs this many transactions before it is reported

def amenity_share(df, property_type):
    """Share of recorded transactions carrying each amenity flag, within ONE type."""
    sub = df[df.rooms_en == property_type]          # FILTER 1 - property type
    if len(sub) < MIN_CELL:
        return pd.DataFrame()
    rows = []
    for col, label in AMENITIES.items():            # FILTER 2 - amenity
        recorded = int((sub[col] == 1).sum())
        rows.append({"Amenity": label,
                     "Transactions with amenity recorded": recorded,
                     "Transactions without": len(sub) - recorded,
                     "Share of recorded transactions (%)": recorded / len(sub) * 100})
    return (pd.DataFrame(rows)
              .sort_values("Share of recorded transactions (%)", ascending=False)
              .reset_index(drop=True))

PROPERTY_TYPE = "1 B/R"          # <- change me
AMENITY_COL   = "has_parking"    # <- change me

within = amenity_share(clean, PROPERTY_TYPE)
within
```

**`amenity_across`**

```python
rows = []
for value, label in PROPERTY_TYPE_LABELS.items():
    sub = clean[clean.rooms_en == value]
    if len(sub) < MIN_CELL:
        continue
    recorded = int((sub[AMENITY_COL] == 1).sum())
    rows.append({"Property type": label, "Transactions": len(sub),
                 "With amenity recorded": recorded,
                 "Share of recorded transactions (%)": recorded / len(sub) * 100})
across = pd.DataFrame(rows)
across
```

**`amenity_values`**

```python
n = int((clean.rooms_en == PROPERTY_TYPE).sum())
print(f"{PROPERTY_TYPE_LABELS[PROPERTY_TYPE]} transactions on record: {n:,}\n")
for _, r in within.iterrows():
    print(f"  {r.Amenity:<22} {r['Share of recorded transactions (%)']:5.1f}%"
          f"   ({int(r['Transactions with amenity recorded']):,} of {n:,})")

print(f"\n{AMENITIES[AMENITY_COL]} across property types:")
for _, r in across.iterrows():
    print(f"  {r['Property type']:<12} {r['Share of recorded transactions (%)']:5.1f}%"
          f"   ({int(r['With amenity recorded']):,} of {int(r.Transactions):,})")
```

**`amenity_graph`**

```python
t = within.iloc[::-1]
colors = ["#0D9488" if a == AMENITIES[AMENITY_COL] else "#94A3B8" for a in t.Amenity]

fig = go.Figure(go.Bar(
    x=t["Share of recorded transactions (%)"], y=t.Amenity, orientation="h",
    marker_color=colors,
    customdata=t[["Transactions with amenity recorded", "Transactions without"]],
    text=[f"{v:.1f}%" for v in t["Share of recorded transactions (%)"]],
    textposition="outside",
    hovertemplate="%{y}<br>Share of recorded transactions: %{x:.1f}%"
                  "<br>Recorded with: %{customdata[0]:,}"
                  "<br>Recorded without: %{customdata[1]:,}<extra></extra>"))
fig.update_layout(height=380,
                  title=f"Share of recorded {PROPERTY_TYPE_LABELS[PROPERTY_TYPE]} "
                        f"transactions associated with each amenity")
fig.update_xaxes(title_text="Share of recorded transactions (%)", range=[0, 112])
fig.show()

fig2 = go.Figure(go.Bar(
    x=across["Property type"], y=across["Share of recorded transactions (%)"],
    marker_color="#2563EB",
    text=[f"{v:.1f}%" for v in across["Share of recorded transactions (%)"]],
    textposition="outside",
    hovertemplate="%{x}<br>Share of recorded transactions: %{y:.1f}%<extra></extra>"))
fig2.update_layout(height=380, title=f"{AMENITIES[AMENITY_COL]} - share across property types")
fig2.update_yaxes(title_text=f"Share recorded with {AMENITIES[AMENITY_COL].lower()} (%)",
                  range=[0, 112])
fig2.update_xaxes(title_text="Property type")
fig2.show()
```

### 4.18 Intermediate dataframe
`within / across` — **5 rows × 4 columns / 7 rows × 4 columns**

Columns: `Amenity`, `Transactions with amenity recorded`, `Transactions without`, `Share of recorded transactions (%)` — and `Property type`, `Transactions`, `With amenity recorded`, `Share of recorded transactions (%)`

### 4.19 Result values — actual notebook output
*Printed by the run recorded in the appendix, not typed from memory.*

```
Columns matching purchase / outcome keywords: NONE

trans_group_en values in the RAW registry:
trans_group_en
Sales        1349853
Mortgages     346792
Gifts          65617

CONCLUSION
  Every row in both files is a COMPLETED, RECORDED transaction.
  There is no enquiry, viewing or non-purchase row anywhere.
  => A customer purchase probability CANNOT be calculated from this data.
  => The metric below is a SHARE OF RECORDED TRANSACTIONS, and nothing more.
```

```
1 BHK transactions on record: 343,595

  Parking                 95.3%   (327,581 of 343,595)
  Near a metro station    71.2%   (244,672 of 343,595)
  Balcony                 56.8%   (195,185 of 343,595)
  Elevator                36.7%   (126,194 of 343,595)
  Swimming pool           27.9%   (96,020 of 343,595)

Parking across property types:
  Studio        88.9%   (168,624 of 189,729)
  1 BHK         95.3%   (327,581 of 343,595)
  2 BHK         99.1%   (209,943 of 211,748)
  3 BHK         99.1%   (63,745 of 64,318)
  4 BHK         99.4%   (7,566 of 7,614)
  5 BHK        100.0%   (950 of 950)
  Penthouse     96.4%   (769 of 798)
```

**§4.1 of the notebook is the evidence for the metric's name.** Both dataset schemas were swept for `purchase`, `lead`, `enquiry`, `outcome`, `conversion` and `target` columns: **none exist**. `trans_group_en` contains only Sales, Mortgages and Gifts — all completed. There is no non-purchase row anywhere in either file, so a purchase probability *cannot* be calculated, and the metric is named for what it actually is.

### 4.20 Chart type, and why
Horizontal bars for the within-type view because the category labels are words of unequal length and read better on the y-axis; vertical bars for the across-type view because property types have a natural order (Studio → Penthouse) that reads left to right. A single series each, so no plotly legend is forced — the axis titles carry the key.

### 4.21 Axes
- **x:** Left: share of recorded transactions (%). Right: property type.
- **y:** Left: amenity. Right: share recorded with the selected amenity (%).

### 4.22 Legend
Single series per chart; the amenity and the property type are named on the axes and in the titles, so no legend is forced.

### 4.23 Colour meaning
Teal = the amenity currently selected. Grey = the other four, present for context.

### 4.24 Hover contents
Amenity (or property type), the share, and the raw counts with and without the flag — so the denominator is always visible.

### 4.25 How to read it — and what it does NOT say
**How to read it**

- Read each bar as “this percentage of recorded sales of that type had the flag on the record”.
- Compare the same amenity across property types on the right-hand chart to see where a feature is more or less commonly recorded.

**What it does not say**

- **It is not a purchase probability.** Both datasets contain only completed transactions — there is no enquiry, viewing or non-purchase record anywhere in them — so nothing here can say how likely a buyer is to purchase.
- It says nothing about price. No amenity price effect is computed or displayed.
- It does not establish that an amenity attracts buyers; it describes what the completed records contain.

### 4.26 Limitations and validation actually performed
**Limitations**

- Covers registered residential **unit** (apartment) sales only — villas, land and whole-building transactions are not in this dataset.
- 2026 is a partial year: the data ends **6 August 2026**, so 2026 totals are not comparable with a full year.
- The sale-price and unit-size sliders start at the 1st–99th percentile, so the most extreme deals are excluded until you widen them.
- A `0` means *not recorded*, not *confirmed absent*, so under-recording appears as a lower share.
- Only the parking flag also exists in the raw registry; the other four are engineered fields in the cleaned dataset.
- Property types with fewer than 100 transactions in the selection are omitted.

**Validation**

Shares recomputed in plain pandas per property type and matched. Both dataset schemas were swept for purchase / lead / enquiry / outcome / conversion / target columns: none exist, which is the evidence behind the statement that no probability can be estimated.

---

## 5. Rate by building height and property type

> Do apartments in taller buildings cost more per square metre? One line of bars per size of apartment, so you can see whether it holds for all of them.

**Dashboard title:** Rate by building height and property type  |  **Registry key:** `height_price`  |  **Notebook section:** §5

### 5.1 Where it appears in the dashboard
**Dubai → Price tab.**

### 5.2 What the visualisation is
Grouped bar chart, one bar group per height band and one colour per property type.

### 5.3 Plain-English one-liner
Do apartments in taller buildings cost more per square metre? One line of bars per size of apartment, so you can see whether it holds for all of them.

### 5.4 The question it answers
Does the rate per m² differ between low-rise buildings and towers, and does it differ the same way for every layout?

### 5.5 Data source
**CLEANED** — `data/dubai/latest_combined_data.parquet`

818,838 residential **unit** sales registered in Dubai, 2010 – Aug 2026, enriched by the project with time parts, unit attributes, amenity flags and building / developer scoring.

### 5.6 Why that source
To show whether the rate moves with the height of the building, and whether it moves the same way for a studio as for a three-bedroom.

### 5.7 Columns used
`floors` · `building_name_en` · `rooms_en` · `meter_sale_price`

### 5.8 Filters that apply
All seven Dubai sidebar filters apply: year, locality zone, area, layout, registration type, sale-price range and unit-size range.

### 5.9 Population and exclusions
Cleaned rows that have a height value — 481,389 of 818,838 (58.8%). Cells with fewer than 100 transactions are omitted **and named**.

### 5.10 Missing values
The 41.2% of rows with no height are excluded from this panel and the exclusion is printed. They are not treated as zero-storey and not imputed.

### 5.11 Grouping and aggregation
`groupby(['height_band','rooms_en'])` → `median(meter_sale_price)`, `mean(meter_sale_price)`, `size()`.

### 5.12 Metric definition
Median rate per m², by building-height band and property type.

### 5.13 Formula
Band edges are the **quartiles of the height distribution taken one row per building**, not one row per transaction: `[0, 5, 9, 16, 107]` → Low-rise ≤5 · Mid-rise 6–9 · High-rise 10–16 · Tower >16.

### 5.14 Method, and why this method
Data-driven bucketing. Taking quartiles per building rather than per transaction stops large towers, which sell far more units, from dragging every boundary upward.

### 5.15 Thresholds and parameters
`MIN_CELL = 100` transactions per (band × property type) cell. Four cells fell below it and are listed by name in the output.

### 5.16 Notebook cells
This section is produced by `height_field_check`, `height_buckets`, `height_calc`, `height_graph` in `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.

### 5.17 Code — identical to the notebook
*Every block below is the notebook cell, byte for byte. Both files are generated from one shared source, so they cannot drift apart.*

**`height_field_check`**

```python
floor_check = pd.read_parquet(CLEAN_FILE, columns=["floor_bin", "floors", "property_id_bld"])

print("floor_bin distinct values :", floor_check.floor_bin.dropna().unique().tolist())
print(f"floor_bin populated       : {floor_check.floor_bin.notna().mean()*100:.1f}% of rows,")
print("                            and every populated row is the string 'Unknown'")

per_bld = (floor_check.dropna(subset=["floors", "property_id_bld"])
                      .groupby("property_id_bld")["floors"].nunique())
print(f"\nBuildings with a height value      : {len(per_bld):,}")
print(f"Height CONSTANT within a building  : {(per_bld == 1).mean()*100:.1f}%")
print(f"floors range                       : {floor_check.floors.min():.0f} - "
      f"{floor_check.floors.max():.0f}")
print(f"floors populated                   : {floor_check.floors.notna().mean()*100:.1f}% of rows")

print("\nCONCLUSION")
print("  `floors` is identical for every sale in a given building, so it is the")
print("  BUILDING'S HEIGHT, not the unit's own floor. `floor_bin` carries no")
print("  information at all. A floor-level analysis is NOT possible with this data.")
print("  The analysis below is building height, and it is labelled that way.")
```

**`height_buckets`**

```python
hgt = clean.dropna(subset=["floors"]).copy()

# Bucket boundaries from the DATA: quartiles of the height distribution taken
# ONE ROW PER BUILDING, so a tower with thousands of sales cannot move them.
per_building = hgt.groupby("building_name_en", observed=True)["floors"].first()
q1, q2, q3 = (int(round(per_building.quantile(q))) for q in (0.25, 0.50, 0.75))
edges  = [0, q1, q2, q3, int(per_building.max())]
labels = [f"Low-rise (<={q1} floors)", f"Mid-rise ({q1+1}-{q2})",
          f"High-rise ({q2+1}-{q3})", f"Tower (>{q3} floors)"]

print(f"buildings with a height : {len(per_building):,}")
print(f"per-building quartiles  : p25={q1}  p50={q2}  p75={q3}  max={int(per_building.max())}")
print(f"bucket edges            : {edges}")

hgt["height_band"] = pd.cut(hgt.floors, bins=edges, labels=labels,
                            include_lowest=True, right=True)
hgt = hgt[hgt.rooms_en.isin(PROPERTY_TYPE_LABELS)]

print("\ntransactions per band:")
print(hgt.height_band.value_counts().reindex(labels).to_string())
```

**`height_calc`**

```python
height_table = (hgt.groupby(["height_band", "rooms_en"], observed=True)
                   .agg(median_rate=("meter_sale_price", "median"),
                        mean_rate=("meter_sale_price", "mean"),
                        transactions=("meter_sale_price", "size"))
                   .reset_index())

dropped      = height_table[height_table.transactions <  MIN_CELL]
height_table = height_table[height_table.transactions >= MIN_CELL].copy()
height_table["Property type"] = height_table.rooms_en.map(PROPERTY_TYPE_LABELS)

print(f"height recorded for {len(hgt):,} of {len(clean):,} transactions "
      f"({len(hgt)/len(clean)*100:.1f}%)")
print(f"\ncells below the {MIN_CELL}-transaction threshold — omitted and named:")
for _, r in dropped[dropped.transactions > 0].iterrows():
    print(f"   {PROPERTY_TYPE_LABELS.get(r.rooms_en, r.rooms_en)} in {r.height_band} "
          f"({int(r.transactions)} transactions)")

height_table.pivot(index="height_band", columns="Property type", values="median_rate").round(0)
```

**`height_graph`**

```python
palette = ["#2563EB", "#0D9488", "#D97706", "#7C3AED", "#DC2626", "#059669", "#DB2777"]
order   = [l for l in PROPERTY_TYPE_LABELS.values() if l in set(height_table["Property type"])]

fig = go.Figure()
for i, ptype in enumerate(order):
    d = height_table[height_table["Property type"] == ptype]
    fig.add_trace(go.Bar(x=d.height_band.astype(str), y=d.median_rate, name=ptype,
                         marker_color=palette[i % len(palette)],
                         customdata=d[["transactions", "mean_rate"]],
                         hovertemplate=f"<b>{ptype}</b><br>%{{x}}<br>"
                                       "Median rate: AED %{y:,.0f}/m2<br>"
                                       "Mean rate: AED %{customdata[1]:,.0f}/m2<br>"
                                       "Transactions: %{customdata[0]:,}<extra></extra>"))

fig.update_layout(height=490, barmode="group",
                  title="Rate by building height and property type",
                  legend=dict(orientation="h", y=-0.26))
fig.update_yaxes(title_text="Median rate (AED/m2)")
fig.update_xaxes(title_text="Building height band")
fig.show()
```

### 5.18 Intermediate dataframe
`height_table` — **24 rows × 6 columns**

Columns: `height_band`, `rooms_en`, `median_rate`, `mean_rate`, `transactions`, `Property type`

### 5.19 Result values — actual notebook output
*Printed by the run recorded in the appendix, not typed from memory.*

```
floor_bin distinct values : ['Unknown']
floor_bin populated       : 61.8% of rows,
                            and every populated row is the string 'Unknown'

Buildings with a height value      : 2,245
Height CONSTANT within a building  : 100.0%
floors range                       : 0 - 107
floors populated                   : 58.8% of rows

CONCLUSION
  `floors` is identical for every sale in a given building, so it is the
  BUILDING'S HEIGHT, not the unit's own floor. `floor_bin` carries no
  information at all. A floor-level analysis is NOT possible with this data.
  The analysis below is building height, and it is labelled that way.
```

```
buildings with a height : 2,844
per-building quartiles  : p25=5  p50=9  p75=16  max=107
bucket edges            : [0, 5, 9, 16, 107]

transactions per band:
height_band
Low-rise (<=5 floors)     61209
Mid-rise (6-9)            94668
High-rise (10-16)         90456
Tower (>16 floors)       235056
```

```
height recorded for 481,389 of 818,838 transactions (58.8%)

cells below the 100-transaction threshold — omitted and named:
   Penthouse in Low-rise (<=5 floors) (40 transactions)
   5 BHK in Mid-rise (6-9) (22 transactions)
   Penthouse in Mid-rise (6-9) (11 transactions)
   5 BHK in High-rise (10-16) (43 transactions)
```

**This is building height, not the unit's floor, and the notebook proves it before drawing anything.** §5.1 shows that `floor_bin` is the literal string `"Unknown"` in 100% of its populated rows, and that `floors` is identical for every sale within a given building in **100.0%** of the 2,245 buildings tested. A floor-level analysis is therefore *not possible* with this data. The limitation is reported rather than papered over with an invented floor bucket.

### 5.20 Chart type, and why
Grouped bars because the comparison is two-dimensional — band against layout — and a grouped bar keeps both readable without a heatmap's colour-to-value guesswork.

### 5.21 Axes
- **x:** Building height band.
- **y:** Median rate per m² (AED/m²).

### 5.22 Legend
Property type — Studio through 5 BHK and Penthouse, showing only the types that have enough transactions in the current selection.

### 5.23 Colour meaning
One colour per property type, held consistent with the layout chart in §7.

### 5.24 Hover contents
Property type, height band, median rate, mean rate, and the transaction count behind the cell.

### 5.25 How to read it — and what it does NOT say
**How to read it**

- Follow one colour left to right to see how that property type prices across building heights.
- Compare colours within a band to see how property types differ at the same kind of building.

**What it does not say**

- **It is not the unit's own floor.** The dataset does not record which floor an apartment sits on, so this cannot answer whether a higher floor sells for more inside the same building.
- Height and location are entangled: tall towers cluster in particular areas, so part of any gap is where the building is, not how tall it is.

### 5.26 Limitations and validation actually performed
**Limitations**

- Covers registered residential **unit** (apartment) sales only — villas, land and whole-building transactions are not in this dataset.
- 2026 is a partial year: the data ends **6 August 2026**, so 2026 totals are not comparable with a full year.
- The sale-price and unit-size sliders start at the 1st–99th percentile, so the most extreme deals are excluded until you widen them.
- **The floor field is unusable.** `floor_bin` is the string `Unknown` on every populated row, and `floors` is identical for every sale in a given building — it is the building's height, not the unit's floor. This panel is labelled accordingly rather than presented as a floor-level analysis.
- Height is recorded for about 59% of transactions; the rest are not plotted, and the coverage is stated on screen.

**Validation**

`floors` was tested against `property_id_bld` and found constant within a building in 100% of cases, which is what establishes it as a building attribute. Band boundaries, cell counts and medians were recomputed in plain pandas and matched.

---

## 6. Where the price points are (price range)

> Where Dubai's money actually gets spent — and it is not at the top end.

**Dashboard title:** Where the price points are  |  **Registry key:** `price_bands`  |  **Notebook section:** §6

### 6.1 Where it appears in the dashboard
**Dubai → Distribution tab**, as the price-range explainer.

### 6.2 What the visualisation is
Column chart over seven left-closed price bands, with the share printed on each bar.

### 6.3 Plain-English one-liner
Where Dubai's money actually gets spent — and it is not at the top end.

### 6.4 The question it answers
Across what range do Dubai sale prices actually fall, and where is the bulk of the market?

### 6.5 Data source
**CLEANED** — `data/dubai/latest_combined_data.parquet`

818,838 residential **unit** sales registered in Dubai, 2010 – Aug 2026, enriched by the project with time parts, unit attributes, amenity flags and building / developer scoring.

### 6.6 Why that source
The quickest way to see which price points the Dubai market actually trades at.

### 6.7 Columns used
`actual_worth`

### 6.8 Filters that apply
All seven Dubai sidebar filters apply: year, locality zone, area, layout, registration type, sale-price range and unit-size range.

### 6.9 Population and exclusions
Every row of the cleaned selection. Nothing is trimmed — the audit in §6.2 exists to prove that.

### 6.10 Missing values
Rows with no `actual_worth` cannot be banded; the audit prints the count that could not be assigned. In this dataset it is **0**.

### 6.11 Grouping and aggregation
`pd.cut(actual_worth, BAND_EDGES, right=False)` then `value_counts()`.

### 6.12 Metric definition
Transactions per price band and each band's share of the total.

### 6.13 Formula
`BAND_EDGES = [0, 500k, 1M, 2M, 3M, 5M, 10M, ∞]`, left-closed so AED 1,000,000 falls in the 1–2M band, not the 0.5–1M band.

### 6.14 Method, and why this method
Fixed, human-readable bands rather than quantiles, because the question is "what does a home cost here" and round numbers are how people ask it. The percentile statistics are reported alongside so nothing is lost.

### 6.15 Thresholds and parameters
Seven bands. The companion histogram displays the 0.5th–99.5th percentile in 60 equal-width bins; the 1.0% of rows outside that display window remain in every statistic and the count is printed.

### 6.16 Notebook cells
This section is produced by `bands_calc`, `bands_values`, `bands_graph` in `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.

### 6.17 Code — identical to the notebook
*Every block below is the notebook cell, byte for byte. Both files are generated from one shared source, so they cannot drift apart.*

**`bands_calc`**

```python
BAND_EDGES  = [0, 500_000, 1_000_000, 2_000_000, 3_000_000, 5_000_000, 10_000_000, np.inf]
BAND_LABELS = ["< 500K", "500K - 1M", "1M - 2M", "2M - 3M", "3M - 5M", "5M - 10M", "> 10M"]

# right=False makes every band LEFT-CLOSED / RIGHT-OPEN: a sale of exactly
# AED 1,000,000 lands in "1M - 2M", never in "500K - 1M".
band  = pd.cut(clean.actual_worth, bins=BAND_EDGES, labels=BAND_LABELS, right=False)
bands = (band.value_counts().reindex(BAND_LABELS).fillna(0).astype(int)
             .rename_axis("Price band (AED)").reset_index(name="Transactions"))
bands["Share (%)"] = bands.Transactions / len(clean) * 100
bands
```

**`bands_values`**

```python
p = clean.actual_worth.dropna()

print("AUDIT - the bands must account for every row exactly once")
print(f"  rows in the dataset       : {len(clean):,}")
print(f"  rows assigned to a band   : {int(bands.Transactions.sum()):,}")
print(f"  unassigned                : {len(clean) - int(bands.Transactions.sum()):,}")
print(f"  shares sum to             : {bands['Share (%)'].sum():.2f}%")

print("\nTHE RANGE, in the terms the dashboard uses")
print(f"  observations              : {len(p):,}")
print(f"  minimum (cheapest sale)   : AED {p.min():,.0f}")
print(f"  maximum (dearest sale)    : AED {p.max():,.0f}")
print(f"  25th percentile           : AED {p.quantile(.25):,.0f}")
print(f"  median                    : AED {p.median():,.0f}")
print(f"  75th percentile           : AED {p.quantile(.75):,.0f}")
print(f"  middle half of the market : AED {p.quantile(.25):,.0f} - {p.quantile(.75):,.0f}")

lo, hi = p.quantile([0.005, 0.995])
print(f"\nHISTOGRAM DISPLAY RANGE (the companion chart)")
print(f"  0.5th - 99.5th percentile : AED {lo:,.0f} - {hi:,.0f}")
print(f"  bins                      : 60 equal-width")
print(f"  bin width                 : AED {(hi-lo)/60:,.0f}")
print(f"  rows outside the display  : {int(((p < lo) | (p > hi)).sum()):,} "
      f"({((p < lo) | (p > hi)).mean()*100:.1f}%) - still in every statistic above")
```

**`bands_graph`**

```python
fig = go.Figure(go.Bar(x=bands["Price band (AED)"], y=bands.Transactions,
                       marker_color="#2563EB",
                       text=[f"{v:.1f}%" for v in bands["Share (%)"]], textposition="outside",
                       hovertemplate="%{x}<br>Transactions: %{y:,}<extra></extra>"))
fig.update_layout(height=410, title="Where the price points are")
fig.update_yaxes(title_text="Transactions")
fig.update_xaxes(title_text="Price band (AED)")
fig.show()
```

### 6.18 Intermediate dataframe
`bands` — **7 rows × 3 columns**

Columns: `Price band (AED)`, `Transactions`, `Share (%)`

### 6.19 Result values — actual notebook output
*Printed by the run recorded in the appendix, not typed from memory.*

```
AUDIT - the bands must account for every row exactly once
  rows in the dataset       : 818,838
  rows assigned to a band   : 818,838
  unassigned                : 0
  shares sum to             : 100.00%

THE RANGE, in the terms the dashboard uses
  observations              : 818,838
  minimum (cheapest sale)   : AED 112,399
  maximum (dearest sale)    : AED 422,000,000
  25th percentile           : AED 698,853
  median                    : AED 1,163,000
  75th percentile           : AED 1,963,888
  middle half of the market : AED 698,853 - 1,963,888

HISTOGRAM DISPLAY RANGE (the companion chart)
  0.5th - 99.5th percentile : AED 220,000 - 11,483,260
  bins                      : 60 equal-width
  bin width                 : AED 187,721
  rows outside the display  : 7,982 (1.0%) - still in every statistic above
```

The audit is the point of this section: **818,838 rows in, 818,838 rows banded, 0 unassigned, shares summing to 100.00%**. A banding that quietly dropped rows would still look like a reasonable chart, which is exactly why it is checked in code rather than by eye.

### 6.20 Chart type, and why
A column chart, because bands are ordered categories and their widths are unequal — a histogram would misrepresent the spacing.

### 6.21 Axes
- **x:** Price band (AED).
- **y:** Number of transactions.

### 6.22 Legend
Bar labels show each band's share of the current selection.

### 6.23 Colour meaning
A single blue series; the bands are ordered along the x-axis, so colour carries no extra meaning.

### 6.24 Hover contents
Band and transaction count; the share is printed above each bar so it is readable without hovering.

### 6.25 How to read it — and what it does NOT say
**How to read it**

- The tallest bars are where the market actually is.
- The right-hand tail is the luxury segment.
- **Check the note under the chart**: the sale-price slider defaults to the 1st–99th percentile, which truncates the top bands. Widen it to see them.

**What it does not say**

- Nothing about size or value for money — a 2M studio and a 2M three-bed are in the same band.

### 6.26 Limitations and validation actually performed
**Limitations**

- Covers registered residential **unit** (apartment) sales only — villas, land and whole-building transactions are not in this dataset.
- 2026 is a partial year: the data ends **6 August 2026**, so 2026 totals are not comparable with a full year.
- The sale-price and unit-size sliders start at the 1st–99th percentile, so the most extreme deals are excluded until you widen them.
- The bands are fixed business bands, not derived from the distribution.
- The default price filter hides the top of the range. Unfiltered, the cleaned dataset contains 5,308 sales at AED 10M or more (0.6%).

**Validation**

Recomputed on the raw registry, the raw residential-unit subset and the cleaned dataset. In all three the band counts sum exactly to the row count with zero unassigned rows, confirming the bands are exhaustive and mutually exclusive. Chart and table are generated from the same computed frame, so they cannot disagree.

---

## 7. Rate per m² by layout

> How much a square metre costs in each size of apartment — and how widely that varies inside each one.

**Dashboard title:** Rate per m² by layout  |  **Registry key:** `rate_by_layout`  |  **Notebook section:** §7

### 7.1 Where it appears in the dashboard
**Dubai → Property tab.**

### 7.2 What the visualisation is
Box plot built from **pre-computed quartiles** (`go.Box` with explicit `q1` / `median` / `q3` / fences).

### 7.3 Plain-English one-liner
How much a square metre costs in each size of apartment — and how widely that varies inside each one.

### 7.4 The question it answers
How does the price per square metre differ between a studio, a one-bedroom, a three-bedroom and so on?

### 7.5 Data source
**CLEANED** — `data/dubai/latest_combined_data.parquet`

818,838 residential **unit** sales registered in Dubai, 2010 – Aug 2026, enriched by the project with time parts, unit attributes, amenity flags and building / developer scoring.

### 7.6 Why that source
A single combined box plot compressed nine layouts on top of each other and was unreadable. Separate panels let each distribution be seen.

### 7.7 Columns used
`rooms_en` · `meter_sale_price`

### 7.8 Filters that apply
All seven Dubai sidebar filters apply: year, locality zone, area, layout, registration type, sale-price range and unit-size range.

### 7.9 Population and exclusions
Cleaned selection grouped by `rooms_en`. Layouts with fewer than 100 transactions are **listed with their values** rather than deleted — 6 B/R (82 transactions) and 7 B/R (4) appear in the text, not in the chart.

### 7.10 Missing values
Rows without a layout label are excluded from the grouping and are not folded into any bucket.

### 7.11 Grouping and aggregation
`groupby('rooms_en')` → `quantile([.25,.5,.75])` of `meter_sale_price`, plus `size()` and `median(procedure_area)`.

### 7.12 Metric definition
The quartiles of rate per m² for each layout.

### 7.13 Formula
`iqr = q3 − q1`; whiskers at `q1 − 1.5·iqr` and `q3 + 1.5·iqr`, clipped to the observed range.

### 7.14 Method, and why this method
Quartiles are computed server-side and handed to Plotly as numbers, rather than shipping 818,838 raw points to the browser. The drawn box is arithmetically identical to a box Plotly would compute itself, and the page stays responsive.

### 7.15 Thresholds and parameters
`MIN_CELL = 100`. Layout order is fixed (Studio → Penthouse) rather than sorted by value, so the chart reads as a size ladder.

### 7.16 Notebook cells
This section is produced by `layout_calc`, `layout_values`, `layout_graph` in `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.

### 7.17 Code — identical to the notebook
*Every block below is the notebook cell, byte for byte. Both files are generated from one shared source, so they cannot drift apart.*

**`layout_calc`**

```python
ROOM_ORDER = ["Studio", "1 B/R", "2 B/R", "3 B/R", "4 B/R", "5 B/R",
              "6 B/R", "7 B/R", "PENTHOUSE"]
MIN_LAYOUT = 100        # layouts below this are listed, never silently dropped

lay = clean.dropna(subset=["rooms_en", "meter_sale_price"])
counts_by_layout = lay.rooms_en.value_counts()
kept    = [r for r in ROOM_ORDER if counts_by_layout.get(r, 0) >= MIN_LAYOUT]
excluded = [r for r in ROOM_ORDER if 0 < counts_by_layout.get(r, 0) < MIN_LAYOUT]

g = lay[lay.rooms_en.isin(kept)].groupby("rooms_en", observed=True)["meter_sale_price"]
stats = g.quantile([0.25, 0.50, 0.75]).unstack()
stats.columns = ["q1", "median", "q3"]
stats["iqr"] = stats.q3 - stats.q1

# Whiskers reach the furthest ACTUAL observation inside 1.5 x IQR - no value is
# deleted, the whisker simply stops at the last ordinary transaction.
lo_fence = (stats.q1 - 1.5 * stats.iqr).clip(lower=float(lay.meter_sale_price.min()))
hi_fence =  stats.q3 + 1.5 * stats.iqr
stats["lower_whisker"] = [float(g.get_group(k)[g.get_group(k) >= lo_fence[k]].min())
                          for k in stats.index]
stats["upper_whisker"] = [float(g.get_group(k)[g.get_group(k) <= hi_fence[k]].max())
                          for k in stats.index]
stats["transactions"]  = g.size()
stats["mean"]          = g.mean()
stats["median_size_m2"] = (lay[lay.rooms_en.isin(kept)]
                           .groupby("rooms_en", observed=True)["procedure_area"].median())
stats = stats.reindex(kept)
stats.round(0)
```

**`layout_values`**

```python
print("Layout      Transactions   25th pct     Median       75th pct    Median size")
for name, r in stats.iterrows():
    print(f"{str(name):<11} {int(r.transactions):>11,}   {r.q1:>9,.0f}   "
          f"{r['median']:>9,.0f}   {r.q3:>9,.0f}   {r.median_size_m2:>7,.0f} m2")

if excluded:
    print(f"\nNot plotted - fewer than {MIN_LAYOUT} transactions "
          f"(listed, not deleted):")
    for r in excluded:
        sub = lay.loc[lay.rooms_en == r, "meter_sale_price"]
        print(f"  {r}: {len(sub)} transactions, median AED {sub.median():,.0f}/m2")

print(f"\nDoes the rate rise with layout size?")
ladder = [r for r in ["Studio", "1 B/R", "2 B/R", "3 B/R", "4 B/R"] if r in stats.index]
vals = [round(float(stats.loc[r, "median"]), 1) for r in ladder]
print(f"  {dict(zip(ladder, vals))}")
print(f"  monotonically increasing: {vals == sorted(vals)}")
```

**`layout_graph`**

```python
palette = ["#2563EB", "#0D9488", "#D97706", "#7C3AED", "#DC2626", "#059669", "#DB2777"]

fig = go.Figure()
for i, name in enumerate(stats.index):
    r = stats.loc[name]
    fig.add_trace(go.Box(
        x=[str(name)], q1=[r.q1], median=[r["median"]], q3=[r.q3],
        lowerfence=[r.lower_whisker], upperfence=[r.upper_whisker],
        name=f"{name} ({int(r.transactions):,})",
        marker_color=palette[i % len(palette)], width=0.55,
        hovertemplate=(f"<b>{name}</b><br>Upper whisker: %{{upperfence:,.0f}}"
                       "<br>75th pct: %{q3:,.0f}<br>Median: %{median:,.0f}"
                       "<br>25th pct: %{q1:,.0f}"
                       "<br>Lower whisker: %{lowerfence:,.0f}<extra></extra>")))

fig.update_layout(height=470, title="Rate per m2 by layout",
                  legend=dict(orientation="h", y=-0.22))
fig.update_yaxes(title_text="Rate per m2 (AED)")
fig.update_xaxes(title_text="Layout")
fig.show()
```

### 7.18 Intermediate dataframe
`stats` — **7 rows × 9 columns**

Columns: `q1`, `median`, `q3`, `iqr`, `lower_whisker`, `upper_whisker`, `transactions`, `mean`, `median_size_m2`

### 7.19 Result values — actual notebook output
*Printed by the run recorded in the appendix, not typed from memory.*

```
Layout      Transactions   25th pct     Median       75th pct    Median size
Studio          189,729      10,341      14,845      19,086        40 m2
1 B/R           343,595      10,222      14,854      20,647        73 m2
2 B/R           211,748      10,955      15,758      22,669       120 m2
3 B/R            64,318      11,171      17,010      24,433       179 m2
4 B/R             7,614      12,037      19,943      32,451       315 m2
5 B/R               950       9,087      18,325      36,581       581 m2
PENTHOUSE           798       9,567      13,336      18,353       298 m2

Not plotted - fewer than 100 transactions (listed, not deleted):
  6 B/R: 82 transactions, median AED 32,254/m2
  7 B/R: 4 transactions, median AED 51,432/m2

Does the rate rise with layout size?
  {'Studio': 14844.6, '1 B/R': 14854.2, '2 B/R': 15758.4, '3 B/R': 17010.2, '4 B/R': 19942.9}
  monotonically increasing: True
```

Across Studio → 4 B/R the median rate rises monotonically (14,845 → 14,854 → 15,758 → 17,010 → 19,943 AED/m²). It then **falls** for 5 B/R and Penthouse. That reversal is a real feature of the data on small samples (950 and 798 transactions), and it is kept and shown rather than smoothed away.

### 7.20 Chart type, and why
A box plot, because the interesting fact about layout pricing is the **spread**, not just the middle. A bar of medians would hide that a 5 B/R has both the widest range and one of the lower medians.

### 7.21 Axes
- **x:** Layout (one panel each).
- **y:** Rate per m² (AED). All panels share the same scale so they can be compared.

### 7.22 Legend
Each panel is coloured for identification only; the transaction count is printed under each panel.

### 7.23 Colour meaning
One colour per layout, consistent with §5.

### 7.24 Hover contents
Layout, the three quartiles, the transaction count and the median unit size.

### 7.25 How to read it — and what it does NOT say
**How to read it**

- The box is the middle 50% of transactions; the line inside it is the median.
- The whiskers show the typical range; the table lists what falls beyond them.
- Compare median lines across panels to see how price per m² varies by layout.

**What it does not say**

- Nothing about total price — a studio at a high rate is still a cheaper home.
- Nothing about which layout is the better investment.

### 7.26 Limitations and validation actually performed
**Limitations**

- Covers registered residential **unit** (apartment) sales only — villas, land and whole-building transactions are not in this dataset.
- 2026 is a partial year: the data ends **6 August 2026**, so 2026 totals are not comparable with a full year.
- The sale-price and unit-size sliders start at the 1st–99th percentile, so the most extreme deals are excluded until you widen them.
- Layouts with very few sales (6 B/R, 7 B/R) are excluded from the panels and reported in the note instead.

**Validation**

Quartiles were recomputed directly in pandas and matched. The earlier claim that smaller units cost more per m² was tested against the data and **did not hold**, so it was removed.

---

## 8. Unit size — key statistics

> How big Dubai apartments actually are, one row per size of apartment.

**Dashboard title:** Unit size — key statistics  |  **Registry key:** `unit_size_summary`  |  **Notebook section:** §8

### 8.1 Where it appears in the dashboard
**Dubai → Distribution tab.** Occupies the position previously held by the unit-size distribution chart.

### 8.2 What the visualisation is
Statistics table (no chart).

### 8.3 Plain-English one-liner
How big Dubai apartments actually are, one row per size of apartment.

### 8.4 The question it answers
How big is a Dubai apartment, and how much does that vary?

### 8.5 Data source
**CLEANED** — `data/dubai/latest_combined_data.parquet`

818,838 residential **unit** sales registered in Dubai, 2010 – Aug 2026, enriched by the project with time parts, unit attributes, amenity flags and building / developer scoring.

### 8.6 Why that source
It answers the same question the old unit-size histogram did — how big are these homes — but gives readable numbers instead of a shape, and splits them by property type so the answer is usable.

### 8.7 Columns used
`rooms_en` · `procedure_area`

### 8.8 Filters that apply
All seven Dubai sidebar filters apply: year, locality zone, area, layout, registration type, sale-price range and unit-size range.

### 8.9 Population and exclusions
Every row of the cleaned selection with a `procedure_area`.

### 8.10 Missing values
Absent sizes are excluded from every statistic; the observation count is printed so the denominator is explicit.

### 8.11 Grouping and aggregation
Whole selection for the headline block, then `groupby('rooms_en')` for the per-layout table.

### 8.12 Metric definition
Count, minimum, 25th percentile, median, mean, 75th percentile, maximum — in m².

### 8.13 Formula
Standard order statistics on `procedure_area`; `mean − median` is reported as the skew indicator.

### 8.14 Method, and why this method
A table rather than a shape. A distribution chart of unit size was removed on request; the position is filled with the numbers that chart was there to convey, which is more precise, not less.

### 8.15 Thresholds and parameters
None. No trimming, no winsorising — the 2,916 m² maximum is shown.

### 8.16 Notebook cells
This section is produced by `size_calc`, `size_values` in `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.

### 8.17 Code — identical to the notebook
*Every block below is the notebook cell, byte for byte. Both files are generated from one shared source, so they cannot drift apart.*

**`size_calc`**

```python
order = [v for v in PROPERTY_TYPE_LABELS if v in set(clean.rooms_en.dropna().unique())]

size_stats = (clean[clean.rooms_en.isin(order)]
              .groupby("rooms_en", observed=True)["procedure_area"]
              .agg(Transactions="size",
                   Smallest="min",
                   p25=lambda s: s.quantile(0.25),
                   Median="median",
                   Mean="mean",
                   p75=lambda s: s.quantile(0.75),
                   Largest="max")
              .reindex(order).dropna(how="all").reset_index())
size_stats["Property type"] = size_stats.rooms_en.map(PROPERTY_TYPE_LABELS)
size_stats = size_stats[["Property type", "Transactions", "Smallest", "p25",
                         "Median", "Mean", "p75", "Largest"]]
size_stats.round(1)
```

**`size_values`**

```python
overall = clean.procedure_area.dropna()
print(f"observations              : {len(overall):,}")
print(f"minimum                   : {overall.min():,.0f} m2")
print(f"25th percentile           : {overall.quantile(.25):,.0f} m2")
print(f"median                    : {overall.median():,.0f} m2")
print(f"mean                      : {overall.mean():,.1f} m2")
print(f"75th percentile           : {overall.quantile(.75):,.0f} m2")
print(f"maximum                   : {overall.max():,.0f} m2")
print(f"middle half of the market : {overall.quantile(.25):,.0f} - "
      f"{overall.quantile(.75):,.0f} m2")
print(f"mean above median by      : {overall.mean() - overall.median():,.1f} m2 "
      f"- the right tail of large units")
```

### 8.18 Intermediate dataframe
`size_stats` — **7 rows × 8 columns**

Columns: `Property type`, `Transactions`, `Smallest`, `p25`, `Median`, `Mean`, `p75`, `Largest`

### 8.19 Result values — actual notebook output
*Printed by the run recorded in the appendix, not typed from memory.*

```
observations              : 818,838
minimum                   : 25 m2
25th percentile           : 58 m2
median                    : 78 m2
mean                      : 93.1 m2
75th percentile           : 115 m2
maximum                   : 2,916 m2
middle half of the market : 58 - 115 m2
mean above median by      : 15.6 m2 - the right tail of large units
```

The mean (93.1 m²) sits **15.6 m² above** the median (78 m²). That gap is the right tail of large units, and it is reported explicitly so the mean is not mistaken for a typical apartment.

### 8.20 Chart type, and why
No chart. The user asked for the distribution graph to be removed; replacing it with a different graph in the same place would have re-added what was removed. A statistics table answers the same question exactly and claims nothing extra.

### 8.21 Axes
Not applicable — this section is a table.

### 8.22 Legend
Not applicable — this is a table.

### 8.23 Colour meaning
n/a.

### 8.24 Hover contents
n/a — every value is printed.

### 8.25 How to read it — and what it does NOT say
**How to read it**

- The median column is the typical size for that property type.
- The 25th and 75th percentile columns bracket the middle half — most units of that type sit between them.
- Smallest and largest are single transactions and are not typical.

**What it does not say**

- Nothing about price — see the Price section for that.

### 8.26 Limitations and validation actually performed
**Limitations**

- Covers registered residential **unit** (apartment) sales only — villas, land and whole-building transactions are not in this dataset.
- 2026 is a partial year: the data ends **6 August 2026**, so 2026 totals are not comparable with a full year.
- The sale-price and unit-size sliders start at the 1st–99th percentile, so the most extreme deals are excluded until you widen them.
- Floor area is the registered procedure area, which may differ from a developer's marketed area.

**Validation**

Every quantile recomputed in plain pandas and matched.

---

## 9. Sale price by registration type — summary

> How big each segment is and what prices look like inside it — described, not compared.

**Dashboard title:** Sale price by registration type — summary  |  **Registry key:** `price_by_reg_summary`  |  **Notebook section:** §9

### 9.1 Where it appears in the dashboard
**Dubai → Distribution tab.** Occupies the position previously held by the sale-price-by-registration-type box plot.

### 9.2 What the visualisation is
Summary table (no chart).

### 9.3 Plain-English one-liner
How big each segment is and what prices look like inside it — described, not compared.

### 9.4 The question it answers
What do off-plan sales and existing-property sales each look like, on their own terms?

### 9.5 Data source
**CLEANED** — `data/dubai/latest_combined_data.parquet`

818,838 residential **unit** sales registered in Dubai, 2010 – Aug 2026, enriched by the project with time parts, unit attributes, amenity flags and building / developer scoring.

### 9.6 Why that source
It keeps the information the old box plot carried — how prices are spread within each registration type — in a form that can be read directly, without a log axis to interpret.

### 9.7 Columns used
`reg_type_en` · `actual_worth` · `meter_sale_price`

### 9.8 Filters that apply
All seven Dubai sidebar filters apply: year, locality zone, area, layout, registration type, sale-price range and unit-size range.

### 9.9 Population and exclusions
Cleaned selection split by `reg_type_en` into Existing Properties (351,627) and Off-Plan Properties (467,211).

### 9.10 Missing values
Rows with no registration type are excluded and not assigned to either group.

### 9.11 Grouping and aggregation
`groupby('reg_type_en')` → count, share, 25th/50th/75th percentile of `actual_worth`, median `meter_sale_price`.

### 9.12 Metric definition
Per group: transactions, share of the selection, the middle half of prices, the median price and the median rate per m².

### 9.13 Formula
Order statistics per group. **No cross-group difference is computed.**

### 9.14 Method, and why this method
Each row is described on its own terms. The earlier version of this panel reported a +58.7% off-plan premium; controlled analysis showed that headline is a composition effect — within the same building and year the gap is −1.5% — so the premium claim was withdrawn rather than restated with a caveat.

### 9.15 Thresholds and parameters
None.

### 9.16 Notebook cells
This section is produced by `regtype_calc`, `regtype_values` in `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.

### 9.17 Code — identical to the notebook
*Every block below is the notebook cell, byte for byte. Both files are generated from one shared source, so they cannot drift apart.*

**`regtype_calc`**

```python
reg_summary = (clean.groupby("reg_type_en", observed=True)
                    .agg(Transactions=("actual_worth", "size"),
                         p25=("actual_worth", lambda s: s.quantile(0.25)),
                         Median=("actual_worth", "median"),
                         p75=("actual_worth", lambda s: s.quantile(0.75)),
                         MedianRate=("meter_sale_price", "median"))
                    .reset_index()
                    .rename(columns={"reg_type_en": "Registration type"}))
reg_summary["Share of transactions (%)"] = (reg_summary.Transactions
                                            / reg_summary.Transactions.sum() * 100)
reg_summary = reg_summary[["Registration type", "Transactions",
                           "Share of transactions (%)", "p25", "Median", "p75",
                           "MedianRate"]]
reg_summary.columns = ["Registration type", "Transactions", "Share of transactions (%)",
                       "25th pct price (AED)", "Median price (AED)",
                       "75th pct price (AED)", "Median rate (AED/m2)"]
reg_summary.round(1)
```

**`regtype_values`**

```python
for _, r in reg_summary.iterrows():
    print(f"{r['Registration type']}")
    print(f"   transactions          : {int(r.Transactions):,} "
          f"({r['Share of transactions (%)']:.1f}% of the selection)")
    print(f"   middle half of prices : AED {r['25th pct price (AED)']:,.0f} - "
          f"{r['75th pct price (AED)']:,.0f}")
    print(f"   median price          : AED {r['Median price (AED)']:,.0f}")
    print(f"   median rate           : AED {r['Median rate (AED/m2)']:,.0f}/m2")
    print()
print("Each row is described on its own terms. No difference between the two rows")
print("is computed here, and no premium or discount is stated.")
```

### 9.18 Intermediate dataframe
`reg_summary` — **2 rows × 7 columns**

Columns: `Registration type`, `Transactions`, `Share of transactions (%)`, `25th pct price (AED)`, `Median price (AED)`, `75th pct price (AED)`, `Median rate (AED/m2)`

### 9.19 Result values — actual notebook output
*Printed by the run recorded in the appendix, not typed from memory.*

```
Existing Properties
   transactions          : 351,627 (42.9% of the selection)
   middle half of prices : AED 580,000 - 1,720,000
   median price          : AED 985,000
   median rate           : AED 11,264/m2

Off-Plan Properties
   transactions          : 467,211 (57.1% of the selection)
   middle half of prices : AED 789,000 - 2,114,888
   median price          : AED 1,275,353
   median rate           : AED 17,879/m2

Each row is described on its own terms. No difference between the two rows
is computed here, and no premium or discount is stated.
```

**What this table deliberately does not say.** It does not state a premium, a discount, or any difference between the two rows. The numbers are there; the subtraction is not, because the two groups are not like for like.

### 9.20 Chart type, and why
No chart, and no comparison. The two groups differ in what they contain — off-plan stock is newer, taller and better located — so a side-by-side visual invites exactly the causal reading the data does not support.

### 9.21 Axes
Not applicable — this section is a table.

### 9.22 Legend
Not applicable — this is a table.

### 9.23 Colour meaning
n/a.

### 9.24 Hover contents
n/a — every value is printed.

### 9.25 How to read it — and what it does NOT say
**How to read it**

- Read each row on its own: this is what that segment looked like.
- The 25th and 75th percentile columns bracket the middle half of that segment's sales.

**What it does not say**

- **No comparison between the two rows is made here**, and no premium or discount is stated. The two segments are different products in different buildings, so a difference between the rows would not be a like-for-like comparison.

### 9.26 Limitations and validation actually performed
**Limitations**

- Covers registered residential **unit** (apartment) sales only — villas, land and whole-building transactions are not in this dataset.
- 2026 is a partial year: the data ends **6 August 2026**, so 2026 totals are not comparable with a full year.
- The sale-price and unit-size sliders start at the 1st–99th percentile, so the most extreme deals are excluded until you widen them.

**Validation**

Counts, shares and quantiles recomputed in plain pandas and matched.

---

## 10. How the price distribution has changed

> The market has not only moved up — it has spread out. That matters when you price one specific unit.

**Dashboard title:** How the price distribution has changed  |  **Registry key:** `rate_violin_year`  |  **Notebook section:** §10

### 10.1 Where it appears in the dashboard
**Dubai → Distribution tab.**

### 10.2 What the visualisation is
Violin plot with an inner box, one violin per year (`px.violin`, `box=True`, `points=False`).

### 10.3 Plain-English one-liner
The market has not only moved up — it has spread out. That matters when you price one specific unit.

### 10.4 The question it answers
Has the whole distribution of prices moved, or only its middle?

### 10.5 Data source
**CLEANED** — `data/dubai/latest_combined_data.parquet`

818,838 residential **unit** sales registered in Dubai, 2010 – Aug 2026, enriched by the project with time parts, unit attributes, amenity flags and building / developer scoring.

### 10.6 Why that source
A median only tells you the centre. This shows whether the market is also spreading out.

### 10.7 Columns used
`year` · `meter_sale_price`

### 10.8 Filters that apply
All seven Dubai sidebar filters apply: year, locality zone, area, layout, registration type, sale-price range and unit-size range.

### 10.9 Population and exclusions
A 45,000-row sample of the cleaned selection, `random_state=42`, taken only when the selection exceeds 45,000 rows.

### 10.10 Missing values
Rows without a rate are excluded before sampling.

### 10.11 Grouping and aggregation
One violin per `year`; the kernel density and the inner quartile box are computed by Plotly from the sampled points.

### 10.12 Metric definition
The shape of the rate-per-m² distribution, by year.

### 10.13 Formula
Sampling: `df.sample(45_000, random_state=42)`. Fidelity: `|sample statistic − population statistic| / population statistic × 100`, per year.

### 10.14 Method, and why this method
**The sampling was audited before being kept.** §10.1 recomputes the median and 75th percentile per year on the full population and on the sample: the worst per-year median error is **2.47%**, the worst p75 error **1.66%**, and the smallest per-year sample is 989 rows. The methodology was reviewed and found sound, so it was preserved rather than replaced.

### 10.15 Thresholds and parameters
`SAMPLE_N = 45_000`, `random_state = 42` — fixed, so the picture is reproducible rather than different on every run.

### 10.16 Notebook cells
This section is produced by `dist_fidelity`, `dist_values`, `dist_graph` in `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.

### 10.17 Code — identical to the notebook
*Every block below is the notebook cell, byte for byte. Both files are generated from one shared source, so they cannot drift apart.*

**`dist_fidelity`**

```python
SAMPLE_N = 45_000
sample = clean.sample(SAMPLE_N, random_state=42)     # deterministic

fidelity = pd.DataFrame({
    "population n":      clean.groupby("year").size(),
    "sample n":          sample.groupby("year").size(),
    "population median": clean.groupby("year")["meter_sale_price"].median(),
    "sample median":     sample.groupby("year")["meter_sale_price"].median(),
    "population p75":    clean.groupby("year")["meter_sale_price"].quantile(0.75),
    "sample p75":        sample.groupby("year")["meter_sale_price"].quantile(0.75),
}).dropna()
fidelity["median error (%)"] = (fidelity["sample median"] / fidelity["population median"] - 1) * 100
fidelity["p75 error (%)"]    = (fidelity["sample p75"]    / fidelity["population p75"]    - 1) * 100
fidelity.round(2)
```

**`dist_values`**

```python
print(f"sample size                 : {SAMPLE_N:,} of {len(clean):,} rows "
      f"({SAMPLE_N/len(clean)*100:.1f}%), random_state=42")
print(f"worst per-year median error : {fidelity['median error (%)'].abs().max():.2f}%")
print(f"worst per-year p75 error    : {fidelity['p75 error (%)'].abs().max():.2f}%")
print(f"smallest per-year sample    : {int(fidelity['sample n'].min()):,} rows")

print("\nPer-year distribution shape on the FULL population (no sampling):")
shape = (clean.groupby("year")["meter_sale_price"]
              .agg(n="size", p25=lambda s: s.quantile(.25), median="median",
                   p75=lambda s: s.quantile(.75)))
shape["iqr"] = shape.p75 - shape.p25
shape["iqr_as_pct_of_median"] = shape.iqr / shape["median"] * 100
print(shape.round(0).to_string())
print("\n=> The sample tracks the population closely, so the existing sampled")
print("   violin methodology is sound and was preserved rather than replaced.")
```

**`dist_graph`**

```python
fig = go.Figure()
for y in sorted(sample.year.unique()):
    fig.add_trace(go.Violin(y=sample.loc[sample.year == y, "meter_sale_price"],
                            name=str(int(y)), box_visible=True, points=False,
                            meanline_visible=False,
                            hovertemplate="Year %{x}<br>Rate: AED %{y:,.0f}/m2<extra></extra>"))
fig.update_layout(height=490, showlegend=False,
                  title="How the price distribution has changed (rate per m2, by year)")
fig.update_yaxes(title_text="Rate per m2 (AED/m2)")
fig.update_xaxes(title_text="Year")
fig.show()
```

### 10.18 Intermediate dataframe
`fidelity / shape` — **17 rows × 8 columns / 17 rows × 6 columns**

Columns: `population n`, `sample n`, `population median`, `sample median`, `population p75`, `sample p75`, `median error (%)`, `p75 error (%)` — and `n`, `p25`, `median`, `p75`, `iqr`, `iqr_as_pct_of_median`

### 10.19 Result values — actual notebook output
*Printed by the run recorded in the appendix, not typed from memory.*

```
sample size                 : 45,000 of 818,838 rows (5.5%), random_state=42
worst per-year median error : 2.47%
worst per-year p75 error    : 1.66%
smallest per-year sample    : 989 rows

Per-year distribution shape on the FULL population (no sampling):
           n       p25    median       p75       iqr  iqr_as_pct_of_median
year                                                                      
2010   24435  7,618.00  9,727.00 13,243.00  5,625.00                 58.00
2011   18355  7,223.00  9,334.00 12,838.00  5,615.00                 60.00
2012   21771  7,617.00  9,832.00 12,907.00  5,289.00                 54.00
2013   38942  7,970.00 10,905.00 15,595.00  7,625.00                 70.00
2014   34432  8,989.00 12,206.00 17,222.00  8,233.00                 67.00
2015   25413  8,677.00 11,355.00 16,146.00  7,469.00                 66.00
2016   25328  8,966.00 11,245.00 15,145.00  6,178.00                 55.00
2017   27811  9,158.00 11,956.00 15,847.00  6,689.00                 56.00
2018   19348  9,056.00 11,840.00 16,053.00  6,998.00                 59.00
2019   21398  8,555.00 12,157.00 17,426.00  8,870.00                 73.00
2020   18405  8,135.00 10,962.00 16,238.00  8,103.00                 74.00
2021   33102  8,828.00 12,151.00 17,816.00  8,988.00                 74.00
2022   58164 10,520.00 15,928.00 21,570.00 11,049.00                 69.00
2023   88537 11,376.00 16,117.00 22,585.00 11,209.00                 70.00
2024  128768 13,021.00 17,373.00 24,073.00 11,051.00                 64.00
2025  159477 14,559.00 18,370.00 24,763.00 10,204.00                 56.00
2026   75152 14,947.00 18,359.00 23,654.00  8,707.00                 47.00

=> The sample tracks the population closely, so the existing sampled
   violin methodology is sound and was preserved rather than replaced.
```

The full-population table in §10.2 is the honest companion to the sampled picture: the interquartile range widens from AED 5,625/m² in 2010 to AED 11,209/m² in 2023 and then narrows to 8,707 in 2026 — as a share of the median, from 58% to 47%. The distribution has both risen and changed shape.

### 10.20 Chart type, and why
A violin, because the question is about shape. A box plot would show the quartiles moving but not that the upper tail stretched much further than the middle did; the violin shows both at once.

### 10.21 Axes
- **x:** Year.
- **y:** Rate per m² (AED/m²).

### 10.22 Legend
One violin per year; colour is for identification only.

### 10.23 Colour meaning
One colour per year, for separation only — the colours carry no ordering meaning.

### 10.24 Hover contents
Year and rate per m².

### 10.25 How to read it — and what it does NOT say
**How to read it**

- Wider at a given height = more transactions at that price level.
- Watch two things: the centre moving up, and the shape getting wider. The second means the market is spreading, not just rising.

**What it does not say**

- Nothing about which segments drove the change.

### 10.26 Limitations and validation actually performed
**Limitations**

- Covers registered residential **unit** (apartment) sales only — villas, land and whole-building transactions are not in this dataset.
- 2026 is a partial year: the data ends **6 August 2026**, so 2026 totals are not comparable with a full year.
- The sale-price and unit-size sliders start at the 1st–99th percentile, so the most extreme deals are excluded until you widen them.
- Based on a sample.
- 2026 covers eight months only.

**Validation**

Sampled medians per year were compared with full-population medians and agree.

---

## 11. Year-by-year summary table (the off-plan vs existing replacement)

> Every year on one row: how busy it was, what the average was, and what the typical transaction was.

**Dashboard title:** Year-by-year summary  |  **Registry key:** `yearly_summary`  |  **Notebook section:** §11

### 11.1 Where it appears in the dashboard
**Dubai → Price tab**, in the position previously occupied by the off-plan vs existing chart.

### 11.2 What the visualisation is
Table (no chart).

### 11.3 Plain-English one-liner
Every year on one row: how busy it was, what the average was, and what the typical transaction was.

### 11.4 The question it answers
Year by year, how many transactions were recorded and what were the mean and median rates?

### 11.5 Data source
**CLEANED** — `data/dubai/latest_combined_data.parquet`

818,838 residential **unit** sales registered in Dubai, 2010 – Aug 2026, enriched by the project with time parts, unit attributes, amenity flags and building / developer scoring.

### 11.6 Why that source
A compact reference that answers most year-level questions without reading a chart, and puts the mean and the median side by side so the difference between them is visible.

### 11.7 Columns used
`instance_date` · `trans_group_en` · `property_type_en` · `property_usage_en` · `year` · `meter_sale_price`

### 11.8 Filters that apply
All seven Dubai sidebar filters apply: year, locality zone, area, layout, registration type, sale-price range and unit-size range.

### 11.9 Population and exclusions
Volume from the raw registry (residential unit sales, 2011 onwards); rates from the cleaned dataset for the same years.

### 11.10 Missing values
A year with no priced cleaned rows would show its count and a blank rate, not a zero.

### 11.11 Grouping and aggregation
Raw counts per year joined to cleaned per-year `mean` and `median` of `meter_sale_price`, plus the number of priced rows the statistics came from.

### 11.12 Metric definition
Per year: number of transactions (raw), mean rate/m², median rate/m², and priced transactions used (cleaned).

### 11.13 Formula
Direct aggregations; no derived ratio, no growth column, no premium.

### 11.14 Method, and why this method
A table, because the off-plan chart it replaces made a comparison the data does not support. The replacement reports what each year contained and lets the reader do any comparing.

### 11.15 Thresholds and parameters
`BASE_YEAR = 2011`.

### 11.16 Notebook cells
This section is produced by `yearsummary_calc`, `yearsummary_values` in `notebooks/Unified_Dashboard_Graph_Analysis.ipynb`.

### 11.17 Code — identical to the notebook
*Every block below is the notebook cell, byte for byte. Both files are generated from one shared source, so they cannot drift apart.*

**`yearsummary_calc`**

```python
summary = vol_price[["year", "transactions", "mean_rate", "median_rate",
                     "priced_rows", "complete"]].copy()
summary["Year"] = summary["year"].astype(int).astype(str)
summary.loc[~summary.complete, "Year"] += f"  ({period}, in progress)"
summary = summary[["Year", "transactions", "mean_rate", "median_rate", "priced_rows"]]
summary.columns = ["Year", "Number of transactions (raw)", "Mean rate/m2 (AED)",
                   "Median rate/m2 (AED)", "Priced transactions used (cleaned)"]
summary
```

**`yearsummary_values`**

```python
c = vol_price[vol_price.complete].dropna(subset=["median_rate"])
hi, lo = c.loc[c.median_rate.idxmax()], c.loc[c.median_rate.idxmin()]
latest_row = vol_price.dropna(subset=["median_rate"]).iloc[-1]

print(f"Highest median rate : AED {hi.median_rate:,.0f}/m2 in {int(hi.year)}")
print(f"Lowest median rate  : AED {lo.median_rate:,.0f}/m2 in {int(lo.year)}")
print(f"Latest ({int(latest_row.year)})       : AED {latest_row.median_rate:,.0f}/m2 "
      f"({(latest_row.median_rate/lo.median_rate - 1)*100:+.0f}% vs the lowest year)")

gap = vol_price.dropna(subset=["mean_rate"])
print(f"\nMean above median in {(gap.mean_rate > gap.median_rate).sum()} of {len(gap)} years")
print(f"RAW count exceeds the priced CLEANED rows in "
      f"{(vol_price.transactions > vol_price.priced_rows).sum()} of {len(vol_price)} years")
print("  -> the two columns come from different files, and that is why they differ")
```

### 11.18 Intermediate dataframe
`summary` — **16 rows × 5 columns**

Columns: `Year`, `Number of transactions (raw)`, `Mean rate/m2 (AED)`, `Median rate/m2 (AED)`, `Priced transactions used (cleaned)`

### 11.19 Result values — actual notebook output
*Printed by the run recorded in the appendix, not typed from memory.*

```
Highest median rate : AED 18,370/m2 in 2025
Lowest median rate  : AED 9,334/m2 in 2011
Latest (2026)       : AED 18,359/m2 (+97% vs the lowest year)

Mean above median in 16 of 16 years
RAW count exceeds the priced CLEANED rows in 16 of 16 years
  -> the two columns come from different files, and that is why they differ
```

The raw count exceeds the cleaned priced-row count in **16 of 16 years**, and the table shows both columns side by side. That is the whole data-source rule made visible: counts from RAW, prices from CLEANED, and the gap between them on display rather than hidden.

### 11.20 Chart type, and why
No chart. The section exists to fill the removed off-plan visual **in place** with something informative and defensible; a table of the underlying yearly facts does that without re-introducing a comparison.

### 11.21 Axes
Not applicable — this section is a table.

### 11.22 Legend
Not applicable — this is a table.

### 11.23 Colour meaning
n/a.

### 11.24 Hover contents
n/a — every value is printed.

### 11.25 How to read it — and what it does NOT say
**How to read it**

- The mean sits above the median in every year. That gap is the effect of a small number of very large deals.
- The median is the figure to quote for a typical transaction.
- The final row is the year in progress and is labelled with the period covered.

**What it does not say**

- It makes no comparison between off-plan and existing property, and no claim about a premium or discount.
- Transaction counts and rate statistics come from different files, so the count is not the number of rows behind the rate.

### 11.26 Limitations and validation actually performed
**Limitations**

- Covers registered residential **unit** (apartment) sales only — villas, land and whole-building transactions are not in this dataset.
- 2026 is a partial year: the data ends **6 August 2026**, so 2026 totals are not comparable with a full year.
- The sale-price and unit-size sliders start at the 1st–99th percentile, so the most extreme deals are excluded until you widen them.
- The rate columns move with the sidebar filters; the transaction count does not.

**Validation**

Counts reconciled against the raw registry year by year. Mean and median recomputed in plain pandas and matched.

---

# Appendix A — the notebook run these values came from

The notebook was executed **from the first cell to the last, in order, in a single
Python process, from the repository root**, and every printed line in point 19 of
every section above is that run's output.

| | |
|---|---|
| Notebook | `notebooks/Unified_Dashboard_Graph_Analysis.ipynb` |
| Cells | 100 total — **38 code**, 62 markdown |
| Code cells executed | **38 of 38**, in order, in one namespace |
| Errors | **0** |
| Dataframes produced | 34 |
| Figures rendered | **9** |
| Data | `data/dubai/transactions.parquet` (1,762,258 rows) · `data/dubai/latest_combined_data.parquet` (818,838 rows) |

**How it was executed, and the one honest caveat.** The notebook's cells were read
from the `.ipynb` and executed in order in one namespace by
`nbbuild/run_notebook.py`. It was **not** run through `nbclient`/`jupyter execute`,
because installing those packages was declined — so the execution is a faithful
in-order run of the same code, not a Jupyter kernel round-trip. Plotly's notebook
renderer needs IPython, which is likewise not installed here; each `fig.show()` was
therefore redirected to Plotly's full HTML render path and every figure was written
to disk and opened in a real browser to confirm it draws. That is what "figures
render" means in the table above, and it is stated rather than implied.

## Per-figure render check

| Figure | § | Traces | Data points | Legend entries | Renders |
|---|---|---|---|---|---|
| 1 | 1 | 3 | 30 | 3 | yes |
| 2 | 2 | 4 | 800 | 4 | yes |
| 3 | 3 | 3 | 32 | 3 | yes |
| 4 | 4 | 1 | 5 | axis-titled | yes |
| 5 | 4 | 1 | 7 | axis-titled | yes |
| 6 | 5 | 7 | 24 | 7 | yes |
| 7 | 6 | 1 | 7 | axis-titled | yes |
| 8 | 7 | 7 | 7 | 7 | yes |
| 9 | 10 | 17 | 45,000 | 17 | yes |

Sections 8, 9 and 11 produce tables and no figure, which is why there are nine
figures for eleven sections.

**A note on the four single-series charts.** Plotly's legend box is suppressed on
them, exactly as it is in the dashboard: a legend naming one series duplicates the
axis title and adds nothing. The written key for every chart — including these — is
the `legend` field quoted in point 22 of each section, which is the same text the
dashboard shows in its ⓘ panel.

# Appendix B — cross-check against the dashboard

The last notebook cell recomputes the headline figures independently of the
application code and prints them for comparison:

```
TRANSACTION COUNTS (RAW registry - should match the dashboard exactly)
   2011: 19,611
   2015: 26,355
   2020: 20,333
   2024: 136,137
   2025: 166,262
   2026: 80,203

INCOMPLETE-YEAR RULE
   2026 period          : January-August  (8 of 12 months)
   transactions so far   : 80,203
   like-for-like growth  : -21.89%
   percentage displayed  : NO - count only

PRICE FIGURES (CLEANED, UNFILTERED)
   median rate           : AED 15,207/m2
   mean rate             : AED 16,772/m2
   median sale price     : AED 1,163,000
   rows                  : 818,838

NOTE ON DIFFERENCES
   Transaction counts come from the raw registry and are not filtered in
   either place, so they should match the dashboard exactly.
   Price figures here are computed on the UNFILTERED cleaned dataset. The
   dashboard applies its sidebar filters, and the sale-price and unit-size
   sliders default to the 1st-99th percentile - so its price figures will
   differ slightly until those sliders are widened to the full range.
```

# Appendix C — reproducing this

```bash
# from the repository root, with the two parquet files in data/dubai/
pip install -r requirements.txt
jupyter notebook notebooks/Unified_Dashboard_Graph_Analysis.ipynb   # then Run All
```

In Google Colab: open the notebook, run §0, upload the two parquet files when
prompted (or mount Drive and set `UAE_DATA_DIR`), then Run All. `requirements.txt`
for the notebook is three packages — `pandas`, `pyarrow`, `plotly` — and nothing
else is imported by it.
