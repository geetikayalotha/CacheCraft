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
    def mean_quality(self) -> float:
        hit_events = [e.quality for e in self.events if e.hit]
        if not hit_events:
            return 0.0
        return round(sum(hit_events) / len(hit_events), 4)

    def per_route(self) -> dict[str, dict[str, float]]:
        acc: dict[str, dict[str, float]] = {}
        for e in self.events:
            bucket = acc.setdefault(e.route, {"total": 0, "hits": 0, "avoided_ms": 0.0})
            bucket["total"] += 1
            bucket["hits"] += int(e.hit)
            bucket["avoided_ms"] += e.avoided_ms
        for bucket in acc.values():
            total = bucket["total"] or 1
            bucket["hit_rate"] = round(bucket["hits"] / total, 4)
            bucket["avoided_ms"] = round(bucket["avoided_ms"], 3)
        return dict(sorted(acc.items()))


def replay(
    requests: Iterable[Request],
    strategy: Strategy,
    *,
    hit_cost_ms: float = 5.0,
    drop_stopwords: bool = True,
) -> ReplayResult:
    """Replay *requests* through *strategy* and return a :class:`ReplayResult`.

    Requests are processed in the order given; sort upstream if you need
    strict timestamp ordering. Each miss is inserted so the cache warms up
    naturally over the trace.
    """

    ordered = sorted(requests, key=lambda r: (r.ts, r.id))
    result = ReplayResult(strategy=strategy.name)

    for req in ordered:
        signals = derive(req.prompt, drop_stopwords=drop_stopwords)
        match = strategy.lookup(signals, req.route)
        if match is not None:
            served = min(hit_cost_ms, req.cost_ms)
            avoided = max(req.cost_ms - served, 0.0)
            result.events.append(
                Event(
                    id=req.id,
                    route=req.route,
                    hit=True,
                    quality=match.quality,
                    kind=match.kind,
                    served_ms=round(served, 3),
                    avoided_ms=round(avoided, 3),
                )
            )
        else:
            strategy.insert(req.id, signals, req.route)
            result.events.append(
                Event(
                    id=req.id,
                    route=req.route,
                    hit=False,
                    quality=0.0,
                    kind="miss",
                    served_ms=round(req.cost_ms, 3),
                    avoided_ms=0.0,
                )
            )

    return result
