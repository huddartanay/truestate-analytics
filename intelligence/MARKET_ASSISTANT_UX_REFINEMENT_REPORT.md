# TruEstate Market Assistant UX refinement

Date: 9 September 2026. Target: the existing `huddartanay/truestate-analytics` repository, `main`, `streamlit_app.py`, and existing Streamlit application. Base: `5ccb0f77fa94c8a50dc5cdb558fb3d4bf5b14002`.

## User-facing changes

The AI component is now **TruEstate Market Assistant**, with **Market Intelligence Summary** above it. The surrounding website, navigation, analytics and design system are unchanged. The question field accepts free-form questions; suggested questions remain original catalog entries.

Successful responses use a deterministic business-language presenter over the already-validated immutable facts. Rejected model drafts and backend diagnostics never become visible. Numbers retain their location, currency, property type, statistic, period, comparison basis, rank, and source attribution. Forecasts remain expectations, calculated figures remain attributed to TruEstate analytics, and conflicting figures remain separate with a disagreement notice. Internal IDs, claims, audits and provenance are retained unchanged.

The summary uses supported sections: Market at a glance, Key market signals, Market context where needed, What’s happening now, What to watch, then Projects & developments and/or Latest property news. Current reporting retains its existing reserved share of the ten-fact budget; chat retains six. Current story titles and bounded publisher excerpts provide concrete detail, names and dates without inventing implications or investment advice. Historical context precedes current news. A real Dubai sample has approximately 415 words; thinner Abu Dhabi, Sharjah, RAK and area coverage is deliberately shorter. Outlook without supported facts remains NO_DATA. The word target never overrides available evidence.

One friendly freshness line uses `Asia/Dubai` consistently: today/yesterday with a local time, otherwise a readable calendar date. Raw timestamps and operational counts are hidden. Sources show only supporting publishers, article titles where supplied, readable publication dates and safe article links; duplicate article references are collapsed. Configured feeds that did not support the answer are not listed.

Summary and answer requests display a professional Streamlit processing container during the actual backend operation, followed by a completion label. There are no artificial delays or technical progress messages. The dashboard remains available on an assistant outage. NO_DATA can name the requested subject/location and offers up to three currently answerable catalog alternatives; it never claims a source was checked when that is unproven. Out-of-scope, temporary unavailability and failed-verification responses use safe business-facing messages.

## Different questions and cache identity

There was no generated-chat answer cache to reuse accidentally. Every submission still executes its own typed question request. History now records an internal hash of normalized question text, all typed context/filter fields and historical/current fingerprints. The summary and shortcut cache now includes the current-intelligence fingerprint as well as the existing page, selection, fact, build and date identity. A refreshed fingerprint invalidates stale summary/shortcuts while preserving the conversation; a genuine page/filter change resets context. Useful caching remains.

The existing question-specific retrieval filters remain unchanged. Tests prove Dubai projects, Dubai rents, Sharjah projects and Dubai news produce appropriately different fact identities. An unsupported outlook returns NO_DATA rather than recycling another answer. Shared real facts may legitimately recur in overlapping questions.

## Evidence-aware suggestions

Candidates come only from the existing 240-question Stage 14 catalog. The website adapter dry-runs the same deterministic hybrid retrieval used for answers against the current stored snapshot and verified historical build. No RSS refresh or model call is used to decide shortcuts. Only ANSWER/PARTIAL_DATA with useful facts qualifies; empty questions are excluded. Selection diversifies both the actual resulting action and article/fact identities, rather than selecting multiple synonymous date variants.

All six tested page contexts currently produce five answerable suggestions. UAE fallback questions explicitly say UAE and clear the narrower page binding; they do not mislabel UAE evidence as local evidence. In particular, RAK has five explicit UAE questions, not fabricated RAK project coverage. If fewer remain available later, the UI displays fewer with an honest note. A missing verified production artifact yields zero shortcuts.

| Page | Answerable shortcuts | Scope behavior |
| --- | ---: | --- |
| Dubai | 5 | Dubai questions |
| Abu Dhabi | 5 | Local reporting/sources plus explicitly UAE prices, rents and projects |
| Sharjah | 5 | Local reporting/projects/sources plus explicitly UAE prices and rents |
| RAK | 5 | Explicit UAE alternatives only for this stored news cohort |
| Area Analysis / Business Bay | 5 | Area reporting plus explicitly UAE alternatives |
| Market Outlook / Dubai | 5 | Supported Dubai facts; no unsupported forecast shortcut |

## Validation

No new RSS network smoke, paid Qwen call, benchmark or synthetic production data was used. Real-cohort checks read the existing verified snapshots; provider success is substituted offline while the real deterministic validator still runs.

