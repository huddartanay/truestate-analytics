# STREAMLIT DEPLOYMENT PLAN

**READY FOR FINAL REVIEWED GITHUB SYNC — locally validated only. No push or deployment performed.**

| Setting | Exact target / behavior |
|---|---|
| Existing repository | huddartanay/truestate-analytics |
| Deployment branch | main |
| Entry point | streamlit_app.py |
| Existing app | truestate-analytics |
| Existing URL | https://truestate-analytics-ncnoxrwqcqvryrx45uir6e.streamlit.app/ |
| Python | Local application tested on 3.12; confirm existing Cloud setting before deployment. |
| Website dependencies | Reviewed root requirements preserve existing website packages and pandas<3, adding the seven completed intelligence dependencies. |
| Ingestion dependencies | Separate fourteen-package Linux/Python 3.12 hash lock. |
| Model secret | Existing app → Manage app → Settings → Secrets → top-level OPENROUTER_API_KEY; enter privately. |
| Durable data | Validated real GitHub release serving/history assets in this same repository; never source SQLite commits. |
| Startup | Controlled serving-artifact materialization and full gate; no RSS, stages or model calls. |
| Reruns | Hourly artifact check bound; no RSS or automatic inference. |
| Missing/invalid data | Last verified build if available; otherwise analytics plus exact unavailable message. |
| Freshness | Intelligence updated: actual completed_at, with original source dates retained. |
| Daily refresh | 02:17 UTC + manual dispatch; operator-enable variable remains unset. |
| Rollback | Reviewed main revert and prior compatible release tag; no force-push, no empty-history publisher fallback. |

All six routes were exercised through the actual entry point: Dubai, Abu Dhabi, Sharjah, RAK, Area Analysis and Market Outlook. Each retained AI Market Summary, Ask TruEstate, exactly five suggestions, free-form input and verified real-build freshness. Reruns and mocked summary/help interactions made no RSS requests; startup made no Qwen request; the real model key was absent during testing.

Before actual deployment, separately authorize synchronization, review public visibility of the exact real bootstrap exports, publish the initial verified release, configure the existing app secret, confirm Cloud Python, set repository variable TRUESTATE_INTELLIGENCE_ENABLED=true, observe a manual workflow and cold hosted startup. These are operator actions, not completed hosted checks. No new repository/app/URL.

See [the production contract](PRODUCTION_DEPLOYMENT.md), [exact synchronization manifest](GITHUB_SYNCHRONIZATION_PLAN.csv), and [implementation report](DEPLOYMENT_PREREQUISITES_REPORT.md). Secrets guidance: [Streamlit documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).
