"""CacheCraft command line interface.

Commands
--------
``bench``
    Replay a trace through a set of strategies and print a comparison.
``inspect``
    Print summary statistics for a trace.
``strategies``
    List the built-in strategies.
``signals``
    Show the derived signals for a single prompt (debugging aid).

Run ``python -m cachecraft --help`` for the full grammar.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import default_config, load_config
from .engine import replay
from .normalize import derive, prefix_key
from .report import render_report
from .strategy import available
from .trace import TraceError, load_trace, trace_stats


def _cmd_strategies(_: argparse.Namespace) -> int:
    for name in available():
        print(name)
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    try:
        requests = load_trace(args.trace)
    except (TraceError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    stats = trace_stats(requests)
    print(json.dumps(stats, indent=2))
    return 0


def _cmd_signals(args: argparse.Namespace) -> int:
    sig = derive(args.prompt)
    out = {
        "canonical": sig.canonical,
        "tokens": list(sig.tokens),
        "fingerprint": sig.fingerprint,
        "prefix_key": prefix_key(sig.canonical, words=args.words),
    }
    print(json.dumps(out, indent=2))
    return 0


def _cmd_bench(args: argparse.Namespace) -> int:
    try:
        requests = load_trace(args.trace)
    except (TraceError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.config:
        try:
            config = load_config(args.config)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    else:
        config = default_config()

    baseline_cost = sum(r.cost_ms for r in requests)
    results = []
    for strategy in config.build_all():
        results.append(
            replay(
                requests,
                strategy,
                hit_cost_ms=config.hit_cost_ms,
                drop_stopwords=config.drop_stopwords,
            )
        )

    rendered = render_report(results, baseline_cost, fmt=args.format)
    if args.out:
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(rendered)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cachecraft",
        description="Semantic Cache Strategy Bench",
