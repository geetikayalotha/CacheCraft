<!-- CacheCraft README -->
<p align="center">
  <img src="docs/assets/forge-banner.svg" alt="CacheCraft — Semantic Cache Strategy Bench" width="720"/>
</p>

# CacheCraft

**CacheCraft is a semantic cache strategy bench.** It takes a recorded trace of
real requests, replays that traffic through a set of candidate caching policies,
and tells you — with numbers, not vibes — which policy would actually have paid
off, how much latency it would have avoided, and what quality risk you would
have accepted to get there.

Semantic caching is deceptively easy to turn on and dangerously easy to get
wrong. An exact-match cache is safe but rarely hits when clients phrase the same
intent three different ways. A fuzzy token-overlap cache hits far more often but
can serve a stale or subtly wrong answer if its threshold is too loose. The only
honest way to choose is to *measure on your own traffic*. CacheCraft is the
workbench where that measurement happens.

The bench is **dependency-free**. The Python package (`cachecraft`) uses only
the Python 3.11 standard library. The Go companion (`craft/`) uses only the Go
standard library. There is nothing to install from a network, nothing to pin,
and nothing to break on an air-gapped machine.

---

## Table of contents

- [Why CacheCraft exists](#why-cachecraft-exists)
- [The mental model](#the-mental-model)
- [Architecture](#architecture)
- [Install and first run](#install-and-first-run)
- [The trace schema](#the-trace-schema)
- [The four strategies](#the-four-strategies)
- [Signals: how text becomes keys](#signals-how-text-becomes-keys)
- [The replay engine](#the-replay-engine)
- [Reports and the trade-off score](#reports-and-the-trade-off-score)
- [CLI reference and recipes](#cli-reference-and-recipes)
- [The Go companion runner](#the-go-companion-runner)
- [Bench configuration](#bench-configuration)
- [Operations guide](#operations-guide)
- [Extension seams](#extension-seams)
- [Design decisions](#design-decisions)
- [Glossary](#glossary)

---

## Why CacheCraft exists

Teams putting a cache in front of an expensive backend — an LLM endpoint, a
search cluster, a rendering service — face the same recurring questions:

1. **Will a cache even help here?** If every request is unique, no policy hits.
2. **Which matching rule fits this traffic?** Exact, prefix, overlap, or
   route-scoped behave wildly differently depending on how clients phrase
   requests.
3. **What threshold is safe?** A loose fuzzy match saves more latency but risks
   returning the wrong cached answer.
4. **What does the win actually look like?** "Hit rate" alone is misleading; a
   90% hit rate that each saves 3ms is worse than a 40% hit rate that each saves
   900ms.

CacheCraft answers all four from a single artifact you already have or can
cheaply capture: **a log of requests with their served latency.** You do not
need the responses. You do not need to reproduce the backend. You replay the
*shape* of the traffic and let the bench compute the counterfactual.

## The mental model

Think of CacheCraft as a foundry. Raw prompts are the ore. The **normalizer** is
the smelter that reduces each prompt to clean signals — a canonical string, a
token multiset, a fingerprint. Each **strategy** is a different die that stamps
those signals into a cache key and decides whether an incoming request matches
something already forged. The **engine** runs the whole trace across the anvil,
warming the cache as it goes. The **report** is the finished measurement you
carry back to the team.

<p align="center">
  <img src="docs/assets/strategy-gauge.svg" alt="Hit rate by strategy" width="640"/>
</p>

The gauge above is exactly what the bench produces on the bundled sample trace:
`exact` hits 20% of the time, `prefix` 50%, and both `overlap` and `route` reach
65%. But hit rate is only one axis — read on for how CacheCraft weighs it
against avoided latency and match quality.

## Architecture

CacheCraft is two cooperating implementations that share one canonicalization
contract, so a trace scored by either yields comparable keys and token sets.

```
                        ┌──────────────────────────────────────────┐
                        │                CacheCraft                 │
                        └──────────────────────────────────────────┘

  request trace (JSONL)                     bench config (JSON, optional)
        │                                            │
        ▼                                            ▼
  ┌───────────────┐      ┌────────────────┐   ┌──────────────────┐
  │  trace.py     │ ───▶ │  normalize.py  │   │   config.py      │
  │  load / stats │      │  Signals       │   │  StrategySpec    │
  └───────────────┘      │  canonical     │   │  BenchConfig     │
                         │  tokens        │   └───────┬──────────┘
                         │  fingerprint   │           │
                         └───────┬────────┘           │ builds
                                 │                     ▼
                                 │            ┌──────────────────┐
                                 └──────────▶ │  strategy.py     │
                                              │  exact  prefix   │
                                              │  overlap  route  │
                                              └───────┬──────────┘
                                                      │ lookup / insert
                                                      ▼
                                              ┌──────────────────┐
                                              │  engine.py       │
                                              │  replay()        │
                                              │  Event stream    │
                                              │  ReplayResult    │
                                              └───────┬──────────┘
                                                      │
                                                      ▼
                                              ┌──────────────────┐
                                              │  report.py       │
                                              │  table  |  json  │
                                              │  tradeoff_score  │
                                              └───────┬──────────┘
                                                      │
                                                      ▼
                                                stdout / file

  Native fast path (large traces):
     craft/normalize.go ─▶ craft/strategy.go ─▶ craft/engine.go ─▶ cmd/craftbench
```

Component responsibilities:

| Module | Responsibility |
| --- | --- |
| `cachecraft/normalize.py` | Reduce raw text to canonical/tokens/fingerprint signals. |
| `cachecraft/trace.py` | Parse and validate JSONL traces; compute trace stats. |
| `cachecraft/strategy.py` | The four matching policies + the `build_strategy` factory. |
| `cachecraft/engine.py` | Replay a trace through a policy, warming the cache. |
| `cachecraft/report.py` | Summaries, the trade-off score, table and JSON renderers. |
| `cachecraft/config.py` | Parse a bench config into buildable strategy specs. |
| `cachecraft/cli.py` | The `bench`, `inspect`, `signals`, `strategies` commands. |
| `craft/` | Native companion runner mirroring the exact & overlap policies. |

## Install and first run

CacheCraft runs straight from a checkout — there is nothing to build for the
Python side.

```bash
# From the repository root
python -m cachecraft strategies
# -> exact / overlap / prefix / route

python -m cachecraft inspect examples/support_trace.jsonl
# -> JSON stats: count, per-route breakdown, total & mean cost

python -m cachecraft bench examples/support_trace.jsonl -c examples/bench.config.json
```

The `bench` command prints a copper/slate comparison table ranking the four
strategies by trade-off score, with a hit-rate profile and a declared winner.

## The trace schema

A trace is **JSON Lines**: one JSON object per line. Blank lines and lines
beginning with `#` are ignored, so fixtures can be commented.

```jsonc
{
  "id":        "req-000123",        // optional; synthesized as req-<line> if absent
  "ts":        1725200000.0,        // optional epoch seconds; controls replay order
  "route":     "chat.completions",  // REQUIRED logical endpoint / model group
  "prompt":    "Summarize the Q3 report",  // REQUIRED request text
  "cost_ms":   840,                 // REQUIRED latency to serve on a MISS
  "tokens_in": 1200,                // optional prompt token count
  "meta":      { "tenant": "acme" } // optional free-form tags
}
```

Only `route`, `prompt`, and `cost_ms` are required. Every malformed line raises
a `TraceError` carrying its 1-based line number, so bad captures fail loudly and
locatably rather than silently skewing a report.

### Where traces come from

- **A proxy tap.** Log each request's route, prompt text, and serve latency.
- **Application logs.** Most services already record these three fields.
- **Synthetic generation.** Hand-write fixtures like `examples/template_trace.jsonl`
  to probe a specific pattern (e.g., shared-prefix templating).

## The four strategies

Every strategy implements the same two-method protocol: `lookup(signals, route)`
returns a `Match` or `None`, and `insert(key, signals, route)` records an entry.
A `Match` carries a **quality** score in `[0, 1]` — how confident the policy is
that the cached answer is reusable.

### `exact` — the safety baseline

Keys on the SHA-1 fingerprint of the canonical text. A hit only occurs when two
requests canonicalize identically. Quality is always `1.0`. This is the policy
you compare everything else against: it never serves a wrong answer, but it
misses whenever wording drifts.

### `prefix` — the template catcher

Keys on the first *N* normalized tokens. It shines when clients build prompts
from a shared stem (`"Translate the following text to French: …"`) and vary only
the tail. Quality reflects how much of the request the shared prefix covers, so
a long tail beyond the prefix lowers confidence.

### `overlap` — the recall maximizer

Compares the incoming token set against every live entry using **Jaccard
similarity** and accepts the best candidate at or above a threshold. Highest hit
rate of the four, but it *needs* a quality floor (the threshold) to stay honest.
Quality equals the Jaccard score of the accepted match.

### `route` — the balanced default

A composite: it tries `exact` first (precision), then falls back to `overlap`
**scoped to the request's route** (recall without crossing endpoints). This
mirrors real routers that never reuse a chat answer for an embeddings call.

| Strategy | Typical hit rate | False-hit risk | Best for |
| --- | --- | --- | --- |
| `exact` | Low | None | Idempotent, byte-stable requests |
| `prefix` | Medium | Low | Templated prompts with shared stems |
| `overlap` | High | Threshold-dependent | Paraphrase-heavy traffic |
| `route` | High | Low–medium | Mixed multi-endpoint workloads |

## Signals: how text becomes keys

All four strategies build on one deterministic reduction, implemented in
`normalize.py` and mirrored in `craft/normalize.go`:

1. **Canonicalize** — NFKC-fold, casefold, strip punctuation, collapse
   whitespace. `"Please, summarize  the Q3 report!"` becomes
   `"please summarize the q3 report"`.
2. **Tokenize** — split into ASCII word/number runs, optionally dropping a small
   set of English filler words so paraphrases align.
3. **Fingerprint** — SHA-1 of the canonical string; the exact-match key.

Inspect any prompt directly:

```bash
python -m cachecraft signals "Please summarize the Q3 revenue report" --words 4
```

```json
{
  "canonical": "please summarize the q3 revenue report",
  "tokens": ["summarize", "q3", "revenue", "report"],
  "fingerprint": "…40 hex chars…",
  "prefix_key": "please summarize the q3"
}
```

Determinism is a hard requirement: the same input must always produce the same
signals, or hit rates would drift between runs. NFKC and SHA-1 are chosen
precisely because they are defined by standards, not by the host locale.

## The replay engine

`engine.replay()` streams requests through a strategy **in timestamp order**,
recording one `Event` per request:

- On a **MISS**, the request is *inserted* so later requests can hit it. The
  event's served latency is the recorded `cost_ms`.
- On a **HIT**, served latency is a fixed `hit_cost_ms` (the lookup cost). The
  **avoided latency** is `cost_ms - hit_cost_ms`, floored at zero.

This models the truth that caches are not free and warm up over time. A cold
cache misses everything at the start of a trace; the report reflects the honest
blended outcome across the whole run.

`ReplayResult` exposes `hit_rate`, `avoided_ms`, `served_ms`, `mean_quality`,
and a `per_route()` breakdown so you can see whether one endpoint is carrying
all the wins.

## Reports and the trade-off score

Hit rate alone lies. CacheCraft blends three axes into a single **trade-off
score** (0–100) so the best all-round policy is obvious:

```
score = 100 * ( 0.5 * min(avoided_ms / baseline_ms, 1)
              + 0.3 * hit_rate
              + 0.2 * mean_quality )
```

- **Avoided latency** (weight 0.5) — the actual payoff, normalized against the
  total cost of serving everything from origin.
- **Hit rate** (weight 0.3) — how often the cache helped at all.
- **Mean quality** (weight 0.2) — a gentle nudge toward policies whose hits are
  trustworthy, discouraging reckless thresholds.

The `table` renderer draws a copper/slate comparison with a hit-rate bar
profile and a declared winner. The `json` renderer emits a machine-readable
comparison document (sorted by score, with `winner` and per-route detail) for
dashboards and CI gates.

## CLI reference and recipes

```
python -m cachecraft <command> [options]

Commands:
  bench       Compare cache strategies over a trace
  inspect     Show trace statistics
  signals     Show derived signals for a single prompt
  strategies  List built-in strategies
```

**Compare all strategies with defaults (no config needed):**

```bash
python -m cachecraft bench examples/support_trace.jsonl
```

**Use a versioned experiment config:**

```bash
python -m cachecraft bench examples/support_trace.jsonl -c examples/bench.config.json
```

**Emit JSON for a dashboard or a CI gate:**

```bash
python -m cachecraft bench examples/support_trace.jsonl -f json -o report.json
```

**Probe a specific pattern (shared-prefix templating):**

```bash
python -m cachecraft bench examples/template_trace.jsonl
# Watch prefix and overlap pull ahead of exact.
```

**Understand a single prompt before tuning thresholds:**

```bash
python -m cachecraft signals "Draft a friendly reply about refunds"
```

## The Go companion runner

For very large traces, the native `craftbench` runs a single-pass replay of the
exact, overlap, and route-scoped-overlap policies and emits JSON. It shares the
exact canonicalization rules with the Python bench.

```bash
cd craft
go build ./...
go run ./cmd/craftbench -trace ../examples/support_trace.jsonl -threshold 0.6
```

```json
{
  "tool": "craftbench",
  "requests": 20,
  "strategies": [
    { "strategy": "exact",         "hits": 4,  "hit_rate": 0.2,  "avoided_ms": 1980 },
    { "strategy": "overlap",       "hits": 13, "hit_rate": 0.65, "avoided_ms": 7917 },
    { "strategy": "route-overlap", "hits": 13, "hit_rate": 0.65, "avoided_ms": 7917 }
  ]
}
```

Because both implementations agree on canonicalization, the Python and Go hit
rates and avoided-latency figures match on the same trace — a built-in
cross-check that the two runners are faithful to one contract.

Flags: `-trace` (required), `-threshold` (overlap floor), `-hit-cost` (hit
latency in ms), `-keep-stopwords` (disable filler removal).

## Bench configuration

A config pins the exact experiment next to the trace so a report is
reproducible. See `examples/bench.config.json`:

```json
{
  "hit_cost_ms": 5.0,
  "drop_stopwords": true,
  "strategies": [
    { "kind": "exact" },
    { "kind": "prefix",  "params": { "words": 5 } },
    { "kind": "overlap", "params": { "threshold": 0.6, "capacity": 512 } },
    { "kind": "route",   "params": { "threshold": 0.55, "capacity": 512 } }
  ]
}
```

`hit_cost_ms` models the lookup cost, `drop_stopwords` toggles filler removal
globally, and each strategy entry carries its own `params`. Unknown keys are
ignored, so you can annotate configs inline.

## Operations guide

- **Capturing a trace.** Log `route`, `prompt`, and serve `cost_ms`. That is the
  minimum viable capture. Add `ts` if you want faithful ordering and `meta` for
  per-tenant slicing.
- **Choosing `hit_cost_ms`.** Set it to your real cache lookup latency (often
  1–10ms). It matters when your origin costs are themselves small.
- **Reading the per-route table.** If one route dominates avoided latency, focus
  caching there and leave cheap routes uncached.
- **Gating in CI.** Run `bench -f json` and fail the pipeline if the winning
  strategy's `tradeoff_score` regresses below a threshold you commit to the
  repo.
- **Threshold tuning.** Sweep `overlap` thresholds from 0.5 to 0.8; watch
  `mean_quality` rise as hit rate falls, and pick the knee.

## Extension seams

CacheCraft is built to be extended without touching the core:

- **New strategy.** Implement `lookup`/`insert` and register a builder in
  `strategy._BUILDERS`. It immediately becomes available to configs and the CLI.
- **New signal.** Add a derivation to `normalize.py` (e.g., a shingled n-gram
  set) and consume it in a strategy. The `Signals` dataclass is the shared
  contract.
- **New report format.** Add a renderer to `report.py` and a `--format` choice
  in `cli.py`.
- **New trace source.** `trace.iter_trace` is a generator; wrap it to stream
  from a database or a message queue instead of a file.

## Design decisions

- **Standard library only.** Portability and zero supply-chain surface beat
  convenience. See `DESIGN.md` for the full rationale.
- **Two implementations, one contract.** Python for expressiveness and the full
  four-strategy suite; Go for throughput on huge traces. They agree by design.
- **Quality is first-class.** Every fuzzy hit carries a confidence score so the
  report can penalize reckless matching rather than rewarding raw hit rate.
- **Deterministic by construction.** NFKC + SHA-1 + explicit stopwords mean two
  runs are byte-identical.

## Glossary

- **Canonical form** — the normalized single-line representation of a prompt.
- **Signals** — the bundle of canonical string, tokens, token set, and
  fingerprint derived from one prompt.
- **Fingerprint** — SHA-1 hex digest of the canonical form; the exact-match key.
- **Jaccard similarity** — intersection over union of two token sets, in
  `[0, 1]`.
- **Hit / Miss** — whether a request found a reusable cached entry.
- **Avoided latency** — origin latency saved by a hit (`cost_ms - hit_cost_ms`).
- **Match quality** — a policy's confidence, in `[0, 1]`, that a hit is reusable.
- **Trade-off score** — the blended 0–100 ranking of a strategy.
- **Route** — a logical endpoint or model group; a natural cache partition.
- **Warm-up** — the early phase of a trace where a cold cache misses before it
  fills.

---

<p align="center"><em>Forge fast caches. Measure before you trust them.</em></p>

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
