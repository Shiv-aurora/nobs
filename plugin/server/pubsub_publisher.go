package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/shiv-aurora/noping/plugin/internal/googleidentity"
)

type accessTokenProvider interface {
	Token(context.Context) (string, error)
}

type workEventPublisher interface {
	Publish(context.Context, workEvent) error
}

type pubSubPublisher struct {
	endpoint string
	tokens   accessTokenProvider
	client   *http.Client
}

func newPubSubPublisher(projectID, topic string) (*pubSubPublisher, error) {
	projectID = strings.TrimSpace(projectID)
	topic = strings.TrimSpace(topic)
	if projectID == "" || topic == "" {
		return nil, errors.New("GoogleCloudProject and PubSubTopic are required for connector events")
	}
	return &pubSubPublisher{
		endpoint: fmt.Sprintf(
			"https://pubsub.googleapis.com/v1/projects/%s/topics/%s:publish",
			url.PathEscape(projectID),
			url.PathEscape(topic),
		),
		tokens: googleidentity.NewAccessTokenProvider(),
		client: &http.Client{Timeout: 10 * time.Second},
	}, nil
}

func (p *pubSubPublisher) Publish(ctx context.Context, event workEvent) error {
	eventJSON, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("encode work event: %w", err)
	}
	body, err := json.Marshal(map[string]any{
		"messages": []map[string]string{{"data": base64.StdEncoding.EncodeToString(eventJSON)}},
	})
	if err != nil {
		return fmt.Errorf("encode Pub/Sub request: %w", err)
	}
	token, err := p.tokens.Token(ctx)
	if err != nil {
		return fmt.Errorf("obtain VM service identity token: %w", err)
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, p.endpoint, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("create Pub/Sub request: %w", err)
	}
	request.Header.Set("Authorization", "Bearer "+token)
	request.Header.Set("Content-Type", "application/json")
	response, err := p.client.Do(request)
	if err != nil {
		return fmt.Errorf("publish work event: %w", err)
	}
	defer response.Body.Close()
	responseBody, _ := io.ReadAll(io.LimitReader(response.Body, 16*1024))
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return fmt.Errorf("Pub/Sub returned %s: %s", response.Status, strings.TrimSpace(string(responseBody)))
	}
	return nil
}
