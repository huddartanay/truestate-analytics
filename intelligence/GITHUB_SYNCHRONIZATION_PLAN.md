# GITHUB SYNCHRONIZATION PLAN

**READY FOR FINAL REVIEWED GITHUB SYNC. STOP BEFORE COMMIT/PUSH.** Authoritative workspace: `/Users/tanayhuddar/Desktop/FULL CODE BASE`. Existing target: `huddartanay/truestate-analytics` → `main` → `streamlit_app.py`. Same app and URL; no new repository or deployment.

Compared and rechecked main: `3ccb233a35ea6fbfdfaa41f024b5e41d437cbb5f`. The initial comparison found 240 main files, 202 identical local files, 37 differing files and one remote-only devcontainer. The local proposed result now incorporates all current main versions before adding the reviewed Stage 18 integration and deployment prerequisites. No remote file is deleted.

Final source allowlist: **119 ADD, 13 MODIFY**, with the remaining main files retained. The [CSV](GITHUB_SYNCHRONIZATION_PLAN.csv) enumerates every local path and its exact disposition/hash. `EXCLUDE` means do not upload this local file; `RETAIN_MAIN` rows preserve existing remote files. Local tests, simulations and histories remain intact and are excluded from the source commit.

## Existing GitHub website fixes preserved

Seven protected files are byte-identical to main: `.streamlit/config.toml`, `platform_core/memory.py`, `regions/dubai_market/data.py`, `platform_core/components.py`, `platform_core/design_system.py`, `platform_core/pdf_report.py`, `platform_core/combined_report.py`. The eighth is the complete `_import_platform` retry guard retained verbatim in `streamlit_app.py` alongside the new startup hook. Preserve navigation, Abu Dhabi report placement, memory handling, Arrow loading, branding and PDFs. Proof: `validation/deployment_prerequisites/website_fixes.json`; all eight checks pass.

## SOURCE CODE TO PUSH — ADD

