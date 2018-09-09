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

