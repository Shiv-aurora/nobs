package main

import (
	"net/http"
	"strings"
)

const mattermostUserIDHeader = "Mattermost-User-ID"

func authenticatedUserID(r *http.Request) string {
	return strings.TrimSpace(r.Header.Get(mattermostUserIDHeader))
}

func (p *Plugin) requireUser(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if authenticatedUserID(r) == "" {
			writeJSONError(w, http.StatusUnauthorized, "Authentication required")
			return
		}
		next.ServeHTTP(w, r)
	})
}
