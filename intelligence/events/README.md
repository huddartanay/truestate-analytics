# Stage 11: deterministic event extraction

Stage 11 answers what happened in an article already accepted by Stages 8–9
and successfully processed by Stage 10. It emits individual evidence-backed
events and links them to existing Stage 10 mentions. It preserves article-level
location scope, upstream identities and all upstream evidence.

This is the operational event layer. Structured price/rent/transaction values
belong to Stage 12; the final intelligence database belongs to Stage 13.
No network, new dependency, LLM, Ollama, embeddings, dashboard imports or UI
integration are used.

## Versions and CLI

Schema is `v0.7`; `EVENT_EXTRACTION_VERSION` is `stage11-v1`. Source, cleaning,
deduplication, relevance and entity versions are unchanged. Material rule,
segmentation, direction, confidence or association changes require a new event
version. Old results retain their original evidence and links.

```sh
python3 -m intelligence.pipeline.run --events-only
python3 -m intelligence.pipeline.run --events-only --json
python3 -m intelligence.pipeline.run --events-only --cleaning-version stage6-v1
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_events
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_pipeline
```

Operational commands use configured storage. Tests isolate all writes in
temporary directories and block network access. The seven operational modes
(`--fetch-only`, `--clean-only`, `--dedupe-only`, `--relevance-only`,
`--uae-relevance-only`, `--entities-only`, `--events-only`) are mutually exclusive.
Event mode rejects fetch options and independent `--since` filtering. It does
not rerun upstream stages. Exit codes are 0 success, 1 partial/failure, 2 usage
error. No completed matching Stage 10 run yields an empty successful event run.

## Taxonomy and v1 semantics

`EventType` contains exactly these 22 values. Rules pair explicit subjects with
actions within bounded text; a noun mention alone normally does not establish
an event. The finite wording supported by each type is inspectable in `rules.py`.

| Event | Required meaning |
| --- | --- |
| PRICE_CHANGE | Explicit movement/stability in sale prices or home values |
| RENT_CHANGE | Explicit movement/stability in rents or rental rates/prices |
| TRANSACTION_VALUE | Explicit worth or aggregate/total monetary transaction value |
| TRANSACTION_VOLUME | Explicit count/number/volume semantics or recorded transaction-count wording |
| SALES_ACTIVITY | Home/property sales activity, separately evidenced from prices |
| MORTGAGE_ACTIVITY | Mortgage registrations, demand, lending or applications with activity |
| OFF_PLAN_ACTIVITY | Explicit off-plan sales/activity with an action |
| READY_PROPERTY_ACTIVITY | Explicit ready-home, secondary-market or completed-unit sales activity |
| NEW_PROJECT | Announcement/introduction of a new project |
| PROJECT_LAUNCH | Explicit project launch, release or opening for sales |
| PROJECT_COMPLETION | Explicit completion, delivery or handover |
| NEW_SUPPLY | Homes/units entering the market or becoming available |
| SUPPLY_PIPELINE | Planned/upcoming supply or future/scheduled delivery |
| DEVELOPER_ACTIVITY | Developer portfolio expansion, acquisition or merger |
| INVESTOR_ACTIVITY | Explicit investor purchases or participation/activity |
| FOREIGN_INVESTMENT | Explicit foreign/international/overseas investment participation |
| REGULATION | Introduction/change of named property, tenancy, ownership or registration rules |
| INFRASTRUCTURE | An actual metro/road/transport/airport development in an eligible article |
| DEMAND_CHANGE | Explicit buyer/housing/tenant/property demand movement |
| MARKET_SENTIMENT | Explicit investor/buyer confidence or market sentiment |
| MARKET_OUTLOOK | Explicit forecast/expectation/projection with property context |
| RENTAL_ACTIVITY | Leasing activity, tenant registrations or tenancy-agreement activity |

Price changes do not imply sales, demand or sentiment. Rent changes do not
imply leasing activity. Generic transaction mentions do not imply count/value.
Non-off-plan activity does not automatically imply ready-property activity.
Foreign investment is not inferred from publisher, currency, country mention
or developer nationality. Infrastructure events do not assert causal effects.
Stage 8/9 acceptance supplies article eligibility; local event subjects/actions
and collision safeguards supply the event evidence.

## Rules and segmentation

Each frozen `Rule` records an ID, event type, compiled bounded pattern,
optional context condition, direction policy, priority, forecast policy and
applicable fields. Patterns pair an explicit subject and action with at most
six intervening normalized tokens, except narrower rule-specific grammar.
No stemming, fuzzy matching, semantic models or arbitrary translation is used.

