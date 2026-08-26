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
        "mean_quality": result.mean_quality,
        "avoided_ms": result.avoided_ms,
        "served_ms": result.served_ms,
        "tradeoff_score": tradeoff_score(result, baseline_cost_ms),
        "per_route": result.per_route(),
    }


def render_json(results: list[ReplayResult], baseline_cost_ms: float) -> str:
    """Render a comparison document as pretty JSON."""

    summaries = [summarize(r, baseline_cost_ms) for r in results]
    summaries.sort(key=lambda s: s["tradeoff_score"], reverse=True)
    doc = {
        "tool": "cachecraft",
        "baseline_cost_ms": round(baseline_cost_ms, 3),
        "winner": summaries[0]["strategy"] if summaries else None,
        "strategies": summaries,
    }
    return json.dumps(doc, indent=2)


def _bar(value: float, width: int = 20) -> str:
    filled = int(round(value * width))
    return "#" * filled + "-" * (width - filled)


def render_table(results: list[ReplayResult], baseline_cost_ms: float) -> str:
    """Render a compact terminal comparison table."""

    summaries = [summarize(r, baseline_cost_ms) for r in results]
    summaries.sort(key=lambda s: s["tradeoff_score"], reverse=True)

    lines = []
    lines.append("CacheCraft strategy comparison")
    lines.append("=" * 62)
    header = f"{'strategy':<10}{'hit%':>7}{'quality':>9}{'avoided_ms':>13}{'score':>8}"
    lines.append(header)
    lines.append("-" * 62)
    for s in summaries:
        lines.append(
            f"{s['strategy']:<10}"
            f"{s['hit_rate'] * 100:>6.1f}%"
            f"{s['mean_quality']:>9.3f}"
            f"{s['avoided_ms']:>13.1f}"
            f"{s['tradeoff_score']:>8.1f}"
        )
    lines.append("-" * 62)
    lines.append("hit-rate profile")
    for s in summaries:
        lines.append(f"  {s['strategy']:<10} [{_bar(s['hit_rate'])}] {s['hit_rate'] * 100:.1f}%")
    if summaries:
        lines.append("")
        lines.append(f"winner: {summaries[0]['strategy']} "
                     f"(score {summaries[0]['tradeoff_score']:.1f})")
    return "\n".join(lines)


def render_report(
    results: list[ReplayResult],
    baseline_cost_ms: float,
    *,
    fmt: str = "table",
) -> str:
    """Render results in the requested format (``table`` or ``json``)."""

    if fmt == "json":
        return render_json(results, baseline_cost_ms)
    if fmt == "table":
        return render_table(results, baseline_cost_ms)
    raise ValueError(f"unknown format {fmt!r}; choose 'table' or 'json'")
