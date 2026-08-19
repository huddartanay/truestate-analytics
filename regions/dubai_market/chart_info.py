"""
The chart-documentation system for the Dubai dashboard.

ONE registry, TWO consumers:

  1. `render_chart_header()` draws the section heading with a subtle ⓘ control;
     opening it shows the full explanation in the app.
  2. `tools/build_chart_reference_docx.py` reads the SAME registry to generate
     Dubai_Analytics_Chart_Reference_Guide.docx.

Because both come from one source, the document can never drift from the app.

Every entry states, honestly, which dataset the chart reads:

    SOURCE_CLEAN   data/dubai/latest_combined_data.parquet  (cleaned)
    SOURCE_RAW     data/dubai/transactions.parquet          (raw registry)
    SOURCE_DERIVED an artefact produced by the earlier modelling work

Nothing in here is decorative: `columns` are the actual column names read by
the chart's builder, and `calculation` describes what the code actually does.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# SOURCE LABELS
# ─────────────────────────────────────────────────────────────────────────────

SOURCE_CLEAN = (
    "CLEANED",
    "data/dubai/latest_combined_data.parquet",
    "818,838 residential **unit** sales registered in Dubai, 2010 – Aug 2026, "
    "enriched by the project with time parts, unit attributes, amenity flags and "
    "building / developer scoring.",
)
SOURCE_RAW = (
    "RAW",
    "data/dubai/transactions.parquet",
    "1,762,262 rows — the full Dubai transaction registry (sales, mortgages and "
    "gifts across units, villas, land and whole buildings), 1966 – Aug 2026, "
    "exactly as supplied.",
)
SOURCE_DERIVED = (
    "DERIVED",
    "regions/dubai/*.csv (forecast artefacts)",
    "Outputs already produced by the project's Dubai modelling pipeline and stored "
    "with the repository. Nothing is refitted at run time.",
)


@dataclass
class ChartInfo:
    """Everything a reader needs to trust and interpret one chart."""

    key: str
    title: str
    section: str
    icon: str = "📊"
    subtitle: str = ""

    # ── Plain language, for a reader who does not work with data ────────────
    one_liner: str = ""            # IN ONE SENTENCE
    steps: list[str] = field(default_factory=list)   # HOW THE NUMBER IS WORKED OUT
    terms: list[str] = field(default_factory=list)   # words on this chart, explained

    what: str = ""                 # WHAT IS THIS?
    why: str = ""                  # WHY IS THIS GRAPH USED?
    source: tuple = SOURCE_CLEAN   # (label, file, description)
    columns: list[str] = field(default_factory=list)
    preparation: str = ""
    calculation: str = ""
    x_axis: str = ""
    y_axis: str = ""
    y2_axis: str = ""
    legend: str = ""
    filters: str = "All seven Dubai sidebar filters apply: year, locality zone, area, layout, registration type, sale-price range and unit-size range."
    how_to_read: list[str] = field(default_factory=list)
    tells_us: list[str] = field(default_factory=list)
    does_not_tell: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    validation: str = ""
    client_explanation: str = ""

    @property
    def source_label(self) -> str:
        return self.source[0]

    @property
    def source_file(self) -> str:
        return self.source[1]

    @property
    def source_desc(self) -> str:
        return self.source[2]


# ─────────────────────────────────────────────────────────────────────────────
# RENDERING
# ─────────────────────────────────────────────────────────────────────────────

_SOURCE_STYLE = {
    "CLEANED": ("#0D9488", "rgba(13,148,136,0.10)"),
    "RAW": ("#D97706", "rgba(217,119,6,0.10)"),
    "DERIVED": ("#7C3AED", "rgba(124,58,237,0.10)"),
}


# ─────────────────────────────────────────────────────────────────────────────
# PLAIN-ENGLISH GLOSSARY
#
# Every word that appears on a Dubai chart and is not everyday English is
# defined here once. Each chart lists the terms it uses; the ⓘ shows only
# those, so nobody has to know what a quartile is before reading a box plot.
# ─────────────────────────────────────────────────────────────────────────────

GLOSSARY: dict[str, str] = {
    "area":
        "The district a property sits in, as recorded in the Dubai land registry — "
        "Marsa Dubai, Business Bay, Palm Jumeirah and so on. Registry areas are "
        "administrative boundaries, so they vary a lot in size and in how much is "
        "built on them; a busier area is not necessarily a better one.",
    "price bracket":
        "A price range used to group sales — “AED 1M – 2M”, for example. Each sale "
        "falls in exactly one bracket. The boundary belongs to the bracket above it, "
        "so a sale at exactly AED 1,000,000 is counted in 1M – 2M and nowhere else.",
    "transaction count":
        "Simply how many sales were recorded. It measures activity, not price and not "
        "value — a thousand cheap sales counts higher than ten expensive ones.",
    "smoothing":
        "Drawing a calmer line through figures that jump around month to month, so the "
        "underlying direction is readable. Smoothing summarises the real observations; "
        "it never replaces them, adds to them, or predicts anything.",
    "trend":
        "The general direction the numbers are moving once the month-to-month noise is "
        "set aside. A trend line describes what has already happened — it is not a "
        "forecast of what happens next.",
    "median":
        "Line every sale up from cheapest to dearest and take the one in the middle — "
        "half are below it, half above. Used instead of the average because a handful "
        "of enormous deals drags an average upwards and stops it describing anybody.",
    "rate per m²":
        "The price of one square metre: total price ÷ floor area. It lets a studio and "
        "a penthouse be compared fairly, because it takes size out of the picture.",
    "total value":
        "Every sale price in the group added together — how much money changed hands.",
    "off-plan":
        "Bought from the developer before the building was finished.",
    "existing property":
        "Already built and completed at the time it was sold. Also called resale or "
        "ready property.",
    "registration type":
        "The Land Department's label for whether a sale was off-plan or existing. It is "
        "recorded on every transaction, so nothing here is guessed.",
    "like-for-like":
        "Comparing only properties that match on the things that matter — same area, "
        "same size of apartment, same year, same off-plan status — so the comparison is "
        "not secretly about something else.",
    "amenity flag":
        "A yes/no column recording whether a feature was noted for that unit. A “no” "
        "means it was **not recorded**, which is not the same as “definitely absent”.",
    "composition effect":
        "When a difference between two groups turns out to be caused by the groups "
        "containing different kinds of thing, rather than by what you were measuring.",
    "percentile":
        "The 90th percentile is the value that 90% of sales come in below. The 1st and "
        "99th are used here to trim off the few extreme deals at each end.",
    "quartile":
        "Split the sales into four equal groups by price. The box in a box plot runs "
        "from the end of the first group to the end of the third — the middle half of "
        "the market.",
    "whisker":
        "The line reaching out of a box. It stretches to the furthest sale still inside "
        "the normal range; anything past it is an unusual deal.",
    "pareto chart":
        "Bars sorted biggest first, with a line showing the running total, so you can "
        "see how few items make up most of the whole.",
    "cumulative share":
        "A running total, as a percentage. Where it crosses 80%, everything to the left "
        "of that point accounts for four-fifths of the market.",
    "year-over-year":
        "This year compared with the year immediately before it — never with a fixed "
        "starting year. So 2025 is measured against 2024, and 2024 against 2023.",
    "partial year":
        "A year the data does not cover in full. 2026 stops on 6 August, so eight "
        "months of it are being compared with somebody else's twelve.",
    "rolling median":
        "For each month, take that month together with the one before and the one "
        "after, and use the middle value of the three. It calms the zig-zag without "
        "moving the level or hiding anything — the real monthly figures are still there.",
    "price band":
        "A price bracket, such as AED 1M – 2M. Every sale falls in exactly one band, so "
        "the bands add up to the whole market.",
    "histogram":
        "Sales sorted into equal-width buckets; the height of each bar is how many "
        "landed in that bucket.",
    "distribution":
        "The shape of the data — where most sales sit and how far the rest spread out.",
    "violin":
        "A smoothed outline of the distribution. Where it bulges, there are more sales "
        "at that price.",
    "log scale":
        "An axis where each step multiplies instead of adding (1M, 10M, 100M). Useful "
        "when the values run from small to enormous.",
    "treemap":
        "Nested rectangles where the size of each box is proportional to the number it "
        "represents.",
    "arima":
        "A standard statistical forecasting model. It learns the pattern of a series "
        "from its own history and projects it forward. It uses no outside information.",
    "confidence band":
        "The range the model expects the true value to fall inside. A wide band means "
        "the model is not very sure.",
    "mape":
        "Mean absolute percentage error — on average, how far the model's past "
        "predictions were from what actually happened, in percent. Lower is better.",
    "locality zone":
        "A six-way grouping of Dubai areas carried in the dataset — Prime Central, "
        "Prime Waterfront, Urban Core, Suburban, Outer/Remote and Unknown.",
    "layout":
        "The bedroom configuration: studio, 1 B/R, 2 B/R and so on.",
}


def source_badge(info: ChartInfo) -> str:
    colour, soft = _SOURCE_STYLE.get(info.source_label, ("#2563EB", "rgba(37,99,235,0.10)"))
    return (
        f'<span class="uae-src-badge" style="color:{colour};background:{soft};'
        f'border-color:{colour}33">{info.source_label} DATA</span>'
    )


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items)


def render_chart_header(info: ChartInfo) -> None:
    """
    Draw a chart heading with a subtle ⓘ next to it.

        📈  How prices are moving            [CLEANED DATA] [ⓘ]
            Median sale price and median rate per m², monthly.

    The ⓘ opens a popover carrying the full explanation. One component, used by
    every chart on the page — no per-chart tooltip logic anywhere.
    """
    head, ctrl = st.columns([9, 1], vertical_alignment="center")

    with head:
        sub = f'<p class="uae-block-sub">{info.subtitle}</p>' if info.subtitle else ""
        st.markdown(
            " ".join(
                f'<div class="uae-block" style="margin-top:1.5rem">'
                f'<div class="uae-block-ic">{info.icon}</div>'
                f'<div><p class="uae-block-title">{info.title} {source_badge(info)}</p>'
                f"{sub}</div></div>".split()
            ),
            unsafe_allow_html=True,
        )

    with ctrl:
        with st.popover("ⓘ", help=f"About “{info.title}”", use_container_width=True):
            _render_body(info)


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{i}. {t}" for i, t in enumerate(items, start=1))


def _render_body(info: ChartInfo) -> None:
    """
    The ⓘ content, ordered for somebody who does not work with data.

    Plain English first — what this is, what is happening inside it, how to read
    it. The technical record (dataset, columns, formula, axes, limitations) sits
    below a divider for anyone who wants to audit it.
    """
    st.markdown(f"### {info.icon}  {info.title}")

    # ── 1. Plain English ────────────────────────────────────────────────────
    if info.one_liner:
        st.info(info.one_liner, icon="💬")

    st.markdown("**What you are looking at**")
    st.markdown(info.what)

    st.markdown("**Why it is here**")
    st.markdown(info.why)

    if info.steps:
        st.markdown("**What happens inside this chart, step by step**")
        st.markdown(_numbered(info.steps))

    if info.how_to_read:
        st.markdown("**How to read it**")
        st.markdown(_bullets(info.how_to_read))

    if info.tells_us:
        st.markdown("**What you can take from it**")
        st.markdown(_bullets(info.tells_us))

    if info.does_not_tell:
        st.markdown("**Good to know**")
        st.markdown(_bullets(info.does_not_tell))

    terms = [t for t in info.terms if t.lower() in GLOSSARY]
    if terms:
        st.markdown("**Words used on this chart**")
        st.markdown("\n".join(f"- **{t.capitalize()}** — {GLOSSARY[t.lower()]}"
                              for t in terms))

    if info.client_explanation:
        st.markdown("**How to put it to a client**")
        st.success(info.client_explanation, icon="🗣️")

    # ── 2. The technical record ─────────────────────────────────────────────
    st.divider()
    st.caption("TECHNICAL DETAIL — for anyone checking the working")

    st.markdown("**Where the numbers come from**")
    st.markdown(
        f"| | |\n|---|---|\n"
        f"| **Data source** | {info.source_label} |\n"
        f"| **Dataset file** | `{info.source_file}` |\n"
        f"| **What that file is** | {info.source_desc} |\n"
        f"| **Columns used** | {', '.join(f'`{c}`' for c in info.columns)} |\n"
    )

    if info.preparation:
        st.markdown("**Data preparation**")
        st.markdown(info.preparation)

    st.markdown("**Calculation**")
    st.markdown(info.calculation)

    axes = []
    if info.x_axis:
        axes.append(f"| **X-axis** | {info.x_axis} |")
    if info.y_axis:
        axes.append(f"| **Y-axis** | {info.y_axis} |")
    if info.y2_axis:
        axes.append(f"| **Right Y-axis** | {info.y2_axis} |")
    if info.legend:
        axes.append(f"| **Legend** | {info.legend} |")
    if axes:
        st.markdown("**Axes and legend**")
        st.markdown("| | |\n|---|---|\n" + "\n".join(axes))

    if info.filters:
        st.markdown("**Filters that affect it**")
        st.markdown(info.filters)

    if info.limitations:
        st.markdown("**Scope of the data**")
        st.markdown(_bullets(info.limitations))

    if info.validation:
        st.markdown("**How this was checked**")
        st.markdown(info.validation)


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

_COMMON_LIMITS = [
    "Covers registered residential **unit** (apartment) sales only — villas, land "
    "and whole-building transactions are not in this dataset.",
    "2026 is a partial year: the data ends **6 August 2026**, so 2026 totals are "
    "not comparable with a full year.",
    "The sale-price and unit-size sliders start at the 1st–99th percentile, so the "
    "most extreme deals are excluded until you widen them.",
]

CHARTS: list[ChartInfo] = [

    # ══════════════════════════════════════════════════════════════ INSIGHTS ══
    ChartInfo(
        key="concentration_pareto",
        title="Where the market is concentrated",
        section="Insights",
        icon="🎯",
        subtitle="How transaction value is distributed across Dubai's areas.",
        what="A Pareto (ABC) chart. Bars are the total value transacted in each area, "
             "tallest first; the line is the running cumulative share of the whole market.",
        why="To show how concentrated the market is. If a handful of areas account for "
            "most of the money, that is where attention, stock and risk sit.",
        columns=["area_name_en", "actual_worth"],
        preparation="Rows are filtered by the sidebar selection. No other transformation.",
        calculation="For each area, `sum(actual_worth)`. Areas are sorted descending; the "
                    "line is the cumulative sum divided by the grand total, as a percentage. "
                    "The top 25 areas are drawn; the cumulative line uses those 25.",
        x_axis="Area, ordered by total transaction value (highest first).",
        y_axis="Total value transacted in the area (AED).",
        y2_axis="Cumulative share of total market value (%), capped at 105 for readability.",
        legend="Blue bars = value per area. Amber line = cumulative share. The dotted "
               "guide marks the 80% level.",
        how_to_read=[
            "Read the bars left to right — each one is a whole area's transaction value.",
            "Follow the amber line to where it crosses 80%: everything to the left of "
            "that point makes up four-fifths of the market.",
            "A line that rises steeply means a very concentrated market.",
        ],
        tells_us=["Which areas carry the market's value, and how few of them there are."],
        does_not_tell=[
            "Nothing about profitability, yield or future performance.",
            "High total value can come from many cheap deals or few expensive ones — "
            "check the accompanying table for both.",
        ],
        limitations=_COMMON_LIMITS,
        validation="The cumulative share is checked to reach 100% across all areas, and "
                   "the per-area totals reconcile with the table underneath.",
        client_explanation="Dubai's residential market is not spread evenly. This chart "
                           "shows how much of the money is changing hands in how few places.",
    ),
    ChartInfo(
        key="tier_price",
        title="Building price tier vs realised rate",
        section="Insights",
        icon="⭐",
        subtitle="Median rate per m² for each price tier carried in the dataset.",
        what="A ranking of the dataset's own building **Price Tier** label against the "
             "rate per m² those buildings actually achieved.",
        why="The tier label was assigned by the project's building-scoring work. This "
            "chart is the sanity check that it lines up with what buyers really paid.",
        columns=["Price Tier", "meter_sale_price"],
        preparation="Rows labelled `Unknown` are excluded. Tiers with fewer than 200 "
                    "transactions in the current selection are dropped so a thin group "
                    "cannot top the ranking.",
        calculation="`median(meter_sale_price)` per tier.",
        x_axis="Median rate per m² (AED).",
        y_axis="Price tier.",
        legend="Single series; hover shows the number of transactions behind each bar.",
        how_to_read=["Tiers should step up in order. If two tiers overlap, the label is "
                     "not separating the market as intended."],
        tells_us=["Whether the tier labels are consistent with realised prices."],
        does_not_tell=["Why a building sits in a tier — the scoring inputs are not in "
                       "this dataset."],
        limitations=_COMMON_LIMITS + ["Tier is a supplied label, not something recomputed here."],
        validation="Cross-checked against the Building Grade chart beside it; both should "
                   "rank in the same direction.",
        client_explanation="A check that our building tiers mean something in the market, "
                           "not just on paper.",
    ),
    ChartInfo(
        key="grade_price",
        title="Building grade vs realised rate",
        section="Insights",
        icon="🏅",
        subtitle="Median rate per m² by the A+ to D building grade in the dataset.",
        what="The dataset's building **Grade** against the rate per m² actually achieved.",
        why="Same purpose as the price-tier chart: verifying that a supplied quality label "
            "is reflected in transaction prices.",
        columns=["Grade", "meter_sale_price"],
        preparation="`Unknown` excluded; grades with fewer than 200 transactions dropped.",
        calculation="`median(meter_sale_price)` per grade.",
        x_axis="Median rate per m² (AED).",
        y_axis="Building grade.",
        legend="Single series; hover shows transaction counts.",
        how_to_read=["Expect A+ at the top and D at the bottom. Any inversion is worth "
                     "investigating in the grading method."],
        tells_us=["Whether building grade tracks realised price."],
        does_not_tell=["How the grade was derived."],
        limitations=_COMMON_LIMITS,
        validation="Compared with the price-tier ranking, which uses a different label.",
        client_explanation="Do higher-graded buildings actually sell for more? This answers it.",
    ),

    # ════════════════════════════════════════════════════════════════ TRENDS ══
    ChartInfo(
        key="monthly_activity",
        title="Monthly market activity",
        section="Trends",
        icon="📅",
        subtitle="Transaction count and total value, month by month.",
        what="How many sales completed each month and how much money that represented.",
        why="Volume is the clearest measure of market activity, and it moves before "
            "prices do.",
        columns=["instance_date", "year_month", "actual_worth"],
        preparation="Transactions are grouped by calendar month using `year_month`.",
        calculation="Per month: `count(rows)`, `sum(actual_worth)`, and a centred "
                    "3-month rolling mean of the count.",
        x_axis="Month.",
        y_axis="Number of transactions.",
        y2_axis="Total value transacted (AED).",
        legend="Blue area = transactions. Dotted amber = 3-month average. "
               "Teal bars = total value.",
        how_to_read=[
            "The blue area is the raw monthly count; the dotted line smooths it.",
            "Bars and line moving apart means the average deal size is changing.",
        ],
        tells_us=["The direction and pace of market activity."],
        does_not_tell=["Nothing about price levels — see the Price section."],
        limitations=_COMMON_LIMITS + [
            "The final month (August 2026) is **incomplete** — only 2,157 transactions "
            "to 6 August versus about 10,800 in a full month, so the last point always "
            "falls sharply.",
        ],
        validation="Monthly counts sum to the filtered row count.",
        client_explanation="How busy the market has been, month by month.",
    ),
    ChartInfo(
        key="annual_volume",
        title="Annual volume",
        section="Trends",
        icon="📆",
        subtitle="Transactions completed each year.",
        what="One bar per calendar year, showing how many sales were registered.",
        why="The simplest long-run view of whether the market is growing or contracting.",
        columns=["year", "actual_worth"],
        preparation="Grouped by the `year` column already present in the dataset.",
        calculation="`count(rows)` per year.",
        x_axis="Year.",
        y_axis="Number of transactions.",
        legend="Bars are coloured red when the year fell against the previous one.",
        how_to_read=["Taller bar = more deals closed."],
        tells_us=["The long-run growth of the Dubai residential-unit market."],
        does_not_tell=["Nothing about prices."],
        limitations=_COMMON_LIMITS + [
            "The 2026 bar covers January–August only and will look artificially low.",
        ],
        validation="Yearly counts sum to the filtered row count.",
        client_explanation="Year by year, how many homes changed hands.",
    ),
    ChartInfo(
        key="quarterly_heatmap",
        title="Quarterly pattern",
        section="Trends",
        icon="🗓️",
        subtitle="Transaction counts by year and quarter.",
        what="A grid of years against quarters, shaded by how busy each quarter was.",
        why="Separates the long-run trend (down the grid) from any repeating "
            "within-year rhythm (across the grid).",
        columns=["year", "quarter", "actual_worth"],
        preparation="Pivot of the filtered rows; no aggregation beyond counting.",
        calculation="`count(rows)` for each year × quarter cell.",
        x_axis="Quarter (Q1–Q4).",
        y_axis="Year.",
        legend="Darker cell = more transactions.",
        how_to_read=[
            "Scan down a column to see how one quarter has changed over the years.",
            "Scan across a row to see the shape of a single year.",
        ],
        tells_us=["Whether Dubai has a recurring seasonal pattern, and how it has changed."],
        does_not_tell=["Nothing about prices or deal size."],
        limitations=_COMMON_LIMITS + ["2026 Q3 is partial and Q4 is absent."],
        validation="Cell counts sum to the filtered row count.",
        client_explanation="Which parts of the year are busiest, and whether that has changed.",
    ),
    ChartInfo(
        key="yoy_growth",
        title="Year-over-year growth",
        section="Trends",
        icon="📈",
        subtitle="Change in volume and in median rate per m², each year against the one before it.",
        what="For every year, the percentage change against the **immediately preceding "
             "year** — never against a fixed baseline.",
        why="This is the chart that answers “compared with last year, did pricing go up "
            "or down?”",
        columns=["year", "actual_worth", "meter_sale_price"],
        preparation="Years are sorted ascending. Every year from 2010 to 2026 is present "
                    "in the data, so no year is compared across a gap.",
        calculation="Growth (%) = (this year − previous year) ÷ previous year × 100, "
                    "applied to the transaction count and to `median(meter_sale_price)` "
                    "separately. Implemented as `pct_change()` on a year-sorted series, "
                    "so 2020 is compared with 2019, 2021 with 2020, and so on.",
        x_axis="Year (the first year has no bar — there is nothing to compare it with).",
        y_axis="Change in transaction volume vs the previous year (%).",
        y2_axis="Change in median rate per m² vs the previous year (%).",
        legend="Bars = volume growth, teal when positive and red when negative. "
               "Dotted blue line = rate growth.",
        how_to_read=[
            "Bars above the zero line mean more deals than last year; below means fewer.",
            "The dotted line is the pricing answer: above zero, the market got more "
            "expensive per m² than the year before.",
            "The two do **not** have to agree — a busy year can be a flat pricing year.",
        ],
        tells_us=[
            "Whether pricing rose or fell against the previous year, and by how much.",
            "Whether activity and pricing are moving together or apart.",
        ],
        does_not_tell=[
            "Nothing about *why* a year moved.",
            "Nothing about the level of prices — only the change.",
        ],
        limitations=_COMMON_LIMITS + [
            "**2026 volume is not comparable.** It covers January–August only, which is "
            "why it shows about −53%. On a like-for-like January–August basis against "
            "2025 the fall is about **−24%**. The panel beside the chart shows that "
            "comparison. The negative value is kept because it is arithmetically correct "
            "for the data present.",
            "Median rate is far less affected by a shorter year than volume is: the "
            "full-year 2026 rate change is −0.1% and the like-for-like figure is +1.1%.",
        ],
        validation="Recomputed independently in pandas: every year is compared with the "
                   "immediately preceding year, all 17 years are present with no gaps, "
                   "and each negative year was checked against its own volume and median "
                   "to confirm it is genuine rather than a formula or ordering error. "
                   "2011 (−24.9%), 2015 (−26.2%), 2018 (−30.4%) and 2020 (−14.0%) are "
                   "real market contractions and have been kept.",
        client_explanation="“Against last year, did the market get busier or quieter, and "
                           "did prices per square metre rise or fall?” Bars answer the "
                           "first, the dotted line answers the second.",
    ),
    ChartInfo(
        key="seasonality",
        title="Seasonality",
        section="Trends",
        icon="🌊",
        subtitle="Which calendar months are busiest, pooled across all years.",
        what="Total transactions in each calendar month, added up across every year "
             "in the selection.",
        why="To see whether Dubai has a genuine within-year rhythm.",
        columns=["month", "actual_worth"],
        preparation="Grouped by the `month` number; all years pooled.",
        calculation="`count(rows)` per calendar month. The dotted line is the mean "
                    "across the twelve months.",
        x_axis="Calendar month.",
        y_axis="Transactions across all years in the selection.",
        legend="Amber dotted line marks the monthly average.",
        how_to_read=["Bars well above the dotted line are consistently busy months."],
        tells_us=["Whether activity is seasonal."],
        does_not_tell=["Whether the pattern still holds recently — pooling hides change "
                       "over time. Use the quarterly grid for that."],
        limitations=_COMMON_LIMITS + [
            "Pooling across 2010–2026 gives recent, higher-volume years more weight.",
            "September–December carry one fewer year than January–August because 2026 "
            "is incomplete.",
        ],
        validation="Monthly totals sum to the filtered row count.",
        client_explanation="The months when Dubai buys.",
    ),

    # ═════════════════════════════════════════════════════════════ GEOGRAPHY ══
    ChartInfo(
        key="top_areas_volume",
        title="Busiest areas",
        section="Geography",
        icon="📍",
        subtitle="The 15 areas with the most transactions.",
        what="A ranking of Dubai areas by number of sales.",
        why="Shows where the market is most liquid — where you can buy and sell easily.",
        columns=["area_name_en"],
        preparation="Filtered rows only.",
        calculation="`count(rows)` per area; top 15 shown.",
        x_axis="Number of transactions.",
        y_axis="Area.",
        how_to_read=["Longer bar = more deals. This is activity, not value."],
        tells_us=["Where the most transactions happen."],
        does_not_tell=["Nothing about price — a busy area can be affordable."],
        limitations=_COMMON_LIMITS,
        validation="Counts reconcile with the area detail table in the same section.",
        client_explanation="Where Dubai is trading most often.",
    ),
    ChartInfo(
        key="top_areas_rate",
        title="Most expensive areas",
        section="Geography",
        icon="💎",
        subtitle="Highest median rate per m², areas with 300+ transactions only.",
        what="A ranking of areas by the median price per square metre achieved there.",
        why="Rate per m² removes unit size from the comparison, so a studio area and a "
            "penthouse area can be compared fairly.",
        columns=["area_name_en", "meter_sale_price"],
        preparation="Areas with fewer than **300** transactions in the current selection "
                    "are excluded, so a single unusual sale cannot top the ranking.",
        calculation="`median(meter_sale_price)` per area; top 15 of those that clear the "
                    "300-transaction threshold.",
        x_axis="Median rate per m² (AED).",
        y_axis="Area.",
        legend="Hover shows how many deals sit behind each bar.",
        how_to_read=["Longer bar = higher price per square metre.",
                     "Always read the transaction count in the tooltip alongside the bar."],
        tells_us=["Which areas command the highest price per square metre."],
        does_not_tell=[
            "Nothing about total spend — an expensive area can be small.",
            "Nothing about value for money or investment return.",
        ],
        limitations=_COMMON_LIMITS + [
            "The 300-transaction floor deliberately hides small, very expensive areas.",
        ],
        validation="Thresholded and unthresholded rankings were compared; the threshold "
                   "removes areas whose median rested on a handful of deals.",
        client_explanation="Dubai's premium addresses, measured per square metre so that "
                           "size does not distort the comparison.",
    ),
    ChartInfo(
        key="area_treemap",
        title="Value map",
        section="Geography",
        icon="🗺️",
        subtitle="Box size = total transaction value; colour = median rate per m².",
        what="A treemap of the top 25 areas by money transacted, shaded by price level.",
        why="Combines two questions in one picture: where the money is, and whether it "
            "is expensive money or high-volume money.",
        columns=["area_name_en", "actual_worth", "meter_sale_price"],
        preparation="Top 25 areas by total value.",
        calculation="Box area ∝ `sum(actual_worth)`; colour = `median(meter_sale_price)`.",
        legend="Darker = higher rate per m².",
        how_to_read=[
            "Large and dark = lots of money at high prices per m².",
            "Large and pale = high volume at accessible prices.",
        ],
        tells_us=["Where value concentrates, and at what price level."],
        does_not_tell=["Nothing geographic — box position carries no map meaning."],
        limitations=_COMMON_LIMITS + ["Only the top 25 areas are drawn."],
        validation="Box values reconcile with the Pareto chart in Insights.",
        client_explanation="One picture of where the money goes and how expensive it is there.",
    ),
    ChartInfo(
        key="area_bubble",
        title="Volume against price",
        section="Geography",
        icon="🔮",
        subtitle="Each bubble is an area.",
        what="A scatter of the 30 busiest areas: activity on one axis, median price on "
             "the other, bubble size for total value.",
        why="Separates busy-and-cheap from quiet-and-expensive at a glance.",
        columns=["area_name_en", "actual_worth", "meter_sale_price"],
        preparation="Top 30 areas by transaction count.",
        calculation="X = `count(rows)`; Y = `median(actual_worth)`; size = "
                    "`sum(actual_worth)`; colour = `median(meter_sale_price)`.",
        x_axis="Number of transactions.",
        y_axis="Median sale price (AED).",
        legend="Colour = median rate per m². Bubble size = total value transacted.",
        how_to_read=["Right = busy. Up = expensive. Big = a lot of money in total.",
                     "The top-right corner is where both activity and price are high."],
        tells_us=["How activity and price level relate across areas."],
        does_not_tell=["Nothing causal — a busy area is not busy *because* it is priced "
                       "the way it is."],
        limitations=_COMMON_LIMITS + ["Only the 30 busiest areas appear."],
        validation="Values reconcile with the area detail table.",
        client_explanation="A market map: which areas are liquid, which are premium, "
                           "and which are both.",
    ),
    ChartInfo(
        key="zone_comparison",
        title="Locality zones",
        section="Geography",
        icon="🌊",
        subtitle="Median rate per m² by the zone label carried in the dataset.",
        what="The dataset's own six-way zone classification (Prime Central, Prime "
             "Waterfront, Urban Core, Suburban, Outer/Remote) against realised rate.",
        why="A coarser, more communicable view than 69 individual areas.",
        columns=["Locality Zone", "meter_sale_price", "actual_worth"],
        preparation="`Unknown` zone excluded. Zones with fewer than 100 transactions dropped.",
        calculation="Bars = `median(meter_sale_price)` per zone; line = `count(rows)`.",
        x_axis="Locality zone.",
        y_axis="Median rate per m² (AED).",
        y2_axis="Number of transactions.",
        legend="Blue bars = price level. Dotted amber = how many deals sit behind it.",
        how_to_read=["Compare bar heights for price, and always check the dotted line "
                     "for how much data supports each bar."],
        tells_us=["The price gradient across Dubai's broad location types."],
        does_not_tell=["How the zone labels were assigned — that came with the dataset."],
        limitations=_COMMON_LIMITS + ["Zone is a supplied label, not recomputed here."],
        validation="Zone medians were checked against the area-level ranking for consistency.",
        client_explanation="Waterfront, central, suburban — what each broad location type costs.",
    ),
    ChartInfo(
        key="metro_effect",
        title="Nearest metro station",
        section="Geography",
        icon="🚇",
        subtitle="Median rate per m² grouped by each unit's nearest station.",
        what="Units grouped by the metro station recorded as nearest to them, ranked by "
             "median rate.",
        why="Metro proximity is a standard value question in any city.",
        columns=["nearest_metro_en", "meter_sale_price"],
        preparation="Stations with fewer than 500 transactions are excluded; top 15 shown.",
        calculation="`median(meter_sale_price)` per station.",
        x_axis="Median rate per m² (AED).",
        y_axis="Nearest metro station.",
        how_to_read=["This ranks **neighbourhoods that those stations serve**, at least "
                     "as much as it ranks the stations themselves."],
        tells_us=["Which metro corridors carry the most expensive stock."],
        does_not_tell=[
            "It does **not** measure the value of being near a metro. That comparison is "
            "in the Price section, and it comes out negative — Dubai's most expensive "
            "waterfront stock is largely not on the metro network.",
            "Distance is not recorded, only which station is nearest.",
        ],
        limitations=_COMMON_LIMITS + [
            "`nearest_metro_en` is blank for some units; those are excluded from this chart.",
        ],
        validation="Station groupings were checked against area names for plausibility.",
        client_explanation="Which metro corridors the expensive stock sits on.",
    ),

    # ══════════════════════════════════════════════════════════════ PROPERTY ══
    ChartInfo(
        key="layout_mix",
        title="Layout mix",
        section="Property",
        icon="🛏️",
        subtitle="What buyers are actually buying.",
        what="Transaction counts for each bedroom configuration.",
        why="Establishes what the typical Dubai unit sale actually is.",
        columns=["rooms_en"],
        preparation="Layouts ordered Studio → 1 B/R → … → Penthouse.",
        calculation="`count(rows)` per `rooms_en` value.",
        x_axis="Layout.",
        y_axis="Number of transactions.",
        how_to_read=["Three layouts — 1 B/R, 2 B/R and Studio — make up the overwhelming "
                     "majority of the market."],
        tells_us=["The shape of demand by unit type."],
        does_not_tell=["Nothing about supply or what is available unsold."],
        limitations=_COMMON_LIMITS,
        validation="Counts sum to the filtered row count; nine distinct layouts confirmed "
                   "present with no nulls.",
        client_explanation="Dubai's residential market is, overwhelmingly, a one- and "
                           "two-bedroom apartment market.",
    ),
    ChartInfo(
        key="size_by_layout",
        title="Typical size by layout",
        section="Property",
        icon="📐",
        subtitle="Median floor area for each layout.",
        what="The median recorded floor area of each bedroom configuration.",
        why="A reference point when comparing listings, and the denominator behind every "
            "rate-per-m² figure on this dashboard.",
        columns=["rooms_en", "procedure_area"],
        preparation="Filtered rows only.",
        calculation="`median(procedure_area)` per layout.",
        x_axis="Layout.",
        y_axis="Median unit size (m²).",
        how_to_read=["Sizes step up cleanly: about 40 m² for a studio, 73 m² for a "
                     "1-bed, 120 m² for a 2-bed."],
        tells_us=["What each layout label means in floor area."],
        does_not_tell=["Nothing about layout quality or usable space."],
        limitations=_COMMON_LIMITS + [
            "`procedure_area` is the registered area, which may include balconies and "
            "shared allocations depending on the registration.",
        ],
        validation="Medians were checked to increase monotonically with bedroom count.",
        client_explanation="What a studio, a one-bed and a two-bed actually measure in Dubai.",
    ),
    ChartInfo(
        key="rate_by_layout",
        title="Rate per m² by layout",
        section="Property",
        icon="💠",
        subtitle="One panel per layout, so the distributions can be compared side by side.",
        what="A small-multiples box plot: each layout gets its own panel showing the "
             "middle 50% of its transactions, its median, and its typical range.",
        why="A single combined box plot compressed nine layouts on top of each other and "
            "was unreadable. Separate panels let each distribution be seen.",
        columns=["rooms_en", "meter_sale_price"],
        preparation="Layouts with fewer than **100** transactions in the current selection "
                    "are shown in a note rather than plotted, because a box drawn from a "
                    "handful of sales is not meaningful. No outliers are deleted — the "
                    "whiskers reach the furthest transaction within 1.5 × IQR and anything "
                    "beyond is summarised in the table below the chart.",
        calculation="Per layout: 25th percentile, median, 75th percentile, and whiskers at "
                    "the furthest observation inside 1.5 × IQR. Quartiles are computed in "
                    "pandas rather than in the browser; the drawn statistics are identical.",
        x_axis="Layout (one panel each).",
        y_axis="Rate per m² (AED). All panels share the same scale so they can be compared.",
        legend="Each panel is coloured for identification only; the transaction count is "
               "printed under each panel.",
        how_to_read=[
            "The box is the middle 50% of transactions; the line inside it is the median.",
            "The whiskers show the typical range; the table lists what falls beyond them.",
            "Compare median lines across panels to see how price per m² varies by layout.",
        ],
        tells_us=[
            "How rate per m² varies across layouts, and how wide the spread is within each.",
            "In this data, larger layouts command a **higher** median rate per m², not a "
            "lower one: about AED 14,845/m² for a studio against AED 19,943/m² for a 4-bed.",
        ],
        does_not_tell=[
            "Nothing about total price — a studio at a high rate is still a cheaper home.",
            "Nothing about which layout is the better investment.",
        ],
        limitations=_COMMON_LIMITS + [
            "Layouts with very few sales (6 B/R, 7 B/R) are excluded from the panels and "
            "reported in the note instead.",
        ],
        validation="Quartiles were recomputed directly in pandas and matched. The earlier "
                   "claim that smaller units cost more per m² was tested against the data "
                   "and **did not hold**, so it was removed.",
        client_explanation="Bigger apartments in Dubai are not cheaper per square metre — "
                           "they are more expensive per square metre. The value is in the "
                           "location and the building, not in buying bulk.",
    ),
    ChartInfo(
        key="reg_type_split",
        title="Off-plan vs existing",
        section="Property",
        icon="🏗️",
        subtitle="Share of transactions by registration type.",
        what="The split between properties bought before completion (off-plan) and "
             "already-built stock (existing).",
        why="It is the single biggest structural divide in the Dubai market and it "
            "affects almost every other figure on this dashboard.",
        columns=["reg_type_en"],
        preparation="None. `reg_type_en` is a clean two-value field with no missing rows.",
        calculation="`count(rows)` per registration type, shown as shares.",
        legend="One slice per registration type.",
        how_to_read=["A majority off-plan share means a developer-led market."],
        tells_us=["Whether the market is being driven by new supply or by resale."],
        does_not_tell=["Nothing about completion risk or delivery timing."],
        limitations=_COMMON_LIMITS,
        validation="Verified against the raw registry: the same two values, "
                   "`reg_type_id` 0 = Off-Plan and 1 = Existing, with no nulls.",
        client_explanation="How much of Dubai's market is buying off-plan from a developer "
                           "versus buying a finished home.",
    ),
    ChartInfo(
        key="procedure_split",
        title="Transaction procedure",
        section="Property",
        icon="🧾",
        subtitle="The registration procedure recorded against each sale.",
        what="The land-department procedure under which each sale was registered.",
        why="Different procedures represent different kinds of transaction, and the mix "
            "shifts as the market shifts between new and resale stock.",
        columns=["procedure_name_en"],
        preparation="Top six procedures shown.",
        calculation="`count(rows)` per procedure.",
        legend="One slice per procedure.",
        how_to_read=["'Sell – Pre registration' corresponds to off-plan; 'Sell' to "
                     "completed property."],
        tells_us=["The registration composition of the market."],
        does_not_tell=["Nothing about price."],
        limitations=_COMMON_LIMITS + ["Only the six most common procedures are shown."],
        validation="Procedure counts cross-checked against the registration-type split.",
        client_explanation="The legal form each sale took — useful context, rarely the "
                           "headline.",
    ),
    ChartInfo(
        key="size_vs_price",
        title="Size against price",
        section="Property",
        icon="🔵",
        subtitle="Each dot is one transaction.",
        what="A scatter of unit size against sale price, coloured by layout.",
        why="Shows the size-price relationship directly, and makes unusual deals visible.",
        columns=["procedure_area", "actual_worth", "rooms_en"],
        preparation="A deterministic random sample of 15,000 transactions "
                    "(`random_state=42`) is drawn so the chart stays responsive. The "
                    "sample size is printed on screen and the shape of the relationship "
                    "is unchanged.",
        calculation="No aggregation — raw transaction values.",
        x_axis="Unit size (m²).",
        y_axis="Sale price (AED).",
        legend="Colour = layout.",
        how_to_read=[
            "The upward cloud is the basic size-price relationship.",
            "Points well above the cloud for their size are premium deals; well below "
            "are discounts or unusual registrations.",
        ],
        tells_us=["How strongly size drives price, and how much scatter there is around it."],
        does_not_tell=["Nothing about *why* a specific point sits where it does."],
        limitations=_COMMON_LIMITS + [
            "It is a sample, so the very rarest transactions may not appear.",
        ],
        validation="Sample medians were compared with full-population medians and agree.",
        client_explanation="Size explains a lot of price in Dubai — but far from all of it. "
                           "The vertical spread at any given size is the location and "
                           "building premium.",
    ),

    # ═════════════════════════════════════════════════════════════════ PRICE ══
    ChartInfo(
        key="price_rate_trend",
        title="How prices are moving",
        section="Price",
        icon="📈",
        subtitle="Median sale price and median rate per m², monthly, with optional smoothing.",
        what="Two monthly series: the median total price paid, and the median price per "
             "square metre. A control lets you show the actual monthly observations, a "
             "smoothed trend, or both together.",
        why="These answer two different questions. Median total price moves when the "
            "**mix** of what people buy changes. Median rate per m² is the cleaner read "
            "on whether Dubai property itself is getting more expensive.",
        columns=["year_month", "instance_date", "actual_worth", "meter_sale_price"],
        preparation="Transactions grouped by calendar month. Every month in the series "
                    "carries at least 814 transactions (median 2,437), so the "
                    "month-to-month movement is genuine market and mix churn, not "
                    "small-sample noise — smoothing is applied for readability only and "
                    "never replaces the underlying observations.",
        calculation="Per month: `median(actual_worth)` and `median(meter_sale_price)`. "
                    "The smoothed series is a **centred LOWESS fit** — locally weighted "
                    "regression, `statsmodels` `lowess`, three robustifying iterations — of "
                    "those monthly medians. The span is derived from the length of the "
                    "selected series, about a ten-month window, so the trend responds to the "
                    "sidebar filters rather than being fixed to the unfiltered data. "
                    "Smoothing reduces the standard deviation of month-on-month change in "
                    "the rate series from 7.6% to about 1.4% without moving the level.",
        x_axis="Month.",
        y_axis="Median sale price (AED).",
        y2_axis="Median rate per m² (AED/m²).",
        legend="Blue = median sale price. Teal = median rate per m². When both views are "
               "shown, the faint line is the actual monthly observation and the solid "
               "line is the smoothed trend.",
        how_to_read=[
            "Use **Smoothed trend** to read direction, and **Actual monthly** to see the "
            "real observations and any single unusual month.",
            "Blue and teal diverging means the mix of what is being bought is changing, "
            "not just the price level.",
        ],
        tells_us=["The direction and pace of price movement, on two different measures."],
        does_not_tell=[
            "Nothing about individual properties or specific areas.",
            "The smoothed line is a reading aid, not a forecast.",
        ],
        limitations=_COMMON_LIMITS + [
            "The final point (August 2026) covers only 6 days and 2,157 transactions "
            "against about 10,800 in a full month. It is flagged on the chart and is the "
            "cause of the sharp drop at the right-hand edge.",
            "**LOWESS was chosen over exponential smoothing on measured evidence, not preference.** On this series LOWESS is both calmer (1.38% vs 3.82% month-on-month movement in the trend) and closer to the observations (2.61% vs 3.51% median deviation). A smoother normally buys calmness by drifting away from the data; LOWESS manages both because it is centred and can use the months on either side of a point, whereas exponential smoothing only looks backwards and must trail every turning point.",
            "Being centred, the first and last months are fitted from fewer neighbouring observations than the middle of the series, so the two ends are the least certain part of the line.",
            "**The trend never extends past the last observed month.** LOWESS is only defined over observed data and does not extrapolate, so no future value is produced. The partial final month is excluded from the fit and the trend line stops at the last complete month, so an incomplete count cannot bend the trend.",
        ],
        validation="Monthly medians were recomputed directly from the parquet and matched. "
                   "Every month's transaction count was checked for thin samples — the "
                   "smallest is 814 (May 2020) — confirming the jaggedness is real and "
                   "not a data artefact.",
        client_explanation="“Are prices going up?” Watch the teal line: that is price per "
                           "square metre, which is not affected by whether people happened "
                           "to buy bigger homes this month.",
    ),
    ChartInfo(
        key="offplan_vs_existing",
        title="Off-plan vs existing pricing",
        section="Price",
        icon="🏗️",
        subtitle="Median rate per m² by year, plus the off-plan premium or discount.",
        what="Two yearly lines — one for off-plan sales, one for existing property — and "
             "a companion chart showing the gap between them as a percentage.",
        why="To answer directly whether off-plan trades at a premium or a discount, "
            "rather than leaving it to be eyeballed from two lines.",
        columns=["year", "reg_type_en", "meter_sale_price"],
        preparation="`reg_type_en` was validated on the raw registry: exactly two values "
                    "(`reg_type_id` 0 = Off-Plan Properties, 1 = Existing Properties) with "
                    "no missing rows, so no reclassification was needed. Years with fewer "
                    "than 100 transactions on either side are excluded from the premium "
                    "calculation.",
        calculation="Per year and registration type: `median(meter_sale_price)`. "
                    "Premium (%) = (off-plan median − existing median) ÷ existing median "
                    "× 100. Positive means off-plan is more expensive.",
        x_axis="Year.",
        y_axis="Median rate per m² (AED/m²) — and, on the companion chart, premium (%).",
        legend="Blue = existing property. Teal = off-plan. On the premium chart, teal bars "
               "are a premium and red bars a discount.",
        how_to_read=[
            "Where the teal line sits above the blue line, buyers are paying more per m² "
            "for unbuilt stock.",
            "The premium chart states the size of that gap directly, year by year.",
        ],
        tells_us=[
            "Off-plan has traded at a **premium in every single year** from 2010 to 2026 "
            "in this dataset, ranging from +4.4% (2011) to +70.9% (2019).",
            "The premium peaked around 2022 (+69.7%) and has narrowed since, to +25.6% "
            "in 2026 — existing stock has been catching up.",
        ],
        does_not_tell=[
            "It does **not** mean an unbuilt apartment is worth more than the finished "
            "one next to it. Held inside a single building, the premium disappears — see "
            "*Why off-plan looks more expensive* directly below this chart.",
            "It does **not** mean off-plan is overpriced. Off-plan and existing stock are "
            "different products in different buildings: newer, higher-graded, in newer "
            "master developments, with payment spread over construction.",
            "Nothing about completion risk, delivery delay or handover quality.",
        ],
        limitations=_COMMON_LIMITS + [
            "**The comparison is not like-for-like, and the difference is not small.** "
            "The two groups differ systematically in building, grade, price tier, area "
            "and developer. Value every building at its own median rate and off-plan "
            "buyers are transacting in buildings worth AED 19,445/m² against AED "
            "12,486/m² for existing buyers — a 55.7% gap, which is almost the whole "
            "headline.",
            "Off-plan prices are registered at contract date; existing prices at sale — "
            "so the two series carry slightly different timing meanings.",
            "The registry records the headline contract price. An off-plan price paid "
            "over three years of construction is not the same money as a resale price "
            "paid at once, and that difference is invisible here.",
        ],
        validation="Recomputed independently in pandas for all 17 years, with transaction "
                   "counts on both sides of every comparison. The premium is positive in "
                   "17 of 17 years. The classification was verified against the raw "
                   "registry rather than assumed, and against the completion dates: 84% "
                   "of off-plan sales occur before the building is finished (median 1.6 "
                   "years before) while existing sales occur a median 2.9 years after.",
        client_explanation="Buyers in Dubai consistently pay more per square metre for "
                           "off-plan than for finished property — but that is because "
                           "off-plan stock is newer and better located. In the same "
                           "building the gap is gone. Quote this chart together with the "
                           "one below it, never on its own.",
    ),
    ChartInfo(
        key="amenities_headline",
        title="How amenities relate to price — headline comparison",
        section="Price",
        icon="✨",
        subtitle="Median rate per m² for units with an amenity against those without.",
        what="For each amenity flag, the straight difference in median rate per m² "
             "between units that carry the flag and units that do not.",
        why="It is the first question every client asks. It is also the most easily "
            "misread number on the dashboard, which is why the like-for-like comparison "
            "sits directly beside it.",
        columns=["has_parking", "swimming_pool", "balcony", "elevator", "metro",
                 "meter_sale_price"],
        preparation="All five flags are complete 0/1 integers with **no missing values**. "
                    "Nothing is imputed and no missing value is treated as a “No”. "
                    "Critically, a 0 means “not recorded as present”, which is not the "
                    "same as “absent” — see the limitations. A group must have at least "
                    "50 transactions on each side to appear.",
        calculation="Difference (%) = (median rate with the amenity − median rate without) "
                    "÷ median rate without × 100.",
        x_axis="Median rate difference versus units without the amenity (%).",
        y_axis="Amenity.",
        legend="Teal = higher median rate with the amenity. Red = lower.",
        how_to_read=[
            "Read this as a **description of two groups of properties**, not as the value "
            "of a feature.",
            "Always read it together with the like-for-like chart beneath it — the two "
            "answer different questions.",
        ],
        tells_us=[
            "How the two groups of properties differ in realised price per m².",
        ],
        does_not_tell=[
            "It does **not** say what an amenity is worth, and it does not support any "
            "causal statement. Parking at +102% does not mean parking doubles a price.",
            "The groups differ in area, layout, building age and — decisively — in "
            "whether the sale was off-plan or existing.",
        ],
        limitations=_COMMON_LIMITS + [
            "**Only `has_parking` exists in the raw registry.** The pool, balcony, "
            "elevator and metro flags are engineered fields that exist only in the "
            "cleaned dataset, so they cannot be re-derived from the raw file.",
            "A 0 conflates “this property does not have it” with “this was never "
            "recorded”. Recording is far more complete for existing property than for "
            "off-plan: a balcony is recorded for 88.8% of existing sales but only 32.9% "
            "of off-plan sales.",
            "Because off-plan trades at a much higher rate per m² than existing "
            "(AED 17,879 vs AED 11,264 median), any flag that is under-recorded off-plan "
            "will show a spurious negative headline.",
        ],
        validation="Every median was recomputed directly from the parquet and matched to "
                   "one decimal place (see `tests/verify_dubai_numbers.py`). Group sizes, "
                   "encodings and null counts were checked for all five flags.",
        client_explanation="This chart compares two piles of properties. It does not "
                           "price a feature. The chart below it does the fairer comparison.",
    ),
    ChartInfo(
        key="amenities_like_for_like",
        title="How amenities relate to price — like-for-like",
        section="Price",
        icon="⚖️",
        subtitle="The same comparison, held within area, layout, year and registration type.",
        what="The amenity comparison repeated inside narrow, comparable groups of "
             "properties, then averaged across those groups.",
        why="The headline comparison is dominated by *which* properties carry each flag. "
            "Comparing only within a single area, layout, year and registration type "
            "removes most of that, leaving a far fairer estimate.",
        columns=["has_parking", "swimming_pool", "balcony", "elevator", "metro",
                 "area_name_en", "rooms_en", "year", "reg_type_en", "meter_sale_price"],
        preparation="Transactions are grouped into area × layout × year × registration-type "
                    "cells. A cell is used only when it contains at least **30** "
                    "transactions on each side of the comparison.",
        calculation="Within each cell, (median rate with − median rate without) ÷ median "
                    "rate without × 100. Cell results are averaged across cells, weighted "
                    "by the number of transactions in each cell.",
        x_axis="Like-for-like median rate difference (%).",
        y_axis="Amenity.",
        legend="Teal = higher, red = lower. The table beside it reports how many "
               "comparable groups and transactions each figure rests on.",
        how_to_read=[
            "This is the number to quote. Compare it with the headline above to see how "
            "much of the raw gap was simply property mix.",
        ],
        tells_us=[
            "Controlling for area, layout, year and registration type, the picture changes "
            "completely: parking +5.2%, pool +7.6%, elevator +6.1%, balcony −2.1%, "
            "near-metro −8.2%.",
            "Four of the five headline results were composition effects, not amenity "
            "effects.",
        ],
        does_not_tell=[
            "Still not causal. Cells control for four characteristics, not for building "
            "quality, floor level, view, finish or developer.",
            "It cannot tell you what a specific building should charge.",
        ],
        limitations=_COMMON_LIMITS + [
            "Requiring 30 transactions on both sides of every cell restricts the analysis "
            "to the busier areas and common layouts.",
            "Parking rests on the fewest comparable cells, because 95% of the cleaned "
            "dataset carries the flag.",
        ],
        validation="Computed at three levels of control and compared: no control, "
                   "area × layout × year, and area × layout × year × registration type. "
                   "The progressive collapse of every headline figure is itself the "
                   "evidence that the headline was a composition effect.",
        client_explanation="Once you compare like with like — same area, same size of "
                           "apartment, same year, same off-plan status — most of the "
                           "dramatic amenity differences disappear. That is the honest "
                           "answer.",
    ),
    ChartInfo(
        key="price_bands",
        title="Where the price points are",
        section="Price",
        icon="💵",
        subtitle="Transactions by sale-price band.",
        what="The market split into seven price bands, with counts and shares in a table "
             "beside the chart.",
        why="The quickest way to see which price points the Dubai market actually trades at.",
        columns=["actual_worth"],
        preparation="Bands are left-closed and right-open (`< 500K` means below 500,000; "
                    "`500K – 1M` means 500,000 up to but not including 1,000,000), so "
                    "every transaction falls in exactly one band and no transaction is "
                    "counted twice. Validated on the raw registry: no null, zero or "
                    "negative sale prices, and no duplicate transaction identifiers.",
        calculation="`count(rows)` per band; share = band count ÷ total filtered "
                    "transactions × 100.",
        x_axis="Price band (AED).",
        y_axis="Number of transactions.",
        legend="Bar labels show each band's share of the current selection.",
        how_to_read=[
            "The tallest bars are where the market actually is.",
            "The right-hand tail is the luxury segment.",
            "**Check the note under the chart**: the sale-price slider defaults to the "
            "1st–99th percentile, which truncates the top bands. Widen it to see them.",
        ],
        tells_us=[
            "Two-thirds of Dubai's residential unit sales fall between AED 500K and 2M.",
        ],
        does_not_tell=[
            "Nothing about size or value for money — a 2M studio and a 2M three-bed are "
            "in the same band.",
        ],
        limitations=_COMMON_LIMITS + [
            "The bands are fixed business bands, not derived from the distribution.",
            "The default price filter hides the top of the range. Unfiltered, the cleaned "
            "dataset contains 5,308 sales at AED 10M or more (0.6%).",
        ],
        validation="Recomputed on the raw registry, the raw residential-unit subset and "
                   "the cleaned dataset. In all three the band counts sum exactly to the "
                   "row count with zero unassigned rows, confirming the bands are "
                   "exhaustive and mutually exclusive. Chart and table are generated from "
                   "the same computed frame, so they cannot disagree.",
        client_explanation="Where Dubai's money actually gets spent — and it is not at the "
                           "top end.",
    ),
    ChartInfo(
        key="forecast",
        title="Published price forecast",
        section="Price",
        icon="🔮",
        source=SOURCE_DERIVED,
        subtitle="Quarterly ARIMA forecasts of rate per m², produced by the existing modelling work.",
        what="The fitted history and forward forecast of quarterly rate per m² for one "
             "area, with a confidence band, plus the model's published accuracy.",
        why="To put a forward view next to the historical analysis, using the results the "
            "project's modelling pipeline already produced.",
        columns=["ds", "area_name_en", "yhat", "actual", "type", "yhat_lower", "yhat_upper",
                 "forecast_quarter", "forecast_price", "growth_factor", "Test_MAPE", "Test_MAE"],
        preparation="Read directly from the stored CSV outputs. **Nothing is refitted at "
                    "run time.** Only the modelled subset of areas is available, not all 69.",
        calculation="None performed here — the ARIMA/SARIMA fitting was done by the "
                    "existing pipeline. This chart displays its published output.",
        x_axis="Quarter.",
        y_axis="Rate per m² (AED/m²).",
        legend="Grey = actual quarterly rate. Dotted teal = model fit to history. "
               "Blue = forecast. Shaded band = the forecast's uncertainty range.",
        filters="**The Dubai sidebar filters do not apply to this chart** — it displays "
                "stored model output for a single area chosen from its own selector.",
        how_to_read=[
            "Check the dotted fit against the grey actuals first: if the model tracked "
            "history poorly, treat the forecast with caution.",
            "A wider shaded band means less confidence.",
            "Read the Test MAPE beside the chart — it is the model's average error on "
            "data it had not seen.",
        ],
        tells_us=["The modelled forward path for the areas that were modelled."],
        does_not_tell=[
            "Nothing about areas that were not modelled.",
            "A forecast is not a commitment; the band is part of the answer, not decoration.",
        ],
        limitations=_COMMON_LIMITS[:1] + [
            "Covers only the subset of areas the pipeline modelled.",
            "Produced at a fixed point in time; it does not update with the dashboard data.",
            "Sidebar filters have no effect on it.",
        ],
        validation="Files are read as published; the app reports any that are missing "
                   "rather than silently drawing an empty chart.",
        client_explanation="Our modelling team's forward view for this area, shown with its "
                           "own error record so you can judge how much to trust it.",
    ),

    # ══════════════════════════════════════════════════════════ DISTRIBUTION ══
    ChartInfo(
        key="dist_price",
        title="Sale price distribution",
        section="Distribution",
        icon="📊",
        subtitle="How sale prices are spread.",
        what="A histogram of sale prices across the current selection.",
        why="Averages hide shape. This shows where transactions actually cluster.",
        columns=["actual_worth"],
        preparation="The chart trims the extreme 0.5% at each end so the bars remain "
                    "legible; the dashed median line is computed on the **untrimmed** "
                    "data. Binning is done in numpy rather than in the browser — the "
                    "chart is identical, just far lighter.",
        calculation="60 equal-width bins between the 0.5th and 99.5th percentiles; "
                    "`count(rows)` per bin.",
        x_axis="Sale price (AED).",
        y_axis="Number of transactions.",
        legend="Dashed amber line marks the median.",
        how_to_read=["The long right tail is normal for property — a few very large deals "
                     "pull the average above the median."],
        tells_us=["The shape of the market, not just its centre."],
        does_not_tell=["Nothing about size, location or quality."],
        limitations=_COMMON_LIMITS + ["The visible range is trimmed at each end."],
        validation="Bin counts were checked to sum to the trimmed row count.",
        client_explanation="What a typical Dubai transaction costs, and how unusual the "
                           "big ones are.",
    ),
    ChartInfo(
        key="dist_rate",
        title="Rate per m² distribution",
        section="Distribution",
        icon="📊",
        subtitle="How rate per m² is spread.",
        what="A histogram of price per square metre.",
        why="More than one peak would indicate genuinely separate market tiers rather "
            "than one continuous market.",
        columns=["meter_sale_price"],
        preparation="Same as the sale-price histogram: 0.5% trimmed each end for display, "
                    "median computed untrimmed.",
        calculation="60 equal-width bins; `count(rows)` per bin.",
        x_axis="Rate per m² (AED/m²).",
        y_axis="Number of transactions.",
        legend="Dashed amber line marks the median.",
        how_to_read=["Look for whether the shape is one hump or several."],
        tells_us=["Whether Dubai prices as one market or as distinct tiers."],
        does_not_tell=["Nothing about which properties sit where in the distribution."],
        limitations=_COMMON_LIMITS + ["The visible range is trimmed at each end."],
        validation="Bin counts sum to the trimmed row count.",
        client_explanation="Is Dubai one market or several? This is where you can see it.",
    ),
    ChartInfo(
        key="dist_size",
        title="Unit size distribution",
        section="Distribution",
        icon="📐",
        subtitle="How unit sizes are spread.",
        what="A histogram of registered floor area.",
        why="Clusters correspond to standard studio, one-bed and two-bed layouts.",
        columns=["procedure_area"],
        preparation="0.5% trimmed each end for display.",
        calculation="60 equal-width bins; `count(rows)` per bin.",
        x_axis="Unit size (m²).",
        y_axis="Number of transactions.",
        legend="Dashed amber line marks the median.",
        how_to_read=["The peaks line up with the standard layouts in the Property section."],
        tells_us=["The physical shape of Dubai's residential stock as traded."],
        does_not_tell=["Nothing about layout quality or usable versus registered area."],
        limitations=_COMMON_LIMITS,
        validation="Peaks were cross-checked against median sizes per layout.",
        client_explanation="The standard sizes Dubai builds and sells.",
    ),
    ChartInfo(
        key="dist_price_by_reg",
        title="Sale price by registration type",
        section="Distribution",
        icon="🏗️",
        subtitle="Price spread for off-plan and existing property.",
        what="Box plots of sale price for each registration type, on a log scale.",
        why="Compares not just the typical price but the whole spread of each segment.",
        columns=["reg_type_en", "actual_worth"],
        preparation="Quartiles computed in pandas; whiskers reach the furthest "
                    "observation within 1.5 × IQR. No transaction is deleted.",
        calculation="25th percentile, median, 75th percentile and 1.5 × IQR whiskers per "
                    "registration type.",
        x_axis="Registration type.",
        y_axis="Sale price (AED) on a logarithmic scale, so the full range fits.",
        legend="One box per registration type.",
        how_to_read=["The box is the middle 50%. Note the **log scale** — equal distances "
                     "represent equal ratios, not equal amounts."],
        tells_us=["How the two segments differ in both level and spread."],
        does_not_tell=["Nothing about rate per m² — see the Price section for that."],
        limitations=_COMMON_LIMITS + ["A log axis makes differences look smaller than they are."],
        validation="Quartiles recomputed in pandas and matched.",
        client_explanation="Off-plan and existing are not just priced differently — they "
                           "have different spreads.",
    ),
    ChartInfo(
        key="rate_violin_year",
        title="How the price distribution has changed",
        section="Distribution",
        icon="🎻",
        subtitle="Rate per m², year by year.",
        what="One violin per year showing the full distribution of rate per m².",
        why="A median only tells you the centre. This shows whether the market is also "
            "spreading out.",
        columns=["year", "meter_sale_price"],
        preparation="A deterministic random sample of 45,000 transactions "
                    "(`random_state=42`) keeps the chart responsive; the distribution "
                    "shape is preserved.",
        calculation="Kernel density estimate of `meter_sale_price` per year, with an "
                    "inner box plot.",
        x_axis="Year.",
        y_axis="Rate per m² (AED/m²).",
        legend="One violin per year; colour is for identification only.",
        how_to_read=[
            "Wider at a given height = more transactions at that price level.",
            "Watch two things: the centre moving up, and the shape getting wider. The "
            "second means the market is spreading, not just rising.",
        ],
        tells_us=["How the whole price distribution has evolved, not just its midpoint."],
        does_not_tell=["Nothing about which segments drove the change."],
        limitations=_COMMON_LIMITS + [
            "Based on a sample.",
            "2026 covers eight months only.",
        ],
        validation="Sampled medians per year were compared with full-population medians "
                   "and agree.",
        client_explanation="The market has not just moved up — it has spread out. That "
                           "matters for how you price a specific unit.",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# THE NEW CHART ADDED IN v1.2.1
# ─────────────────────────────────────────────────────────────────────────────

CHARTS.append(ChartInfo(
    key="amenities_ladder",
    title="Why the raw amenity number is so much bigger",
    section="Price",
    icon="🔎",
    subtitle="The same amenity, measured under progressively fairer comparisons.",
    what="One bar per comparison, read top to bottom. The top bar compares every unit "
         "carrying the amenity flag against every unit without it, whatever kind of "
         "property they are. Each bar below it compares only properties that also match "
         "on one more characteristic — first area, then layout, then year, then "
         "off-plan status. The bottom bar is the fair comparison.",
    why="Because the raw amenity number is the single most misread figure on this "
        "dashboard, and telling somebody “it is a composition effect” does not help "
        "them. Watching the gap melt as the comparison gets fairer does.",
    columns=["has_parking", "swimming_pool", "balcony", "elevator", "metro",
             "meter_sale_price", "area_name_en", "rooms_en", "year", "reg_type_en"],
    preparation="Rows are filtered by the sidebar selection. For every level except the "
                "first, properties are grouped into matched sets and a set must hold at "
                "least 30 transactions on each side to be used, so a handful of deals "
                "cannot swing the answer.",
    calculation="Level 0 is `(median rate with ÷ median rate without − 1) × 100` across "
                "the whole selection. Each level after that computes that same "
                "percentage **inside every matched set separately**, then averages the "
                "sets weighted by how many transactions each holds.",
    x_axis="Difference in median rate per m², in percent.",
    y_axis="How tightly the comparison is controlled.",
    legend="Amber = the raw, uncontrolled comparison. Grey = partly controlled. "
           "Teal or red = the fair comparison, and its direction.",
    how_to_read=[
        "Start at the **top** bar — that is the raw number, the one people quote, and "
        "it is usually the biggest.",
        "Work downwards. Each bar removes one more reason the two groups of properties "
        "might differ for reasons that have nothing to do with the amenity.",
        "The **bottom bar is the answer.** If it is much smaller than the top one, the "
        "raw number was mostly describing which kind of property carries the label.",
        "The middle bars can move up as well as down. That is expected — each level is "
        "measured on a different set of comparable properties, so the sample changes "
        "as well as the control. Only the top and bottom bars are meant to be compared "
        "directly.",
    ],
    tells_us=[
        "How much of an amenity's apparent price gap survives once you compare "
        "comparable properties.",
        "Which characteristic does the damage — the level where the bar suddenly "
        "shrinks is the one that was really driving the raw number.",
    ],
    does_not_tell=[
        "It still does not prove causation. Even the bottom bar is an association "
        "measured across four controls, not an experiment.",
        "It cannot control for floor level, view, finish, service charge or developer "
        "— none of those are in the dataset.",
    ],
    limitations=_COMMON_LIMITS + [
        "Tightening the comparison also shrinks the sample: the fairest level uses "
        "fewer transactions than the raw one. Both counts are on the hover.",
        "If the selection is narrow, some levels may not have any matched set large "
        "enough and will be missing from the chart.",
    ],
    validation="Every level was recomputed independently with plain pandas in "
               "`tests/verify_dubai_changes.py`, including the weighting and the "
               "30-transaction floor.",
    client_explanation="“The big number compares two different kinds of property. When "
                       "we compare like with like, the difference is this much.” That "
                       "is the whole story in one picture.",
))

CHART_BY_KEY = {c.key: c for c in CHARTS}


CHARTS.append(ChartInfo(
    key="offplan_ladder",
    title="Why off-plan looks more expensive",
    section="Price",
    icon="🏢",
    subtitle="The off-plan premium, measured under progressively fairer comparisons.",
    what="One bar per comparison, read top to bottom. The top bar is the straight "
         "off-plan-against-existing comparison. Each bar below it compares only sales "
         "that also match on one more thing — same year, then same area, then same "
         "master development, then same project, then the same building. The bottom "
         "bar compares units in a single building in a single year.",
    why="Because the headline contradicts common sense, and the contradiction is the "
        "interesting part. A finished apartment can be walked through, inspected and "
        "moved into; an off-plan one cannot. It should not be worth less. The ladder "
        "shows that it is not — the premium belongs to the buildings off-plan is sold "
        "in, not to being unbuilt.",
    columns=["reg_type_en", "meter_sale_price", "area_name_en", "master_project_en",
             "project_name_en", "building_name_en", "year"],
    preparation="Rows are filtered by the sidebar selection. For every level except the "
                "first, sales are grouped into matched sets and a set must hold at least "
                "30 transactions on each side to be used.",
    calculation="Level 0 is `(off-plan median rate ÷ existing median rate − 1) × 100` "
                "across the whole selection. Each level below computes that same "
                "percentage **inside every matched set separately**, then averages the "
                "sets weighted by how many transactions each holds. The same function "
                "computes the amenity ladder, so the two arguments are made the same way.",
    x_axis="Difference in median rate per m² between off-plan and existing, in percent.",
    y_axis="How tightly the comparison is controlled.",
    legend="Amber = the raw, uncontrolled comparison. Grey = partly controlled. "
           "Teal or red = the same-building comparison, and its direction.",
    how_to_read=[
        "The **top** bar is the number on the chart above it — around +59% across the "
        "whole dataset.",
        "Area and master development barely dent it, because a single area contains "
        "both old cheap towers and new luxury ones.",
        "It collapses at **project** and **building** level. Inside one building, "
        "off-plan is not dearer — it is slightly cheaper.",
        "That is the answer: the premium is a statement about **which buildings** are "
        "sold off-plan, not about buying before completion.",
    ],
    tells_us=[
        "That the off-plan premium is a stock-quality effect, not a payment-for-risk "
        "effect.",
        "Roughly where the effect lives — between master development and individual "
        "building, i.e. in the specific tower rather than the neighbourhood.",
    ],
    does_not_tell=[
        "It does not say a specific off-plan purchase is good or bad value. That "
        "depends on the building, the payment plan and the handover date.",
        "It cannot see payment terms. An off-plan headline price paid over three years "
        "is not the same money as a resale price paid at once, and the registry records "
        "only the headline.",
        "It says nothing about what happens to an off-plan unit's value after handover.",
    ],
    limitations=_COMMON_LIMITS + [
        "The same-building level is a much smaller sample than the headline: a building "
        "needs 30 off-plan **and** 30 existing sales in the same year to qualify. Counts "
        "are on the hover, and a larger pooled-across-years figure is shown beside the "
        "chart as a cross-check.",
        "Buildings with both kinds of sale in one year are typically at or just past "
        "handover, so the same-building comparison leans towards recently completed "
        "stock rather than the whole market.",
        "Off-plan and existing are not identical products even inside one building — "
        "different floors, views and finishes are not in this dataset.",
    ],
    validation="Every level was recomputed independently with plain pandas in "
               "`tests/verify_dubai_changes.py`. The classification itself was checked "
               "against the completion dates: 84% of off-plan sales occur before the "
               "building is finished, a median 1.6 years before, while existing sales "
               "occur a median 2.9 years after — so the label means what it says.",
    client_explanation="“Off-plan sells for more per square metre because off-plan stock "
                       "is newer and better located — not because buyers pay a premium "
                       "for something they cannot see. Put an off-plan and a finished "
                       "unit in the same building and the gap disappears.”",
))

CHART_BY_KEY = {c.key: c for c in CHARTS}


# ─────────────────────────────────────────────────────────────────────────────
# v1.3 — RAW volume · yearly summary · controlled amenity · floor band
# ─────────────────────────────────────────────────────────────────────────────

SOURCE_RAW_COUNTS = (
    "RAW",
    "data/dubai/transactions.parquet",
    "The full Dubai transaction registry exactly as supplied, 1,762,262 rows. "
    "Transaction counts are taken from here, restricted to residential unit sales "
    "(928,489 rows) so the population matches the rest of the page, with no "
    "cleaning applied.",
)

_V13 = [
    ChartInfo(
        key="raw_yoy_volume",
        title="Transactions recorded each year",
        section="Trends",
        icon="📊",
        subtitle="Counted from the raw registry, with year-over-year growth.",
        source=SOURCE_RAW_COUNTS,
        what="Bars are the number of sales registered in each year, taken straight from the "
             "raw registry. The dotted line is the change against the year immediately "
             "before. The most recent year is still in progress and is drawn in amber.",
        why="Because a transaction count should say how many transactions were recorded. "
            "The cleaned dataset has had rows removed by preprocessing — between 668 and "
            "7,369 a year — so counting there understates activity. Price analysis still "
            "uses the cleaned file; volume does not.",
        columns=["instance_date", "trans_group_en", "property_type_en", "property_usage_en"],
        preparation="Rows are counted, never loaded in full: only four columns are read and "
                    "the result is a count per year and month. The population is the same "
                    "one the rest of the page uses — sales, of units, in residential use — "
                    "taken from the registry with no cleaning. The count across the entire "
                    "registry, including mortgages, gifts, land and villas, is reported "
                    "beside it in the table and on the hover so neither figure is hidden.",
        calculation="Per completed year: `((this year − previous year) ÷ previous year) × "
                    "100`, chained so every year is measured against the one directly "
                    "before it. The first year in the series is the base and carries no "
                    "growth figure. **The incomplete final year is handled separately** — "
                    "see the limitations.",
        x_axis="Year.",
        y_axis="Transactions recorded (left axis).",
        y2_axis="Year-over-year growth, in percent (right axis).",
        legend="Two series: the bars are transactions recorded, the dotted line is "
               "year-over-year growth. The incomplete year's bar is amber and is annotated "
               "with the period actually covered.",
        filters="**None.** This is the one Dubai chart the sidebar does not filter, because "
                "it answers “how many transactions were registered”, not “how many match my "
                "selection”. Every other chart on the page responds to the filters.",
        how_to_read=[
            "The bars are counts — read them as they are.",
            "The dotted line only exists for completed years. Where it is missing, no "
            "comparable annual figure exists.",
            "The amber bar is the year in progress. Its height is a real count of a shorter "
            "period, so it is **not** comparable with the full years beside it.",
        ],
        tells_us=[
            "How many residential unit sales were registered in Dubai each year.",
            "Which years grew and which contracted, measured against the year before.",
        ],
        does_not_tell=[
            "Nothing about prices — this is volume only.",
            "It does not forecast how the incomplete year will finish.",
        ],
        limitations=[
            "**The incomplete year never shows a negative or zero growth figure.** Comparing "
            "part of a year against a whole one produces a decline that is an artefact of "
            "the calendar, not the market. A percentage appears for that year only when the "
            "like-for-like comparison against the same months of the previous year is "
            "strictly positive.",
            "The counts are registrations, so a sale appears on the date it was registered, "
            "not the date it was agreed.",
            "The registry starts in 1966, but the series begins at 2011 so that every bar "
            "has a comparable predecessor.",
        ],
        validation="Counted directly from the raw parquet and cross-checked against the "
                   "cleaned dataset year by year: the raw slice is larger in every single "
                   "year, by 668 to 7,369 transactions, which is the preprocessing loss "
                   "this chart exists to avoid. Duplicate transaction identifiers in the "
                   "raw registry: zero.",
        client_explanation="“This is how many homes actually changed hands each year, "
                           "counted from the registry itself. The current year is only "
                           "part-complete, so we show the count but not a growth rate.”",
    ),

    ChartInfo(
        key="yearly_summary",
        title="Year-by-year summary",
        section="Price",
        icon="📋",
        subtitle="Transactions, mean rate and median rate for every year.",
        what="A table with one row per year: how many transactions were recorded, the mean "
             "rate per m², and the median rate per m².",
        why="A compact reference that answers most year-level questions without reading a "
            "chart, and puts the mean and the median side by side so the difference between "
            "them is visible.",
        columns=["instance_date", "trans_group_en", "property_type_en", "property_usage_en",
                 "year", "meter_sale_price"],
        preparation="**Two sources, on purpose.** The transaction count is taken from the "
                    "raw registry so it is not reduced by cleaning. The mean and median "
                    "rate come from the cleaned dataset, which is the validated basis for "
                    "every price figure on this page and which responds to the sidebar "
                    "filters. Each column is labelled with its source, and the number of "
                    "priced transactions actually used is shown so the two are never "
                    "confused.",
        calculation="Transactions: `count(rows)` per year on the raw registry. Mean rate: "
                    "`mean(meter_sale_price)`. Median rate: `median(meter_sale_price)`. "
                    "Both on the cleaned, filtered selection.",
        x_axis="Rows are years.",
        y_axis="Columns are transactions, mean rate and median rate.",
        legend="Not applicable — this is a table.",
        how_to_read=[
            "The mean sits above the median in every year. That gap is the effect of a "
            "small number of very large deals.",
            "The median is the figure to quote for a typical transaction.",
            "The final row is the year in progress and is labelled with the period covered.",
        ],
        tells_us=[
            "The level and direction of rates year by year, alongside how busy each year was.",
        ],
        does_not_tell=[
            "It makes no comparison between off-plan and existing property, and no claim "
            "about a premium or discount.",
            "Transaction counts and rate statistics come from different files, so the "
            "count is not the number of rows behind the rate.",
        ],
        limitations=_COMMON_LIMITS + [
            "The rate columns move with the sidebar filters; the transaction count does not.",
        ],
        validation="Counts reconciled against the raw registry year by year. Mean and median "
                   "recomputed in plain pandas and matched.",
        client_explanation="“Here is every year at a glance — how many sales, what the "
                           "average was, and what the typical transaction was.”",
    ),

    ChartInfo(
        key="height_price",
        title="Rate by floor band and property layout",
        section="Price",
        icon="🏢",
        subtitle="Median rate per m² across low-rise, mid-rise, high-rise and tower buildings.",
        what="Grouped bars: one band of floor band along the bottom, one colour per "
             "property layout, and the median rate per m² up the side.",
        why="To show whether the rate moves with the height of the building, and whether it "
            "moves the same way for a studio as for a three-bedroom.",
        columns=["floors", "building_name_en", "rooms_en", "meter_sale_price"],
        preparation="Bands are **derived from the data**: the quartiles of the height "
                    "distribution measured one row per building, so a single tower with "
                    "thousands of sales cannot move the boundaries. Combinations with fewer "
                    "than 100 transactions are omitted and named on screen rather than "
                    "dropped silently.",
        calculation="Rows are filtered to those with a floor count of at least 1, then placed in one of four FIXED floor bands: Low-rise 1–10, Mid-rise 11–25, High-rise 26–40, Tower 41 and above. Boundaries are inclusive at the top, so exactly 10 floors is Low-rise and exactly 11 is Mid-rise. Within each band × property layout: `median(meter_sale_price)`, `mean(meter_sale_price)` and `size()`. Cells below 100 transactions are omitted and named.",
        x_axis="Floor band.",
        y_axis="Median rate per m² (AED/m²).",
        legend="Property layout — Studio through 5 BHK and Penthouse, showing only the types "
               "that have enough transactions in the current selection.",
        how_to_read=[
            "Follow one colour left to right to see how that property layout prices across "
            "floor bands.",
            "Compare colours within a band to see how property layouts differ at the same "
            "kind of building.",
        ],
        tells_us=[
            "Whether taller buildings carry higher rates per m², and whether that holds "
            "across property layouts.",
        ],
        does_not_tell=[
            "**It is not the unit's own floor.** The dataset does not record which floor an "
            "apartment sits on, so this cannot answer whether a higher floor sells for more "
            "inside the same building.",
            "Height and location are entangled: tall towers cluster in particular areas, so "
            "part of any gap is where the building is, not how tall it is.",
        ],
        limitations=_COMMON_LIMITS + [
            "**The floor field is unusable.** `floor_bin` is the string `Unknown` on every "
            "populated row, and `floors` is identical for every sale in a given building — "
            "it is the building's height, not the unit's floor. This panel is labelled "
            "accordingly rather than presented as a floor-level analysis.",
            "Height is recorded for about 59% of transactions; the rest are not plotted, "
            "and the coverage is stated on screen.",
        ],
        validation="`floors` was tested against `property_id_bld` and found constant within "
                   "a building in 100% of cases, which is what establishes it as a building "
                   "attribute. Band boundaries, cell counts and medians were recomputed in "
                   "plain pandas and matched.",
        client_explanation="“Taller buildings carry higher rates per square metre, and it "
                           "holds for every size of apartment. What we cannot tell you from "
                           "this data is whether the fifteenth floor beats the fifth in the "
                           "same tower — that is not recorded.”",
    ),
]

CHARTS.extend(_V13)

# Charts removed in v1.3. Their entries go with them, so the registry can never
# document something the page no longer draws.
_REMOVED_V13 = {
    "yoy_growth",              # replaced by raw_yoy_volume (raw counts, 2026 rule)
    "offplan_vs_existing",     # replaced by the year-by-year summary table
    "offplan_ladder",          # off-plan explanation removed on request
    "amenities_headline",      # replaced by the controlled comparison
    "amenities_ladder",        # replaced by the controlled comparison
    "amenities_like_for_like", # replaced by the controlled comparison
    "dist_size",               # unit size distribution removed on request
    "dist_price_by_reg",       # sale price by registration type removed on request
    "forecast",                # published price forecast removed on request
}
CHARTS[:] = [c for c in CHARTS if c.key not in _REMOVED_V13]
CHART_BY_KEY = {c.key: c for c in CHARTS}

CHARTS.extend([
    ChartInfo(
        key="unit_size_summary",
        title="Unit size — key statistics",
        section="Distribution",
        icon="📐",
        subtitle="How big the units are, by property layout.",
        what="A table: for each property layout, how many transactions there were and how "
             "floor area is spread — the smallest, the quarter point, the median, the "
             "three-quarter point and the largest.",
        why="It answers the same question the old unit-size histogram did — how big are "
            "these homes — but gives readable numbers instead of a shape, and splits them "
            "by property layout so the answer is usable.",
        columns=["rooms_en", "procedure_area"],
        preparation="Rows are filtered by the sidebar selection. Only property layouts present "
                    "in the selection are listed.",
        calculation="Per property layout: `count(rows)`, `min`, 25th percentile, `median`, "
                    "75th percentile and `max` of `procedure_area`.",
        x_axis="Rows are property layouts.",
        y_axis="Columns are the size statistics, in m².",
        legend="Not applicable — this is a table.",
        how_to_read=[
            "The median column is the typical size for that property layout.",
            "The 25th and 75th percentile columns bracket the middle half — most units of "
            "that type sit between them.",
            "Smallest and largest are single transactions and are not typical.",
        ],
        tells_us=["The standard sizes Dubai builds and sells, per property layout."],
        does_not_tell=["Nothing about price — see the Price section for that."],
        limitations=_COMMON_LIMITS + [
            "Floor area is the registered procedure area, which may differ from a "
            "developer's marketed area.",
        ],
        validation="Every quantile recomputed in plain pandas and matched.",
        client_explanation="“A Dubai one-bedroom is typically this many square metres, and "
                           "most of them fall in this range.”",
    ),
    ChartInfo(
        key="price_by_reg_summary",
        title="Sale price by registration type — summary",
        section="Distribution",
        icon="🧾",
        subtitle="Each registration type described on its own terms.",
        what="A table with one row per registration type: how many transactions it accounts "
             "for, its share of the selection, and where its sale prices sit.",
        why="It keeps the information the old box plot carried — how prices are spread "
            "within each registration type — in a form that can be read directly, without "
            "a log axis to interpret.",
        columns=["reg_type_en", "actual_worth", "meter_sale_price"],
        preparation="Rows are filtered by the sidebar selection. `reg_type_en` is a clean "
                    "two-value field on the raw registry, so nothing is reclassified.",
        calculation="Per registration type: `count(rows)`, share of the selection, the 25th "
                    "percentile, `median` and 75th percentile of `actual_worth`, and "
                    "`median(meter_sale_price)`.",
        x_axis="Rows are registration types.",
        y_axis="Columns are transaction counts and price statistics.",
        legend="Not applicable — this is a table.",
        how_to_read=[
            "Read each row on its own: this is what that segment looked like.",
            "The 25th and 75th percentile columns bracket the middle half of that segment's "
            "sales.",
        ],
        tells_us=["How large each segment is, and the price level and spread inside it."],
        does_not_tell=[
            "**No comparison between the two rows is made here**, and no premium or "
            "discount is stated. The two segments are different products in different "
            "buildings, so a difference between the rows would not be a like-for-like "
            "comparison.",
        ],
        limitations=_COMMON_LIMITS,
        validation="Counts, shares and quantiles recomputed in plain pandas and matched.",
        client_explanation="“Here is how much of the market each segment is, and what "
                           "prices look like inside each one.”",
    ),
    ChartInfo(
        key="market_history",
        title="What the record shows",
        section="Price",
        icon="🧭",
        subtitle="Where rates have been, and where they are now.",
        what="Four figures — the latest median rate, the highest and lowest years on record, "
             "and the average change per year — with the full year-by-year record behind "
             "them.",
        why="The forecast section was removed. Rather than replace one projection with "
            "another, this states what actually happened: the recorded history of the rate, "
            "which is the evidence a reader can check.",
        columns=["year", "meter_sale_price", "actual_worth"],
        preparation="Rows are filtered by the sidebar selection and grouped by year.",
        calculation="`median(meter_sale_price)` per year. Average change per year is the "
                    "compound rate between the first and last year in the selection: "
                    "`((last ÷ first) ^ (1 ÷ years) − 1) × 100`.",
        x_axis="Rows are years.",
        y_axis="Median rate per m² and median price.",
        legend="Not applicable — KPI cards and a table.",
        how_to_read=[
            "The average change per year smooths a path that was not smooth — check the "
            "highest and lowest years beside it.",
            "The year-by-year table underneath is the actual path.",
        ],
        tells_us=["The recorded direction and pace of rate movement across the selection."],
        does_not_tell=[
            "**It is not a forecast.** Nothing here projects a future value, and past "
            "movement does not establish future movement.",
            "The latest year may be partial, in which case its median covers fewer months.",
        ],
        limitations=_COMMON_LIMITS + [
            "A compound average across a cycle hides the cycle. It is shown with the peak "
            "and trough years so it cannot stand alone.",
        ],
        validation="Yearly medians and the compound rate recomputed in plain pandas and "
                   "matched.",
        client_explanation="“Rates went from here to there over this many years, averaging "
                           "this much a year — with the best and worst years marked. That "
                           "is the record, not a prediction.”",
    ),
])
CHART_BY_KEY = {c.key: c for c in CHARTS}

CHARTS.extend([
    ChartInfo(
        key="amenity_transaction_share",
        title="Share of Recorded Transactions Associated with Each Amenity",
        section="Price",
        icon="🎛️",
        subtitle="How often each feature appears on the record here, against the Dubai figure.",
        what="One grouped bar chart, two bars per amenity. The coloured bar is the selected "
             "area and property layout; the grey bar is the same measurement across all of "
             "Dubai under the current filters. The gap between them is the point of the "
             "chart. Amenities are ordered by the size of that gap.",
        why="An earlier version ranked the five amenities by raw recorded share. Parking is "
            "recorded on between 88.9% and 100% of transactions in every property layout, so "
            "it came first every time, in every area, and read as though parking mattered "
            "most. That was a fact about which field the registry fills in, dressed up as a "
            "market finding. Comparing each amenity against its own Dubai-wide figure "
            "removes the illusion: a near-constant like parking sits level with its baseline "
            "and shows no gap, while a genuine difference stands out.",
        source=SOURCE_CLEAN,
        columns=["area_name_en", "rooms_en", "has_parking", "swimming_pool", "balcony",
                 "elevator", "metro"],
        preparation="Rows are filtered by the sidebar, then by the panel's Area and Property "
                    "type controls to form the selection. The baseline is the sidebar "
                    "selection before those two controls are applied — every area, every "
                    "property layout. A selection needs at least 100 transactions before any "
                    "share is reported. Nothing is imputed.",
        calculation="For each amenity, in both the selection and the baseline: "
                    "`(rows where the flag == 1) ÷ (rows) × 100`. The difference column is "
                    "the selection percentage minus the baseline percentage, in percentage "
                    "points. No model, no weighting, no adjustment.",
        x_axis="Amenity, ordered by the size of the difference from the Dubai figure.",
        y_axis="Share of recorded transactions (%).",
        legend="Two series, both named in the legend: the coloured bar is the selected area "
               "and property layout, the grey bar is all Dubai under the current filters. The "
               "amenity chosen in the third control is drawn in a deeper shade.",
        filters="All seven Dubai sidebar filters apply, plus the Area, Property layout and "
                "Amenity controls on the panel itself. All three redraw this one chart.",
        how_to_read=[
            "**Read the gap between the two bars, not the height of either one.** Height is "
            "how often a feature is written on the record, which is mostly a fact about "
            "record-keeping.",
            "A tall pair of bars that are level with each other — parking, usually — means "
            "this slice is unremarkable for that feature.",
            "A wide gap means the feature is recorded far more, or far less, often here "
            "than across the city. That is the finding.",
            "Change the area or the property layout to move the coloured bars; the grey "
            "baseline moves only with the sidebar filters.",
        ],
        tells_us=[
            "Which features are distinctive of a slice of the market, relative to Dubai.",
            "How completely each amenity field is populated, which is worth knowing before "
            "trusting any of these figures.",
        ],
        does_not_tell=[
            "**Nothing about price.** No amenity price effect is computed or displayed.",
            "**It is not a purchase probability.** Both datasets hold only completed "
            "transactions — there is no enquiry, viewing or non-purchase record anywhere in "
            "them — so nothing here can say how likely a buyer is to purchase.",
            "It does not say an amenity attracts buyers, adds value, or causes anything. It "
            "describes what the completed records contain.",
            "A tall bar does not mean an important feature. Parking is the standing example.",
        ],
        limitations=[
            "Covers registered residential **unit** (apartment) sales only.",
            "2026 is a partial year: the data ends **6 August 2026**.",
            "A `0` means *not recorded*, not *confirmed absent*, so under-recording appears "
            "as a lower share.",
            "Only the parking flag also exists in the raw registry; the other four are "
            "engineered fields in the cleaned dataset.",
            "Selections with fewer than 100 transactions are not reported at all, rather "
            "than reported on thin evidence.",
            "The baseline moves with the sidebar filters, so the comparison is against the "
            "Dubai you have currently selected, not against Dubai in the abstract.",
        ],
        validation="Shares recomputed in plain pandas for both the selection and the "
                   "baseline and matched; the difference column is verified to equal "
                   "selection minus baseline exactly. Both dataset schemas were swept for "
                   "purchase / lead / enquiry / outcome / conversion / target columns: none "
                   "exist, which is the evidence behind the statement that no probability "
                   "can be estimated. Parking's share was measured across all seven property "
                   "types (88.9%–100.0%), which is the evidence for abandoning the raw "
                   "ranking.",
        client_explanation="“Of the one-bedroom sales we have on record, this share had "
                           "parking noted on the record. It tells you how common the feature "
                           "is in completed deals — it is not a chance-of-buying figure.”",
    ),
    ChartInfo(
        key="volume_vs_price",
        title="Volume against price, by year",
        section="Price",
        icon="📈",
        subtitle="Transaction volume from the raw registry against the mean rate per m².",
        what="Bars are the number of transactions recorded each year; the line is the mean "
             "rate per m² for the same year on the secondary axis.",
        why="To answer whether busy years are also expensive years — whether activity and "
            "pricing move together across the cycle.",
        columns=["instance_date", "trans_group_en", "property_type_en", "property_usage_en",
                 "year", "meter_sale_price"],
        preparation="**Two sources, deliberately.** Volume is counted in the raw registry so "
                    "it is not reduced by cleaning. The rate is computed on the cleaned, "
                    "filtered dataset. Each is labelled in the legend and in the table.",
        calculation="Volume: `count(rows)` per year on the raw registry. Price: "
                    "**`mean(meter_sale_price)`** per year on the cleaned dataset.",
        x_axis="Year.",
        y_axis="Left: transaction volume (raw registry). Right: mean rate per m² (AED/m²).",
        legend="Three entries: transaction volume, the part-year bar for the year still in "
               "progress, and the mean rate line.",
        how_to_read=[
            "Bars rising together with the line means activity and pricing moved together.",
            "The amber bar is the year in progress; its volume covers part of a year only.",
        ],
        tells_us=[
            "Whether transaction activity and the average price per m² have moved together "
            "across the years in the selection.",
        ],
        does_not_tell=[
            "It does not establish that volume drives price or the reverse — they move "
            "together, which is not the same as one causing the other.",
            "The part-year bar is not comparable in height with the full years beside it.",
        ],
        limitations=_COMMON_LIMITS + [
            "**This chart uses the mean, not the median**, unlike the rest of the page. The "
            "mean is pulled upward by a small number of very large deals; both are shown in "
            "the table underneath so the difference stays visible.",
            "Volume comes from the raw registry and does not respond to the sidebar filters; "
            "the rate line does.",
        ],
        validation="Volume reconciled against the raw registry year by year; the mean rate "
                   "recomputed in plain pandas and matched. The mean sits above the median "
                   "in all 16 years, as expected for a right-skewed price distribution.",
        client_explanation="“Busy years have also been dear years. We use the average here "
                           "rather than the typical transaction because the question is "
                           "about the money moving through the market, and the average "
                           "counts the big deals the median leaves out.”",
    ),
])
CHART_BY_KEY = {c.key: c for c in CHARTS}
CHARTS[:] = [c for c in CHARTS if c.key != "amenity_by_property_type"]
CHART_BY_KEY = {c.key: c for c in CHARTS}


# ─────────────────────────────────────────────────────────────────────────────
# PLAIN ENGLISH
#
# Written for a reader with no data background. `one_liner` is what the chart is
# in one sentence; `steps` is what actually happens to the data, in words, with
# no formula; `terms` selects the glossary entries that chart needs.
#
# Kept apart from the technical entries above so the two can be reviewed — and
# rewritten — independently.
# ─────────────────────────────────────────────────────────────────────────────

_PLAIN: dict[str, dict] = {

    # ══════════════════════════════════════════════════════════════ INSIGHTS ══
    "concentration_pareto": dict(
        one_liner="A few Dubai areas take most of the money. This shows how few.",
        steps=[
            "Take every sale that passes your sidebar filters.",
            "Add up the money spent in each area.",
            "Line the areas up, biggest spender first.",
            "Draw the running total as a line, so you can see where it reaches 80%.",
        ],
        terms=["pareto chart", "cumulative share", "total value"],
    ),
    "tier_price": dict(
        one_liner="Do the buildings we label “premium” actually sell for premium prices?",
        steps=[
            "Take every sale in your selection that has a price-tier label.",
            "Group the sales by that label.",
            "For each label, find the middle price per square metre.",
            "Draw one bar per label so the labels can be compared.",
        ],
        terms=["median", "rate per m²"],
    ),
    "grade_price": dict(
        one_liner="Same check as the tier chart, using the A+ to D building grade.",
        steps=[
            "Take every sale that carries a building grade.",
            "Group them by grade.",
            "For each grade, find the middle price per square metre.",
            "Rank the grades so you can see whether A+ really beats D.",
        ],
        terms=["median", "rate per m²"],
    ),

    # ════════════════════════════════════════════════════════════════ TRENDS ══
    "monthly_activity": dict(
        one_liner="How busy the market was, month by month, and how much money moved.",
        steps=[
            "Take every sale in your selection and note which month it happened in.",
            "Count the sales in each month, and add up their prices.",
            "Draw the count as the shaded area and the money as bars.",
            "Add a three-month average line so the general direction is visible "
            "through the monthly wobble.",
        ],
        terms=["total value", "rolling median"],
    ),
    "annual_volume": dict(
        one_liner="How many homes changed hands each year.",
        steps=[
            "Take every sale in your selection.",
            "Count how many happened in each calendar year.",
            "Draw one bar per year.",
        ],
        terms=["partial year"],
    ),
    "quarterly_heatmap": dict(
        one_liner="A calendar grid: which three-month stretches are busy, and whether "
                  "that has changed over the years.",
        steps=[
            "Put every sale into the year and quarter it happened in.",
            "Count the sales in each year-and-quarter square.",
            "Shade each square — darker means busier.",
        ],
        terms=["partial year"],
    ),
    "yoy_growth": dict(
        one_liner="Did the market get busier or quieter than last year, and did prices "
                  "per square metre rise or fall?",
        steps=[
            "Count the sales in each year, and find each year's middle price per "
            "square metre.",
            "Take one year and the year immediately before it.",
            "Work out the change as a percentage of that previous year.",
            "Repeat down the whole series, so every year is compared with its own "
            "predecessor — never with a fixed starting year.",
        ],
        terms=["year-over-year", "median", "rate per m²", "partial year"],
    ),
    "seasonality": dict(
        one_liner="Which months of the year Dubai tends to buy in, with every year "
                  "stacked together.",
        steps=[
            "Ignore which year a sale happened in — keep only the month.",
            "Add up all the Januaries, all the Februaries, and so on.",
            "Draw one bar per calendar month, with the twelve-month average as a "
            "dotted line.",
        ],
        terms=[],
    ),

    # ═════════════════════════════════════════════════════════════ GEOGRAPHY ══
    "top_areas_volume": dict(
        one_liner="The fifteen areas where the most homes change hands.",
        steps=[
            "Take every sale in your selection.",
            "Count how many happened in each area.",
            "Show the fifteen busiest.",
        ],
        terms=[],
    ),
    "top_areas_rate": dict(
        one_liner="Dubai's most expensive addresses, measured per square metre so that "
                  "big homes do not automatically win.",
        steps=[
            "Group every sale by area.",
            "Throw out any area with fewer than 300 sales, so one unusual deal cannot "
            "put an area at the top.",
            "For each remaining area, find the middle price per square metre.",
            "Show the fifteen highest.",
        ],
        terms=["median", "rate per m²"],
    ),
    "area_treemap": dict(
        one_liner="One picture of where Dubai's money goes, and how pricey it is there.",
        steps=[
            "Add up the money spent in each area.",
            "Give each area a rectangle sized by that total.",
            "Colour the rectangle by the area's middle price per square metre.",
        ],
        terms=["treemap", "total value", "median", "rate per m²"],
    ),
    "area_bubble": dict(
        one_liner="A market map: busy areas to the right, expensive areas at the top.",
        steps=[
            "Take the thirty busiest areas.",
            "Plot each one by how many sales it had (across) and its middle sale price "
            "(up).",
            "Size the bubble by the total money spent there, and colour it by price "
            "per square metre.",
        ],
        terms=["median", "rate per m²", "total value"],
    ),
    "zone_comparison": dict(
        one_liner="What each broad kind of location costs — waterfront, central, "
                  "suburban and so on.",
        steps=[
            "Group every sale by the zone label the dataset carries.",
            "For each zone, find the middle price per square metre.",
            "Draw that as bars, with the number of sales as a line so you can see how "
            "much weight each zone carries.",
        ],
        terms=["locality zone", "median", "rate per m²"],
    ),
    "metro_effect": dict(
        one_liner="Which metro corridors the expensive stock sits on.",
        steps=[
            "Group every sale by the metro station recorded as its nearest.",
            "For each station, find the middle price per square metre.",
            "Rank the stations.",
        ],
        terms=["median", "rate per m²"],
    ),

    # ══════════════════════════════════════════════════════════════ PROPERTY ══
    "layout_mix": dict(
        one_liner="What people are actually buying — studios, one-beds, two-beds.",
        steps=[
            "Take every sale in your selection.",
            "Count how many were studios, how many one-bedroom, and so on.",
            "Draw one bar per layout.",
        ],
        terms=["layout"],
    ),
    "size_by_layout": dict(
        one_liner="How big a Dubai studio, one-bed or two-bed actually is.",
        steps=[
            "Group the sales by layout.",
            "For each layout, find the middle floor area.",
            "Draw one bar per layout.",
        ],
        terms=["median", "layout"],
    ),
    "rate_by_layout": dict(
        one_liner="How much a square metre costs in each size of apartment — and how "
                  "widely that varies inside each one.",
        steps=[
            "Group every sale by layout, and drop any layout with fewer than 100 sales "
            "(those are listed underneath rather than deleted).",
            "For each layout, work out the price per square metre at the quarter, "
            "half and three-quarter points of its sales.",
            "Draw a box from the quarter point to the three-quarter point, with a line "
            "at the middle — so the box holds the middle half of that layout's market.",
            "Give each layout its own panel, all on the same scale, so they can be "
            "compared side by side.",
        ],
        terms=["quartile", "whisker", "median", "rate per m²", "layout"],
    ),
    "reg_type_split": dict(
        one_liner="How much of the market is buying from a developer before completion, "
                  "versus buying a finished home.",
        steps=[
            "Take every sale and read its registration type.",
            "Count how many are off-plan and how many are existing.",
            "Show the two as shares of the whole.",
        ],
        terms=["off-plan", "existing property", "registration type"],
    ),
    "procedure_split": dict(
        one_liner="The legal form each sale took, as recorded by the Land Department.",
        steps=[
            "Take every sale and read its procedure name.",
            "Count how many fall under each procedure.",
            "Show them as shares.",
        ],
        terms=[],
    ),
    "size_vs_price": dict(
        one_liner="Every sale as one dot: bigger homes cost more, but how much more "
                  "depends heavily on where they are.",
        steps=[
            "Take a large random sample of the sales in your selection (drawing every "
            "one would freeze the browser).",
            "Plot each as a dot — floor area across, price up.",
            "Colour the dots by layout.",
        ],
        terms=["layout", "distribution"],
    ),

    # ═════════════════════════════════════════════════════════════════ PRICE ══
    "price_rate_trend": dict(
        one_liner="Are prices going up? Watch the teal line — that is price per square "
                  "metre, which does not move just because people bought bigger homes "
                  "this month.",
        steps=[
            "Put every sale into the month it happened in.",
            "For each month, find the middle sale price and the middle price per "
            "square metre.",
            "Draw those as two lines against two different scales.",
            "For the smoothed view, replace each month with the middle value of itself "
            "and its two neighbours — the real monthly figures stay available and are "
            "listed in the table underneath.",
        ],
        terms=["median", "rate per m²", "smoothing", "trend", "partial year"],
    ),
    "offplan_vs_existing": dict(
        one_liner="Off-plan property has sold for more per square metre than finished "
                  "property in every year of this dataset. This shows by how much.",
        steps=[
            "Split each year's sales into off-plan and existing.",
            "Find the middle price per square metre for each side.",
            "Skip any year with fewer than 100 sales on either side.",
            "Work out the gap as a percentage of the existing-property figure — "
            "positive means off-plan cost more.",
        ],
        terms=["off-plan", "existing property", "registration type", "median",
               "rate per m²"],
    ),
    "offplan_ladder": dict(
        one_liner="If a finished flat you can walk through should be worth more than a "
                  "drawing — and it should — this is the chart that explains the "
                  "headline. The premium belongs to the buildings, not to being unbuilt.",
        steps=[
            "Start with the straight comparison: every off-plan sale against every "
            "existing sale.",
            "Now compare only sales from the same year. Recalculate.",
            "Now only sales in the same area. Then the same master development. Then "
            "the same project. Then the same individual building.",
            "At each step, work out the difference inside every matched set separately, "
            "then average the sets — bigger sets count for more.",
            "A set needs at least 30 sales on each side to be used at all, so a handful "
            "of deals in one tower cannot decide the answer.",
        ],
        terms=["off-plan", "existing property", "registration type", "median",
               "rate per m²", "like-for-like", "composition effect"],
    ),
    "unit_size_summary": dict(
        one_liner="How big Dubai apartments actually are, one row per size of apartment.",
        steps=[
            "Take every sale in your selection that records a floor area.",
            "Group the sales by property layout.",
            "For each type, find the smallest, the typical, and the largest — plus the "
            "quarter and three-quarter points that bracket the middle half.",
        ],
        terms=["median", "quartile", "percentile", "layout"],
    ),
    "price_by_reg_summary": dict(
        one_liner="How big each segment is and what prices look like inside it — described, "
                  "not compared.",
        steps=[
            "Split the sales into off-plan and existing.",
            "Count each side and work out its share of the selection.",
            "For each side separately, find the quarter point, the middle and the "
            "three-quarter point of its sale prices.",
            "Report the two rows side by side without subtracting one from the other.",
        ],
        terms=["off-plan", "existing property", "registration type", "median", "quartile"],
    ),
    "market_history": dict(
        one_liner="Where the price per square metre has been and where it is now — the "
                  "record, not a prediction.",
        steps=[
            "Group every sale in your selection by year.",
            "Find the middle price per square metre in each year.",
            "Pick out the highest year, the lowest year and the most recent one.",
            "Work out the average yearly change between the first and last year.",
        ],
        terms=["median", "rate per m²", "partial year"],
    ),
    "amenity_transaction_share": dict(
        one_liner="How often each feature shows up on the paperwork here, next to how often "
                  "it shows up across Dubai — the difference between the two is the point.",
        steps=[
            "Take the sales that match the area and property layout you picked.",
            "For each feature, count how many of those sales have it written on the record, "
            "and turn that into a percentage.",
            "Do exactly the same sum for the whole of Dubai, so there is something to "
            "compare against.",
            "Draw the two side by side, one pair of bars per feature.",
            "Sort so the feature that differs most from the rest of Dubai comes first.",
        ],
        terms=["amenity flag", "layout", "area"],
    ),
    "volume_vs_price": dict(
        one_liner="Were the busy years also the expensive years?",
        steps=[
            "Count each year's transactions in the raw registry.",
            "Take the same year's sales from the cleaned dataset and work out the average "
            "price per square metre.",
            "Draw the counts as bars and the average as a line on its own scale.",
            "Mark the year still in progress separately, because its bar covers fewer months.",
        ],
        terms=["rate per m²", "median", "partial year"],
    ),
    "raw_yoy_volume": dict(
        one_liner="How many homes actually changed hands each year, counted from the "
                  "registry itself — and how that compares with the year before.",
        steps=[
            "Read the registration date of every transaction in the raw registry.",
            "Keep the same kind of sale the rest of this page covers — residential "
            "apartments — with no cleaning applied to the count.",
            "Count how many landed in each year.",
            "For each completed year, work out the change against the year immediately "
            "before it, as a percentage of that year.",
            "The year still in progress gets a bar but no percentage, unless it is already "
            "ahead of the same months of last year.",
        ],
        terms=["year-over-year", "partial year"],
    ),
    "yearly_summary": dict(
        one_liner="Every year on one row: how busy it was, what the average was, and what "
                  "the typical transaction was.",
        steps=[
            "Count each year's transactions in the raw registry.",
            "Take the same year's sales from the cleaned dataset and work out the average "
            "price per square metre.",
            "Work out the middle value too — the median.",
            "Put them side by side so the gap between average and typical is visible.",
        ],
        terms=["median", "rate per m²", "partial year"],
    ),
    "height_price": dict(
        one_liner="Do apartments in taller buildings cost more per square metre? One line "
                  "of bars per size of apartment, so you can see whether it holds for all "
                  "of them.",
        steps=[
            "Take every sale where the building's height is recorded.",
            "Work out the four floor bands from the data itself — the quartiles of how "
            "tall the buildings are, counting each building once.",
            "Put every sale into its band.",
            "Inside each band, find the middle price per square metre for each size of "
            "apartment.",
            "Leave out any combination with fewer than 100 sales, and say which ones were "
            "left out.",
        ],
        terms=["median", "rate per m²", "quartile", "layout"],
    ),
    "amenities_headline": dict(
        one_liner="The raw comparison — everything with a feature against everything "
                  "without it. It is shown for transparency, not for quoting.",
        steps=[
            "Split the sales into two piles: those recorded with the feature and those "
            "recorded without.",
            "Find the middle price per square metre in each pile.",
            "Express the difference as a percentage of the “without” pile.",
            "Do that for all five features.",
        ],
        terms=["amenity flag", "median", "rate per m²", "composition effect"],
    ),
    "amenities_ladder": dict(
        one_liner="Watch what happens to the big number as the comparison gets fairer. "
                  "Reading down, each bar compares properties that match on one more "
                  "thing — by the bottom bar you are comparing genuinely similar homes, "
                  "and the answer can shrink, or flip.",
        steps=[
            "Start with the raw comparison: every unit with the feature against every "
            "unit without it.",
            "Now only compare units in the same area as each other. Recalculate.",
            "Now also require the same layout. Then the same year. Then the same "
            "off-plan status.",
            "At each step, work out the difference inside every matched set separately, "
            "then average the sets — bigger sets count for more.",
            "A set needs at least 30 sales on each side to be used at all.",
        ],
        terms=["like-for-like", "composition effect", "amenity flag", "median",
               "rate per m²", "off-plan", "existing property"],
    ),
    "amenities_like_for_like": dict(
        one_liner="The honest version of the amenity question — and the numbers to use "
                  "in front of a client.",
        steps=[
            "Sort every sale into a matched set: same area, same layout, same year, "
            "same off-plan status.",
            "Keep only the sets that hold at least 30 sales both with and without the "
            "feature.",
            "Inside each set, compare the two middle prices per square metre.",
            "Average those set-by-set results, letting bigger sets count for more.",
        ],
        terms=["like-for-like", "amenity flag", "median", "rate per m²",
               "composition effect"],
    ),
    "price_bands": dict(
        one_liner="Where Dubai's money actually gets spent — and it is not at the top "
                  "end.",
        steps=[
            "Take seven fixed price brackets, from under 500K to 10M and above.",
            "Put every sale into exactly one bracket. Each bracket includes its lower "
            "limit and stops just short of the next, so nothing is counted twice and "
            "nothing is left out.",
            "Count the sales in each bracket and work out its share of the total.",
            "Draw the counts as bars, with the same numbers in the table beside them.",
        ],
        terms=["price band", "percentile"],
    ),
    "forecast": dict(
        one_liner="The forward view our modelling work already produced for this area, "
                  "shown with its own error record so you can judge how far to trust it.",
        steps=[
            "Read the forecast files the modelling pipeline saved earlier. Nothing is "
            "recalculated here.",
            "Draw the model's fit against what actually happened, so you can see how "
            "well it tracked history.",
            "Draw the forward quarters, with a shaded band for the range the model "
            "expects.",
            "Show the model's published error score next to it.",
        ],
        terms=["arima", "confidence band", "mape", "rate per m²"],
    ),

    # ══════════════════════════════════════════════════════════ DISTRIBUTION ══
    "dist_price": dict(
        one_liner="What a typical Dubai sale costs, and how unusual the very big ones "
                  "are.",
        steps=[
            "Take every sale price in your selection.",
            "Trim the most extreme half-percent at each end so the chart is readable.",
            "Slice the remaining range into 60 equal buckets.",
            "Count how many sales land in each bucket and draw that as a bar.",
        ],
        terms=["histogram", "distribution", "percentile", "median"],
    ),
    "dist_rate": dict(
        one_liner="Is Dubai one market or several? If there is more than one hump, "
                  "there is more than one market.",
        steps=[
            "Take the price per square metre of every sale.",
            "Trim the extremes at each end for readability.",
            "Slice the range into 60 equal buckets and count what lands in each.",
        ],
        terms=["histogram", "distribution", "rate per m²", "median"],
    ),
    "dist_size": dict(
        one_liner="The standard sizes Dubai builds and sells.",
        steps=[
            "Take the floor area of every sale.",
            "Trim the extremes at each end.",
            "Slice the range into 60 equal buckets and count what lands in each.",
        ],
        terms=["histogram", "distribution", "median"],
    ),
    "dist_price_by_reg": dict(
        one_liner="Off-plan and finished property are not just priced differently — "
                  "they are spread differently.",
        steps=[
            "Split the sales into off-plan and existing.",
            "For each side, find the quarter, half and three-quarter points of the "
            "price range.",
            "Draw a box covering the middle half, with a line at the middle.",
            "Use a multiplying scale on the price axis, because the values run from a "
            "few hundred thousand to hundreds of millions.",
        ],
        terms=["quartile", "whisker", "log scale", "off-plan", "existing property"],
    ),
    "rate_violin_year": dict(
        one_liner="The market has not only moved up — it has spread out. That matters "
                  "when you price one specific unit.",
        steps=[
            "Take a large random sample of the sales, so the chart stays responsive.",
            "Group them by year.",
            "For each year, draw a smoothed outline of where its prices per square "
            "metre sit — wider means more sales at that level.",
            "Put a small box plot inside each outline for the middle half.",
        ],
        terms=["violin", "distribution", "rate per m²", "quartile"],
    ),
}

# ═════════════════════════════════════════════════════════════════════════════
# v1.4 — top areas inside each price bracket, and the smoothing method review
# ═════════════════════════════════════════════════════════════════════════════

CHARTS.extend([
    ChartInfo(
        key="top_areas_by_band",
        title="Top 5 areas in each price bracket",
        section="Distribution",
        icon="🏙️",
        subtitle="Which areas are busiest at each price point.",
        what="For the selected sale-price bracket, the five areas with the most recorded "
             "transactions in that bracket, ranked, with the count behind each one.",
        why="The bracket chart above says how many sales happened at each price level. This "
            "says where they happened. An area that is busy overall does not necessarily "
            "appear here — it has to be busy at this particular price.",
        source=SOURCE_CLEAN,
        columns=["actual_worth", "area_name_en"],
        preparation="Rows are filtered by the sidebar selection, then to those with a valid "
                    "sale price (present and greater than zero). Each is assigned to exactly "
                    "one bracket. Transactions with a valid price but no recorded area count "
                    "toward the bracket total but cannot be ranked, and are reported "
                    "separately in the audit.",
        calculation="Within each bracket: `value_counts()` on the area column, take the top "
                    "five. Share of bracket = `area transactions ÷ transactions in that "
                    "bracket × 100`. Nothing is hard-coded — the names come out of the data.",
        x_axis="Transactions recorded in the selected bracket.",
        y_axis="Area, ranked, with rank 1 at the top.",
        legend="Single series — the axis titles carry the key. The rank is printed in the "
               "category label and the count at the end of each bar.",
        filters="All seven Dubai sidebar filters apply, plus the price-bracket selector on "
                "the panel itself. Note that the sale-price slider can empty a bracket "
                "entirely — that is the filter, not missing data.",
        how_to_read=[
            "Read each bar as “this many sales in this bracket were recorded in this area”.",
            "The share underneath tells you how concentrated the bracket is: five areas "
            "holding most of it means that price point is geographically narrow.",
            "Switch brackets to see the map of the market change — cheap and expensive "
            "stock are not in the same places.",
        ],
        tells_us=[
            "Where transactions at a given price level are concentrated.",
            "How concentrated or dispersed each price bracket is across Dubai.",
        ],
        does_not_tell=[
            "Nothing about whether an area is good value — a high count is activity, not "
            "quality or return.",
            "It does not rank areas by price. An area can top the count in two different "
            "brackets at once.",
            "It says nothing about supply — only about recorded transactions.",
        ],
        limitations=[
            "Covers registered residential **unit** (apartment) sales only.",
            "The sale-price slider defaults to the 1st–99th percentile, so the top and "
            "bottom brackets can look empty until it is widened.",
            "Areas are as recorded in the registry; a large area and a small one are ranked "
            "on the same footing, so population and stock size are not controlled for.",
            "Only the top five are drawn. The remaining areas in a bracket are summarised as "
            "a share, not listed.",
        ],
        validation="Bracket assignment is audited on every render: the count of transactions "
                   "with a valid sale price must equal the count classified into a bracket, "
                   "with zero unassigned. Boundaries are left-closed / right-open, so a sale "
                   "of exactly AED 1,000,000 falls in 1M – 2M and nowhere else. The audit is "
                   "shown in the panel rather than kept in the code.",
        client_explanation="“At this price point, these are the five busiest areas in Dubai, "
                           "and this is how many sales each of them recorded.”",
    ),
])
CHART_BY_KEY.update({c.key: c for c in CHARTS})

_PLAIN.update({
    "top_areas_by_band": {
        "one_liner": "At this price, these are the five busiest areas in Dubai — and how "
                     "many sales each of them recorded.",
        "steps": [
            "Take every sale in your current selection that has a real price on it.",
            "Sort each sale into one price bracket — and only one.",
            "Inside the bracket you picked, count how many sales happened in each area.",
            "Keep the five areas with the most, and rank them.",
            "Show how much of the whole bracket those five account for.",
        ],
        "terms": ["price bracket", "transaction count", "area"],
    }
})

for _c in CHARTS:
    _p = _PLAIN.get(_c.key, {})
    _c.one_liner = _p.get("one_liner", "") or _c.client_explanation
    _c.steps = _p.get("steps", [])
    _c.terms = _p.get("terms", [])

# ═════════════════════════════════════════════════════════════════════════════
# FORECAST — the live TruEstate Forecast API
#
# A fourth source label. The three above describe files in this repository;
# this one describes an answer fetched over the network at the moment it is
# asked for, which is a materially different kind of number and is labelled as
# such rather than folded into "DERIVED".
#
# Appended after the plain-English merge loop above, so its `steps` and `terms`
# are its own rather than being overwritten by an absent `_PLAIN` entry.
# ═════════════════════════════════════════════════════════════════════════════

SOURCE_API = (
    "FORECAST API",
    "GET http://51.38.112.237:9500/forecast",
    "The TruEstate Forecast API. Returns up to 6 months of LOWESS-smoothed history "
    "for one property profile, a single current valuation point, and 5–6 months of "
    "projection — optionally with a second, news-adjusted trajectory and a written "
    "market narrative. Nothing is stored; each answer is fetched when it is asked for.",
)

_SOURCE_STYLE["FORECAST API"] = ("#B8731B", "rgba(184,115,27,0.10)")

GLOSSARY.update({
    "valuation point":
        "The single current-month price the model puts on the property profile you "
        "described. Both forecast lines start from it, which is why it is called the "
        "anchor.",
    "macro forecast":
        "The projection that follows the broad market trend, with each month's growth "
        "capped so one step cannot swing the line wildly.",
    "news-adjusted forecast":
        "A second projection from the same starting point that also takes recent "
        "real-world news about the area into account. It is uncapped, so it can move "
        "further than the macro line — the gap between the two is the point of showing "
        "both.",
    "forecast horizon":
        "How many months ahead the projection reaches. It is however many months the "
        "service returns — here, five or six.",
    "narrative":
        "A short written explanation, produced by the forecasting service, of the market "
        "events behind the two lines separating.",
})

CHARTS.append(ChartInfo(
    key="api_forecast",
    title="Area price trend — forecast",
    section="Forecast",
    icon="🔮",
    subtitle="History, the current valuation point, and the months ahead, for one "
             "property profile.",
    one_liner="You describe a property — area, rooms, floor, size — and this shows what it "
              "has been worth per square metre, what it is worth now, and where two "
              "different projections put it over the next few months.",
    what="One chart carrying four things: the area's recorded market history from the "
         "cleaned dataset, the forecasting service's own smoothed history for the profile "
         "you described, the current valuation point, and two forward projections — one "
         "following the broad market, one also weighing recent news.",
    why="Every other chart in this dashboard looks backwards. This is the one place the "
        "platform says anything about the months ahead, and it does so for a specific "
        "property rather than for the area as a whole.",
    source=SOURCE_API,
    columns=["area_name", "procedure_area", "rooms_en", "reg_type_en", "floor_bin",
             "Grade", "project_grade", "Developer_grade", "has_parking", "swimming_pool",
             "balcony", "elevators", "metro", "news_available"],
    preparation="The area comes from the global 📍 Area — this section reads it and shows "
                "it read-only, and has no area control of its own. The remaining inputs "
                "are restricted to the values `data/dubai/input_ranges.csv` records for "
                "that area, so a combination the model has never seen cannot be sent. "
                "Anything left as “Any” is omitted from the request, which is what makes "
                "the service fall back to that area's own typical value.",
    calculation="The request is a single GET. The response is drawn as received: history "
                "arrives already smoothed by the service (LOWESS, frac = 0.10) and is not "
                "smoothed again here; both forecast lines are plotted from the valuation "
                "point because the service propagates both from that same baseline. No "
                "second model, average or extrapolation is applied on this side.",
    x_axis="Month. The vertical marker sits on the valuation point's own timestamp, read "
           "from the response.",
    y_axis="Price per square metre, in AED.",
    legend="Recorded market history (cleaned dataset) · Model history (service, smoothed) · "
           "Valuation point · Macro forecast (dashed) · News-adjusted forecast · the shaded "
           "region between the two forecasts.",
    filters="The global 📍 Area applies. The Dubai sidebar filters do not — the forecast "
            "describes the property profile set in this section, and the service is asked "
            "about that profile directly.",
    steps=[
        "You pick an area under 📍 Area. This section reads that choice.",
        "The valid options for that area are loaded from `input_ranges.csv`, so only "
        "values the model has actually seen are offered.",
        "You describe the property — rooms, floor, size, grades, amenities. Anything left "
        "as “Any” is simply not sent.",
        "One request goes to the forecasting service carrying exactly those values.",
        "The reply comes back with history, a valuation point and the months ahead, and is "
        "drawn exactly as received.",
    ],
    how_to_read=[
        "Start at the vertical marker — that is now, according to the service.",
        "The dashed green line is the broad-market path; the solid coral line is the same "
        "path with recent news weighed in.",
        "The shaded region between them is how far apart the two views are. Wide means the "
        "news is pulling hard against the trend.",
        "The soft grey line behind everything is the whole area's recorded median, for "
        "context. It is a different measurement from the profile line and will usually sit "
        "at a different level.",
    ],
    tells_us=[
        "What the model values this specific property profile at today, per square metre.",
        "The direction and size of the movement it expects over the months it covers.",
        "How much recent news changes that picture, and in which direction.",
    ],
    does_not_tell=[
        "It is a price per square metre for one profile — a whole-unit valuation and an "
        "area-wide average are both different figures.",
        "The two lines are the service's projections, which is a different thing from an "
        "offer or a lending valuation.",
    ],
    limitations=[
        "The projection runs as far as the service's response reaches — five or six months "
        "— and the chart stops there. No month is repeated or extended to fill a longer "
        "window.",
        "The response carries no uncertainty figure, so no confidence interval is drawn. "
        "The shaded region is the distance between the two returned lines.",
        "The historical-window control changes how much recorded history is shown behind "
        "the forecast; the forecast itself is as long as the response.",
        "`input_ranges.csv` publishes ranges for 35 areas. For any other area the full "
        "published range is offered and the service applies its own handling — including "
        "saying plainly when it does not cover that area.",
    ],
    validation="Every value plotted traces to a field in the response: `before_prediction`, "
               "`prediction_point`, `forecast` and `news_adjusted_forecast`. The exact "
               "request URL is shown beneath the chart, so any figure can be checked "
               "against the service directly. The forecast is stored with the area and "
               "inputs that produced it and is withheld the moment either changes, so a "
               "result from one area can never appear under another.",
    client_explanation="Describe a property and this tells you what it is worth per square "
                       "metre now and where it is heading over the next few months — with "
                       "and without recent news factored in.",
    terms=["valuation point", "macro forecast", "news-adjusted forecast",
           "forecast horizon", "narrative", "smoothing", "rate per m²", "median"],
))

CHART_BY_KEY.update({c.key: c for c in CHARTS})

# A chart without plain-English content is a bug, not a style preference.
_MISSING_PLAIN = [c.key for c in CHARTS if not c.steps]
if _MISSING_PLAIN:  # pragma: no cover - guarded by tests/verify_dubai_changes.py
    raise RuntimeError(f"chart_info: no plain-English steps for {_MISSING_PLAIN}")

SECTIONS = ["Insights", "Trends", "Geography", "Property", "Price", "Distribution",
            "Forecast"]


def info(key: str) -> ChartInfo:
    return CHART_BY_KEY[key]


def header(key: str) -> None:
    """Shorthand: render the documented header for a chart by key."""
    render_chart_header(CHART_BY_KEY[key])
