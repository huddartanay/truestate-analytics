"""
Professional PDF report for the Dubai analytics.

WHY MATPLOTLIB AND NOT REPORTLAB. A PDF library would be a new dependency, and
`matplotlib` is already a declared dependency of this project — so the report
adds nothing to the environment. `matplotlib.backends.backend_pdf.PdfPages`
writes real multi-page vector PDFs, and drawing each page on a figure canvas
gives exact control over the margins, the page border, the typography and the
page numbering the brief asks for.

WHERE THE NUMBERS COME FROM. Every value is computed here from the same
dataframe and the same `regions.dubai_market.metrics` functions the dashboard
calls. Nothing is hard-coded, and nothing is re-derived by a second method that
could drift from the screen.

WHY THE CHARTS ARE REDRAWN. Exporting a Plotly figure to an image needs
`kaleido`, which is not installed and would be another dependency. The charts
here are therefore drawn with matplotlib from the SAME computed frames that
feed the on-screen Plotly charts — so they are true vector renderings of the
same numbers, not screenshots of the UI.
"""

from __future__ import annotations

import gc
import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

# ── page geometry, in inches (A4 portrait) ──────────────────────────────────
PAGE_W, PAGE_H = 8.27, 11.69
M_L, M_R, M_T, M_B = 0.78, 0.78, 0.86, 0.80
BORDER_INSET = 0.30

CONTENT_W = PAGE_W - M_L - M_R
CONTENT_TOP = PAGE_H - M_T
CONTENT_BOTTOM = M_B

# The report palette is the site's palette. `design_system` is the single source
# of the brand colours; they are imported rather than restated so the PDF cannot
# drift away from the interface it reports on.
from platform_core.design_system import (  # noqa: E402
    BRAND_BRONZE, BRAND_GOLD, BRAND_INK, BRAND_SAND,
)

INK = BRAND_INK              # near-black, the logo's ground
MUTED = "#6B6560"            # warm grey, so it sits with the bronze
RULE = "#DED7CC"             # hairlines and table borders
ACCENT = BRAND_BRONZE        # headings, eyebrows, the cover rule
ACCENT_2 = BRAND_SAND        # secondary accent
AMBER = BRAND_GOLD
FAINT = "#F6F3EE"            # KPI panels
HEADER_FILL = "#F0E6D6"      # table header row
BAND_FILL = "#FBF8F3"        # alternating table rows

SERIES = [BRAND_BRONZE, "#0D9488", BRAND_GOLD, "#7C3AED", "#DC2626", "#059669",
          "#DB2777"]

#: The company mark, placed at the top of every cover page.
LOGO_FILE = Path(__file__).resolve().parent / "assets" / "truestates_logo.png"


def _fx(x_in: float) -> float:
    return x_in / PAGE_W


def _fy(y_in: float) -> float:
    return y_in / PAGE_H


