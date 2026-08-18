#!/usr/bin/env bash
# Build the deploy folder for TruEstate Analytics.
#
#   ./build_deploy.sh          -> ~/Downloads/truestate-deploy
#   ./build_deploy.sh --lean   -> the same, without the Experimental artefacts
#
# The Experimental Analysis environment is included IN FULL by default. Its six
# generations read a long tail of files under regions/dubai/, and shipping that
# folder whole is the only way to guarantee every version behaves exactly as it
# does locally. --lean drops it (~250 MB smaller) but Experimental will then
# report that its entry point is missing.
#
# The 78 MB raw registry is replaced by its precomputed monthly counts, which
# carry identical numbers. Everything else is copied as it is.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${HOME}/Downloads/truestate-deploy"
MODE="${1:-}"

# Use the project venv when there is one — the aggregate needs pyarrow, which a
# bare system python usually does not have.
PY="python3"
if [ -x "$SRC/.venv/bin/python" ]; then PY="$SRC/.venv/bin/python"; fi

echo "Rebuilding the precomputed raw counts…"
if ! "$PY" tools/build_raw_counts.py; then
  if [ -f "$SRC/data/dubai/raw_transaction_counts.parquet" ]; then
    echo "  could not rebuild — keeping the existing raw_transaction_counts.parquet."
    echo "  (Re-run with the venv active if transactions.parquet has changed.)"
  else
    echo "  ERROR: no precomputed counts exist and they could not be built." >&2
    echo "  Activate the venv and re-run:  source .venv/bin/activate && ./build_deploy.sh" >&2
    exit 1
  fi
fi

echo "Staging into ${DEST}…"
# Keep .git if the destination is already a repository — otherwise re-running
# this script would throw away the remote and the commit history, and the push
# to the existing Streamlit deployment would have to start over.
mkdir -p "$DEST"
find "$DEST" -mindepth 1 -maxdepth 1 -not -name ".git" -exec rm -rf {} + 2>/dev/null || true

EXCLUDES=(
  --exclude=".venv" --exclude="__pycache__" --exclude="*.pyc" --exclude=".DS_Store"
  --exclude="data/dubai/transactions.parquet"
  --exclude="_backup_v1.1" --exclude="_patched" --exclude="build"
  --exclude=".git" --exclude="truestate-deploy"
)
if [ "$MODE" = "--lean" ]; then
  EXCLUDES+=( --exclude="regions/dubai" )
  echo "  --lean: leaving out the Experimental Analysis artefacts."
else
  echo "  including the Experimental Analysis environment in full."
fi

( cd "$SRC" && tar -cf - "${EXCLUDES[@]}" . ) | ( cd "$DEST" && tar -xf - )

cat > "$DEST/.gitignore" <<'GI'
.venv/
__pycache__/
*.pyc
.DS_Store
data/dubai/transactions.parquet
_backup_v1.1/
_patched/
GI

echo
echo "Done: $DEST  ($(du -sh "$DEST" | cut -f1))"
if [ -d "$DEST/.git" ]; then
  echo
  echo "This folder is already connected to GitHub. To update the live app:"
  echo "    cd $DEST && git add -A && git commit -m \"update\" && git push"
  echo "Streamlit Cloud redeploys automatically on push."
else
  echo "Next steps are in $DEST/DEPLOY.md"
fi
