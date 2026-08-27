package domain

import (
	"regexp"
	"strings"
)

var restrictedTerms = regexp.MustCompile(`(?i)\b(salary|compensation|ssn|medical record|home address)\b`)

func IsRestrictedQuery(text string) bool {
	return restrictedTerms.MatchString(text)
}

func CanonicalDecisionKey(text string) string {
	lowered := strings.ToLower(text)
	if strings.Contains(lowered, "atlas") && (strings.Contains(lowered, "security") || strings.Contains(lowered, "exception") || strings.Contains(lowered, "bypass")) {
		return "atlas_security_exception"
	}
	return strings.Join(strings.Fields(lowered), "_")
}
