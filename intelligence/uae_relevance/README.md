# Stage 9: UAE real-estate relevance

Stage 9 consumes **accepted, stored Stage 8 contexts** and asks whether their
property subject has a meaningful UAE connection. It does not run Stage 8,
fetch content, infer causality, extract entities, or integrate with the UI.

## Contract

`classify(CleanArticle, RealEstateRelevanceResult)` is pure and returns a frozen
`Decision`. It rejects ineligible or mismatched identities and unknown registry
sources. `UAERealEstateRelevanceResult` adds the full Stage 8 key, optional group
reference, `uae_relevance_version`, `registry_version`, and an aware operational
timestamp. Stage 8 model and algorithm are unchanged.

The result contains score, acceptance, confidence, source policy/threshold,
bounded positive/exclusion evidence and a reason. No emirate, city, area,
community, project, building, or developer output fields are present. A
`geo:dubai` rule label is relevance evidence, not an extracted entity.

## stage9-v1 scoring (precedence order)

| Score | Exact rule |
|---|---|
| 5 | Direct title geo/property proximity and direct body evidence covering at least 15% of body tokens |
| 4 | Direct title geo/property proximity; or at least two distinct direct body sentences covering at least 25% of body tokens |
| 3 | At least one direct body sentence covering at least 15% of body tokens |
| 2 | Direct body proximity exists but falls below the 15% focus threshold |
| 1 | UAE geography or ambiguous UAE terminology survives only as weak/incidental context |
| 0 | No UAE geographic property connection |

Local source acceptance is **>=3**. International acceptance is **>=4**. Source
policy comes from Stage 3: country `AE`, non-international region, and non-Tier-3
source are local; other registered sources use the stricter policy. Unknown
sources fail closed. Country/region/tier data is not copied into a new registry.
The legacy environment thresholds do not change this versioned policy.

Source origin supplies no points. A local publisher's foreign-property story
stays rejected. Only the canonical article's source determines threshold;
adding a local syndicated member cannot invent article-level UAE evidence.
Registry version is part of the persisted key so changed source policy metadata
can coexist with previous results. Material rule changes require a new
`UAE_RELEVANCE_VERSION`; changing static thresholds without a version bump is
unsupported.

Confidence is HIGH for scores 0/4/5, MEDIUM for 3, LOW for 1/2. These are rule
strength labels, not calibrated probabilities. HIGH at score 0 means no covered
UAE connection was found, not certainty about every language or possible name.

## Evidence and context

Temporary normalized text uses the existing Stage 8 NFKC/casefold, punctuation,
Arabic diacritic/tatweel and alef normalization. No stored clean text is changed.
The Stage 8 positive property lexicon and property-type/activity matcher are
reused, with a small explicit Stage 9 supplement. Stage 8's accepted identity
and version are mandatory; geography never bypasses the topic gate.

Title and body are scanned separately. Matches cannot cross sentence endings,
semicolons, or newlines. A geographic phrase and a property phrase must have
at most **8 intervening normalized tokens** in the same sentence. Commas stay
inside a sentence for multi-emirate discussion. Title evidence has precedence.

Body focus share is the number of tokens in distinct qualifying sentences,
divided by all normalized body tokens, including suppressed sentences.
Repeated identical sentences contribute once, preventing copied sentences from
manufacturing a material section. This is sentence-focus coverage, not the
fraction of tokens that literally match lexicon entries. Title-only direct
coverage is sufficient for score 4. Body-only international acceptance requires
two distinct qualifying sentences and >=25% coverage.

Whole sentences are conservatively suppressed for configured office/HQ,
commentator/byline, biography/listing, conference/route, footer/navigation,
country-list and Emirates-brand contexts. Foreign-market names in the same
sentence as UAE geography suppress that sentence, even if proximity otherwise
passes. A separate material UAE section can still qualify. This intentionally
misses some nuanced mixed-country investment sentences.

All seven emirates, UAE and United Arab Emirates have explicit English phrases.
Hyphen/punctuation and capitalization variants normalize consistently. RAK/UAQ
are recognized only as bounded uppercase tokens with property context. Lowercase
ambiguous abbreviations are not positive geographic evidence.

