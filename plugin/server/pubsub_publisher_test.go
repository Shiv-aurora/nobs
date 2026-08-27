package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
)

type staticAccessToken string

func (token staticAccessToken) Token(context.Context) (string, error) {
	return string(token), nil
}

func TestPubSubPublisherUsesServiceIdentityAndNormalizedEnvelope(t *testing.T) {
	var published workEvent
	transport := publisherRoundTripFunc(func(r *http.Request) (*http.Response, error) {
		if r.Header.Get("Authorization") != "Bearer vm-token" {
			t.Fatal("publisher did not use VM access token")
		}
		var request struct {
			Messages []struct {
				Data string `json:"data"`
			} `json:"messages"`
		}
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			t.Fatal(err)
		}
		raw, err := base64.StdEncoding.DecodeString(request.Messages[0].Data)
		if err != nil {
			t.Fatal(err)
		}
		if err := json.Unmarshal(raw, &published); err != nil {
			t.Fatal(err)
		}
		return &http.Response{
			StatusCode: http.StatusOK,
			Status:     "200 OK",
			Header:     make(http.Header),
			Body:       io.NopCloser(strings.NewReader(`{"messageIds":["1"]}`)),
			Request:    r,
		}, nil
	})

	publisher := &pubSubPublisher{
		endpoint: "https://pubsub.googleapis.test/v1/projects/test/topics/events:publish",
		tokens:   staticAccessToken("vm-token"),
		client:   &http.Client{Transport: transport},
	}
	want := workEvent{
		ID:          "github:1",
		Source:      "github",
		EventType:   "repository.pushed",
		ActorUserID: "maya",
		EntityIDs:   []string{"atlas"},
		OccurredAt:  time.Date(2026, 8, 27, 20, 0, 0, 0, time.UTC),
		Payload:     map[string]any{"ref": "refs/heads/main"},
	}
	if err := publisher.Publish(context.Background(), want); err != nil {
		t.Fatal(err)
	}
	if published.ID != want.ID || published.ActorUserID != want.ActorUserID || published.EventType != want.EventType {
		t.Fatalf("published=%#v want=%#v", published, want)
	}
}

type publisherRoundTripFunc func(*http.Request) (*http.Response, error)

func (fn publisherRoundTripFunc) RoundTrip(request *http.Request) (*http.Response, error) {
	return fn(request)
}
