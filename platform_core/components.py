"""
Shared presentation components for the platform shell.

These render the NEW global UI only (hero, region cards, breadcrumbs, headers,
explainer notes, platform map). They never touch analytical output.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st


def _clean(html: str) -> str:
    """Collapse whitespace so Streamlit's markdown parser cannot split the block."""
    return " ".join(html.split())


# ─────────────────────────────────────────────────────────────────────────────
# BASIC BLOCKS
# ─────────────────────────────────────────────────────────────────────────────


def breadcrumb(*crumbs: str) -> None:
    """
    Render a small 'you are here' trail above the page content.

    The first crumb is the company name and is marked `brand`, which exempts it
    from the trail's small-caps styling (see `.uae-topbar .brand`). Everything
    after it — "Locations", "Abu Dhabi", "Forecast" — keeps the uppercase look
    the header was designed with.
    """
    parts = []
    last = len(crumbs) - 1
    for i, crumb in enumerate(crumbs):
        cls = " ".join(c for c in ("brand" if i == 0 else "",
                                   "here" if i == last else "") if c)
        if i:
            parts.append('<span class="sep">›</span>')
        parts.append(f'<span class="{cls}">{crumb}</span>')
    st.markdown(_clean(f'<div class="uae-topbar">{"".join(parts)}</div>'), unsafe_allow_html=True)


def section(title: str, subtitle: str = "", icon: str = "◆") -> None:
    """Platform-level section header (distinct from the regions' own headers)."""
    sub = f'<p class="uae-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        _clean(
            f'<div class="uae-section"><div class="uae-section-ic">{icon}</div>'
            f'<div><div class="uae-h2">{title}</div>{sub}</div></div>'
        ),
        unsafe_allow_html=True,
    )


def note(text: str, icon: str = "💡") -> None:
    """Short 'what is this?' explainer. Kept deliberately brief."""
    st.markdown(
        _clean(f'<div class="uae-note"><span class="ic">{icon}</span><p>{text}</p></div>'),
        unsafe_allow_html=True,
    )


def stat_strip(items: list[tuple[str, str]]) -> None:
    """items = [(value, label), ...]"""
    cells = "".join(
        f'<div class="uae-stat uae-d{min(i + 1, 6)}">'
        f'<div class="uae-stat-value">{v}</div>'
        f'<div class="uae-stat-label">{l}</div></div>'
        for i, (v, l) in enumerate(items)
    )
    st.markdown(_clean(f'<div class="uae-stats">{cells}</div>'), unsafe_allow_html=True)


def tile(icon: str, title: str, text: str, delay: int = 1) -> None:
    st.markdown(
        _clean(
            f'<div class="uae-tile uae-d{min(delay, 6)}">'
            f'<div class="uae-tile-icon">{icon}</div>'
            f'<p class="uae-tile-title">{title}</p>'
            f'<p class="uae-tile-text">{text}</p></div>'
        ),
        unsafe_allow_html=True,
    )


