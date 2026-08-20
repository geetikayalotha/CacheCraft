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
    fingerprint: str = field(compare=False)


def canonicalize(text: str) -> str:
    """Return a canonical single-line representation of *text*.

    Steps: Unicode NFKC folding, lower-casing, punctuation removal, and
    whitespace collapse. The result is stable across platforms because NFKC
    is defined by the Unicode standard, not the host locale.
    """

    folded = unicodedata.normalize("NFKC", text)
    lowered = folded.casefold()
    without_punct = _PUNCT.sub(" ", lowered)
    collapsed = _WHITESPACE.sub(" ", without_punct).strip()
    return collapsed


def tokenize(text: str, *, drop_stopwords: bool = True) -> tuple[str, ...]:
    """Tokenize *text* into content tokens.

    Tokens are maximal runs of ASCII letters and digits taken from the
    canonical form. When *drop_stopwords* is true, common filler words are
    removed to sharpen overlap comparisons.
    """

    canonical = canonicalize(text)
    raw = _TOKEN.findall(canonical)
    if drop_stopwords:
        return tuple(tok for tok in raw if tok not in _STOPWORDS)
    return tuple(raw)


def fingerprint(canonical: str) -> str:
    """Return a stable hex fingerprint for a canonical string."""

    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def derive(text: str, *, drop_stopwords: bool = True) -> Signals:
    """Derive the full :class:`Signals` bundle for *text*."""

    canonical = canonicalize(text)
    tokens = tokenize(text, drop_stopwords=drop_stopwords)
    return Signals(
        canonical=canonical,
        tokens=tokens,
        token_set=frozenset(tokens),
        fingerprint=fingerprint(canonical),
    )


def prefix_key(text: str, *, words: int) -> str:
    """Return a normalized-prefix key using the first *words* tokens.

    The prefix key groups requests that begin the same way — a common pattern
    when clients build prompts from a shared template and vary only the tail.
    """

    toks = tokenize(text, drop_stopwords=False)
    head = toks[: max(words, 0)]
    return " ".join(head)


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    """Return the Jaccard similarity of two token iterables in [0, 1]."""

    sa, sb = frozenset(a), frozenset(b)
    if not sa and not sb:
        return 1.0
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)
