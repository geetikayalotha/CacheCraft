"""CacheCraft — Semantic Cache Strategy Bench.

CacheCraft simulates and compares semantic cache policies against recorded
request traces. It answers a single operational question with rigor: *given
this traffic and these candidate policies, which caching strategy actually
pays off, and at what quality cost?*

The package is deliberately dependency-free. Every module relies only on the
Python 3.11 standard library so the bench runs identically on a laptop, a CI
runner, or an air-gapped box.

Public surface
--------------
- :func:`cachecraft.trace.load_trace` — parse a JSONL request trace.
- :func:`cachecraft.strategy.build_strategy` — construct a policy from config.
- :func:`cachecraft.engine.replay` — replay a trace through a policy.
- :func:`cachecraft.report.render_report` — turn results into a report.

The command line entry point lives in :mod:`cachecraft.cli`.
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "trace",
    "normalize",
    "strategy",
    "engine",
    "report",
]

__version__ = "0.6.0"
