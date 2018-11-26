package craft

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sort"
	"strings"
)

// Request is one recorded request from a trace.
type Request struct {
	ID       string  `json:"id"`
	Route    string  `json:"route"`
	Prompt   string  `json:"prompt"`
	CostMS   float64 `json:"cost_ms"`
	TS       float64 `json:"ts"`
	TokensIn int     `json:"tokens_in"`
}

// LoadTrace parses a JSONL request trace from r. Blank lines and lines that
// begin with '#' are ignored so fixtures can carry comments.
func LoadTrace(r io.Reader) ([]Request, error) {
	var out []Request
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		var req Request
		if err := json.Unmarshal([]byte(line), &req); err != nil {
			return nil, fmt.Errorf("line %d: %w", lineNo, err)
		}
		if req.Route == "" || req.Prompt == "" {
			return nil, fmt.Errorf("line %d: route and prompt are required", lineNo)
		}
		if req.ID == "" {
			req.ID = fmt.Sprintf("req-%06d", lineNo)
		}
		out = append(out, req)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

// Result aggregates a replay of one strategy over a trace.
type Result struct {
	Strategy  string  `json:"strategy"`
	Total     int     `json:"requests"`
	Hits      int     `json:"hits"`
	HitRate   float64 `json:"hit_rate"`
	AvoidedMS float64 `json:"avoided_ms"`
	ServedMS  float64 `json:"served_ms"`
	MeanQual  float64 `json:"mean_quality"`
}

// Replay streams requests through a strategy, inserting misses so the cache
// warms over the trace. It returns aggregate metrics.
func Replay(reqs []Request, s Strategy, hitCostMS float64, dropStopwords bool) Result {
	ordered := make([]Request, len(reqs))
	copy(ordered, reqs)
	sort.SliceStable(ordered, func(i, j int) bool {
		if ordered[i].TS == ordered[j].TS {
			return ordered[i].ID < ordered[j].ID
