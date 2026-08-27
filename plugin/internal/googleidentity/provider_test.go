package googleidentity

import (
	"encoding/base64"
	"fmt"
	"testing"
	"time"
)

func jwtWithExpiry(exp int64) string {
	header := base64.RawURLEncoding.EncodeToString([]byte(`{"alg":"RS256"}`))
	payload := base64.RawURLEncoding.EncodeToString([]byte(fmt.Sprintf(`{"exp":%d}`, exp)))
	return header + "." + payload + ".signature"
}

func TestExpiry(t *testing.T) {
	want := time.Unix(2_000_000_000, 0)
	got, err := expiry(jwtWithExpiry(want.Unix()))
	if err != nil {
		t.Fatal(err)
	}
	if !got.Equal(want) {
		t.Fatalf("got %v want %v", got, want)
	}
}

func TestExpiryRejectsMalformedToken(t *testing.T) {
	if _, err := expiry("not-a-jwt"); err == nil {
		t.Fatal("expected error")
	}
}
