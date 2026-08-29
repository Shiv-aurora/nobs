package main

import (
	"bufio"
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

	"github.com/shiv-aurora/noping/plugin/internal/googleidentity"
	"github.com/shiv-aurora/noping/plugin/internal/signing"
)

var errAgentUnavailable = errors.New("NoBS agent service unavailable")

type tokenProvider interface {
	Token(context.Context) (string, error)
}

type agentClient struct {
	baseURL       string
	secret        []byte
	client        *http.Client
	tokenProvider tokenProvider
}

func newAgentClient(baseURL, secret string, useGoogleIdentity bool, cloudRunAudience string) (*agentClient, error) {
	baseURL = strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if baseURL == "" {
		return nil, errors.New("agent service URL is empty")
	}
	parsed, err := url.Parse(baseURL)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return nil, fmt.Errorf("invalid agent service URL: %q", baseURL)
	}
	var provider tokenProvider
	if useGoogleIdentity {
		provider, err = googleidentity.New(cloudRunAudience)
		if err != nil {
			return nil, err
		}
	}
	return &agentClient{
		baseURL:       baseURL,
		secret:        []byte(secret),
		tokenProvider: provider,
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
	if c.tokenProvider != nil {
		token, tokenErr := c.tokenProvider.Token(ctx)
		if tokenErr != nil {
			return nil, 0, nil, fmt.Errorf("obtain Google service identity: %w", tokenErr)
		}
		request.Header.Set("Authorization", "Bearer "+token)
	}
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

func (c *agentClient) streamQuery(ctx context.Context, query queryRequest, onEvent func(queryStreamEvent)) (*channelAgentResult, int, http.Header, error) {
	payload, err := json.Marshal(query)
	if err != nil {
		return nil, 0, nil, fmt.Errorf("marshal request: %w", err)
	}
	const path = "/v1/query/stream"
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+path, bytes.NewReader(payload))
	if err != nil {
		return nil, 0, nil, fmt.Errorf("create request: %w", err)
	}
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Accept", "application/x-ndjson")
	if c.tokenProvider != nil {
		token, tokenErr := c.tokenProvider.Token(ctx)
		if tokenErr != nil {
			return nil, 0, nil, fmt.Errorf("obtain Google service identity: %w", tokenErr)
		}
		request.Header.Set("Authorization", "Bearer "+token)
	}
	timestamp := strconv.FormatInt(time.Now().Unix(), 10)
	request.Header.Set("X-NoPing-Timestamp", timestamp)
	request.Header.Set("X-NoPing-Signature-Version", signing.Version)
	request.Header.Set("X-NoPing-Signature", c.sign(timestamp, http.MethodPost, path, payload))
	response, err := c.client.Do(request)
	if err != nil {
		return nil, 0, nil, fmt.Errorf("%w: %v", errAgentUnavailable, err)
	}
	defer response.Body.Close()
	if response.StatusCode >= http.StatusMultipleChoices {
		body, readErr := io.ReadAll(io.LimitReader(response.Body, 2*1024*1024))
		if readErr != nil {
			return nil, response.StatusCode, response.Header, readErr
		}
		return nil, response.StatusCode, response.Header, fmt.Errorf("agent stream rejected: %s", strings.TrimSpace(string(body)))
	}
	var result channelAgentResult
	foundResult := false
	scanner := bufio.NewScanner(io.LimitReader(response.Body, 4*1024*1024))
	scanner.Buffer(make([]byte, 64*1024), 2*1024*1024)
	for scanner.Scan() {
		var event queryStreamEvent
		if err := json.Unmarshal(scanner.Bytes(), &event); err != nil {
			return nil, response.StatusCode, response.Header, fmt.Errorf("decode agent stream: %w", err)
		}
		if onEvent != nil {
			onEvent(event)
		}
		if event.Event == "completed" {
			var completed struct {
				Result channelAgentResult `json:"result"`
			}
			if err := json.Unmarshal(event.Data, &completed); err != nil {
				return nil, response.StatusCode, response.Header, fmt.Errorf("decode completed result: %w", err)
			}
			result = completed.Result
			foundResult = true
		}
		if event.Event == "failed" {
			return nil, response.StatusCode, response.Header, errors.New("agent stream failed")
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, response.StatusCode, response.Header, fmt.Errorf("read agent stream: %w", err)
	}
	if !foundResult {
		return nil, response.StatusCode, response.Header, errors.New("agent stream ended without a result")
	}
	return &result, response.StatusCode, response.Header, nil
}

func (c *agentClient) resolveDelegation(ctx context.Context, request delegationResolutionRequest) (*delegationResolution, error) {
	payload, statusCode, _, err := c.do(ctx, http.MethodPost, "/v1/delegation/resolve", request)
	if err != nil {
		return nil, err
	}
	if statusCode >= http.StatusMultipleChoices {
		return nil, fmt.Errorf("delegation preflight rejected with status %d", statusCode)
	}
	var result delegationResolution
	if err := json.Unmarshal(payload, &result); err != nil {
		return nil, fmt.Errorf("decode delegation preflight: %w", err)
	}
	return &result, nil
}
