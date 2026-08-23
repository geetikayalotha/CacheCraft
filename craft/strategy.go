package craft

// Strategy is the tiny protocol implemented by every native cache policy.
type Strategy interface {
	Name() string
	Lookup(s Signals, route string) (Match, bool)
	Insert(key string, s Signals, route string)
}

// Match describes a cache hit and its quality in [0, 1].
type Match struct {
	Key     string
	Quality float64
	Kind    string
}

type entry struct {
	sig   Signals
	route string
	key   string
}

// ExactStrategy keys on the canonical fingerprint. Zero false hits.
type ExactStrategy struct {
	byFP map[string]string
}

// NewExact builds an exact-match strategy.
func NewExact() *ExactStrategy { return &ExactStrategy{byFP: map[string]string{}} }

// Name returns the strategy identifier.
func (e *ExactStrategy) Name() string { return "exact" }

// Lookup returns a match when the fingerprint has been seen before.
func (e *ExactStrategy) Lookup(s Signals, _ string) (Match, bool) {
	if k, ok := e.byFP[s.Fingerprint]; ok {
		return Match{Key: k, Quality: 1.0, Kind: "exact"}, true
	}
	return Match{}, false
}

// Insert records a fingerprint for future lookups.
func (e *ExactStrategy) Insert(key string, s Signals, _ string) {
	if _, ok := e.byFP[s.Fingerprint]; !ok {
		e.byFP[s.Fingerprint] = key
	}
}

// OverlapStrategy accepts the best token-set match above a threshold, optionally
// scoped to the request route.
type OverlapStrategy struct {
	threshold   float64
	routeScoped bool
	entries     []entry
}

// NewOverlap builds a token-overlap strategy.
func NewOverlap(threshold float64, routeScoped bool) *OverlapStrategy {
	return &OverlapStrategy{threshold: threshold, routeScoped: routeScoped}
}

// Name returns the strategy identifier.
func (o *OverlapStrategy) Name() string {
	if o.routeScoped {
		return "route-overlap"
	}
	return "overlap"
}

// Lookup scans live entries for the best Jaccard match at or above threshold.
func (o *OverlapStrategy) Lookup(s Signals, route string) (Match, bool) {
	best := 0.0
	bestKey := ""
	for _, e := range o.entries {
		if o.routeScoped && e.route != route {
			continue
		}
		score := Jaccard(s.TokenSet, e.sig.TokenSet)
		if score > best {
			best, bestKey = score, e.key
		}
	}
	if bestKey != "" && best >= o.threshold {
		return Match{Key: bestKey, Quality: round4(best), Kind: "overlap"}, true
	}
	return Match{}, false
}

// Insert appends an entry to the scan set.
func (o *OverlapStrategy) Insert(key string, s Signals, route string) {
	o.entries = append(o.entries, entry{sig: s, route: route, key: key})
}

func round4(v float64) float64 {
	return float64(int(v*10000+0.5)) / 10000
}
