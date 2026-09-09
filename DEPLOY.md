# Deploying the existing TruEstate application

Use the existing `huddartanay/truestate-analytics` repository, `main` branch and `streamlit_app.py` entry point. The existing application is https://truestate-analytics-ncnoxrwqcqvryrx45uir6e.streamlit.app/ . Do not create another repository, app or deployment URL.

The authoritative local workspace is `FULL CODE BASE`. Synchronize only the reviewed production allowlist and preserve the deployment fixes already in GitHub main. Its inherited local Git root is the user’s home directory; do not use blanket staging from that repository.

- [Production deployment contract](intelligence/PRODUCTION_DEPLOYMENT.md)
- [GitHub synchronization plan](intelligence/GITHUB_SYNCHRONIZATION_PLAN.md)
- [Streamlit deployment plan](intelligence/STREAMLIT_DEPLOYMENT_PLAN.md)
- [Deployment prerequisites report](intelligence/DEPLOYMENT_PREREQUISITES_REPORT.md)
- [Deployment closure audit](intelligence/PRODUCTION_DEPLOYMENT_CLOSURE_REPORT.md)

The application integration, portable artifact/history delivery, daily workflow, recovery and startup contract are implemented and locally validated. No code synchronization, production release, workflow activation or hosted deployment has occurred. Review the exact source manifest, public bootstrap-artifact contents and remaining operator actions before separately authorizing synchronization. Store OPENROUTER_API_KEY only in the existing app’s Streamlit Secrets; never in Git or release assets.

The legacy build_deploy.sh targets a separate local copy and is not the synchronization mechanism for this closure. It was not executed.
