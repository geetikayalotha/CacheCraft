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
