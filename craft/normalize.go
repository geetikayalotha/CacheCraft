// Package craft is the native companion runner for CacheCraft.
//
// It mirrors the Python bench's core signal derivation and the exact and
// token-overlap strategies, but is tuned for speed on very large traces where
// a compiled single-pass replay is preferable. The two implementations agree
// on canonicalization rules so a trace scored by either produces comparable
// fingerprints and token sets.
package craft

import (
	"crypto/sha1"
	"encoding/hex"
	"strings"
	"unicode"
)

// stopwords mirrors the small filler set used by the Python normalizer.
var stopwords = map[string]struct{}{
	"a": {}, "an": {}, "the": {}, "of": {}, "to": {}, "in": {}, "on": {},
	"for": {}, "and": {}, "or": {}, "is": {}, "are": {}, "please": {},
	"kindly": {}, "could": {}, "would": {}, "can": {}, "you": {}, "me": {},
	"my": {}, "our": {},
}

// Signals holds the derived matching signals for one prompt.
type Signals struct {
	Canonical   string
	Tokens      []string
	TokenSet    map[string]struct{}
	Fingerprint string
}

// Canonicalize lower-cases the text, strips punctuation, and collapses runs of
// whitespace into single spaces. It is the shared foundation for every
// strategy so that matching is deterministic.
func Canonicalize(text string) string {
	var b strings.Builder
	b.Grow(len(text))
	prevSpace := false
	for _, r := range strings.ToLower(text) {
		switch {
		case unicode.IsLetter(r) || unicode.IsDigit(r):
			b.WriteRune(r)
			prevSpace = false
		case unicode.IsSpace(r) || unicode.IsPunct(r) || unicode.IsSymbol(r):
			if !prevSpace {
				b.WriteRune(' ')
				prevSpace = true
			}
		}
	}
	return strings.TrimSpace(b.String())
}

// Tokenize splits canonical text into content tokens, optionally dropping the
// common filler words in stopwords.
func Tokenize(text string, dropStopwords bool) []string {
	fields := strings.Fields(Canonicalize(text))
	out := make([]string, 0, len(fields))
	for _, f := range fields {
		if dropStopwords {
			if _, skip := stopwords[f]; skip {
				continue
			}
		}
		out = append(out, f)
	}
	return out
}

// Fingerprint returns a stable SHA-1 hex digest for a canonical string.
func Fingerprint(canonical string) string {
	sum := sha1.Sum([]byte(canonical))
	return hex.EncodeToString(sum[:])
}

// Derive builds the full Signals bundle for a prompt.
func Derive(text string, dropStopwords bool) Signals {
	canonical := Canonicalize(text)
	tokens := Tokenize(text, dropStopwords)
	set := make(map[string]struct{}, len(tokens))
	for _, t := range tokens {
		set[t] = struct{}{}
	}
	return Signals{
		Canonical:   canonical,
		Tokens:      tokens,
		TokenSet:    set,
		Fingerprint: Fingerprint(canonical),
	}
}

// Jaccard returns the token-set similarity of two Signals in [0, 1].
func Jaccard(a, b map[string]struct{}) float64 {
	if len(a) == 0 && len(b) == 0 {
		return 1.0
	}
	inter := 0
	for k := range a {
		if _, ok := b[k]; ok {
			inter++
		}
	}
	union := len(a) + len(b) - inter
	if union == 0 {
		return 0.0
	}
	return float64(inter) / float64(union)
}
