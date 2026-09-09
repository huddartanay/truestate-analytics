# Stage 8: real-estate relevance

This offline stage answers whether cleaned article content directly concerns
property or real-estate market activity. It has no geography requirement and
does not perform Stage 9 UAE relevance. No entity extraction, market events,
final intelligence schema, UI, networking or LLM integration is introduced.

## Contract and scoring

`classify(CleanArticle)` returns a frozen `Decision`. It uses no clock, random
state, article/source identity, source trust or location. `RealEstateRelevanceResult`
adds immutable canonical identity, raw hash, cleaning/dedup/relevance versions,
context hash, optional group ID and caller-supplied aware evaluation timestamp.
Evaluation time is operational metadata, not a classification input.

`RELEVANCE_VERSION = stage8-v1`; acceptance is **score >= 3** for all locations.
Material future changes to rules, normalization or scoring require a new version.
The legacy local/international config thresholds are not used by this stage.

| Score | Rule, in precedence order |
|---|---|
| 5 | High-precision title phrase plus a focused body spanning at least two categories |
| 4 | High-precision title; or title property-type/activity co-occurrence plus focused body; or body with at least three categories and density >= 0.05 |
| 3 | Title property-type/activity co-occurrence; or focused body with at least two distinct phrases in at least two categories and density >= 0.03 |
| 2 | Some high-precision body phrase or contextual property activity, without enough focus/diversity |
| 1 | Weak terminology only |
| 0 | No qualifying signal after safeguards |

Density is the number of token positions covered by surviving high-precision
phrases divided by all normalized body tokens. Nested phrases count a position
once. Suppressed/background sentences remain in the denominator. Thresholds
express an explicit precision preference: two property categories and at least
3% evidence-bearing tokens for body-only acceptance; three categories and 5%
for a stronger body-only score. They are conservative fixture choices, not
production-calibrated boundaries. Repeated weak words never accumulate points.

Categories: property market, sales/transactions, rentals, development, supply,
mortgages, investment/yield and regulation. `rules.py` centrally contains the
finite lexicon, weak terms, collision masks and same-clause contextual vocabulary.
`config.py` contains version, score boundary, density thresholds, 12-word context
window and 24-signal bound. A title match is stronger than one body mention.

Confidence is a rule-strength label: HIGH for 0/4/5, MEDIUM for 3, LOW for 1/2.
It is **not a probability, statistical calibration or measured accuracy**.
Unknown/uncovered language can produce score 0; HIGH there means no configured
signal survived, not certainty that a human would reject the article.

## Safeguards and language

NFKC, casefold, punctuation/hyphen spacing, Arabic diacritic/tatweel removal and
bounded alef normalization are applied only to temporary classifier text.
English and a finite Arabic phrase set are searched regardless of the Stage 6
language label. Mixed and unknown inputs remain safe; no translation or stemming
is performed. Arabic coverage is narrower, particularly attached prefixes,
inflection and regional vocabulary. Other languages are not comprehensively
covered. These are documented recall limits.

Intellectual/software/object/material property phrases are masked before
positive matching. Company-background, agricultural/conservation, humanitarian
shelter and employee-accommodation sentences are conservatively suppressed.
Generic macroeconomics, company names and infrastructure supply no positive
points. A road construction phrase between a housing type and construction
action blocks that contextual match. Direct mortgage, housing, development or
rental focus still qualifies alongside economics/infrastructure. Bare commercial
projects and data-center development are insufficient without property context.

Evidence is bounded to 24 unique signals per polarity, each <=120 characters.
Signals contain fixed lexicon phrases/category IDs and title/body location, never
article excerpts. Reason text is <=240 characters and records the selected rule,
category counts and body density. No chain-of-thought or duplicated body text.

## Canonical context and provenance

The pipeline reads one completed Stage 7 run (SUCCESS or PARTIAL_SUCCESS) for
the requested cleaning/dedup versions, ordered by completion time then SQLite
rowid. It uses only that run's immutable group snapshots, avoiding overlapping
historical memberships. Each stored canonical is classified once. Ungrouped
cleaned records are singletons, including new rows not present in an older
dedup snapshot. No deduplication runs implicitly; unseen duplicate relationships
can therefore cause repeated classification until Stage 7 is explicitly run.

