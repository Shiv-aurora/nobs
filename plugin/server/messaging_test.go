package main

import (
	"testing"

	"github.com/mattermost/mattermost/server/public/model"
)

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

func TestSeededDelegateDemo(t *testing.T) {
	post := &model.Post{Props: model.StringInterface{"nobs_seed_delegate_demo": "daniel-ooo"}}
	if got := seededDelegateDemo(post); got != "daniel-ooo" {
		t.Fatalf("got %q, want daniel-ooo", got)
	}
	if got := seededDelegateDemo(&model.Post{}); got != "" {
		t.Fatalf("empty props returned %q", got)
	}
}

func TestSeededDelegateRepliesCoverEveryJudgeDM(t *testing.T) {
	scenarios := []string{
		"daniel-ooo",
		"sarah-policy-boundary", "sarah-sensitive-refusal",
		"daniel-release-evidence", "daniel-human-merge",
		"priya-multi-status", "priya-calendar-owner",
		"alex-criteria", "alex-decision-boundary",
		"shivam-meeting-status", "shivam-calendar-boundary",
		"helen-privacy-boundary", "helen-sensitive-refusal",
	}
	for _, scenario := range scenarios {
		reply, ok := seededDelegateReplyFor(scenario)
		if !ok {
			t.Fatalf("missing seeded reply for %q", scenario)
		}
		if reply.representedUsername == "" || reply.message == "" || reply.route == "" || reply.agentsConsulted < 2 {
			t.Fatalf("incomplete seeded reply for %q: %#v", scenario, reply)
		}
		if reply.securityState != "allowed" && reply.securityState != "blocked" {
			t.Fatalf("invalid security state for %q: %q", scenario, reply.securityState)
		}
	}
	if _, ok := seededDelegateReplyFor("unknown-scenario"); ok {
		t.Fatal("unknown scenario unexpectedly resolved")
	}
}
