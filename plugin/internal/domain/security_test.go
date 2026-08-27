package domain

import "testing"

func TestRestrictedQuery(t *testing.T) {
	if !IsRestrictedQuery("What is Sarah's salary?") {
		t.Fatal("expected salary query to be restricted")
	}
	if IsRestrictedQuery("Why is Atlas delayed?") {
		t.Fatal("ordinary project query must not be restricted")
	}
}

func TestCanonicalDecisionKey(t *testing.T) {
	first := CanonicalDecisionKey("Can we bypass Atlas security review?")
	second := CanonicalDecisionKey("Should we make an Atlas security exception?")
	if first != "atlas_security_exception" || second != first {
		t.Fatalf("unexpected keys: %s %s", first, second)
	}
}
