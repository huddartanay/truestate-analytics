-- ═══════════════════════════════════════════════════════════════════════════
-- Intelligence layer — operational SQLite schema
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Stages 4–12 operational evidence plus Stage 13 serving projections.
--
-- Stage 4 tables `feed_run_log` and `article_sightings` support:
--   1. Per-source-per-run operational logging (start/end, status, counts,
--      error type, ETag / Last-Modified for conditional requests)
--   2. Idempotent sighting of raw articles (dedup by article_id + raw_hash,
--      merely counts re-sightings without re-writing raw payloads)
-- Stage 6 adds separate cleaned versions and cleaning-run metadata below.
--
-- Stage 13 adds coherent serving builds below; no query or LLM runtime.
--
-- Portability: TEXT for UUIDs and ISO-8601 timestamps, no SQLite-only
-- functions, all FKs are named so Postgres migration is a mechanical port.
-- ═══════════════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- ── feed_run_log ─────────────────────────────────────────────────────────
-- One row per attempt to fetch one source. Nothing else writes here.
CREATE TABLE IF NOT EXISTS feed_run_log (
    run_id            TEXT PRIMARY KEY,          -- UUID
    source_id         TEXT NOT NULL,             -- registry source_id
    started_at        TEXT NOT NULL,             -- ISO-8601 UTC
    completed_at      TEXT,                      -- NULL while in-flight
    status            TEXT NOT NULL,             -- SUCCESS | NOT_MODIFIED |
                                                 -- SKIPPED_RATE_LIMIT |
                                                 -- FAILED_UNAVAILABLE |
                                                 -- FAILED_MALFORMED |
                                                 -- FAILED_TIMEOUT |
                                                 -- FAILED_EMPTY (info) |
                                                 -- FAILED_OTHER
    http_status       INTEGER,                   -- NULL if request never made
    entries_seen      INTEGER NOT NULL DEFAULT 0,
    entries_new       INTEGER NOT NULL DEFAULT 0,
    entries_duplicate INTEGER NOT NULL DEFAULT 0,
    duration_ms       INTEGER,
    etag              TEXT,                      -- captured for next conditional GET
    last_modified     TEXT,                      -- captured for next conditional GET
    error_type        TEXT,                      -- typed exception class name
    error_message     TEXT                       -- <= 500 chars, truncated in code
);

CREATE INDEX IF NOT EXISTS ix_feed_run_log_source_started
    ON feed_run_log (source_id, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_feed_run_log_started
    ON feed_run_log (started_at DESC);


-- ── article_sightings ─────────────────────────────────────────────────────
-- One row per (source_id, article_id, raw_hash) — a "sighting" of a raw
-- article. Repeated identical sightings only bump last_seen_at + counter.
-- If the raw_hash changes for the same article_id, a NEW row is inserted
-- (i.e., we treat a body edit as a distinct sighting). The Stage 7 dedupe
-- engine will use these rows to reason about identity across sources.
CREATE TABLE IF NOT EXISTS article_sightings (
    sighting_id     TEXT PRIMARY KEY,            -- UUID
    source_id       TEXT NOT NULL,               -- registry source_id
    article_id      TEXT NOT NULL,               -- deterministic
                                                 --   sha1(source_id::stable_key)
    raw_hash        TEXT NOT NULL,               -- deterministic
                                                 --   sha256(title|url|pub|body)
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    sighting_count  INTEGER NOT NULL DEFAULT 1,
    -- Denormalised pointers into the raw JSONL log so the row is self-locating
    -- without joining anything else.
    raw_jsonl_path  TEXT NOT NULL,               -- e.g., data/intelligence/raw_articles/2026-09-03.jsonl
    raw_jsonl_line  INTEGER NOT NULL,            -- 1-based line number
    UNIQUE (source_id, article_id, raw_hash)
);

CREATE INDEX IF NOT EXISTS ix_sightings_article
    ON article_sightings (article_id);
CREATE INDEX IF NOT EXISTS ix_sightings_source_last_seen
    ON article_sightings (source_id, last_seen_at DESC);


-- ── schema_meta ───────────────────────────────────────────────────────────
-- A single-row table recording the schema version applied. Later stages will
-- add proper migrations under `db/migrations/`; for now this is a simple
-- guard so `apply_schema` is idempotent and detects drift.
CREATE TABLE IF NOT EXISTS schema_meta (
    key          TEXT PRIMARY KEY,
    value        TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

-- Stage 6: independent cleaned versions; no changes to raw sightings.
CREATE TABLE IF NOT EXISTS cleaned_articles (
    article_id               TEXT NOT NULL CHECK (length(article_id) = 40),
    raw_hash                 TEXT NOT NULL CHECK (length(raw_hash) = 64),
    cleaning_version         TEXT NOT NULL,
    source_id                TEXT NOT NULL,
    source_name              TEXT NOT NULL,
    rss_url                  TEXT NOT NULL,
    retrieved_at             TEXT NOT NULL,
    content_type             TEXT NOT NULL CHECK (content_type = 'rss'),
    clean_title              TEXT NOT NULL,
    clean_body               TEXT NOT NULL,
    normalized_published_at  TEXT,
    detected_language        TEXT NOT NULL CHECK (detected_language IN ('en', 'ar', 'mixed', 'unknown')),
    word_count               INTEGER NOT NULL CHECK (word_count >= 0),
    date_parse_error         INTEGER NOT NULL CHECK (date_parse_error IN (0, 1)),
    PRIMARY KEY (article_id, raw_hash, cleaning_version),
    CHECK (date_parse_error = 0 OR normalized_published_at IS NULL)
);
CREATE INDEX IF NOT EXISTS ix_cleaned_source_retrieved
    ON cleaned_articles (source_id, retrieved_at);
CREATE INDEX IF NOT EXISTS ix_cleaned_published
    ON cleaned_articles (normalized_published_at);

CREATE TABLE IF NOT EXISTS cleaning_run_log (
    run_id             TEXT PRIMARY KEY,
    started_at         TEXT NOT NULL,
    completed_at       TEXT,
    status             TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'PARTIAL_SUCCESS', 'FAILED')),
    records_seen       INTEGER NOT NULL DEFAULT 0,
    records_cleaned    INTEGER NOT NULL DEFAULT 0,
    records_failed     INTEGER NOT NULL DEFAULT 0,
    records_skipped    INTEGER NOT NULL DEFAULT 0,
    files_failed       INTEGER NOT NULL DEFAULT 0,
    duration_ms        INTEGER,
    cleaning_version   TEXT NOT NULL,
    since              TEXT,
    error_count        INTEGER NOT NULL DEFAULT 0,
    error_type         TEXT,
    error_message      TEXT,
    errors_json        TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS ix_cleaning_run_started
    ON cleaning_run_log (started_at DESC);

-- Stage 7: positive relationships and immutable group snapshots only.
CREATE TABLE IF NOT EXISTS article_duplicate_pairs (
    cleaning_version   TEXT NOT NULL,
    dedup_version      TEXT NOT NULL CHECK (length(dedup_version) BETWEEN 1 AND 64),
    left_article_id    TEXT NOT NULL,
    left_raw_hash      TEXT NOT NULL,
    right_article_id   TEXT NOT NULL,
    right_raw_hash     TEXT NOT NULL,
    duplicate_type     TEXT NOT NULL CHECK (duplicate_type IN ('EXACT_DUPLICATE', 'NEAR_DUPLICATE')),
    exact_fingerprint  TEXT,
    title_similarity   REAL NOT NULL CHECK (title_similarity BETWEEN 0 AND 100),
    body_similarity    REAL NOT NULL CHECK (body_similarity BETWEEN 0 AND 100),
    overall_similarity REAL NOT NULL CHECK (overall_similarity BETWEEN 0 AND 100),
    created_at         TEXT NOT NULL,
    PRIMARY KEY (cleaning_version, dedup_version, left_article_id, left_raw_hash, right_article_id, right_raw_hash),
    CHECK ((left_article_id, left_raw_hash) < (right_article_id, right_raw_hash)),
    CHECK ((duplicate_type = 'EXACT_DUPLICATE' AND exact_fingerprint IS NOT NULL AND length(exact_fingerprint) = 64)
        OR (duplicate_type = 'NEAR_DUPLICATE' AND exact_fingerprint IS NULL)),
    FOREIGN KEY (left_article_id, left_raw_hash, cleaning_version)
        REFERENCES cleaned_articles (article_id, raw_hash, cleaning_version),
    FOREIGN KEY (right_article_id, right_raw_hash, cleaning_version)
        REFERENCES cleaned_articles (article_id, raw_hash, cleaning_version)
);
CREATE INDEX IF NOT EXISTS ix_duplicate_pairs_right
    ON article_duplicate_pairs (cleaning_version, dedup_version, right_article_id, right_raw_hash);

CREATE TABLE IF NOT EXISTS duplicate_groups (
    cleaning_version     TEXT NOT NULL,
    dedup_version        TEXT NOT NULL,
    group_id             TEXT NOT NULL CHECK (length(group_id) = 64),
    canonical_article_id TEXT NOT NULL,
    canonical_raw_hash   TEXT NOT NULL,
    member_count         INTEGER NOT NULL CHECK (member_count >= 2),
    members_json         TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    PRIMARY KEY (cleaning_version, dedup_version, group_id),
    FOREIGN KEY (canonical_article_id, canonical_raw_hash, cleaning_version)
        REFERENCES cleaned_articles (article_id, raw_hash, cleaning_version)
);

CREATE TABLE IF NOT EXISTS dedup_run_log (
    run_id             TEXT PRIMARY KEY,
    started_at         TEXT NOT NULL,
    completed_at       TEXT,
    status             TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'PARTIAL_SUCCESS', 'FAILED')),
    cleaning_version   TEXT NOT NULL,
    dedup_version      TEXT NOT NULL,
    records_seen       INTEGER NOT NULL DEFAULT 0,
    records_valid      INTEGER NOT NULL DEFAULT 0,
    records_failed     INTEGER NOT NULL DEFAULT 0,
    candidate_pairs    INTEGER NOT NULL DEFAULT 0,
    fuzzy_comparisons  INTEGER NOT NULL DEFAULT 0,
    pairs_skipped      INTEGER NOT NULL DEFAULT 0,
    exact_duplicates   INTEGER NOT NULL DEFAULT 0,
    near_duplicates    INTEGER NOT NULL DEFAULT 0,
    pairs_inserted     INTEGER NOT NULL DEFAULT 0,
    groups_evaluated   INTEGER NOT NULL DEFAULT 0,
    groups_created     INTEGER NOT NULL DEFAULT 0,
    duration_ms        INTEGER,
    error_count        INTEGER NOT NULL DEFAULT 0,
    error_type         TEXT,
    error_message      TEXT,
    errors_json        TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS ix_dedup_run_started ON dedup_run_log (started_at DESC);

