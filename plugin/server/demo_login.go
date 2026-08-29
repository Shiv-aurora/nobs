package main

import (
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/mattermost/mattermost/server/public/model"
)

const demoSessionDuration = 12 * time.Hour

func (p *Plugin) handleDemoLogin(w http.ResponseWriter, r *http.Request) {
	config := p.getConfiguration()
	if !config.PublicDemoLogin {
		http.NotFound(w, r)
		return
	}
	if !isSameOriginFormPost(r) {
		writeJSONError(w, http.StatusForbidden, "Demo login requires a same-origin request")
		return
	}

	user, appErr := p.API.GetUserByUsername(config.DemoLoginUsername)
	if appErr != nil || user == nil || user.DeleteAt != 0 || user.IsBot || user.IsSystemAdmin() {
		writeJSONError(w, http.StatusForbidden, "The configured demo user is unavailable")
		return
	}

	expiresAt := model.GetMillis() + demoSessionDuration.Milliseconds()
	session, appErr := p.API.CreateSession(&model.Session{
		UserId:    user.Id,
		Roles:     user.Roles,
		ExpiresAt: expiresAt,
		Props: model.StringMap{
			model.SessionPropType: "nobs_public_demo",
		},
	})
	if appErr != nil || session == nil || session.Token == "" {
		p.API.LogError("NoBS could not create a public demo session")
		writeJSONError(w, http.StatusServiceUnavailable, "The demo workspace is temporarily unavailable")
		return
	}

	secure := r.TLS != nil || strings.EqualFold(firstForwardedValue(r.Header.Get("X-Forwarded-Proto")), "https")
	expires := time.Now().Add(demoSessionDuration)
	http.SetCookie(w, &http.Cookie{
		Name:     model.SessionCookieToken,
		Value:    session.Token,
		Path:     "/",
		Expires:  expires,
		MaxAge:   int(demoSessionDuration.Seconds()),
		HttpOnly: true,
		Secure:   secure,
		SameSite: http.SameSiteLaxMode,
	})
	http.SetCookie(w, &http.Cookie{
		Name:     model.SessionCookieUser,
		Value:    user.Id,
		Path:     "/",
		Expires:  expires,
		MaxAge:   int(demoSessionDuration.Seconds()),
		HttpOnly: false,
		Secure:   secure,
		SameSite: http.SameSiteLaxMode,
	})
	w.Header().Set("Cache-Control", "no-store")
	http.Redirect(w, r, "/acme/channels/project-atlas", http.StatusSeeOther)
}

func isSameOriginFormPost(r *http.Request) bool {
	origin := strings.TrimSpace(r.Header.Get("Origin"))
	if origin == "" {
		return false
	}
	parsed, err := url.Parse(origin)
	if err != nil || parsed.Host == "" {
		return false
	}
	requestHost := firstForwardedValue(r.Header.Get("X-Forwarded-Host"))
	if requestHost == "" {
		requestHost = r.Host
	}
	return strings.EqualFold(parsed.Host, requestHost)
}

func firstForwardedValue(value string) string {
	return strings.TrimSpace(strings.Split(value, ",")[0])
}
