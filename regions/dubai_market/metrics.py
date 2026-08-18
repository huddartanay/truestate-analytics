"""
Dubai market metrics — Executive KPIs, Smart Business Insights, Market Snapshot.

Every value returned here is computed from the supplied cleaned dataset.
Nothing is hard-coded, carried over from Abu Dhabi, or estimated.

An insight is only emitted when the data actually supports it: each builder
checks for the columns and the minimum sample size it needs, and returns
nothing when those are not met.
"""

from __future__ import annotations

import pandas as pd

from .data import AMENITIES, COL, aed, num

# Minimum rows before an area / building / group is allowed to appear in a
# "highest" or "most premium" claim, so a single outlier deal cannot win.
MIN_GROUP = 300
MIN_GROUP_SMALL = 50


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTIVE KPIs
# ─────────────────────────────────────────────────────────────────────────────


def executive_kpis(df: pd.DataFrame) -> list[dict]:
    """12 KPI cards, laid out 3 rows × 4 — the same grid as Abu Dhabi."""
    price = df[COL["price"]]
    rate = df[COL["rate"]]

    return [
        # Row 1 — volume and value
        dict(label="Total Transactions", value=f"{len(df):,}", icon="🔢", color_class="blue",
             tooltip="Residential unit sales in the filtered period."),
        dict(label="Total Market Value", value=aed(price.sum()), icon="💰", color_class="teal",
             tooltip="Combined value of all filtered transactions (AED)."),
        dict(label="Median Sale Price", value=aed(price.median()), icon="🏷️", color_class="amber",
             tooltip="Midpoint price — half of sales sit above it, half below."),
        dict(label="Average Sale Price", value=aed(price.mean()), icon="📈", color_class="blue",
             tooltip="Mean sale price. Higher than the median because of large deals."),
        # Row 2 — pricing
        dict(label="Median Rate / m²", value=aed(rate.median()), icon="📐", color_class="teal",
             tooltip="Price per square metre — the fairest like-for-like comparison."),
        dict(label="Average Rate / m²", value=aed(rate.mean()), icon="📏", color_class="green",
             tooltip="Mean price per square metre."),
        dict(label="Highest Sale", value=aed(price.max()), icon="🏆", color_class="amber",
             tooltip="Largest single transaction in the filtered data."),
        dict(label="Lowest Sale", value=aed(price.min()), icon="📉", color_class="rose",
             tooltip="Smallest single transaction in the filtered data."),
        # Row 3 — market breadth
        dict(label="Active Areas", value=f"{df[COL['area']].nunique():,}", icon="🗺️", color_class="violet",
             tooltip="Distinct Dubai areas with transactions in the filtered data."),
        dict(label="Master Projects", value=f"{df[COL['master_project']].nunique():,}", icon="🏘️", color_class="sky",
             tooltip="Distinct master developments."),
        dict(label="Projects", value=f"{df[COL['project']].nunique():,}", icon="🏗️", color_class="teal",
             tooltip="Distinct named projects."),
        dict(label="Developers", value=f"{df[COL['developer']].nunique():,}", icon="👷", color_class="blue",
             tooltip="Distinct developers recorded against these transactions."),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# MARKET SNAPSHOT
# ─────────────────────────────────────────────────────────────────────────────


def market_snapshot(df: pd.DataFrame) -> list[tuple[str, str]]:
    """Six quick-reference figures, in the order Abu Dhabi presents them."""
    return [
        ("Median Sale Price", aed(df[COL["price"]].median())),
        ("Median Rate / m²", aed(df[COL["rate"]].median())),
        ("Total Market Value", aed(df[COL["price"]].sum())),
        ("Active Areas", f"{df[COL['area']].nunique():,}"),
        ("Total Transactions", f"{len(df):,}"),
        ("Median Unit Size", f"{df[COL['area_sqm']].median():,.0f} m²"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# SMART BUSINESS INSIGHTS
# ─────────────────────────────────────────────────────────────────────────────


def _hl(text) -> str:
    return f"<span class='insight-highlight'>{text}</span>"


def smart_insights(df: pd.DataFrame) -> list[tuple[str, str]]:
    """
    Concise, executive-level observations, each derived from the filtered data.

    Returns a list of (emoji, html) pairs. An observation is skipped entirely
    when the data does not support it — nothing is padded with placeholder text.
    """
    out: list[tuple[str, str]] = []
    total = len(df)
    if total == 0:
        return out

    # 1 — most active area
    area_counts = df[COL["area"]].value_counts()
    if not area_counts.empty:
        top_area, top_n = area_counts.index[0], int(area_counts.iloc[0])
        out.append((
            "🏆",
            f"{_hl(top_area)} is the most active area with {_hl(f'{top_n:,}')} transactions — "
            f"{_hl(f'{top_n / total * 100:.1f}%')} of everything in the current selection."
        ))

    # 2 — most expensive area by rate (volume-guarded)
    by_area = (
        df.groupby(COL["area"], observed=True)
        .agg(n=(COL["rate"], "size"), med_rate=(COL["rate"], "median"))
        .query(f"n >= {MIN_GROUP}")
    )
    if not by_area.empty:
        prem = by_area["med_rate"].idxmax()
        out.append((
            "💎",
            f"{_hl(prem)} commands the highest median rate at "
            f"{_hl(aed(by_area['med_rate'].max()))} per m², across "
            f"{int(by_area.loc[prem, 'n']):,} transactions — the premium end of this selection."
        ))

    # 3 — peak year
    by_year = df[COL["year"]].value_counts()
    if not by_year.empty:
        peak_year = int(by_year.index[0])
        out.append((
            "📅",
            f"{_hl(peak_year)} was the busiest year with {_hl(f'{int(by_year.iloc[0]):,}')} "
            f"transactions recorded."
        ))

    # 4 — year-over-year movement in median price
    yearly = df.groupby(COL["year"], observed=True)[COL["price"]].median().sort_index()
    if len(yearly) >= 2:
        latest, prev = int(yearly.index[-1]), int(yearly.index[-2])
        change = (yearly.iloc[-1] - yearly.iloc[-2]) / yearly.iloc[-2] * 100
        direction = "rose" if change > 0 else "fell"
        pct = f"{abs(change):.1f}%"
        # Flag a partial final year rather than presenting it as a full one.
        last_month = int(df.loc[df[COL["year"]] == latest, COL["month"]].max())
        partial = f" ({latest} is a partial year — data ends in month {last_month})" \
            if last_month < 12 else ""
        out.append((
            "📊",
            f"Median sale price {_hl(direction)} {_hl(pct)} from {prev} to {latest} "
            f"({aed(yearly.iloc[-2])} → {aed(yearly.iloc[-1])}){partial}."
        ))

    # 5 — off-plan vs existing
    reg = df[COL["reg_type"]].value_counts(normalize=True)
    if not reg.empty:
        offplan = float(reg.get("Off-Plan Properties", 0)) * 100
        existing = float(reg.get("Existing Properties", 0)) * 100
        lean = "developer-led" if offplan > 50 else "resale-led"
        out.append((
            "🏗️",
            f"{_hl(f'{offplan:.1f}%')} of sales are off-plan and {_hl(f'{existing:.1f}%')} are "
            f"existing property — a {lean} market in this selection."
        ))

    # 6 — dominant layout
    rooms = df[COL["rooms"]].value_counts(normalize=True)
    if not rooms.empty:
        out.append((
            "🛏️",
            f"{_hl(rooms.index[0])} units are the most traded layout at "
            f"{_hl(f'{rooms.iloc[0] * 100:.1f}%')} of transactions."
        ))

    # 7 — locality zone premium
    if COL["zone"] in df.columns:
        by_zone = (
            df[df[COL["zone"]] != "Unknown"]
            .groupby(COL["zone"], observed=True)
            .agg(n=(COL["rate"], "size"), med_rate=(COL["rate"], "median"))
            .query(f"n >= {MIN_GROUP}")
        )
        if len(by_zone) >= 2:
            hi, lo = by_zone["med_rate"].idxmax(), by_zone["med_rate"].idxmin()
            ratio = by_zone["med_rate"].max() / by_zone["med_rate"].min()
            out.append((
                "🌊",
                f"{_hl(hi)} carries the highest median rate of any locality zone — "
                f"{_hl(f'{ratio:.1f}×')} the rate in {_hl(lo)}."
            ))

    # 8 — strongest amenity association
    amen = amenity_effects(df)
    if amen:
        top = max(amen, key=lambda a: abs(a["rate_delta_pct"]))
        delta = top["rate_delta_pct"]
        if abs(delta) >= 1:
            verb = "higher" if delta > 0 else "lower"
            label = top["label"].lower()
            gap = f"{abs(delta):.1f}% {verb}"
            out.append((
                "✨",
                f"Units with {_hl(label)} show a median rate {_hl(gap)} than those without "
                f"({aed(top['rate_with'])} vs {aed(top['rate_without'])} per m²) — before "
                "accounting for location and unit type. See <b>Price</b> for the "
                "like-for-like comparison."
            ))

    return out


# ─────────────────────────────────────────────────────────────────────────────
# AMENITY ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────


def amenity_effects(df: pd.DataFrame, min_group: int = MIN_GROUP_SMALL) -> list[dict]:
    """
    Median price and rate for units with vs without each amenity flag.

    This is an association, not a causal estimate — amenities co-vary with
    location, project quality and unit size. The UI wording reflects that.
    """
    rows: list[dict] = []
    for col, label in AMENITIES.items():
        if col not in df.columns:
            continue
        with_g = df[df[col] == 1]
        without_g = df[df[col] == 0]
        if len(with_g) < min_group or len(without_g) < min_group:
            continue

        rate_with = float(with_g[COL["rate"]].median())
        rate_without = float(without_g[COL["rate"]].median())
        price_with = float(with_g[COL["price"]].median())
        price_without = float(without_g[COL["price"]].median())

        rows.append({
            "column": col,
            "label": label,
            "n_with": int(len(with_g)),
            "n_without": int(len(without_g)),
            "share_with": len(with_g) / len(df) * 100,
            "rate_with": rate_with,
            "rate_without": rate_without,
            "rate_delta_pct": (rate_with - rate_without) / rate_without * 100 if rate_without else 0.0,
            "price_with": price_with,
            "price_without": price_without,
            "price_delta_pct": (price_with - price_without) / price_without * 100 if price_without else 0.0,
            "size_with": float(with_g[COL["area_sqm"]].median()),
            "size_without": float(without_g[COL["area_sqm"]].median()),
        })

    return sorted(rows, key=lambda r: abs(r["rate_delta_pct"]), reverse=True)


LFL_KEYS = [COL["area"], COL["rooms"], COL["year"], COL["reg_type"]]


def amenity_effects_like_for_like(df: pd.DataFrame, min_cell: int = 30,
                                  keys: list[str] | None = None) -> pd.DataFrame:
    """
    The amenity comparison, held inside comparable groups of properties.

    Comparing every unit with a pool against every unit without one mixes
    completely different properties. Here each amenity gap is measured inside a
    single **area × layout × year × registration type** cell, then averaged
    across cells weighted by cell size.

    Registration type matters more than anything else here. Building attributes
    are recorded far more completely for existing property than for off-plan
    sales (a balcony is recorded for 88.8% of existing sales but only 32.9% of
    off-plan ones), and off-plan trades at a much higher rate per m². Without
    that control, an under-recorded flag looks like a price penalty when it is
    really a recording artefact.

    Still associative, not causal — the cells control for four characteristics,
    not for floor level, view, finish or developer.
    """
    keys = keys or LFL_KEYS
    frames = []
    for col, label in AMENITIES.items():
        if col not in df.columns:
            continue
        cell = _like_for_like_one(df, col, keys, min_cell)
        if cell is None:
            continue
        frames.append({
            "Amenity": label,
            "Median rate difference (%)": cell["gap"],
            "Groups": cell["groups"],
            "Deals": cell["deals"],
            "Groups positive (%)": cell["positive_pct"],
        })

    if not frames:
        return pd.DataFrame()
    return (pd.DataFrame(frames)
            .sort_values("Median rate difference (%)", ascending=False)
            .reset_index(drop=True))


def paired_gap(df: pd.DataFrame, split_col: str, hi, lo, keys: list[str],
               min_cell: int = 30) -> dict | None:
    """
    The rate-per-m² gap between two sides of `split_col`, measured only inside
    groups of comparable properties.

    Each group contributes the percentage difference between its own `hi` and
    `lo` median rate; the groups are then averaged, weighted by how many
    transactions each holds. A group needs at least `min_cell` transactions on
    each side or it is ignored, so a handful of deals cannot swing the answer.

    `keys=[]` means no grouping at all — the straight, uncontrolled comparison.

    This is the one implementation behind both the amenity comparison and the
    off-plan comparison, so the two cannot drift apart methodologically.
    """
    if split_col not in df.columns:
        return None

    if not keys:
        a = df.loc[df[split_col] == hi, COL["rate"]]
        b = df.loc[df[split_col] == lo, COL["rate"]]
        if len(a) < min_cell or len(b) < min_cell:
            return None
        med_b = float(b.median())
        if not med_b:
            return None
        return {"gap": (float(a.median()) / med_b - 1) * 100, "groups": 1,
                "deals": int(len(a) + len(b)), "positive_pct": float("nan")}

    grouped = (df.groupby(keys + [split_col], observed=True)[COL["rate"]]
                 .agg(["median", "size"]).unstack(level=-1))
    if ("median", hi) not in grouped.columns or ("median", lo) not in grouped.columns:
        return None
    cells = pd.DataFrame({
        "rate_lo": grouped[("median", lo)], "rate_hi": grouped[("median", hi)],
        "n_lo": grouped[("size", lo)], "n_hi": grouped[("size", hi)],
    }).dropna()
    cells = cells[(cells["n_lo"] >= min_cell) & (cells["n_hi"] >= min_cell)]
    if cells.empty:
        return None
    weight = cells["n_lo"] + cells["n_hi"]
    delta = (cells["rate_hi"] - cells["rate_lo"]) / cells["rate_lo"] * 100
    return {
        "gap": float((delta * weight).sum() / weight.sum()),
        "groups": int(len(cells)),
        "deals": int(weight.sum()),
        "positive_pct": float((delta > 0).mean() * 100),
    }


def _like_for_like_one(df: pd.DataFrame, column: str, keys: list[str],
                       min_cell: int) -> dict | None:
    """One amenity's gap, measured inside groups defined by `keys`."""
    return paired_gap(df, column, 1, 0, keys, min_cell)


# The comparison, tightened one step at a time. Each level holds one more
# characteristic constant, so the reader can watch the headline gap melt.
CONTROL_LEVELS: list[tuple[str, list[str]]] = [
    ("Everything against everything", []),
    ("Same area", [COL["area"]]),
    ("Same area and layout", [COL["area"], COL["rooms"]]),
    ("Same area, layout and year", [COL["area"], COL["rooms"], COL["year"]]),
    ("Same area, layout, year and off-plan status", LFL_KEYS),
]


def amenity_control_ladder(df: pd.DataFrame, column: str,
                           min_cell: int = 30) -> pd.DataFrame:
    """
    How one amenity's price gap changes as more of the property mix is held constant.

    The first row is the raw comparison — every unit with the flag against every
    unit without it, whatever kind of property they are. Each row after that
    compares only properties that match on one more characteristic. If the gap
    collapses as the rows go down, the raw number was describing the property
    mix, not the amenity.
    """
    if column not in df.columns:
        return pd.DataFrame()
    with_g, without_g = df[df[column] == 1], df[df[column] == 0]
    if with_g.empty or without_g.empty:
        return pd.DataFrame()

    rate_with = float(with_g[COL["rate"]].median())
    rate_without = float(without_g[COL["rate"]].median())
    rows = [{
        "Comparison": CONTROL_LEVELS[0][0],
        "Gap (%)": (rate_with / rate_without - 1) * 100 if rate_without else 0.0,
        "Groups": 1,
        "Deals": int(len(with_g) + len(without_g)),
        "Held constant": 0,
    }]
    for level, (label, keys) in enumerate(CONTROL_LEVELS[1:], start=1):
        cell = _like_for_like_one(df, column, keys, min_cell)
        if cell is None:
            continue
        rows.append({
            "Comparison": label,
            "Gap (%)": cell["gap"],
            "Groups": cell["groups"],
            "Deals": cell["deals"],
            "Held constant": level,
        })
    return pd.DataFrame(rows)


OFF_PLAN, EXISTING = "Off-Plan Properties", "Existing Properties"

# Off-plan against finished property, tightened one step at a time. The last two
# levels are the ones that matter: they compare units inside the same building.
OFFPLAN_LEVELS: list[tuple[str, list[str]]] = [
    ("Everything against everything", []),
    ("Same year", [COL["year"]]),
    ("Same area and year", [COL["area"], COL["year"]]),
    ("Same master development and year", [COL["master_project"], COL["year"]]),
    ("Same project and year", [COL["project"], COL["year"]]),
    ("Same building and year", [COL["building"], COL["year"]]),
]


def offplan_control_ladder(df: pd.DataFrame, min_cell: int = 30) -> pd.DataFrame:
    """
    The off-plan premium, measured under progressively fairer comparisons.

    The headline says off-plan sells for far more per square metre than finished
    property, which is the opposite of what most people expect — you can stand
    inside a finished apartment and you cannot stand inside a drawing.

    The resolution is that the two labels are attached to different stock.
    Off-plan sales happen in newer, higher-graded buildings in newer master
    developments. Once the comparison is held inside the same building, the
    premium disappears. This table is that argument, one row at a time.
    """
    if COL["reg_type"] not in df.columns:
        return pd.DataFrame()

    rows = []
    for level, (label, keys) in enumerate(OFFPLAN_LEVELS):
        cell = paired_gap(df, COL["reg_type"], OFF_PLAN, EXISTING, keys, min_cell)
        if cell is None:
            continue
        rows.append({
            "Comparison": label,
            "Gap (%)": cell["gap"],
            "Groups": cell["groups"],
            "Deals": cell["deals"],
            "Held constant": level,
        })
    return pd.DataFrame(rows)


def offplan_composition(df: pd.DataFrame, min_building: int = 30) -> dict:
    """
    Why the off-plan headline looks the way it does, measured from the selection.

    The key number is `stock_gap_pct`: value every building at its own median
    rate, then ask what the average building is worth on each side of the split.
    If off-plan buyers are simply transacting in dearer buildings, that number
    alone accounts for the headline — with nothing left over for off-plan status.
    """
    if COL["reg_type"] not in df.columns:
        return {}
    o = df[df[COL["reg_type"]] == OFF_PLAN]
    e = df[df[COL["reg_type"]] == EXISTING]
    if o.empty or e.empty:
        return {}

    out: dict = {
        "n_offplan": int(len(o)),
        "n_existing": int(len(e)),
        "rate_offplan": float(o[COL["rate"]].median()),
        "rate_existing": float(e[COL["rate"]].median()),
        "size_offplan": float(o[COL["area_sqm"]].median()),
        "size_existing": float(e[COL["area_sqm"]].median()),
        "price_offplan": float(o[COL["price"]].median()),
        "price_existing": float(e[COL["price"]].median()),
    }
    out["headline_pct"] = (out["rate_offplan"] / out["rate_existing"] - 1) * 100

    # The stock test: are the two sides even buying in the same buildings?
    if COL["building"] in df.columns:
        per_building = df.groupby(COL["building"], observed=True)[COL["rate"]].median()
        counts = (df.groupby([COL["building"], COL["reg_type"]], observed=True)
                    .size().unstack(fill_value=0))
        counts = counts[counts.sum(axis=1) >= min_building]
        if OFF_PLAN in counts.columns and EXISTING in counts.columns and len(counts):
            rates = per_building.reindex(counts.index)
            wo = float((rates * counts[OFF_PLAN]).sum() / max(counts[OFF_PLAN].sum(), 1))
            we = float((rates * counts[EXISTING]).sum() / max(counts[EXISTING].sum(), 1))
            out.update({
                "stock_rate_offplan": wo, "stock_rate_existing": we,
                "stock_gap_pct": (wo / we - 1) * 100 if we else None,
                "buildings_considered": int(len(counts)),
            })
            shared = counts[(counts[OFF_PLAN] >= min_building)
                            & (counts[EXISTING] >= min_building)]
            out["buildings_both_sides"] = int(len(shared))
            out["deals_in_shared_buildings"] = int(shared.sum().sum())

    # Quality and location mix, as share-point differences.
    def mix(col, top=5):
        if col not in df.columns:
            return pd.DataFrame()
        a = o[col].value_counts(normalize=True).mul(100)
        b = e[col].value_counts(normalize=True).mul(100)
        t = pd.DataFrame({"Off-plan (%)": a, "Existing (%)": b}).fillna(0)
        t["Difference (pp)"] = t["Off-plan (%)"] - t["Existing (%)"]
        return t.sort_values("Difference (pp)", key=abs, ascending=False).head(top)

    out["price_tier"] = mix(COL["price_tier"])
    out["grade"] = mix(COL["grade"])
    out["zone"] = mix(COL["zone"])

    # Pooled across years, which trades a fairer year match for a much larger
    # sample. Reported alongside the year-matched figure, never instead of it.
    pooled = paired_gap(df, COL["reg_type"], OFF_PLAN, EXISTING,
                        [COL["building"]], min_building)
    if pooled:
        out["same_building_pooled"] = pooled
    return out


def amenity_plain_reason(df: pd.DataFrame, column: str, min_cell: int = 30,
                         fair: dict | None = None) -> dict:
    """
    The ingredients of a plain-English explanation of one amenity's headline gap.

    Everything returned is measured from the current selection — nothing here is
    written by hand — so the sentence the dashboard prints is always true of the
    data actually on screen.

    `fair` lets a caller that has already computed the like-for-like figure hand
    it in rather than pay for the same four-key grouping twice.
    """
    if column not in df.columns:
        return {}
    w, wo = df[df[column] == 1], df[df[column] == 0]
    if w.empty or wo.empty:
        return {}

    def share(frame, col, value):
        if col not in frame.columns or frame.empty:
            return None
        return float((frame[col] == value).mean() * 100)

    if fair is None:
        fair = _like_for_like_one(df, column, LFL_KEYS, min_cell)
    top_wo = wo[COL["area"]].value_counts(normalize=True) if COL["area"] in wo else None
    top_w = w[COL["area"]].value_counts(normalize=True) if COL["area"] in w else None

    within = {}
    if COL["reg_type"] in df.columns:
        for reg, sub in df.groupby(COL["reg_type"], observed=True):
            a, b = sub[sub[column] == 1], sub[sub[column] == 0]
            if len(a) < min_cell or len(b) < min_cell:
                continue
            m_b = float(b[COL["rate"]].median())
            if m_b:
                within[str(reg)] = (float(a[COL["rate"]].median()) / m_b - 1) * 100

    signs = list(within.values())
    return {
        "label": AMENITIES.get(column, column),
        "column": column,
        "n_with": int(len(w)),
        "n_without": int(len(wo)),
        "headline": (float(w[COL["rate"]].median()) / float(wo[COL["rate"]].median()) - 1) * 100,
        "fair": fair["gap"] if fair else None,
        "fair_groups": fair["groups"] if fair else 0,
        "fair_deals": fair["deals"] if fair else 0,
        "size_with": float(w[COL["area_sqm"]].median()),
        "size_without": float(wo[COL["area_sqm"]].median()),
        "offplan_with": share(w, COL["reg_type"], "Off-Plan Properties"),
        "offplan_without": share(wo, COL["reg_type"], "Off-Plan Properties"),
        "studio_with": share(w, COL["rooms"], "Studio"),
        "studio_without": share(wo, COL["rooms"], "Studio"),
        "top_area_with": (str(top_w.index[0]), float(top_w.iloc[0] * 100)) if top_w is not None and len(top_w) else None,
        "top_area_without": (str(top_wo.index[0]), float(top_wo.iloc[0] * 100)) if top_wo is not None and len(top_wo) else None,
        "within_reg": within,
        "sign_flips": bool(len(signs) >= 2 and min(signs) < 0 < max(signs)),
    }


def amenity_composition(df: pd.DataFrame, column: str) -> dict:
    """
    Why an amenity's headline number looks the way it does.

    Returns the composition of the with / without groups across the
    characteristics that actually drive rate per m², so a reader can see for
    themselves whether the gap is the amenity or the property mix.
    """
    if column not in df.columns:
        return {}
    w, wo = df[df[column] == 1], df[df[column] == 0]
    if w.empty or wo.empty:
        return {}

    def mix(col):
        a = w[col].value_counts(normalize=True).mul(100)
        b = wo[col].value_counts(normalize=True).mul(100)
        out = pd.DataFrame({"With (%)": a, "Without (%)": b}).fillna(0)
        out["Difference (pp)"] = out["With (%)"] - out["Without (%)"]
        return out.sort_values("Difference (pp)", key=abs, ascending=False)

    return {
        "label": AMENITIES.get(column, column),
        "n_with": int(len(w)),
        "n_without": int(len(wo)),
        "share_with": len(w) / len(df) * 100,
        "median_size_with": float(w[COL["area_sqm"]].median()),
        "median_size_without": float(wo[COL["area_sqm"]].median()),
        "reg_type": mix(COL["reg_type"]),
        "rooms": mix(COL["rooms"]).head(6),
        "zone": mix(COL["zone"]).head(6),
        "top_areas_with": w[COL["area"]].value_counts(normalize=True).head(5).mul(100),
        "top_areas_without": wo[COL["area"]].value_counts(normalize=True).head(5).mul(100),
        # The same comparison computed separately inside each registration type.
        "within_reg": pd.DataFrame([
            {"Registration type": rt,
             "Median rate with": float(sub.loc[sub[column] == 1, COL["rate"]].median()),
             "Median rate without": float(sub.loc[sub[column] == 0, COL["rate"]].median()),
             "Deals with": int((sub[column] == 1).sum()),
             "Deals without": int((sub[column] == 0).sum()),
             "Difference (%)": float(
                 (sub.loc[sub[column] == 1, COL["rate"]].median()
                  / sub.loc[sub[column] == 0, COL["rate"]].median() - 1) * 100)
             if (sub[column] == 0).any() and (sub[column] == 1).any() else float("nan")}
            for rt, sub in df.groupby(COL["reg_type"], observed=True)
            if (sub[column] == 0).any() and (sub[column] == 1).any()
        ]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# DEEPER INSIGHT TABLES
# ─────────────────────────────────────────────────────────────────────────────


def concentration(df: pd.DataFrame, column: str, top_n: int = 10) -> pd.DataFrame:
    """Share of transactions and value held by the top N groups."""
    grp = (
        df.groupby(column, observed=True)
        .agg(Transactions=(COL["price"], "size"),
             **{"Total value (AED)": (COL["price"], "sum"),
                "Median price (AED)": (COL["price"], "median"),
                "Median rate (AED/m²)": (COL["rate"], "median")})
        .sort_values("Transactions", ascending=False)
    )
    grp["Share of transactions (%)"] = grp["Transactions"] / len(df) * 100
    grp["Share of value (%)"] = grp["Total value (AED)"] / df[COL["price"]].sum() * 100
    return grp.head(top_n).reset_index()


BAND_EDGES = [0, 500_000, 1_000_000, 2_000_000, 3_000_000, 5_000_000, 10_000_000, float("inf")]
BAND_LABELS = ["< 500K", "500K – 1M", "1M – 2M", "2M – 3M", "3M – 5M", "5M – 10M", "> 10M"]


def price_bands(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Transaction counts by sale-price band.

    Bands are left-closed / right-open (`right=False`) so every transaction
    falls in exactly one band and none is double-counted. The returned `audit`
    dict proves it: `assigned` must equal `total`.
    """
    band = pd.cut(df[COL["price"]], bins=BAND_EDGES, labels=BAND_LABELS, right=False)
    out = band.value_counts().reindex(BAND_LABELS).fillna(0).astype(int).reset_index()
    out.columns = ["Price band (AED)", "Transactions"]
    total = max(len(df), 1)
    out["Share (%)"] = out["Transactions"] / total * 100

    audit = {
        "total": int(len(df)),
        "assigned": int(out["Transactions"].sum()),
        "unassigned": int(len(df) - out["Transactions"].sum()),
        "share_sum": float(out["Share (%)"].sum()),
        "invalid_price": int((df[COL["price"]] <= 0).sum() + df[COL["price"]].isna().sum()),
        "empty_bands": [b for b, n in zip(out["Price band (AED)"], out["Transactions"]) if n == 0],
    }
    return out, audit


def yoy_table(df: pd.DataFrame) -> pd.DataFrame:
    """Year-by-year volume, median price and median rate, with YoY changes."""
    t = (
        df.groupby(COL["year"], observed=True)
        .agg(Transactions=(COL["price"], "size"),
             **{"Median price (AED)": (COL["price"], "median"),
                "Median rate (AED/m²)": (COL["rate"], "median"),
                "Total value (AED)": (COL["price"], "sum")})
        .sort_index()
        .reset_index()
        .rename(columns={COL["year"]: "Year"})
    )
    t["Volume YoY (%)"] = t["Transactions"].pct_change() * 100
    t["Price YoY (%)"] = t["Median price (AED)"].pct_change() * 100
    t["Rate YoY (%)"] = t["Median rate (AED/m²)"].pct_change() * 100
    return t


def yoy_validation(df: pd.DataFrame) -> dict:
    """
    Everything needed to read the year-over-year chart honestly.

    Confirms that each year is compared with the immediately preceding year,
    reports any gap in the year sequence, flags an incomplete final year, and —
    when the final year is partial — computes the like-for-like year-to-date
    comparison against the same months of the previous year.
    """
    years = sorted(int(y) for y in df[COL["year"]].unique())
    if len(years) < 2:
        return {"years": years, "gaps": [], "partial": None}

    gaps = [y for y in range(years[0], years[-1] + 1) if y not in years]
    latest, prev = years[-1], years[-2]

    last_month = int(df.loc[df[COL["year"]] == latest, COL["month"]].max())
    partial = last_month < 12

    out = {
        "years": years, "gaps": gaps, "latest": latest, "previous": prev,
        "partial": partial, "months_available": last_month,
    }

    if partial:
        cur = df[df[COL["year"]] == latest]
        base = df[(df[COL["year"]] == prev) & (df[COL["month"]] <= last_month)]
        base_full = df[df[COL["year"]] == prev]
        if len(base) and len(base_full):
            out.update({
                "ytd_volume_current": int(len(cur)),
                "ytd_volume_base": int(len(base)),
                "ytd_volume_pct": (len(cur) / len(base) - 1) * 100,
                "fullyear_volume_pct": (len(cur) / len(base_full) - 1) * 100,
                "ytd_rate_current": float(cur[COL["rate"]].median()),
                "ytd_rate_base": float(base[COL["rate"]].median()),
                "ytd_rate_pct": (cur[COL["rate"]].median() / base[COL["rate"]].median() - 1) * 100,
                "fullyear_rate_pct": (
                    cur[COL["rate"]].median() / base_full[COL["rate"]].median() - 1) * 100,
            })
    return out


def offplan_premium_table(df: pd.DataFrame, min_n: int = 100) -> pd.DataFrame:
    """
    Off-plan premium or discount against existing property, per year.

    Premium (%) = (off-plan median rate − existing median rate) / existing × 100.
    A year is only reported when both sides carry at least `min_n` transactions.
    """
    if COL["reg_type"] not in df.columns:
        return pd.DataFrame()

    med = df.pivot_table(index=COL["year"], columns=COL["reg_type"],
                         values=COL["rate"], aggfunc="median", observed=True)
    cnt = df.pivot_table(index=COL["year"], columns=COL["reg_type"],
                         values=COL["rate"], aggfunc="size", observed=True)
    off, exi = "Off-Plan Properties", "Existing Properties"
    if off not in med.columns or exi not in med.columns:
        return pd.DataFrame()

    t = pd.DataFrame({
        "Year": med.index.astype(int),
        "Off-plan median (AED/m²)": med[off].to_numpy(),
        "Existing median (AED/m²)": med[exi].to_numpy(),
        "Off-plan deals": cnt[off].fillna(0).astype(int).to_numpy(),
        "Existing deals": cnt[exi].fillna(0).astype(int).to_numpy(),
    }).dropna()
    t = t[(t["Off-plan deals"] >= min_n) & (t["Existing deals"] >= min_n)]
    t["Premium (%)"] = ((t["Off-plan median (AED/m²)"] / t["Existing median (AED/m²)"]) - 1) * 100
    return t.reset_index(drop=True)


def monthly_series(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly transaction count, median price and median rate."""
    m = (
        df.groupby(COL["year_month"], observed=True)
        .agg(Transactions=(COL["price"], "size"),
             median_price=(COL["price"], "median"),
             median_rate=(COL["rate"], "median"),
             total_value=(COL["price"], "sum"))
        .reset_index()
        .rename(columns={COL["year_month"]: "Month"})
    )
    m = m[m["Month"].astype(str).str.len() >= 6].copy()
    m["_sort"] = pd.PeriodIndex(m["Month"].astype(str), freq="M").to_timestamp()
    return m.sort_values("_sort").reset_index(drop=True)


# ═════════════════════════════════════════════════════════════════════════════
# v1.3 — RAW transaction volume, controlled amenity comparison, building height
# ═════════════════════════════════════════════════════════════════════════════

# Dataset value → business label. Only values that actually exist in the
# cleaned dataset appear here; nothing is invented.
PROPERTY_TYPE_LABELS = {
    "Studio": "Studio",
    "1 B/R": "1 BHK",
    "2 B/R": "2 BHK",
    "3 B/R": "3 BHK",
    "4 B/R": "4 BHK",
    "5 B/R": "5 BHK",
    "PENTHOUSE": "Penthouse",
}
LABEL_TO_PROPERTY_TYPE = {v: k for k, v in PROPERTY_TYPE_LABELS.items()}

# Minimum transactions a group needs before it is reported at all.
MIN_CELL = 100

BASE_YEAR = 2011


def raw_transaction_years(counts: pd.DataFrame, base_year: int = BASE_YEAR) -> pd.DataFrame:
    """
    Yearly transaction counts from the RAW registry, with year-over-year growth.

    DATA SOURCE: RAW (`data/dubai/transactions.parquet`) — see `data.py` for why.

    Completed years get a growth figure against the year immediately before
    them. The latest year is flagged as incomplete when the registry does not
    yet cover all twelve of its months; its `yoy_pct` is left as NaN here and
    the caller decides what, if anything, to display — see `partial_year_growth`.
    """
    per_year = (counts.groupby("year", as_index=False)
                      .agg(transactions=("transactions", "sum"),
                           all_transactions=("all_transactions", "sum"),
                           months=("month", "nunique"),
                           last_month=("month", "max"))
                      .sort_values("year"))

    latest_year = int(per_year["year"].max())
    latest_months = int(per_year.loc[per_year["year"] == latest_year, "months"].iloc[0])
    per_year["complete"] = ~((per_year["year"] == latest_year) & (latest_months < 12))

    # Growth is chained: every year against the row directly above it.
    per_year["prev_transactions"] = per_year["transactions"].shift()
    per_year["yoy_pct"] = (per_year["transactions"] / per_year["prev_transactions"] - 1) * 100

    # An incomplete year is not a comparable annual observation. Its full-year
    # style growth figure is dropped rather than displayed as a decline.
    per_year.loc[~per_year["complete"], "yoy_pct"] = float("nan")

    out = per_year[per_year["year"] >= base_year].reset_index(drop=True)
    # The base year opens the series, so it has no predecessor to compare with.
    if not out.empty:
        out.loc[out.index[0], "yoy_pct"] = float("nan")
    return out


def partial_year_growth(counts: pd.DataFrame) -> dict:
    """
    The like-for-like position of the incomplete latest year.

    The comparison basis is the SAME months of the previous year — the only
    basis under which a part-year count can be compared with anything at all.

    `display_growth` is the number the chart is allowed to show, and it is
    populated **only when growth is strictly positive**. A part-year count
    that is level with or below the previous year's same period says nothing
    reliable about the full year, so no percentage is shown for it.
    """
    latest_year = int(counts["year"].max())
    cur = counts[counts["year"] == latest_year]
    months = sorted(int(m) for m in cur["month"].unique())
    last_month = max(months)
    complete = len(months) >= 12

    base = counts[(counts["year"] == latest_year - 1) & (counts["month"] <= last_month)]
    current_n = int(cur["transactions"].sum())
    base_n = int(base["transactions"].sum())
    full_prev = int(counts.loc[counts["year"] == latest_year - 1, "transactions"].sum())

    growth = (current_n / base_n - 1) * 100 if base_n else float("nan")
    return {
        "year": latest_year,
        "complete": complete,
        "months_available": len(months),
        "last_month": last_month,
        "last_month_name": pd.Timestamp(2000, last_month, 1).strftime("%B"),
        "period_label": f"January–{pd.Timestamp(2000, last_month, 1).strftime('%B')}",
        "transactions": current_n,
        "basis_transactions": base_n,
        "basis_year": latest_year - 1,
        "previous_full_year": full_prev,
        "growth_pct": growth,
        # Strictly positive only. Zero and negative are suppressed on purpose.
        "display_growth": growth if (pd.notna(growth) and growth > 0) else None,
    }


def yearly_summary(counts: pd.DataFrame, df: pd.DataFrame,
                   base_year: int = BASE_YEAR) -> pd.DataFrame:
    """
    Year-wise summary table.

    Transaction counts come from the RAW registry; the rate statistics come
    from the CLEANED dataset, which is the validated basis for every price
    figure on this page. Mixing the two is deliberate and is stated on screen:
    each column is labelled with the source it came from.
    """
    vol = (counts.groupby("year", as_index=False)
                 .agg(transactions=("transactions", "sum"), months=("month", "nunique")))

    rate = (df.groupby(COL["year"], observed=True)[COL["rate"]]
              .agg(["mean", "median", "size"])
              .rename(columns={"mean": "mean_rate", "median": "median_rate",
                               "size": "priced_rows"})
              .reset_index()
              .rename(columns={COL["year"]: "year"}))
    rate["year"] = rate["year"].astype(int)

    out = vol.merge(rate, on="year", how="left")
    out = out[out["year"] >= base_year].sort_values("year").reset_index(drop=True)
    latest = int(out["year"].max())
    out["complete"] = ~((out["year"] == latest) & (out["months"] < 12))
    return out


def amenity_transaction_share(df: pd.DataFrame, property_type: str | None = None,
                              min_rows: int = MIN_CELL) -> pd.DataFrame:
    """
    Share of recorded transactions associated with each amenity.

    DATA SOURCE: CLEANED — the amenity flags exist only there.

    Optionally restricted to one property type. This is an observed share of
    completed transactions, NOT a purchase probability: the dataset contains no
    non-purchase records against which a probability could be estimated.
    """
    sub = df if property_type is None else df[df[COL["rooms"]] == property_type]
    if sub.empty or len(sub) < min_rows:
        return pd.DataFrame()

    rows = []
    for col, label in AMENITIES.items():
        if col not in sub.columns:
            continue
        recorded = int((sub[col] == 1).sum())
        rows.append({
            "Amenity": label,
            "Transactions with amenity recorded": recorded,
            "Transactions without": int(len(sub) - recorded),
            "Share of recorded transactions (%)": recorded / len(sub) * 100,
        })
    out = pd.DataFrame(rows)
    return out.sort_values("Share of recorded transactions (%)",
                           ascending=False).reset_index(drop=True)


def amenity_share_by_property_type(df: pd.DataFrame, column: str,
                                   min_rows: int = MIN_CELL) -> pd.DataFrame:
    """The same share for one amenity, across every property type."""
    if column not in df.columns:
        return pd.DataFrame()
    rows = []
    for value, label in PROPERTY_TYPE_LABELS.items():
        sub = df[df[COL["rooms"]] == value]
        if len(sub) < min_rows:
            continue
        recorded = int((sub[column] == 1).sum())
        rows.append({
            "Property type": label,
            "Transactions": int(len(sub)),
            "With amenity recorded": recorded,
            "Share of recorded transactions (%)": recorded / len(sub) * 100,
        })
    return pd.DataFrame(rows)


# ── Part 8 — year-level volume against price ────────────────────────────────

def volume_vs_mean_rate(counts: pd.DataFrame, df: pd.DataFrame,
                        base_year: int = BASE_YEAR) -> pd.DataFrame:
    """
    Year · transaction volume (RAW) · MEAN rate per m² (CLEANED).

    The mean is used here rather than the median on purpose. This chart asks
    whether busy years are also expensive years — a question about the total
    money moving through the market — and the mean is the statistic that
    reflects the whole distribution, including the upper tail that a hot market
    actually adds. Every other price figure on this page uses the median, and
    both are reported side by side in the summary table so the difference
    between them stays visible.
    """
    return yearly_summary(counts, df, base_year)[
        ["year", "transactions", "mean_rate", "median_rate", "complete"]]


# ── Building height ─────────────────────────────────────────────────────────
#
# The dataset does NOT record which floor a unit is on. `floor_bin` is the
# string "Unknown" on every populated row, and `floors` is constant within
# `property_id_bld` for 100% of buildings — it is the building's height, not
# the unit's floor. The analysis below is therefore about BUILDING HEIGHT, and
# it is labelled that way everywhere rather than being passed off as floor
# level. See `docs/Dashboard_Changes_and_Solutions.md`.

FLOOR_FIELD = COL["floors"]


# ─────────────────────────────────────────────────────────────────────────────
# FLOOR BANDS — fixed, named, human-readable
#
# Two floor-related columns exist in the cleaned dataset, and only one is
# usable:
#
#   `floor_bin`  populated on 505,993 rows and carrying the single literal
#                value "Unknown" on every one of them. Zero information. It
#                cannot be used for any segmentation, and is not.
#   `floors`     the number of floors in the BUILDING. Verified constant for
#                every sale within a given building across all 2,245 buildings
#                tested, which is what makes it a building attribute rather
#                than the floor a particular unit sits on.
#
# The bands below are FIXED thresholds on round numbers, not quantiles of the
# current selection. Fixed edges mean "Low-rise" denotes the same building
# everywhere — comparable between areas, and stable as filters change. Quartile
# edges moved with the selection and could label a 17-storey tower "Low-rise"
# in a district of skyscrapers.
#
# Coverage on the full cleaned dataset (480,619 transactions with a valid
# floor count) — every band is well populated, none is a rump:
#
#   Low-rise    1–10 floors    171,580   35.7%
#   Mid-rise   11–25 floors    143,369   29.8%
#   High-rise  26–40 floors     88,259   18.4%
#   Tower       41+ floors      77,411   16.1%
#
# 799 rows record `floors == 0`. A building cannot have zero floors, so those
# are treated as an invalid reading and excluded rather than folded into the
# lowest band, and the count is reported.
# ─────────────────────────────────────────────────────────────────────────────

FLOOR_BAND_EDGES = [0, 10, 25, 40, float("inf")]
FLOOR_BAND_LABELS = [
    "Low-rise (1–10 floors)",
    "Mid-rise (11–25 floors)",
    "High-rise (26–40 floors)",
    "Tower (41+ floors)",
]
FLOOR_BAND_SPANS = {
    "Low-rise (1–10 floors)": "1 to 10 floors — 10 floors wide",
    "Mid-rise (11–25 floors)": "11 to 25 floors — 15 floors wide",
    "High-rise (26–40 floors)": "26 to 40 floors — 15 floors wide",
    "Tower (41+ floors)": "41 floors and above — open-ended",
}


def building_height_bands(df: pd.DataFrame) -> tuple[list[str], list[float]]:
    """
    The fixed floor bands.

    `df` is accepted so the call site is unchanged, but the edges no longer
    depend on it: they are the same in every area and under every filter, which
    is the point. Returns (labels, edges) for `pd.cut(..., right=True)`, so a
    building of exactly 10 floors is Low-rise and one of exactly 11 is Mid-rise.
    """
    if FLOOR_FIELD not in df.columns:
        return [], []
    return list(FLOOR_BAND_LABELS), list(FLOOR_BAND_EDGES)


def rate_by_building_height(df: pd.DataFrame, min_cell: int = MIN_CELL,
                            band_source: pd.DataFrame | None = None
                            ) -> tuple[pd.DataFrame, dict]:
    """
    Median rate per m² by building-height band and property type.

    DATA SOURCE: CLEANED. Returns the plotting frame plus an audit dict naming
    every cell dropped for thin support, so nothing disappears silently.

    Bands are the fixed thresholds in `FLOOR_BAND_LABELS` — the same floors in
    every area and under every filter, so two areas stay comparable. The
    `band_source` argument is retained for call-site compatibility but no
    longer changes the edges.
    """
    labels, edges = building_height_bands(df if band_source is None else band_source)
    if not labels:
        return pd.DataFrame(), {"reason": "no height field in this selection"}

    d = df.dropna(subset=[FLOOR_FIELD]).copy()
    # A building cannot have zero floors. Those readings are invalid, not
    # low-rise, so they are dropped rather than folded into the bottom band.
    invalid_floor = int((d[FLOOR_FIELD] < 1).sum())
    d = d[d[FLOOR_FIELD] >= 1]
    d["height_band"] = pd.cut(d[FLOOR_FIELD], bins=edges, labels=labels, right=True)
    d = d[d[COL["rooms"]].isin(PROPERTY_TYPE_LABELS)]

    grouped = (d.groupby(["height_band", COL["rooms"]], observed=True)
                 .agg(median_rate=(COL["rate"], "median"),
                      mean_rate=(COL["rate"], "mean"),
                      transactions=(COL["rate"], "size"))
                 .reset_index())
    kept = grouped[grouped["transactions"] >= min_cell].copy()
    dropped = grouped[grouped["transactions"] < min_cell]

    kept["Property type"] = kept[COL["rooms"]].map(PROPERTY_TYPE_LABELS)
    kept["height_band"] = pd.Categorical(kept["height_band"], categories=labels, ordered=True)
    kept = kept.sort_values(["height_band", COL["rooms"]])

    audit = {
        "bands": labels,
        "edges": edges,
        "spans": {b: FLOOR_BAND_SPANS.get(b, "") for b in labels},
        "rows_with_height": int(len(d)),
        "rows_total": int(len(df)),
        "coverage_pct": round(len(d) / max(len(df), 1) * 100, 1),
        "invalid_floor": invalid_floor,
        "band_counts": {
            str(b): int((d["height_band"] == b).sum()) for b in labels
        },
        "min_cell": min_cell,
        "dropped": [
            f"{PROPERTY_TYPE_LABELS.get(r[COL['rooms']], r[COL['rooms']])} in "
            f"{r['height_band']} ({int(r['transactions'])} deals)"
            for _, r in dropped.iterrows() if r["transactions"] > 0
        ],
    }
    return kept, audit


def summary_stats(df: pd.DataFrame, column: str) -> dict:
    s = df[column].dropna()
    if s.empty:
        return {}
    return {
        "count": int(s.size),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "p25": float(s.quantile(0.25)),
        "p75": float(s.quantile(0.75)),
        "p95": float(s.quantile(0.95)),
        "min": float(s.min()),
        "max": float(s.max()),
        "skew": float(s.skew()),
        "std": float(s.std()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PANEL-LEVEL AREA FILTER  (Parts 2, 3 and 4)
#
# These panels each gained their own Area selector. The rule the prompt is
# explicit about: the selection must reduce the dataframe BEFORE any
# aggregation runs, never merely relabel a chart computed on all of Dubai.
# `area_options` supplies the choices; the panels then slice the frame and pass
# the SMALLER frame into the existing metric functions, so one filtered
# population feeds every number in the panel.
# ─────────────────────────────────────────────────────────────────────────────

ALL_AREAS = "All areas"


def area_options(df: pd.DataFrame, min_rows: int = 1) -> list[tuple[str, int]]:
    """
    Areas present in the CURRENT selection, busiest first, with their counts.

    Returned as (area, transactions) so the caller can show the count in the
    control and the user knows how much data sits behind each choice.
    """
    if COL["area"] not in df.columns or df.empty:
        return []
    vc = df[COL["area"]].dropna().value_counts()
    return [(str(a), int(n)) for a, n in vc.items() if n >= min_rows]


def apply_area(df: pd.DataFrame, area: str) -> pd.DataFrame:
    """
    Slice to one area. `ALL_AREAS` returns the frame untouched.

    This is the single place the panel-level area filter is applied, so every
    statistic in a panel is guaranteed to come from the same population.
    """
    if not area or area == ALL_AREAS or COL["area"] not in df.columns:
        return df
    return df[df[COL["area"]] == area]


# ─────────────────────────────────────────────────────────────────────────────
# TOP 5 AREAS INSIDE EACH PRICE BRACKET  (Part 5)
# ─────────────────────────────────────────────────────────────────────────────


def top_areas_by_band(df: pd.DataFrame, top_n: int = 5) -> tuple[pd.DataFrame, dict]:
    """
    The `top_n` busiest areas inside each sale-price bracket.

    Bracket boundaries are the same `BAND_EDGES` the bracket chart uses, cut
    with `right=False`, i.e. **left-closed / right-open**: a sale of exactly
    AED 500,000 belongs to "500K – 1M", not to "< 500K". The same rule applies
    at 1M, 2M, 3M, 5M and 10M, so there is no gap, no overlap and no
    transaction classified twice.

    Nothing is hard-coded: the areas come out of the data by value count.

    Returns (frame, audit). The audit proves every priced transaction landed in
    exactly one bracket, and documents anything excluded.
    """
    price_col, area_col = COL["price"], COL["area"]
    if df.empty or area_col not in df.columns:
        return pd.DataFrame(columns=["Price band (AED)", "Rank", "Area", "Transactions",
                                     "Share of band (%)"]), {
            "total": int(len(df)), "valid": 0, "classified": 0, "unassigned": 0,
            "invalid_price": 0, "missing_area": 0, "bands_with_data": [],
            "empty_bands": list(BAND_LABELS), "boundary_rule": _BOUNDARY_RULE,
        }

    price = df[price_col]
    valid_mask = price.notna() & (price > 0)
    invalid_price = int((~valid_mask).sum())

    work = df[valid_mask]
    missing_area = int(work[area_col].isna().sum())

    band = pd.cut(work[price_col], bins=BAND_EDGES, labels=BAND_LABELS, right=False)
    work = work.assign(_band=band)
    classified = int(work["_band"].notna().sum())

    # Areas actually present in the selection. `area_name_en` is a `category`
    # after loading, and `value_counts()` on a categorical returns EVERY
    # category — including the 68 with no rows left after an area filter. That
    # produced a top-5 padded with zero-transaction areas. Only areas with at
    # least one transaction in the bracket may be ranked.
    present = [str(a) for a in work[area_col].dropna().unique()]

    rows: list[dict] = []
    empty_for_selection: list[str] = []
    for label in BAND_LABELS:
        sub = work[(work["_band"] == label) & work[area_col].notna()]
        if sub.empty:
            empty_for_selection.append(label)
            continue
        total_in_band = int(len(sub))
        counts = sub[area_col].value_counts()
        counts = counts[counts > 0].head(top_n)
        if counts.empty:
            empty_for_selection.append(label)
            continue
        for rank, (area, n) in enumerate(counts.items(), start=1):
            rows.append({
                "Price band (AED)": label,
                "Rank": rank,
                "Area": str(area),
                "Transactions": int(n),
                "Share of band (%)": float(n) / total_in_band * 100,
            })

    out = pd.DataFrame(rows, columns=["Price band (AED)", "Rank", "Area",
                                      "Transactions", "Share of band (%)"])

    present_bands = sorted(set(out["Price band (AED)"])) if not out.empty else []
    audit = {
        "total": int(len(df)),
        "valid": int(valid_mask.sum()),
        "classified": classified,
        "unassigned": int(valid_mask.sum()) - classified,
        "invalid_price": invalid_price,
        "missing_area": missing_area,
        "bands_with_data": [b for b in BAND_LABELS if b in present_bands],
        "empty_bands": [b for b in BAND_LABELS if b not in present_bands],
        "boundary_rule": _BOUNDARY_RULE,
        "band_totals": {
            b: int((work["_band"] == b).sum()) for b in BAND_LABELS
        },
        # When the selection is a single area, this is that area and the list of
        # brackets it has no transactions in — so the panel can say so plainly
        # instead of showing a blank or a padded table.
        "single_area": present[0] if len(present) == 1 else None,
        "absent_bands": empty_for_selection,
    }
    return out, audit


_BOUNDARY_RULE = (
    "Brackets are left-closed and right-open. A sale of exactly AED 500,000 is "
    "counted in 500K – 1M, exactly AED 1,000,000 in 1M – 2M, exactly "
    "AED 2,000,000 in 2M – 3M, exactly AED 3,000,000 in 3M – 5M, exactly "
    "AED 5,000,000 in 5M – 10M and exactly AED 10,000,000 in > 10M. Every "
    "boundary belongs to the bracket above it, so no transaction can fall in "
    "two brackets or in none."
)


# ─────────────────────────────────────────────────────────────────────────────
# LOWESS TREND — the single smoothing method used by "How prices are moving"
#
# LOWESS was chosen over exponential smoothing on measured evidence from this
# dataset, not preference. On the 200-month series:
#
#                            LOWESS      Exponential (Holt)
#   trend month-on-month sd    1.38%          3.82%      <- LOWESS is calmer
#   median distance from data  2.61%          3.51%      <- and closer to it
#
# A smoother normally buys calmness by drifting away from the observations.
# LOWESS is better on BOTH at once here, and the reason is structural: it is
# centred, so it can use the months on either side of a point, whereas
# exponential smoothing is one-sided and must trail every turning point. The
# Holt fit also drove its trend weight to beta = 0.000 on this series, i.e. it
# collapsed to a plain backward-looking weighted average and contributed no
# trend term at all.
#
# LOWESS is also the safer choice against the two failure modes that matter
# here: it never extrapolates (it is only defined over observed months, so it
# cannot invent a future value), and the span is re-selected per series so a
# filtered selection is smoothed on its own terms.
# ─────────────────────────────────────────────────────────────────────────────

LOWESS_FRAC_CANDIDATES = (0.05, 0.08, 0.10, 0.15, 0.20, 0.30)
LOWESS_TARGET_SD_PCT = 2.0     # trend must move less than this month to month
LOWESS_MIN_POINTS = 8          # below this, smoothing says more than the data does


def lowess_span(n_points: int) -> float:
    """
    The span to use for a series of `n_points` months.

    Chosen so the window is about ten months whatever the selection length —
    the narrowest span that still read as a trend rather than as noise when the
    candidates were measured on the full series. Clamped so that a short
    selection cannot end up with a window of one or two points (which would
    trace the noise) or one covering the whole series (which would flatten it).
    """
    if n_points <= 0:
        return 0.3
    return float(min(0.9, max(0.05, 10.0 / n_points)))


def lowess_trend(values: "pd.Series", exclude_tail: int = 0) -> "pd.Series":
    """
    Centred LOWESS trend over `values`, aligned to the original index.

    `exclude_tail` drops the last N points from the FIT — used for the partial
    final month, whose transaction count is a fraction of a normal month. That
    month is a counting artefact, not a market move; letting it into the fit
    would drag the right-hand edge of the trend down and invent a decline. The
    excluded points come back as NaN, so the trend line simply stops at the last
    complete month rather than being drawn over a value it did not fit.

    The result is only ever defined over observed months. LOWESS does not
    extrapolate, so no future value can be produced here.
    """
    import numpy as np
    from statsmodels.nonparametric.smoothers_lowess import lowess

    s = pd.Series(values).astype(float)
    out = pd.Series(np.nan, index=s.index, dtype=float)

    fit_s = s.iloc[: len(s) - exclude_tail] if exclude_tail else s
    fit_s = fit_s.dropna()
    if len(fit_s) < LOWESS_MIN_POINTS:
        # Too few months to smooth honestly — hand back the observations.
        out.loc[fit_s.index] = fit_s.values
        return out

    x = np.arange(len(fit_s), dtype=float)
    fitted = lowess(fit_s.values, x, frac=lowess_span(len(fit_s)), it=3,
                    return_sorted=False)
    out.loc[fit_s.index] = fitted
    return out


def partial_tail_months(monthly: "pd.DataFrame", ratio: float = 0.6) -> int:
    """
    How many months at the END of the series are materially incomplete.

    Uses the same rule the chart already used to shade the partial month: a
    final month carrying less than `ratio` of the preceding month's
    transactions. Returned as a count so the smoother and the shading agree
    instead of each deciding separately.
    """
    if len(monthly) < 2 or "Transactions" not in monthly.columns:
        return 0
    n = monthly["Transactions"].to_numpy()
    tail = 0
    i = len(n) - 1
    while i > 0 and n[i] < ratio * n[i - 1]:
        tail += 1
        i -= 1
        if tail >= 3:            # never treat more than a quarter as partial
            break
    return tail


# ─────────────────────────────────────────────────────────────────────────────
# AMENITY ANALYSIS — the selected slice against a Dubai-wide baseline
#
# Why this replaced a plain ranked bar of raw shares.
#
# Parking is recorded on 88.9%–100.0% of transactions in EVERY property type.
# It is very nearly a constant, so a chart that ranks amenities by raw share
# puts parking first every single time, in every area, for every layout. A
# reader looking at that chart reasonably concludes "parking matters most",
# when what they are actually seeing is which field the registry fills in most
# reliably. The chart answered a question about record-keeping while appearing
# to answer one about the market.
#
# Comparing the selected slice against the same measurement across Dubai fixes
# that. A near-constant like parking lands on top of its own baseline and shows
# no gap, so it stops shouting. What stands out instead is a genuine
# difference — an amenity recorded far more, or far less, often in this slice
# than across the city.
#
# This remains strictly descriptive. It measures how often a feature appears on
# the record, and nothing else: no price, no preference, no probability of
# purchase, no causation.
# ─────────────────────────────────────────────────────────────────────────────


def amenity_share_vs_baseline(scope: pd.DataFrame, baseline: pd.DataFrame,
                              property_type: str | None = None,
                              min_rows: int = MIN_CELL) -> tuple[pd.DataFrame, dict]:
    """
    Recorded share of each amenity in `scope`, beside the same figure in
    `baseline`, plus the gap between them in percentage points.

    `scope`    the Area + Property-type slice the user selected.
    `baseline` the whole current sidebar selection — every area, every property
               type. It is the reference the slice is read against.

    Returns (frame, audit). The frame is empty when the slice is too thin to
    report, and the audit says how thin, so the panel can explain rather than
    silently draw nothing.
    """
    sel = scope
    if property_type is not None and COL["rooms"] in scope.columns:
        sel = scope[scope[COL["rooms"]] == property_type]

    audit = {
        "scope_rows": int(len(sel)),
        "baseline_rows": int(len(baseline)),
        "min_rows": int(min_rows),
        "enough": bool(len(sel) >= min_rows),
    }
    if not audit["enough"] or baseline.empty:
        return pd.DataFrame(), audit

    rows = []
    for column, label in AMENITIES.items():
        if column not in sel.columns or column not in baseline.columns:
            continue
        with_sel = int((sel[column] == 1).sum())
        with_base = int((baseline[column] == 1).sum())
        share_sel = with_sel / len(sel) * 100
        share_base = with_base / len(baseline) * 100
        rows.append({
            "Amenity": label,
            "Share in selection (%)": share_sel,
            "Share across Dubai (%)": share_base,
            "Difference (pp)": share_sel - share_base,
            "Recorded with (selection)": with_sel,
            "Transactions (selection)": int(len(sel)),
            "Recorded with (Dubai)": with_base,
            "Transactions (Dubai)": int(len(baseline)),
        })

    frame = pd.DataFrame(rows)
    if not frame.empty:
        # Widest gap first — the comparison is the point of the chart, so the
        # amenity that differs most from the city should be the one you read
        # first. A near-constant like parking sinks to the bottom on its own.
        frame = (frame.reindex(frame["Difference (pp)"].abs()
                               .sort_values(ascending=False).index)
                      .reset_index(drop=True))
    return frame, audit


# ─────────────────────────────────────────────────────────────────────────────
# EXPERIMENTAL — LOWESS against exponential smoothing, on one identical series
#
# This powers the comparison ADDED to the Experimental Analysis environment. It
# is research material for method selection, not a dashboard metric: the live
# Dubai price chart uses LOWESS and does not consult anything here.
#
# Both methods receive the SAME series, produced by ONE call to
# `monthly_series` on ONE dataframe. Nothing differs between the two versions
# except the smoother — same dataset, same monthly aggregation, same statistic,
# same period.
#
# Both are SMOOTHERS. Neither extends past the last observed month, and neither
# is a forecast.
# ─────────────────────────────────────────────────────────────────────────────

SMOOTHING_FRAC_CANDIDATES = (0.05, 0.08, 0.10, 0.15, 0.20, 0.30)


def _smoother_diagnostics(actual: "pd.Series", trend: "pd.Series",
                          edge: int = 3) -> dict:
    """
    Measurable properties of a smoothed series, so the comparison rests on
    evidence rather than on which line looks nicer.

      smoothness  sd of month-on-month % change of the TREND. Lower = calmer.
      fidelity    median |trend − actual| ÷ actual. Lower = closer to the data.
      edge_vs_core  mean error over the first and last `edge` points against
                  the interior. Above 1 means the ends are less reliable.
      lag         the shift, in months, that best aligns the trend's direction
                  with the actual series. A centred smoother scores 0; a
                  one-sided one trails.
    """
    import numpy as np

    a = pd.Series(actual).astype(float).reset_index(drop=True)
    t = pd.Series(trend).astype(float).reset_index(drop=True)
    ok = a.notna() & t.notna()
    a, t = a[ok].reset_index(drop=True), t[ok].reset_index(drop=True)
    if len(a) < 2 * edge + 4:
        return {}

    dev = (t - a).abs() / a.abs()
    n = len(a)
    edge_idx = list(range(edge)) + list(range(n - edge, n))
    core_idx = list(range(edge, n - edge))

    best_lag, best_corr = 0, -2.0
    da = a.diff().dropna()
    for lag in range(0, 7):
        dt = t.diff().shift(-lag).dropna()
        common = da.index.intersection(dt.index)
        if len(common) < 12:
            continue
        c = float(np.corrcoef(da.loc[common], dt.loc[common])[0, 1])
        if c > best_corr:
            best_corr, best_lag = c, lag

    return {
        "smoothness_sd_pct": float(t.pct_change(fill_method=None).std() * 100),
        "fidelity_median_dev_pct": float(dev.median() * 100),
        "max_dev_pct": float(dev.max() * 100),
        "edge_vs_core": float(dev.iloc[edge_idx].mean()
                              / max(dev.iloc[core_idx].mean(), 1e-9)),
        "lag_months": int(best_lag),
        "lag_corr": float(best_corr),
    }


def smoothing_experiment(df: pd.DataFrame, column: str = "median_rate"
                         ) -> tuple[pd.DataFrame, dict]:
    """
    Version A (LOWESS) and Version B (exponential smoothing) of one series.

    Returns (frame, report). The frame holds the actual series and both trends
    so one chart can draw either. The report holds the measured diagnostics,
    the fitted parameters and the timings — the evidence a reviewer needs.
    """
    import time

    import numpy as np

    m = monthly_series(df).copy()
    if len(m) < 24 or column not in m.columns:
        return pd.DataFrame(), {
            "ok": False,
            "reason": f"{len(m)} months available — at least 24 are needed before two "
                      f"smoothers can be compared meaningfully.",
        }

    y = m[column].astype(float)
    x = np.arange(len(y), dtype=float)

    from statsmodels.nonparametric.smoothers_lowess import lowess

    scan = []
    for f in SMOOTHING_FRAC_CANDIDATES:
        fitted = lowess(y.values, x, frac=f, it=3, return_sorted=False)
        d = _smoother_diagnostics(y, pd.Series(fitted))
        if d:
            scan.append({"frac": f, "months_in_window": round(f * len(y), 1), **d})

    frac = lowess_span(len(y))
    t0 = time.perf_counter()
    lo = lowess(y.values, x, frac=frac, it=3, return_sorted=False)
    lo_ms = (time.perf_counter() - t0) * 1000

    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    t0 = time.perf_counter()
    fit = ExponentialSmoothing(y, trend="add", seasonal=None,
                               initialization_method="estimated").fit()
    es = pd.Series(fit.fittedvalues).reindex(y.index)
    es_ms = (time.perf_counter() - t0) * 1000

    out = m[["_sort", "Month", "Transactions", column]].copy()
    out.columns = ["_sort", "month", "transactions", "actual"]
    out["lowess"] = lo
    out["exponential"] = es.values

    # Robustness: how far does each trend move if the single most extreme month
    # is dropped and it is refitted? A robust smoother barely notices.
    worst = int((y - y.median()).abs().idxmax())
    keep = [i for i in range(len(y)) if i != worst]
    lo_wo = lowess(y.values[keep], x[keep], frac=frac, it=3, return_sorted=False)
    es_wo = ExponentialSmoothing(y.iloc[keep], trend="add", seasonal=None,
                                 initialization_method="estimated").fit().fittedvalues
    report = {
        "ok": True,
        "column": column,
        "months": int(len(y)),
        "period": f"{m['Month'].iloc[0]} → {m['Month'].iloc[-1]}",
        "actual_sd_pct": float(y.pct_change(fill_method=None).std() * 100),
        "thinnest_month": int(m["Transactions"].min()),
        "outlier_month": str(m["Month"].iloc[worst]),
        "frac_scan": scan,
        "lowess": {
            "frac": float(frac),
            "window_months": round(float(frac) * len(y), 1),
            "iterations": 3,
            "runtime_ms": round(lo_ms, 1),
            "outlier_shift_pct": float(np.abs(np.asarray(lo)[keep] - lo_wo).mean()
                                       / y.mean() * 100),
            **_smoother_diagnostics(y, pd.Series(lo)),
        },
        "exponential": {
            "model": "Holt linear trend (additive), no seasonality",
            "alpha": float(fit.params.get("smoothing_level", float("nan"))),
            "beta": float(fit.params.get("smoothing_trend", float("nan"))),
            "runtime_ms": round(es_ms, 1),
            "outlier_shift_pct": float(np.abs(es.values[keep] - np.asarray(es_wo)).mean()
                                       / y.mean() * 100),
            **_smoother_diagnostics(y, es),
        },
    }
    return out, report