Group IDs and canonical selection come from Stage 7 and are never rewritten.
Results link to immutable group snapshots and cleaned identities. Members and
source references remain available through `members_json` and cleaned rows.
The context hash binds `[cleaning_version,dedup_version,group_id,article_id,raw_hash]`.
Changed membership or canonical/version policy creates a distinguishable result;
historical results remain. A malformed group member skips its entire group while
healthy standalone inputs continue. Unparseable/overlapping memberships stop
publication because safe singleton membership cannot be established.

`--since` means **any group member's retrieved_at >= cutoff**, or the singleton's
retrieval time. It can select an older canonical through a new duplicate member.
Unknown naive retrieval values under a cutoff are isolated as errors. Without
a cutoff they are preserved, never assigned a timezone. No filtering on publication
date or source geography. This filter still requires reading the full cohort.

## SQLite, concurrency and logs

Shared additive schema v0.4 adds `real_estate_relevance`, `relevance_run_log`,
`relevance_run_results` and Stage 8A's `pipeline_run_owners` (13 operational tables
total). Fresh/v0.1/v0.2/v0.3/current schemas are supported; unknown versions are
rejected and DDL/stamp changes roll back together on errors. No Stage 13 schema.

Result identity is `(article_id,raw_hash,cleaning_version,dedup_version,
relevance_version,context_id)`. Parameterized insert-on-conflict preserves old
decisions and timestamps; matching existing keys skip classifier work. SQL score
and acceptance checks, primary keys and foreign keys protect stored identities.
`relevance_run_results` records both new and reused results for each run.

The same bounded whole-run POSIX advisory lock/ownership convention as cleaning
and deduplication prevents active-run takeover. Startup reconciles only owned
RUNNING rows older than one hour, after acquiring exclusive pipeline ownership.
FAILED/AbortedRun is the equivalent of an aborted status in existing contracts.
Completed and legacy unowned logs are untouched. OS lock release handles process
death; no SIGKILL cleanup or distributed-filesystem safety is claimed.

Read snapshot → release transaction → compute → BEGIN IMMEDIATE → verify cleaned
signature and canonical context → atomically publish results, links and final
success log. Changed inputs raise SnapshotChanged and require an explicit retry.
Structural failure rolls back new results and logs FAILED separately. A failure
of final logging itself can leave RUNNING until subsequent owned-run recovery.

`records_seen` counts selected-version input rows before cutoff; `canonical_records_seen`
counts eligible canonical/singleton contexts. Relevant/irrelevant counts describe
new committed results; skipped counts describe existing results. Failed count is
failed input/context/operation events, so a malformed member and affected group
may each contribute. These counters are not asserted to sum to records_seen.
Fatal rollback resets committed-result counters to zero. Logs retain at most
100 type/ordinal errors plus the full error count, never arbitrary exception text.

## CLI and verification

The four modes are mutually exclusive:

```sh
python3 -m intelligence.pipeline.run --fetch-only
python3 -m intelligence.pipeline.run --clean-only --since 2026-09-07
python3 -m intelligence.pipeline.run --dedupe-only --since 2026-09-07
python3 -m intelligence.pipeline.run --relevance-only --since 2026-09-07 --json
```

Only fetch mode can acquire data. These examples are documentation, not production
commands run during implementation. Dedup/relevance accept `--cleaning-version`.
Exit codes: 0 SUCCESS, 1 PARTIAL_SUCCESS/FAILED, 2 invalid CLI usage. Versions are
also selectable through the Python API. Relevance has no automatic upstream stage.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_issue_fixes
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_relevance
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_stage8_regressions
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m intelligence.tests.verify_stage8_regressions --application
```

Suites use temporary databases/raw fixtures and deny network connections. A fresh
interpreter CLI check asserts acquisition, raw readers, cleaner and dedup comparator
are not imported. Corpus labels cover the required 55 cases plus adversarial,
Arabic, mixed and unknown examples. Synthetic checks exercise score 0–5, constraints,
canonical/version changes, migrations, failures, immutability and call counts.

Classification calls scale with eligible canonical contexts: 50/100/200 standalone
records require 50/100/200 calls; reruns require zero; 50 syndicated members require
one. Text matching uses a fixed lexicon and bounded proximity patterns; token-span
lookups use binary search. No article-pair comparisons occur in Stage 8. Snapshot,
cohort and pending-result memory still scale with input size; signature rechecks
hold a writer lock for O(N) input work. This is an SQLite MVP, not a streaming or
distributed platform. No production latency or precision/recall claims are made.

The historical 292-article corpus and some application regression inputs are absent.
No data was fetched or fabricated to resolve those environment limitations.
