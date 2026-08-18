"""
Runtime that embeds an existing regional Streamlit app inside the platform.

Design goal: WRAP, don't rewrite.

The regional scripts are executed as-is with `runpy`, inside a context that
makes their original assumptions true again:

  * working directory  — both apps resolve data with bare relative filenames
                         ("target_df.csv", "df_area_plot_stats.xlsx", ...).
                         Rather than rewriting ~90 path literals we simply run
                         each region from its own directory, so every existing
                         path keeps resolving exactly as it did before.
  * import path        — the region directory and the platform root are on
                         sys.path for the duration of the run only.
  * embed flag         — tells region_bridge that the shell owns page config,
                         appearance and top-level navigation.

Everything is restored in a `finally` block, and Streamlit's own control-flow
exceptions (st.rerun / st.stop) are re-raised untouched.
"""

from __future__ import annotations

import os
import runpy
import sys
import threading
import traceback
from pathlib import Path

import streamlit as st

from . import region_bridge

# The working directory is process-global. Serialise region execution so two
# concurrent browser sessions can never observe each other's chdir.
_REGION_LOCK = threading.RLock()

# Streamlit signals reruns and stops with exceptions — these must never be
# caught and rendered as errors.
_CONTROL_FLOW = {"RerunException", "StopException", "RerunData"}


def _is_control_flow(exc: BaseException) -> bool:
    return type(exc).__name__ in _CONTROL_FLOW


def _error_card(title: str, detail: str, hint: str = "") -> None:
    hint_html = f'<p style="margin:.55rem 0 0 0;font-size:.82rem;opacity:.85">{hint}</p>' if hint else ""
    st.markdown(
        " ".join(
            f"""
            <div style="background:rgba(220,38,38,.06);border:1px solid rgba(220,38,38,.28);
                        border-left:4px solid #DC2626;border-radius:12px;padding:1.05rem 1.25rem;
                        margin:.5rem 0 1rem 0">
              <p style="margin:0;font-size:.95rem;font-weight:700;color:#B91C1C">⚠️ {title}</p>
              <p style="margin:.4rem 0 0 0;font-size:.85rem;line-height:1.6">{detail}</p>
              {hint_html}
            </div>
            """.split()
        ),
        unsafe_allow_html=True,
    )


def run_region(entry: Path, working_dir: Path, region_label: str) -> None:
    """
    Execute a regional Streamlit script inside the platform shell.

    Raises nothing to the caller except Streamlit control-flow exceptions.
    """
    entry = Path(entry)
    working_dir = Path(working_dir)

    if not entry.exists():
        _error_card(
            f"{region_label} application not found",
            f"Expected entry point <code>{entry.name}</code> in "
            f"<code>regions/{working_dir.name}/</code>.",
            "Restore the file, or check that the repository was copied in full.",
        )
        return

    with _REGION_LOCK:
        prev_cwd = os.getcwd()
        root_dir = str(Path(__file__).resolve().parent.parent)
        added_paths = []

        for path in (root_dir, str(working_dir)):
            if path not in sys.path:
                sys.path.insert(0, path)
                added_paths.append(path)

        region_bridge._set_embedded(True)
        os.chdir(working_dir)

        try:
            runpy.run_path(str(entry), run_name="__main__")

        except BaseException as exc:  # noqa: BLE001 — deliberate broad guard
            if _is_control_flow(exc):
                raise

            if isinstance(exc, FileNotFoundError):
                missing = getattr(exc, "filename", None) or str(exc)
                _error_card(
                    f"{region_label}: a required data file is missing",
                    f"The dashboard tried to open <code>{missing}</code> and could not find it.",
                    "This file ships with the regional codebase — confirm it was copied into "
                    f"<code>regions/{working_dir.name}/</code>.",
                )
            elif isinstance(exc, (ImportError, ModuleNotFoundError)):
                _error_card(
                    f"{region_label}: a required package is missing",
                    f"<code>{exc}</code>",
                    "Install the unified dependencies: <code>pip install -r requirements.txt</code>",
                )
            else:
                _error_card(
                    f"{region_label}: this section could not be rendered",
                    f"<code>{type(exc).__name__}: {exc}</code>",
                    "The rest of the platform is unaffected — use the sidebar to continue.",
                )

            # Full diagnostics stay available for development, collapsed by default.
            with st.expander("🔧 Technical details (for developers)", expanded=False):
                st.code("".join(traceback.format_exception(exc)), language="text")

        finally:
            os.chdir(prev_cwd)
            region_bridge._set_embedded(False)
            for path in added_paths:
                try:
                    sys.path.remove(path)
                except ValueError:
                    pass
