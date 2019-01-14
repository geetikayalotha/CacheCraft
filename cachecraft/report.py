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
