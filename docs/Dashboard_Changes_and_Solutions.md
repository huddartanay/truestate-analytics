# Dashboard Changes and Solutions

**Scope:** the Dubai section of the unified TruEstates analytics platform.
Abu Dhabi, the Experimental Analysis environment, navigation, styling, theme and
the platform shell were not modified. Local build — not deployed.

---

## 1. Summary of implemented changes

| # | Change | Type |
|---|---|---|
| 1 | Transaction-volume analysis moved onto the **RAW** registry | Replaced |
| 2 | Year-over-year chart rebuilt with the incomplete-year rule | Replaced |
| 3 | Amenity analysis replaced by a **controlled property-type + amenity** comparison | Replaced |
| 4 | New **building-height** price analysis (see §11 for the floor-level limitation) | Added |
| 5 | Off-plan pricing chart replaced by a **year-by-year summary table** | Replaced |
| 6 | Off-plan premium/discount removed | Removed |
| 7 | "Why off-plan looks more expensive" removed | Removed |
| 8 | Amenity headline comparison removed | Removed |
| 9 | Unit-size histogram replaced by a **unit-size statistics table** | Replaced |
| 10 | Sale-price-by-registration-type box plot replaced by a **registration-type summary table** | Replaced |
| 11 | Published price forecast replaced by a **market-history insight panel** | Replaced |
| 12 | Price-range explanation added to the distribution charts | Added |
| 13 | Price-distribution chart reviewed and preserved | Reviewed |
| 14 | Legends audited on every remaining chart | Verified |

Every removed section's position is now occupied by a replacement on the same
subject. No blank space was left, and no unrelated chart was added.

---

## 2–8. Each modified visualisation

### 2.1 Year-over-year transaction growth

**Original problem.** The chart counted transactions in the **cleaned** dataset and
compared the incomplete 2026 period against a full 2025, producing a −52.9% bar
that read as a market collapse.

**Solution.** Rebuilt as *Transactions recorded each year*, counting from the raw
registry, with the incomplete year given its own series and no growth figure
unless growth is strictly positive.

**Methodology.** Counts per year from the raw registry. Completed years:
`((this year − previous year) ÷ previous year) × 100`, chained. 2011 is the base
year and carries no percentage.

**Data source: RAW** (`data/dubai/transactions.parquet`).

**Why RAW.** Preprocessing removes rows from the cleaned file. Measured
year by year, the shortfall is **668 to 7,369 transactions**:

| Year | RAW residential unit sales | Cleaned | Removed by cleaning |
|---|---|---|---|
| 2011 | 19,611 | 18,355 | 1,256 |
| 2015 | 26,355 | 25,413 | 942 |
| 2020 | 20,333 | 18,405 | 1,928 |
| 2024 | 136,137 | 128,768 | 7,369 |
| 2025 | 166,262 | 159,477 | 6,785 |

A transaction count must state how many transactions were recorded, so it is
counted where nothing has been removed.

**Which raw slice.** Residential unit sales — the same population every other
Dubai chart uses (928,489 rows). Counting the entire registry instead would
change the subject from residential sales to sales + mortgages + gifts across
land and villas. The whole-registry figure (1,762,258) is reported alongside it
in the hover and in the expandable table, so neither is hidden.

**Interpretation.** Volume grew every year from 2021 to 2025, peaking at 166,262
registrations in 2025. Contractions in 2014, 2015, 2016, 2018 and 2020 are
genuine and were kept.

---

### 2.2 The 2026 rule (validated before implementation, §20)

Computed from the raw registry:

| Figure | Value |
|---|---|
| Latest date in the registry | **2026-08-06** |
| Latest 2026 month | **8 (August)** — detected dynamically, never hard-coded |
| Months available | 8 of 12 |
| 2026 transactions to date | **80,203** |
| Comparison basis — Jan–Aug 2025 | **102,675** |
| 2025 full year | 166,262 |
| Like-for-like growth | **−21.9%** |

