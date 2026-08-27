package googleidentity

import (
	"context"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
)

func TestAccessTokenProviderCachesMetadataToken(t *testing.T) {
	calls := 0
	transport := roundTripFunc(func(r *http.Request) (*http.Response, error) {
		calls++
		if r.Header.Get("Metadata-Flavor") != "Google" {
			t.Fatal("metadata request must set Metadata-Flavor")
		}
		return &http.Response{
			StatusCode: http.StatusOK,
			Status:     "200 OK",
			Header:     make(http.Header),
			Body:       io.NopCloser(strings.NewReader(`{"access_token":"short-lived","expires_in":3600}`)),
			Request:    r,
		}, nil
	})

	provider := NewAccessTokenProvider()
	provider.client = &http.Client{Transport: transport}
	provider.now = func() time.Time { return time.Unix(1_800_000_000, 0) }
	first, err := provider.Token(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	second, err := provider.Token(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if first != "short-lived" || second != first || calls != 1 {
		t.Fatalf("unexpected cache result: first=%q second=%q calls=%d", first, second, calls)
	}
}

type roundTripFunc func(*http.Request) (*http.Response, error)

func (fn roundTripFunc) RoundTrip(request *http.Request) (*http.Response, error) {
	return fn(request)
}