@dataclass
class Report:
    """
    A page-flow document.

    `y` is the current baseline, measured in inches from the bottom of the
    page. Every writer moves it down and opens a new page when the space left
    is not enough for what comes next — which is what stops content being
    clipped or a heading being stranded at the foot of a page.
    """

    title: str
    subtitle: str
    pdf: PdfPages
    fig: object = None
    y: float = CONTENT_TOP
    page_no: int = 0
    footer_note: str = ""
    eyebrow: str = "TRUESTATES ANALYTICS"
    _pages: list = field(default_factory=list)

    # ── page lifecycle ──────────────────────────────────────────────────────
    def new_page(self, first: bool = False) -> None:
        if self.fig is not None:
            self._finish_page()
        self.fig = plt.figure(figsize=(PAGE_W, PAGE_H), dpi=200)
        self.fig.patch.set_facecolor("white")
        self.page_no += 1
        self._draw_border()
        if not first:
            self._draw_header()
        self.y = CONTENT_TOP if not first else PAGE_H - M_T

    def _draw_border(self) -> None:
        """A single hairline rule inset from the trim — corporate, not decorative."""
        w = PAGE_W - 2 * BORDER_INSET
        h = PAGE_H - 2 * BORDER_INSET
        self.fig.add_artist(Rectangle(
            (_fx(BORDER_INSET), _fy(BORDER_INSET)), _fx(w), _fy(h),
            transform=self.fig.transFigure, fill=False,
            edgecolor=RULE, linewidth=0.7))

    def _draw_header(self) -> None:
        self.fig.text(_fx(M_L), _fy(PAGE_H - M_T + 0.26), self.title,
                      fontsize=7.5, color=MUTED, va="bottom", ha="left")
        self.fig.text(_fx(PAGE_W - M_R), _fy(PAGE_H - M_T + 0.26), self.subtitle,
                      fontsize=7.5, color=MUTED, va="bottom", ha="right")
        self.fig.add_artist(plt.Line2D(
            [_fx(M_L), _fx(PAGE_W - M_R)],
            [_fy(PAGE_H - M_T + 0.18)] * 2,
            transform=self.fig.transFigure, color=RULE, linewidth=0.6))

    def _finish_page(self) -> None:
        self.fig.text(_fx(PAGE_W / 2), _fy(M_B - 0.34), f"— {self.page_no} —",
                      fontsize=7.5, color=MUTED, ha="center", va="center")
        if self.footer_note:
            self.fig.text(_fx(M_L), _fy(M_B - 0.34), self.footer_note,
                          fontsize=6.8, color=MUTED, ha="left", va="center")
        self.fig.add_artist(plt.Line2D(
            [_fx(M_L), _fx(PAGE_W - M_R)], [_fy(M_B - 0.20)] * 2,
            transform=self.fig.transFigure, color=RULE, linewidth=0.6))
        self.pdf.savefig(self.fig)
        plt.close(self.fig)
        self.fig = None

    def close(self) -> None:
        if self.fig is not None:
            self._finish_page()

    def space(self, needed: float) -> None:
        """
        Open a new page unless `needed` inches remain.

        Also opens one when there is no current page at all — which is the state
        immediately after the cover, since `title_page()` closes its own figure.
        Without this, the first writer after the cover would have nothing to
        draw on.
        """
        if self.fig is None or self.y - needed < CONTENT_BOTTOM:
            self.new_page()

    # ── writers ─────────────────────────────────────────────────────────────
    def h1(self, text: str, needs: float = 0.0) -> None:
        """`needs` = height of the first block that follows, so the heading and
        that block stay together instead of splitting across a page."""
        self.space(1.05 + needs)
        self.y -= 0.30
        self.fig.text(_fx(M_L), _fy(self.y), text, fontsize=16.5, color=INK,
                      fontweight="bold", va="top", ha="left")
        self.y -= 0.30
        self.fig.add_artist(plt.Line2D(
            [_fx(M_L), _fx(M_L + 1.5)], [_fy(self.y)] * 2,
            transform=self.fig.transFigure, color=ACCENT, linewidth=2.0))
        self.y -= 0.22

    def h2(self, text: str, needs: float = 0.0) -> None:
        self.space(0.85 + needs)
        self.y -= 0.22
        self.fig.text(_fx(M_L), _fy(self.y), text, fontsize=11.5, color=INK,
                      fontweight="bold", va="top", ha="left")
        self.y -= 0.26

    def body(self, text: str, size: float = 9.0, colour: str = INK,
             leading: float = 0.155, wrap: int = 104) -> None:
        import textwrap

        for para in text.split("\n"):
            if not para.strip():
                self.y -= leading * 0.6
                continue
            for line in textwrap.wrap(para.strip(), wrap) or [""]:
                self.space(leading + 0.05)
                self.fig.text(_fx(M_L), _fy(self.y), line, fontsize=size,
                              color=colour, va="top", ha="left")
                self.y -= leading
        self.y -= 0.06

    def bullets(self, items: list[str], size: float = 9.0) -> None:
        import textwrap

        for it in items:
            lines = textwrap.wrap(it, 98) or [""]
            for i, line in enumerate(lines):
                self.space(0.20)
                if i == 0:
                    self.fig.text(_fx(M_L + 0.06), _fy(self.y), "•", fontsize=size,
                                  color=ACCENT, va="top", ha="left")
                self.fig.text(_fx(M_L + 0.24), _fy(self.y), line, fontsize=size,
                              color=INK, va="top", ha="left")
                self.y -= 0.155
            self.y -= 0.03
        self.y -= 0.05

    def kpis(self, cards: list[tuple[str, str]], per_row: int = 3) -> None:
        """A row of headline figures, boxed."""
        rows = [cards[i:i + per_row] for i in range(0, len(cards), per_row)]
        for row in rows:
            self.space(0.85)
            self.y -= 0.06
            gap = 0.13
            w = (CONTENT_W - gap * (per_row - 1)) / per_row
            h = 0.66
            for i, (label, value) in enumerate(row):
                x = M_L + i * (w + gap)
                self.fig.add_artist(Rectangle(
                    (_fx(x), _fy(self.y - h)), _fx(w), _fy(h),
                    transform=self.fig.transFigure, facecolor=FAINT,
                    edgecolor=RULE, linewidth=0.6))
                self.fig.text(_fx(x + 0.12), _fy(self.y - 0.19), label.upper(),
                              fontsize=6.6, color=MUTED, va="center", ha="left")
                self.fig.text(_fx(x + 0.12), _fy(self.y - 0.44), value,
                              fontsize=13.0, color=INK, fontweight="bold",
                              va="center", ha="left")
            self.y -= h + 0.16

    def table(self, headers: list[str], rows: list[list[str]],
              widths: list[float] | None = None, size: float = 8.0,
              align_right_from: int = 1, caption: str = "") -> None:
        """
        A table that paginates. The header repeats on every page it spans, and
        the font is never shrunk to force a fit — the table breaks instead.
        """
        n = len(headers)
        widths = widths or [1.0 / n] * n
        widths = [w / sum(widths) for w in widths]
        xs, acc = [], 0.0
        for w in widths:
            xs.append(M_L + acc * CONTENT_W)
            acc += w
        row_h = 0.215
        head_h = 0.26

        def draw_head() -> None:
            self.fig.add_artist(Rectangle(
                (_fx(M_L), _fy(self.y - head_h)), _fx(CONTENT_W), _fy(head_h),
                transform=self.fig.transFigure, facecolor=HEADER_FILL,
                edgecolor=RULE, linewidth=0.6))
            for i, htxt in enumerate(headers):
                right = i >= align_right_from
                x = xs[i] + (widths[i] * CONTENT_W - 0.09) if right else xs[i] + 0.09
                self.fig.text(_fx(x), _fy(self.y - head_h / 2), htxt, fontsize=size - 0.3,
                              color=INK, fontweight="bold", va="center",
                              ha="right" if right else "left")
            self.y -= head_h

        self.space(head_h + row_h * 3)
        draw_head()

        for r_i, row in enumerate(rows):
            if self.y - row_h < CONTENT_BOTTOM:
                self.new_page()
                draw_head()
            if r_i % 2 == 1:
                self.fig.add_artist(Rectangle(
                    (_fx(M_L), _fy(self.y - row_h)), _fx(CONTENT_W), _fy(row_h),
                    transform=self.fig.transFigure, facecolor=BAND_FILL,
                    edgecolor="none"))
            for i, cell in enumerate(row):
                right = i >= align_right_from
                x = xs[i] + (widths[i] * CONTENT_W - 0.09) if right else xs[i] + 0.09
                txt = str(cell)
                if len(txt) > 34 and not right:
                    txt = txt[:33] + "…"
                self.fig.text(_fx(x), _fy(self.y - row_h / 2), txt, fontsize=size,
                              color=INK, va="center", ha="right" if right else "left")
            self.y -= row_h

        self.fig.add_artist(plt.Line2D(
            [_fx(M_L), _fx(M_L + CONTENT_W)], [_fy(self.y)] * 2,
            transform=self.fig.transFigure, color=RULE, linewidth=0.6))
        self.y -= 0.10
        if caption:
            self.body(caption, size=7.4, colour=MUTED, leading=0.135, wrap=126)

    # Tick labels, the x-axis title and the legend all render OUTSIDE the axes
    # box, so the flow has to reserve room for them or the next thing written
    # lands on top of them.
    AXIS_GUTTER = 0.52

    def chart(self, draw, height: float = 2.9, title: str = "",
              caption: str = "") -> None:
        """
        Place a matplotlib-drawn chart. `draw(ax)` receives an axes sized to the
        content width, so labels are laid out at final size and cannot be
        squashed by a later rescale.

        `height` is the height of the PLOT AREA. `AXIS_GUTTER` is added beneath
        it for the tick labels and the axis title.
        """
        self.space(height + self.AXIS_GUTTER + (0.30 if title else 0) + 0.42)
        if title:
            self.y -= 0.04
            self.fig.text(_fx(M_L), _fy(self.y), title, fontsize=10.0, color=INK,
                          fontweight="bold", va="top", ha="left")
            self.y -= 0.26

        ax = self.fig.add_axes([
            _fx(M_L + 0.42), _fy(self.y - height),
            _fx(CONTENT_W - 0.42), _fy(height)])
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(RULE)
            ax.spines[side].set_linewidth(0.7)
        ax.tick_params(labelsize=7.2, colors=MUTED, length=3, width=0.6)
        ax.grid(axis="y", color=RULE, linewidth=0.5, alpha=0.55)
        ax.set_axisbelow(True)
        draw(ax)
        for lbl in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            lbl.set_color(INK)
        self.y -= height + self.AXIS_GUTTER
        if caption:
            self.body(caption, size=7.4, colour=MUTED, leading=0.135, wrap=126)

    def _draw_logo(self, y: float, width: float = 1.55) -> float:
        """
        Place the company mark and return the cursor below it.

        The image is read at its own proportions, so the mark is never squashed.
        If the file is absent the cover simply starts at the eyebrow instead.
        """
        try:
            import matplotlib.image as mpimg

            if not LOGO_FILE.exists():
                return y
            img = mpimg.imread(str(LOGO_FILE))
            h_px, w_px = img.shape[0], img.shape[1]
            height = width * (h_px / w_px)
            ax = self.fig.add_axes([
                _fx(M_L), _fy(y - height), _fx(width), _fy(height)])
            ax.imshow(img)
            ax.axis("off")
            return y - height - 0.42
        except Exception:  # pragma: no cover - a cover page is never worth a crash
            return y

    def title_page(self, meta: list[tuple[str, str]], lede: str) -> None:
        """
        Cover page, laid out with an explicit downward cursor.

        Every element advances `y` by its own height before the next one is
        placed. The previous version positioned the eyebrow, the accent rule and
        the title from three independent constants, and because matplotlib
        draws text downward from a `va="top"` anchor, the rule landed inside the
        title's body. A single cursor makes that class of overlap impossible.
        """
        import textwrap

        self.new_page(first=True)
        y = PAGE_H - 1.55

        # Company mark. Drawn at its own aspect ratio so it is never stretched,
        # and simply skipped if the asset is missing — a missing logo must not
        # cost anyone their report.
        y = self._draw_logo(y)

        # Eyebrow
        self.fig.text(_fx(M_L), _fy(y), self.eyebrow,
                      fontsize=9.5, color=ACCENT, fontweight="bold",
                      va="top", ha="left")
        y -= 0.30

        # Accent rule, clear of both the eyebrow above and the title below
        self.fig.add_artist(Rectangle(
            (_fx(M_L), _fy(y)), _fx(0.92), _fy(0.05),
            transform=self.fig.transFigure, facecolor=ACCENT, edgecolor="none"))
        y -= 0.40

        # Title. Long titles ("Market Analytics & Forecast Report") used to run
        # past the right margin and into the page border, so the size steps down
        # and the text wraps to the content width instead of overflowing it.
        title_size = 26 if len(self.title) <= 26 else 22 if len(self.title) <= 36 else 19
        wrap_at = max(18, int(CONTENT_W * 72 / (title_size * 0.56)))
        for line in textwrap.wrap(self.title, wrap_at) or [self.title]:
            self.fig.text(_fx(M_L), _fy(y), line, fontsize=title_size, color=INK,
                          fontweight="bold", va="top", ha="left")
            y -= title_size / 42.0
        y -= 0.20

        # Subtitle
        self.fig.text(_fx(M_L), _fy(y), self.subtitle,
                      fontsize=12, color=MUTED, va="top", ha="left")
        y -= 0.58

        # Lede
        for line in textwrap.wrap(lede, 88):
            self.fig.text(_fx(M_L), _fy(y), line, fontsize=9.3, color=INK,
                          va="top", ha="left")
            y -= 0.185

        # Separator
        y -= 0.34
        self.fig.add_artist(plt.Line2D(
            [_fx(M_L), _fx(PAGE_W - M_R)], [_fy(y)] * 2,
            transform=self.fig.transFigure, color=RULE, linewidth=0.7))
        y -= 0.42

        # Metadata block
        for label, value in meta:
            self.fig.text(_fx(M_L), _fy(y), label.upper(), fontsize=7.0,
                          color=MUTED, va="top", ha="left")
            self.fig.text(_fx(M_L + 2.05), _fy(y - 0.012), value, fontsize=9.3,
                          color=INK, va="top", ha="left", fontweight="bold")
            y -= 0.31

        self.fig.text(_fx(M_L), _fy(1.34),
                      "Generated from the TruEstates Analytics platform.",
                      fontsize=8.0, color=MUTED, va="top", ha="left")
        self.fig.text(_fx(M_L), _fy(1.16),
                      "Every figure in this report is computed from the transaction data at "
                      "generation time. No value is hard-coded.",
                      fontsize=8.0, color=MUTED, va="top", ha="left")
        self._finish_page_titleless()

    def _finish_page_titleless(self) -> None:
        """The title page carries the border but no header, footer or number."""
        self.pdf.savefig(self.fig)
        plt.close(self.fig)
        self.fig = None
        self.page_no = 0


def new_document(title: str, subtitle: str, footer_note: str = "") -> tuple[Report, io.BytesIO]:
    buf = io.BytesIO()
    pdf = PdfPages(buf)
    rep = Report(title=title, subtitle=subtitle, pdf=pdf)
    rep.footer_note = footer_note
    return rep, buf


def finish(rep: Report, buf: io.BytesIO) -> bytes:
    """
    Close the document and hand back the bytes.

    The figures and the buffer are released explicitly. matplotlib holds a
    reference to every figure it creates, and a report can create a dozen; on a
    small hosted instance that is the difference between finishing and being
    killed for memory.
    """
    rep.close()
    rep.pdf.close()
    buf.seek(0)
    data = buf.getvalue()
    buf.close()
    plt.close("all")
    gc.collect()
    return data


def stamp() -> str:
    return datetime.now().strftime("%d %B %Y, %H:%M")
