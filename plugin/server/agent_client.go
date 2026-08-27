package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/shiv-aurora/noping/plugin/internal/signing"
)

var errAgentUnavailable = errors.New("NoPing agent service unavailable")

type agentClient struct {
	baseURL string
	secret  []byte
	client  *http.Client
}

func newAgentClient(baseURL, secret string) (*agentClient, error) {
	baseURL = strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if baseURL == "" {
		return nil, errors.New("agent service URL is empty")
	}
	parsed, err := url.Parse(baseURL)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return nil, fmt.Errorf("invalid agent service URL: %q", baseURL)
	}
	return &agentClient{
		baseURL: baseURL,
		secret:  []byte(secret),
		client: &http.Client{
			Timeout: 125 * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:        10,
				MaxIdleConnsPerHost: 4,
				IdleConnTimeout:     30 * time.Second,
			},
		},
	}, nil
}

func (c *agentClient) sign(timestamp, method, target string, body []byte) string {
	return signing.Sign(string(c.secret), timestamp, method, target, body)
}

func (c *agentClient) do(ctx context.Context, method, path string, body any) ([]byte, int, http.Header, error) {
	var payload []byte
	var err error
	if body != nil {
		payload, err = json.Marshal(body)
		if err != nil {
			return nil, 0, nil, fmt.Errorf("marshal request: %w", err)
		}
	}
	request, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, bytes.NewReader(payload))
	if err != nil {
		return nil, 0, nil, fmt.Errorf("create request: %w", err)
	}
	request.Header.Set("Content-Type", "application/json")
	timestamp := strconv.FormatInt(time.Now().Unix(), 10)
	request.Header.Set("X-NoPing-Timestamp", timestamp)
	request.Header.Set("X-NoPing-Signature-Version", signing.Version)
	request.Header.Set("X-NoPing-Signature", c.sign(timestamp, method, path, payload))

	response, err := c.client.Do(request)
	if err != nil {
		return nil, 0, nil, fmt.Errorf("%w: %v", errAgentUnavailable, err)
	}
	defer response.Body.Close()
	responseBody, err := io.ReadAll(io.LimitReader(response.Body, 2*1024*1024))
	if err != nil {
		return nil, response.StatusCode, response.Header, fmt.Errorf("read agent response: %w", err)
	}
	return responseBody, response.StatusCode, response.Header, nil
}