-- A group's hash names its membership snapshot. Later members create a new
-- snapshot; this link identifies the groups evaluated by a particular run.
CREATE TABLE IF NOT EXISTS dedup_run_groups (
    run_id           TEXT NOT NULL,
    cleaning_version TEXT NOT NULL,
    dedup_version    TEXT NOT NULL,
    group_id         TEXT NOT NULL,
    PRIMARY KEY (run_id, group_id),
    FOREIGN KEY (run_id) REFERENCES dedup_run_log (run_id),
    FOREIGN KEY (cleaning_version, dedup_version, group_id)
        REFERENCES duplicate_groups (cleaning_version, dedup_version, group_id)
);

-- Stage 8A: ownership is recorded only for processes holding our pipeline lock.
-- Legacy RUNNING rows without ownership are never guessed to be abandoned.
CREATE TABLE IF NOT EXISTS pipeline_run_owners (
    pipeline     TEXT NOT NULL,
    run_id       TEXT NOT NULL,
    owner_token  TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    since        TEXT,
    cohort_hash  TEXT,
    PRIMARY KEY (pipeline, run_id)
);

-- Stage 8 operational relevance only. Existing upstream rows remain immutable.
CREATE TABLE IF NOT EXISTS real_estate_relevance (
    article_id TEXT NOT NULL,
    raw_hash TEXT NOT NULL,
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL CHECK(length(dedup_version) BETWEEN 1 AND 64),
    relevance_version TEXT NOT NULL CHECK(length(relevance_version) BETWEEN 1 AND 64),
    context_id TEXT NOT NULL CHECK(length(context_id)=64),
    group_id TEXT,
    relevance_score INTEGER NOT NULL CHECK(relevance_score IN (0,1,2,3,4,5)),
    is_real_estate_relevant INTEGER NOT NULL CHECK(is_real_estate_relevant IN (0,1)),
    confidence TEXT NOT NULL CHECK(confidence IN ('HIGH','MEDIUM','LOW')),
    matched_positive_signals TEXT NOT NULL,
    matched_negative_signals TEXT NOT NULL,
    decision_reason TEXT NOT NULL CHECK(length(decision_reason) BETWEEN 1 AND 240),
    evaluated_at TEXT NOT NULL,
    PRIMARY KEY(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id),
    CHECK(is_real_estate_relevant = (relevance_score >= 3)),
    FOREIGN KEY(article_id,raw_hash,cleaning_version)
        REFERENCES cleaned_articles(article_id,raw_hash,cleaning_version),
    FOREIGN KEY(cleaning_version,dedup_version,group_id)
        REFERENCES duplicate_groups(cleaning_version,dedup_version,group_id)
);
CREATE TABLE IF NOT EXISTS relevance_run_log (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('RUNNING','SUCCESS','PARTIAL_SUCCESS','FAILED')),
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    since TEXT,
    records_seen INTEGER NOT NULL DEFAULT 0,
    canonical_records_seen INTEGER NOT NULL DEFAULT 0,
    relevant_count INTEGER NOT NULL DEFAULT 0,
    irrelevant_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    error_count INTEGER NOT NULL DEFAULT 0,
    error_type TEXT,
    error_message TEXT,
    errors_json TEXT NOT NULL DEFAULT '[]',
    dedup_run_id TEXT,
    FOREIGN KEY(dedup_run_id) REFERENCES dedup_run_log(run_id)
);
CREATE INDEX IF NOT EXISTS ix_relevance_run_started ON relevance_run_log(started_at DESC);
CREATE TABLE IF NOT EXISTS relevance_run_results (
    run_id TEXT NOT NULL,
    article_id TEXT NOT NULL,
    raw_hash TEXT NOT NULL,
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    context_id TEXT NOT NULL,
    PRIMARY KEY(run_id,article_id,raw_hash,context_id),
    FOREIGN KEY(run_id) REFERENCES relevance_run_log(run_id),
    FOREIGN KEY(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id)
        REFERENCES real_estate_relevance(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id)
);

