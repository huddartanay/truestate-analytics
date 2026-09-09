# Stage 16 grounded answer backend

This backend uses the merged 18-stage roadmap. Stage 14 owns scope, routing and
actions; Stage 13 owns facts, calculations and rankings. Stage 16 packages those
facts, calls the existing Stage 15 OpenRouter client, validates every claim and
renders final prose with deterministic provenance and citations.

The fixed MVP model is `qwen/qwen3-235b-a22b-2507` at `parasail/fp8`. Its Stage 15
status remains `MVP_ENGINEERING_EXCEPTION`; strict certification remains FAILED.
Stage 16 does not amend that history or recertify the model.

```python
from intelligence.answer_engine import answer_question, generate_dashboard_summary

answer = answer_question("How are Dubai property prices moving?", "Dubai")
# answer.status, answer.answer, answer.claims, answer.evidence, answer.audit

summary = generate_dashboard_summary(
    page_context="Dubai",
    dashboard_facts=verified_dashboard_facts,
    intelligence_context=None,  # optional genuine Stage 14 QueryResponse
)
```

`verified_dashboard_facts` is a sequence of `DashboardFact` objects or equivalent
dicts. Each requires identity, registered location, metric, exact decimal string
value, unit, calendar period, provenance, observed/forecast nature, source and
reference. Rankings additionally require a rank and group ID. The caller must be
a trusted backend adapter over existing website calculations. User-authored
assertions are not verified dashboard facts. Stage 18 will supply that adapter;
no website code has been connected or changed here.

Contexts accept Stage 14 `PageContext`, equivalent dicts, or existing page aliases
including Dubai, Abu Dhabi, Sharjah, RAK, BUSINESS_BAY and MARKET_OUTLOOK. Existing
Stage 14 unsupported filters and scope decisions remain authoritative. For
relative periods the class/module help API accepts an aware `as_of` datetime.
Only the exact phrase “Which Dubai areas increased the most?” receives an explicit
paraphrase to Stage 14's existing “largest price increases” action; it is routed
through Stage 14 again and never rewrites an OUT_OF_SCOPE result.

Evidence is capped at six facts and the user JSON context at 18,000 UTF-8 bytes.
Selection is deterministic: complete conflict groups first, then action kind,
recency, ranking group and position, stable identity. Final evidence uses that
stable order and IDs E1–E6. Conflicts and ranking groups are indivisible. An atomic
group exceeding six facts, or a comparison that cannot fit in its entirety,
fails safely. Other truncation is explicit PARTIAL_DATA. Dashboard facts have
priority over supplemental intelligence; they are never recomputed.

Every generated claim must match its evidence's value, unit, location, period,
provenance, nature and rank, with complete ordered ID coverage. Optional model
draft text is never published. Final templates supply labels immediately before
each citation. This structurally mitigates the known T34 placement defect.
Model drafts containing detectable unsupported figures, locations, citations or
causality are rejected as well. This is a conservative template-based MVP, not
unrestricted narrative generation.

OUT_OF_SCOPE, NO_DATA, AMBIGUOUS, UNSUPPORTED and NOT_COMPARABLE return without
inference. Missing comparison sides stay explicit. Contract corruption produces
VALIDATION_FAILED. Operational errors produce TEMPORARILY_UNAVAILABLE with safe
metadata; no replacement model or fabricated answer is used.

One process-wide semaphore permits one inference sequence. Default HTTP timeout
is 30 seconds, with at most two retries and 2/4-second minimum backoff. Retry-After
may extend the wait; guidance above 120 seconds returns temporary unavailability
and a retry delay without retrying early. Multi-process hosting would need one
worker or a shared limiter in its deployment design. No deployment is included.
The existing OpenRouter client retains ZDR, denied data collection, no provider
fallback and pinned maximum prices. The key is read only from the environment.

Operational logs contain only the `Audit` whitelist: IDs, intent/action, evidence
count/IDs, model, latency, attempts/retries, status, validation, safe error code and
versions. They exclude question text, prompts, claim content, credentials and
reasoning. Full examples in Stage 16 validation artifacts use synthetic fixtures.

Offline checks:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_answer_engine
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_stage16_pipeline
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_stage16_regression
```

The regression runner removes the OpenRouter key from child environments. Three
obsolete Stage 15 recovery scripts require their original pre-MVP checkpoint;
their preserved failed audit runs are documented separately. Legacy standalone
Streamlit scripts compile but are not imported as ordinary modules: their
existing launcher supplies the working directory and session context.

The explicit `stage16_live_smoke` module is a checkpointed, two-request fixture
smoke, with zero retries, conservative pacing and a $0.02 reservation. Completed
attempts are never restarted. Do not delete its ledger to rerun it. The permanent
offline pipeline never needs the key or network.

Stage 17 complete-system testing and Stage 18 UI/deployment remain unimplemented.
See [the Stage 16 report](../STAGE16_REPORT.md) for measured results and lineage.
