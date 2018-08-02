"""Text normalization and tokenization primitives.

Every matching strategy in CacheCraft reduces a raw prompt to one or more
*signals*: a canonical string, a stable prefix, a token multiset, or a route
tag. This module owns those reductions so that all strategies share one
consistent notion of "what the words are".

The transforms here are intentionally cheap and deterministic. They use no
external NLP libraries — only :mod:`re`, :mod:`unicodedata`, and plain string
operations. Determinism matters: two runs over the same trace must produce
byte-identical signals, otherwise hit rates would drift between reports.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

_WHITESPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", flags=re.UNICODE)
_TOKEN = re.compile(r"[a-z0-9]+", flags=re.UNICODE)

# Common English filler that carries little cache-matching signal. Kept small
# and explicit rather than importing a stopword corpus.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "to",
        "in",
        "on",
        "for",
        "and",
        "or",
        "is",
        "are",
        "please",
        "kindly",
        "could",
        "would",
        "can",
        "you",
        "me",
        "my",
        "our",
    }
)


@dataclass(frozen=True)
class Signals:
    """The bundle of derived signals for a single request text.

    Attributes
    ----------
    canonical:
        Lower-cased, whitespace-collapsed, punctuation-stripped text.
    tokens:
        Ordered content tokens after stopword removal.
    token_set:
        Unique tokens as a frozenset for overlap math.
    fingerprint:
        A stable SHA-1 hex digest of the canonical form, used as the key for
        exact matching.
    """

    canonical: str
    tokens: tuple[str, ...]
    token_set: frozenset[str] = field(compare=False)