-- Stage 9: separate UAE relevance linked to immutable Stage 8 contexts.
CREATE TABLE IF NOT EXISTS uae_real_estate_relevance (
    article_id TEXT NOT NULL,
    raw_hash TEXT NOT NULL,
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    context_id TEXT NOT NULL,
    group_id TEXT,
    uae_relevance_version TEXT NOT NULL CHECK(length(uae_relevance_version) BETWEEN 1 AND 64),
    registry_version TEXT NOT NULL CHECK(length(registry_version) BETWEEN 1 AND 64),
    uae_relevance_score INTEGER NOT NULL CHECK(uae_relevance_score IN (0,1,2,3,4,5)),
    is_uae_real_estate_relevant INTEGER NOT NULL CHECK(is_uae_real_estate_relevant IN (0,1)),
    confidence TEXT NOT NULL CHECK(confidence IN ('HIGH','MEDIUM','LOW')),
    source_context TEXT NOT NULL CHECK(source_context IN ('LOCAL_UAE','INTERNATIONAL')),
    acceptance_threshold INTEGER NOT NULL CHECK(acceptance_threshold IN (3,4)),
    matched_uae_signals TEXT NOT NULL,
    matched_exclusion_signals TEXT NOT NULL,
    decision_reason TEXT NOT NULL CHECK(length(decision_reason) BETWEEN 1 AND 240),
    evaluated_at TEXT NOT NULL,
    PRIMARY KEY(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id,uae_relevance_version,registry_version),
    CHECK(acceptance_threshold = CASE source_context WHEN 'LOCAL_UAE' THEN 3 ELSE 4 END),
    CHECK(is_uae_real_estate_relevant = (uae_relevance_score >= acceptance_threshold)),
    FOREIGN KEY(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id)
        REFERENCES real_estate_relevance(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id),
    FOREIGN KEY(cleaning_version,dedup_version,group_id)
        REFERENCES duplicate_groups(cleaning_version,dedup_version,group_id)
);
CREATE INDEX IF NOT EXISTS ix_uae_relevance_versions
    ON uae_real_estate_relevance(cleaning_version,dedup_version,relevance_version,uae_relevance_version,registry_version);
CREATE TABLE IF NOT EXISTS uae_relevance_run_log (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('RUNNING','SUCCESS','PARTIAL_SUCCESS','FAILED')),
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    uae_relevance_version TEXT NOT NULL,
    registry_version TEXT NOT NULL,
    stage8_run_id TEXT,
    since TEXT,
    records_seen INTEGER NOT NULL DEFAULT 0,
    eligible_stage8_records INTEGER NOT NULL DEFAULT 0,
    ineligible_count INTEGER NOT NULL DEFAULT 0,
    evaluated_count INTEGER NOT NULL DEFAULT 0,
    uae_relevant_count INTEGER NOT NULL DEFAULT 0,
    not_uae_relevant_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    error_count INTEGER NOT NULL DEFAULT 0,
    error_type TEXT,
    error_message TEXT,
    errors_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY(stage8_run_id) REFERENCES relevance_run_log(run_id)
);
CREATE INDEX IF NOT EXISTS ix_uae_relevance_run_started ON uae_relevance_run_log(started_at DESC);
CREATE TABLE IF NOT EXISTS uae_relevance_run_results (
    run_id TEXT NOT NULL,
    article_id TEXT NOT NULL,
    raw_hash TEXT NOT NULL,
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    context_id TEXT NOT NULL,
    uae_relevance_version TEXT NOT NULL,
    registry_version TEXT NOT NULL,
    PRIMARY KEY(run_id,article_id,raw_hash,context_id),
    FOREIGN KEY(run_id) REFERENCES uae_relevance_run_log(run_id),
    FOREIGN KEY(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id,uae_relevance_version,registry_version)
        REFERENCES uae_real_estate_relevance(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id,uae_relevance_version,registry_version)
);

-- Stage 10: structured mentions only; upstream decisions remain immutable.
CREATE TABLE IF NOT EXISTS entity_extraction_results (
    extraction_id TEXT PRIMARY KEY CHECK(length(extraction_id)=64),
    article_id TEXT NOT NULL,
    raw_hash TEXT NOT NULL,
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    context_id TEXT NOT NULL,
    group_id TEXT,
    uae_relevance_version TEXT NOT NULL,
    registry_version TEXT NOT NULL,
    entity_extraction_version TEXT NOT NULL CHECK(length(entity_extraction_version) BETWEEN 1 AND 64),
    entity_registry_version TEXT NOT NULL CHECK(length(entity_registry_version) BETWEEN 1 AND 64),
    location_scope TEXT NOT NULL CHECK(location_scope IN ('DUBAI','ABU_DHABI','SHARJAH','AJMAN','RAS_AL_KHAIMAH','FUJAIRAH','UMM_AL_QUWAIN','UAE_WIDE','MULTI_EMIRATE','UNKNOWN')),
    mention_count INTEGER NOT NULL CHECK(mention_count BETWEEN 0 AND 256),
    evaluated_at TEXT NOT NULL,
    UNIQUE(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id,uae_relevance_version,registry_version,entity_extraction_version,entity_registry_version),
    FOREIGN KEY(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id,uae_relevance_version,registry_version)
        REFERENCES uae_real_estate_relevance(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id,uae_relevance_version,registry_version),
    FOREIGN KEY(cleaning_version,dedup_version,group_id)
        REFERENCES duplicate_groups(cleaning_version,dedup_version,group_id)
);
CREATE INDEX IF NOT EXISTS ix_entity_extraction_versions
    ON entity_extraction_results(cleaning_version,dedup_version,relevance_version,uae_relevance_version,registry_version,entity_extraction_version,entity_registry_version);
