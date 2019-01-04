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