Text is divided at sentence punctuation, nonnumeric commas, semicolons,
newlines and explicit conjunctions (`while`, `whereas`, `but`, `and`, `as`,
`بينما`, `ولكن`, `لكن`). Numeric internal commas/decimal points remain evidence.
Within each clause, text uses Stage 10's mapped Unicode normalization. Matching
does not change stored clean text. Each rule emits at most one instance per
clause/field. Repeated evidence in distinct clauses or TITLE/BODY remains
distinct; this preserves traceability rather than deduplicating reporting.

Same-clause specificity prevents redundant labels:

- PROJECT_LAUNCH suppresses NEW_PROJECT and DEVELOPER_ACTIVITY.
- NEW_PROJECT and PROJECT_COMPLETION suppress DEVELOPER_ACTIVITY.
- OFF_PLAN_ACTIVITY and READY_PROPERTY_ACTIVITY suppress generic SALES_ACTIVITY.
- FOREIGN_INVESTMENT suppresses generic INVESTOR_ACTIVITY.
- RENT_CHANGE suppresses the generic price substring inside rental-price wording.

Separate clauses can retain separate events. PROJECT_LAUNCH and OFF_PLAN_ACTIVITY
can coexist. PROJECT_COMPLETION and NEW_SUPPLY coexist only when their separate
explicit evidence is present; a completed-home adjective alone does not imply
a completion event. TRANSACTION_VALUE and TRANSACTION_VOLUME remain independent.

## Direction, confidence, negation and time

Direction is INCREASE, DECREASE, STABLE or UNKNOWN. It is extracted only from
the rule's matched subject/action evidence using explicit morphology lists.
Conflicting direction words produce UNKNOWN. Nondirectional rules always use
UNKNOWN. No magnitude or stronger movement class is calculated.

HIGH means explicit retained TITLE evidence; MEDIUM means explicit retained BODY
evidence. These are policy labels, not probabilities. LOW events are not emitted.

Any registered negation in a clause suppresses its events. The vocabulary covers
`not`, `no`, `without`, `never`, expanded/contracted English negatives, and bounded
Arabic equivalents including `لم`, `لن`, `لا`, `ليس`, `بدون`, `غير`. This
deliberately conservative policy can suppress an affirmative claim next to an
unrelated negation in the same clause. It never flips a negated increase into a
decrease or assumes that no decline means stability.

Registered historical clauses such as “last year” or “previously” are omitted.
An independently stated current clause can survive. Explicit future language
suppresses observed-change, launch and completion claims. Only applicable
MARKET_OUTLOOK/SUPPLY_PIPELINE rules can survive that gate. V1 performs no period
extraction, temporal resolution, quotation attribution or conditional reasoning.

## Evidence, identity and entity associations

`RealEstateEvent` contains event ID, event-result ID, event type, rule ID,
TITLE/BODY field, matched text, original offsets, confidence, direction and
typed entity links. `EventExtractionResult` owns the complete upstream lineage,
copied article scope, event version, ordered instances and evaluation timestamp.
This avoids duplicating article identity on every event model; the relational
event-result foreign key makes it available for every instance.

Offsets are Python Unicode-character indexes, zero-based and end-exclusive:

```python
clean_text[event.start_offset:event.end_offset] == event.matched_text
```

An association references a Stage 10 `mention_index` and its existing `entity_id`.
Only mentions entirely inside the same clause and within twelve intervening
tokens of the event evidence qualify. For repeated mentions of one entity,
nearest distance then earliest mention index breaks ties. Links are unique and
sorted by entity ID. `CLAUSE_CONTEXT` describes contextual association, not an
inferred actor, owner, investor nationality, causal relation or metric subject.

There is no article-wide entity attachment, cross-sentence pronoun resolution,
new entity creation or inferred parent mention. This keeps the critical case
“Dubai home prices increased while Abu Dhabi rents declined” separate: Dubai
links to PRICE_CHANGE; Abu Dhabi links to RENT_CHANGE. An unrelated developer in
another sentence is not linked. Article `location_scope` remains Stage 10's
authoritative value, including UAE_WIDE, MULTI_EMIRATE and UNKNOWN.

