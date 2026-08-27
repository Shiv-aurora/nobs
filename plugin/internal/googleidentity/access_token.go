package googleidentity

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"
)

const metadataAccessTokenEndpoint = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"

// AccessTokenProvider obtains short-lived OAuth access tokens from the Compute
// Engine metadata server. It never stores a service-account key on disk.
type AccessTokenProvider struct {
	client *http.Client
	now    func() time.Time

	mu        sync.Mutex
	token     string
	expiresAt time.Time
}

func NewAccessTokenProvider() *AccessTokenProvider {
	return &AccessTokenProvider{
		client: &http.Client{Timeout: 3 * time.Second},
		now:    time.Now,
	}
}

func (p *AccessTokenProvider) Token(ctx context.Context) (string, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.token != "" && p.expiresAt.After(p.now().Add(90*time.Second)) {
		return p.token, nil
	}

	request, err := http.NewRequestWithContext(ctx, http.MethodGet, metadataAccessTokenEndpoint, nil)
	if err != nil {
		return "", fmt.Errorf("create metadata access-token request: %w", err)
	}
	request.Header.Set("Metadata-Flavor", "Google")
	response, err := p.client.Do(request)
	if err != nil {
		return "", fmt.Errorf("fetch Google access token: %w", err)
	}
	defer response.Body.Close()
	body, err := io.ReadAll(io.LimitReader(response.Body, 16*1024))
	if err != nil {
		return "", fmt.Errorf("read Google access token: %w", err)
	}
	if response.StatusCode != http.StatusOK {
		return "", fmt.Errorf("metadata access-token endpoint returned %s", response.Status)
	}
	var payload struct {
		AccessToken string `json:"access_token"`
		ExpiresIn   int64  `json:"expires_in"`
	}
	if err := json.Unmarshal(body, &payload); err != nil {
		return "", errors.New("metadata access-token response is invalid JSON")
	}
	if payload.AccessToken == "" || payload.ExpiresIn <= 0 {
		return "", errors.New("metadata access-token response is incomplete")
	}
	p.token = payload.AccessToken
	p.expiresAt = p.now().Add(time.Duration(payload.ExpiresIn) * time.Second)
	return p.token, nil
}
