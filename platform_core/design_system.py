"""
Global design system for the unified platform.

One brand, two regions.

The palette is deliberately built on the same token family the Abu Dhabi
dashboard already uses (blue-600 / teal-600 on a slate neutral ramp, Inter
typeface) so the platform shell and the regional dashboards read as a single
product rather than two applications side by side.

Two CSS payloads are exposed:

  build_platform_css(dark)   → injected FIRST, before any region code runs.
  build_shell_lock_css(dark) → injected LAST, after region code has run.

The second payload exists because the regional dashboards inject their own
full-page stylesheets. In CSS, later rules of equal specificity win, so the
shell re-asserts ownership of the global chrome (sidebar, brand, navigation)
at the end of the script run. Region content styling is left untouched.
"""

# ─────────────────────────────────────────────────────────────────────────────
# TOKENS
# ─────────────────────────────────────────────────────────────────────────────

# The sidebar is intentionally dark in BOTH themes. It now carries the
# TruEstates ground colour, so the rail reads as the brand and the workspace
# reads as the document sitting on it.
SIDEBAR_BG = "linear-gradient(180deg, #0C0C0D 0%, #131211 55%, #0A0A0B 100%)"
SIDEBAR_TEXT = "#D6D0C8"
SIDEBAR_MUTED = "#8C857C"
SIDEBAR_GROUP = "#786F64"
SIDEBAR_BORDER = "rgba(201, 151, 63, 0.14)"
SIDEBAR_HOVER = "rgba(201, 151, 63, 0.09)"
SIDEBAR_ACTIVE_BG = "rgba(184, 115, 27, 0.20)"
SIDEBAR_ACTIVE_TEXT = "#FFFFFF"
SIDEBAR_ACTIVE_BAR = "#C9973F"

# ── Brand ────────────────────────────────────────────────────────────────────
# The palette is taken from the TruEstates.ai mark: a near-black ground with a
# bronze accent. The values below are the actual colours sampled from the logo,
# not approximations — #0A0A0B is 78% of its pixels and #B8731B is the accent
# on the wordmark and the bar-chart glyph.
#
# These drive the PLATFORM CHROME only — rail, cards, headers, buttons, hero.
# The analytical chart palette lives in platform_core/chart_theme.py and is
# deliberately left alone: recolouring the charts would change every figure the
# regression suite fingerprints, and categorical series need hues chosen for
# separability rather than for brand.
BRAND_INK = "#0A0A0B"        # logo ground
BRAND_BRONZE = "#B8731B"     # logo accent
BRAND_GOLD = "#C9973F"       # lighter bronze, for hover and highlights
BRAND_SAND = "#977349"       # muted metallic, for secondary strokes

BRAND_BLUE = BRAND_BRONZE    # every chrome reference to "brand" resolves here
BRAND_TEAL = "#0D9488"
BRAND_SKY = BRAND_GOLD


