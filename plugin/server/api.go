package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/gorilla/mux"
	"github.com/mattermost/mattermost/server/public/model"
	"github.com/mattermost/mattermost/server/public/plugin"
)

func (p *Plugin) initRouter() *mux.Router {
	router := mux.NewRouter()
	// GitHub cannot hold a Mattermost session; this endpoint is authenticated by
	// the webhook HMAC before it can publish a normalized event.
	router.HandleFunc("/connectors/github", p.handleGitHubWebhook).Methods(http.MethodPost)
	api := router.PathPrefix("/api/v1").Subrouter()
	api.Use(p.requireUser)
	api.HandleFunc("/health", p.handleHealth).Methods(http.MethodGet)
	api.HandleFunc("/bootstrap", p.handleBootstrap).Methods(http.MethodGet)
	api.HandleFunc("/query", p.handleQuery).Methods(http.MethodPost)
	api.HandleFunc("/messages/agent-reply", p.handleChannelAgentReply).Methods(http.MethodPost)
	api.HandleFunc("/runs/{runID}", p.handleRun).Methods(http.MethodGet)
	api.HandleFunc("/decisions", p.handleDecisions).Methods(http.MethodGet)
	api.HandleFunc("/decisions/{decisionID}/resolve", p.handleResolveDecision).Methods(http.MethodPost)
	api.HandleFunc("/registry", p.handleRegistry).Methods(http.MethodGet)
	api.HandleFunc("/audit", p.handleAudit).Methods(http.MethodGet)
	api.HandleFunc("/metrics", p.handleMetrics).Methods(http.MethodGet)
	api.HandleFunc("/demo/reset", p.handleDemoReset).Methods(http.MethodPost)
	return router
}

func (p *Plugin) handleChannelAgentReply(w http.ResponseWriter, r *http.Request) {
	var request channelAgentReplyRequest
	if err := decodeJSON(r, &request); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	request.Text = strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(request.Text), "@noping"))
	if len(request.Text) < 3 || request.ChannelID == "" {
		writeJSONError(w, http.StatusBadRequest, "A channel and a question are required")
		return
	}
	userID := authenticatedUserID(r)
	if _, appErr := p.API.GetChannelMember(request.ChannelID, userID); appErr != nil {
		writeJSONError(w, http.StatusForbidden, "You do not have access to this channel")
		return
	}
	channel, appErr := p.API.GetChannel(request.ChannelID)
	if appErr != nil || channel == nil {
		writeJSONError(w, http.StatusNotFound, "Channel not found")
		return
	}
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	client, err := p.currentAgentClient()
	if err != nil {
		writeJSONError(w, http.StatusServiceUnavailable, err.Error())
		return
	}
	query := queryRequest{
		RequesterID: actorKey,
		Text:        request.Text,
		TeamID:      channel.TeamId,
		Context: map[string]any{
			"channel_id":     request.ChannelID,
			"source_post_id": request.SourcePostID,
		},
	}
	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()
	payload, statusCode, headers, err := client.do(ctx, http.MethodPost, "/v1/query", query)
	if err != nil {
		p.API.LogError("NoPing channel agent request failed", "error", err.Error())
		writeJSONError(w, http.StatusServiceUnavailable, "The NoPing agent is temporarily unavailable")
		return
	}
	if retryAfter := headers.Get("Retry-After"); retryAfter != "" {
		w.Header().Set("Retry-After", retryAfter)
	}
	if statusCode >= http.StatusMultipleChoices {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(statusCode)
		_, _ = w.Write(payload)
		return
	}
	var result channelAgentResult
	if err := json.Unmarshal(payload, &result); err != nil {
		writeJSONError(w, http.StatusBadGateway, "The NoPing agent returned an invalid response")
		return
	}
	if p.botUserID == "" {
		writeJSONError(w, http.StatusServiceUnavailable, "The NoPing agent identity is unavailable")
		return
	}
	if _, memberErr := p.API.GetTeamMember(channel.TeamId, p.botUserID); memberErr != nil {
		if _, addErr := p.API.CreateTeamMember(channel.TeamId, p.botUserID); addErr != nil {
			p.API.LogError("NoPing agent could not join team", "team_id", channel.TeamId, "error", addErr.Error())
			writeJSONError(w, http.StatusInternalServerError, "The NoPing agent could not join this workspace")
			return
		}
	}
	if _, memberErr := p.API.GetChannelMember(request.ChannelID, p.botUserID); memberErr != nil {
		if _, addErr := p.API.AddChannelMember(request.ChannelID, p.botUserID); addErr != nil {
			p.API.LogError("NoPing agent could not join channel", "channel_id", request.ChannelID, "error", addErr.Error())
			writeJSONError(w, http.StatusInternalServerError, "The NoPing agent could not join this channel")
			return
		}
	}
	routeNames := make([]string, 0, len(result.Route))
	for _, step := range result.Route {
		if step.DelegateName != "" {
			routeNames = append(routeNames, step.DelegateName)
		}
	}
	message := result.Answer
	if message == "" {
		message = result.Headline
	}
	agentPost := &model.Post{
		UserId:    p.botUserID,
		ChannelId: request.ChannelID,
		RootId:    request.RootID,
		Message:   message,
		Props: model.StringInterface{
			"noping_agent":              true,
			"noping_run_id":             result.RunID,
			"noping_status":             result.Status,
			"noping_route":              strings.Join(routeNames, " → "),
			"noping_agents_consulted":   len(result.Route),
			"noping_people_interrupted": result.PeopleInterrupted,
			"noping_source_post_id":     request.SourcePostID,
		},
	}
	created, createErr := p.API.CreatePost(agentPost)
	if createErr != nil {
		p.API.LogError("NoPing could not publish channel reply", "error", createErr.Error())
		writeJSONError(w, http.StatusInternalServerError, "The answer was generated but could not be posted")
		return
	}
	p.publishRunUpdate(channel.TeamId, userID, map[string]any{
		"run_id":   result.RunID,
		"status":   result.Status,
		"headline": result.Headline,
	})
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]any{"result": result, "post": created, "message": fmt.Sprintf("NoPing replied in %s", channel.DisplayName)})
}

