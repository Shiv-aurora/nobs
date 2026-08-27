package main

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/gorilla/mux"
	"github.com/mattermost/mattermost/server/public/plugin"
)

func (p *Plugin) initRouter() *mux.Router {
	router := mux.NewRouter()
	api := router.PathPrefix("/api/v1").Subrouter()
	api.Use(p.requireUser)
	api.HandleFunc("/health", p.handleHealth).Methods(http.MethodGet)
	api.HandleFunc("/bootstrap", p.handleBootstrap).Methods(http.MethodGet)
	api.HandleFunc("/query", p.handleQuery).Methods(http.MethodPost)
	api.HandleFunc("/runs/{runID}", p.handleRun).Methods(http.MethodGet)
	api.HandleFunc("/decisions", p.handleDecisions).Methods(http.MethodGet)
	api.HandleFunc("/decisions/{decisionID}/resolve", p.handleResolveDecision).Methods(http.MethodPost)
	api.HandleFunc("/registry", p.handleRegistry).Methods(http.MethodGet)
	api.HandleFunc("/audit", p.handleAudit).Methods(http.MethodGet)
	api.HandleFunc("/demo/reset", p.handleDemoReset).Methods(http.MethodPost)
	return router
}

func (p *Plugin) ServeHTTP(_ *plugin.Context, w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	p.router.ServeHTTP(w, r)
}

func (p *Plugin) currentAgentClient() (*agentClient, error) {
	config := p.getConfiguration()
	return newAgentClient(config.AgentServiceURL, config.ServiceSigningSecret)
}

func (p *Plugin) proxy(w http.ResponseWriter, r *http.Request, method, path string, body any) {
	client, err := p.currentAgentClient()
	if err != nil {
		writeJSONError(w, http.StatusServiceUnavailable, err.Error())
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()
	payload, statusCode, headers, err := client.do(ctx, method, path, body)
	if err != nil {
		p.API.LogError("NoPing agent request failed", "path", path, "error", err.Error())
		writeJSONError(w, http.StatusServiceUnavailable, "The organizational agent service is temporarily unavailable.")
		return
	}
	if retryAfter := headers.Get("Retry-After"); retryAfter != "" {
		w.Header().Set("Retry-After", retryAfter)
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_, _ = w.Write(payload)
}

func (p *Plugin) handleHealth(w http.ResponseWriter, r *http.Request) {
	p.proxy(w, r, http.MethodGet, "/healthz", nil)
}

func (p *Plugin) handleBootstrap(w http.ResponseWriter, r *http.Request) {
	query := url.Values{}
	query.Set("user_id", authenticatedUserID(r))
	p.proxy(w, r, http.MethodGet, "/v1/bootstrap?"+query.Encode(), nil)
}

func (p *Plugin) handleQuery(w http.ResponseWriter, r *http.Request) {
	var request queryRequest
	if err := decodeJSON(r, &request); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	request.RequesterID = authenticatedUserID(r)
	if request.TeamID == "" {
		request.TeamID = strings.TrimSpace(r.URL.Query().Get("team_id"))
	}
	if len(strings.TrimSpace(request.Text)) < 3 {
		writeJSONError(w, http.StatusBadRequest, "Query must be at least 3 characters")
		return
	}
	p.proxy(w, r, http.MethodPost, "/v1/query", request)
}

func (p *Plugin) handleRun(w http.ResponseWriter, r *http.Request) {
	runID := url.PathEscape(mux.Vars(r)["runID"])
	p.proxy(w, r, http.MethodGet, "/v1/runs/"+runID, nil)
}

func (p *Plugin) handleDecisions(w http.ResponseWriter, r *http.Request) {
	query := url.Values{}
	query.Set("assignee_id", authenticatedUserID(r))
	p.proxy(w, r, http.MethodGet, "/v1/decisions?"+query.Encode(), nil)
}

func (p *Plugin) handleResolveDecision(w http.ResponseWriter, r *http.Request) {
	var resolution decisionResolution
	if err := decodeJSON(r, &resolution); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	resolution.ActorID = authenticatedUserID(r)
	if resolution.Status != "approved" && resolution.Status != "rejected" && resolution.Status != "discuss" {
		writeJSONError(w, http.StatusBadRequest, "Invalid decision status")
		return
	}
	if len(strings.TrimSpace(resolution.Rationale)) < 2 {
		writeJSONError(w, http.StatusBadRequest, "Rationale is required")
		return
	}
	decisionID := url.PathEscape(mux.Vars(r)["decisionID"])
	p.proxy(w, r, http.MethodPost, "/v1/decisions/"+decisionID+"/resolve", resolution)
}

func (p *Plugin) handleRegistry(w http.ResponseWriter, r *http.Request) {
	p.proxy(w, r, http.MethodGet, "/v1/registry", nil)
}

func (p *Plugin) handleAudit(w http.ResponseWriter, r *http.Request) {
	limit := r.URL.Query().Get("limit")
	path := "/v1/audit"
	if limit != "" {
		query := url.Values{}
		query.Set("limit", limit)
		path += "?" + query.Encode()
	}
	p.proxy(w, r, http.MethodGet, path, nil)
}

func (p *Plugin) handleDemoReset(w http.ResponseWriter, r *http.Request) {
	config := p.getConfiguration()
	if !config.DemoMode {
		writeJSONError(w, http.StatusForbidden, "Demo reset is disabled")
		return
	}
	p.proxy(w, r, http.MethodPost, "/v1/demo/reset", map[string]any{})
}

func decodeJSON(r *http.Request, target any) error {
	decoder := json.NewDecoder(io.LimitReader(r.Body, maxRequestBodyBytes))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(target); err != nil {
		if errors.Is(err, io.EOF) {
			return errors.New("JSON body is required")
		}
		return errors.New("Invalid JSON body")
	}
	return nil
}

func writeJSONError(w http.ResponseWriter, statusCode int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(agentServiceError{Detail: message})
}
