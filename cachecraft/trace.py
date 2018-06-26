"""Request-trace loading and validation.

A CacheCraft trace is a JSON Lines file where each line is one recorded
request. The schema is intentionally small so it can be produced by a proxy,
an application log tap, or a hand-written fixture.

Line schema
-----------
::

    {
      "id":        "req-000123",     # optional; synthesized if absent
      "ts":        1725200000.0,     # optional epoch seconds (float or int)
      "route":     "chat.completions",  # logical endpoint / model group
      "prompt":    "Summarize the Q3 revenue report",  # required
      "cost_ms":   840,              # latency to serve on a MISS (required)
      "tokens_in": 1200,             # optional prompt token count
      "meta":      { "tenant": "acme" }  # optional free-form tags
    }

Only ``route``, ``prompt``, and ``cost_ms`` are required. Everything else is
filled with deterministic defaults so partial traces still replay cleanly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


class TraceError(ValueError):
    """Raised when a trace line cannot be parsed or is missing a field."""


@dataclass(frozen=True)
class Request:
    """One recorded request from a trace."""

    id: str
    route: str
    prompt: str
    cost_ms: float
    ts: float = 0.0
    tokens_in: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


def _coerce(line_no: int, raw: dict[str, Any]) -> Request:
    for required in ("route", "prompt", "cost_ms"):
        if required not in raw:
            raise TraceError(
                f"line {line_no}: missing required field {required!r}"
            )
    try:
        cost = float(raw["cost_ms"])
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise TraceError(f"line {line_no}: cost_ms must be numeric") from exc
    if cost < 0:
        raise TraceError(f"line {line_no}: cost_ms must be non-negative")

    req_id = str(raw.get("id") or f"req-{line_no:06d}")
    return Request(
        id=req_id,
        route=str(raw["route"]),
        prompt=str(raw["prompt"]),
        cost_ms=cost,
        ts=float(raw.get("ts", 0.0)),
        tokens_in=int(raw.get("tokens_in", 0)),
        meta=dict(raw.get("meta", {})),
    )


def iter_trace(path: str | Path) -> Iterator[Request]:
    """Yield :class:`Request` objects from a JSONL trace file.

    Blank lines and lines beginning with ``#`` are skipped, which makes it
    easy to annotate fixtures. Each malformed line raises :class:`TraceError`
