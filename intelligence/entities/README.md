# Stage 10: geographic and real-estate entities

Stage 10 consumes persisted, accepted Stage 9 contexts, validates their Stage 8
acceptance and canonical cleaned evidence, and produces versioned entity results
and relational mentions. It never changes raw evidence, cleaned articles,
duplicate groups, or either relevance decision. Event extraction is deferred to
Stage 11. No network, new dependency, model service, embedding, dashboard import,
or runtime loading of application datasets is used.

## Versions and execution

- Schema: `v0.6` (20 operational tables; four added for Stage 10).
- Extractor: `stage10-v1`.
- Entity registry: `entity-registry-v1`.
- Existing source registry: `v0.1`, independent of the entity registry.

```sh
python3 -m intelligence.pipeline.run --entities-only
python3 -m intelligence.pipeline.run --entities-only --json
python3 -m intelligence.pipeline.run --entities-only --cleaning-version stage6-v1
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_entities
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_pipeline
```

Operational CLI commands use configured storage. Verification commands isolate
all writes in temporary directories and deny network access. All six CLI modes
are mutually exclusive. Stage 10 rejects fetch options and an independent
`--since`: it consumes the complete cohort linked to the latest completed
successful/partially successful Stage 9 run matching the requested upstream
versions. No completed run means an empty successful extraction run. Exit codes
are 0 for success, 1 for partial success/failure, and 2 for CLI usage errors.

## Bounded registry and local provenance

`catalog.json` contains 43 explicit definitions. Each has a stable typed ID,
canonical name, typed aliases with language/abbreviation metadata, active status,
optional parent, optional emirate, and provenance. Dataset-derived provenance
includes the local path, source columns/relationship, and SHA-256. These hashes
record the inspected source revision; they are not checked against large data
files during extraction.

Sources were inspected read-only:

| Local source | Inspected content | Registry use |
| --- | --- | --- |
| `data/dubai/latest_combined_data.parquet` | 818,838 rows; 69 areas, 85 master projects, 2,260 projects, 4,548 buildings, 462 developers | Selected explicit names and unambiguous parent relationships |
| `regions/abu_dhabi/Abu_Dhabi_Sales_Cleaned (1).csv` | 109,097 rows; 132 districts, 928 communities, 368 projects | Selected districts and projects with uniquely observed parents |
| `regions/sharjah/sources.py` | Existing static area definitions | Al Khan and Muwaileh Commercial |
| `regions/rak/sources.py` | Existing static area definitions | Jazeerat AL Marjan |
| Stage 10 authorization | Finite UAE geographic vocabulary and explicit same-name city policy | Country, seven emirates, qualified Dubai/Abu Dhabi cities |

Dubai source SHA-256:
`af11b45a3264d46586397fe46cb41686a55daed7a598eae89e61d3ecc5d9d335`.
Abu Dhabi source SHA-256:
`8e63124b58155e780c98e227fcc480643dcf437632e1dbb2d22a5834cb085785`.

The catalog is a deliberately small projection, not an exhaustive property
directory. Dubai `area_name_en` maps to AREA, `master_project_en` to COMMUNITY,
`project_name_en` to PROJECT, `building_name_en` to BUILDING, and
`developer_name_en` to DEVELOPER. Abu Dhabi District maps to AREA. Opaque coded
community names are omitted; a selected project can point directly to its
uniquely verified district. Static Sharjah/RAK area labels map to AREA.

Verified Dubai parent chains include Dubai Marina → Marsa Dubai, Motor City →
Al Hebiah First, Sobha Solis → Motor City, and Sobha Solis Tower C → Sobha Solis.
Downtown Dubai is a COMMUNITY from `master_project_en`, with Dubai emirate as
its parent. Its ambiguous intermediate Burj Khalifa district is omitted.
Business Bay keeps its explicit AREA identity; the same label in the master
project column is not added as a conflicting second identity. Burj Khalifa,
generic/private names, uncertain relationships and guessed developer mergers
are excluded. These are extraction ontology choices; source data is unchanged.

