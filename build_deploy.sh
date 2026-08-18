#!/usr/bin/env bash
# Build the deploy folder for TruEstate Analytics.
#
#   ./build_deploy.sh            -> ~/Downloads/truestate-deploy  (~75 MB)
#   ./build_deploy.sh --with-experimental   (~372 MB)
#
# The 78 MB raw registry is replaced by its precomputed monthly counts, which
# carry identical numbers. Everything else is copied as it is.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${HOME}/Downloads/truestate-deploy"
WITH_EXP="${1:-}"

echo "Rebuilding the precomputed raw counts…"
python3 tools/build_raw_counts.py

echo "Staging into ${DEST}…"
rm -rf "$DEST"; mkdir -p "$DEST"

EXCLUDES=(
  --exclude=".venv" --exclude="__pycache__" --exclude="*.pyc" --exclude=".DS_Store"
  --exclude="data/dubai/transactions.parquet"
  --exclude="_backup_v1.1" --exclude="_patched" --exclude="build"
  --exclude=".git" --exclude="truestate-deploy"
)
if [ "$WITH_EXP" != "--with-experimental" ]; then
  EXCLUDES+=( --exclude="regions/dubai" )
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
echo "Next steps are in $DEST/DEPLOY.md"