CREATE TABLE IF NOT EXISTS entity_mentions (
    extraction_id TEXT NOT NULL,
    mention_index INTEGER NOT NULL CHECK(mention_index BETWEEN 0 AND 255),
    entity_id TEXT NOT NULL,
    canonical_name TEXT NOT NULL CHECK(length(canonical_name) BETWEEN 1 AND 160),
    entity_type TEXT NOT NULL CHECK(entity_type IN ('COUNTRY','EMIRATE','CITY','AREA','COMMUNITY','PROJECT','BUILDING','DEVELOPER')),
    parent_entity_id TEXT,
    matched_text TEXT NOT NULL CHECK(length(matched_text) BETWEEN 1 AND 160),
    normalized_alias TEXT NOT NULL CHECK(length(normalized_alias) BETWEEN 1 AND 160),
    source_field TEXT NOT NULL CHECK(source_field IN ('TITLE','BODY')),
    start_offset INTEGER NOT NULL CHECK(typeof(start_offset)='integer' AND start_offset>=0),
    end_offset INTEGER NOT NULL CHECK(typeof(end_offset)='integer' AND end_offset>start_offset),
    confidence TEXT NOT NULL CHECK(confidence IN ('HIGH','MEDIUM')),
    extraction_method TEXT NOT NULL CHECK(extraction_method IN ('EXACT_ALIAS','CONTEXT_ABBREVIATION')),
    PRIMARY KEY(extraction_id,mention_index),
    CHECK(end_offset-start_offset=length(matched_text)),
    FOREIGN KEY(extraction_id) REFERENCES entity_extraction_results(extraction_id)
);
CREATE INDEX IF NOT EXISTS ix_entity_mentions_identity ON entity_mentions(entity_id,entity_type,extraction_id);
CREATE INDEX IF NOT EXISTS ix_entity_mentions_parent ON entity_mentions(parent_entity_id,entity_type);
CREATE TABLE IF NOT EXISTS entity_extraction_run_log (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('RUNNING','SUCCESS','PARTIAL_SUCCESS','FAILED')),
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    uae_relevance_version TEXT NOT NULL,
    registry_version TEXT NOT NULL,
    entity_extraction_version TEXT NOT NULL,
    entity_registry_version TEXT NOT NULL,
    stage9_run_id TEXT,
    since TEXT,
    records_seen INTEGER NOT NULL DEFAULT 0,
    eligible_stage9_records INTEGER NOT NULL DEFAULT 0,
    ineligible_count INTEGER NOT NULL DEFAULT 0,
    evaluated_count INTEGER NOT NULL DEFAULT 0,
    records_with_entities INTEGER NOT NULL DEFAULT 0,
    records_without_entities INTEGER NOT NULL DEFAULT 0,
    mention_count INTEGER NOT NULL DEFAULT 0,
    country_mentions INTEGER NOT NULL DEFAULT 0,
    emirate_mentions INTEGER NOT NULL DEFAULT 0,
    city_mentions INTEGER NOT NULL DEFAULT 0,
    area_mentions INTEGER NOT NULL DEFAULT 0,
    community_mentions INTEGER NOT NULL DEFAULT 0,
    project_mentions INTEGER NOT NULL DEFAULT 0,
    building_mentions INTEGER NOT NULL DEFAULT 0,
    developer_mentions INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    error_count INTEGER NOT NULL DEFAULT 0,
    error_type TEXT,
    error_message TEXT,
    errors_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY(stage9_run_id) REFERENCES uae_relevance_run_log(run_id)
);
CREATE INDEX IF NOT EXISTS ix_entity_extraction_run_started ON entity_extraction_run_log(started_at DESC);
CREATE TABLE IF NOT EXISTS entity_extraction_run_results (
    run_id TEXT NOT NULL,
    extraction_id TEXT NOT NULL,
    PRIMARY KEY(run_id,extraction_id),
    FOREIGN KEY(run_id) REFERENCES entity_extraction_run_log(run_id),
    FOREIGN KEY(extraction_id) REFERENCES entity_extraction_results(extraction_id)
);

-- Stage 11: evidence-backed events only; no numeric market observations.
CREATE TABLE IF NOT EXISTS event_extraction_results (
    event_result_id TEXT PRIMARY KEY CHECK(length(event_result_id)=64),
    extraction_id TEXT NOT NULL,
    article_id TEXT NOT NULL,
    raw_hash TEXT NOT NULL,
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    context_id TEXT NOT NULL,
    uae_relevance_version TEXT NOT NULL,
    registry_version TEXT NOT NULL,
    entity_extraction_version TEXT NOT NULL,
    entity_registry_version TEXT NOT NULL,
    group_id TEXT,
    event_extraction_version TEXT NOT NULL CHECK(length(event_extraction_version) BETWEEN 1 AND 64),
    location_scope TEXT NOT NULL CHECK(location_scope IN ('DUBAI','ABU_DHABI','SHARJAH','AJMAN','RAS_AL_KHAIMAH','FUJAIRAH','UMM_AL_QUWAIN','UAE_WIDE','MULTI_EMIRATE','UNKNOWN')),
    event_count INTEGER NOT NULL CHECK(event_count BETWEEN 0 AND 128),
    evaluated_at TEXT NOT NULL,
    UNIQUE(extraction_id,event_extraction_version),
    UNIQUE(event_result_id,extraction_id),
    FOREIGN KEY(extraction_id) REFERENCES entity_extraction_results(extraction_id),
    FOREIGN KEY(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id,uae_relevance_version,registry_version,entity_extraction_version,entity_registry_version) REFERENCES entity_extraction_results(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id,uae_relevance_version,registry_version,entity_extraction_version,entity_registry_version)
);
CREATE INDEX IF NOT EXISTS ix_event_extraction_versions ON event_extraction_results(event_extraction_version,entity_extraction_version,entity_registry_version);
CREATE TABLE IF NOT EXISTS real_estate_event_instances (
    event_id TEXT PRIMARY KEY CHECK(length(event_id)=64),
    event_result_id TEXT NOT NULL,
    extraction_id TEXT NOT NULL,
    event_index INTEGER NOT NULL CHECK(event_index BETWEEN 0 AND 127),
    event_type TEXT NOT NULL CHECK(event_type IN ('PRICE_CHANGE','RENT_CHANGE','TRANSACTION_VALUE','TRANSACTION_VOLUME','SALES_ACTIVITY','MORTGAGE_ACTIVITY','OFF_PLAN_ACTIVITY','READY_PROPERTY_ACTIVITY','NEW_PROJECT','PROJECT_LAUNCH','PROJECT_COMPLETION','NEW_SUPPLY','SUPPLY_PIPELINE','DEVELOPER_ACTIVITY','INVESTOR_ACTIVITY','FOREIGN_INVESTMENT','REGULATION','INFRASTRUCTURE','DEMAND_CHANGE','MARKET_SENTIMENT','MARKET_OUTLOOK','RENTAL_ACTIVITY')),
    rule_id TEXT NOT NULL,
    source_field TEXT NOT NULL CHECK(source_field IN ('TITLE','BODY')),
    matched_text TEXT NOT NULL CHECK(length(matched_text) BETWEEN 1 AND 640),
    start_offset INTEGER NOT NULL CHECK(typeof(start_offset)='integer' AND start_offset>=0),
    end_offset INTEGER NOT NULL CHECK(typeof(end_offset)='integer' AND end_offset>start_offset),
    confidence TEXT NOT NULL CHECK(confidence IN ('HIGH','MEDIUM')),
    direction TEXT NOT NULL CHECK(direction IN ('INCREASE','DECREASE','STABLE','UNKNOWN')),
    CHECK(end_offset-start_offset=length(matched_text)),
    UNIQUE(event_result_id,event_index),
    UNIQUE(event_id,extraction_id),
    FOREIGN KEY(event_result_id,extraction_id) REFERENCES event_extraction_results(event_result_id,extraction_id)
);
CREATE INDEX IF NOT EXISTS ix_event_type_direction ON real_estate_event_instances(event_type,direction,event_result_id);
CREATE TABLE IF NOT EXISTS event_entity_links (
    event_id TEXT NOT NULL,
    extraction_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    mention_index INTEGER NOT NULL,
    relationship TEXT NOT NULL CHECK(relationship='CLAUSE_CONTEXT'),
    PRIMARY KEY(event_id,entity_id),
    FOREIGN KEY(event_id,extraction_id) REFERENCES real_estate_event_instances(event_id,extraction_id),
    FOREIGN KEY(extraction_id,mention_index) REFERENCES entity_mentions(extraction_id,mention_index)
);
CREATE INDEX IF NOT EXISTS ix_event_entity_identity ON event_entity_links(entity_id,event_id);
CREATE TABLE IF NOT EXISTS event_run_log (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('RUNNING','SUCCESS','PARTIAL_SUCCESS','FAILED')),
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    uae_relevance_version TEXT NOT NULL,
    registry_version TEXT NOT NULL,
    entity_extraction_version TEXT NOT NULL,
    entity_registry_version TEXT NOT NULL,
    event_extraction_version TEXT NOT NULL,
    stage10_run_id TEXT,
    since TEXT,
    records_seen INTEGER NOT NULL DEFAULT 0,
    eligible_stage10_records INTEGER NOT NULL DEFAULT 0,
    evaluated_count INTEGER NOT NULL DEFAULT 0,
    records_with_events INTEGER NOT NULL DEFAULT 0,
    records_without_events INTEGER NOT NULL DEFAULT 0,
    event_count INTEGER NOT NULL DEFAULT 0,
    event_type_counts_json TEXT NOT NULL DEFAULT '{}',
    failed_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    error_count INTEGER NOT NULL DEFAULT 0,
    error_type TEXT,
    error_message TEXT,
    errors_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY(stage10_run_id) REFERENCES entity_extraction_run_log(run_id)
);
CREATE INDEX IF NOT EXISTS ix_event_run_started ON event_run_log(started_at DESC);
CREATE TABLE IF NOT EXISTS event_run_results (
    run_id TEXT NOT NULL,
    event_result_id TEXT NOT NULL,
    PRIMARY KEY(run_id,event_result_id),
    FOREIGN KEY(run_id) REFERENCES event_run_log(run_id),
    FOREIGN KEY(event_result_id) REFERENCES event_extraction_results(event_result_id)
);

