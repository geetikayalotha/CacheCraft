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
