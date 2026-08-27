package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"strings"
	"testing"
	"time"
)

func TestVerifyGitHubSignature(t *testing.T) {
	secret := strings.Repeat("s", 32)
	body := []byte(`{"repository":{"full_name":"acme/noping"}}`)
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write(body)
	signature := "sha256=" + hex.EncodeToString(mac.Sum(nil))
	if !verifyGitHubSignature(secret, signature, body) {
		t.Fatal("valid GitHub signature was rejected")
	}
	if verifyGitHubSignature(secret, signature, append(body, ' ')) {
		t.Fatal("modified GitHub payload must be rejected")
	}
}

func TestNormalizeGitHubReviewUsesConfiguredIdentityAndEntities(t *testing.T) {
	body := []byte(`{
		"action":"submitted",
		"sender":{"login":"octocat"},
		"repository":{"full_name":"acme/noping","html_url":"https://github.com/acme/noping"},
		"pull_request":{"number":42,"title":"AUTH-392 finalize Atlas auth","html_url":"https://github.com/acme/noping/pull/42","updated_at":"2026-08-27T20:00:00Z"},
		"review":{"state":"approved","html_url":"https://github.com/acme/noping/pull/42#review","submitted_at":"2026-08-27T20:05:00Z"}
	}`)
	config := &configuration{
		GitHubIdentityMap:   `{"octocat":"daniel"}`,
		GitHubRepositoryMap: `{"acme/noping":["atlas"]}`,
	}
	event, err := normalizeGitHubWebhook("pull_request_review", "delivery-1", body, config, time.Unix(0, 0))
	if err != nil {
		t.Fatal(err)
	}
	if event.ID != "github:delivery-1" || event.EventType != "pull_request.reviewed" || event.ActorUserID != "daniel" {
		t.Fatalf("unexpected normalized event: %#v", event)
	}
	wantEntities := []string{"acme/noping", "atlas", "auth-392"}
	if strings.Join(event.EntityIDs, ",") != strings.Join(wantEntities, ",") {
		t.Fatalf("entities=%v want=%v", event.EntityIDs, wantEntities)
	}
	if event.Payload["review_state"] != "approved" || event.Payload["number"] != 42 {
		t.Fatalf("unexpected normalized payload: %#v", event.Payload)
	}
}

func TestNormalizeGitHubWebhookRejectsUnmappedActor(t *testing.T) {
	body := []byte(`{"ref":"refs/heads/main","sender":{"login":"unknown"},"repository":{"full_name":"acme/noping"},"commits":[]}`)
	_, err := normalizeGitHubWebhook("push", "delivery-2", body, &configuration{GitHubIdentityMap: `{}`}, time.Now())
	if err == nil || !strings.Contains(err.Error(), "no NoPing identity mapping") {
		t.Fatalf("expected unmapped identity error, got %v", err)
	}
}