| Check | Result |
| --- | --- |
| Focused UX unit/real-cohort/widget tests | 13 tests PASS; all 30 displayed shortcut buttons clicked |
| Existing current-intelligence tests | 10 PASS |
| Existing real current-cohort tests | 7 PASS |
| Stage 18 integration | 12 PASS |
| Six complete existing website routes | 6 PASS; summary, free-form and shortcut controls exercised |
| Stage 17 system | 195 checks PASS; network attempts 0 |
| Stage 16 pipeline | 7,145 checks PASS; network attempts 0 |
| Answer engine | 166 checks PASS; network calls 0 |
| Stage 14 critical routing/catalog | 1,644 checks PASS; all 240 catalog entries; network 0 |
| Provider/security preservation | 303 checks PASS; network calls 0 |
| Sharjah / RAK application data | 83 / 132 checks PASS |
| Dubai numbers / forecast integration | PASS |
| Application compilation/imports | 62 files compile; 50 modules import; failures 0; network attempts 0 |

Focused checks cover plain numeric semantics, forecasts, comparison basis/ranking, clean publishers/links, hidden terminology and raw timestamps, safe error text, rejected-draft suppression, request identity, fingerprint invalidation without conversation loss, fewer/no suggestions with missing data, genuine question-specific packages and processing states before backend calls.

Initial suggestion-diversity assertions exposed catalog actions that resolved to the same actual action; selection was corrected to deduplicate the actual retrieval action. Initial full-page smoke runs used an empty hosted-cache directory and correctly exposed zero suggestions. Their logs remain in the local audit folder; reruns explicitly selected the existing verified real production artifact. Missing-artifact tests remain fail-closed. Legacy local Stage 18 assertions were updated only for authorized UI labels, hidden IDs, expanded safe history metadata and answerable counts from zero to five. Routing fixtures and critical contracts were not weakened.

The historical strict Stage 15 certification remains FAILED under the existing authorized MVP engineering exception. Passing these UX/regression checks does not rewrite that history or constitute a new model qualification.

## Files and unchanged boundaries

- `intelligence/current/retrieval.py`
- `intelligence/current/suggestions.py`
- `intelligence/production/worker.py`
- `platform_core/ai_presentation.py`
- `platform_core/ai_service.py`
- `platform_core/ai_ui.py`
- `tests/test_market_assistant_ux.py`
- `intelligence/MARKET_ASSISTANT_UX_REFINEMENT_REPORT.md`

The current retrieval change only supplies the already-stored article title when the source-details fact did not carry it. The worker delegates shortcut selection to the website adapter. No Stage 3–14 implementation, model/provider setting, grounding validator, RSS ingestion pipeline, database, dependency, entry point, regional page, workflow or scheduler configuration changes. Secret and developer-path scans and the exact allowlist/source diff review are required before staging. Runtime snapshots, validation logs, local legacy test scaffolding, caches and secrets remain excluded from Git.

## Commit and deployment record

Authorized publication is one targeted commit named `Refine TruEstate market assistant experience`, followed by a normal non-force push to existing `main`. The commit containing this report is the source change under review; its own SHA cannot be embedded in its content. At report creation publication is pending. The final local completion receipt records the actual commit SHA, push result and remote verification after publication, without creating a second documentation commit.

Remote main was rechecked against the base above before staging. The daily scheduler remains disabled; no scheduler flag is changed. No repository, Streamlit application or deployment URL is created. The existing Streamlit Secrets setting is left untouched.

## Hosted validation checklist

These are post-deployment checks, not claims of completed hosted or paid-model testing:

- Confirm the existing application deploys this commit from main and retains all six dashboard routes.
- On each page, confirm the two new component names, one friendly freshness line, and only currently answerable suggestions.
- Generate a summary and inspect the professional processing state, supported figures, and current developments near the end when available.
- Confirm clean publisher names, article dates/titles and links, with no internal IDs or operational text.
- Submit distinct Dubai project/rent and Sharjah project questions; inspect relevance and retained location/period/source qualifiers.
- Ask about unavailable Khalid Bin City / RAK projects: expect honest insufficient-information guidance and answerable alternatives, never invented local coverage.
- Check out-of-scope guidance, safe temporary-unavailability and failed-verification states, conversation clearing and context changes.
- Confirm missing/expired current information does not disable the dashboard; verify production secret behavior in the existing deployment without exposing its value.

Local audit evidence remains under `intelligence/validation/market_assistant_ux/`, including regression results, initial failed smoke logs, successful reruns, six real presentation samples and question/fact identity comparisons. Hosted paid-model behavior and the Streamlit deployment finish remain separate checks. Rollback, if necessary, is a normal reviewed revert of this one commit; historical intelligence and current cache architecture are unchanged.
