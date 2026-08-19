"""
The Abu Dhabi area-wise PDF report.

Abu Dhabi's dashboard, data and analytical logic are NOT touched by this module.
It imports that region's own `utils/data_loader.py` and uses its own cleaning
path — the same `load_data()` → `get_cleaned_apartments_df()` chain the
dashboard uses — so the report cannot report numbers the dashboard would not.

WHAT THIS REPORT CAN AND CANNOT SAY
──────────────────────────────────
Abu Dhabi's file is not Dubai's. It has 17 columns, and the ones this report
uses are the ones that exist:

    District              the "area" for Abu Dhabi
    Community, Project Name
    Property Sale Price (AED), Rate (AED per SQM), Property Sold Area (SQM)
    Property Layout, Property Layout, Asset Class
    Sale Application Type, Sale Application Date, Year / Month / Quarter

There is no floor, no amenity flag, no building-height field and no registration
type in this dataset, so this report carries no section on any of them. Nothing
is filled in from Dubai and nothing is estimated to fill a gap.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from platform_core import config as C
from platform_core import pdf_report as R

AD_DIR = C.ABU_DHABI_DIR
AREA_COL = "District"


class AbuDhabiReportError(RuntimeError):
    """Raised when the Abu Dhabi data cannot be loaded — never swallowed."""


def _load_module(name: str, relative: str):
    """
    Import a module out of `regions/abu_dhabi/` without importing that region's
    app, and without leaving its directory on `sys.path` afterwards.
    """
    path = AD_DIR / relative
    if not path.exists():
        raise AbuDhabiReportError(f"{relative} was not found under regions/abu_dhabi/.")
    added = str(AD_DIR)
    inserted = added not in sys.path
    if inserted:
        sys.path.insert(0, added)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault(name, module)
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and added in sys.path:
            sys.path.remove(added)


def load_clean() -> tuple[pd.DataFrame, dict]:
    """
    Abu Dhabi's cleaned apartment frame and its column map, via that region's
    own loader. Returns `(df_cleaned, COLS)`.
    """
    try:
        settings = _load_module("_ad_settings", "config/settings.py")
        loader = _load_module("_ad_data_loader", "utils/data_loader.py")
        raw = loader.load_data()
        return loader.get_cleaned_apartments_df(raw), settings.COLS
    except AbuDhabiReportError:
        raise
    except Exception as exc:  # pragma: no cover - surfaced, never swallowed
        raise AbuDhabiReportError(
            f"The Abu Dhabi dataset could not be loaded ({type(exc).__name__}: {exc})."
        ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# CHEAP DISTRICT LIST
#
# Filling the district dropdown used to require the whole cleaned frame, which
# meant the Abu Dhabi dataset sat in memory on every visit to the report page —
# on top of the Dubai dataset. That is what pushed a hosted instance past its
# memory ceiling. This reads three columns instead of seventeen and builds the
# same list, and the full frame is loaded only when a report is actually built.
# ─────────────────────────────────────────────────────────────────────────────

AD_CSV = AD_DIR / "Abu_Dhabi_Sales_Cleaned (1).csv"


@st.cache_data(show_spinner=False)
def district_counts() -> dict[str, int]:
    """District → apartment-sale count, without loading the whole dataset."""
    if not AD_CSV.exists():
        raise AbuDhabiReportError(
            "The Abu Dhabi sales file was not found under regions/abu_dhabi/.")
    try:
        thin = pd.read_csv(AD_CSV, usecols=["Asset Class", "Property Type", "District"],
                           low_memory=False)
    except Exception as exc:  # pragma: no cover - surfaced, never swallowed
        raise AbuDhabiReportError(
            f"The Abu Dhabi district list could not be read "
            f"({type(exc).__name__}: {exc}).") from exc

    for col in ("Asset Class", "Property Type", "District"):
        thin[col] = thin[col].astype(str).str.strip().str.lower()
    apt = thin[(thin["Asset Class"] == "residential")
               & (thin["Property Type"] == "apartment")]
    counts = apt["District"].value_counts()
    del thin, apt
    return {str(k): int(v) for k, v in counts.items()}


def districts(df: pd.DataFrame) -> list[str]:
    """Districts present in the cleaned frame, busiest first."""
    if AREA_COL not in df.columns:
        return []
    counts = df[AREA_COL].dropna().value_counts()
    return [str(d) for d in counts.index]


def _title(value: str) -> str:
    """The loader lower-cases the string columns; titles read better."""
    return str(value).title() if value else value


def _aed(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(v) >= 1e9:
        return f"AED {v / 1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"AED {v / 1e6:,.2f}M"
    return f"AED {v:,.0f}"


# ─────────────────────────────────────────────────────────────────────────────
# THE DOCUMENT
# ─────────────────────────────────────────────────────────────────────────────

ALL_AREAS = "All districts"


def build(district: str = ALL_AREAS) -> bytes:
    """Render the Abu Dhabi report for one district and return the PDF bytes."""
    df_all, cols = load_clean()
    df = df_all if district == ALL_AREAS else df_all[
        df_all[AREA_COL].astype(str).str.lower() == str(district).lower()]

    if df.empty:
        raise AbuDhabiReportError(
            f"No apartment transactions are recorded in {_title(district)}, so there is "
            f"nothing to report for it.")

    rep, buf = R.new_document(
        title="Market Analytics Report",
        subtitle=f"Abu Dhabi · {_title(district)}",
        footer_note=f"Abu Dhabi analytics · {_title(district)}",
    )

    dates = pd.to_datetime(df[cols["date"]], errors="coerce").dropna()
    coverage = f"{dates.min():%d %b %Y} to {dates.max():%d %b %Y}" if len(dates) else "—"
    years = df[cols["year"]].dropna()
    period = f"{int(years.min())} – {int(years.max())}" if len(years) else "—"

    rep.title_page(
        meta=[
            ("Reporting period", period),
            ("Data coverage", coverage),
            ("District", _title(district)),
            ("Transactions analysed", f"{len(df):,}"),
            ("Share of dataset", f"{len(df) / max(len(df_all), 1) * 100:.1f}%"),
            ("Generated", R.stamp()),
        ],
        lede=(
            "An analysis of recorded residential apartment sales in Abu Dhabi, prepared "
            "from the Abu Dhabi transaction records held by the TruEstate Analytics "
            "platform. The report covers transaction activity, price and rate levels, "
            "how they have moved, the mix of layouts and unit sizes, sale type, and where "
            "activity concentrates by community and project."
        ),
    )

    rep.new_page()
    write_sections(rep, df, df_all, district, cols, period)
    return R.finish(rep, buf)


def write_sections(rep, df: pd.DataFrame, df_all: pd.DataFrame, district: str,
                   cols: dict, period: str) -> None:
    """Write the Abu Dhabi analysis into an existing report."""
    price, rate, area_sqm = cols["price"], cols["rate"], cols["area_sqm"]

    # ── 1. Executive summary ────────────────────────────────────────────────
    rep.h1("Executive summary", needs=2.4)
    rep.kpis([
        ("Transactions", f"{len(df):,}"),
        ("Total value", _aed(df[price].sum())),
        ("Median sale price", _aed(df[price].median())),
        ("Median rate per m²", _aed(df[rate].median())),
        ("Median unit size", f"{df[area_sqm].median():,.0f} m²"),
        ("Reporting period", period),
    ], per_row=3)
    rep.body(
        f"This report covers {len(df):,} recorded residential apartment sales in "
        f"{_title(district)}, which is {len(df) / max(len(df_all), 1) * 100:.1f}% of the "
        f"cleaned Abu Dhabi apartment dataset. Figures are computed at generation time "
        f"from that dataset; none is stored or hard-coded."
    )

    # ── 2. Activity over time ───────────────────────────────────────────────
    yearly = (df.groupby(cols["year"], as_index=False)
                .agg(Transactions=(price, "size"), Value=(price, "sum"),
                     MedianPrice=(price, "median")))
    yearly = yearly.dropna(subset=[cols["year"]]).sort_values(cols["year"])
    if not yearly.empty:
        rep.h1("Transaction activity", needs=2.4)

        def draw_vol(ax):
            ax.bar(yearly[cols["year"]].astype(int).astype(str),
                   yearly["Transactions"], color=R.ACCENT, width=0.62)
            ax.set_ylabel("Transactions", fontsize=7.4)

        rep.chart(draw_vol, height=2.5, title="Recorded apartment sales per year",
                  caption="Counts are of recorded sale applications in the cleaned "
                          "apartment dataset. A part-year at either end is shown as it "
                          "stands, not annualised.")
        rep.table(
            ["Year", "Transactions", "Total value", "Median price"],
            [[str(int(r[cols["year"]])), f"{int(r['Transactions']):,}",
              _aed(r["Value"]), _aed(r["MedianPrice"])]
             for _, r in yearly.iterrows()],
            widths=[1.1, 1.5, 1.9, 1.8],
        )

    # ── 3. Price and rate ───────────────────────────────────────────────────
    rep.h1("Price and rate levels", needs=2.4)
    monthly = (df.assign(_m=pd.to_datetime(df[cols["date"]], errors="coerce")
                              .dt.to_period("M").dt.to_timestamp())
                 .dropna(subset=["_m"])
                 .groupby("_m", as_index=False)
                 .agg(median_rate=(rate, "median"), median_price=(price, "median")))
    if len(monthly) >= 2:
        def draw_rate(ax):
            ax.plot(monthly["_m"], monthly["median_rate"], color=R.ACCENT_2, linewidth=1.5)
            ax.set_ylabel("Median rate (AED/m²)", fontsize=7.4)
            for lbl in ax.get_xticklabels():
                lbl.set_rotation(45)
                lbl.set_ha("right")
                lbl.set_fontsize(6.4)

        rep.chart(draw_rate, height=2.5,
                  title="Median rate per m², by month",
                  caption="The median of recorded rate per m² in each month. A median is "
                          "used rather than a mean so a handful of very large sales does "
                          "not move the line on its own.")

    q = df[price].quantile([0.25, 0.5, 0.75])
    rep.table(
        ["Measure", "Sale price (AED)", "Rate (AED/m²)", "Unit size (m²)"],
        [["Lower quartile", _aed(q.loc[0.25]), _aed(df[rate].quantile(0.25)),
          f"{df[area_sqm].quantile(0.25):,.0f}"],
         ["Median", _aed(q.loc[0.50]), _aed(df[rate].median()),
          f"{df[area_sqm].median():,.0f}"],
         ["Upper quartile", _aed(q.loc[0.75]), _aed(df[rate].quantile(0.75)),
          f"{df[area_sqm].quantile(0.75):,.0f}"],
         ["Mean", _aed(df[price].mean()), _aed(df[rate].mean()),
          f"{df[area_sqm].mean():,.0f}"]],
        widths=[1.6, 1.9, 1.5, 1.3],
        caption="Quartiles describe the middle of the market; the mean sits above the "
                "median wherever a few large sales pull it up.",
    )

    # ── 4. Layout mix ───────────────────────────────────────────────────────
    layout_col = cols["layout"]
    if layout_col in df.columns:
        lay = (df.groupby(layout_col, as_index=False)
                 .agg(Transactions=(price, "size"), MedianPrice=(price, "median"),
                      MedianRate=(rate, "median"), MedianSize=(area_sqm, "median")))
        lay = lay.sort_values("Transactions", ascending=False).head(12)
        if not lay.empty:
            rep.h1("Layout mix", needs=2.4)

            def draw_lay(ax):
                labels = [_title(v) for v in lay[layout_col]][::-1]
                ax.barh(labels, lay["Transactions"][::-1], color=R.SERIES[2], height=0.62)
                ax.set_xlabel("Transactions", fontsize=7.4)

            rep.chart(draw_lay, height=2.6, title="Transactions by layout",
                      caption="Layouts as recorded in the dataset, ranked by how many "
                              "sales carry each one.")
            rep.table(
                ["Layout", "Transactions", "Median price", "Median rate", "Median size"],
                [[_title(r[layout_col]), f"{int(r['Transactions']):,}",
                  _aed(r["MedianPrice"]), _aed(r["MedianRate"]),
                  f"{r['MedianSize']:,.0f} m²"] for _, r in lay.iterrows()],
                widths=[1.7, 1.2, 1.5, 1.3, 1.1],
            )

    # ── 5. Where activity sits ──────────────────────────────────────────────
    group_col = cols["community"] if district != ALL_AREAS else AREA_COL
    if group_col in df.columns:
        top = (df.groupby(group_col, as_index=False)
                 .agg(Transactions=(price, "size"), MedianPrice=(price, "median"),
                      MedianRate=(rate, "median")))
        top = top.sort_values("Transactions", ascending=False).head(12)
        if not top.empty and len(top) > 1:
            label = "community" if group_col == cols["community"] else "district"
            rep.h1(f"Activity by {label}", needs=2.4)
            rep.table(
                [label.title(), "Transactions", "Share", "Median price", "Median rate"],
                [[_title(r[group_col]), f"{int(r['Transactions']):,}",
                  f"{r['Transactions'] / len(df) * 100:.1f}%",
                  _aed(r["MedianPrice"]), _aed(r["MedianRate"])]
                 for _, r in top.iterrows()],
                widths=[2.0, 1.2, 0.9, 1.5, 1.4],
                caption=f"The busiest {label}s in this selection, by recorded transaction "
                        f"count. Share is of the transactions in this report.",
            )

    # ── 6. Sale type ────────────────────────────────────────────────────────
    sale_col = cols["sale_type"]
    if sale_col in df.columns and df[sale_col].nunique() > 1:
        st_tab = (df.groupby(sale_col, as_index=False)
                    .agg(Transactions=(price, "size"), MedianPrice=(price, "median"),
                         MedianRate=(rate, "median")))
        st_tab = st_tab.sort_values("Transactions", ascending=False)
        rep.h1("Sale type", needs=1.9)
        rep.table(
            ["Sale application type", "Transactions", "Share", "Median price",
             "Median rate"],
            [[_title(r[sale_col]), f"{int(r['Transactions']):,}",
              f"{r['Transactions'] / len(df) * 100:.1f}%",
              _aed(r["MedianPrice"]), _aed(r["MedianRate"])]
             for _, r in st_tab.iterrows()],
            widths=[2.0, 1.2, 0.9, 1.5, 1.4],
            caption="Sale application types as recorded. A price difference between types "
                    "reflects the mix of what was sold under each, not a like-for-like "
                    "comparison of the same unit.",
        )

    # ── 7. Methodology ──────────────────────────────────────────────────────
    rep.h1("Methodology and scope", needs=2.4)
    rep.h2("Data source")
    rep.bullets([
        "regions/abu_dhabi/Abu_Dhabi_Sales_Cleaned (1).csv — the Abu Dhabi sales "
        "records held by the platform.",
        "Loaded through the Abu Dhabi dashboard's own loader, so this report and that "
        "dashboard read the same cleaned frame.",
    ])
    rep.h2("How this selection was formed")
    rep.bullets([
        "Residential apartments only: asset class *residential* and property layout "
        "*apartment*, as the dashboard defines them.",
        "Rows without a recorded rate or sold area are excluded.",
        "Rate, price and sold area are each trimmed to their 1st–99th percentile, which "
        "is the dashboard's own cleaning step.",
        (f"Filtered to the district {_title(district)}."
         if district != ALL_AREAS else
         "All districts are included."),
    ])
    rep.h2("How to read these figures")
    rep.bullets([
        "Counts are of recorded sale applications, which is a measure of activity rather "
        "than of stock.",
        "Medians describe the middle of the market; means sit higher wherever a few large "
        "sales pull them up.",
        "This dataset records apartments. Villas, land and other property layouts are "
        "outside the cleaned frame this report is built on.",
        "The dataset carries no floor number, amenity flag or building-height field, so "
        "this report contains no section on any of them.",
    ])
