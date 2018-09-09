# CacheCraft Design Notes

## Product intent
CacheCraft makes simulates cache policies across request traces to compare hit rate, saved latency and match quality practical in a reviewable developer workflow. It favors compact source data, deterministic scoring and reports that retain the evidence behind every result.

## Design principles
1. **Traceable results** — every score connects to normalized input records and named calculations.
2. **Portable artifacts** — JSON and Markdown reports travel cleanly through pull requests and release notes.