Result identity is SHA-256 of `[Stage 10 extraction_id, event version]`.
Instance identity hashes that result identity plus type, field, span, rule,
direction, exact evidence and associated mention identities. Timestamps and
run UUIDs are excluded. Result models additionally verify that the upstream
extraction ID binds all ten Stage 10 identity/version fields.

Limits are 128 event instances per article, 640 characters per evidence span
and 32 entity links per event. Exceeding a limit fails the article with a typed
error; no evidence is silently truncated. Models are frozen, forbid extra fields
and validate ordering, unique IDs, exact span length, confidence and identity.
Boundary validation checks actual source slices, rule safeguards, direction and
associations against immutable Stage 10 mentions.

## Persistence and eligibility

Five additive tables bring the operational schema to 25 tables:

| Table | Purpose |
| --- | --- |
| event_extraction_results | Versioned per-Stage-10-context result and lineage |
| real_estate_event_instances | Queryable event type/direction/evidence instances |
| event_entity_links | Associations to exact Stage 10 mention identities |
| event_run_log | Operational run status, versions and bounded counters/errors |
| event_run_results | Separate run-to-result reuse/provenance links |

Results have unique `(extraction_id, event_extraction_version)` keys and foreign
keys to Stage 10. Instances link to their owning result. Association foreign keys
bind both the instance's upstream extraction and the specific Stage 10 mention.
Readback also verifies linked entity IDs against the referenced mentions.
Indexes support event type/direction, entity lookup, versions and run time.
The per-type run counter JSON has the finite 22-type vocabulary; it is telemetry,
not authoritative event storage.

Only the latest completed SUCCESS/PARTIAL_SUCCESS Stage 10 run matching all
seven requested upstream versions is consumed. Its Stage 9 and Stage 8 run
provenance remains anchored even if newer upstream runs exist. Every result must
have valid Stage 8/9 acceptance, matching versions/context, clean evidence and
canonical duplicate provenance. Zero-mention UNKNOWN results remain eligible.
Failed/missing Stage 10 results cannot be inferred from raw or cleaned records.

Same-key reruns link existing results with zero extraction calls. Changed event
or upstream entity versions create separate results and stable historical IDs.
Raw evidence, cleaned articles, duplicate history, relevance decisions, entity
definitions, entity results and mentions are never updated by Stage 11.

## Transactions and failures

The shared pipeline guard and owned stale-run recovery are reused. Read the
selected Stage 10 run/results/mentions, anchored Stage 9/8 runs/results, clean
cohort and groups in a read transaction. Compute outside a write transaction.
Then obtain `BEGIN IMMEDIATE`, compare the full snapshot again, and atomically
publish results, instances, links, run linkage and final run status.

Concurrent upstream change causes `SnapshotChanged`. Persistence failure rolls
back all event output; a failed run log remains. Malformed individual contexts
are isolated so healthy contexts can complete with PARTIAL_SUCCESS. Structural
orphan references fail closed. Old owned runs are recoverable; legacy/unowned
and recent runs are preserved. Errors retain sanitized type/record diagnostics
for the first 100 failures plus an unbounded total count, never arbitrary
exception text or full article bodies.

## Stage 12 boundary and limitations

TRANSACTION_VALUE and TRANSACTION_VOLUME classify textual meaning. A digit
pattern can recognize count wording, but no number is converted or stored as
a market observation. Evidence may contain `8%`, `10,000` or `AED 20 billion`.
There are no structured value, currency, percentage, price, rent, yield, unit,
transaction-count or price-per-area fields. Verification rejects these extras
on result, event and association models.

The deterministic corpus covers all 22 types, direction, negation, precedence,
multi-event clauses, original offsets, Arabic and entity associations. The
permanent pipeline uses real local-feed Stage 3→11 producers and persisted
readback, with immutable evidence checks and localized failure diagnostics.
Tests also cover migration from fresh/v0.1–v0.6/current, rollback, concurrency,
ownership, CLI and 50/100/200-context call scaling.

Coverage remains finite. Arabic rules target prices, rents, sales/transactions,
projects, handover, mortgages, off-plan, regulation, demand and foreign investment;
attached morphology and unregistered wording may be missed. Conjunction/list
splitting, dotted abbreviations, omitted subjects, same-clause multiple projects,
long-distance relationships and historical wording beyond the small vocabulary
are not fully resolved. Broad collision suppression favors precision over recall.
An eligible article may therefore have no retained events. Synthetic checks are
not measured production precision/recall. The historical 292-record runtime
corpus is absent; no replay or download of that corpus was performed.