-- Stage 12: exact numeric observations; no aggregation or market ranking.
CREATE TABLE IF NOT EXISTS metric_extraction_results (
    metric_result_id TEXT PRIMARY KEY CHECK(length(metric_result_id)=64),
    event_result_id TEXT NOT NULL,
    metric_extraction_version TEXT NOT NULL CHECK(length(metric_extraction_version) BETWEEN 1 AND 64),
    source_id TEXT NOT NULL,
    extraction_id TEXT NOT NULL,
    article_id TEXT NOT NULL,
    raw_hash TEXT NOT NULL,
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    context_id TEXT NOT NULL,
    uae_relevance_version TEXT NOT NULL,
    registry_version TEXT NOT NULL,
    entity_extraction_version TEXT NOT NULL,
    entity_registry_version TEXT NOT NULL,
    group_id TEXT,
    event_extraction_version TEXT NOT NULL CHECK(length(event_extraction_version) BETWEEN 1 AND 64),
    location_scope TEXT NOT NULL CHECK(location_scope IN ('DUBAI','ABU_DHABI','SHARJAH','AJMAN','RAS_AL_KHAIMAH','FUJAIRAH','UMM_AL_QUWAIN','UAE_WIDE','MULTI_EMIRATE','UNKNOWN')),
    observation_count INTEGER NOT NULL CHECK(observation_count BETWEEN 0 AND 256),
    evaluated_at TEXT NOT NULL,
    UNIQUE(event_result_id,metric_extraction_version),
    UNIQUE(metric_result_id,extraction_id),
    UNIQUE(metric_result_id,event_result_id),
    FOREIGN KEY(event_result_id,extraction_id) REFERENCES event_extraction_results(event_result_id,extraction_id),
    FOREIGN KEY(extraction_id) REFERENCES entity_extraction_results(extraction_id),
    FOREIGN KEY(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id,uae_relevance_version,registry_version,entity_extraction_version,entity_registry_version) REFERENCES entity_extraction_results(article_id,raw_hash,cleaning_version,dedup_version,relevance_version,context_id,uae_relevance_version,registry_version,entity_extraction_version,entity_registry_version)
);
CREATE INDEX IF NOT EXISTS ix_metric_version ON metric_extraction_results(metric_extraction_version,event_extraction_version);
CREATE TABLE IF NOT EXISTS market_observations (
    observation_id TEXT PRIMARY KEY CHECK(length(observation_id)=64),
    metric_result_id TEXT NOT NULL,
    extraction_id TEXT NOT NULL,
    event_result_id TEXT NOT NULL,
    observation_index INTEGER NOT NULL CHECK(observation_index BETWEEN 0 AND 255),
    metric TEXT NOT NULL CHECK(metric IN ('SALE_PRICE','AVERAGE_SALE_PRICE','MEDIAN_SALE_PRICE','SALE_PRICE_PER_SQFT','SALE_PRICE_PER_SQM','RENTAL_PRICE','ANNUAL_RENT','MONTHLY_RENT','RENTAL_YIELD','PRICE_CHANGE_PCT','RENT_CHANGE_PCT','TRANSACTION_VALUE','TRANSACTION_VOLUME')),
    value TEXT NOT NULL CHECK(typeof(value)='text'),
    reported_value TEXT NOT NULL CHECK(typeof(reported_value)='text'),
    reported_value_text TEXT NOT NULL,
    scale TEXT NOT NULL CHECK(scale IN ('ONE','THOUSAND','MILLION','BILLION')),
    currency TEXT CHECK(currency IN ('AED','USD','EUR','GBP')),
    unit TEXT NOT NULL CHECK(unit IN ('CURRENCY_AMOUNT','CURRENCY_PER_SQFT','CURRENCY_PER_SQM','PERCENT','TRANSACTIONS')),
    period_basis TEXT NOT NULL CHECK(period_basis IN ('MOM','QOQ','YOY','MONTHLY','QUARTERLY','ANNUAL','CURRENT','UNKNOWN')),
    reported_period_text TEXT,
    property_type TEXT NOT NULL CHECK(property_type IN ('APARTMENT','VILLA','TOWNHOUSE','LAND','COMMERCIAL','OFFICE','RETAIL','WAREHOUSE','RESIDENTIAL','COMMERCIAL_PROPERTY','UNKNOWN')),
    nature TEXT NOT NULL CHECK(nature IN ('OBSERVED','SOURCE_REPORTED_FORECAST')),
    qualifier TEXT NOT NULL CHECK(qualifier IN ('EXACT','APPROXIMATE','GREATER_THAN','LESS_THAN')),
    statistic TEXT NOT NULL CHECK(statistic IN ('UNSPECIFIED','AVERAGE','MEDIAN')),
    direction TEXT NOT NULL CHECK(direction IN ('INCREASE','DECREASE','STABLE','UNKNOWN')),
    rule_id TEXT NOT NULL,
    source_field TEXT NOT NULL CHECK(source_field IN ('TITLE','BODY')),
    start_offset INTEGER NOT NULL CHECK(start_offset>=0),
    end_offset INTEGER NOT NULL,
    numeric_start INTEGER NOT NULL,
    numeric_end INTEGER NOT NULL,
    matched_text TEXT NOT NULL CHECK(length(matched_text) BETWEEN 1 AND 640),
    confidence TEXT NOT NULL CHECK(confidence IN ('HIGH','MEDIUM')),
    CHECK(end_offset-start_offset=length(matched_text)),
    CHECK(start_offset<=numeric_start AND numeric_start<numeric_end AND numeric_end<=end_offset),
    CHECK(numeric_end-numeric_start=length(reported_value_text)),
    UNIQUE(metric_result_id,observation_index),
    UNIQUE(observation_id,extraction_id),
    UNIQUE(observation_id,event_result_id),
    FOREIGN KEY(metric_result_id,extraction_id) REFERENCES metric_extraction_results(metric_result_id,extraction_id),
    FOREIGN KEY(metric_result_id,event_result_id) REFERENCES metric_extraction_results(metric_result_id,event_result_id)
);
CREATE INDEX IF NOT EXISTS ix_observation_dimensions ON market_observations(metric,nature,currency,unit,period_basis,property_type);
CREATE TABLE IF NOT EXISTS observation_entity_links (
    observation_id TEXT NOT NULL,
    extraction_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    mention_index INTEGER NOT NULL,
    relationship TEXT NOT NULL CHECK(relationship='CLAUSE_CONTEXT'),
    PRIMARY KEY(observation_id,entity_id),
    FOREIGN KEY(observation_id,extraction_id) REFERENCES market_observations(observation_id,extraction_id),
    FOREIGN KEY(extraction_id,mention_index) REFERENCES entity_mentions(extraction_id,mention_index)
);
CREATE INDEX IF NOT EXISTS ix_observation_entity ON observation_entity_links(entity_id,observation_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_event_context ON real_estate_event_instances(event_id,event_result_id);
CREATE TABLE IF NOT EXISTS observation_event_links (
    observation_id TEXT NOT NULL,
    event_result_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    PRIMARY KEY(observation_id,event_id),
    FOREIGN KEY(observation_id,event_result_id) REFERENCES market_observations(observation_id,event_result_id),
    FOREIGN KEY(event_id,event_result_id) REFERENCES real_estate_event_instances(event_id,event_result_id)
);
CREATE TABLE IF NOT EXISTS metric_run_log (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('RUNNING','SUCCESS','PARTIAL_SUCCESS','FAILED')),
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    uae_relevance_version TEXT NOT NULL,
    registry_version TEXT NOT NULL,
    entity_extraction_version TEXT NOT NULL,
    entity_registry_version TEXT NOT NULL,
    event_extraction_version TEXT NOT NULL,
    metric_extraction_version TEXT NOT NULL,
    stage11_run_id TEXT,
    since TEXT,
    records_seen INTEGER NOT NULL DEFAULT 0,
    eligible_stage11_records INTEGER NOT NULL DEFAULT 0,
    evaluated_count INTEGER NOT NULL DEFAULT 0,
    records_with_observations INTEGER NOT NULL DEFAULT 0,
    records_without_observations INTEGER NOT NULL DEFAULT 0,
    observation_count INTEGER NOT NULL DEFAULT 0,
    metric_type_counts_json TEXT NOT NULL DEFAULT '{}',
    failed_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    error_count INTEGER NOT NULL DEFAULT 0,
    error_type TEXT,
    error_message TEXT,
    errors_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY(stage11_run_id) REFERENCES event_run_log(run_id)
);
CREATE INDEX IF NOT EXISTS ix_metric_run_started ON metric_run_log(started_at DESC);
CREATE TABLE IF NOT EXISTS metric_run_results (
    run_id TEXT NOT NULL,
    metric_result_id TEXT NOT NULL,
    PRIMARY KEY(run_id,metric_result_id),
    FOREIGN KEY(run_id) REFERENCES metric_run_log(run_id),
    FOREIGN KEY(metric_result_id) REFERENCES metric_extraction_results(metric_result_id)
);

