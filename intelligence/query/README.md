# Merged Stage 14: deterministic query boundary

This backend belongs to the merged 18-stage roadmap. It consumes the current
Stage 13 intelligence build and returns validated structured evidence. It does
not generate answers, call models, fetch feeds, calculate new market metrics,
or import Streamlit. Stages 15–18 remain separate future work.

## Entry points

```python
from datetime import datetime, timezone
from intelligence.query.models import QueryRequest, PageContext
from intelligence.query.service import query, evidence_package
from intelligence.query.suggestions import get_context_suggestions

context = PageContext(page_id="DUBAI_OVERVIEW", page_type="EMIRATE", emirate="DUBAI")
reference = datetime(2026, 9, 7, 9, tzinfo=timezone.utc)
response = query(QueryRequest(question="What's happening this week?",
                              page_context=context, as_of=reference, limit=10))
shortcuts = get_context_suggestions(context, as_of=reference)
package = evidence_package(response)
```

The caller supplies the reference time; routing never reads the wall clock.
The original question remains in `QueryResponse.request`. The handoff package
permits only AVAILABLE/PARTIAL evidence and excludes rejected questions. This
is a data contract, not an implemented model or grounded answer engine.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.query.run \
  --question "Latest Dubai property news" --page-context DUBAI --limit 10
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.query.run \
  --question "What's happening this week?" --page-context DUBAI \
  --as-of 2026-09-07T09:00:00+00:00
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_query
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_pipeline
```

The debug CLI prints JSON. No database/current build returns NO_DATA without
creating a database. Invalid CLI requests or database errors produce a bounded
error and nonzero exit. The Python API raises storage/contract errors instead
of misrepresenting a corrupt or incompatible datastore as missing evidence.

## Scope, resolution and page contract

Scope validation precedes catalog and action selection. Supported scope is
TruEstate/UAE real estate, including registered locations, events, metrics,
projects and developers. Foreign markets and unrelated subjects are rejected;
page context and selected IDs cannot authorize a rejected question. Exact
predictions, guarantees, purchase advice, conversions and unsupported
calculations stop without querying. General website navigation has no supplied
serving evidence and returns UNSUPPORTED; this is not a general chatbot.

Resolution uses existing Stage 10 aliases and hierarchy. It does not fuzzy-match
unknown areas or create entities. Explicit question/structured geography takes
precedence over page context, then UAE_WIDE. Conflicting explicit fields or
unresolved comparisons require clarification. An explicit new emirate clears
the page's area. A page's property type is a fallback; an explicit property type
wins. Unsupported dashboard data filters return UNSUPPORTED rather than being
silently applied to RSS-derived observations.

`PageContext` carries page ID/type, emirate, city, area, community, project,
building, developer, property type, bounded active filters and dashboard section.
`resolution.page` offers adapters for global/overview/help, emirates, forecast/
market outlook and the Business Bay example. Actual callers supply canonical
page/entity context; no session state or UI code is accessed. Existing website
routes include overview, Abu Dhabi, Dubai, Sharjah, RAK, area and forecast.

Supported periods are LATEST/current, TODAY, THIS_WEEK (Monday start), THIS_MONTH,
LAST_MONTH, explicit YYYY-MM, and Q1–Q4 with explicit or reference year. Calendar
windows are UTC, half-open. MoM/QoQ/YoY select stored movement bases. Relative
periods require an aware `as_of`; quarters without a year do too. News/events
use original publication timestamps; null dates are not assigned invented dates.
Monthly/quarterly observations use their explicit observation period. Daily/
weekly historical metric requests are UNSUPPORTED, and corresponding snapshot
sections are marked UNSUPPORTED. Unsupported structured time expressions and
unresolved year-only/future requests are not silently widened to all history.

The router is a finite deterministic lexical grammar, not general natural
language understanding. Unrecognized requests stop. More aliases or supported
phrases require explicit rules and regression cases, not a model fallback.

## Registered actions and evidence

`registry.ACTIONS` is a read-only map of 24 action definitions: 15 required
news/history/ranking/snapshot/project/regulation/outlook/comparison/source
actions and nine event-specific capabilities. Definitions declare supported
intents, required/optional filters, contexts, bounded limits, output type and
version. Area, emirate and comparison requirements are checked before DB access.

All SQL uses owned fragments and bound filter parameters. SQLite opens the
existing database with `mode=ro`, `query_only=ON`, a restrictive authorizer and
one transaction per action. The current build is read once inside that snapshot.
Direct raw/operational/upstream table reads are prohibited. The existing
Stage 13 `intelligence_news` and `intelligence_facts` views may resolve their
specific source tables through SQLite's view context; no rejection gates are
bypassed. Queries never create tables, logs, caches or user history.

Facts preserve Decimal text, units, currencies, property type, statistic,
observation nature and provenance. SOURCE_REPORTED_FORECAST stays separate from
OBSERVED; SOURCE_REPORTED percentages stay separate from SYSTEM_CALCULATED
movements. Source disagreements are flagged without averaging. Movement and
ranking records cite both observations. Rankings retain stored group IDs,
positions and ranks and may contain multiple independent groups. No reranking,
unit conversion, currency conversion or new market calculation occurs.

Every record references validated evidence containing build, metric-result,
article, raw hash, source ID/name/feed/article URL and available timestamps;
entity/event/observation/movement/ranking IDs are supplied where applicable.
These identities join the unchanged Stage 13 → Stage 12 → Stage 3 provenance.
Source details add allowlisted registry tier and trust score metadata only.

News is ordered by published date descending, retrieved date descending and
stable identity; null publication dates sort last. Event ties include event ID.
Area news requires actual Stage 13 entity association. No emirate-only story is
promoted to an area result without an association. Each query fetches at most
`limit + 1` to detect truncation (default 10, maximum 50). History can return
`limit` observations plus `limit` movements; snapshot sections each retain their
own bound. Truncation is explicit and yields PARTIAL.

Twelve output models share metadata, exact filters, build ID, supplied `as_of`,
latest returned evidence timestamp, result/evidence counts and answer policy.
Statuses are AVAILABLE, PARTIAL, NO_DATA, OUT_OF_SCOPE, AMBIGUOUS, UNSUPPORTED and
NOT_COMPARABLE. Available results cannot be empty; stopped results cannot contain
facts; records without evidence or with mixed builds cannot validate.
`latest_available_at` describes the returned evidence, not live market freshness.

Market snapshots contain independently assessed news, events, prices, rents,
transactions, projects, regulations and outlook sections. Comparisons keep each
side separately, use requested metric family, and check source, period, unit,
property, statistic, nature, hierarchy and movement basis. Incompatible sides
are NOT_COMPARABLE; partly compatible or incomplete sides are PARTIAL. There is
no computed winner, average, synthetic index or cross-source amalgamation.

## Catalog and exactly five suggestions

`catalog.QUESTIONS` contains 240 stable, enabled definitions: 220 literal
questions (six require page context) and 20 entity/comparison templates. Twenty-
five editorial topics span UAE-wide and all seven emirates. Additional time,
property, area, project, developer and comparison definitions cover 24 categories.
Catalog records carry ID, label, template, category, intent, action, context
rules, default filters, output model, priority and version. Selected IDs must
match the rendered original question; they never replace scope validation.

Suggestions are backend data only. Selection prefers supported context/entity
prompts, active property type, available evidence, editorial priority and category
diversity. At most 32 representatives are probed. Insufficient local candidates
are filled with compatible UAE-wide entries; IDs are unique, order deterministic
for the same build and reference time, and exactly five are returned whenever
five valid candidates exist. NO_DATA entries remain honest supported shortcuts.
Free-form requests use the same router and are not limited to the catalog.

## Validation and extension rules

The focused suite covers every enabled question/action/output, 112 separately
specified free-form variants, all emirates and area/project/developer/property
suggestions, rejection without database access, context/time conflicts, numeric
provenance, source disagreements, stored ranks, comparisons, SQL injection,
readonly authorizer enforcement and invalid output contracts. It constructs real
Stage 3–13 evidence in temporary storage and compares all 45 tables and raw
bytes/metadata before and after querying. Actual action SQL plans and bounded
results are checked on 100/500/1000-record cohorts.

The permanent `verify_pipeline` gate now runs Stage 3 → Stage 14, reuses the
exhaustive query checks against its own produced cohort, and prints the 240-row
catalog matrix, 15 connected requests, suggestion sets and backward lineage.
Failures include Stage 14 subcomponent, bounded question/expected/actual/action
metadata, upstream status and immutability. Network entry points are denied.
Future stages must extend this same gate and preserve prior contracts.