**−21.9% is not strictly positive, so no percentage is displayed for 2026.** The
chart shows the count only. The bar is amber, it has its own legend entry —
*"2026 — January–August only (in progress)"* — and its hover reads *"Part year —
not comparable with a full year"*. The growth line simply has no point at 2026.

The period label is derived from `max(month)` in the raw data at run time. If the
registry is refreshed to September, the label, the basis and the rule all move
with it.

---

### 3. Hover information

| Series | Hover shows |
|---|---|
| Completed year | Year · Transactions recorded · All registry transactions |
| Incomplete year | Year and period · Transactions recorded so far · All registry transactions · "Part year — not comparable with a full year" |
| Growth line | Year · Growth vs previous year (%) — completed years only |

---

### 4. Property type + amenity analysis

**Original problem.** The amenity charts compared every unit with a feature
against every unit without it across the whole market, so the comparison was
dominated by which property types sat on each side.

**Solution.** *Price with and without an amenity, by property type* — two filters,
and the comparison never leaves the selected property type.

- **Property type filter:** Studio, 1 BHK, 2 BHK, 3 BHK, 4 BHK, 5 BHK, Penthouse.
  These map to the dataset's own `rooms_en` values (`Studio`, `1 B/R` … `5 B/R`,
  `PENTHOUSE`). No category was invented; `6 B/R` (82 rows) and `7 B/R` (4 rows)
  exist but never clear the reporting threshold.
- **Amenity filter:** Parking, Swimming pool, Balcony, Elevator, Near a metro
  station — the five binary flags that exist in the dataset. No other valid
  amenity field was found: `swimming_pools` and `elevators` are counts of the
  same features, and `unit_balcony_area` is an area, not a flag.

**Methodology.** Filter to the property type → split by the amenity flag →
`median(meter_sale_price)` on each side, with the 25th and 75th percentiles drawn
as a range through each bar. Both sides must hold **≥100 transactions** or the
comparison is withheld with an explanation.

**Data source: CLEANED** — the amenity flags exist only there.

**Interpretation and wording.** The output is described as an **observed
difference between two groups of recorded transactions**. The on-screen text
states explicitly that it does not establish causation, that the two groups can
still differ by building, age, floor area and location, and that a `0` means
*not recorded*, not *confirmed absent*. Median unit size is shown for both sides
so a reader can see when the two groups are not the same kind of property. No
"+102%"-style causal statement appears anywhere.

**Validated cell sizes:** 29 of the 30 property-type × amenity combinations have
enough data. The exception — 5 BHK × Parking, which has zero units recorded
without parking — is correctly reported as insufficient rather than as a result.

---

### 5. Floor-wise price analysis → **building height**

**What was requested:** how price varies by floor level, by property type.

**What the data supports — investigated before implementing:**

| Field | Finding |
|---|---|
| `floor_bin` | 61.8% of rows carry the literal string `Unknown`; the remaining 38.2% are null. **No floor information at all.** |
| `floors` | Populated for 58.8% of rows, range 0–107. **Constant within `property_id_bld` in 100.0% of buildings.** Princess Tower = 89 on all 1,723 of its sales; Elite Residence = 75 on all 1,596. |
| `bld_levels` | Same character, correlated 0.987 with `floors`. |
| Raw registry | Contains no floor field at all. |

**Conclusion: the dataset does not record which floor a unit is on.** A true
floor-level analysis cannot be produced from these files. Rather than invent
buckets over a building attribute and label them "floors", the panel answers the
closest question the data does support — **does the rate differ by building
height?** — and says so in a warning on the chart.

**Bucket methodology (data-driven, §5).** Boundaries are the quartiles of the
height distribution taken **one row per building**, so a single tower with
thousands of sales cannot move them. Computed at run time on the current
selection:

| Band | Transactions |
|---|---|
| Low-rise (≤5 floors) | 87,719 |
| Mid-rise (6–9) | 84,660 |
| High-rise (10–16) | 98,474 |
| Tower (>16 floors) | 210,565 |