-- Stage 13: additive, build-scoped serving projections. Numeric source facts
-- remain in Stage 12; views expose them without duplicating numeric evidence.
CREATE TABLE IF NOT EXISTS intelligence_builds (
    build_id TEXT PRIMARY KEY CHECK(length(build_id)=64),
    cohort_hash TEXT NOT NULL,
    stage12_run_id TEXT REFERENCES metric_run_log(run_id),
    intelligence_build_version TEXT NOT NULL,
    market_movement_version TEXT NOT NULL,
    ranking_version TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    policy_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    counts_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS intelligence_current (
    channel TEXT PRIMARY KEY CHECK(channel='CURRENT'),
    build_id TEXT NOT NULL REFERENCES intelligence_builds(build_id)
);
CREATE TABLE IF NOT EXISTS intelligence_articles (
    build_id TEXT NOT NULL REFERENCES intelligence_builds(build_id),
    metric_result_id TEXT NOT NULL REFERENCES metric_extraction_results(metric_result_id),
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    rss_url TEXT NOT NULL,
    article_url TEXT,
    published_at TEXT,
    retrieved_at TEXT NOT NULL,
    location_scope TEXT NOT NULL CHECK(location_scope IN ('DUBAI','ABU_DHABI','SHARJAH','AJMAN','UMM_AL_QUWAIN','RAS_AL_KHAIMAH','FUJAIRAH','UAE_WIDE','MULTI_EMIRATE','UNKNOWN')),
    stage8_accepted INTEGER NOT NULL CHECK(stage8_accepted=1),
    stage9_accepted INTEGER NOT NULL CHECK(stage9_accepted=1),
    PRIMARY KEY(build_id,metric_result_id)
);
CREATE INDEX IF NOT EXISTS ix_intelligence_news ON intelligence_articles(build_id,published_at DESC);
CREATE INDEX IF NOT EXISTS ix_intelligence_source ON intelligence_articles(build_id,source_id,published_at DESC);
CREATE INDEX IF NOT EXISTS ix_intelligence_scope ON intelligence_articles(build_id,location_scope,published_at DESC);
-- Direct SQL insertion is also gated against the upstream accepted decisions.
CREATE TRIGGER IF NOT EXISTS intelligence_uae_gate BEFORE INSERT ON intelligence_articles
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM metric_extraction_results m
        JOIN real_estate_relevance r ON r.article_id=m.article_id AND r.raw_hash=m.raw_hash
          AND r.cleaning_version=m.cleaning_version AND r.dedup_version=m.dedup_version
          AND r.relevance_version=m.relevance_version AND r.context_id=m.context_id
        JOIN uae_real_estate_relevance u ON u.article_id=m.article_id AND u.raw_hash=m.raw_hash
          AND u.cleaning_version=m.cleaning_version AND u.dedup_version=m.dedup_version
          AND u.relevance_version=m.relevance_version AND u.context_id=m.context_id
          AND u.uae_relevance_version=m.uae_relevance_version AND u.registry_version=m.registry_version
        WHERE m.metric_result_id=NEW.metric_result_id AND r.is_real_estate_relevant=1 AND u.is_uae_real_estate_relevant=1
    ) THEN RAISE(ABORT,'Stage 13 requires accepted Stage 8 and Stage 9 lineage') END;