| LOCAL FILE | GITHUB DESTINATION | ACTION | REASON |
|---|---|---|---|
| `.github/workflows/production-intelligence.yml` | `.github/workflows/production-intelligence.yml` | ADD | Daily/manual real-RSS publisher, pinned actions, one concurrency group, explicit operator activation. |
| `deploy/requirements-intelligence.lock` | `deploy/requirements-intelligence.lock` | ADD | Fourteen exact Linux/Python 3.12 dependency versions and wheel hashes, including transitive packages. |
| `intelligence/DEPLOYMENT_PREREQUISITES_REPORT.md` | `intelligence/DEPLOYMENT_PREREQUISITES_REPORT.md` | ADD | Final local implementation, tests, exclusions, operator actions and readiness evidence. |
| `intelligence/GITHUB_SYNCHRONIZATION_PLAN.csv` | `intelligence/GITHUB_SYNCHRONIZATION_PLAN.csv` | ADD | Reviewed deployment/synchronization documentation; no credentials or runtime data. |
| `intelligence/GITHUB_SYNCHRONIZATION_PLAN.md` | `intelligence/GITHUB_SYNCHRONIZATION_PLAN.md` | ADD | Reviewed deployment/synchronization documentation; no credentials or runtime data. |
| `intelligence/PRODUCTION_DEPLOYMENT.md` | `intelligence/PRODUCTION_DEPLOYMENT.md` | ADD | Reviewed deployment/synchronization documentation; no credentials or runtime data. |
| `intelligence/PRODUCTION_DEPLOYMENT_CLOSURE_REPORT.md` | `intelligence/PRODUCTION_DEPLOYMENT_CLOSURE_REPORT.md` | ADD | Reviewed deployment/synchronization documentation; no credentials or runtime data. |
| `intelligence/STREAMLIT_DEPLOYMENT_PLAN.md` | `intelligence/STREAMLIT_DEPLOYMENT_PLAN.md` | ADD | Reviewed deployment/synchronization documentation; no credentials or runtime data. |
| `intelligence/__init__.py` | `intelligence/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/answer_engine/README.md` | `intelligence/answer_engine/README.md` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/answer_engine/__init__.py` | `intelligence/answer_engine/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/answer_engine/engine.py` | `intelligence/answer_engine/engine.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/answer_engine/models.py` | `intelligence/answer_engine/models.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/answer_engine/prompt.py` | `intelligence/answer_engine/prompt.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/answer_engine/rendering.py` | `intelligence/answer_engine/rendering.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/answer_engine/retrieval.py` | `intelligence/answer_engine/retrieval.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/cleaning/__init__.py` | `intelligence/cleaning/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/cleaning/clean.py` | `intelligence/cleaning/clean.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/config.py` | `intelligence/config.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/__init__.py` | `intelligence/db/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/cleaning.py` | `intelligence/db/cleaning.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/connection.py` | `intelligence/db/connection.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/deduplication.py` | `intelligence/db/deduplication.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/entities.py` | `intelligence/db/entities.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/events.py` | `intelligence/db/events.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/intelligence.py` | `intelligence/db/intelligence.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/locking.py` | `intelligence/db/locking.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/metrics.py` | `intelligence/db/metrics.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/relevance.py` | `intelligence/db/relevance.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/runs.py` | `intelligence/db/runs.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/schema.sql` | `intelligence/db/schema.sql` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/snapshots.py` | `intelligence/db/snapshots.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/db/uae_relevance.py` | `intelligence/db/uae_relevance.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/deduplication/README.md` | `intelligence/deduplication/README.md` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/deduplication/__init__.py` | `intelligence/deduplication/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/deduplication/compare.py` | `intelligence/deduplication/compare.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/deduplication/groups.py` | `intelligence/deduplication/groups.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/deduplication/normalize.py` | `intelligence/deduplication/normalize.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/entities/README.md` | `intelligence/entities/README.md` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/entities/__init__.py` | `intelligence/entities/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/entities/catalog.json` | `intelligence/entities/catalog.json` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/entities/extract.py` | `intelligence/entities/extract.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/entities/normalize.py` | `intelligence/entities/normalize.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/entities/registry.py` | `intelligence/entities/registry.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/enums.py` | `intelligence/enums.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/errors.py` | `intelligence/errors.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/events/README.md` | `intelligence/events/README.md` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/events/__init__.py` | `intelligence/events/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/events/extract.py` | `intelligence/events/extract.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/events/identity.py` | `intelligence/events/identity.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/events/rules.py` | `intelligence/events/rules.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/llm/README.md` | `intelligence/llm/README.md` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/llm/__init__.py` | `intelligence/llm/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/llm/openrouter.py` | `intelligence/llm/openrouter.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/llm/openrouter_settings.py` | `intelligence/llm/openrouter_settings.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/metrics/README.md` | `intelligence/metrics/README.md` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/metrics/__init__.py` | `intelligence/metrics/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/metrics/extract.py` | `intelligence/metrics/extract.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/metrics/identity.py` | `intelligence/metrics/identity.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/metrics/numbers.py` | `intelligence/metrics/numbers.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/metrics/rules.py` | `intelligence/metrics/rules.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/pipeline/__init__.py` | `intelligence/pipeline/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/pipeline/clean.py` | `intelligence/pipeline/clean.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/pipeline/deduplicate.py` | `intelligence/pipeline/deduplicate.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/pipeline/entities.py` | `intelligence/pipeline/entities.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/pipeline/events.py` | `intelligence/pipeline/events.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/pipeline/fetch.py` | `intelligence/pipeline/fetch.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/pipeline/intelligence.py` | `intelligence/pipeline/intelligence.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/pipeline/metrics.py` | `intelligence/pipeline/metrics.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/pipeline/relevance.py` | `intelligence/pipeline/relevance.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/pipeline/run.py` | `intelligence/pipeline/run.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/pipeline/uae_relevance.py` | `intelligence/pipeline/uae_relevance.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/production/__init__.py` | `intelligence/production/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/production/artifacts.py` | `intelligence/production/artifacts.py` | ADD | Production-only portable DB/history export, integrity gates, safe archives and atomic materialization. |
| `intelligence/production/refresh.py` | `intelligence/production/refresh.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/production/release_job.py` | `intelligence/production/release_job.py` | ADD | Restore before controlled ingestion; no publication on acquisition/build/artifact failure. |
| `intelligence/production/releases.py` | `intelligence/production/releases.py` | ADD | Fixed existing GitHub repository, bounded release transfer and validated draft-to-published handoff. |
| `intelligence/production/startup.py` | `intelligence/production/startup.py` | ADD | Artifact-only startup, hourly check bound, last-valid recovery and fixed-repository rollback selection. |
| `intelligence/production/store.py` | `intelligence/production/store.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/production/worker.py` | `intelligence/production/worker.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/query/README.md` | `intelligence/query/README.md` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/query/__init__.py` | `intelligence/query/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/query/actions.py` | `intelligence/query/actions.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/query/catalog.py` | `intelligence/query/catalog.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/query/models.py` | `intelligence/query/models.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/query/registry.py` | `intelligence/query/registry.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/query/resolution.py` | `intelligence/query/resolution.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/query/router.py` | `intelligence/query/router.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/query/run.py` | `intelligence/query/run.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/query/service.py` | `intelligence/query/service.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/query/suggestions.py` | `intelligence/query/suggestions.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/relevance/README.md` | `intelligence/relevance/README.md` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/relevance/__init__.py` | `intelligence/relevance/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/relevance/classify.py` | `intelligence/relevance/classify.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/relevance/rules.py` | `intelligence/relevance/rules.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/schemas.py` | `intelligence/schemas.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/serving/README.md` | `intelligence/serving/README.md` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/serving/__init__.py` | `intelligence/serving/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/serving/build.py` | `intelligence/serving/build.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/serving/movements.py` | `intelligence/serving/movements.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/serving/periods.py` | `intelligence/serving/periods.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/serving/policy.py` | `intelligence/serving/policy.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/serving/rankings.py` | `intelligence/serving/rankings.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/serving/series.py` | `intelligence/serving/series.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/sources/__init__.py` | `intelligence/sources/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/sources/health.py` | `intelligence/sources/health.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/sources/registry.py` | `intelligence/sources/registry.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/storage/__init__.py` | `intelligence/storage/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/storage/check.py` | `intelligence/storage/check.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/storage/raw.py` | `intelligence/storage/raw.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/storage/rotation.py` | `intelligence/storage/rotation.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/storage/validate.py` | `intelligence/storage/validate.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/uae_relevance/README.md` | `intelligence/uae_relevance/README.md` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/uae_relevance/__init__.py` | `intelligence/uae_relevance/__init__.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/uae_relevance/classify.py` | `intelligence/uae_relevance/classify.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `intelligence/uae_relevance/rules.py` | `intelligence/uae_relevance/rules.py` | ADD | Completed production backend dependency or its module contract; preserve algorithm and selected model unchanged. |
| `platform_core/ai_facts.py` | `platform_core/ai_facts.py` | ADD | Shared Stage 18 trusted-fact adapter, safe serving boundary or native AI UI. |
| `platform_core/ai_service.py` | `platform_core/ai_service.py` | ADD | Shared Stage 18 trusted-fact adapter, safe serving boundary or native AI UI. |
| `platform_core/ai_ui.py` | `platform_core/ai_ui.py` | ADD | Retain Stage 18 UI, require portable production read gate, show exact unavailable text and actual completion timestamp. |

## SOURCE CODE TO PUSH — MODIFY

| LOCAL FILE | GITHUB DESTINATION | ACTION | REASON |
|---|---|---|---|
| `.gitignore` | `.gitignore` | MODIFY | Apply the reviewed dependency, documentation or exclusion change. |
| `DEPLOY.md` | `DEPLOY.md` | MODIFY | Apply the reviewed dependency, documentation or exclusion change. |
| `README.md` | `README.md` | MODIFY | Apply the reviewed dependency, documentation or exclusion change. |
| `build_deploy.sh` | `build_deploy.sh` | MODIFY | Apply the reviewed dependency, documentation or exclusion change. |
| `platform_core/runtime.py` | `platform_core/runtime.py` | MODIFY | Apply only the Stage 18 integration delta; keep GitHub branding and other existing behavior. |
| `platform_pages/area.py` | `platform_pages/area.py` | MODIFY | Apply only the Stage 18 integration delta; keep GitHub branding and other existing behavior. |
| `platform_pages/forecast.py` | `platform_pages/forecast.py` | MODIFY | Apply only the Stage 18 integration delta; keep GitHub branding and other existing behavior. |
| `platform_pages/region_abu_dhabi.py` | `platform_pages/region_abu_dhabi.py` | MODIFY | Apply only the Stage 18 integration delta; keep GitHub branding and other existing behavior. |
| `platform_pages/region_rak.py` | `platform_pages/region_rak.py` | MODIFY | Apply only the Stage 18 integration delta; keep GitHub branding and other existing behavior. |
| `platform_pages/region_sharjah.py` | `platform_pages/region_sharjah.py` | MODIFY | Apply only the Stage 18 integration delta; keep GitHub branding and other existing behavior. |
| `regions/dubai_market/dashboard.py` | `regions/dubai_market/dashboard.py` | MODIFY | Apply only the Stage 18 integration delta; keep GitHub branding and other existing behavior. |
| `requirements.txt` | `requirements.txt` | MODIFY | Apply the reviewed dependency, documentation or exclusion change. |
| `streamlit_app.py` | `streamlit_app.py` | MODIFY | Retain the entire main import guard and add the controlled artifact startup hook. |

The exact final changes against main are in local review evidence `validation/deployment_prerequisites/reviewed_modifications.patch`, superseding the earlier plan-only patch. Copy current allowlisted files only after checking the manifest hash. Deployment tests are local proof, not runtime inputs. Do not run the legacy build_deploy.sh or stage from the inherited home-directory Git root.

## PRODUCTION ARTIFACTS DELIVERED OUTSIDE SOURCE COMMIT

The verified bootstrap export is under `validation/deployment_prerequisites/bootstrap-release/`, containing only `production-serving.tar.gz`, `production-publisher-state.tar.gz`, and `production-release.json`. **No files under that local validation directory go into the source commit.** Only these three individually reviewed real assets may be uploaded separately as a production release after authorization. The simulated replay release and temporary runner directories are validation artifacts and must never be uploaded.

Build `2ac86fd669437a7788cc3a6fa3fd5484557b423d6d8d3e0322fc4f307256ab24` retains its real classification and original completion timestamp `2026-09-08T18:22:38.161179+00:00`. Portable DB SHA256: `a3d11387f4f5a5b18bf32d26beb016826be2340dec5e1d7a4bed69800b7b22d2`. The original database and raw archive remain unchanged. Public release visibility and exact export contents must be reviewed before upload. Runtime SQLite is not committed into main. No synthetic intelligence is a deployment option.

## LOCAL/TEST FILES NEVER TO PUSH

EXCLUDE real keys/secrets; `.env*`; real `.streamlit/secrets.toml`; temporary/runtime SQLite/WAL/SHM; `data/intelligence/**`; `data/production_intelligence/**`; raw RSS runs; test and synthetic fixtures; `intelligence/tests/**`; `intelligence/benchmarks/**`; `intelligence/validation/**`; development Ollama/gate helpers outside the allowlist; caches, virtual environments, pycache, Mac metadata; unnecessary historical local reports. Existing unchanged tests/data already on main remain there; no deletion is proposed.

## Dependencies, configuration and deployment

Retain existing root dependencies and pandas<3; add feedparser, pydantic, beautifulsoup4, lxml, python-dateutil, rapidfuzz and certifi as already used by intelligence. The daily workflow uses a separate exact fourteen-package hash lock, commit-pinned actions, one concurrency group, and contents-write only in the publisher job. Its explicit enable variable remains an operator action. Root .gitignore protects secrets/runtime/test/benchmark/cache paths and now also excludes local deployment outputs.

See [Streamlit deployment plan](STREAMLIT_DEPLOYMENT_PLAN.md) and [production contract](PRODUCTION_DEPLOYMENT.md). The actual key belongs only in existing Streamlit Secrets, never Actions. Before any authorized sync recheck main SHA, review this complete allowlist and data visibility, and review the current passing local gates plus the preserved historical strict failure. After separate authorization synchronize the tested tree, publish the initial reviewed real release, configure the existing app secret, enable/observe the workflow, and validate the same hosted app URL. No commit, push, release or deployment is part of this step.
