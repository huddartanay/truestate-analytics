"""
Static configuration for the intelligence layer.

Runtime data lives under `data/intelligence/`, which is gitignored — see
`.gitignore`. This module reads env-var overrides so the same code runs
against a local Ollama and against a remote endpoint without file edits.

Stage 3 uses only the paths section. Ollama, thresholds and prompts are
introduced by later stages.
"""

from __future__ import annotations

import os
from pathlib import Path


# ── Paths ────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "intelligence"

DB_PATH = DATA_DIR / "intelligence.db"
RAW_ARTICLES_DIR = DATA_DIR / "raw_articles"
LOGS_DIR = DATA_DIR / "logs"
PROMPTS_LOG_DIR = DATA_DIR / "prompts_used"
BACKUPS_DIR = DATA_DIR / "backups"


def ensure_data_dirs() -> None:
    """Create the runtime storage layout. Idempotent."""
    for d in (DATA_DIR, RAW_ARTICLES_DIR, LOGS_DIR, PROMPTS_LOG_DIR, BACKUPS_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ── RSS fetcher (used by Stage 4; declared here so all config is one place) ──
RSS_USER_AGENT = os.getenv(
    "INTELLIGENCE_RSS_USER_AGENT",
    "TruEstate-Intelligence/1.0 (+https://github.com/huddartanay/truestate-analytics)",
)
RSS_TIMEOUT_SECONDS = float(os.getenv("INTELLIGENCE_RSS_TIMEOUT", "20"))
RSS_MAX_CONCURRENT = int(os.getenv("INTELLIGENCE_RSS_MAX_CONCURRENT", "4"))
RSS_MAX_BYTES = int(os.getenv("INTELLIGENCE_RSS_MAX_BYTES", str(4_000_000)))

# ── Raw JSONL rotation (Stage 5) ──────────────────────────────────────────
# Maximum bytes a single YYYY-MM-DD[.NN].jsonl partition may grow to before
# writes roll over into the next partition. Historical files are NEVER
# renamed — rotation only ever creates new files, so article_sightings
# pointers stay stable.
RAW_JSONL_MAX_BYTES = int(os.getenv(
    "INTELLIGENCE_RAW_JSONL_MAX_BYTES", str(100 * 1024 * 1024)   # 100 MB
))


# ── Relevance thresholds (used by Stages 8–9; declared here now for reference)
RELEVANCE_MIN_LOCAL = int(os.getenv("INTELLIGENCE_RE_MIN_LOCAL", "3"))
RELEVANCE_MIN_INTERNATIONAL = int(
    os.getenv("INTELLIGENCE_RE_MIN_INTERNATIONAL", "4")
)


# ── Stage 15 local runtime: no configuration cleared the measured critical gate.
# No environment model override, candidate list or production fallback is allowed.
# A future measured selection must pin exactly one model before generation works.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
SELECTED_MODEL = None
SELECTED_PROMPT_STRATEGY = None
MODEL_SELECTION_STATUS = "NO_QUALIFYING_CONFIGURATION"
OLLAMA_MODEL = ""
OLLAMA_CONTEXT_LENGTH = None
OLLAMA_TEMPERATURE = None
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT", "90"))


# ── Schema / registry version stamps ─────────────────────────────────────────
SCHEMA_VERSION = "v0.9"      # Stage 13 additive serving and derived analytics
REGISTRY_VERSION = "v0.1"    # bump when sources/registry.py contents change materially
CLEANING_VERSION = "stage6-v1"

# Stage 7: conservative fixture-evaluated v1; changes require a new version.
DEDUP_VERSION = "stage7-v1"
DEDUP_TITLE_MIN = 90.0
DEDUP_BODY_MIN = 97.0
DEDUP_OVERALL_MIN = 96.0
DEDUP_BODY_WEIGHT = 0.8
DEDUP_LENGTH_RATIO_MIN = 0.90
DEDUP_EXACT_MIN_WORDS = 12
DEDUP_EXACT_MIN_CHARS = 80
DEDUP_NEAR_MIN_WORDS = 40
DEDUP_NEAR_MIN_CHARS = 240
DEDUP_TITLE_MIN_WORDS = 3
DEDUP_WINDOW_DAYS = 7
DEDUP_SHINGLE_WORDS = 5
DEDUP_SKETCH_SIZE = 8

# Local cooperating processes; unsupported advisory-lock platforms fail closed.
OPERATION_LOCK_TIMEOUT_SECONDS = 5.0
STALE_RUN_SECONDS = 3600

# Stage 8 is geography-agnostic; the legacy local/international settings above
# are not used by this classifier. Lexical rules live in relevance/rules.py.
RELEVANCE_VERSION = "stage8-v1"
RELEVANCE_ACCEPT_SCORE = 3
RELEVANCE_BODY_DENSITY = 0.03
RELEVANCE_BODY_STRONG_DENSITY = 0.05
RELEVANCE_CONTEXT_WINDOW = 12
RELEVANCE_MAX_EVIDENCE = 24


UAE_RELEVANCE_VERSION = "stage9-v1"


ENTITY_EXTRACTION_VERSION = "stage10-v1"
ENTITY_REGISTRY_VERSION = "entity-registry-v1"
EVENT_EXTRACTION_VERSION = "stage11-v1"
METRIC_EXTRACTION_VERSION = "stage12-v1"
INTELLIGENCE_BUILD_VERSION = "stage13-v1"
MARKET_MOVEMENT_VERSION = "stage13-v1"
RANKING_VERSION = "stage13-v1"


__all__ = [
    "INTELLIGENCE_BUILD_VERSION", "MARKET_MOVEMENT_VERSION", "RANKING_VERSION",
    "EVENT_EXTRACTION_VERSION", "METRIC_EXTRACTION_VERSION",
    "ENTITY_EXTRACTION_VERSION", "ENTITY_REGISTRY_VERSION",
    "UAE_RELEVANCE_VERSION",
    "ROOT_DIR", "DATA_DIR", "DB_PATH", "RAW_ARTICLES_DIR", "LOGS_DIR",
    "PROMPTS_LOG_DIR", "BACKUPS_DIR", "ensure_data_dirs",
    "RSS_USER_AGENT", "RSS_TIMEOUT_SECONDS", "RSS_MAX_CONCURRENT", "RSS_MAX_BYTES",
    "RAW_JSONL_MAX_BYTES",
    "RELEVANCE_MIN_LOCAL", "RELEVANCE_MIN_INTERNATIONAL",
    "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS",
    "SELECTED_MODEL", "SELECTED_PROMPT_STRATEGY", "MODEL_SELECTION_STATUS",
    "OLLAMA_CONTEXT_LENGTH", "OLLAMA_TEMPERATURE",
    "SCHEMA_VERSION", "REGISTRY_VERSION", "CLEANING_VERSION",
    "DEDUP_VERSION", "DEDUP_TITLE_MIN", "DEDUP_BODY_MIN", "DEDUP_OVERALL_MIN",
    "DEDUP_BODY_WEIGHT", "DEDUP_LENGTH_RATIO_MIN", "DEDUP_EXACT_MIN_WORDS",
    "DEDUP_EXACT_MIN_CHARS", "DEDUP_NEAR_MIN_WORDS", "DEDUP_NEAR_MIN_CHARS",
    "DEDUP_TITLE_MIN_WORDS", "DEDUP_WINDOW_DAYS", "DEDUP_SHINGLE_WORDS", "DEDUP_SKETCH_SIZE",
    "OPERATION_LOCK_TIMEOUT_SECONDS", "STALE_RUN_SECONDS",
    "RELEVANCE_VERSION", "RELEVANCE_ACCEPT_SCORE", "RELEVANCE_BODY_DENSITY",
    "RELEVANCE_BODY_STRONG_DENSITY", "RELEVANCE_CONTEXT_WINDOW", "RELEVANCE_MAX_EVIDENCE",
]

# Merged Stage 14: deterministic read-only query control. No model runtime.
QUERY_ROUTER_VERSION = "stage14-v1"
INTELLIGENCE_ACTION_VERSION = "stage14-v1"
PREDEFINED_QUESTION_VERSION = "stage14-v1"
SUGGESTED_PROMPT_VERSION = "stage14-v1"
__all__ += ["QUERY_ROUTER_VERSION", "INTELLIGENCE_ACTION_VERSION", "PREDEFINED_QUESTION_VERSION", "SUGGESTED_PROMPT_VERSION"]

# Stage 15 runtime/benchmark contract; selection is persisted only after measurement.
MODEL_SELECTION_VERSION = "stage15-v1"
__all__ += ["MODEL_SELECTION_VERSION"]