END;
CREATE TABLE IF NOT EXISTS intelligence_article_entities (
    build_id TEXT NOT NULL,
    metric_result_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    extraction_id TEXT NOT NULL,
    mention_index INTEGER NOT NULL,
    PRIMARY KEY(build_id,metric_result_id,entity_id),
    FOREIGN KEY(build_id,metric_result_id) REFERENCES intelligence_articles(build_id,metric_result_id),
    FOREIGN KEY(extraction_id,mention_index) REFERENCES entity_mentions(extraction_id,mention_index)
);
CREATE INDEX IF NOT EXISTS ix_intelligence_entity ON intelligence_article_entities(build_id,entity_id,metric_result_id);
CREATE TABLE IF NOT EXISTS intelligence_events (
    build_id TEXT NOT NULL,
    event_id TEXT NOT NULL REFERENCES real_estate_event_instances(event_id),
    metric_result_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    PRIMARY KEY(build_id,event_id),
    FOREIGN KEY(build_id,metric_result_id) REFERENCES intelligence_articles(build_id,metric_result_id)
);
CREATE INDEX IF NOT EXISTS ix_intelligence_event ON intelligence_events(build_id,event_type,metric_result_id);
CREATE TABLE IF NOT EXISTS intelligence_event_entities (
    build_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    PRIMARY KEY(build_id,event_id,entity_id),
    FOREIGN KEY(build_id,event_id) REFERENCES intelligence_events(build_id,event_id),
    FOREIGN KEY(event_id,entity_id) REFERENCES event_entity_links(event_id,entity_id)
);
CREATE INDEX IF NOT EXISTS ix_intelligence_event_entity ON intelligence_event_entities(build_id,entity_id,event_id);
CREATE TABLE IF NOT EXISTS market_series (
    build_id TEXT NOT NULL REFERENCES intelligence_builds(build_id),
    series_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    scope TEXT NOT NULL,
    source_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    property_type TEXT NOT NULL,
    statistic TEXT NOT NULL,
    currency TEXT NOT NULL,
    unit TEXT NOT NULL,
    nature TEXT NOT NULL CHECK(nature='OBSERVED'),
    frequency TEXT NOT NULL CHECK(frequency IN ('MONTHLY','QUARTERLY','ANNUAL')),
    PRIMARY KEY(build_id,series_id)
);
CREATE INDEX IF NOT EXISTS ix_series_dimensions ON market_series(build_id,metric,entity_id,property_type,source_id,frequency);
CREATE TABLE IF NOT EXISTS intelligence_observations (
    build_id TEXT NOT NULL,
    observation_id TEXT NOT NULL REFERENCES market_observations(observation_id),
    metric_result_id TEXT NOT NULL,
    family TEXT NOT NULL CHECK(family IN ('PRICE','RENT','TRANSACTION')),
    metric TEXT NOT NULL,
    property_type TEXT NOT NULL,
    nature TEXT NOT NULL CHECK(nature IN ('OBSERVED','SOURCE_REPORTED_FORECAST')),
    provenance TEXT NOT NULL CHECK(provenance='SOURCE_REPORTED'),
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    scope TEXT NOT NULL,
    period TEXT,
    frequency TEXT,
    period_ordinal INTEGER,
    series_id TEXT,
    exclusion_reason TEXT,
    PRIMARY KEY(build_id,observation_id),
    FOREIGN KEY(build_id,metric_result_id) REFERENCES intelligence_articles(build_id,metric_result_id),
    FOREIGN KEY(build_id,series_id) REFERENCES market_series(build_id,series_id),
    CHECK((series_id IS NULL AND exclusion_reason IS NOT NULL) OR (series_id IS NOT NULL AND exclusion_reason IS NULL))
);
CREATE INDEX IF NOT EXISTS ix_serving_observation ON intelligence_observations(build_id,metric,property_type,period);
CREATE INDEX IF NOT EXISTS ix_serving_series_period ON intelligence_observations(build_id,series_id,period_ordinal);
CREATE INDEX IF NOT EXISTS ix_serving_observation_scope ON intelligence_observations(build_id,scope,entity_id,nature);
CREATE TABLE IF NOT EXISTS market_movements (
    build_id TEXT NOT NULL,
    movement_id TEXT NOT NULL,
    series_id TEXT NOT NULL,
    current_observation_id TEXT NOT NULL,
    comparison_observation_id TEXT NOT NULL,
    basis TEXT NOT NULL CHECK(basis IN ('MOM','QOQ','YOY')),
    period TEXT NOT NULL,
    change_pct TEXT NOT NULL CHECK(typeof(change_pct)='text'),
    classification TEXT NOT NULL CHECK(classification IN ('STRONG_INCREASE','INCREASE','STABLE','DECREASE','STRONG_DECREASE')),
    provenance TEXT NOT NULL CHECK(provenance='SYSTEM_CALCULATED'),
    market_movement_version TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    PRIMARY KEY(build_id,movement_id),
    UNIQUE(build_id,series_id,current_observation_id,basis),
    FOREIGN KEY(build_id,series_id) REFERENCES market_series(build_id,series_id),
    FOREIGN KEY(build_id,current_observation_id) REFERENCES intelligence_observations(build_id,observation_id),
    FOREIGN KEY(build_id,comparison_observation_id) REFERENCES intelligence_observations(build_id,observation_id)
);
CREATE INDEX IF NOT EXISTS ix_movement_filter ON market_movements(build_id,basis,classification,period);
CREATE TABLE IF NOT EXISTS market_movement_unavailable (
    build_id TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    basis TEXT NOT NULL,
    reason TEXT NOT NULL CHECK(reason IN ('MISSING_COMPARISON_PERIOD','ZERO_DENOMINATOR','SOURCE_CONFLICT')),
    PRIMARY KEY(build_id,observation_id,basis),
    FOREIGN KEY(build_id,observation_id) REFERENCES intelligence_observations(build_id,observation_id)
);
CREATE TABLE IF NOT EXISTS market_rankings (
    build_id TEXT NOT NULL REFERENCES intelligence_builds(build_id),
    ranking_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    scope TEXT NOT NULL,
    source_id TEXT NOT NULL,
    property_type TEXT NOT NULL,
    statistic TEXT NOT NULL,
    currency TEXT NOT NULL,
    unit TEXT NOT NULL,
    nature TEXT NOT NULL,
    frequency TEXT NOT NULL,
    basis TEXT NOT NULL,
    period TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('INCREASE','DECREASE')),
    ranking_version TEXT NOT NULL,
    movement_version TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    PRIMARY KEY(build_id,ranking_id)
);
CREATE INDEX IF NOT EXISTS ix_ranking_filter ON market_rankings(build_id,metric,scope,entity_type,basis,period,direction);
CREATE TABLE IF NOT EXISTS market_ranking_entries (
    build_id TEXT NOT NULL,
    ranking_id TEXT NOT NULL,
    position INTEGER NOT NULL CHECK(position>0),
    rank_number INTEGER NOT NULL CHECK(rank_number>0 AND rank_number<=position),
    movement_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    PRIMARY KEY(build_id,ranking_id,position),
    UNIQUE(build_id,ranking_id,entity_id),
    FOREIGN KEY(build_id,ranking_id) REFERENCES market_rankings(build_id,ranking_id),
    FOREIGN KEY(build_id,movement_id) REFERENCES market_movements(build_id,movement_id)
);
CREATE TABLE IF NOT EXISTS intelligence_run_log (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('RUNNING','SUCCESS','FAILED')),
    stage12_run_id TEXT REFERENCES metric_run_log(run_id),
    build_id TEXT REFERENCES intelligence_builds(build_id),
    cohort_hash TEXT,
    cleaning_version TEXT NOT NULL,
    dedup_version TEXT NOT NULL,
    relevance_version TEXT NOT NULL,
    uae_relevance_version TEXT NOT NULL,
    registry_version TEXT NOT NULL,
    entity_extraction_version TEXT NOT NULL,
    entity_registry_version TEXT NOT NULL,
    event_extraction_version TEXT NOT NULL,
    metric_extraction_version TEXT NOT NULL,
    intelligence_build_version TEXT NOT NULL,
    market_movement_version TEXT NOT NULL,
    ranking_version TEXT NOT NULL,
    counts_json TEXT NOT NULL DEFAULT '{}',
    reused_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    error_count INTEGER NOT NULL DEFAULT 0,
    error_type TEXT,
    error_message TEXT,
    errors_json TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS ix_intelligence_run_started ON intelligence_run_log(started_at DESC);
