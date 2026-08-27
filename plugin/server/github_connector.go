package main

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"sort"
	"strings"
	"time"
)

const maxGitHubWebhookBytes int64 = 1024 * 1024

var workItemReference = regexp.MustCompile(`\b[A-Z][A-Z0-9]+-\d+\b`)

type githubWebhook struct {
	Action string `json:"action"`
	Ref    string `json:"ref"`
	Sender struct {
		Login string `json:"login"`
	} `json:"sender"`
	Repository struct {
		FullName string `json:"full_name"`
		HTMLURL  string `json:"html_url"`
	} `json:"repository"`
	PullRequest *struct {
		Number    int       `json:"number"`
		Title     string    `json:"title"`
		HTMLURL   string    `json:"html_url"`
		UpdatedAt time.Time `json:"updated_at"`
		Merged    bool      `json:"merged"`
		Draft     bool      `json:"draft"`
	} `json:"pull_request"`
	Review *struct {
		State       string    `json:"state"`
		HTMLURL     string    `json:"html_url"`
		SubmittedAt time.Time `json:"submitted_at"`
	} `json:"review"`
	HeadCommit *struct {
		ID        string    `json:"id"`
		Timestamp time.Time `json:"timestamp"`
		URL       string    `json:"url"`
	} `json:"head_commit"`
	Commits []json.RawMessage `json:"commits"`
}

func verifyGitHubSignature(secret, signature string, body []byte) bool {
	if secret == "" || !strings.HasPrefix(signature, "sha256=") {
		return false
	}
	provided, err := hex.DecodeString(strings.TrimPrefix(signature, "sha256="))
	if err != nil {
		return false
	}
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write(body)
	return hmac.Equal(mac.Sum(nil), provided)
}

func parseIdentityMap(raw string) (map[string]string, error) {
	values := map[string]string{}
	if err := json.Unmarshal([]byte(raw), &values); err != nil {
		return nil, errors.New("GitHubIdentityMap must be a JSON object")
	}
	normalized := make(map[string]string, len(values))
	for login, actorID := range values {
		login = strings.ToLower(strings.TrimSpace(login))
		actorID = strings.TrimSpace(actorID)
		if login != "" && actorID != "" {
			normalized[login] = actorID
		}
	}
	return normalized, nil
}

func parseRepositoryMap(raw string) (map[string][]string, error) {
	if strings.TrimSpace(raw) == "" {
		return map[string][]string{}, nil
	}
	values := map[string][]string{}
	if err := json.Unmarshal([]byte(raw), &values); err != nil {
		return nil, errors.New("GitHubRepositoryMap must map repository names to entity ID arrays")
	}
	return values, nil
}

