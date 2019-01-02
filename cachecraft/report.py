"""Report rendering.

Turns one or more :class:`~cachecraft.engine.ReplayResult` objects into
structured output. Two renderers are provided:

- :func:`render_json` — a machine-readable comparison document.
- :func:`render_table` — a copper/slate ASCII table for the terminal.

The comparison also computes a *trade-off score* per strategy that blends hit
rate, avoided latency, and match quality into a single ranking number so the
best all-round policy is obvious at a glance.
"""

from __future__ import annotations

import json
from typing import Any

from .engine import ReplayResult


def tradeoff_score(result: ReplayResult, baseline_cost_ms: float) -> float:
    """Blend hit rate, latency savings, and quality into one 0-100 score.

    The score rewards saving real latency and keeping match quality high while
    lightly penalizing low quality hits (which risk stale answers). It is a
    ranking aid, not a physical unit.
    """

    if not result.total or baseline_cost_ms <= 0:
        return 0.0
    savings_ratio = min(result.avoided_ms / baseline_cost_ms, 1.0)
    quality = result.mean_quality
    hit_rate = result.hit_rate
    raw = (0.5 * savings_ratio) + (0.3 * hit_rate) + (0.2 * quality)
    return round(raw * 100, 2)


def summarize(result: ReplayResult, baseline_cost_ms: float) -> dict[str, Any]:
    """Return a summary dict for a single strategy result."""

    return {
        "strategy": result.strategy,
        "requests": result.total,
        "hits": result.hits,
        "hit_rate": result.hit_rate,
