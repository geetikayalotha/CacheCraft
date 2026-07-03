# Changelog

All notable changes to CacheCraft are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project governance and contributor documentation (`CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`).
- Architecture and design references (`ARCHITECTURE.md`, `DESIGN.md`).
- Packaging metadata (`pyproject.toml`), developer `Makefile`, and CI workflow.

## [0.6.0] - 2025-09-01

### Added
- `route` strategy: exact-first matching with a route-scoped `overlap`
  fallback, modeling routers that never reuse an answer across endpoints.
- Per-route breakdown in `ReplayResult.per_route()` and in both the table and
  JSON reports, so you can see which endpoint carries the caching wins.
- Native Go companion runner (`craft/`) with `craftbench` mirroring the
  `exact` and `overlap` policies for large-trace throughput.

### Changed
- Trade-off score reweighted to `0.5*avoided + 0.3*hit_rate + 0.2*quality`
  so avoided latency, not raw hit rate, drives the ranking.

## [0.5.0] - 2025-08-18

### Added
- `overlap` strategy using Jaccard similarity over token sets with a
  configurable acceptance threshold and bounded LRU store.
- Match `quality` score in `[0, 1]` carried by every hit so reports can
  penalize reckless fuzzy matching.

### Changed
- Replay engine now models a fixed `hit_cost_ms` per hit and reports
  `avoided_ms` floored at zero, reflecting that caches are not free.

## [0.4.0] - 2025-08-04

### Added
- `prefix` strategy keyed on the first N normalized tokens for templated
  prompts that share a stem.
- Bench configuration loader (`config.py`) so an experiment can be versioned
  as JSON alongside its trace.

### Fixed
- Deterministic canonicalization via Unicode NFKC folding, ensuring signals
  are byte-identical across platforms and locales.

## [0.3.0] - 2025-07-21

### Added
- JSONL trace loader with 1-based line-number errors (`TraceError`), comment
  and blank-line skipping, and `trace_stats` summaries.
- `exact` strategy keyed on the SHA-1 fingerprint of the canonical text as the
  zero-false-hit safety baseline.
- Initial CLI with `bench`, `inspect`, `signals`, and `strategies` commands.

[Unreleased]: https://example.com/cachecraft/compare/v0.6.0...HEAD
[0.6.0]: https://example.com/cachecraft/releases/tag/v0.6.0
[0.5.0]: https://example.com/cachecraft/releases/tag/v0.5.0
[0.4.0]: https://example.com/cachecraft/releases/tag/v0.4.0
[0.3.0]: https://example.com/cachecraft/releases/tag/v0.3.0