def tokens(dark: bool = False) -> dict:
    """Return the workspace (main content area) token set."""
    if dark:
        return dict(
            app_bg="#0A0A0B",
            surface="#151517",
            surface_alt="#101012",
            border="#2C2620",
            text="#F5F3F0",
            text_soft="#C6C1BA",
            text_muted="#8C857C",
            accent=BRAND_BRONZE,
            accent_soft="rgba(184,115,27,0.16)",
            teal=BRAND_TEAL,
            shadow="0 1px 3px rgba(0,0,0,0.6), 0 10px 28px rgba(0,0,0,0.45)",
            shadow_hover="0 6px 34px rgba(184,115,27,0.26), 0 2px 8px rgba(0,0,0,0.55)",
            hero_bg="linear-gradient(135deg, #17120A 0%, #0A0A0B 58%, #12100C 100%)",
            hero_border="rgba(184,115,27,0.30)",
            grid="rgba(201,151,63,0.08)",
        )
    return dict(
        app_bg="#FAF8F5",
        surface="#FFFFFF",
        surface_alt="#FBF9F6",
        border="#E9E3DA",
        text="#14120F",
        text_soft="#544E45",
        text_muted="#8C857C",
        accent=BRAND_BRONZE,
        accent_soft="#FBF3E7",
        teal=BRAND_TEAL,
        shadow="0 1px 2px rgba(20,18,15,0.05), 0 8px 24px rgba(20,18,15,0.05)",
        shadow_hover="0 10px 34px rgba(184,115,27,0.16), 0 2px 6px rgba(20,18,15,0.06)",
        hero_bg="linear-gradient(135deg, #FDF6EA 0%, #FBF9F6 55%, #F5F1EA 100%)",
        hero_border="#EFE2CE",
        grid="rgba(20,18,15,0.05)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN STYLESHEET
# ─────────────────────────────────────────────────────────────────────────────


def _dark_content_layer(t: dict, dark: bool) -> str:
    """Base text/surface rules so region content stays readable in dark mode."""
    if not dark:
        return "/* light mode — regions style themselves */"
    return f"""
[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3,
[data-testid="stMainBlockContainer"] h4,
[data-testid="stMainBlockContainer"] h5,
[data-testid="stMainBlockContainer"] h6 {{ color: {t['text']}; }}

[data-testid="stMainBlockContainer"] p,
[data-testid="stMainBlockContainer"] li,
[data-testid="stMainBlockContainer"] label,
[data-testid="stMainBlockContainer"] .stMarkdown,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] {{
  color: {t['text_soft']};
}}
[data-testid="stMainBlockContainer"] strong,
[data-testid="stMainBlockContainer"] b {{ color: {t['text']}; }}
[data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"],
[data-testid="stMainBlockContainer"] small {{ color: {t['text_muted']}; }}

/* Markdown tables written by the regions */
[data-testid="stMainBlockContainer"] table {{ color: {t['text_soft']}; }}
[data-testid="stMainBlockContainer"] th {{
  color: {t['text']}; border-color: {t['border']};
}}
[data-testid="stMainBlockContainer"] td {{ border-color: {t['border']}; }}

/* Tabs */
[data-testid="stMainBlockContainer"] [data-baseweb="tab"] {{ color: {t['text_muted']}; }}
[data-testid="stMainBlockContainer"] [data-baseweb="tab"][aria-selected="true"] {{
  color: {t['accent']};
}}
[data-testid="stMainBlockContainer"] [data-baseweb="tab-list"] {{
  border-bottom-color: {t['border']};
}}

/* Expanders */
[data-testid="stMainBlockContainer"] [data-testid="stExpander"] details {{
  background: {t['surface']}; border-color: {t['border']};
}}
[data-testid="stMainBlockContainer"] [data-testid="stExpander"] summary,
[data-testid="stMainBlockContainer"] [data-testid="stExpander"] summary * {{
  color: {t['text']};
}}

/* Metrics, code blocks, inputs */
[data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"] * {{ color: {t['text_muted']}; }}
[data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] {{ color: {t['text']}; }}
[data-testid="stMainBlockContainer"] pre,
[data-testid="stMainBlockContainer"] code {{
  background: {t['surface_alt']} !important; color: {t['text_soft']} !important;
}}
[data-testid="stMainBlockContainer"] [data-baseweb="select"] > div,
[data-testid="stMainBlockContainer"] [data-baseweb="input"] > div {{
  background: {t['surface']}; border-color: {t['border']}; color: {t['text']};
}}
[data-testid="stMainBlockContainer"] [data-baseweb="select"] div {{ color: {t['text']}; }}
"""


def build_platform_css(dark: bool = False) -> str:
    t = tokens(dark)
    dark_content = _dark_content_layer(t, dark)

    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ══════════════════════════════════════════════════════════════════════════
   1. TOKENS
══════════════════════════════════════════════════════════════════════════ */
:root {{
  --uae-accent: {t['accent']};
  --uae-teal: {t['teal']};
  --uae-surface: {t['surface']};
  --uae-surface-alt: {t['surface_alt']};
  --uae-border: {t['border']};
  --uae-text: {t['text']};
  --uae-text-soft: {t['text_soft']};
  --uae-text-muted: {t['text_muted']};
  --uae-shadow: {t['shadow']};
  --uae-shadow-hover: {t['shadow_hover']};

  /* spacing scale */
  --uae-s1: 0.25rem; --uae-s2: 0.5rem;  --uae-s3: 0.75rem;
  --uae-s4: 1rem;    --uae-s5: 1.5rem;  --uae-s6: 2rem;
  --uae-s7: 3rem;    --uae-s8: 4rem;

  --uae-radius-sm: 8px;
  --uae-radius: 14px;
  --uae-radius-lg: 20px;

  --uae-ease: cubic-bezier(0.22, 1, 0.36, 1);
}}

/* ══════════════════════════════════════════════════════════════════════════
   2. BASE / WORKSPACE
══════════════════════════════════════════════════════════════════════════ */
html, body, .stApp, [class*="css"] {{
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
}}

.stApp {{ background: {t['app_bg']}; }}

#MainMenu, footer {{ visibility: hidden; }}
[data-testid="stHeader"] {{ background: transparent; }}

.main .block-container,
[data-testid="stMainBlockContainer"] {{
  padding: 1.35rem 2.25rem 4rem 2.25rem;
  max-width: 1560px;
}}

/* ══════════════════════════════════════════════════════════════════════════
   3. TYPOGRAPHY HIERARCHY
══════════════════════════════════════════════════════════════════════════ */
.uae-display {{
  font-size: clamp(2.1rem, 4.4vw, 3.4rem);
  line-height: 1.06;
  letter-spacing: -0.032em;
  font-weight: 800;
  color: {t['text']};
  margin: 0 0 0.6rem 0;
}}
.uae-display .accent {{
  background: linear-gradient(120deg, {BRAND_BLUE} 0%, {BRAND_TEAL} 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}}
.uae-lede {{
  font-size: 1.02rem; line-height: 1.68; font-weight: 400;
  color: {t['text_soft']}; max-width: 62ch; margin: 0;
}}
.uae-eyebrow {{
  display: inline-flex; align-items: center; gap: 0.5rem;
  font-size: 0.68rem; font-weight: 700; letter-spacing: 0.14em;
  text-transform: uppercase; color: {t['accent']};
  background: {t['accent_soft']};
  border: 1px solid {t['border']};
  padding: 0.36rem 0.8rem; border-radius: 999px; margin-bottom: 1.05rem;
}}
.uae-h2 {{
  font-size: 1.28rem; font-weight: 700; letter-spacing: -0.015em;
  color: {t['text']}; margin: 0 0 0.25rem 0;
}}
.uae-h3 {{
  font-size: 0.95rem; font-weight: 700; color: {t['text']};
  margin: 0 0 0.2rem 0;
}}
.uae-sub {{
  font-size: 0.85rem; color: {t['text_muted']}; margin: 0; line-height: 1.6;
}}

/* ══════════════════════════════════════════════════════════════════════════
   4. PLATFORM HEADER (region banner + breadcrumb)
══════════════════════════════════════════════════════════════════════════ */
.uae-topbar {{
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.74rem; font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase; color: {t['text_muted']};
  margin-bottom: 0.85rem;
}}
.uae-topbar .sep {{ opacity: 0.45; }}
.uae-topbar .here {{ color: {t['accent']}; }}
/* The company name is a name, not a label, so it keeps the capitalisation it
   is written with. The rest of the trail ("Locations", "Abu Dhabi") stays in
   the small-caps style this header was designed around. Without this rule the
   breadcrumb rendered the brand as TruEstates analytics on every page — the
   string was already correct, the stylesheet was shouting it. */
.uae-topbar .brand {{ text-transform: none; letter-spacing: 0.02em; }}

.uae-region-header {{
  position: relative; overflow: hidden;
  display: flex; align-items: center; gap: 1.15rem; flex-wrap: wrap;
  background: {t['surface']};
  border: 1px solid {t['border']};
  border-radius: var(--uae-radius-lg);
  padding: 1.35rem 1.6rem;
  margin-bottom: 1.35rem;
  box-shadow: {t['shadow']};
  animation: uae-fade-up 0.5s var(--uae-ease) both;
}}
.uae-region-header::before {{
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 5px;
  background: linear-gradient(180deg, var(--rc, {BRAND_BLUE}), transparent 130%);
}}
.uae-region-flag {{
  width: 58px; height: 58px; flex: none;
  display: grid; place-items: center; font-size: 1.85rem;
  border-radius: 16px;
  background: var(--rcs, {t['accent_soft']});
  border: 1px solid {t['border']};
}}
.uae-region-title {{
  font-size: 1.55rem; font-weight: 800; letter-spacing: -0.022em;
  color: {t['text']}; margin: 0; line-height: 1.15;
}}
.uae-region-sub {{
  font-size: 0.86rem; color: {t['text_muted']}; margin: 0.18rem 0 0 0;
}}
.uae-region-spacer {{ flex: 1 1 auto; }}
.uae-chip {{
  display: inline-flex; align-items: center; gap: 0.38rem;
  font-size: 0.7rem; font-weight: 600; letter-spacing: 0.04em;
  color: {t['text_soft']};
  background: {t['surface_alt']};
  border: 1px solid {t['border']};
  border-radius: 999px; padding: 0.32rem 0.72rem; white-space: nowrap;
}}
.uae-chip .dot {{
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--rc, {BRAND_BLUE});
  box-shadow: 0 0 0 3px var(--rcs, {t['accent_soft']});
}}

/* ══════════════════════════════════════════════════════════════════════════
   5. CARDS
══════════════════════════════════════════════════════════════════════════ */
.uae-card {{
  background: {t['surface']};
  border: 1px solid {t['border']};
  border-radius: var(--uae-radius);
  padding: 1.25rem 1.35rem;
  box-shadow: {t['shadow']};
  height: 100%;
}}

/* Region cards on the landing page */
.uae-region-card {{
  position: relative; overflow: hidden;
  display: block; height: 100%;
  background: {t['surface']};
  border: 1px solid {t['border']};
  border-radius: var(--uae-radius-lg);
  padding: 1.6rem 1.65rem 1.4rem 1.65rem;
  box-shadow: {t['shadow']};
  transition: transform 0.34s var(--uae-ease), box-shadow 0.34s var(--uae-ease),
              border-color 0.34s var(--uae-ease);
  animation: uae-fade-up 0.55s var(--uae-ease) both;
}}
.uae-region-card::after {{
  content: ""; position: absolute; inset: 0;
  background: radial-gradient(560px circle at 88% -18%, var(--rcs, {t['accent_soft']}), transparent 62%);
  opacity: 0.85; pointer-events: none;
}}
.uae-region-card > * {{ position: relative; z-index: 1; }}
.uae-region-card:hover {{
  transform: translateY(-5px);
  box-shadow: {t['shadow_hover']};
  border-color: var(--rc, {BRAND_BLUE});
}}
.uae-region-card:hover .uae-rc-cta {{ gap: 0.7rem; color: var(--rc, {BRAND_BLUE}); }}
.uae-region-card:hover .uae-rc-cta .arrow {{ transform: translateX(3px); }}

.uae-rc-flag {{
  width: 54px; height: 54px; display: grid; place-items: center;
  font-size: 1.7rem; border-radius: 15px;
  background: var(--rcs, {t['accent_soft']});
  border: 1px solid {t['border']};
  margin-bottom: 1rem;
}}
.uae-rc-name {{
  font-size: 1.42rem; font-weight: 800; letter-spacing: -0.02em;
  color: {t['text']}; margin: 0; line-height: 1.1;
}}
.uae-rc-kicker {{
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.13em;
  text-transform: uppercase; color: var(--rc, {BRAND_BLUE});
  margin: 0.4rem 0 0.75rem 0;
}}
.uae-rc-desc {{
  font-size: 0.855rem; line-height: 1.66; color: {t['text_soft']};
  margin: 0 0 1.05rem 0; min-height: 5.4rem;
}}
.uae-rc-tags {{
  display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1.15rem;
  /* reserve two rows so both region cards end at the same height and their
     attached CTA buttons line up */
  min-height: 3.55rem; align-content: flex-start;
}}
.uae-rc-tag {{
  font-size: 0.685rem; font-weight: 600; color: {t['text_soft']};
  background: {t['surface_alt']}; border: 1px solid {t['border']};
  border-radius: 7px; padding: 0.25rem 0.55rem;
}}
.uae-rc-cta {{
  display: inline-flex; align-items: center; gap: 0.42rem;
  font-size: 0.85rem; font-weight: 700; color: {t['text_soft']};
  transition: gap 0.28s var(--uae-ease), color 0.28s var(--uae-ease);
}}
.uae-rc-cta .arrow {{ transition: transform 0.28s var(--uae-ease); display: inline-block; }}

/* Feature / capability tiles */
.uae-tile {{
  background: {t['surface']};
  border: 1px solid {t['border']};
  border-radius: var(--uae-radius);
  padding: 1.05rem 1.15rem;
  height: 100%;
  transition: transform 0.28s var(--uae-ease), box-shadow 0.28s var(--uae-ease),
              border-color 0.28s var(--uae-ease);
  animation: uae-fade-up 0.5s var(--uae-ease) both;
}}
.uae-tile:hover {{
  transform: translateY(-3px);
  box-shadow: {t['shadow_hover']};
  border-color: {t['accent']};
}}
.uae-tile-icon {{
  width: 38px; height: 38px; display: grid; place-items: center;
  border-radius: 11px; font-size: 1.1rem; margin-bottom: 0.7rem;
  background: {t['accent_soft']}; border: 1px solid {t['border']};
}}
.uae-tile-title {{ font-size: 0.9rem; font-weight: 700; color: {t['text']}; margin: 0 0 0.22rem 0; }}
.uae-tile-text {{ font-size: 0.79rem; line-height: 1.62; color: {t['text_muted']}; margin: 0; }}

/* Stat strip */
.uae-stats {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
  gap: 0.9rem; margin: 1.4rem 0 0 0;
}}
.uae-stat {{
  background: {t['surface']}; border: 1px solid {t['border']};
  border-radius: var(--uae-radius); padding: 0.95rem 1.05rem;
  animation: uae-fade-up 0.5s var(--uae-ease) both;
}}
.uae-stat-value {{
  font-size: 1.42rem; font-weight: 800; letter-spacing: -0.02em;
  color: {t['text']}; line-height: 1.1;
}}
.uae-stat-label {{
  font-size: 0.7rem; font-weight: 600; letter-spacing: 0.07em;
  text-transform: uppercase; color: {t['text_muted']}; margin-top: 0.25rem;
}}

