// Command craftbench is the native companion runner for CacheCraft. It replays
// a JSONL request trace through the exact and token-overlap strategies and
// prints a compact JSON comparison. It shares canonicalization rules with the
// Python bench so results are directly comparable.
//
// Usage:
//
//	craftbench -trace path/to/trace.jsonl [-threshold 0.6] [-hit-cost 5]
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	craft "cachecraft/craft"
