"""Strategy configuration.

A bench config is a JSON document that names the strategies to compare and the
global replay knobs. It lets you version the exact experiment alongside the
trace so a report is reproducible.

Config schema
-------------
::

    {
      "hit_cost_ms": 5.0,
      "drop_stopwords": true,
      "strategies": [
        { "kind": "exact" },
        { "kind": "prefix",  "params": { "words": 5 } },
        { "kind": "overlap", "params": { "threshold": 0.6 } },
        { "kind": "route",   "params": { "threshold": 0.55 } }
      ]
    }

If no config is supplied the CLI falls back to :func:`default_config`, which
compares all four built-in strategies with sensible defaults.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .strategy import Strategy, available, build_strategy


class ConfigError(ValueError):
    """Raised when a bench config is structurally invalid."""

