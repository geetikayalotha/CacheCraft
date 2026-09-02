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


@dataclass
class StrategySpec:
    kind: str
    params: dict[str, Any] = field(default_factory=dict)

    def build(self) -> Strategy:
        return build_strategy(self.kind, self.params)


@dataclass
class BenchConfig:
    strategies: list[StrategySpec]
    hit_cost_ms: float = 5.0
    drop_stopwords: bool = True

    def build_all(self) -> list[Strategy]:
        return [spec.build() for spec in self.strategies]


def default_config() -> BenchConfig:
    """Return a config comparing every built-in strategy."""

    specs = [StrategySpec(kind=name) for name in available()]
    return BenchConfig(strategies=specs)


def parse_config(raw: dict[str, Any]) -> BenchConfig:
    """Validate and build a :class:`BenchConfig` from a mapping."""

    if "strategies" not in raw or not isinstance(raw["strategies"], list):
        raise ConfigError("config must contain a 'strategies' array")
    specs: list[StrategySpec] = []
    for i, entry in enumerate(raw["strategies"]):
        if not isinstance(entry, dict) or "kind" not in entry:
            raise ConfigError(f"strategies[{i}] must be an object with a 'kind'")
        specs.append(
            StrategySpec(kind=str(entry["kind"]), params=dict(entry.get("params", {})))
        )
    return BenchConfig(
        strategies=specs,
        hit_cost_ms=float(raw.get("hit_cost_ms", 5.0)),
        drop_stopwords=bool(raw.get("drop_stopwords", True)),
    )


def load_config(path: str | Path) -> BenchConfig:
    """Load a bench config from a JSON file."""

    text = Path(path).read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON config: {exc.msg}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config root must be a JSON object")
    return parse_config(raw)