**Chart.** X = height band, Y = median rate per m², legend = property type.
Combinations below 100 transactions are omitted and **named on screen**
(Penthouse in low-rise and mid-rise, 5 BHK in mid-rise and high-rise). Height is
recorded for 58.8% of transactions and the coverage is stated.

**Interpretation.** The rate rises with building height for every property type —
1 BHK from AED 8,342/m² in low-rise to AED 14,650/m² in towers, Studio from
7,674 to 13,586. Height and location are entangled, and the chart says so.

---

### 6–8. Off-plan sections

- **Off-plan vs existing pricing chart — removed**, replaced in the same position
  by the year-by-year summary table (Year · Number of transactions · Mean rate/m²
  · Median rate/m²). Transaction counts come from RAW, rate statistics from
  CLEANED, and each column is labelled with its source. 2026 is labelled
  *"(January–August, in progress)"*.
- **Off-plan premium or discount — removed.** No premium or discount is computed
  or stated anywhere on the page.
- **"Why off-plan looks more expensive" — removed.** Not replaced with another
  causal explanation.
- The registration-type **share** donut in the Property section was not listed for
  removal and is unchanged.

---

### 9–12. Removals with in-position replacements

| Removed | Replacement in the same position | Source |
|---|---|---|
| Unit size distribution (Distribution, left) | **Unit size — key statistics**: per property type, transactions and the smallest / 25th / median / 75th / largest floor area | CLEANED |
| Sale price by registration type (Distribution, right) | **Sale price by registration type — summary**: per type, transactions, share, 25th/median/75th price and median rate. Descriptive only — the two rows are not compared | CLEANED |
| Published price forecast (end of Price) | **What the record shows**: latest median rate, highest and lowest years, average change per year, with the year-by-year record. A forecast is not replaced with another forecast | CLEANED |

---

### 10. Price-range explanation

Added under the two histograms, describing the calculation that actually runs:

- **Minimum / maximum**: the cheapest and dearest single transactions in the
  selection, named as single transactions rather than typical values.
- **Where the market concentrates**: the 25th–75th percentile band and the median,
  quoted with the share of transactions inside it.
- **Where one property sits**: how to locate a price on the axis and read the bar
  height as "how many others were priced like this".
- **The methodology, named**: the bars cover the **0.5th to 99.5th percentile**,
  that span is divided into **60 equal-width bins**, and the bar height is the
  count per bin. The 1% outside the display span is still included in the median,
  the minimum and the maximum. Every figure in the text is recomputed from the
  same selection, so the words cannot describe one thing while the chart draws
  another.

---

### 13. Price-distribution review — *"How the price distribution has changed"*

**Reviewed:** data source, filtering, price variable, sampling, year grouping,
distribution calculation, plotting method, tooltip, axis handling, and whether it
answers the question.

| Aspect | Finding |
|---|---|
| Data source | CLEANED — correct for a price analysis |
| Variable | `meter_sale_price` — correct; rate per m² removes unit size from the comparison |
| Grouping | One violin per year — correct for "how has the distribution changed" |
| Sampling | 45,000 rows, `random_state=42` (deterministic) |
| **Sampling fidelity** | Worst per-year median error **2.47%**, worst 75th-percentile error **1.66%**; smallest per-year sample **989** rows |
| Distribution | Kernel density with an inner box plot — appropriate |
| Legend | Colour encodes the year, which the x-axis already labels; no legend is needed and none is forced (§16 allows this for single-series-per-category charts) |

**Verdict: the methodology is sound and was preserved.** No change was made to the
calculation. The claim it supports — that the distribution has both moved up and
widened — is visible in the chart and consistent with the summary statistics
table beneath it.

---

### 14. Legend and visualisation improvements

Every remaining Dubai chart was checked. Multi-series charts carry a legend with
business-friendly labels:

