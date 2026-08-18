# Notebook — Unified Dashboard Graph Analysis

Reproduces, independently of the application code, every number behind the
eleven Dubai dashboard visualisations in scope, then draws the visualisation
from those numbers.

| File | What it is |
|---|---|
| `Unified_Dashboard_Graph_Analysis.ipynb` | The notebook. 100 cells — 38 code, 62 markdown. |
| `../docs/Unified_Dashboard_Graph_and_Code_Explanation.md` | The companion document: each visualisation against 26 documentation points. |
| `requirements.txt` | The notebook's three dependencies. Separate from the app's. |

**The notebook does not import the Streamlit application.** It re-implements
each calculation in plain pandas, so agreement with the dashboard is evidence
rather than a tautology. The last cell prints the headline figures for
side-by-side comparison with the running dashboard.

---

## The two datasets

| File | What it is | Rows | Used for |
|---|---|---|---|
| `data/dubai/transactions.parquet` | **RAW** Dubai registry, exactly as supplied | 1,762,258 | Transaction **counts** and volume |
| `data/dubai/latest_combined_data.parquet` | **CLEANED** residential unit sales, enriched | 818,838 | All **price** and rate statistics |

Cleaning removes **109,651 rows (11.8%)** from the residential-unit-sale
population, so a count taken on the cleaned file understates recorded activity.
That is the whole reason for the split: **counts from RAW, prices from CLEANED**.
Where one chart needs both (§3 and §11), each column is labelled with the file
it came from and both are shown side by side.

---

## Running it

### Google Colab

1. Open `Unified_Dashboard_Graph_Analysis.ipynb` in Colab.
2. Run **§0 Setup**. If the parquet files are not present it offers an upload
   prompt; alternatively mount Drive and set `UAE_DATA_DIR` to the folder
   holding them.
3. **Runtime → Run all.**

`pandas`, `pyarrow` and `plotly` are pre-installed on Colab. The first cell
carries a commented-out `pip install` line for the rare case one is missing.

### Locally

```bash
cd uae-real-estate-analytics
pip install -r notebooks/requirements.txt

# Either run from the repository root, where data/dubai/ already exists:
jupyter notebook notebooks/Unified_Dashboard_Graph_Analysis.ipynb

# Or point it at the parquet files wherever they live:
UAE_DATA_DIR=/path/to/parquet/folder jupyter notebook notebooks/Unified_Dashboard_Graph_Analysis.ipynb
```

Then **Cell → Run All**. Total runtime is about 8 seconds on the full dataset.

---

## Structure

Every section follows the same order, so the numbers can be checked before the
picture:

> **DATA → FILTER → CALCULATION → INTERMEDIATE DATAFRAME → RESULT VALUES → VISUALISATION**

| § | Visualisation | Output |
|---|---|---|
| 0 | Setup and data loading | — |
| 1 | Transactions recorded each year (year-over-year growth) | figure |
| 2 | How prices are moving | figure |
| 3 | Volume against price | figure |
| 4 | Share of recorded transactions associated with each amenity | 2 figures |
| 5 | Rate by building height and property type | figure |
| 6 | Where the price points are | figure |
| 7 | Rate per m² by layout | figure |
| 8 | Unit size — key statistics | table |
| 9 | Sale price by registration type — summary | table |
| 10 | How the price distribution has changed | figure |
| 11 | Year-by-year summary | table |
| A | Cross-check against the dashboard | printed |

Nine figures for eleven sections: §8, §9 and §11 are tables, and §4 draws two.

---

## Three things the notebook establishes before drawing anything

These exist because the analysis they support would otherwise be an invention.

1. **§4.1 — there is no purchase outcome in this data.** Both schemas were swept
   for `purchase` / `lead` / `enquiry` / `outcome` / `conversion` / `target`
   columns: none exist. `trans_group_en` holds only Sales, Mortgages and Gifts,
   all completed. A purchase probability therefore *cannot* be calculated, and
   the metric is named for what it is — a share of recorded transactions.

2. **§5.1 — the height field is the building's, not the unit's.** `floor_bin` is
   the literal string `"Unknown"` in 100% of its populated rows, and `floors` is
   identical for every sale within a building in **100.0%** of the 2,245
   buildings tested. A unit-level floor analysis is not possible; the section is
   building height and is labelled that way.

3. **§10.1 — the 45,000-row sample is faithful.** Worst per-year median error
   **2.47%**, worst p75 error **1.66%**, smallest per-year sample 989 rows. The
   existing sampled-violin methodology was reviewed and kept on that evidence
   rather than replaced on a hunch.

---

## Verifying it

```bash
python tests/verify_notebook_and_doc.py
```

55 checks: the notebook parses, all 38 code cells execute in order in one
namespace with no error, all 9 figures render with real data, every code block
in the explanation document is byte-identical to a notebook cell, every quoted
result is what the run actually printed, all 26 documentation points are present
in all 11 sections, and the prose carries no causal claim the data cannot
support.