func (p *Plugin) ServeHTTP(_ *plugin.Context, w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	p.router.ServeHTTP(w, r)
}

func (p *Plugin) currentAgentClient() (*agentClient, error) {
	config := p.getConfiguration()
	return newAgentClient(config.AgentServiceURL, config.ServiceSigningSecret, config.UseGoogleIdentity, config.CloudRunAudience)
}

func (p *Plugin) proxy(w http.ResponseWriter, r *http.Request, method, path string, body any) ([]byte, int, bool) {
	client, err := p.currentAgentClient()
	if err != nil {
		writeJSONError(w, http.StatusServiceUnavailable, err.Error())
		return nil, http.StatusServiceUnavailable, false
	}
	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()
	payload, statusCode, headers, err := client.do(ctx, method, path, body)
	if err != nil {
		p.API.LogError("NoPing agent request failed", "path", path, "error", err.Error())
		writeJSONError(w, http.StatusServiceUnavailable, "The organizational agent service is temporarily unavailable.")
		return nil, http.StatusServiceUnavailable, false
	}
	if retryAfter := headers.Get("Retry-After"); retryAfter != "" {
		w.Header().Set("Retry-After", retryAfter)
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_, _ = w.Write(payload)
	return payload, statusCode, true
}

func (p *Plugin) handleHealth(w http.ResponseWriter, r *http.Request) {
	p.proxy(w, r, http.MethodGet, "/v1/health", nil)
}

func (p *Plugin) handleBootstrap(w http.ResponseWriter, r *http.Request) {
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	query := url.Values{}
	query.Set("user_id", actorKey)
	p.proxy(w, r, http.MethodGet, "/v1/bootstrap?"+query.Encode(), nil)
}

func (p *Plugin) handleQuery(w http.ResponseWriter, r *http.Request) {
	var request queryRequest
	if err := decodeJSON(r, &request); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	request.RequesterID = actorKey
	if request.TeamID == "" {
		request.TeamID = strings.TrimSpace(r.URL.Query().Get("team_id"))
	}
	if len(strings.TrimSpace(request.Text)) < 3 {
		writeJSONError(w, http.StatusBadRequest, "Query must be at least 3 characters")
		return
	}
	payload, statusCode, proxied := p.proxy(w, r, http.MethodPost, "/v1/query", request)
	if !proxied || statusCode >= http.StatusMultipleChoices {
		return
	}
	var notification queryResultNotification
	if err := json.Unmarshal(payload, &notification); err == nil {
		p.publishRunUpdate(request.TeamID, authenticatedUserID(r), map[string]any{
			"run_id":   notification.RunID,
			"status":   notification.Status,
			"headline": notification.Headline,
		})
		if notification.DecisionAssigneeID != "" {
			if assigneeUserID := p.userIDForActorKey(notification.DecisionAssigneeID); assigneeUserID != "" {
				p.publishDecisionUpdate(assigneeUserID, map[string]any{
					"decision_id": notification.DecisionID,
					"headline":    notification.Headline,
				})
			}
		}
	}
}

func (p *Plugin) handleRun(w http.ResponseWriter, r *http.Request) {
	runID := url.PathEscape(mux.Vars(r)["runID"])
	p.proxy(w, r, http.MethodGet, "/v1/runs/"+runID, nil)
}

func (p *Plugin) handleDecisions(w http.ResponseWriter, r *http.Request) {
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	query := url.Values{}
	query.Set("assignee_id", actorKey)
	p.proxy(w, r, http.MethodGet, "/v1/decisions?"+query.Encode(), nil)
}

func (p *Plugin) handleResolveDecision(w http.ResponseWriter, r *http.Request) {
	var resolution decisionResolution
	if err := decodeJSON(r, &resolution); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	resolution.ActorID = actorKey
	if resolution.Status != "approved" && resolution.Status != "rejected" && resolution.Status != "discuss" {
		writeJSONError(w, http.StatusBadRequest, "Invalid decision status")
		return
	}
	if len(strings.TrimSpace(resolution.Rationale)) < 2 {
		writeJSONError(w, http.StatusBadRequest, "Rationale is required")
		return
	}
	decisionID := url.PathEscape(mux.Vars(r)["decisionID"])
	_, statusCode, proxied := p.proxy(w, r, http.MethodPost, "/v1/decisions/"+decisionID+"/resolve", resolution)
	if proxied && statusCode < http.StatusMultipleChoices {
		p.publishDecisionUpdate(authenticatedUserID(r), map[string]any{
			"decision_id": decisionID,
			"status":      resolution.Status,
		})
	}
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

func (p *Plugin) handleMetrics(w http.ResponseWriter, r *http.Request) {
	p.proxy(w, r, http.MethodGet, "/v1/metrics", nil)
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
