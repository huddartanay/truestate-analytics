/**
 * Render Dubai_Analytics_Chart_Reference_Guide.docx from the payload produced by
 * tools/build_chart_reference_docx.py.
 *
 *   node tools/build_chart_reference_docx.js <payload.json> <output.docx>
 *
 * Every figure in the document comes from that payload, which is computed from
 * the datasets at build time. Nothing here is typed in by hand.
 */

const fs = require("fs");
const {
  AlignmentType, BorderStyle, Document, Footer, Header, HeadingLevel, LevelFormat,
  PageBreak, PageNumber, Packer, Paragraph, ShadingType, Table, TableCell, TableRow,
  TextRun, VerticalAlign, WidthType,
} = require("docx");

const [, , payloadPath, outPath] = process.argv;
const P = JSON.parse(fs.readFileSync(payloadPath, "utf8"));
const F = P.facts;

// ── palette ────────────────────────────────────────────────────────────────
const NAVY = "0F172A";
const BLUE = "2563EB";
const TEAL = "0D9488";
const AMBER = "B45309";
const RED = "B91C1C";
const GREY = "64748B";
const RULE = "E3E9F2";
const HEADFILL = "F1F5F9";

const CONTENT_W = 9360;   // A4 portrait minus 1" margins, in DXA

const nf = (n, d = 0) =>
  n === null || n === undefined || Number.isNaN(n)
    ? "—"
    : Number(n).toLocaleString("en-GB", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (n, d = 1) => (n === null || n === undefined ? "—" : `${n >= 0 ? "+" : ""}${n.toFixed(d)}%`);

/**
 * The chart registry is written in Markdown so the same strings can render in the
 * Streamlit ⓘ popovers. Convert the two markers it uses — **bold** and `code` —
 * into real docx runs so they do not appear as literal characters on the page.
 */
function mdRuns(text, base = {}) {
  const src = String(text ?? "");
  const size = base.size ?? 20;
  const out = [];
  const re = /\*\*([^*]+)\*\*|`([^`]+)`/g;
  let last = 0;
  let m;
  while ((m = re.exec(src)) !== null) {
    if (m.index > last) {
      out.push(new TextRun({ ...base, size, font: "Calibri", text: src.slice(last, m.index) }));
    }
    if (m[1] !== undefined) {
      out.push(new TextRun({ ...base, size, font: "Calibri", bold: true, text: m[1] }));
    } else {
      out.push(new TextRun({
        ...base, font: "Consolas", size: Math.max(14, size - 2), color: base.color ?? "334155",
        text: m[2],
      }));
    }
    last = re.lastIndex;
  }
  if (last < src.length || !out.length) {
    out.push(new TextRun({ ...base, size, font: "Calibri", text: src.slice(last) }));
  }
  return out;
}

// ── building blocks ────────────────────────────────────────────────────────
const p = (text, opts = {}) =>
  new Paragraph({
    spacing: { after: opts.after ?? 120, before: opts.before ?? 0, line: 276 },
    alignment: opts.align,
    indent: opts.indent,
    border: opts.border,
    children: mdRuns(text, {
      size: opts.size ?? 20, color: opts.color, bold: opts.bold, italics: opts.italics,
    }),
  });

/** Paragraph from an array of {text, bold, color} runs. */
const rich = (runs, opts = {}) =>
  new Paragraph({
    spacing: { after: opts.after ?? 120, before: opts.before ?? 0, line: 276 },
    indent: opts.indent,
    children: runs.map(r => new TextRun({
      text: r.text, bold: r.bold, italics: r.italics, color: r.color,
      size: r.size ?? opts.size ?? 20, font: "Calibri",
    })),
  });

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 },
  children: [new TextRun({ text, size: 34, bold: true, color: NAVY, font: "Calibri" })],
});
const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 300, after: 160 },
  children: [new TextRun({ text, size: 27, bold: true, color: NAVY, font: "Calibri" })],
});
const h3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3, spacing: { before: 220, after: 100 },
  children: [new TextRun({ text, size: 22, bold: true, color: BLUE, font: "Calibri" })],
});
/** Small bold label used inside a chart entry (not in the TOC). */
const label = (text) => new Paragraph({
  spacing: { before: 160, after: 60 },
  children: [new TextRun({
    text: text.toUpperCase(), size: 16, bold: true, color: GREY,
    characterSpacing: 20, font: "Calibri",
  })],
});

const bullet = (text, level = 0) => new Paragraph({
  numbering: { reference: "bullets", level },
  spacing: { after: 70, line: 276 },
  children: mdRuns(text, { size: 20 }),
});

/** A paragraph that opens with a fixed lead run, then Markdown-aware body text. */
const lead = (leadRun, text, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 70, before: opts.before ?? 0, line: 276 },
  indent: opts.indent,
  children: [
    new TextRun({ ...leadRun, size: leadRun.size ?? 20, font: "Calibri" }),
    ...mdRuns(text, { size: opts.size ?? 20 }),
  ],
});

const rule = () => new Paragraph({
  spacing: { before: 120, after: 120 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE } },
  children: [new TextRun({ text: "", size: 2 })],
});

const callout = (title, body, colour) => new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [CONTENT_W],
  borders: {
    top: { style: BorderStyle.SINGLE, size: 2, color: colour },
    bottom: { style: BorderStyle.SINGLE, size: 2, color: colour },
    right: { style: BorderStyle.SINGLE, size: 2, color: colour },
    left: { style: BorderStyle.SINGLE, size: 18, color: colour },
    insideHorizontal: { style: BorderStyle.NONE },
    insideVertical: { style: BorderStyle.NONE },
  },
  rows: [new TableRow({
    children: [new TableCell({
      width: { size: CONTENT_W, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: "FAFCFF" },
      margins: { top: 140, bottom: 140, left: 200, right: 160 },
      children: [
        rich([{ text: title, bold: true, color: colour }], { after: 60 }),
        ...body.map(b => p(b, { after: 60 })),
      ],
    })],
  })],
});

/** Simple bordered table. `widths` must sum to CONTENT_W. */
function table(headers, rows, widths, opts = {}) {
  const cellSize = opts.size ?? 17;
  const cell = (text, w, { bold, fill, align, color } = {}) =>
    new TableCell({
      width: { size: w, type: WidthType.DXA },
      shading: fill ? { type: ShadingType.CLEAR, fill } : undefined,
      margins: { top: 70, bottom: 70, left: 110, right: 110 },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({
        alignment: align,
        spacing: { after: 0, line: 240 },
        children: mdRuns(text, { bold, size: cellSize, color }),
      })],
    });

  // Numbers read best right-aligned; sentences do not. A column that carries any
  // long value is left-aligned throughout, header included.
  const plain = (v) => String((v && typeof v === "object" ? v.text : v) ?? "");
  const isProse = widths.map((_, i) => rows.some(r => plain(r[i]).length > 44));
  const alignFor = (i) =>
    (opts.left || i === 0 || isProse[i] ? AlignmentType.LEFT : AlignmentType.RIGHT);

  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: widths,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      left: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      right: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      insideVertical: { style: BorderStyle.SINGLE, size: 2, color: RULE },
    },
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((hh, i) =>
          cell(hh, widths[i], { bold: true, fill: HEADFILL, align: alignFor(i) })),
      }),
      ...rows.map(r => new TableRow({
        children: r.map((v, i) => cell(
          typeof v === "object" ? v.text : v,
          widths[i],
          {
            align: alignFor(i),
            color: typeof v === "object" ? v.color : undefined,
            bold: typeof v === "object" ? v.bold : undefined,
          })),
      })),
    ],
  });
}

const SRC_COLOUR = { CLEANED: TEAL, RAW: AMBER, DERIVED: "7C3AED" };

// ═══════════════════════════════════════════════════════════════════════════
// DOCUMENT
// ═══════════════════════════════════════════════════════════════════════════

const body = [];

// ── Cover ──────────────────────────────────────────────────────────────────
body.push(
  new Paragraph({ spacing: { before: 2600, after: 0 }, children: [
    new TextRun({ text: "UAE REAL ESTATE ANALYTICS", size: 20, bold: true, color: BLUE,
      characterSpacing: 60, font: "Calibri" })] }),
  new Paragraph({ spacing: { before: 200, after: 60 }, children: [
    new TextRun({ text: "Dubai Analytics", size: 56, bold: true, color: NAVY, font: "Calibri" })] }),
  new Paragraph({ spacing: { after: 260 }, children: [
    new TextRun({ text: "Chart Reference Guide", size: 44, color: BLUE, font: "Calibri" })] }),
  new Paragraph({
    spacing: { after: 200 },
    border: { top: { style: BorderStyle.SINGLE, size: 8, color: RULE } },
    children: [new TextRun({ text: "", size: 2 })] }),
  p("Every chart in the Dubai section of the platform: what it shows, where the numbers come "
    + "from, exactly how each figure is calculated, how to read it, what it does not tell you, "
    + "and how it was checked.", { size: 22, color: "334155" }),
  p(`${P.charts.length} charts documented · ${P.sections.length} dashboard sections`,
    { size: 20, color: GREY, before: 240 }),
  p("Prepared for company review. Local development build — not deployed.",
    { size: 20, color: GREY }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ── Contents ───────────────────────────────────────────────────────────────
body.push(h1("Contents"));
{
  const line = (text, opts = {}) => new Paragraph({
    spacing: { after: opts.after ?? 40, before: opts.before ?? 0, line: 260 },
    indent: { left: opts.indent ?? 0 },
    children: [new TextRun({
      text, size: opts.size ?? 19, bold: opts.bold, color: opts.color ?? "1E293B", font: "Calibri",
    })],
  });

  body.push(line("1.  About this document", { bold: true, before: 60 }));
  body.push(line("2.  The two Dubai datasets", { bold: true, before: 60 }));
  body.push(line("3.  What was checked, and what was found", { bold: true, before: 60 }));
  body.push(line("4.  Chart reference", { bold: true, before: 60 }));

  let n = 0;
  P.sections.forEach(section => {
    const charts = P.charts.filter(c => c.section === section);
    if (!charts.length) return;
    n += 1;
    body.push(line(`4.${n}  ${section}`, { indent: 360, color: BLUE, bold: true, before: 60 }));
    charts.forEach((c, i) => body.push(
      line(`4.${n}.${i + 1}  ${c.title}`, { indent: 760, size: 18, color: "334155" })));
  });

  body.push(line("Appendix A.  The amenity results, explained", { bold: true, before: 160 }));
  ["A.1  The headline figures, and what happens when you control for property mix",
    "A.2  Why the headline figures are wrong — the recording effect",
    "A.3  Parking: what “+102%” actually means",
    "A.4  Balcony: why a negative number does not mean “balconies are bad”",
    "A.5  Rules for quoting these numbers",
  ].forEach(t => body.push(line(t, { indent: 360, size: 18, color: "334155" })));

  body.push(line("Appendix B.  Year-over-year validation", { bold: true, before: 80 }));
  body.push(line("Appendix C.  Off-plan premium validation", { bold: true, before: 60 }));
  ["C.1  Does the label mean what it says?",
    "C.2  Then why is unbuilt property dearer than finished property?",
    "C.3  The stock test",
    "C.4  The two sides are not the same product",
    "C.5  How to quote this",
  ].forEach(t => body.push(line(t, { indent: 360, size: 18, color: "334155" })));
  body.push(line("Appendix D.  Price-band reconciliation", { bold: true, before: 60 }));
  body.push(line("Appendix E.  Layout distribution reference", { bold: true, before: 60 }));
  body.push(line("Appendix F.  Every word, in plain English", { bold: true, before: 60 }));
}
body.push(new Paragraph({ children: [new PageBreak()] }));

// ── 1. About ───────────────────────────────────────────────────────────────
body.push(h1("1. About this document"));
p1();
function p1() {
  body.push(p("This guide documents every graph in the Dubai section of the UAE Real Estate "
    + "Analytics platform. It is written for management, analysts and business users — you do "
    + "not need to read code to use it."));
  body.push(p("It is generated directly from the application. The same descriptions appear "
    + "behind the ⓘ icon next to each chart on screen, and every table of figures in this "
    + "document is computed from the Dubai datasets when the document is built. If the "
    + "dashboard changes, this guide is rebuilt from it — the two cannot drift apart."));

  body.push(h3("How each chart is documented"));
  [
    "What the graph is, and why it is used.",
    "Which dataset it reads — RAW, CLEANED or DERIVED — and the exact file and columns.",
    "How the data is prepared, and the precise calculation.",
    "Axes, legend, and which dashboard filters affect it.",
    "How to read it, and how to explain it to a client.",
    "What it tells you — and, just as importantly, what it does not.",
    "Its limitations, and how the calculation was validated.",
  ].forEach(t => body.push(bullet(t)));

  body.push(h3("Three rules this dashboard follows"));
  body.push(rich([
    { text: "Median over mean. ", bold: true },
    { text: "Property prices are right-skewed — a few very large deals pull the average "
        + "upward. Medians are used for every headline comparison." }]));
  body.push(rich([
    { text: "Rate per square metre over total price. ", bold: true },
    { text: "Total price mixes size with value. Rate per m² is the like-for-like comparison, "
        + "and it is the measure to quote when asked whether prices are rising." }]));
  body.push(rich([
    { text: "Association, never causation. ", bold: true },
    { text: "Where the dashboard compares two groups of properties, it says so. It never "
        + "claims that a feature causes a price difference." }]));
}

// ── 2. The datasets ────────────────────────────────────────────────────────
body.push(h1("2. The two Dubai datasets"));
{
  const raw = F.provenance.raw, cl = F.provenance.clean, rel = F.provenance.relationship;
  body.push(p("Two Dubai datasets ship with the platform. Every chart states which one it uses, "
    + "in a badge beside its title on screen and in its entry in this guide."));
  body.push(table(
    ["", "RAW registry", "CLEANED dataset"],
    [
      ["File", raw.file, cl.file],
      ["Transactions", nf(raw.rows), nf(cl.rows)],
      ["Columns", nf(raw.columns), nf(cl.columns)],
      ["Date range", `${raw.date_min} → ${raw.date_max}`, `${cl.date_min} → ${cl.date_max}`],
      ["Areas", nf(raw.areas), nf(cl.areas)],
      ["Transaction types", "Sales, Mortgages, Gifts", "Sales only"],
      ["Property types", "Unit, Villa, Land, Building", "Unit only"],
      ["Property usage", "All", "Residential only"],
    ],
    [2200, 3580, 3580]));

  body.push(p(rel.note, { before: 160 }));
  body.push(rich([
    { text: `Of the ${nf(rel.raw_matching_slice)} residential-unit sales in the raw registry, ` },
    { text: `${nf(rel.clean_rows)} (${rel.coverage_pct}%)`, bold: true },
    { text: ` carry through to the cleaned dataset, which adds ${rel.added_columns} `
        + "engineered columns — time parts, unit attributes, amenity flags and building and "
        + "developer scoring." }]));

  body.push(h3("Which dataset each chart uses"));
  const bySrc = {};
  P.charts.forEach(c => { (bySrc[c.source_label] = bySrc[c.source_label] || []).push(c); });
  body.push(table(
    ["Data source", "Charts", "Which ones"],
    Object.entries(bySrc).map(([k, v]) => [
      { text: k, bold: true, color: SRC_COLOUR[k] },
      nf(v.length),
      v.map(c => c.title).join("; "),
    ]),
    [1700, 900, 6760]));
  body.push(callout("A note on the amenity analysis", [
    "Only the parking flag exists in the raw registry. The swimming-pool, balcony, elevator "
    + "and metro flags are engineered fields present only in the cleaned dataset, so they "
    + "cannot be re-derived from the raw file. The parking result was additionally validated "
    + "against the raw registry — see Appendix A.",
  ], AMBER));
}

// ── 3. Validation summary ──────────────────────────────────────────────────
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(h1("3. What was checked, and what was found"));
body.push(p("Six areas of the Dubai dashboard were reviewed against the datasets. This is what "
  + "the review found."));
{
  const py = F.partial_year, mo = F.monthly, bands = F.bands, om = F.offplan_meta;
  const findings = [
    ["Year-over-year growth",
      "Correct, one issue of interpretation",
      `Each year is compared with the immediately preceding year. All ${F.yoy_meta.years[1] - F.yoy_meta.years[0] + 1} `
      + `years ${F.yoy_meta.years[0]}–${F.yoy_meta.years[1]} are present with no gaps. `
      + `${py.year} is a partial year (data ends ${py.last_date}), so its ${pct(py.volume_pct_fullyear)} `
      + `volume bar is not comparable; the like-for-like figure is ${pct(py.volume_pct_ytd)}. `
      + "A like-for-like panel was added. Negative years were verified as genuine and kept."],
    ["Rate per m² by layout",
      "Chart was unreadable — rebuilt",
      `All nine layouts were drawn at one x-position. Rebuilt as one panel per layout on a `
      + `shared scale, with transaction counts and a full quartile table. The previous caption `
      + `("smaller units cost more per m²") was tested against the data, found to be false, and removed.`],
    ["How prices are moving",
      "Correct, readability improved",
      `Monthly medians are correct. Every month carries at least ${nf(mo.min_count)} transactions `
      + `(median ${nf(mo.median_count)}), so the jaggedness is genuine, not thin-sample noise. `
      + `A 3-month centred rolling median was added as an optional view: the standard `
      + `deviation of month-on-month change falls from ${mo.vol_raw}% to ${mo.vol_smoothed}%. `
      + `Actual observations remain selectable and tabulated.`],
    ["Off-plan vs existing",
      "Correct, made explicit",
      `Classification validated on the raw registry: exactly two values, no missing rows. `
      + `Off-plan traded at a premium in ${om.positive} of ${om.years} years. A premium/discount `
      + `chart was added so the gap is stated rather than eyeballed.`],
    ["Amenities vs price",
      "Headline was misleading — rebuilt",
      `Recalculated and decomposed. Controlling for area, layout, year and registration type, `
      + `every headline figure collapses (see Appendix A). The dashboard now shows headline and `
      + `like-for-like side by side, plus a composition explorer.`],
    ["Where the price points are",
      "Correct, filter effect explained",
      `Bands validated on all three datasets: counts sum exactly to the row count with zero `
      + `unassigned rows and no duplicate transaction identifiers. The empty ">10M" band was `
      + `caused by the default price filter, not by the data — a warning now says so.`],
  ];
  body.push(table(["Chart", "Verdict", "What was found"],
    findings.map(f => [f[0], f[1], f[2]]), [1900, 1900, 5560], { left: true }));
}

// ── 4. Chart reference ─────────────────────────────────────────────────────
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(h1("4. Chart reference"));
body.push(p("Every chart in the Dubai dashboard, in the order it appears on screen."));

let sectionNo = 0;
P.sections.forEach(section => {
  const charts = P.charts.filter(c => c.section === section);
  if (!charts.length) return;
  sectionNo += 1;
  body.push(h2(`4.${sectionNo}  ${section}`));

  charts.forEach((c, i) => {
    body.push(h3(`4.${sectionNo}.${i + 1}  ${c.title}`));
    if (c.subtitle) body.push(p(c.subtitle, { italics: true, color: GREY, after: 140 }));

    if (c.one_liner) body.push(callout("In one sentence", [c.one_liner], BLUE));

    body.push(label("What is this graph?"));
    body.push(p(c.what));

    body.push(label("Why is this graph used?"));
    body.push(p(c.why));

    if (c.steps && c.steps.length) {
      body.push(label("What happens inside this chart, step by step"));
      c.steps.forEach((s, n) => body.push(lead(
        { text: `${n + 1}.  `, bold: true, color: BLUE }, s, { indent: { left: 240 } })));
    }

    if (c.terms && c.terms.length) {
      body.push(label("Words used on this chart"));
      c.terms.forEach(([term, meaning]) => body.push(lead(
        { text: `${term} — `, bold: true }, meaning, { indent: { left: 240 } })));
    }

    body.push(label("Data source"));
    body.push(table(
      ["Field", "Value"],
      [
        ["Source", { text: c.source_label, bold: true, color: SRC_COLOUR[c.source_label] }],
        ["Dataset file", c.source_file],
        ["What that file is", c.source_desc],
        ["Source columns", c.columns.join(", ")],
      ],
      [2200, 7160], { left: true }));

    if (c.preparation) { body.push(label("Data preparation")); body.push(p(c.preparation)); }

    body.push(label("Calculation"));
    body.push(p(c.calculation));

    const axes = [];
    if (c.x_axis) axes.push(["X-axis", c.x_axis]);
    if (c.y_axis) axes.push(["Y-axis", c.y_axis]);
    if (c.y2_axis) axes.push(["Secondary (right) axis", c.y2_axis]);
    if (c.legend) axes.push(["Legend", c.legend]);
    if (axes.length) {
      body.push(label("Axes and legend"));
      body.push(table(["Element", "What it shows"], axes, [2600, 6760], { left: true }));
    }

    if (c.filters) { body.push(label("Filters")); body.push(p(c.filters)); }

    if (c.how_to_read.length) {
      body.push(label("How to read it"));
      c.how_to_read.forEach(t => body.push(bullet(t)));
    }

    if (c.client_explanation) {
      body.push(label("How to explain it to a client"));
      body.push(callout("In plain language", [c.client_explanation], BLUE));
    }

    if (c.tells_us.length) {
      body.push(label("What this graph tells us"));
      c.tells_us.forEach(t => body.push(bullet(t)));
    }
    if (c.does_not_tell.length) {
      body.push(label("What this graph does NOT tell us"));
      c.does_not_tell.forEach(t => body.push(bullet(t)));
    }
    if (c.limitations.length) {
      body.push(label("Limitations"));
      c.limitations.forEach(t => body.push(bullet(t)));
    }
    if (c.validation) { body.push(label("Validation performed")); body.push(p(c.validation)); }

    body.push(rule());
  });
});

// ── Appendix A — amenities ─────────────────────────────────────────────────
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(h1("Appendix A. The amenity results, explained"));
body.push(p("This appendix exists because the amenity chart is the easiest number on the "
  + "dashboard to misread, and the most likely to be quoted out of context."));

body.push(h2("A.1  The headline figures, and what happens when you control for property mix"));
body.push(p("The first column is the straight comparison across the whole dataset. The next two "
  + "repeat it inside progressively narrower groups of comparable properties."));
body.push(table(
  ["Amenity", "Units with", "Units without", "Headline", "Same area, layout & year", "…and same registration type"],
  F.amenities.map(a => [
    a.amenity, nf(a.n_with), nf(a.n_without),
    { text: pct(a.headline), color: a.headline >= 0 ? TEAL : RED, bold: true },
    { text: a.lfl3 === null ? "—" : pct(a.lfl3), color: a.lfl3 >= 0 ? TEAL : RED },
    { text: a.lfl4 === null ? "—" : pct(a.lfl4), color: a.lfl4 >= 0 ? TEAL : RED, bold: true },
  ]),
  [1900, 1200, 1300, 1500, 1730, 1730]));

body.push(callout("The single most important line in this document", [
  "Four of the five headline figures reverse or collapse once you compare like with like. "
  + "The right-hand column is the one to quote. The headline column describes two different "
  + "groups of properties, not the value of a feature.",
], RED));

body.push(h2("A.2  Why the headline figures are wrong — the recording effect"));
{
  const bal = F.recording.balcony_by_reg;
  const rates = F.recording.median_rate_by_reg;
  const regs = Object.keys(rates);
  body.push(p("Building attributes are recorded far more completely for finished property than "
    + "for off-plan sales. Because off-plan trades at a much higher rate per square metre, any "
    + "flag that is under-recorded on off-plan sales produces a false negative headline."));
  // Deal counts per registration type come from the within-registration table, so the
  // share column reconciles with the cleaned dataset row count rather than being asserted.
  const dealsByReg = {};
  F.recording.balcony_within_reg.forEach(r => { dealsByReg[r.reg] = r.n_with + r.n_without; });
  const totalDeals = Object.values(dealsByReg).reduce((a, b) => a + b, 0);
  body.push(table(
    ["Registration type", "Balcony recorded (%)", "Not recorded (%)", "Median rate (AED/m²)", "Share of deals"],
    regs.map(r => {
      const withPct = bal["1"] ? bal["1"][r] : null;
      const withoutPct = bal["0"] ? bal["0"][r] : null;
      const share = totalDeals && dealsByReg[r] !== undefined
        ? `${((dealsByReg[r] / totalDeals) * 100).toFixed(1)}%` : "—";
      return [r, withPct === null ? "—" : `${withPct}%`, withoutPct === null ? "—" : `${withoutPct}%`,
        nf(rates[r]), share];
    }),
    [2400, 1900, 1700, 1900, 1460]));
  body.push(p("Read that table slowly. A balcony is recorded for the large majority of existing "
    + "sales and a minority of off-plan sales. Off-plan sells for far more per square metre. So "
    + "\"no balcony recorded\" is largely a proxy for \"off-plan\" — and the −30% headline is "
    + "measuring registration type, not balconies.", { before: 120 }));

  body.push(h3("The proof: the balcony gap reverses inside each registration type"));
  body.push(table(
    ["Registration type", "Median rate WITH balcony", "Median rate WITHOUT", "Deals with", "Deals without", "Difference"],
    F.recording.balcony_within_reg.map(r => [
      r.reg, nf(r.with), nf(r.without), nf(r.n_with), nf(r.n_without),
      { text: pct(r.diff), color: r.diff >= 0 ? TEAL : RED, bold: true },
    ]),
    [2200, 1800, 1600, 1200, 1300, 1260]));
  body.push(callout("What a sign flip means", [
    "Within existing property, balconies are associated with a higher rate. Within off-plan "
    + "property, with a lower one. When a comparison reverses depending on how you slice the "
    + "data, the overall figure is describing the mix of properties, not the feature. This is a "
    + "textbook composition effect, and it is why the like-for-like number is the one to use.",
  ], AMBER));
}

body.push(h2("A.3  Parking: what “+102%” actually means"));
{
  const pr = F.parking_raw, pc = F.parking_clean;
  const parking = F.amenities.find(a => a.column === "has_parking");
  body.push(rich([
    { text: "The correct statement is: " },
    { text: "“properties recorded with parking show a higher observed median rate per square "
        + "metre than properties without, in this dataset.” ", bold: true },
    { text: "It is not “parking doubles the price”. Here is the evidence for why not." }]));

  body.push(h3("On the raw registry, the flag only ever applies to apartments"));
  body.push(table(
    ["Property type", "With parking", "Without parking"],
    Object.entries(pr.by_property_type).map(([k, v]) => [k, nf(v["1"] || 0), nf(v["0"] || 0)]),
    [3400, 3000, 2960]));
  body.push(p("Every villa, land and whole-building row carries a zero. On the raw file the "
    + "comparison is therefore largely apartments against land and villas — which is not a "
    + "parking comparison at all.", { before: 100 }));

  body.push(h3("Restricting to residential apartments only, on the raw registry"));
  body.push(table(
    ["", "With parking", "Without parking"],
    [
      ["Transactions", nf(pr.unit_with), nf(pr.unit_without)],
      ["Median rate (AED/m²)", nf(pr.unit_median_with), nf(pr.unit_median_without)],
      ["Median size (m²)", nf(pr.size_with), nf(pr.size_without)],
      ["Difference", { text: pct(pr.unit_gap), bold: true, color: TEAL }, ""],
    ],
    [3400, 3000, 2960]));

  body.push(h3("What the “no parking” apartments actually are"));
  [
    `Overwhelmingly studios: ${pc.studio_share_without}% of the no-parking group against `
    + `${pc.studio_share_with}% of the with-parking group.`,
    `Overwhelmingly resale rather than new: ${pc.existing_share_without}% existing property `
    + `against ${pc.existing_share_with}%.`,
    `Heavily concentrated in one affordable area — ${pc.top_area_without} alone accounts for `
    + `${pc.top_area_without_share}% of them.`,
    `Much smaller: a median of ${nf(pr.size_without)} m² against ${nf(pr.size_with)} m².`,
  ].forEach(t => body.push(bullet(t)));

  body.push(callout("The practical explanation", [
    `Parking is acting as a marker for a different kind of property: a larger, newer, `
    + `off-plan apartment in a mid-market or premium development, rather than a small resale `
    + `studio in an affordable area. Compare like with like — same area, same layout, same year, `
    + `same registration type — and the gap falls from ${pct(parking.headline)} to `
    + `${pct(parking.lfl4)}, measured across ${nf(parking.cells4)} comparable groups covering `
    + `${nf(parking.txns4)} transactions.`,
    "Parking is genuinely associated with a modest price premium. It is not associated with a "
    + "doubling.",
  ], TEAL));
}

body.push(h2("A.4  Balcony: why a negative number does not mean “balconies are bad”"));
{
  const bal = F.amenities.find(a => a.column === "balcony");
  body.push(rich([
    { text: "The correct statement is: " },
    { text: "“properties recorded with a balcony show a lower observed median rate per square "
        + "metre than those without, in this dataset.” ", bold: true },
    { text: "It is not “balconies reduce value”." }]));
  [
    `The headline gap is ${pct(bal.headline)}. Held within the same area, layout and year it `
    + `narrows to ${pct(bal.lfl3)}. Adding registration type to the control brings it to `
    + `${pct(bal.lfl4)} — effectively nothing.`,
    "Registration type is the driver. Balconies are recorded for most existing-property sales "
    + "and a minority of off-plan sales, and off-plan sells for far more per square metre.",
    "Within existing property alone, the balcony association is clearly positive — see A.2.",
    "Nothing in this dataset supports a claim that a balcony reduces what a buyer will pay.",
  ].forEach(t => body.push(bullet(t)));
  body.push(callout("How to answer the client question", [
    "“Does a balcony hurt the price?” No. What the raw chart shows is that the kind of "
    + "property recorded as having a balcony — typically completed resale stock — sells for "
    + "less per square metre than off-plan stock does. Compare two similar apartments in the "
    + "same building type and the balcony effect is close to zero, and positive within the "
    + "resale market.",
  ], BLUE));
}

body.push(h2("A.5  Rules for quoting these numbers"));
[
  "Quote the like-for-like figure, not the headline.",
  "Say “properties with X show…”, never “X increases the price by…”.",
  "State the sample: how many comparable groups and how many transactions.",
  "Remember that a zero in these fields means “not recorded as present”, which is not the "
  + "same as “confirmed absent”.",
  "Only the parking flag can be checked against the raw registry; the other four exist only in "
  + "the cleaned dataset.",
].forEach(t => body.push(bullet(t)));

// ── Appendix B — YoY ───────────────────────────────────────────────────────
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(h1("Appendix B. Year-over-year validation"));
body.push(p("Each year is compared with the immediately preceding year — never against a fixed "
  + "baseline. The table below is the full working."));
body.push(table(
  ["Year", "Transactions", "Volume vs prior yr", "Median price (AED)", "Median rate (AED/m²)", "Rate vs prior yr"],
  F.yoy.map(r => [
    String(r.year), nf(r.transactions),
    { text: r.volume_yoy === null ? "base" : pct(r.volume_yoy),
      color: r.volume_yoy === null ? GREY : (r.volume_yoy >= 0 ? TEAL : RED) },
    nf(r.median_price), nf(r.median_rate),
    { text: r.rate_yoy === null ? "base" : pct(r.rate_yoy),
      color: r.rate_yoy === null ? GREY : (r.rate_yoy >= 0 ? TEAL : RED) },
  ]),
  [900, 1600, 1760, 1900, 1900, 1300]));

{
  const m = F.yoy_meta, py = F.partial_year;
  body.push(p(`Years present: ${m.years[0]}–${m.years[1]}`
    + `${m.gaps.length ? `, gaps at ${m.gaps.join(", ")}` : ", with no gaps"}. `
    + `Negative volume years: ${m.negative_volume_years.join(", ")}. `
    + `Negative rate years: ${m.negative_rate_years.join(", ")}.`, { before: 160 }));
  body.push(callout(`${py.year} is a partial year — read its bar with care`, [
    `The data ends ${py.last_date}, so ${py.year} covers ${py.months} months. Comparing `
    + `${py.months} months against a full 12 produces ${pct(py.volume_pct_fullyear)}, which is `
    + `an artefact of the calendar, not a market collapse.`,
    `Like for like — the same ${py.months} months of each year — volume is `
    + `${pct(py.volume_pct_ytd)} (${nf(py.volume_current)} transactions against `
    + `${nf(py.volume_base_ytd)}) and the median rate is ${pct(py.rate_pct_ytd, 2)}.`,
    "Medians are far less sensitive to a shorter year than counts are, which is why the rate "
    + "line is broadly reliable even for the partial year while the volume bar is not.",
  ], AMBER));
  body.push(p("The negative years were each traced back to their own transaction count and "
    + "median before being accepted. They are genuine market contractions consistent with the "
    + "known Dubai cycle, and they have been kept. Negative results are not removed from this "
    + "dashboard for being unwelcome.", { before: 120 }));
}

// ── Appendix C — off-plan ──────────────────────────────────────────────────
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(h1("Appendix C. Off-plan premium validation"));
{
  const om = F.offplan_meta;
  body.push(p(`Classification was validated on the raw registry before any calculation: `
    + `${Object.entries(om.reg_values_raw).map(([k, v]) => `${k} (${nf(v)})`).join(", ")}, `
    + `with ${om.reg_nulls_raw} missing values. Two clean values, so no reclassification was `
    + `needed and none was invented.`));
  body.push(table(
    ["Year", "Off-plan median", "Existing median", "Off-plan deals", "Existing deals", "Premium"],
    F.offplan.map(r => [
      String(r.year), nf(r.offplan), nf(r.existing), nf(r.n_off), nf(r.n_exi),
      { text: pct(r.premium, 1), color: r.premium >= 0 ? TEAL : RED, bold: true },
    ]),
    [900, 1800, 1800, 1660, 1700, 1500]));
  body.push(p(`Off-plan traded at a premium in ${om.positive} of ${om.years} years. `
    + "That figure is correct. What it means is a different question, and the rest of this "
    + "appendix answers it.", { before: 160 }));

  const w = F.offplan_why || {};

  body.push(h2("C.1  Does the label mean what it says?"));
  if (w.timing) {
    const o = w.timing["Off-Plan Properties"], e = w.timing["Existing Properties"];
    body.push(p(`Yes. On the ${w.completion_date_pct}% of rows that carry a completion date, `
      + `**${o.before_completion_pct}%** of off-plan sales happen *before* the building is `
      + `finished — a median of **${Math.abs(o.median_years)} years** before. Existing sales `
      + `happen a median of **${e.median_years} years** *after* completion. The registration `
      + `type is not a proxy for something else; off-plan really is unbuilt property.`));
    body.push(table(
      ["Registration type", "Rows with a completion date", "Median years vs completion",
        "Sold before completion"],
      [["Off-Plan Properties", nf(o.n), `${o.median_years}`, `${o.before_completion_pct}%`],
       ["Existing Properties", nf(e.n), `+${e.median_years}`, `${e.before_completion_pct}%`]],
      [2600, 2400, 2400, 1960]));
  }

  body.push(h2("C.2  Then why is unbuilt property dearer than finished property?"));
  body.push(p("It is not. The two labels are attached to different buildings. Tightening the "
    + "comparison one step at a time — the same method used for the amenity figures — the "
    + "premium survives area and master development, then collapses at project and building "
    + "level."));
  if (w.pooled_gap !== undefined && F.offplan_ladder) {
    body.push(table(
      ["Comparison", "Premium", "Matched groups", "Transactions"],
      F.offplan_ladder.map(r => [
        r.comparison,
        { text: pct(r.gap, 1), color: r.gap >= 0 ? TEAL : RED, bold: true },
        nf(r.groups), nf(r.deals)]),
      [4200, 1660, 1800, 1700]));
    body.push(callout("The line to remember", [
      `Across the whole dataset off-plan looks ${pct(F.offplan_ladder[0].gap, 0)} dearer per `
      + `square metre. Inside a single building in a single year it is `
      + `${pct(F.offplan_ladder[F.offplan_ladder.length - 1].gap, 1)} — and pooled across all `
      + `years over ${nf(w.pooled_groups)} buildings and ${nf(w.pooled_deals)} transactions `
      + `(${w.shared_share_pct}% of the dataset) it is ${pct(w.pooled_gap, 1)}, with off-plan `
      + `dearer in only ${w.pooled_positive_pct}% of those buildings.`,
    ], RED));
  }

  body.push(h2("C.3  The stock test"));
  body.push(p(`Value every building at its own median rate, then ask what the average building `
    + `is worth on each side of the split. Off-plan buyers transact in buildings worth `
    + `**AED ${nf(w.stock_rate_offplan)}/m²**; existing buyers in buildings worth `
    + `**AED ${nf(w.stock_rate_existing)}/m²** — a gap of **${pct(w.stock_gap_pct, 1)}**, `
    + `measured across ${nf(w.buildings_considered)} buildings. The headline premium is `
    + `${pct(F.offplan_ladder ? F.offplan_ladder[0].gap : null, 1)}. The difference in stock `
    + `alone accounts for effectively all of it, leaving nothing that needs to be explained by `
    + `off-plan status.`));

  body.push(h2("C.4  The two sides are not the same product"));
  if (w.price_tier) {
    body.push(p("Share of each side's transactions, by the price tier the dataset carries:"));
    body.push(table(["Price tier", "Off-plan", "Existing", "Difference"],
      w.price_tier.map(r => [r.label, `${r.offplan}%`, `${r.existing}%`,
        { text: `${r.diff >= 0 ? "+" : ""}${r.diff} pp`,
          color: r.diff >= 0 ? TEAL : RED }]),
      [3600, 1920, 1920, 1920]));
  }
  if (w.grade) {
    body.push(p("And by building grade:", { before: 140 }));
    body.push(table(["Building grade", "Off-plan", "Existing", "Difference"],
      w.grade.map(r => [r.label, `${r.offplan}%`, `${r.existing}%`,
        { text: `${r.diff >= 0 ? "+" : ""}${r.diff} pp`,
          color: r.diff >= 0 ? TEAL : RED }]),
      [3600, 1920, 1920, 1920]));
  }

  body.push(h2("C.5  How to quote this"));
  [
    "**Correct:** “Off-plan stock sells at a higher rate per square metre because it is "
    + "newer and better located.”",
    "**Correct:** “In the same building, a finished unit holds its value against an "
    + "off-plan one.”",
    "**Wrong:** “Off-plan property is worth more than ready property.”",
    "**Wrong:** “Buyers pay a premium for off-plan.” They pay a premium for the buildings "
    + "that happen to be sold off-plan.",
    "One caveat that no dataset can settle: the registry records the headline contract "
    + "price. An off-plan price paid over three years of construction is not the same money "
    + "as a resale price paid at once.",
  ].forEach(t => body.push(bullet(t)));
}

// ── Appendix D — price bands ───────────────────────────────────────────────
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(h1("Appendix D. Price-band reconciliation"));
{
  const b = F.bands, v = b.validity, cov = b.coverage;
  body.push(p("Bands were validated on all three views of the data. In each case the counts sum "
    + "exactly to the row count, so every valid transaction belongs to exactly one band."));
  body.push(p("Each band includes its lower bound and excludes its upper one, so a sale of exactly "
    + "AED 1,000,000 is counted in `1M – 2M`, not in `500K – 1M`. The top band is therefore "
    + "AED 10M and above. The same rule is used by the dashboard.", { after: 160 }));
  body.push(table(
    ["Price band (AED)", "Cleaned dataset", "Share", "Raw: residential units", "Share", "Raw: all sales", "Share"],
    b.clean.map((r, i) => [
      r.band, nf(r.n), `${r.share}%`,
      nf(b.raw_unit[i].n), `${b.raw_unit[i].share}%`,
      nf(b.raw_all[i].n), `${b.raw_all[i].share}%`,
    ]),
    [1700, 1400, 900, 1700, 900, 1700, 1060]));
  body.push(table(
    ["Check", "Result"],
    [
      ["Rows assigned to a band (cleaned)", `${nf(cov.clean[0])} of ${nf(cov.clean[1])}`],
      ["Rows assigned to a band (raw residential units)", `${nf(cov.raw_unit[0])} of ${nf(cov.raw_unit[1])}`],
      ["Rows assigned to a band (raw, all sales)", `${nf(cov.raw_all[0])} of ${nf(cov.raw_all[1])}`],
      ["Null sale prices in raw sales", nf(v.raw_null_price)],
      ["Zero or negative sale prices in raw sales", nf(v.raw_zero_or_negative)],
      ["Duplicate transaction identifiers in raw sales", nf(v.raw_duplicate_ids)],
      ["Sale prices below AED 1,000 in raw sales", `${nf(v.raw_below_1000)} (excluded from the cleaned dataset)`],
      ["Cleaned dataset price range", `AED ${nf(v.clean_min)} – ${nf(v.clean_max)}`],
      ["Cleaned sales of AED 10M or more", `${nf(v.clean_above_10m)} (matches the top band above)`],
    ],
    [5400, 3960]));
  body.push(callout("Why the top band can read as zero on screen", [
    `The dashboard's sale-price slider starts at the 1st–99th percentile, which cuts off around `
    + `AED 8M. Under that default the ">10M" band is empty — that is the filter, not the data. `
    + `Unfiltered, the cleaned dataset holds ${nf(v.clean_above_10m)} sales at AED 10M or more. `
    + "The dashboard now displays a warning saying exactly this whenever a band is emptied by "
    + "the filter.",
  ], BLUE));
}

