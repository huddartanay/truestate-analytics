# Production intelligence deployment contract

**Locally implemented and validated; no Git synchronization or hosted deployment has occurred.** The existing target remains `huddartanay/truestate-analytics` → `main` → `streamlit_app.py`, serving the existing truestate-analytics app.

## Architecture and portable history

B + C is implemented: the daily publisher restores a verified real checkpoint, runs the existing registered RSS pipeline, and publishes versioned GitHub release assets. Streamlit downloads only a serving bundle into an ephemeral cache. Runtime SQLite files are never normal source commits. The app does not ingest RSS, execute Stages 3–13 or call a model on startup.

`production-serving.tar.gz` contains `current.json`, one `builds/<sha256>/intelligence.db`, its `manifest.json`, and the bundle integrity manifest. The existing Stage 13 schema and its operational metadata are retained because the production gate and foreign keys require them; raw JSONL files are absent from the serving bundle.

`production-publisher-state.tar.gz` separately contains the same verified serving checkpoint, a consistent full working SQLite backup, `history.json`, the cumulative receipt ledger and exactly the referenced real raw JSONL partitions. This retains deduplication, observations, prior periods, rankings, lineage and idempotency without manufacturing missing periods or rankings. Temporary runs, logs, candidate builds, locks, credentials and fixtures are excluded. Missing or invalid latest publisher history stops the job; it never restarts from empty state or silently rolls history back.

The exporter copies SQLite, changes only `article_sightings.raw_jsonl_path` to a validated partition name relative to `RAW_ARTICLES_DIR`, and VACUUMs the copy so old absolute strings do not survive in free pages. The existing Stage 5 reader already resolves that representation. Every raw pointer is checked against its exact source/article/hash record and receipt. Original databases/raw files are untouched; the portable copy has a new SHA256 with `origin_sha256` preserving its source identity. Serving and history build IDs/timestamps/receipts must agree.

## Integrity and publication boundary

Contract `truestate-portable-production-v1` supplements the existing `stage18-production-v1` gate. Export and materialization require PRODUCTION, COMPLETE, coherent, supported schema/build versions, completed timestamp, registered real-source receipts, attested raw identities, full SQLite integrity and foreign-key checks. TEST/SYNTHETIC/fixture identities, missing metadata, unsupported versions, hash corruption and developer paths fail closed.

Each tar member has a SHA256 and length in `bundle.json`. `production-release.json` binds both compressed assets to SHA256/length and the production build/timestamp/DB digest. Archives are restricted to exact expected members, regular files, safe relative names, at most 20,000 members and 512 MiB compressed/expanded; links, traversal, duplicates and unexpected DBs fail. GitHub asset digests and sizes are also checked when present on reads and are required after uploads. No archive extraction API can write outside staging.

Hashes detect corruption, not an administrator forging provenance. Repository write access and the real-ingestion attesting publisher are the explicit trust boundary inherited from Stage 18. This public repository's release assets are public: review the exact bootstrap serving/history exports before separately approving upload.

Tags are `truestate-intelligence-v1-YYYYMMDDTHHMMSSZ-<artifact-sha-first12>-<run-id>`. The publisher verifies both bundles before creating a draft; all three assets must upload and match before publishing. Failed uploads remain drafts, ignored by readers. Existing releases are neither overwritten nor deleted. No application rerun creates a release.

## Workflow and dependencies

`.github/workflows/production-intelligence.yml` targets existing main, daily `17 2 * * *` (02:17 UTC), and manual dispatch. A single concurrency group does not cancel a running publisher. The job is **disabled until the operator sets repository variable `TRUESTATE_INTELLIGENCE_ENABLED=true`**, after the first verified real release exists. It uses Ubuntu 24.04/Python 3.12, commit-pinned official checkout/setup-python actions and `pip --require-hashes` with the fourteen-package `deploy/requirements-intelligence.lock`. Linux-compatible wheels and their hashes were resolved and checked offline; hosted Actions execution remains an operator verification, not a claimed local Linux run.

Only `contents: write` is granted to the publisher job for release/tag creation; default permission is contents read. Checkout does not persist credentials. `GITHUB_TOKEN` is used only by release transport and removed from the ingestion child; OPENROUTER_API_KEY is removed and never configured for the workflow. Only the existing enabled registry is fetched, sequentially, respecting its intervals and conditional cache state. No new/disabled sources, discovery or cross-provider fallback.

`python -m intelligence.production.release_job scheduled` restores latest history into a fresh runner, invokes the existing refresh CLI, rejects any failed registered acquisition or unsuccessful pipeline, packages and validates both outputs, then publishes. Failure leaves the prior remote release available. Safe workflow error codes identify the failed boundary without logging headers, keys or response bodies.

GitHub schedules are best effort and public-repository inactivity may disable them. Monitor workflow status and the actual displayed completion timestamp. See [GitHub schedule behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) and [release API](https://docs.github.com/en/rest/releases/releases).

## Startup, secrets and fallback

The sole entry point retains main's import retry guard and watcher setting, and calls the startup adapter. Default local cache is a runtime temporary directory; `TRUESTATE_PRODUCTION_ROOT` may select a writable cache. Release retrieval uses the fixed approved repository and HTTPS GitHub asset hosts, bounded downloads and no write credentials. An advisory lock plus a persisted check timestamp limits checks to hourly across reruns/cache clearing. A warm-cache transfer failure retains the verified current build; a cold cache tries up to three published candidates. A lost/corrupt pointer may recover an older locally verified generation. Corrupt candidates never replace the current pointer.

The AI component independently requires the full portable serving gate. Missing data leaves analytics usable and displays “TruEstate intelligence data is currently unavailable.” It keeps exactly five contextual suggestions and free-form UAE questions. “Intelligence updated: <actual completed_at>” reports build completion, not live acquisition or an invented freshness time. Source publication/retrieval dates remain available.

The real model key belongs only in existing Streamlit app → Manage app → Settings → Secrets, as top-level `OPENROUTER_API_KEY`. Enter its value privately; never in Git, workflow YAML, reports or release data. Missing credentials do not break dashboards. The existing Qwen configuration and bounded provider behavior remain unchanged. See [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

## Local checks and remaining operator sequence

Read `DEPLOYMENT_PREREQUISITES_REPORT.md` for evidence: deployment tests, real clean-runner replay, six actual Streamlit routes, existing Stage 18/17/16/query/provider/MVP/application regression, and the preserved historical strict failure. No real RSS fetch, paid inference, release creation or remote workflow run occurred.

After separate authorization: recheck main; synchronize the exact manifest; review and upload the prepared real bootstrap assets with the validated publisher; configure the existing app secret/confirm Cloud Python; enable the workflow variable; observe one manual run and cold hosted startup at the same URL. A first scheduled run deliberately stops if no verified bootstrap release exists. The validated `GitHubReleases.publish` API supports the one-time reviewed bootstrap with a trusted commit/run identifier and operator credential; no bootstrap publication was attempted here.

Code rollback is a reviewed revert on the same main, never reset/force-push. Website data rollback can set process configuration `TRUESTATE_INTELLIGENCE_RELEASE_TAG` to a previously verified tag in the same namespace/repository and restart/allow the bounded refresh interval. The scheduler still restores latest publisher history, independently of a website rollback. Keep prior compatible releases; no automatic deletion. Never substitute fixtures.
