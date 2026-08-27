package main

import (
	"errors"
	"net/http"
	"strings"
)

const mattermostUserIDHeader = "Mattermost-User-ID"

func authenticatedUserID(r *http.Request) string {
	return strings.TrimSpace(r.Header.Get(mattermostUserIDHeader))
}

// authenticatedActorKey converts Mattermost's opaque user ID into the stable,
// server-verified username used by NoPing's organizational identity graph. The
// browser never supplies or overrides this mapping.
func (p *Plugin) authenticatedActorKey(r *http.Request) (string, error) {
	userID := authenticatedUserID(r)
	if userID == "" {
		return "", errors.New("authentication required")
	}
	user, appErr := p.API.GetUser(userID)
	if appErr != nil || user == nil || strings.TrimSpace(user.Username) == "" {
		return "", errors.New("authenticated Mattermost identity could not be resolved")
	}
	return strings.ToLower(strings.TrimSpace(user.Username)), nil
}

func (p *Plugin) actorKeyOrError(w http.ResponseWriter, r *http.Request) (string, bool) {
	actorKey, err := p.authenticatedActorKey(r)
	if err != nil {
		writeJSONError(w, http.StatusUnauthorized, err.Error())
		return "", false
	}
	return actorKey, true
}

func (p *Plugin) userIDForActorKey(actorKey string) string {
	user, appErr := p.API.GetUserByUsername(actorKey)
	if appErr != nil || user == nil {
		return ""
	}
	return user.Id
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
