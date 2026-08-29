package main

import "testing"

func TestParseHumanOnlyMessage(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		message string
		direct  bool
	}{
		{"leading token", "  --direct @sarah please call me", "@sarah please call me", true},
		{"token must be first", "hello --direct @sarah", "hello --direct @sarah", false},
		{"similar prefix", "--directly ask Sarah", "--directly ask Sarah", false},
		{"empty direct", "--direct  ", "", true},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			message, direct := parseHumanOnlyMessage(test.input)
			if message != test.message || direct != test.direct {
				t.Fatalf("got (%q, %v), want (%q, %v)", message, direct, test.message, test.direct)
			}
		})
	}
}

func TestMentionPatternExcludesEmailAddresses(t *testing.T) {
	matches := mentionPattern.FindAllStringSubmatch("email maya@example.com, ask @sarah and @channel", -1)
	if len(matches) != 2 || matches[0][1] != "sarah" || matches[1][1] != "channel" {
		t.Fatalf("unexpected mentions: %#v", matches)
	}
}
