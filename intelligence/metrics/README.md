# Stage 12 — Price / Rent / Transaction Extraction

`METRIC_EXTRACTION_VERSION=stage12-v1`; shared additive schema `v0.8`.

Stage 12 consumes the latest completed SUCCESS/PARTIAL_SUCCESS Stage 11 run
matching all eight upstream versions. It follows that run's exact Stage 10,
9 and 8 cohort provenance, validates their stored acceptance/context/identity,
and reads canonical CleanArticle evidence. A zero-event Stage 11 result is
eligible: an explicit price level need not describe a directional event.
There is no fetching, upstream reclassification, entity discovery, event
re-extraction, LLM, dependency installation or application integration.

## Representation and taxonomy

Frozen `MarketObservation` and `MetricExtractionResult` models live in
`intelligence/schemas.py`; controlled dimensions live in `enums.py`.
The result preserves source ID, article/raw identity, all upstream versions,
canonical group/context, entity extraction ID, event result ID and location
scope. Observations reference this lineage-bearing result. The result reuses
Stage 11's lineage validation and requires its inherited `events` tuple to be
empty; existing event instances remain exclusively in Stage 11 tables.

The 13 metric types are SALE_PRICE, AVERAGE_SALE_PRICE, MEDIAN_SALE_PRICE,
SALE_PRICE_PER_SQFT, SALE_PRICE_PER_SQM, RENTAL_PRICE, ANNUAL_RENT, MONTHLY_RENT,
RENTAL_YIELD, PRICE_CHANGE_PCT, RENT_CHANGE_PCT, TRANSACTION_VALUE and
TRANSACTION_VOLUME. Average/median are additionally retained in `statistic`,
including rent and per-area observations, without inventing derived averages.

Reported and normalized values are finite `decimal.Decimal`; Python floats
and integers are rejected at the observation model boundary. JSON and SQLite
use canonical, non-exponential decimal TEXT. Conversion is exact even beyond
28 digits, with a bounded local precision of 40. Signed source changes preserve
the original numeral separately from the normalized direction. An unsigned
reported decline of 5% becomes -5; `fell by -5%` is rejected as contradictory.
Explicit signed changes are accepted; a stable event alone creates no zero.
Zero requires an explicit numeral and compatible stable wording/sign.

AED (including Dh/Dhs/درهم/دراهم), USD, EUR and GBP require explicit adjacent
currency text. Bare dollar symbols and unrecognized currencies are unsupported.
No FX conversion occurs. English thousands grouping and decimal notation,
Arabic/Persian digits and Arabic numeric separators are bounded and exact.
Ambiguous `1.500`, malformed grouping, and lowercase `m` fail closed. Thousand,
million, billion, K, M, MN and BN are normalized; original numeric/scale text
and scale enum are retained. Up to 24 source digits and six fractional digits
are accepted. Ranges and starting-from prices are intentionally unsupported.
Approximate/greater-than/less-than qualifiers must be adjacent to the amount
(optionally separated by its currency); qualifiers describe the reported
magnitude, including when a decline is normalized to a negative change.

Money, money/sqft, money/sqm, percent and transaction counts remain distinct.
No area conversion, monthly-to-annual multiplication or unit inference occurs.
Property types retain apartment, villa, townhouse, land, office, retail,
warehouse, residential and commercial terminology, with UNKNOWN for generic
property. Existing read-only application conventions were inspected:
`regions/dubai_market/data.py` maps `actual_worth` to AED totals and
`meter_sale_price` to AED/m²; `regions/abu_dhabi/config/settings.py` explicitly
maps Property Sale Price (AED), Property Sold Area (SQM), Rate (AED per SQM)
and Property Type. Stage 12 does not join or rewrite these application datasets.

## Context, evidence and association

Rules split original clean title/body at nonnumeric punctuation and bounded
conjunctions; numeric commas/decimal points remain intact. They require an
explicit metric subject near each numeral. Nearest numeric subjects separate
price, rent, yield and transaction numbers even within a single clause.
Revenue/profit, development costs, mortgage values, GDP, interest, hotel room
rates, salaries, stock prices and similar collisions suppress the clause.
Negation suppresses extraction. A count needs an adjacent transaction noun or
explicit transaction-count/volume subject. Supply counts never become sales.

Ordinary unsigned price/rent changes require a same-clause matching Stage 11
event. Explicit numeric forecast, historical and signed-change grammar are
bounded exceptions because Stage 11 v1 deliberately suppresses historical or
forecast observed-change events and does not classify signs alone. They do
not modify upstream events. Transaction amount/count grammar is a second
explicit exception: Stage 11 v1 does not cover every numeric formulation,
including `transactions reached AED 50 billion`. Price levels and rental
yields require their own explicit context and may have no associated event.
These exceptions still require an accepted stored Stage 11 result.

