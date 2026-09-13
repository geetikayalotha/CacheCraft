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
)

func main() {
	tracePath := flag.String("trace", "", "path to a JSONL request trace")
	threshold := flag.Float64("threshold", 0.6, "overlap similarity threshold")
	hitCost := flag.Float64("hit-cost", 5.0, "latency of a cache hit in ms")
	keepStop := flag.Bool("keep-stopwords", false, "do not drop filler tokens")
	flag.Parse()

	if *tracePath == "" {
		fmt.Fprintln(os.Stderr, "error: -trace is required")
		os.Exit(2)
	}

	f, err := os.Open(*tracePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(2)
	}
	defer f.Close()

	reqs, err := craft.LoadTrace(f)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(2)
	}

	dropStop := !*keepStop
	strategies := []craft.Strategy{
		craft.NewExact(),
		craft.NewOverlap(*threshold, false),
		craft.NewOverlap(*threshold, true),
	}

	results := make([]craft.Result, 0, len(strategies))
	for _, s := range strategies {
		results = append(results, craft.Replay(reqs, s, *hitCost, dropStop))
	}

	doc := map[string]any{
		"tool":       "craftbench",
		"requests":   len(reqs),
		"strategies": results,
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	if err := enc.Encode(doc); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}
}