Developer definitions retain source identities. `Emaar Properties` is an explicit
legal-suffix omission alias of `EMAAR PROPERTIES (P.J.S.C)`; `Dubai Creek Harbour
LLC` is a punctuation variant of `DUBAI CREEK HARBOUR L.L.C`. Neither rule merges
separate legal entities. Bare `Emaar` and `Sobha` are not aliases.

## Ontology and hierarchy

The eight entity types are COUNTRY, EMIRATE, CITY, AREA, COMMUNITY, PROJECT,
BUILDING, and DEVELOPER. IDs are explicit lowercase names prefixed by type,
for example `emirate:dubai`, `community:dubai:dubai_marina`, and
`project:dubai:sobha_solis`. Aliases and mention positions never determine identity.

| Child | Allowed direct parent types |
| --- | --- |
| COUNTRY | None |
| EMIRATE | COUNTRY |
| CITY | EMIRATE |
| AREA | EMIRATE, CITY |
| COMMUNITY | EMIRATE, CITY, AREA |
| PROJECT | EMIRATE, CITY, AREA, COMMUNITY |
| BUILDING | EMIRATE, CITY, AREA, COMMUNITY, PROJECT |
| DEVELOPER | None |

Geographic children carry a specific emirate consistent with every parent.
Registry loading rejects duplicate IDs, mismatched ID/type prefixes, conflicting
normalized aliases or abbreviation policies, missing/inactive parents for active
children, invalid parent types, cycles, and cross-emirate links. Developers have
no geographic parent or emirate. Production definitions are validated frozen
models; the entity mapping is read-only.

Bare `Dubai` and `Abu Dhabi` identify EMIRATE. Only explicit registered phrases
such as `Dubai City` or `City of Abu Dhabi` identify CITY. A city does not also
emit an overlapping emirate mention. Projects, buildings and developers keep
their types even when their names contain geographic aliases.

## Aliases, overlap and original offsets

Matching uses exact registered aliases after character-wise NFKD normalization,
case folding, combining-mark/tatweel removal, and punctuation/whitespace
collapse. This deliberately supports accent/Arabic-diacritic variation. English
and explicitly curated Arabic geographic names are supported; Arabic aliases
are not invented for dataset entities. Attached Arabic prefixes, spelling
mistakes and unregistered transliterations may remain unmatched.

Each normalized character maps back to its original clean-text character span.
Regex word boundaries prevent substring matches. All candidates are resolved
globally by longest normalized alias, then earliest position and stable ID;
overlapping shorter candidates are suppressed. Repeated, nonoverlapping mentions
survive. Output is ordered by TITLE before BODY, then original span position.

`RAK` and `UAQ` require exact uppercase source spelling and qualifying property
context in the same sentence, at most eight intervening tokens away. They use
MEDIUM confidence and `CONTEXT_ABBREVIATION`; other aliases use HIGH confidence
and `EXACT_ALIAS`. Confidence records match policy, not a calibrated probability.
Bare English `Emirates` is deliberately unregistered. The Arabic country alias
immediately preceded by `طيران` is suppressed as an airline-brand safeguard.
These conservative rules do not provide general named-entity disambiguation.

Every mention contains entity ID, canonical name, type, direct parent ID,
matched text, normalized alias, TITLE/BODY source field, start/end offsets,
confidence, and extraction method. Offsets use Python Unicode character indexes,
zero-based with exclusive end:

```python
clean_text[mention.start_offset:mention.end_offset] == mention.matched_text
```

Boundary validation checks canonical registry identity/type/parent, exact source
slice, registered normalized alias, entity-ID set and derived scope. Result
models additionally enforce ordered nonoverlapping mentions. The limits are 160
original characters per mention and 256 mentions per article. Exceeding either
fails that article with `EntityExtractionError`; evidence is never truncated.

