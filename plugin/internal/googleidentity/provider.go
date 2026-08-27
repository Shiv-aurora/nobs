package googleidentity

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

const metadataIdentityEndpoint = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"

type Provider struct {
	audience string
	client   *http.Client
	now      func() time.Time

	mu        sync.Mutex
	token     string
	expiresAt time.Time
}

func New(audience string) (*Provider, error) {
	audience = strings.TrimSpace(audience)
	if audience == "" {
		return nil, errors.New("Cloud Run audience is required")
	}
	return &Provider{
		audience: audience,
		client:   &http.Client{Timeout: 3 * time.Second},
		now:      time.Now,
	}, nil
}

func (p *Provider) Token(ctx context.Context) (string, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.token != "" && p.expiresAt.After(p.now().Add(90*time.Second)) {
		return p.token, nil
	}
	token, expiresAt, err := p.fetch(ctx)
	if err != nil {
		return "", err
	}
	p.token = token
	p.expiresAt = expiresAt
	return token, nil
}

func (p *Provider) fetch(ctx context.Context) (string, time.Time, error) {
	endpoint, _ := url.Parse(metadataIdentityEndpoint)
	query := endpoint.Query()
	query.Set("audience", p.audience)
	query.Set("format", "full")
	endpoint.RawQuery = query.Encode()
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint.String(), nil)
	if err != nil {
		return "", time.Time{}, fmt.Errorf("create metadata identity request: %w", err)
	}
	request.Header.Set("Metadata-Flavor", "Google")
	response, err := p.client.Do(request)
	if err != nil {
		return "", time.Time{}, fmt.Errorf("fetch Google identity token: %w", err)
	}
	defer response.Body.Close()
	body, err := io.ReadAll(io.LimitReader(response.Body, 16*1024))
	if err != nil {
		return "", time.Time{}, fmt.Errorf("read Google identity token: %w", err)
	}
	if response.StatusCode != http.StatusOK {
		return "", time.Time{}, fmt.Errorf("metadata identity endpoint returned %s", response.Status)
	}
	token := strings.TrimSpace(string(body))
	expiresAt, err := expiry(token)
	if err != nil {
		return "", time.Time{}, err
	}
	return token, expiresAt, nil
}

func expiry(token string) (time.Time, error) {
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return time.Time{}, errors.New("metadata identity response is not a JWT")
	}
	payload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return time.Time{}, errors.New("metadata identity JWT payload is invalid")
	}
	var claims struct {
		ExpiresAt int64 `json:"exp"`
	}
	if err := json.Unmarshal(payload, &claims); err != nil || claims.ExpiresAt <= 0 {
		return time.Time{}, errors.New("metadata identity JWT has no valid expiry")
	}
	return time.Unix(claims.ExpiresAt, 0), nil
}