Bare English “Emirates” is ambiguous. “In/across/throughout the Emirates” can
supply evidence with property context; Emirates airline/NBD/group sentences
are suppressed. No developer or area dictionary is included; developer names
alone supply no UAE evidence.

Arabic coverage is finite: الإمارات، الإمارات العربية المتحدة، دبي، أبوظبي،
أبو ظبي، الشارقة، عجمان، رأس الخيمة، الفجيرة، أم القيوين, alongside the Stage 8
property lexicon and a small supplement. No translation, stemming, external NLP,
attached-prefix analysis or comprehensive dialect coverage is claimed.

Each evidence polarity contains at most 24 unique fixed labels of at most 120
characters. Reasons contain at most 240 characters and expose rule/count/share/
threshold metadata, never article excerpts, full bodies or chain-of-thought.

## Stored input, history and safety

Schema `v0.5` adds three operational tables (16 total):
`uae_real_estate_relevance`, `uae_relevance_run_log`, `uae_relevance_run_results`.

Result primary key:
`(article_id, raw_hash, cleaning_version, dedup_version, relevance_version,
context_id, uae_relevance_version, registry_version)`.

The Stage 8 identity and group have foreign keys. SQL checks constrain scores,
booleans, thresholds and acceptance. Version and run-start indexes support
cohort selection/history. Parameterized conflict-ignore insertion preserves
existing rows and evaluation times; each run links new and reused results.

Stage 9 selects **one latest completed Stage 8 run** (SUCCESS or PARTIAL_SUCCESS)
for the requested cleaning/dedup/relevance versions, by completion timestamp and
rowid. It consumes only that run's linked results, avoiding overlapping history.
Eligible canonical identities/context hashes and group membership are validated.
Malformed result contexts are isolated; no singleton/member fallback is invented.

Stage 9 does not implement an independent `--since` filter. The CLI rejects it.
If the selected Stage 8 run used a cutoff, its already selected canonical cohort
is consumed intact, including an older canonical selected by a newer member.
New cleaned articles are invisible until Stage 8 explicitly publishes a run.
A database with no completed Stage 8 run logs a successful empty Stage 9 run.

Read snapshot -> release transaction -> compute -> BEGIN IMMEDIATE -> verify
snapshot -> publish results, links and final log atomically. The signature covers
the selected Stage 8 run/results, full selected cleaning-version cohort, and
versioned duplicate groups, including malformed SQLite BLOB values. Concurrent
changes abort publication with SnapshotChanged and permit retry. Classification
holds no long write transaction. Structural SQL failures roll back publication;
failed-run metadata is retained. No upstream results are updated.

Existing advisory locks, run ownership and conservative stale recovery are
reused under `uae_relevance`. Only owned, old RUNNING rows are reconciled after
exclusive lock acquisition. Legacy unowned and recent rows remain untouched.
No distributed-lock guarantee is claimed.

Fresh/v0.1/v0.2/v0.3/v0.4/v0.5 initialization is additive and repeatable. Unknown
versions fail closed; DDL and version stamps roll back together. The public
`apply_schema` entry point now uses the same atomic migration implementation.
Stage 9 itself does not create raw directories or modify production runtime data.

## CLI and validation

The mutually exclusive modes are `--fetch-only`, `--clean-only`, `--dedupe-only`,
`--relevance-only`, and `--uae-relevance-only`. Stage 9 supports `--json` and
`--cleaning-version`; it rejects acquisition options and `--since`. Exit status
is 0 for success, 1 for partial/failure, 2 for invalid usage.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_uae_relevance
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_pipeline
```

The permanent gate connects actual Stage 3 -> Stage 9 producers/readers, retains
backward lineage, checks raw/clean/duplicate/Stage 8 immutability, and denies
network entry points. Stage 9's suite uses synthetic fixtures and 50/100/200
eligible-context operation counts, with zero classifier calls on reusable reruns.
Work is linear in eligible article text plus scanned upstream cohort/history;
there is no pairwise article comparison. Group-history scanning can grow with
retained history, even when few contexts are eligible.

The historical 292-record dataset is unavailable locally. Synthetic validation
proves contracts and specified examples, not production precision/recall.
Explicit geography, finite Arabic coverage, sentence-level suppression and
body-focus thresholds intentionally prioritize precision over borderline recall.