## Location scope

The supported values are DUBAI, ABU_DHABI, SHARJAH, AJMAN, RAS_AL_KHAIMAH,
FUJAIRAH, UMM_AL_QUWAIN, UAE_WIDE, MULTI_EMIRATE and UNKNOWN. Distinct specific
emirates from geographic mentions determine scope: one gives that emirate; two
or more give MULTI_EMIRATE. With none, a country mention gives UAE_WIDE;
otherwise scope is UNKNOWN. A country mention alongside one specific location
does not broaden it to UAE_WIDE. A developer alone never supplies geography.

Child mentions may contribute their validated registry emirate to scope. Parent
mentions are never fabricated: a mention of Sobha Solis can imply DUBAI scope
without emitting unmentioned Motor City, Dubai or UAE spans. An accepted Stage 9
article can validly produce UNKNOWN and zero mentions under this finite registry.

## Storage, history and snapshot safety

The four additive tables are `entity_extraction_results`, `entity_mentions`,
`entity_extraction_run_log`, and `entity_extraction_run_results`. Mention identity,
type and parent are queryable relational columns. Unique entity IDs are derived
from stored mentions on readback. No opaque entity-list blob is authoritative.

The result identity includes the full Stage 9 key:
`article_id`, `raw_hash`, `cleaning_version`, `dedup_version`,
`relevance_version`, `context_id`, `uae_relevance_version`, `registry_version`,
plus `entity_extraction_version` and `entity_registry_version`. A deterministic
SHA-256 of this ten-field key is `extraction_id`; the complete key also has a
unique constraint. Full Stage 9 and duplicate-group foreign keys preserve
backward provenance. Canonical duplicate contexts are processed once, and
duplicate members resolve through their existing canonical group.

Same-key reruns link existing results without extracting again. Changed
extractor/registry/upstream versions or canonical context create new results
while preserving old rows. Catalog changes require a new entity registry
version; algorithm/policy changes require an extractor version bump. Historical
mentions retain their original canonical labels and parent IDs.

The existing shared pipeline guard and owned-run recovery are reused. Stage 10
reads its selected Stage 9 run/results, Stage 8 results/run links, clean cohort
and duplicate groups inside a read transaction. After extraction, it obtains
`BEGIN IMMEDIATE`, recomputes the snapshot and refuses publication if anything
changed. Results, mentions, run links and final run status commit atomically.
Persistence/snapshot failures roll back all extraction output; a failed run log
remains. Foreign pipeline run ownership and recent active runs are preserved.

Malformed individual accepted contexts fail locally while healthy contexts
continue. Orphaned structural references fail the run. Run logs capture all
versions, Stage 9 run ID, eligible/ineligible/seen/evaluated/skipped/failed counts,
records with/without entities, total and per-type mention counts, duration and
status. Errors retain only bounded type/record diagnostics (first 100), with a
separate total count. No article body or arbitrary exception text is logged.

## Validation and limitations

`verify_entities` covers the finite English/Arabic corpus, ontology rejection,
offsets, overlap, scope, eligibility, persisted readback, history, transactional
rollback, concurrent upstream mutation, locks, bounded errors, CLI behavior,
fresh/additive migration paths and 50/100/200 article extraction-call scaling.
The permanent pipeline harness drives actual Stage 3→10 input/output boundaries
from local feed bytes and checks stored lineage, all entity types, all seven
emirates, UNKNOWN/UAE-wide/multi-emirate scope, failures and immutability.

These are synthetic correctness and contract tests, not production precision or
recall estimates. Areas/projects/buildings/developers are intentionally bounded;
city coverage has only two explicitly qualified cities. Historical runtime
datasets absent from the workspace cannot be replayed. There is no Streamlit
integration, event/numeric extraction, investment interpretation, or Stage 11
implementation.
