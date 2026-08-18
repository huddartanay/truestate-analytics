#!/usr/bin/env python3
"""
Work out which files under `regions/dubai/` the Experimental Analysis app
actually reads, and write the list to `regions/dubai/MANIFEST.txt`.

    python tools/build_experimental_manifest.py

Why this exists: `regions/dubai/` is 313 MB, but the six experiment generations
only ever open about 63 MB of it. The rest is saved HTML plots, spreadsheets and
intermediate CSVs that no code path touches. A hosted copy of the application
does not need them, and shipping them makes the repository four times larger for
no functional gain.

The manifest is DERIVED, not hand-written: this script parses the experimental
sources for every filename they reference, so it cannot drift out of date the
way a maintained list would. Re-run it whenever `trial.py`, `FC_st.py` or
`testing.py` changes.

Nothing about the Experimental Analysis application itself is modified. Its
source files are read here and never written.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "regions" / "dubai"
MANIFEST = EXP / "MANIFEST.txt"

#: The scripts the platform actually executes for this environment.
SOURCES = ["trial.py", "FC_st.py", "testing.py"]

#: Anything referenced as a quoted filename with one of these extensions.
DATA_SUFFIXES = (".csv", ".xlsx", ".xls", ".parquet", ".pkl", ".png", ".jpg",
                 ".json", ".txt")

QUOTED = re.compile(r"""['"]([^'"\n]{1,200}?\.(?:csv|xlsx|xls|parquet|pkl|png|jpg|json|txt))['"]""")

#: A filename can contain the other quote character — `dt_model_Me'Aisem_First.pkl`
#: is written inside double quotes and its apostrophe truncates the match above.
#: This second pass catches any file on disk whose name appears in the source at
#: all, so a quoting quirk cannot silently drop a model from the manifest.
def _by_presence(text: str, present: set[str]) -> set[str]:
    return {n for n in present if n in text}


def main() -> int:
    if not EXP.exists():
        print(f"error: {EXP} not found.", file=sys.stderr)
        return 1

    present = {p.name for p in EXP.iterdir() if p.is_file()}
    referenced: set[str] = set()

    for name in SOURCES:
        path = EXP / name
        if not path.exists():
            print(f"  note: {name} is not present, skipping it.")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for hit in QUOTED.findall(text):
            # Reduce "some/dir/file.csv" to its basename; the app reads from its
            # own working directory.
            referenced.add(Path(hit).name)
        referenced |= _by_presence(text, present)

    keep = sorted(n for n in referenced if n in present)
    unresolved = sorted(n for n in referenced if n not in present)

    # The scripts themselves, plus anything the environment needs to start.
    always = [n for n in SOURCES + ["requirements.txt", ".gitignore"] if n in present]
    keep = sorted(set(keep) | set(always))

    # Directories the app expects to exist even when empty.
    dirs = [d.name for d in EXP.iterdir() if d.is_dir() and not d.name.startswith(".")]

    MANIFEST.write_text("\n".join(keep) + "\n", encoding="utf-8")

    kept_bytes = sum((EXP / n).stat().st_size for n in keep)
    all_bytes = sum(p.stat().st_size for p in EXP.rglob("*") if p.is_file())

    print(f"referenced by the experiments : {len(referenced)}")
    print(f"present and kept              : {len(keep)}")
    if unresolved:
        print(f"referenced but not on disk    : {unresolved}")
    print(f"subdirectories (not scanned)   : {dirs}")
    print()
    print(f"kept   {kept_bytes / 1e6:>7.1f} MB")
    print(f"folder {all_bytes / 1e6:>7.1f} MB")
    print(f"saved  {(all_bytes - kept_bytes) / 1e6:>7.1f} MB")
    print(f"\nwritten: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
