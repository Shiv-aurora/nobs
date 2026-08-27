package signing

import "testing"

func TestSignatureContract(t *testing.T) {
	got := Sign("shared-test-secret", "1787850000", "POST", "/v1/query?trace=true", []byte(`{"requester_id":"maya","text":"Why is Atlas delayed?"}`))
	want := "4f795a00c16e608dd833fc09f09a59b23cc7b4335868a9f69263df73b3d7575b"
	if got != want {
		t.Fatalf("signature mismatch: got %s", got)
	}
}

func TestSignatureBindsTarget(t *testing.T) {
	body := []byte(`{"ok":true}`)
	first := Sign("secret", "123", "POST", "/v1/query", body)
	second := Sign("secret", "123", "POST", "/v1/events", body)
	if first == second {
		t.Fatal("signatures must differ across request targets")
	}
}
