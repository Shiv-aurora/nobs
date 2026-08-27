package signing

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"strings"
)

const Version = "v1"

// CanonicalMessage binds a request signature to its timestamp, HTTP method,
// exact request target (path + query), and body. This prevents a valid signed
// body from being replayed against another NoPing endpoint.
func CanonicalMessage(timestamp, method, target string, body []byte) []byte {
	prefix := Version + "\n" + timestamp + "\n" + strings.ToUpper(method) + "\n" + target + "\n"
	message := make([]byte, 0, len(prefix)+len(body))
	message = append(message, []byte(prefix)...)
	return append(message, body...)
}

func Sign(secret, timestamp, method, target string, body []byte) string {
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write(CanonicalMessage(timestamp, method, target, body))
	return hex.EncodeToString(mac.Sum(nil))
}
