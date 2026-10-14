"""Cache matching strategies.

CacheCraft ships four policies. Each implements the same tiny protocol:

- ``lookup(signals, route)`` returns a :class:`Match` or ``None``.
- ``insert(key, signals, route)`` records an entry for future lookups.

A *match* carries a quality score in [0, 1] describing how confident the
policy is that the cached answer is reusable. Exact matches always score 1.0;
fuzzy policies score by similarity so reports can weigh hit rate against
match quality.

The four strategies
-------------------
``exact``
    Keys on the SHA-1 fingerprint of the canonical text. Zero false hits,
    lowest hit rate. The safety baseline.

``prefix``
    Keys on the first *N* normalized tokens. Great for templated prompts that
    share a stem and vary only in the tail.

``overlap``
    Token-set Jaccard similarity against every live entry in the same route,
    accepting the best candidate above a threshold. Highest hit rate, needs a
    quality floor to stay honest.

``route``
    A composite that tries ``exact`` first, then falls back to ``overlap``
    but *scoped to the request's route*. Balances precision and recall and
    models real routers that never cross endpoints.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Protocol

from .normalize import Signals, jaccard, prefix_key


@dataclass(frozen=True)
class Match:
    """A cache hit describing which entry matched and how well."""

    key: str
    quality: float
    kind: str


class Strategy(Protocol):
    """The protocol every cache policy implements."""

    name: str

    def lookup(self, signals: Signals, route: str) -> Match | None: ...

    def insert(self, key: str, signals: Signals, route: str) -> None: ...


class _LruStore:
    """A bounded LRU keyed store shared by the fuzzy strategies."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._items: "OrderedDict[str, tuple[Signals, str]]" = OrderedDict()

    def touch(self, key: str) -> None:
        if key in self._items:
            self._items.move_to_end(key)

    def put(self, key: str, signals: Signals, route: str) -> None:
        self._items[key] = (signals, route)
        self._items.move_to_end(key)
        while self.capacity and len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def items(self) -> list[tuple[str, Signals, str]]:
        return [(k, s, r) for k, (s, r) in self._items.items()]


class ExactStrategy:
    name = "exact"

    def __init__(self, capacity: int = 0) -> None:
        self._store = _LruStore(capacity)
        self._by_fp: dict[str, str] = {}

    def lookup(self, signals: Signals, route: str) -> Match | None:
        key = self._by_fp.get(signals.fingerprint)
        if key is None:
            return None
        self._store.touch(key)
        return Match(key=key, quality=1.0, kind="exact")

    def insert(self, key: str, signals: Signals, route: str) -> None:
        self._by_fp[signals.fingerprint] = key
        self._store.put(key, signals, route)


class PrefixStrategy:
    name = "prefix"

    def __init__(self, words: int = 6, capacity: int = 0) -> None:
        self.words = words
        self._store = _LruStore(capacity)
        self._by_prefix: dict[str, str] = {}

    def _pk(self, signals: Signals) -> str:
        return prefix_key(signals.canonical, words=self.words)

    def lookup(self, signals: Signals, route: str) -> Match | None:
        pk = self._pk(signals)
        key = self._by_prefix.get(pk)
        if key is None:
            return None
        self._store.touch(key)
        # Quality reflects how much of the request the shared prefix covers.
        covered = min(len(signals.tokens), self.words)
        denom = max(len(signals.tokens), 1)
        quality = round(0.5 + 0.5 * (covered / denom), 4)
        return Match(key=key, quality=quality, kind="prefix")

    def insert(self, key: str, signals: Signals, route: str) -> None:
        self._by_prefix.setdefault(self._pk(signals), key)
        self._store.put(key, signals, route)


class OverlapStrategy:
    name = "overlap"

    def __init__(self, threshold: float = 0.6, capacity: int = 512,
                 route_scoped: bool = False) -> None:
        self.threshold = threshold
        self.route_scoped = route_scoped
        self._store = _LruStore(capacity)

    def lookup(self, signals: Signals, route: str) -> Match | None:
        best_key: str | None = None
        best_score = 0.0
        for key, cand, cand_route in self._store.items():
            if self.route_scoped and cand_route != route:
                continue
            score = jaccard(signals.token_set, cand.token_set)
            if score > best_score:
                best_score, best_key = score, key
        if best_key is not None and best_score >= self.threshold:
            self._store.touch(best_key)
            return Match(key=best_key, quality=round(best_score, 4),
                         kind="overlap")
        return None

    def insert(self, key: str, signals: Signals, route: str) -> None:
        self._store.put(key, signals, route)


class RouteStrategy:
    """Exact-first, then route-scoped overlap fallback."""

    name = "route"

    def __init__(self, threshold: float = 0.55, capacity: int = 512) -> None:
        self._exact = ExactStrategy(capacity=capacity)
        self._overlap = OverlapStrategy(
            threshold=threshold, capacity=capacity, route_scoped=True
        )

    def lookup(self, signals: Signals, route: str) -> Match | None:
        hit = self._exact.lookup(signals, route)
        if hit is not None:
            return hit
        return self._overlap.lookup(signals, route)

    def insert(self, key: str, signals: Signals, route: str) -> None:
        self._exact.insert(key, signals, route)
        self._overlap.insert(key, signals, route)


_BUILDERS = {
    "exact": lambda p: ExactStrategy(capacity=int(p.get("capacity", 0))),
    "prefix": lambda p: PrefixStrategy(
        words=int(p.get("words", 6)), capacity=int(p.get("capacity", 0))
    ),
    "overlap": lambda p: OverlapStrategy(
        threshold=float(p.get("threshold", 0.6)),
        capacity=int(p.get("capacity", 512)),
        route_scoped=bool(p.get("route_scoped", False)),
    ),
    "route": lambda p: RouteStrategy(
        threshold=float(p.get("threshold", 0.55)),
        capacity=int(p.get("capacity", 512)),
    ),
}


def build_strategy(kind: str, params: dict[str, Any] | None = None) -> Strategy:
    """Construct a strategy by name from a parameter mapping.

    Parameters
    ----------
    kind:
        One of ``exact``, ``prefix``, ``overlap``, ``route``.
    params:
        Strategy-specific knobs (``threshold``, ``words``, ``capacity``,
        ``route_scoped``). Unknown keys are ignored so configs can carry
        annotations.
    """

    builder = _BUILDERS.get(kind)
    if builder is None:
        raise ValueError(
            f"unknown strategy {kind!r}; choose from {sorted(_BUILDERS)}"
        )
    return builder(params or {})


def available() -> list[str]:
    """Return the sorted list of built-in strategy names."""

    return sorted(_BUILDERS)
