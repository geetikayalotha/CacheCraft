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