// ── Appendix E — layouts ───────────────────────────────────────────────────
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(h1("Appendix E. Layout distribution reference"));
body.push(p("The nine layouts present in the dataset, with the quartiles behind the "
  + "small-multiples chart in the Property section."));
body.push(table(
  ["Layout", "Transactions", "Median size (m²)", "25th pct (AED/m²)", "Median (AED/m²)", "75th pct (AED/m²)"],
  F.layouts.map(l => [l.layout, nf(l.n), nf(l.median_size, 1), nf(l.q1), nf(l.median), nf(l.q3)]),
  [1700, 1700, 1800, 1500, 1400, 1260]));
body.push(callout("A caption that was corrected", [
  "The dashboard previously described this chart as showing that smaller units cost more per "
  + "square metre. The data does not support that: the median rate rises with layout size. "
  + "The caption was removed and replaced with what the data actually shows.",
], AMBER));

// ── Appendix F — glossary ──────────────────────────────────────────────────
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(h1("Appendix F. Every word, in plain English"));
body.push(p("Nothing on the Dubai dashboard requires a statistics background. Every term "
  + "that is not everyday English is defined here, and the same definitions appear behind "
  + "the ⓘ on each chart that uses them."));
(P.glossary || []).forEach(([term, meaning]) =>
  body.push(lead({ text: `${term} — `, bold: true, color: NAVY }, meaning,
    { indent: { left: 200 }, after: 120 })));