func normalizeGitHubWebhook(eventName, deliveryID string, body []byte, config *configuration, now time.Time) (workEvent, error) {
	var payload githubWebhook
	if err := json.Unmarshal(body, &payload); err != nil {
		return workEvent{}, errors.New("GitHub webhook body is invalid JSON")
	}
	if strings.TrimSpace(deliveryID) == "" || strings.TrimSpace(payload.Repository.FullName) == "" {
		return workEvent{}, errors.New("GitHub delivery and repository identity are required")
	}
	identities, err := parseIdentityMap(config.GitHubIdentityMap)
	if err != nil {
		return workEvent{}, err
	}
	actorID := identities[strings.ToLower(strings.TrimSpace(payload.Sender.Login))]
	if actorID == "" {
		return workEvent{}, fmt.Errorf("GitHub actor %q has no NoPing identity mapping", payload.Sender.Login)
	}
	repositories, err := parseRepositoryMap(config.GitHubRepositoryMap)
	if err != nil {
		return workEvent{}, err
	}
	entitySet := map[string]struct{}{strings.ToLower(payload.Repository.FullName): {}}
	for _, entityID := range repositories[payload.Repository.FullName] {
		if entityID = strings.TrimSpace(entityID); entityID != "" {
			entitySet[entityID] = struct{}{}
		}
	}

	eventType := ""
	occurredAt := now.UTC()
	eventPayload := map[string]any{"repository": payload.Repository.FullName}
	switch eventName {
	case "push":
		eventType = "repository.pushed"
		eventPayload["ref"] = payload.Ref
		eventPayload["commit_count"] = len(payload.Commits)
		if payload.HeadCommit != nil {
			eventPayload["commit"] = payload.HeadCommit.ID
			eventPayload["source_url"] = payload.HeadCommit.URL
			if !payload.HeadCommit.Timestamp.IsZero() {
				occurredAt = payload.HeadCommit.Timestamp
			}
		}
	case "pull_request", "pull_request_review":
		if payload.PullRequest == nil || payload.PullRequest.Number <= 0 {
			return workEvent{}, errors.New("GitHub pull request payload is incomplete")
		}
		action := strings.ToLower(strings.TrimSpace(payload.Action))
		if eventName == "pull_request_review" {
			eventType = "pull_request.reviewed"
			if payload.Review == nil {
				return workEvent{}, errors.New("GitHub review payload is incomplete")
			}
			eventPayload["review_state"] = strings.ToLower(payload.Review.State)
			eventPayload["source_url"] = payload.Review.HTMLURL
			if !payload.Review.SubmittedAt.IsZero() {
				occurredAt = payload.Review.SubmittedAt
			}
		} else {
			if action == "closed" && payload.PullRequest.Merged {
				action = "merged"
			}
			if action == "" {
				return workEvent{}, errors.New("GitHub pull request action is required")
			}
			eventType = "pull_request." + action
			eventPayload["review_state"] = action
			eventPayload["source_url"] = payload.PullRequest.HTMLURL
			if !payload.PullRequest.UpdatedAt.IsZero() {
				occurredAt = payload.PullRequest.UpdatedAt
			}
		}
		eventPayload["number"] = payload.PullRequest.Number
		eventPayload["draft"] = payload.PullRequest.Draft
		for _, reference := range workItemReference.FindAllString(payload.PullRequest.Title, -1) {
			entitySet[strings.ToLower(reference)] = struct{}{}
		}
	default:
		return workEvent{}, fmt.Errorf("unsupported GitHub event %q", eventName)
	}

	entityIDs := make([]string, 0, len(entitySet))
	for entityID := range entitySet {
		entityIDs = append(entityIDs, entityID)
	}
	sort.Strings(entityIDs)
	return workEvent{
		ID:          "github:" + deliveryID,
		Source:      "github",
		EventType:   eventType,
		ActorUserID: actorID,
		EntityIDs:   entityIDs,
		OccurredAt:  occurredAt,
		Payload:     eventPayload,
	}, nil
}

func (p *Plugin) githubPublisher(config *configuration) (workEventPublisher, error) {
	return newPubSubPublisher(config.GoogleCloudProject, config.PubSubTopic)
}

func (p *Plugin) handleGitHubWebhook(w http.ResponseWriter, r *http.Request) {
	config := p.getConfiguration()
	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, maxGitHubWebhookBytes))
	if err != nil {
		writeJSONError(w, http.StatusRequestEntityTooLarge, "GitHub webhook body exceeds the configured limit")
		return
	}
	if !verifyGitHubSignature(config.GitHubWebhookSecret, r.Header.Get("X-Hub-Signature-256"), body) {
		writeJSONError(w, http.StatusUnauthorized, "Invalid GitHub webhook signature")
		return
	}
	if r.Header.Get("X-GitHub-Event") == "ping" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusAccepted)
		_, _ = w.Write([]byte(`{"accepted":true,"event":"ping"}`))
		return
	}
	event, err := normalizeGitHubWebhook(
		r.Header.Get("X-GitHub-Event"),
		r.Header.Get("X-GitHub-Delivery"),
		body,
		config,
		time.Now(),
	)
	if err != nil {
		writeJSONError(w, http.StatusUnprocessableEntity, err.Error())
		return
	}
	publisher, err := p.githubPublisher(config)
	if err != nil {
		writeJSONError(w, http.StatusServiceUnavailable, err.Error())
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 12*time.Second)
	defer cancel()
	if err := publisher.Publish(ctx, event); err != nil {
		p.API.LogError("NoPing GitHub event publish failed", "delivery_id", event.ID, "error", err.Error())
		writeJSONError(w, http.StatusServiceUnavailable, "GitHub event could not be queued")
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusAccepted)
	_ = json.NewEncoder(w).Encode(map[string]any{"accepted": true, "event_id": event.ID})
}