CREATE TABLE IF NOT EXISTS intelligence_run_results (
    run_id TEXT PRIMARY KEY REFERENCES intelligence_run_log(run_id),
    build_id TEXT NOT NULL REFERENCES intelligence_builds(build_id)
);
CREATE VIEW IF NOT EXISTS intelligence_news AS
    SELECT a.*,m.article_id,m.raw_hash,m.cleaning_version,m.extraction_id,m.event_result_id,
           c.clean_title,c.clean_body
    FROM intelligence_articles a JOIN intelligence_current p USING(build_id)
    JOIN metric_extraction_results m USING(metric_result_id)
    JOIN cleaned_articles c ON c.article_id=m.article_id AND c.raw_hash=m.raw_hash AND c.cleaning_version=m.cleaning_version;
CREATE VIEW IF NOT EXISTS intelligence_facts AS
    SELECT i.*,o.value,o.reported_value,o.reported_value_text,o.reported_period_text,o.period_basis,
           o.currency,o.unit,o.statistic,o.qualifier,o.direction,o.source_field,o.start_offset,o.end_offset,
           o.matched_text,o.confidence,a.source_id,a.source_name,a.rss_url,a.article_url,a.published_at,a.retrieved_at
    FROM intelligence_observations i JOIN intelligence_current p USING(build_id)
    JOIN market_observations o USING(observation_id)
    JOIN intelligence_articles a ON a.build_id=i.build_id AND a.metric_result_id=i.metric_result_id;
CREATE VIEW IF NOT EXISTS intelligence_price_observations AS SELECT * FROM intelligence_facts WHERE family='PRICE';
CREATE VIEW IF NOT EXISTS intelligence_rent_observations AS SELECT * FROM intelligence_facts WHERE family='RENT';
CREATE VIEW IF NOT EXISTS intelligence_transaction_observations AS SELECT * FROM intelligence_facts WHERE family='TRANSACTION';
CREATE TRIGGER IF NOT EXISTS intelligence_event_parent BEFORE INSERT ON intelligence_events
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM real_estate_event_instances e JOIN metric_extraction_results m USING(event_result_id)
        WHERE e.event_id=NEW.event_id AND m.metric_result_id=NEW.metric_result_id
    ) THEN RAISE(ABORT,'Event must belong to accepted serving article') END;
END;
CREATE TRIGGER IF NOT EXISTS intelligence_observation_parent BEFORE INSERT ON intelligence_observations
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM market_observations o WHERE o.observation_id=NEW.observation_id AND o.metric_result_id=NEW.metric_result_id
    ) THEN RAISE(ABORT,'Observation must belong to accepted serving article') END;
END;

CREATE TRIGGER IF NOT EXISTS intelligence_article_entity_parent BEFORE INSERT ON intelligence_article_entities
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM metric_extraction_results m JOIN entity_mentions e USING(extraction_id)
        WHERE m.metric_result_id=NEW.metric_result_id AND m.extraction_id=NEW.extraction_id
          AND e.mention_index=NEW.mention_index AND e.entity_id=NEW.entity_id
    ) THEN RAISE(ABORT,'Entity must belong to accepted serving article') END;
END;

CREATE TRIGGER IF NOT EXISTS immutable_intelligence_builds BEFORE UPDATE ON intelligence_builds
BEGIN
    SELECT RAISE(ABORT,'Stage 13 serving builds are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_intelligence_articles BEFORE UPDATE ON intelligence_articles
BEGIN
    SELECT RAISE(ABORT,'Stage 13 serving builds are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_intelligence_article_entities BEFORE UPDATE ON intelligence_article_entities
BEGIN
    SELECT RAISE(ABORT,'Stage 13 serving builds are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_intelligence_events BEFORE UPDATE ON intelligence_events
BEGIN
    SELECT RAISE(ABORT,'Stage 13 serving builds are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_intelligence_event_entities BEFORE UPDATE ON intelligence_event_entities
BEGIN
    SELECT RAISE(ABORT,'Stage 13 serving builds are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_intelligence_observations BEFORE UPDATE ON intelligence_observations
BEGIN
    SELECT RAISE(ABORT,'Stage 13 serving builds are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_market_series BEFORE UPDATE ON market_series
BEGIN
    SELECT RAISE(ABORT,'Stage 13 serving builds are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_market_movements BEFORE UPDATE ON market_movements
BEGIN
    SELECT RAISE(ABORT,'Stage 13 serving builds are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_market_movement_unavailable BEFORE UPDATE ON market_movement_unavailable
BEGIN
    SELECT RAISE(ABORT,'Stage 13 serving builds are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_market_rankings BEFORE UPDATE ON market_rankings
BEGIN
    SELECT RAISE(ABORT,'Stage 13 serving builds are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_market_ranking_entries BEFORE UPDATE ON market_ranking_entries
BEGIN
    SELECT RAISE(ABORT,'Stage 13 serving builds are immutable');
END;
