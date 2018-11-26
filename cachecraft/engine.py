"""The replay engine.

The engine streams a trace through a policy in timestamp order and records,
for each request, whether it was a cache HIT or MISS, the match quality, and
the latency outcome. On a MISS the response is *inserted* into the cache so
later requests can hit it — exactly how a real cache warms up.

Latency model
-------------
- A MISS costs the request's recorded ``cost_ms`` (the origin must serve it).
- A HIT costs a fixed, configurable ``hit_cost_ms`` (the cache lookup itself).
- *Avoided latency* for a hit is ``cost_ms - hit_cost_ms`` (never negative).

This keeps the model honest: caches are not free, and a hit that saves almost
nothing is reported as such.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .normalize import derive
from .strategy import Strategy
from .trace import Request


@dataclass
class Event:
    """The outcome of replaying one request."""

    id: str
    route: str
    hit: bool
    quality: float
    kind: str
    served_ms: float
    avoided_ms: float


@dataclass
class ReplayResult:
    """Aggregate outcome of replaying a whole trace through one strategy."""

    strategy: str
    events: list[Event] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.events)

    @property
    def hits(self) -> int:
        return sum(1 for e in self.events if e.hit)

    @property
    def hit_rate(self) -> float:
        return round(self.hits / self.total, 4) if self.total else 0.0

    @property
    def avoided_ms(self) -> float:
        return round(sum(e.avoided_ms for e in self.events), 3)

    @property
    def served_ms(self) -> float:
        return round(sum(e.served_ms for e in self.events), 3)

    @property
