# Deploying TruEstates analytics to Streamlit Community Cloud

This folder is deploy-ready. Every route in it has been rendered headlessly and
all six test suites pass against it.

**I cannot press the deploy button for you.** Streamlit Community Cloud deploys
from a GitHub repository and requires you to sign in to GitHub and to Streamlit
in a browser. Creating accounts or entering your credentials is not something I
will do on your behalf, so the last three steps below are yours. They take about
ten minutes.

---

## 1. What is in this folder, and what was left out

| | |
|---|---|
| Size | ~372 MB with the Experimental artefacts, ~73 MB without them |
| Largest file | `data/dubai/latest_combined_data.parquet`, 52 MB |
| Left out | `data/dubai/transactions.parquet` (78 MB), `.venv/`, `__pycache__`, `_backup_v1.1/`, `_patched/` |

**The 78 MB raw registry is not needed to run this.** `tools/build_raw_counts.py`
aggregated it into `data/dubai/raw_transaction_counts.parquet` — 6.7 KB, and
every count in it is identical to the number the application would compute from
the registry itself (verified row by row: 519 rows, 928,489 residential unit
sales, 1,762,258 transactions in total). The application reads the registry when
it is present and this aggregate only when it is not, so your local copy is
unaffected.

Re-run `python tools/build_raw_counts.py` whenever the registry is replaced,
or the hosted copy will describe an older registry than your local one.

### Decide this before you push

`regions/dubai/` is 299 MB of Experimental Analysis artefacts — model pickles,
intermediate CSVs and saved HTML plots. They are what the 🧪 Experimental
Analysis section reads.

- **Keep them** and the repository is ~372 MB. Nothing exceeds GitHub's 100 MB
  per-file limit, so it will push, but the clone is slow and Streamlit's free
  tier will feel it.
- **Drop them** (`rm -rf regions/dubai`) and the repository is ~73 MB and
  comfortable. The eight other routes are unaffected; 🧪 Experimental Analysis
  will report that its artefacts are unavailable rather than showing figures.

For a public demo, dropping them is the better trade.

## 2. Two things to decide before this is public

**The data becomes public.** The Dubai Land Department transaction records and
the Abu Dhabi sales file are both in this repository. On Streamlit Community
Cloud the repository must be public, so anyone can download them. If that is not
intended, deploy from a private repo on a paid tier, or host somewhere with
access control.

**The forecast endpoint becomes reachable through the app.** Every Market Pulse
press makes the hosted server call `http://51.38.112.237:9500/forecast`, which
has no authentication. A public URL means anyone can drive requests at that
service as fast as they like. Consider putting the endpoint behind a key, rate
limiting it, or leaving the Forecast section out of the public build.

## 3. Push to GitHub

```bash
cd ~/Downloads/truestate-deploy

# optional, per the decision above
rm -rf regions/dubai

git init -b main
git add -A
git commit -m "TruEstates analytics"
```

Create an empty repository at <https://github.com/new> — **public**, and do not
add a README or .gitignore. Then:

```bash
git remote add origin https://github.com/<your-username>/truestate-analytics.git
git push -u origin main
```

GitHub will warn about the 52 MB parquet. That is a warning, not a rejection —
the limit is 100 MB.

## 4. Deploy

1. Go to <https://share.streamlit.io> and sign in with the same GitHub account.
2. **Create app** → **Deploy a public app from GitHub**.
3. Repository `<your-username>/truestate-analytics`, branch `main`,
   main file path `streamlit_app.py`.
4. **Deploy**.

The first build installs the dependencies and takes a few minutes. Your URL will
be `https://<something>.streamlit.app` — click **Advanced settings** before
deploying if you want to choose the subdomain.

## 5. If the build fails

- **`ModuleNotFoundError`** — a dependency is missing from `requirements.txt`.
  Add it and push; the app redeploys automatically.
- **App restarts, or "Oh no"** — the free tier's memory ceiling. The Dubai
  dataset caches at roughly 55 MB, which fits, but opening several heavy tabs at
  once can push past it. Dropping `regions/dubai/` helps most.
- **First load is slow** — expected. The 52 MB parquet is read and cached on
  first request; everything after that is fast until the app sleeps.
- **App has gone to sleep** — free-tier apps idle out after inactivity. Anyone
  visiting can wake it, but the first visitor waits.