def directory_row(icon: str, title: str, text: str, badge: str = "", accent: str = "#2563EB",
                  accent_soft: str = "rgba(37,99,235,0.10)", delay: int = 1) -> None:
    """A single row in a section directory (used by the region landing views)."""
    badge_html = f'<span class="uae-row-badge">{badge}</span>' if badge else ""
    st.markdown(
        _clean(
            f'<div class="uae-row uae-d{min(delay, 6)}" style="--rc:{accent};--rcs:{accent_soft}">'
            f'<div class="uae-row-ic">{icon}</div>'
            f'<div><p class="uae-row-title">{title}{badge_html}</p>'
            f'<p class="uae-row-text">{text}</p></div></div>'
        ),
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HERO / REGION HEADER
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# BRAND
# ─────────────────────────────────────────────────────────────────────────────

_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "truestates_logo.png"


@lru_cache(maxsize=1)
def _logo_data_uri() -> str:
    """
    The TruEstates.ai mark as a base64 data URI.

    Inlined rather than served as a static file because Streamlit's static
    file serving is disabled by default, and a broken <img> on the opening
    page is worse than a slightly larger stylesheet. Cached so the file is
    read once per process.
    """
    try:
        raw = _LOGO_PATH.read_bytes()
    except OSError:
        return ""
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def brand_mark(width: int = 210, align: str = "left", caption: str = "") -> None:
    """
    The company mark. Renders nothing at all if the asset is missing, so a
    lost file can never break a page.
    """
    uri = _logo_data_uri()
    if not uri:
        return
    just = {"left": "flex-start", "center": "center", "right": "flex-end"}.get(align, "flex-start")
    cap = (f'<p style="margin:.5rem 0 0 0;font-size:.76rem;letter-spacing:.04em;'
           f'color:var(--uae-text-muted)">{caption}</p>') if caption else ""
    st.markdown(
        _clean(
            f'<div style="display:flex;flex-direction:column;align-items:{just};'
            f'margin:.2rem 0 1.15rem 0">'
            f'<img src="{uri}" alt="TruEstates.ai" style="width:{width}px;height:auto;'
            f'border-radius:12px;display:block">{cap}</div>'
        ),
        unsafe_allow_html=True,
    )



def hero(eyebrow: str, title_html: str, lede: str) -> None:
    st.markdown(
        _clean(
            f'<div class="uae-d1" style="animation:uae-fade-up .55s var(--uae-ease) both">'
            f'<div class="uae-eyebrow">{eyebrow}</div>'
            f'<h1 class="uae-display">{title_html}</h1>'
            f'<p class="uae-lede">{lede}</p></div>'
        ),
        unsafe_allow_html=True,
    )


def region_header(region: dict, chips: list[str] | None = None) -> None:
    """
    The persistent regional banner. Confirms WHERE the user is at all times,
    and keeps the unified shell visible above the existing dashboard.
    """
    chip_html = "".join(
        f'<span class="uae-chip"><span class="dot"></span>{c}</span>' for c in (chips or [])
    )
    st.markdown(
        _clean(
            f'<div class="uae-region-header" style="--rc:{region["accent"]};--rcs:{region["accent_soft"]}">'
            f'<div class="uae-region-flag">{region["flag"]}</div>'
            f'<div><h2 class="uae-region-title">{region["name"].upper()}</h2>'
            f'<p class="uae-region-sub">{region["subtitle"]}</p></div>'
            f'<div class="uae-region-spacer"></div>'
            f'<div style="display:flex;gap:.4rem;flex-wrap:wrap">{chip_html}</div>'
            f"</div>"
        ),
        unsafe_allow_html=True,
    )


def region_card(region: dict, delay: int = 1) -> None:
    """
    Landing-page card for one region.

    The card is rendered with a square bottom edge so the real Streamlit button
    placed directly beneath it reads as the card's own "Explore Analytics"
    footer — a single object, not a card plus a stray button.
    """
    tags = "".join(f'<span class="uae-rc-tag">{h}</span>' for h in region["highlights"])
    st.markdown(
        _clean(
            f'<div class="uae-region-card uae-d{delay}" '
            f'style="--rc:{region["accent"]};--rcs:{region["accent_soft"]};'
            f'border-radius:20px 20px 0 0;padding-bottom:1.15rem">'
            f'<div class="uae-rc-flag">{region["flag"]}</div>'
            f'<h3 class="uae-rc-name">{region["name"].upper()}</h3>'
            f'<p class="uae-rc-kicker">{region.get("kicker", "Real Estate Analytics")}</p>'
            f'<p class="uae-rc-desc">{region["description"]}</p>'
            f'<div class="uae-rc-tags" style="margin-bottom:.15rem">{tags}</div>'
            f"</div>"
        ),
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM MAP
# ─────────────────────────────────────────────────────────────────────────────


def platform_map(branches: list[dict]) -> None:
    """
    A compact tree of the whole platform:

                  TruEstates analytics
              ┌───────────────┼───────────────┐
          Abu Dhabi         Dubai       Experimental
              │               │               │
           sections       sections       generations

    Each branch is {"title", "subtitle", "accent", "soft", "leaves"} where
    leaves is a list of (badge, label) pairs.
    """

    def _leaves(items, accent, soft):
        return "".join(
            f'<div class="uae-leaf uae-d{min(i + 1, 6)}" style="--rc:{accent};--rcs:{soft}">'
            + (f'<span class="lbadge">{b}</span>' if b else "")
            + f"{label}</div>"
            for i, (b, label) in enumerate(items)
        )

    cols = "".join(
        f'<div style="display:flex;flex-direction:column;align-items:center;'
        f'max-width:330px;min-width:210px">'
        f'<div class="uae-node region" style="border-color:{b["accent"]}">'
        f'<span class="n-title">{b["title"]}</span>'
        f'<span class="n-sub">{b["subtitle"]}</span></div>'
        f'<div class="uae-leafs">{_leaves(b["leaves"], b["accent"], b["soft"])}</div>'
        f"</div>"
        for b in branches
    )

    html = f"""
    <div class="uae-map">
      <div class="uae-map-root">
        <div class="uae-node root">
          <span class="n-title">TruEstates analytics</span>
          <span class="n-sub">TruEstates platform shell</span>
        </div>
      </div>
      <div class="uae-connector"></div>
      <div class="uae-branch">{cols}</div>
    </div>
    """
    st.markdown(_clean(html), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────


def footer(version: str, context: str = "") -> None:
    ctx = f" &nbsp;·&nbsp; {context}" if context else ""
    st.markdown(
        _clean(
            f'<div class="uae-footer">'
            f"<div><b>TruEstates analytics</b> &nbsp;·&nbsp; Abu Dhabi &amp; Dubai{ctx}</div>"
            f"<div>Streamlit + Plotly &nbsp;·&nbsp; v{version} &nbsp;·&nbsp; "
            f"Analytical &amp; informational use only</div>"
            f"</div>"
        ),
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# REGIONAL DASHBOARD PRIMITIVES
# (used by platform-authored regional dashboards — currently Dubai)
# ─────────────────────────────────────────────────────────────────────────────


def kpi_card(label: str, value: str, icon: str = "📊", color: str = "blue",
             tooltip: str | None = None) -> str:
    """Return HTML for one KPI card. Mirrors the Abu Dhabi card language."""
    tip = f' title="{tooltip}"' if tooltip else ""
    return _clean(
        f'<div class="uae-kpi {color}"{tip}>'
        f'<div class="uae-kpi-ic">{icon}</div>'
        f'<div class="uae-kpi-label">{label}</div>'
        f'<div class="uae-kpi-value">{value}</div>'
        f"</div>"
    )


def kpi_grid(cards: list[dict], per_row: int = 4) -> None:
    """Render KPI cards in rows of `per_row`."""
    import streamlit as _st

    for start in range(0, len(cards), per_row):
        cols = _st.columns(per_row, gap="medium")
        for i, col in enumerate(cols):
            idx = start + i
            if idx >= len(cards):
                continue
            k = cards[idx]
            with col:
                _st.markdown(
                    kpi_card(k["label"], k["value"], k.get("icon", "📊"),
                             k.get("color_class", "blue"), k.get("tooltip")),
                    unsafe_allow_html=True,
                )
        _st.markdown("<div style='height:0.85rem'></div>", unsafe_allow_html=True)


def insight_row(emoji: str, html: str) -> None:
    st.markdown(
        _clean(f'<div class="uae-insight"><span class="em">{emoji}</span><p>{html}</p></div>'),
        unsafe_allow_html=True,
    )


def block(title: str, subtitle: str = "", icon: str = "▪") -> None:
    """Sub-section heading inside a regional dashboard."""
    sub = f'<p class="uae-block-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        _clean(
            f'<div class="uae-block"><div class="uae-block-ic">{icon}</div>'
            f'<div><p class="uae-block-title">{title}</p>{sub}</div></div>'
        ),
        unsafe_allow_html=True,
    )


def chart_note(text: str) -> None:
    """One-line plain-English reading of the chart above it."""
    st.markdown(f'<p class="uae-chart-note">{text}</p>', unsafe_allow_html=True)


def divider_label(text: str) -> None:
    st.markdown(f'<div class="uae-divider-label">{text}</div>', unsafe_allow_html=True)
