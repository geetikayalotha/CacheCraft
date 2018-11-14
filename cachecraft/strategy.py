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
