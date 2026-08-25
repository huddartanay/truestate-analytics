# 🏙️ TruEstates Analytics

One unified analytics platform for the UAE property market.

Two regional dashboards — **Abu Dhabi** and **Dubai** — plus a separate
**Experimental Analysis** environment holding the modelling work behind them.
One entry point, one navigation, one design system.

> **Local development build. Not deployed.**
> Nothing has been pushed to Streamlit Cloud and no existing deployment has been touched.

---

## Run it

```bash
cd uae-real-estate-analytics

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

streamlit run streamlit_app.py
```

Then open <http://localhost:8501>.

The first time you open **Abu Dhabi** it parses a 20 MB transaction file and takes
around 45 seconds; it is cached for the rest of the session. **Dubai** takes about
8 seconds on first load and ~4 seconds thereafter.

---

## What's inside

| | |
|---|---|
| 🏠 **Overview** | Landing page — what the platform is, and a route into each environment |
| 🇦🇪 **Abu Dhabi** | The existing transaction dashboard: 12 analytical tabs, live sidebar filtering |
| 🇦🇪 **Dubai** | The regional dashboard: Executive KPIs, Smart Business Insights and Market Snapshot, then Insights · Trends · Geography · Property · Price · Distribution |
| 🧪 **Experimental Analysis** | The research environment: V1, V2, V2.1, FC, Area Combination and V2.2, preserved as built |
| 🧭 **Explore Platform** | A map of every section, with a direct route to each |
| ℹ️ **About** | Architecture, data sources and disclaimers |

---

## Layout

```
streamlit_app.py      the only entry point — owns page config, design, navigation, routing
platform_core/        the shell (no analytics live here)
platform_pages/       overview · explore · about · the three environment pages
regions/abu_dhabi/    the existing Abu Dhabi dashboard, preserved
regions/dubai_market/ the Dubai regional dashboard (new)
regions/dubai/        the existing experiments, preserved
data/dubai/           the raw + cleaned Dubai datasets and their provenance record
tools/                provenance builder · chart reference guide builder
docs/                 architecture · integration change log · checklist · chart reference guide
```

## The rule this was built on

The existing dashboards are the source of truth. **No analytical logic was
rewritten.** Ten chrome-only edits were made across the two codebases — page
configuration, branding, navigation and hiding `Data Summary` — each documented
in [`docs/INTEGRATION_CHANGES.md`](docs/INTEGRATION_CHANGES.md).

Every view was executed in both the original and the unified app and compared on
KPI values, table contents and chart data: **27 of 27 identical**. Every Dubai
headline figure was independently recomputed from the parquet with plain pandas:
**31 of 31 verified** (`python tests/verify_dubai_numbers.py`). The six charts
reworked in v1.2 are recomputed the same way: **87 of 87 verified**
(`python tests/verify_dubai_changes.py`).

Every Dubai chart carries an ⓘ icon documenting what it shows, which dataset it
reads, how it is calculated, what it does *not* tell you and how it was checked.
The same registry generates the company-facing
[`docs/Dubai_Analytics_Chart_Reference_Guide.docx`](docs/Dubai_Analytics_Chart_Reference_Guide.docx),
so the two cannot drift apart:

```bash
python tools/build_chart_reference_docx.py
```

Both regions also still run standalone, exactly as before:

```bash
streamlit run regions/abu_dhabi/app.py     # the Abu Dhabi dashboard
streamlit run regions/dubai/trial.py       # the experiments, Data Summary included
```

---

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — architecture and conflict assessment (written before implementation)
- [`docs/INTEGRATION_CHANGES.md`](docs/INTEGRATION_CHANGES.md) — every line that changed, and why
- [`docs/CHECKLIST.md`](docs/CHECKLIST.md) — build status, test results, known issues
- [`docs/Dubai_Analytics_Chart_Reference_Guide.docx`](docs/Dubai_Analytics_Chart_Reference_Guide.docx) — every Dubai chart explained, for company review
