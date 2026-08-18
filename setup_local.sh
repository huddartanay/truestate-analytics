#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
#  UAE Real Estate Analytics — local assembly
#
#  Fills regions/abu_dhabi and regions/dubai from your two original zips.
#  Nothing is downloaded and your original zips are not modified.
#
#  Usage, from inside this folder:
#      ./setup_local.sh
#      ./setup_local.sh /path/to/abu-dhabi-...zip /path/to/adding_modified--main.zip
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="${HOME}/Downloads"

AD_ZIP="${1:-${DOWNLOADS}/abu-dhabi-real-estate-dashboard-main.zip}"
DXB_ZIP="${2:-${DOWNLOADS}/adding_modified--main.zip}"

say()  { printf '\033[1;34m▸\033[0m %s\n' "$1"; }
ok()   { printf '\033[1;32m✓\033[0m %s\n' "$1"; }
die()  { printf '\033[1;31m✗\033[0m %s\n' "$1" >&2; exit 1; }

[ -f "$AD_ZIP" ]  || die "Abu Dhabi zip not found: $AD_ZIP"
[ -f "$DXB_ZIP" ] || die "Dubai zip not found: $DXB_ZIP"
[ -d "$HERE/_patched" ] || die "_patched/ is missing — run this from the folder it shipped in."

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ── Abu Dhabi ───────────────────────────────────────────────────────────────
say "Unpacking Abu Dhabi…"
unzip -q -o "$AD_ZIP" -d "$TMP/ad"
AD_SRC="$(find "$TMP/ad" -maxdepth 3 -type d -name 'abu dhabi dashboard' | head -1)"
[ -n "$AD_SRC" ] || die "Could not find the 'abu dhabi dashboard' folder inside $AD_ZIP"

rm -rf "$HERE/regions/abu_dhabi"
mkdir -p "$HERE/regions"
cp -R "$AD_SRC" "$HERE/regions/abu_dhabi"
find "$HERE/regions/abu_dhabi" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
ok "regions/abu_dhabi  ($(find "$HERE/regions/abu_dhabi" -type f | wc -l | tr -d ' ') files)"

# ── Dubai ───────────────────────────────────────────────────────────────────
say "Unpacking Dubai… (this one is large, give it a moment)"
unzip -q -o "$DXB_ZIP" -d "$TMP/dxb"
DXB_SRC="$(find "$TMP/dxb" -maxdepth 3 -type f -name 'trial.py' | head -1)"
[ -n "$DXB_SRC" ] || die "Could not find trial.py inside $DXB_ZIP"
DXB_SRC="$(dirname "$DXB_SRC")"

rm -rf "$HERE/regions/dubai"
cp -R "$DXB_SRC" "$HERE/regions/dubai"
rm -rf "$HERE/regions/dubai/.devcontainer"
find "$HERE/regions/dubai" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
ok "regions/dubai  ($(find "$HERE/regions/dubai" -type f | wc -l | tr -d ' ') files)"

# ── Integration edits (see docs/INTEGRATION_CHANGES.md) ─────────────────────
say "Applying the 8 documented integration edits…"
cp "$HERE/_patched/abu_dhabi_app.py" "$HERE/regions/abu_dhabi/app.py"
cp "$HERE/_patched/dubai_trial.py"   "$HERE/regions/dubai/trial.py"
ok "regions/abu_dhabi/app.py and regions/dubai/trial.py updated"

# ── Sanity check ────────────────────────────────────────────────────────────
say "Checking required data files…"
MISSING=0
for f in "regions/abu_dhabi/Abu_Dhabi_Sales_Cleaned (1).csv" \
         "regions/dubai/target_df.csv" \
         "regions/dubai/onehot_encoder.pkl" \
         "regions/dubai/train_columns.pkl"; do
  [ -f "$HERE/$f" ] || { printf '  \033[1;31mmissing:\033[0m %s\n' "$f"; MISSING=1; }
done
PKL_COUNT="$(ls "$HERE/regions/dubai"/dt_model_*.pkl 2>/dev/null | wc -l | tr -d ' ')"
[ "$PKL_COUNT" = "20" ] || { printf '  \033[1;33mwarning:\033[0m found %s of 20 area models\n' "$PKL_COUNT"; }
[ "$MISSING" = "0" ] && ok "all key data and model files present"

cat <<'EOF'

────────────────────────────────────────────────────────────
  Ready. Next:

      python3 -m venv .venv
      source .venv/bin/activate
      pip install -r requirements.txt
      streamlit run streamlit_app.py

  Then open http://localhost:8501
────────────────────────────────────────────────────────────
EOF
