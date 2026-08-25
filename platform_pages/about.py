"""About the unified platform."""

from __future__ import annotations

import streamlit as st

from platform_core import components as ui
from platform_core import config as C


def render() -> None:
    ui.breadcrumb("TruEstates Analytics", "About")

    ui.hero(
        eyebrow="ℹ️ About",
        title_html='About this <span class="accent">platform</span>',
        lede=(
            "One enterprise shell over two regional analytics environments and one research "
            "environment. The shell and the Dubai dashboard are new; the Abu Dhabi dashboard "
            "and the analytical experiments are the originals, preserved."
        ),
    )

    ui.section("Design principle", "Product integration, not a code merge.", "🧩")

    st.markdown(
        """
The Abu Dhabi dashboard and the Dubai experiments are treated as the **source of truth**.
They were wrapped, isolated and integrated — not rewritten. No data processing, feature
engineering, statistical calculation, model output, forecast or KPI formula in that existing
work was modified.

What is new is everything *around* it: the global entry point, the design system, the
navigation rail, the landing and orientation pages, the runtime that lets several
applications share one browser session — and the **Dubai regional dashboard**, built from
the supplied Dubai datasets to mirror the structure Abu Dhabi already established.
        """
    )

    c1, c2 = st.columns(2, gap="large")

    with c1:
        ui.section("Architecture", "", "🏗️")
        st.code(
            """uae-real-estate-analytics/
├── streamlit_app.py          ← the only entry point
├── platform_core/            ← NEW shell (config, design,
│                                nav, components, runtime,
│                                chart theme, region bridge)
├── platform_pages/           ← overview / explore / about
│                                + the three environment pages
├── regions/
│   ├── abu_dhabi/            ← existing modular dashboard
│   ├── dubai_market/         ← NEW Dubai regional dashboard
│   │   ├── data.py  metrics.py
│   │   └── charts.py  dashboard.py
│   └── dubai/                ← existing experiments (trial.py)
├── data/dubai/               ← raw + cleaned parquet, provenance
├── tools/                    ← provenance builder
└── docs/                     ← architecture & change log""",
            language="text",
        )

    with c2:
        ui.section("Data sources", "", "📦")
        st.markdown(
            """
| Environment | Source | Coverage |
|---|---|---|
| **Abu Dhabi** | Abu Dhabi DMT transaction records | 2019 – 2026 |
| **Dubai** | Dubai transaction registry (cleaned residential-unit sales) | 2010 – 2026 |
| **Experimental** | Pre-computed analytical artefacts from the modelling notebooks | varies |

**Abu Dhabi** runs from a single cleaned transaction file, re-filtered live from the sidebar.

**Dubai** runs from `latest_combined_data.parquet` — 818,838 residential unit sales enriched
with time parts, unit attributes, amenity flags and building / developer scoring. The raw
registry (`transactions.parquet`, 1.76M rows) ships alongside it and is compared against the
cleaned file in the *Where this data comes from* panel on the Dubai page.

**Experimental Analysis** reads the aggregated tables, saved model files and forecast outputs
produced by the original modelling notebooks. It does not retrain anything at runtime.
            """
        )

        ui.section("Environment isolation", "", "🔒")
        st.markdown(
            """
- One global `st.set_page_config()`, owned by the platform.
- Platform routing state is namespaced `uae.*`; Dubai's filters are namespaced `dxb_*`.
- Each embedded environment executes from its own working directory, so its data paths
  resolve unchanged.
- A failure inside one environment is caught and reported without taking down the shell.
            """
        )

    ui.section("Reading the numbers", "", "🔍")
    st.markdown(
        """
- **Median over mean.** Property prices are right-skewed — a few very large deals pull the
  average up. Medians are used for headline comparisons throughout.
- **Rate per m² over total price.** Total price mixes size with value. Rate per square metre
  is the like-for-like comparison.
- **Association, not causation.** The amenity analysis on the Dubai *Price* section reports
  how prices differ between units that do and do not have a feature, including a
  like-for-like version held within area and layout. It does not claim the amenity causes
  the difference.
- **Volume guards.** Any "highest" or "most premium" claim excludes groups below a minimum
  transaction count, so one unusual sale cannot top a ranking.
        """
    )

    ui.section("Scope and disclaimers", "", "⚠️")
    st.info(
        "This platform is for **analytical and informational purposes only**. It does not "
        "constitute financial, legal or investment advice. Past market trends do not guarantee "
        "future performance. Model outputs and forecasts carry uncertainty and should be read "
        "alongside their published metrics."
    )

    st.caption(
        f"TruEstates Analytics · v{C.PLATFORM_VERSION} · local development build · "
        "not deployed"
    )

    ui.footer(C.PLATFORM_VERSION, "About")
