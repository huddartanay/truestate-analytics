# Apply this update and run it

This package contains **all the code**, with every edit from this round of work
already in it. It does **not** contain the datasets or the two large regional
asset folders — you already have those, and shipping 450 MB of unchanged data
would be pointless.

## Install

```bash
cd ~/Downloads/uae-real-estate-analytics
unzip -o ~/Downloads/uae-complete.zip
```

`-o` overwrites without prompting. This replaces the code and leaves
`data/`, `regions/dubai/`, `regions/abu_dhabi/` and `.venv/` untouched.

## Run

```bash
pkill -f streamlit
cd ~/Downloads/uae-real-estate-analytics
source .venv/bin/activate
streamlit run streamlit_app.py --server.port 8501
```

Open **http://localhost:8501**.

**No `pip install` is needed.** The PDF report is built with `matplotlib`,
which is already in your virtual environment. Nothing new was added to
`requirements.txt`.

## Check you are on the new build

Open **🇦🇪 Dubai**. At the very top, above Executive KPIs, you should see a
dropdown labelled **📍 Area — applies to this entire Dubai dashboard**, and the
tab row should end with **📄 Download Report**. If neither is there, the unzip
did not land in this folder.

```bash
cd ~/Downloads/uae-real-estate-analytics
source .venv/bin/activate
python tests/verify_v14_changes.py | tail -3
```

Expect `ALL 86 CHECKS PASSED`. If the file is missing, the unzip did not land
in the right folder — make sure you are in `uae-real-estate-analytics`, not
`uae-real-estate-analytics 2`.

## New in this build — the Forecast

**Where it is.** Inside **📄 Download Detailed Report**, below the PDF section.
Both places that show that area carry it: the rail page and the 7th tab on the
Dubai dashboard.

**The area is read-only.** There is no second area selector. The Forecast reads
the global 📍 Area and shows it in a disabled control. Change the area and the
Forecast reloads that area's valid inputs, resets anything the new area does not
accept (and says which), and drops any forecast held for the previous area
before it draws.

**`input_ranges.csv` was not in the codebase.** It is now, at
`data/dubai/input_ranges.csv` — your uploaded copy, unchanged. If it is ever
missing the Forecast says so and offers nothing rather than guessing ranges.

**Check the API from your Mac before anything else:**

```bash
cd ~/Downloads/uae-real-estate-analytics
source .venv/bin/activate
python tests/verify_forecast_api.py
```

This hits `http://51.38.112.237:9500/forecast` live and prints exactly what
comes back. It could not be run from the machine this build was prepared on —
that host is blocked there — so this is the first real call.

Two lines in its output matter:

* **Forecast horizon.** If it prints 5 or 6 months, the 1Y / 2Y / 3Y+ control
  is correctly a *historical window* control, and the forecast lines stop after
  those months. Nothing is repeated or extrapolated to fill a longer window.
* **Uncertainty fields.** If it prints `none`, the chart is right to draw no
  confidence band. The shaded region on the chart is the gap between the macro
  and news-adjusted lines — both returned by the API — and is labelled as that.
  If it lists a field, tell me and a real band can be drawn from it.

**No new dependency.** The client uses `urllib` from the standard library.
`requirements.txt` is unchanged.

## What is in this build

**Sidebar order**

```
🏠  Overview
    LOCATIONS
🇦🇪  Abu Dhabi
🇦🇪  Dubai
📍  Area                        ← one global Dubai area selector
📄  Download Detailed Report    ← sits between Area and Experimental
🧪  Experimental Analysis
    PLATFORM
🧭  Explore Platform
ℹ️  About
```

**📍 Area — right at the top of the Dubai page.** A single dropdown above the
Executive KPIs. Pick an area and the *entire* Dubai dashboard recalculates:
KPIs, insights, snapshot, all six analytical tabs and the report. The dataframe
is filtered before any grouping runs, so the numbers change, not just the
titles. No individual chart has its own area dropdown. The 📍 Area page in the
rail writes the same setting — one control, two places.

**📄 Download Report — the 7th tab in the Dubai dashboard**, immediately after
Distribution. The PDF builds itself when you open the tab and rebuilds whenever
the area changes, so the download button is simply there. There is also a
Download Detailed Report page in the rail; both produce the same file.

The report is 8–9 pages: title page, executive summary, transaction volume,
price movement, layout, building height, amenities, registration type, price
brackets with top-5 areas, and methodology.

**🧪 Experimental Analysis** — the six original generations are untouched. A
seventh, *Trend Smoothing · LOWESS vs Exponential*, has been added alongside
them.

**Dubai dashboard**

- Registration-type summary carries **Mean Price** beside the median.
- The price trend uses a **centred LOWESS** fit; the partial final month is
  excluded from the fit, so the trend stops at the last complete month.
- The amenity chart compares your slice against the Dubai baseline, so parking
  — recorded on 88.9%–100% of everything — no longer dominates by construction.
- "Where the price points are" ranks the **top 5 areas in every price bracket**,
  including above AED 10M.

## Verified before shipping

Extracted to an empty folder and run from there: all eight routes render with
zero exceptions, the global area moves the Dubai figures (791,126 → 15,701 for
Palm Jumeirah), and the PDF generates for every area tested.

| Suite | Result |
|---|---|
| `tests/verify_v14_changes.py` | 86 / 86 |
| `tests/verify_dubai_changes.py` | 221 / 221 |
| `tests/verify_dubai_numbers.py` | 31 / 31 |
| `tests/verify_notebook_and_doc.py` | 55 / 55 |
| `tests/regression.py all` | 27 / 27 views identical to the originals |

Abu Dhabi and all six original experiment generations are byte-identical to
the originals.

## If something goes wrong

Streamlit prints a `use_container_width` deprecation notice on startup. It is
harmless — that API is used throughout the original code and works until the
end of 2025.

The first load of the Dubai page or an All-Areas report takes 15–30 seconds
while the 52 MB dataset is read and cached. Everything after that is a couple
of seconds.
