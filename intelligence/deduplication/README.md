# Stage 7 v1 content duplication

This stage reads immutable `CleanArticle` rows and adds positive content
relationships. Shared topics, events, projects or sources are not evidence of
duplication. `NOT_DUPLICATE` is returned by comparison but not stored. No source
record is merged, deleted or rewritten.

## Representation and exact eligibility

Each title and body is NFC-normalized, casefolded, NFC-normalized again, then
Arabic/Persian digits become ASCII, curly single/double quotes become straight
quotes, and U+2010..U+2014 dashes become ASCII hyphens. All whitespace, including
paragraph breaks, collapses to one space. Other punctuation, word order and
all words remain. Mathematical minus is not mapped. This affects comparison
strings only; Stage 6 text stays intact.

The exact fingerprint is SHA-256 over UTF-8 compact JSON `[title,body]`, with
`ensure_ascii=False`, separators `(',', ':')`, and no trailing newline. JSON
escaping separates the two fields unambiguously. Equality also checks both
normalized strings, not just hashes.

Exact classification needs at least 12 body tokens containing a letter/number
and 80 body characters. Title-only, empty and tiny-body records receive no
positive relationship, even with equal fingerprints. An absent title is safe
for exact matching when the body meets these requirements.

## Conservative Stage 7 v1 threshold

Near comparisons need at least 40 body words, 240 body characters and three
title whitespace tokens on each side. Body length ratio must be at least 0.90.
Use only RapidFuzz `fuzz.ratio`, on title and body separately, with no processor.
Title must score at least 90, body at least 97 and `0.2*title + 0.8*body` at least
96. All boundaries are inclusive on unrounded scores. No token-set scoring.

Before fuzzy scoring, reject changed counts of explicit negation tokens
(`no/not/never/neither/nor/without`, English `n't` endings, and
`لا/لم/لن/ليس/ليست/غير/بدون`) or a changed ordered sequence of numeric-bearing
word tokens. Apply these checks separately to title and body. These are lexical
vetoes, not semantic understanding or structured number extraction. No guard
can guarantee equivalent meaning; changed names or an unrecognized opposite
may still score highly. False negatives are preferable to aggressive merging.

Thresholds were selected after scoring the fixed synthetic cases in
`intelligence/tests/fixtures/deduplication.py`:

| Category | Title ratio | Body ratio | Weighted ratio |
|---|---:|---:|---:|
| Exact / formatting | 100 | 100 | 100 |
| Minor headline/body edits, small added paragraph | 94.52–100 | 97.67–100 | 98.13–99.58 |
| Same headline, different body | 100 | 45.56 | 56.45 |
| Same event/project/developer/topic or unrelated | 37.04–60.99 | 45.23–46.38 | 43.59–49.30 |
| Large addition / containment | 100 | 66.61–80.66 | 73.29–84.53 |
| Inserted negation | 100 | 99.74 | 99.79 (vetoed) |

These are synthetic fixture measurements, not production precision/recall.
The historical 292-record runtime corpus is unavailable. Material changes to
normalization, guards, thresholds, candidate policy or canonical ordering need
a new `DEDUP_VERSION`. Existing versioned results are never overwritten.

## Candidates and time

Exact fingerprint buckets have no date limit. Near candidates share an exact
normalized-title hash or at least one of the eight smallest SHA-256 hashes of
five-word body shingles. Inverted postings generate candidates; minimum
content, body-length ratio and a seven-day inclusive window filter them before
fuzzy scoring. The primary timestamp is normalized publication; fallback is
aware retrieval. If neither is established, the time gate is bypassed. No date
or zone is invented. Same-source and cross-source records follow identical
rules, including versions sharing an article ID but having different raw hashes.

Each run processes one cleaning version (default `stage6-v1`). Different
cleaning versions are independent cohorts and retain their historical results.
`--since YYYY-MM-DD` selects retrieval anchors at/after UTC midnight. Candidate
records include the entire compatible cleaning cohort, so an anchor can match
an older article under the existing exact/near rules. Only pairs touching an
anchor are evaluated. Stored positive edges still contribute to groups.
`--cleaning-version VERSION` selects another existing cohort. The cutoff is
stored in `pipeline_run_owners`; naive retrieval values cannot be anchors.

The sketch can miss near copies, especially extensively edited short texts.
There is no arbitrary bucket cap. Repetitive corpora can still generate dense
candidate sets; storing all positive pairs in an exact group is inherently
quadratic. All selected cleaned rows and postings currently fit in memory.

## Groups, canonical records and transactions

Pairs are ordered lexically by `(article_id, raw_hash)` inside a cleaning/dedup
version. SQL checks reject reversed/self pairs and foreign keys reference both
immutable cleaned identities. Only positive edges form connected components.
Group membership is transitive; it does not assert every member pair passed
direct comparison. Singletons are not duplicate groups.

Canonical order is: established publication before absent publication, earliest
publication, greatest normalized body word count, then lexical article/raw
identity. Source trust is not used. This selects a stable representative, not
a factually authoritative record.

Group IDs hash compact JSON `[cleaning_version,dedup_version,sorted_members]`.
Membership growth produces a new immutable snapshot, preserving earlier groups.
`dedup_run_groups` links each run to its evaluated snapshots;
`groups_for_run(conn, run_id)` retrieves them without mixing old memberships.

The shared additive schema supports empty/v0.1/v0.2/v0.3/v0.4 databases and rejects
unknown versions. Stage 7 reads a consistent snapshot, releases its read
transaction, computes without a SQLite writer lock, then rechecks the cleaned
signature and stored positive pairs in `BEGIN IMMEDIATE`. Changed input aborts
publication for a safe explicit retry. New pairs, group links and successful
final log commit atomically. The signature recheck still takes O(N) time under
the writer lock. Malformed rows are isolated; structural errors roll back all
new results and finalize a failed log separately.

A bounded POSIX advisory pipeline lock serializes cooperating runs. On startup,
old owned RUNNING logs are reconciled to FAILED/AbortedRun after one hour. An
active owner retains its OS lock regardless of age; SIGKILL releases that lock.
Legacy unowned RUNNING logs are not changed because their liveness is unknown.

`SUCCESS` includes an empty cohort. Isolated record errors produce
`PARTIAL_SUCCESS` when valid records remain, otherwise `FAILED`. Fatal processing
errors produce `FAILED`. Logs contain counts and at most 100 exception-type/row-
ordinal details, never article bodies. Exact/near counters count positive
candidate classifications, including existing pairs; inserted counters reflect
new committed results. Fuzzy comparisons count pairs, each with two ratio calls.

Run offline with `python3 -m intelligence.pipeline.run --dedupe-only --json`.
Exit codes: 0 success, 1 partial/failure, 2 invalid CLI usage. This path never
invokes ingestion, cleaning, raw storage, probes or network clients.