/* Info / explainer boxes */
.uae-note {{
  display: flex; gap: 0.75rem; align-items: flex-start;
  background: {t['accent_soft']};
  border: 1px solid {t['border']};
  border-left: 3px solid {t['accent']};
  border-radius: var(--uae-radius-sm);
  padding: 0.8rem 1rem; margin: 0.6rem 0 1.15rem 0;
}}
.uae-note .ic {{ font-size: 0.95rem; line-height: 1.5; }}
.uae-note p {{ margin: 0; font-size: 0.83rem; line-height: 1.65; color: {t['text_soft']}; }}
.uae-note b {{ color: {t['text']}; }}

/* Section header inside platform pages */
.uae-section {{
  display: flex; align-items: center; gap: 0.8rem;
  margin: 2.1rem 0 1.05rem 0;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid {t['border']};
}}
.uae-section-ic {{
  width: 34px; height: 34px; flex: none; display: grid; place-items: center;
  border-radius: 10px; font-size: 1rem;
  background: {t['accent_soft']}; border: 1px solid {t['border']};
}}

/* ══════════════════════════════════════════════════════════════════════════
   5b. REGIONAL DASHBOARD PRIMITIVES
   KPI cards, insight rows and chart notes for platform-authored regional
   dashboards (currently Dubai). Deliberately mirrors the Abu Dhabi component
   language so the two regions read as one product. Abu Dhabi keeps its own
   classes; nothing here overrides them.
══════════════════════════════════════════════════════════════════════════ */
.uae-kpi {{
  position: relative; overflow: hidden; height: 100%; min-height: 132px;
  background: {t['surface']};
  border: 1px solid {t['border']};
  border-radius: 12px;
  padding: 1.2rem 1.3rem;
  box-shadow: {t['shadow']};
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  animation: uae-fade-up 0.45s var(--uae-ease) both;
}}
.uae-kpi:hover {{
  transform: translateY(-3px);
  box-shadow: {t['shadow_hover']};
  border-color: {t['accent']};
}}
.uae-kpi::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  border-radius: 12px 12px 0 0;
  background: linear-gradient(90deg, {BRAND_BLUE}, #60A5FA);
}}
.uae-kpi.teal::before   {{ background: linear-gradient(90deg, #0D9488, #2DD4BF); }}
.uae-kpi.amber::before  {{ background: linear-gradient(90deg, #D97706, #FCD34D); }}
.uae-kpi.green::before  {{ background: linear-gradient(90deg, #059669, #34D399); }}
.uae-kpi.violet::before {{ background: linear-gradient(90deg, #7C3AED, #A78BFA); }}
.uae-kpi.rose::before   {{ background: linear-gradient(90deg, #E11D48, #FB7185); }}
.uae-kpi.sky::before    {{ background: linear-gradient(90deg, #0284C7, #38BDF8); }}

.uae-kpi-ic {{
  width: 40px; height: 40px; border-radius: 10px;
  display: grid; place-items: center; font-size: 1.2rem;
  margin-bottom: 0.9rem; background: {t['accent_soft']};
}}
.uae-kpi.teal   .uae-kpi-ic {{ background: rgba(13,148,136,0.10); }}
.uae-kpi.amber  .uae-kpi-ic {{ background: rgba(217,119,6,0.10); }}
.uae-kpi.green  .uae-kpi-ic {{ background: rgba(5,150,105,0.10); }}
.uae-kpi.violet .uae-kpi-ic {{ background: rgba(124,58,237,0.10); }}
.uae-kpi.rose   .uae-kpi-ic {{ background: rgba(225,29,72,0.09); }}
.uae-kpi.sky    .uae-kpi-ic {{ background: rgba(2,132,199,0.09); }}

.uae-kpi-label {{
  font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.1em; color: {t['text_muted']}; margin-bottom: 0.3rem;
}}
.uae-kpi-value {{
  font-size: 1.55rem; font-weight: 800; line-height: 1.1;
  letter-spacing: -0.01em; color: {t['text']};
}}

/* Insight row */
.uae-insight {{
  display: flex; gap: 0.85rem; align-items: flex-start;
  background: {t['accent_soft']};
  border: 1px solid {t['border']};
  border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.65rem;
  transition: transform 0.22s var(--uae-ease), border-color 0.22s var(--uae-ease);
  animation: uae-fade-up 0.45s var(--uae-ease) both;
}}
.uae-insight:hover {{ transform: translateX(3px); border-color: {t['accent']}; }}
.uae-insight .em {{ font-size: 1.05rem; line-height: 1.45; }}
.uae-insight p {{
  margin: 0; font-size: 0.855rem; line-height: 1.62; color: {t['text_soft']};
}}
.uae-insight .insight-highlight {{
  font-weight: 700; color: {t['accent']};
}}

/* Data-source badge next to a chart title */
.uae-src-badge {{
  display: inline-block; vertical-align: middle;
  font-size: 0.56rem; font-weight: 800; letter-spacing: 0.09em;
  border: 1px solid; border-radius: 5px;
  padding: 0.1rem 0.34rem; margin-left: 0.45rem;
  position: relative; top: -1px;
}}

/* The ⓘ control beside a chart title */
.stApp [data-testid="stPopover"] > button,
.stApp [data-testid="stPopoverButton"] {{
  border-radius: 999px !important;
  border: 1px solid {t['border']} !important;
  background: {t['surface']} !important;
  color: {t['text_muted']} !important;
  font-size: 0.9rem !important;
  min-height: 0 !important; padding: 0.2rem 0.5rem !important;
  transition: color 0.2s var(--uae-ease), border-color 0.2s var(--uae-ease),
              background 0.2s var(--uae-ease);
}}
.stApp [data-testid="stPopover"] > button:hover,
.stApp [data-testid="stPopoverButton"]:hover {{
  color: {t['accent']} !important;
  border-color: {t['accent']} !important;
  background: {t['accent_soft']} !important;
}}
.stApp [data-testid="stPopoverBody"] {{ max-height: 70vh; }}
.stApp [data-testid="stPopoverBody"] table {{ font-size: 0.78rem; }}
.stApp [data-testid="stPopoverBody"] li {{ font-size: 0.82rem; line-height: 1.6; }}

/* Chart note */
.uae-chart-note {{
  font-size: 0.78rem; line-height: 1.6; color: {t['text_muted']};
  border-left: 3px solid {t['accent']};
  padding: 0.15rem 0 0.15rem 0.7rem;
  margin: 0.35rem 0 1.4rem 0;
}}

/* Sub-section heading inside a regional dashboard */
.uae-block {{
  display: flex; align-items: center; gap: 0.7rem;
  margin: 1.7rem 0 0.9rem 0;
}}
.uae-block-ic {{
  width: 30px; height: 30px; flex: none; display: grid; place-items: center;
  border-radius: 9px; font-size: 0.92rem;
  background: {t['accent_soft']}; border: 1px solid {t['border']};
}}
.uae-block-title {{
  font-size: 1.06rem; font-weight: 700; color: {t['text']}; margin: 0; line-height: 1.2;
}}
.uae-block-sub {{ font-size: 0.79rem; color: {t['text_muted']}; margin: 0; }}

.uae-divider-label {{
  display: flex; align-items: center; gap: 0.75rem;
  margin: 2.1rem 0 0.9rem 0;
  font-size: 0.68rem; font-weight: 700; letter-spacing: 0.16em;
  text-transform: uppercase; color: {t['text_muted']};
}}
.uae-divider-label::after {{
  content: ""; flex: 1; height: 1px; background: {t['border']};
}}

/* ══════════════════════════════════════════════════════════════════════════
   6. PLATFORM MAP (Explore)
══════════════════════════════════════════════════════════════════════════ */
.uae-map {{
  background:
    linear-gradient({t['grid']} 1px, transparent 1px) 0 0 / 26px 26px,
    linear-gradient(90deg, {t['grid']} 1px, transparent 1px) 0 0 / 26px 26px,
    {t['surface']};
  border: 1px solid {t['border']};
  border-radius: var(--uae-radius-lg);
  padding: 1.7rem 1.2rem 1.9rem 1.2rem;
  box-shadow: {t['shadow']};
  overflow-x: auto;
}}
.uae-map-root {{ display: flex; justify-content: center; }}
.uae-node {{
  display: inline-flex; flex-direction: column; align-items: center;
  gap: 0.12rem; text-align: center;
  border-radius: 12px; padding: 0.6rem 1rem;
  border: 1px solid {t['border']}; background: {t['surface']};
  box-shadow: {t['shadow']};
  min-width: 132px;
}}
.uae-node .n-title {{ font-size: 0.83rem; font-weight: 700; color: {t['text']}; }}
.uae-node .n-sub {{ font-size: 0.68rem; color: {t['text_muted']}; }}
.uae-node.root {{ border-color: {t['accent']}; }}
.uae-node.region {{ border-width: 1.5px; }}
.uae-connector {{
  width: 2px; height: 26px; margin: 0 auto;
  background: linear-gradient(180deg, {t['border']}, {t['accent']});
  animation: uae-grow 0.6s var(--uae-ease) both;
}}
.uae-branch {{
  display: flex; justify-content: center; gap: 2.6rem; flex-wrap: wrap;
  position: relative; padding-top: 0.15rem;
}}
.uae-leafs {{ display: flex; flex-direction: column; gap: 0.42rem; margin-top: 0.75rem; }}
.uae-leaf {{
  font-size: 0.755rem; font-weight: 500; color: {t['text_soft']};
  background: {t['surface_alt']}; border: 1px solid {t['border']};
  border-radius: 8px; padding: 0.4rem 0.7rem; text-align: left;
  transition: transform 0.22s var(--uae-ease), border-color 0.22s var(--uae-ease),
              background 0.22s var(--uae-ease);
  animation: uae-fade-in 0.5s var(--uae-ease) both;
}}
.uae-leaf:hover {{
  transform: translateX(3px);
  border-color: var(--rc, {BRAND_BLUE});
  background: var(--rcs, {t['accent_soft']});
}}
.uae-leaf .lbadge {{
  display: inline-block; font-size: 0.6rem; font-weight: 700;
  letter-spacing: 0.06em; color: var(--rc, {BRAND_BLUE});
  border: 1px solid {t['border']}; border-radius: 5px;
  padding: 0.04rem 0.32rem; margin-right: 0.42rem;
}}

/* ══════════════════════════════════════════════════════════════════════════
   7. SECTION DIRECTORY ROWS (Dubai / Abu Dhabi section pickers)
══════════════════════════════════════════════════════════════════════════ */
.uae-row {{
  display: flex; gap: 0.95rem; align-items: flex-start;
  background: {t['surface']}; border: 1px solid {t['border']};
  border-radius: var(--uae-radius); padding: 0.95rem 1.1rem;
  margin-bottom: 0.6rem;
  transition: transform 0.24s var(--uae-ease), border-color 0.24s var(--uae-ease),
              box-shadow 0.24s var(--uae-ease);
  animation: uae-fade-up 0.45s var(--uae-ease) both;
}}
.uae-row:hover {{
  transform: translateX(3px); border-color: var(--rc, {BRAND_BLUE});
  box-shadow: {t['shadow_hover']};
}}
.uae-row-ic {{
  width: 36px; height: 36px; flex: none; display: grid; place-items: center;
  border-radius: 10px; font-size: 1rem;
  background: var(--rcs, {t['accent_soft']}); border: 1px solid {t['border']};
}}
.uae-row-title {{
  font-size: 0.9rem; font-weight: 700; color: {t['text']};
  display: flex; align-items: center; gap: 0.5rem; margin: 0 0 0.18rem 0;
}}
.uae-row-badge {{
  font-size: 0.6rem; font-weight: 700; letter-spacing: 0.07em;
  color: var(--rc, {BRAND_BLUE}); border: 1px solid {t['border']};
  background: {t['surface_alt']}; border-radius: 5px; padding: 0.08rem 0.36rem;
}}
.uae-row-text {{ font-size: 0.79rem; line-height: 1.6; color: {t['text_muted']}; margin: 0; }}

/* ══════════════════════════════════════════════════════════════════════════
   8. FOOTER
══════════════════════════════════════════════════════════════════════════ */
.uae-footer {{
  margin-top: 3rem; padding-top: 1.1rem;
  border-top: 1px solid {t['border']};
  display: flex; flex-wrap: wrap; gap: 0.6rem 1.2rem;
  align-items: center; justify-content: space-between;
  font-size: 0.73rem; color: {t['text_muted']};
}}
.uae-footer b {{ color: {t['text_soft']}; }}

/* ══════════════════════════════════════════════════════════════════════════
   9. ANIMATIONS  (purposeful only; disabled for reduced-motion users)
══════════════════════════════════════════════════════════════════════════ */
@keyframes uae-fade-up {{
  from {{ opacity: 0; transform: translateY(12px); }}
  to   {{ opacity: 1; transform: none; }}
}}
@keyframes uae-fade-in {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes uae-grow {{ from {{ transform: scaleY(0); transform-origin: top; }} to {{ transform: scaleY(1); }} }}
@keyframes uae-slide-in {{
  from {{ opacity: 0; transform: translateX(-8px); }}
  to   {{ opacity: 1; transform: none; }}
}}

.uae-d1 {{ animation-delay: 0.05s; }}
.uae-d2 {{ animation-delay: 0.11s; }}
.uae-d3 {{ animation-delay: 0.17s; }}
.uae-d4 {{ animation-delay: 0.23s; }}
.uae-d5 {{ animation-delay: 0.29s; }}
.uae-d6 {{ animation-delay: 0.35s; }}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }}
}}

/* ══════════════════════════════════════════════════════════════════════════
   9b. DARK-MODE CONTENT LAYER
   The Abu Dhabi dashboard ships its own dark stylesheet; the Dubai suite was
   only ever built for a light page. When the platform is in dark appearance
   the shell therefore supplies the base readability rules for standard
   Streamlit elements in the workspace — text colour and surfaces only. No
   chart, table or analytical output is altered.
══════════════════════════════════════════════════════════════════════════ */
{dark_content}

/* ══════════════════════════════════════════════════════════════════════════
   10. RESPONSIVE
══════════════════════════════════════════════════════════════════════════ */
@media (max-width: 1180px) {{
  .main .block-container,
  [data-testid="stMainBlockContainer"] {{ padding: 1.1rem 1.25rem 3rem 1.25rem; }}
  .uae-rc-desc {{ min-height: 0; }}
}}
@media (max-width: 820px) {{
  .uae-display {{ font-size: 1.95rem; }}
  .uae-region-header {{ padding: 1.05rem 1.1rem; gap: 0.85rem; }}
  .uae-region-flag {{ width: 46px; height: 46px; font-size: 1.4rem; }}
  .uae-region-title {{ font-size: 1.2rem; }}
  .uae-branch {{ gap: 1.1rem; }}
  .uae-footer {{ flex-direction: column; align-items: flex-start; }}
}}

/* Charts and tables must never overflow their container at any width */
[data-testid="stPlotlyChart"], .stPlotlyChart {{ max-width: 100%; }}
[data-testid="stDataFrame"] {{ width: 100%; }}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# SHELL LOCK — injected AFTER the regional app has written its own CSS
# ─────────────────────────────────────────────────────────────────────────────


def build_shell_lock_css(dark: bool = False) -> str:
    """
    Re-assert platform ownership of the global chrome.

    The regional dashboards inject full-page stylesheets that target
    `.stApp [data-testid="stSidebar"]`. This payload is emitted at the very end of the
    script run so the shell's navigation rail always wins the cascade, while
    everything inside the regions' own content area is left alone.
    """
    t = tokens(dark)

    return f"""
<style>
/* ── Navigation rail ─────────────────────────────────────────────────── */
.stApp [data-testid="stSidebar"] {{
  background: {SIDEBAR_BG} !important;
  border-right: 1px solid {SIDEBAR_BORDER} !important;
  box-shadow: 4px 0 24px rgba(2, 8, 20, 0.16) !important;
}}
.stApp [data-testid="stSidebar"] > div:first-child {{ padding-top: 0.5rem !important; }}
[data-testid="stSidebarContent"] {{ background: transparent !important; }}

.stApp [data-testid="stSidebar"] * {{ border-color: {SIDEBAR_BORDER}; }}
.stApp [data-testid="stSidebar"] p,
.stApp [data-testid="stSidebar"] span,
.stApp [data-testid="stSidebar"] label,
.stApp [data-testid="stSidebar"] li,
.stApp [data-testid="stSidebar"] .stMarkdown {{
  color: {SIDEBAR_TEXT} !important;
}}
.stApp [data-testid="stSidebar"] h1,
.stApp [data-testid="stSidebar"] h2,
.stApp [data-testid="stSidebar"] h3,
.stApp [data-testid="stSidebar"] h4 {{
  color: #EAF1FB !important; font-weight: 700 !important;
}}
.stApp [data-testid="stSidebar"] hr {{
  border-color: {SIDEBAR_BORDER} !important; margin: 0.85rem 0 !important;
}}

/* Region widget surfaces stay readable on the dark rail */
.stApp [data-testid="stSidebar"] [data-baseweb="select"] > div,
.stApp [data-testid="stSidebar"] [data-baseweb="input"] > div,
.stApp [data-testid="stSidebar"] .stMultiSelect > div > div,
.stApp [data-testid="stSidebar"] .stSelectbox > div > div,
.stApp [data-testid="stSidebar"] .stTextInput > div > div {{
  background: rgba(255,255,255,0.055) !important;
  border: 1px solid {SIDEBAR_BORDER} !important;
  color: #EAF1FB !important;
}}
.stApp [data-testid="stSidebar"] [data-baseweb="select"] svg {{ fill: {SIDEBAR_MUTED} !important; }}
.stApp [data-testid="stSidebar"] [data-baseweb="tag"] {{
  background: rgba(56,189,248,0.22) !important; color: #EAF1FB !important;
}}
.stApp [data-testid="stSidebar"] [data-testid="stSliderTickBarMin"],
.stApp [data-testid="stSidebar"] [data-testid="stSliderTickBarMax"] {{
  color: {SIDEBAR_MUTED} !important;
}}
.stApp [data-testid="stSidebar"] [data-testid="stAlertContainer"] p {{ color: inherit !important; }}

/* ── Brand block ─────────────────────────────────────────────────────── */
.stApp .uae-brand {{
  display: flex; align-items: center; gap: 0.7rem;
  padding: 0.55rem 0.35rem 0.95rem 0.35rem;
  border-bottom: 1px solid {SIDEBAR_BORDER};
  margin-bottom: 0.9rem;
}}
.stApp .uae-brand-mark {{
  width: 40px; height: 40px; flex: none; display: grid; place-items: center;
  border-radius: 12px; font-size: 1.15rem;
  background: linear-gradient(135deg, {BRAND_BLUE} 0%, {BRAND_TEAL} 100%);
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.34);
}}
.stApp .uae-brand-name {{
  font-size: 0.86rem !important; font-weight: 800 !important;
  letter-spacing: 0.01em; color: #FFFFFF !important; line-height: 1.18;
  margin: 0 !important;
}}
.stApp .uae-brand-name .l2 {{ color: {BRAND_SKY} !important; }}
.stApp .uae-brand-tag {{
  font-size: 0.63rem !important; font-weight: 600 !important;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: {SIDEBAR_MUTED} !important; margin: 0.14rem 0 0 0 !important;
}}

/* ── Group labels & separators ───────────────────────────────────────── */
.stApp .uae-navgroup {{
  font-size: 0.62rem !important; font-weight: 700 !important;
  letter-spacing: 0.16em; text-transform: uppercase;
  color: {SIDEBAR_GROUP} !important;
  margin: 1.05rem 0 0.45rem 0.5rem !important;
}}
.stApp .uae-navrule {{
  height: 1px; background: {SIDEBAR_BORDER};
  margin: 0.85rem 0.1rem;
}}

/* Tighten the rail's vertical rhythm — Streamlit's default block gap is sized
   for form layouts and makes a navigation list look disconnected. */
.stApp [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 0.3rem !important; }}
.stApp [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {{ gap: 0.3rem; }}

/* Any other button an environment puts in the rail (reset filters, etc.) gets
   the subtle dark-rail treatment. The nav rules below are more specific, so
   navigation items are unaffected. */
.stApp [data-testid="stSidebar"] .stButton > button {{
  background: rgba(255,255,255,0.05) !important;
  border: 1px solid {SIDEBAR_BORDER} !important;
  border-radius: 9px !important;
  color: {SIDEBAR_TEXT} !important;
  font-size: 0.78rem !important; font-weight: 600 !important;
  transition: background 0.2s var(--uae-ease), color 0.2s var(--uae-ease);
}}
.stApp [data-testid="stSidebar"] .stButton > button:hover {{
  background: rgba(255,255,255,0.10) !important; color: #FFFFFF !important;
}}
.stApp [data-testid="stSidebar"] .stButton > button p {{ color: inherit !important; }}

/* ── Nav items (Streamlit buttons wrapped in keyed containers) ───────── */
.stApp [data-testid="stSidebar"] [class*="st-key-uaenav-"] {{ margin-bottom: 0.16rem; }}
.stApp [data-testid="stSidebar"] [class*="st-key-uaenav-"] .stButton > button {{
  width: 100%;
  justify-content: flex-start !important;
  text-align: left !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  border-radius: 10px !important;
  color: {SIDEBAR_TEXT} !important;
  font-size: 0.845rem !important; font-weight: 500 !important;
  padding: 0.5rem 0.7rem !important;
  min-height: 0 !important; box-shadow: none !important;
  transition: background 0.2s var(--uae-ease), color 0.2s var(--uae-ease),
              transform 0.2s var(--uae-ease), border-color 0.2s var(--uae-ease);
}}
.stApp [data-testid="stSidebar"] [class*="st-key-uaenav-"] .stButton > button p {{
  color: inherit !important; font-size: inherit !important; font-weight: inherit !important;
}}
.stApp [data-testid="stSidebar"] [class*="st-key-uaenav-"] .stButton > button:hover {{
  background: {SIDEBAR_HOVER} !important;
  color: #FFFFFF !important;
  transform: translateX(2px);
}}
.stApp [data-testid="stSidebar"] [class*="st-key-uaenav-"] .stButton > button:focus-visible {{
  outline: 2px solid {BRAND_SKY} !important; outline-offset: 2px;
}}

/* Active state */
.stApp [data-testid="stSidebar"] [class*="st-key-uaenav-"][class*="-on"] .stButton > button {{
  background: {SIDEBAR_ACTIVE_BG} !important;
  color: {SIDEBAR_ACTIVE_TEXT} !important;
  font-weight: 700 !important;
  border-color: rgba(56,189,248,0.28) !important;
  box-shadow: inset 3px 0 0 0 {SIDEBAR_ACTIVE_BAR} !important;
  animation: uae-slide-in 0.28s var(--uae-ease) both;
}}
.stApp [data-testid="stSidebar"] [class*="st-key-uaenav-"][class*="-on"] .stButton > button p {{
  color: {SIDEBAR_ACTIVE_TEXT} !important; font-weight: 700 !important;
}}

/* Sub-items (Dubai workspaces) sit one level in */
.stApp [data-testid="stSidebar"] [class*="st-key-uaesub-"] {{ margin-bottom: 0.12rem; }}
.stApp [data-testid="stSidebar"] [class*="st-key-uaesub-"] .stButton > button {{
  width: 100%;
  justify-content: flex-start !important; text-align: left !important;
  background: transparent !important; border: 1px solid transparent !important;
  border-left: 1px solid {SIDEBAR_BORDER} !important;
  border-radius: 0 8px 8px 0 !important;
  margin-left: 0.85rem;
  color: {SIDEBAR_MUTED} !important;
  font-size: 0.79rem !important; font-weight: 500 !important;
  padding: 0.36rem 0.65rem !important; min-height: 0 !important;
  box-shadow: none !important;
  transition: all 0.2s var(--uae-ease);
}}
.stApp [data-testid="stSidebar"] [class*="st-key-uaesub-"] .stButton > button p {{
  color: inherit !important; font-size: inherit !important;
}}
.stApp [data-testid="stSidebar"] [class*="st-key-uaesub-"] .stButton > button:hover {{
  color: #EAF1FB !important; background: {SIDEBAR_HOVER} !important;
  border-left-color: {BRAND_SKY} !important;
}}
.stApp [data-testid="stSidebar"] [class*="st-key-uaesub-"][class*="-on"] .stButton > button {{
  color: #FFFFFF !important; font-weight: 700 !important;
  background: rgba(56,138,255,0.12) !important;
  border-left: 2px solid {SIDEBAR_ACTIVE_BAR} !important;
}}
.stApp [data-testid="stSidebar"] [class*="st-key-uaesub-"][class*="-on"] .stButton > button p {{
  color: #FFFFFF !important; font-weight: 700 !important;
}}

/* ── Region-controls divider ─────────────────────────────────────────── */
.stApp .uae-ctrl-head {{
  display: flex; align-items: center; gap: 0.5rem;
  margin: 1.5rem 0 0.7rem 0;
  padding-top: 0.9rem;
  border-top: 1px solid {SIDEBAR_BORDER};
}}
.stApp .uae-ctrl-head .lbl {{
  font-size: 0.62rem !important; font-weight: 700 !important;
  letter-spacing: 0.15em; text-transform: uppercase;
  color: {SIDEBAR_GROUP} !important; white-space: nowrap; margin: 0 !important;
}}
.stApp .uae-ctrl-head .ln {{ flex: 1; height: 1px; background: {SIDEBAR_BORDER}; }}

/* ── Sidebar footer ──────────────────────────────────────────────────── */
.stApp .uae-side-footer {{
  margin-top: 1.2rem; padding-top: 0.8rem;
  border-top: 1px solid {SIDEBAR_BORDER};
  font-size: 0.64rem !important; color: {SIDEBAR_GROUP} !important;
  line-height: 1.6;
}}

/* ── Region call-to-action buttons (Overview page) ───────────────────── */
.stApp [class*="st-key-uaecta-"] .stButton > button {{
  width: 100%;
  justify-content: center !important;
  background: var(--cta, #B8731B) !important;
  border: 1px solid var(--cta, #B8731B) !important;
  border-radius: 0 0 var(--uae-radius-lg) var(--uae-radius-lg) !important;
  color: #FFFFFF !important;
  font-size: 0.87rem !important; font-weight: 700 !important;
  letter-spacing: 0.01em;
  padding: 0.7rem 1rem !important;
  margin-top: -0.55rem;
  box-shadow: 0 8px 22px -10px var(--cta, #B8731B) !important;
  transition: filter 0.24s var(--uae-ease), transform 0.24s var(--uae-ease),
              box-shadow 0.24s var(--uae-ease);
}}
.stApp [class*="st-key-uaecta-"] .stButton > button p {{
  color: #FFFFFF !important; font-weight: 700 !important; font-size: inherit !important;
}}
.stApp [class*="st-key-uaecta-"] .stButton > button:hover {{
  filter: brightness(1.08);
  transform: translateY(-1px);
  box-shadow: 0 14px 30px -12px var(--cta, #B8731B) !important;
}}
.stApp [class*="st-key-uaecta-"] .stButton > button:focus-visible {{
  outline: 2px solid #FFFFFF !important; outline-offset: -4px;
}}

.stApp [class*="st-key-uaecta-abu_dhabi"] .stButton > button {{ --cta: {BRAND_BLUE}; }}
.stApp [class*="st-key-uaecta-dubai"] .stButton > button {{ --cta: {BRAND_TEAL}; }}
.stApp [class*="st-key-uaecta-experimental"] .stButton > button {{ --cta: #7C3AED; }}

/* ── Theme toggle button in the rail ─────────────────────────────────── */
.stApp [data-testid="stSidebar"] [class*="st-key-uaetheme"] .stButton > button {{
  width: 100%;
  justify-content: flex-start !important;
  background: rgba(255,255,255,0.045) !important;
  border: 1px solid {SIDEBAR_BORDER} !important;
  border-radius: 10px !important;
  color: {SIDEBAR_TEXT} !important;
  font-size: 0.78rem !important; font-weight: 600 !important;
  padding: 0.42rem 0.7rem !important; min-height: 0 !important;
  transition: all 0.2s var(--uae-ease);
}}
.stApp [data-testid="stSidebar"] [class*="st-key-uaetheme"] .stButton > button:hover {{
  background: rgba(255,255,255,0.09) !important; color: #FFFFFF !important;
}}
.stApp [data-testid="stSidebar"] [class*="st-key-uaetheme"] .stButton > button p {{
  color: inherit !important; font-size: inherit !important; font-weight: inherit !important;
}}

/* Keep the workspace background under platform ownership too */
body .stApp {{ background: {t['app_bg']} !important; }}
</style>
"""
