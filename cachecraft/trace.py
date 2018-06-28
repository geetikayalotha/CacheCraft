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
