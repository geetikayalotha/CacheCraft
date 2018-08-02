"""CacheCraft — Semantic Cache Strategy Bench.

CacheCraft simulates and compares semantic cache policies against recorded
request traces. It answers a single operational question with rigor: *given
this traffic and these candidate policies, which caching strategy actually
pays off, and at what quality cost?*

The package is deliberately dependency-free. Every module relies only on the
Python 3.11 standard library so the bench runs identically on a laptop, a CI
runner, or an air-gapped box.

Public surface
--------------
