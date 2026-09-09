# Stage 13 — serving intelligence, market movements and rankings

This is merged Stage 13 of the 18-stage roadmap. It consumes stored Stage 12
results, their anchored Stage 3–11 evidence and existing raw URL pointers.
It runs offline and never imports or changes the existing dashboards.

## Run and publication contract

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.pipeline.run --build-intelligence-only --json
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_intelligence
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_pipeline
```

The production command writes the configured intelligence database. Validation
commands instead use temporary roots, with all network entry points blocked.
The nine CLI modes are mutually exclusive. Fetch flags and `--since` are
rejected for Stage 13. Exit 0 means a complete successful publication; exit 1
means build failure and exit 2 means incompatible arguments.

`intelligence_current` selects exactly one complete build. Consumers should
read this pointer and all required tables within **one SQLite read transaction**
to avoid combining builds if publication occurs between queries. The news and
three observation-family views select the current build automatically.

The builder opens an upstream read snapshot; validates the stored accepted
Stage 8/9 gates, canonical context, versions, entity/event lineage, exact clean
offsets and Stage 12 observation identities; then computes outside the write
transaction. `BEGIN IMMEDIATE` rechecks the snapshot and raw URLs before
inserting all serving rows, movements, rankings, run membership and CURRENT.
Any error rolls back that entire publication. The failed operational run is
logged separately; the previous build remains available. No partial serving
build is published. Cooperating Stage 13 writers hold the existing local
pipeline ownership lock; upstream writers may proceed during computation.

Schema v0.9 adds 14 tables (45 total), views, indexes and gate triggers.
Migrations accept fresh databases and v0.1–v0.9, are repeatable and roll back
DDL and the version stamp together. Unknown versions are refused. No existing
evidence rows, tables or columns are replaced.

## Serving and provenance

`intelligence_articles` references the Stage 12 result, which references the
Stage 11 result, Stage 10 extraction, accepted Stage 9/8 context and cleaned
article. The original article ID/raw hash joins raw sightings and JSONL
file/line evidence. Article projections retain source ID/name, RSS URL,
publication time, retrieval time and article URL. The original clean model
has no URL field, so the URL is read from confined raw sighting pointers in
one streaming pass per file. Missing pointers produce an explicit NULL URL
and a log counter, never an invented URL. No `raw_payload` is copied.

Article entity links reference original Stage 10 mention offsets and canonical
IDs. Event projections reference original Stage 11 event IDs; event links
remain clause-specific. The existing immutable entity registry supplies names
and geographic ancestry. Article scope includes all seven emirates,
UAE_WIDE, MULTI_EMIRATE and UNKNOWN. Observation geography is selected from
its own Stage 12 links: the single most specific entity on one registry branch.
Conflicting geographic branches stay UNKNOWN. An article's MULTI_EMIRATE label
never overwrites the separate Dubai and Abu Dhabi clauses.

The SQL article gate independently requires accepted upstream decisions;
foreign-only real-estate articles remain in operational evidence and cannot
enter the serving build. Child FKs and parent-consistency triggers preserve
the same accepted article ancestry. Publisher nationality is irrelevant:
an accepted BBC article about UAE property is included.

`intelligence_observations` contains serving dimensions and references the
original Stage 12 observation. `intelligence_facts` joins its exact Decimal
TEXT values, units, currency, statistics, reported period/value text, qualifier,
direction, offsets, evidence and source metadata. The PRICE, RENT and
TRANSACTION views cover all 13 Stage 12 metrics. Forecasts and source-reported
percentage changes stay queryable with `SOURCE_REPORTED` provenance.
Calculated movements use `SYSTEM_CALCULATED` and their two observation IDs.
For example a reported 12% and a calculated 10% are both retained.

## Periods and comparability

Only literal observation period evidence is resolved:

| Evidence | Frequency | Period |
|---|---|---|
| August 2026 | MONTHLY | 2026-08 |
| Q2 2026 | QUARTERLY | 2026-Q2 |
| 2025 / in 2025 | ANNUAL | 2025 |

English full month names and optional `in`, `during`, `for` prefixes are
supported. Relative periods, CURRENT, half-years, ambiguous ranges and unknown
text remain unresolved and queryable. Publication/retrieval time is never a
period fallback. This deliberately conservative coverage can be extended only
with fixtures and a new build policy/version.

Series keys hash canonical entity ID, hierarchy level, emirate scope, source,
metric, property type, statistic, currency, unit, observation nature and
frequency. Thus average/median, sqft/sqm, annual/monthly rent, rent/yield,
transaction value/volume, property types, currencies, sources and hierarchy
levels never mix. Unspecified property/statistic values occupy their own
buckets and are never mapped to a specific segment. Rental-yield movements
are relative percentage changes of a yield level, not percentage-point changes.

Forecasts, source-reported changes, non-exact qualifiers, unresolved periods
and ambiguous geography do not form historical series. No accepted outlier
is silently trimmed; exact comparable extreme values remain eligible.

Distinct observations at the same source/series/period are all preserved but
that period is blocked as `SOURCE_CONFLICT`, even if their values agree.
Neither publication time nor an arbitrary identity selects a winner. Different
sources always have separate series; no averaging or implicit hierarchy.

## Movement arithmetic and labels

Monthly series support adjacent-month MoM and matching-month YoY; quarterly
series support adjacent-quarter QoQ and matching-quarter YoY; annual series
support previous-year YoY. Year rollovers are ordinary adjacent ordinals.
No gaps are bridged. Missing comparisons and zero denominators create explicit
`market_movement_unavailable` reasons, never fake zero/Infinity movements.
A real current zero against a positive denominator is a valid −100% change.

Formula: `100 × (current − previous) / previous`. Source values remain exact;
subtraction and multiplication use sufficient precision for both operands.
Only division rounds, to 50 significant Decimal digits with ROUND_HALF_EVEN.
No binary float or early display rounding is involved. Movement IDs bind
series, current/comparison observation IDs, basis, movement version and policy.

Default `MovementPolicy` is centrally defined and configurable via a validated
immutable policy object. Its version, thresholds, precision and rounding rule
are persisted with each build and included in identity:

| Change | Classification |
|---|---|
| ≥ +10% | STRONG_INCREASE |
| > +0.5% and < +10% | INCREASE |
| −0.5% through +0.5%, inclusive | STABLE |
| > −10% and < −0.5% | DECREASE |
| ≤ −10% | STRONG_DECREASE |

These are descriptive magnitude labels, not statistical significance. The
read-only dashboard audit found no authoritative existing five-class policy.
Dashboard aggregate/yearly/partial-year formulas retain their existing behavior;
RSS observations do not substitute for the dashboard datasets.

## Rankings and identity

Rankings use calculated movements only. Dimensions include metric, property,
statistic, currency, unit, source, nature, frequency, current period, comparison
basis, hierarchy level and peer scope. Emirate peers share UAE_WIDE; area,
community, project and building peers remain within their emirate and own
hierarchy. Country-only and UNKNOWN/MULTI_EMIRATE geography are excluded.
Single-entity groups are retained with candidate counts; rank 1 does not imply
broad market coverage.

Positive changes rank descending; negative changes rank ascending (largest
decline first). Zero is excluded. A small nonzero change within the STABLE
label band may rank by its actual sign: the magnitude label does not erase
the numeric movement. Decimal values are sorted without converting to float.
Ties use competition ranks (1, 1, 3), with canonical entity ID as deterministic
ordering and a separate unique position. Rank IDs include all dimensions and
ranking/movement/policy versions. Raw source percentages never enter rankings.

Build identity binds the semantic Stage 12 cohort, upstream semantic model content (excluding operational evaluation times),
available URLs, all versions and movement policy. Operational rerun UUIDs are
not semantic content: repeating Stage 12 on unchanged evidence reuses the
same Stage 13 build without movement/ranking work. Changed cohorts or versions
produce a new retained build. A run log anchors the selected Stage 12 run even
when it reuses an earlier build. No historical observations are overwritten.

## Logging, performance and next-stage boundary

Runs log all 12 transformation/registry versions, cohort/build/run IDs, times,
status, accepted/excluded article counts, observation-family counts, forecasts,
resolved/unresolved periods, series, MoM/QoQ/YoY, missing/zero/conflict reasons,
rankings/candidates/directions, reuse and bounded component diagnostics.
Indexes cover current news by time/source/scope/entity, event type/entity,
observation dimensions and series/period, movement basis/class and rankings.
EXPLAIN checks assert indexed searches for representative parameterized queries.

Computation uses a series/period lookup map, at most two lookups per observation,
and deterministic sorting. It is O(n log n) overall, with O(n) indexing and
memory; there is no all-pairs comparison. Tests exercise 100/500/1000 observations
with operation counts; timing measurements are descriptive, not brittle gates.

Stage 14 may consume the current build, views, original evidence joins and
structured movement/ranking tables within a read transaction. This stage
implements no intent router, intelligence actions, suggested prompts, chat,
summary, retrieval-to-LLM, Ollama or UI integration. Stages 15–17 remain model,
grounded-answer and testing work; Stage 18 integrates the existing website.
Synthetic fixtures establish correctness of supported contracts; they do not
establish that real RSS feeds contain enough comparable historical observations.