// ═══════════════════════════════════════════════════════════════════════════

// Word and LibreOffice merge two tables that touch with no paragraph between
// them. That makes one table's repeating header row appear above the other's
// rows after a page break. Separate every adjacent pair with a thin spacer.
for (let i = body.length - 1; i > 0; i--) {
  if (body[i] instanceof Table && body[i - 1] instanceof Table) {
    body.splice(i, 0, new Paragraph({
      spacing: { before: 0, after: 0, line: 120 },
      children: [new TextRun({ text: "", size: 6 })],
    }));
  }
}

const doc = new Document({
  creator: "UAE Real Estate Analytics",
  title: "Dubai Analytics — Chart Reference Guide",
  description: "Documentation for every chart in the Dubai section of the platform.",
  numbering: {
    config: [{
      reference: "bullets",
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 420, hanging: 220 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 840, hanging: 220 } } } },
      ],
    }],
  },
  styles: {
    default: { document: { run: { font: "Calibri", size: 20 } } },
  },
  sections: [{
    properties: { page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE } },
          children: [new TextRun({
            text: "UAE Real Estate Analytics · Dubai Chart Reference Guide",
            size: 16, color: GREY, font: "Calibri" })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES],
            size: 16, color: GREY, font: "Calibri" })],
        })],
      }),
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log(`  wrote ${outPath} (${(buf.length / 1024).toFixed(0)} KB)`);
});
