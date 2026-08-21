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
    )
    parser.add_argument("--version", action="version", version=f"cachecraft {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_bench = sub.add_parser("bench", help="compare cache strategies over a trace")
    p_bench.add_argument("trace", help="path to a JSONL request trace")
    p_bench.add_argument("-c", "--config", help="bench config JSON (optional)")
    p_bench.add_argument("-f", "--format", choices=["table", "json"], default="table")
    p_bench.add_argument("-o", "--out", help="write report to a file instead of stdout")
    p_bench.set_defaults(func=_cmd_bench)

    p_inspect = sub.add_parser("inspect", help="show trace statistics")
    p_inspect.add_argument("trace", help="path to a JSONL request trace")
    p_inspect.set_defaults(func=_cmd_inspect)

    p_sig = sub.add_parser("signals", help="show derived signals for a prompt")
    p_sig.add_argument("prompt", help="prompt text to analyze")
    p_sig.add_argument("--words", type=int, default=6, help="prefix width")
    p_sig.set_defaults(func=_cmd_signals)

    p_strat = sub.add_parser("strategies", help="list built-in strategies")
    p_strat.set_defaults(func=_cmd_strategies)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
