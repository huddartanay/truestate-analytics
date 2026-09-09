# Stage 15 local model runtime

`ollama.py` supplies a loopback-only, bounded Ollama client. It disables HTTP
proxies, rejects remote URLs and redirects, requires an already-installed tag,
and exposes no pull/push/create endpoint. It strips optional reasoning fields.
There is no network retry, model fallback, ensemble or application selector.
The runtime entry point requires a single measured selection in configuration.
Until a configuration clears the critical gate, generation fails closed.
No Stage 16 production prompt, retrieval or answer engine exists here.

Development-only candidate iteration and A/B/C instructions live under
`intelligence/benchmarks/`; they are never imported by the production client.
The benchmark requires all three approved tags already installed and never
acquires models itself. Results checkpoint after each measured request.

The authorized target is Apple M1 / 8 GB / macOS 15.7.3. Ollama was installed
through Homebrew and started explicitly, without enabling a login service:

```sh
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 \
OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 \
OLLAMA_CONTEXT_LENGTH=2048 OLLAMA_KEEP_ALIVE=5m \
OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 ollama serve
```

The local API is reachable only through localhost. Production code performs no
model acquisition. Benchmark models remain optional development artifacts in
the Ollama store; unused candidates are not application dependencies.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.tests.verify_stage15
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.benchmarks.stage15_run
PYTHONDONTWRITEBYTECODE=1 python3 -m intelligence.benchmarks.stage15_report
```

The live benchmark needs host permission for localhost and macOS telemetry.
It samples process RSS and kernel pressure/swap, aborting a task-owned runner
on critical pressure or excessive swap growth. Offline tests deny all network
and mock inference; they do not re-run or inflate measured benchmark results.
Read the predeclared protocol and final benchmark report for methodology,
resource limits, actual measurements, failure flags and selection limitations.

Current measured outcome: no configuration cleared the declared critical gate.
Production model/prompt/context selection is therefore unset and generation is
disabled. See [the measured report](../STAGE15_MODEL_PROMPT_BENCHMARK.md), including
scorer limitations, all original safety stops and controlled retries. Stage 15
is incomplete; the runtime integration alone does not authorize Stage 16.
