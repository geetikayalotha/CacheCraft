# CacheCraft Architecture

CacheCraft is a Semantic Cache Strategy Bench that simulates cache policies across request traces to compare hit rate, saved latency and match quality. The repository uses a Python orchestration layer and a focused native companion so input normalization, deterministic analysis and report rendering remain easy to inspect.

## System flow

`	ext
fixtures or operator input -> parser -> normalized domain records -> analysis engine -> report model -> terminal / JSON / Markdown
` 

## Components

- **Python package** owns command handling, portable parsers, report assembly and example workflows.
