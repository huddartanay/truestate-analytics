# Tests

`verify_dubai_numbers.py` — recomputes every Dubai headline figure (Executive
KPIs, Market Snapshot, Smart Business Insights, amenity comparisons) directly
from `data/dubai/latest_combined_data.parquet` with plain pandas, and compares
against what `regions/dubai_market/metrics.py` produces.

```bash
python tests/verify_dubai_numbers.py
```

31 checks. This is the evidence behind the claim that nothing on the Dubai page
is fabricated.

---

`verify_dubai_changes.py` — independently recomputes the six analyses reworked
in v1.2 (year-over-year, rate per m² by layout, price smoothing, the off-plan
premium, the amenity comparison and the price bands) from the cleaned parquet
*and* the raw registry, and compares against `metrics.py` / `charts.py`.

```bash
python tests/verify_dubai_changes.py
```

87 checks. Every figure quoted in `docs/Dubai_Analytics_Chart_Reference_Guide.docx`
is covered here.

---

`regression.py` (in the working directory beside the repo, with `harness.py`)
runs each original standalone application and the unified platform headlessly
and compares every metric, dataframe and chart trace:

```bash
python tests/regression.py all      # 27 / 27 views identical
```
