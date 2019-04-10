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