| Chart | Legend |
|---|---|
| Transactions recorded each year | Transactions recorded · 2026 — January–August only (in progress) · Year-over-year growth (%) |
| Monthly market activity | Transactions · Total value (AED) · 3-month average |
| How prices are moving | Median sale price / Median rate — actual and 3-month trend |
| Price with and without an amenity | With *amenity* · Without *amenity* (both named dynamically) |
| Rate by building height | One entry per property type present in the selection |
| Size against price | One entry per layout |
| Locality zones | Median rate · Transactions |

Single-series charts (annual volume, seasonality, area rankings, histograms,
price bands, treemap, heatmap, violins) carry titles and axis labels instead of a
forced legend, as §16 permits. No legend entry refers to data that is not
plotted, and legend labels move with the filters.

---

### 15. Validation performed

| Check | Result |
|---|---|
| RAW row count | 1,762,262; 4 null dates; **0 duplicate transaction ids** |
| RAW date range | 1966-01-18 → **2026-08-06** |
| RAW slices | all 1,762,262 · sales 1,349,853 · sales+unit 1,038,690 · **sales+unit+residential 928,489** |
| Cleaned row count | 818,838, date range 2010-01-01 → 2026-08-06 |
| Yearly counts | Recomputed per year on RAW and matched to the dashboard |
| Latest 2026 month | 8 — derived from the data, asserted not hard-coded |
| 2026 rule | Like-for-like −21.9% → percentage suppressed, count shown |
| Amenity values | All five flags complete 0/1, no nulls, no imputation |
| Property-type values | Every label maps to a real `rooms_en` value |
| Floor distribution | `floor_bin` unusable; `floors` constant within building in 100.0% of cases |
| Price statistics | Mean and median per year recomputed and matched |
| Missing values | Height missing for 41.2% of rows — stated on screen, rows excluded not imputed |

**Automated:** `python tests/verify_dubai_changes.py` → **210 / 210 checks passed**
(71 of them new for these changes).

---

### 16. Local testing performed

The application was executed locally (`streamlit run streamlit_app.py`) and driven
in a real browser at 1600 px.

| Test | Result |
|---|---|
| Application starts | HTTP 200, **0 errors in the server log** |
| Python errors / missing imports / missing files | None |
| Headless render of the Dubai route | 19 metrics · 16 dataframes · 27 figures · **0 exceptions** |
| Browser JavaScript errors | **None** |
| Charts render | All verified by screenshot |
| Property-type filter | Rendered and switched |
| Amenity filter | Rendered and switched |
| Floor/height buckets | Four bands render with the property-type legend |
| 2026 display logic | Count shown, amber, no growth point — verified visually and by test |
| Hover information | Verified on the volume chart, amenity bars and height bars |
| Yearly table | Renders with both sources labelled |
| Price distribution | Renders unchanged |
| Dark mode | Verified on the height chart |
| **Regression — Abu Dhabi and Experimental** | **27 / 27 views byte-identical to the original applications** |
| Dubai headline figures | **31 / 31** unchanged |

**One defect found and fixed during testing.** The first build of the volume chart
drew every year on top of 2011. The cause was `add_annotation` anchored to a value
on a `type="category"` axis, which collapses the axis in this Plotly build. It was
isolated by rendering the figure outside Streamlit and bisecting the figure spec.
The annotation was replaced with a second bar series for the incomplete year,
which also gives it its own legend entry and hover text.

---

## Known limitations

1. **Unit floor level is not in the data.** The height panel is labelled as
   building height and cannot answer whether a higher floor sells for more inside
   the same building.
2. **Building height is missing for 41.2% of transactions**; those rows are
   excluded from that panel and the coverage is displayed.
3. **The volume chart ignores the sidebar filters** by design — it reports what was
   registered, not what matches a selection. This is stated on the chart and in
   its ⓘ.
4. **The summary table mixes two sources by design** — raw counts, cleaned rates.
   Each column is labelled, and the number of priced rows actually used is shown.
5. **Only the parking flag also exists in the raw registry.** Pool, balcony,
   elevator and metro are engineered fields in the cleaned dataset.