Matching change/transaction events and applicable MARKET_OUTLOOK events are
linked only within the observation clause. Entity links use Stage 10 mention
indices, original offsets and the existing maximum 12-token proximity policy.
No article-wide entity assignment or parent inference occurs. Different
clauses retain different emirates/areas. Omitted subjects/pronouns never
inherit entities across clauses. Unsplit clauses with competing emirates or areas/communities fail closed;
a cross-clause resolution engine is outside this version.

OBSERVED and SOURCE_REPORTED_FORECAST remain separate dimensions. Forecast,
expected, projected, future tense and explicit next-period wording preserve
source predictions without generating predictions. Period basis is explicit
MOM/QOQ/YOY/MONTHLY/QUARTERLY/ANNUAL/CURRENT/UNKNOWN; reported month/year,
quarter/year, half-year and relative-period text is preserved literally.
No resolved dates or time-series arithmetic are inferred. Rental annual/monthly
basis describes the rent level's reporting period; comparative percentage bases
remain on separate change observations.

Every observation stores exact clean field/clause offsets and evidence, plus
its exact numeric substring offsets. `text[start:end] == matched_text` is
validated. Title confidence is HIGH; body confidence MEDIUM. LOW is absent.
Identical title/body clause facts deduplicate only with matching complete
semantics and entity IDs; the title evidence/links are retained. Repeated body
spans, differing clauses, entities, types, periods or nature stay distinct.
This conservative policy intentionally does not collapse paraphrases.

Result IDs bind Stage 11 result ID and extraction version. Observation IDs
bind their result, exact value, original numeral/scale, all dimensions,
qualifiers, nature, rule, evidence offsets/text and entity/event associations.
Evaluation timestamps do not change IDs. Both models validate their hashes.

## Storage and operations

Six additive tables bring the operational schema to 31 tables:

- `metric_extraction_results`: immutable versioned per-context result.
- `market_observations`: exact numeric TEXT, dimensions and evidence.
- `observation_entity_links`: normalized Stage 10 mention references.
- `observation_event_links`: normalized Stage 11 event references.
- `metric_run_log`: versions, Stage 11 cohort, counters, timing/status/errors.
- `metric_run_results`: canonical result membership for every run, including reruns.

Foreign keys bind observations, both association types and upstream contexts.
Readback checks counts, ordering, identities, numeric representation and link
lineage. Initialization accepts empty and v0.1–v0.8 databases, rejects unknown
versions and rolls back DDL plus version stamping on error. Existing tables
and historical rows are preserved; one additive unique event-context index
supports the Stage 12 composite event foreign key.

The metrics advisory lock spans the entire run. Snapshot reads happen in a
read transaction; extraction follows outside any transaction. Publication uses
BEGIN IMMEDIATE, recomputes the same full upstream snapshot signature and
atomically inserts results/observations/links/run membership plus final log.
Changed upstream evidence aborts all pending output. Individual malformed
contexts are isolated. Errors expose only type and ordinal, capped at 100,
while total errors remain counted. Shared ownership recovers old abandoned
metric runs and leaves recent/unowned runs untouched. Other pipelines remain
free to write, with snapshot validation handling changes. Identical reruns
reuse canonical rows/timestamps and make zero extraction calls. New versions
retain separate histories.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.pipeline.run --metrics-only
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.pipeline.run --metrics-only --json
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_metrics
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_pipeline
```

The CLI has eight mutually exclusive modes. Metrics rejects fetch options and
`--since`; it supports `--cleaning-version` with the existing configured
upstream versions. Errors/partial success return a nonzero exit status.
All validation writes use temporary roots and disable bytecode generation.
The permanent pipeline's numeric fixtures use actual local RSS/Atom bytes and
all existing producers from Stage 3 onwards, with manually asserted numeric
expectations, full lineage, immutability and failure localization.

Coverage is a deterministic synthetic corpus, not a real-world accuracy claim.
The earlier 292-article feed corpus is absent; it was not fetched. Arabic
support is deliberately bounded to reviewed price/rent/transaction words,
digits and currencies. Unsupported/ambiguous expressions remain unstructured.

## Merged Stage 13 boundary

The current roadmap contains 18 merged stages. The next stage is **Merged
Stage 13 — Intelligence Database + Market Movements + Increase / Decrease
Rankings**. It can consume these versioned, provenance-backed observations.
Stage 12 performs no aggregation, monthly snapshots, comparison engine,
calculated MoM/QoQ/YoY, movement classification or rankings. Only percentages
explicitly reported by sources are extracted. No final intelligence database,
UI, application integration, commit or push is part of Stage 12.
