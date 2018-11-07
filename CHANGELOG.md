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
