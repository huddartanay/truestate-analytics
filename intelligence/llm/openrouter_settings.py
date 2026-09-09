"""Single MVP model accepted by explicit engineering exception; strict gate failed.

No key storage, model override or fallback list. Stage 16 orchestration pending.
"""
LLM_PROVIDER = 'openrouter'
OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
OPENROUTER_MODEL = 'qwen/qwen3-235b-a22b-2507'
SELECTED_MODEL = OPENROUTER_MODEL
MVP_PRODUCTION_MODEL = OPENROUTER_MODEL
SELECTED_PROMPT_STRATEGY = 'STRUCTURED_GROUNDED_SAFETY'
MVP_PROMPT_STRATEGY = SELECTED_PROMPT_STRATEGY
SELECTED_PROMPT_REVISION = 'provenance-v1'
SELECTED_SCORER_REVISION = 'provenance-binding-v1.1'
SELECTED_PROVIDER = {
    'provider': 'parasail/fp8',
    'provider_name': 'Parasail',
    'response_models': ('qwen/qwen3-235b-a22b-07-25',),
    'pricing': {'prompt': '0.00000014', 'completion': '0.0000008',
                'input_cache_read': '0.00000005', 'discount': 0},
}
MODEL_SELECTION_VERSION = 'stage15-mvp-v1'
SELECTION_STATUS = 'MVP_ENGINEERING_EXCEPTION'
MODEL_SELECTION_STATUS = SELECTION_STATUS
MVP_MODEL_SELECTION = 'ACCEPTED_BY_ENGINEERING_EXCEPTION'
STRICT_CERTIFICATION = False
STRICT_STAGE15_CERTIFICATION = 'FAILED'
TIMEOUT_SECONDS = 90
MAX_OUTPUT_TOKENS = 1024
TEMPERATURE = 0
