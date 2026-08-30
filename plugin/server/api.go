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
	"github.com/gorilla/websocket"
	"github.com/mattermost/mattermost/server/public/model"
	"github.com/mattermost/mattermost/server/public/plugin"
)

func (p *Plugin) initRouter() *mux.Router {
	router := mux.NewRouter()
	// GitHub cannot hold a Mattermost session; this endpoint is authenticated by
	// the webhook HMAC before it can publish a normalized event.
	router.HandleFunc("/connectors/github", p.handleGitHubWebhook).Methods(http.MethodPost)
	router.HandleFunc("/api/v1/demo-login", p.handleDemoLogin).Methods(http.MethodPost)
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
	api.HandleFunc("/meetings", p.handleMeetings).Methods(http.MethodGet)
	api.HandleFunc("/meetings/{meetingID}", p.handleMeeting).Methods(http.MethodGet)
	api.HandleFunc("/meetings/{meetingID}/prepare", p.handlePrepareMeeting).Methods(http.MethodPost)
	api.HandleFunc("/meetings/{meetingID}/actions", p.handleMeetingAction).Methods(http.MethodPost)
	api.HandleFunc("/meetings/{meetingID}/share", p.handleShareMeeting).Methods(http.MethodPost)
	api.HandleFunc("/meetings/{meetingID}/delegations", p.handleCreateMeetingDelegation).Methods(http.MethodPost)
	api.HandleFunc("/meetings/{meetingID}/attendance", p.handleMeetingAttendance).Methods(http.MethodPost)
	api.HandleFunc("/meeting-delegations/{delegationID}", p.handleMeetingDelegation).Methods(http.MethodGet)
	api.HandleFunc("/meeting-delegations/{delegationID}/mission", p.handleUpdateMeetingDelegation).Methods(http.MethodPatch)
	api.HandleFunc("/meeting-delegations/{delegationID}/start", p.handleStartMeetingDelegation).Methods(http.MethodPost)
	api.HandleFunc("/meeting-delegations/{delegationID}/end", p.handleEndMeetingDelegation).Methods(http.MethodPost)
	api.HandleFunc("/meeting-delegations/{delegationID}/revoke", p.handleRevokeMeetingDelegation).Methods(http.MethodPost)
	api.HandleFunc("/meeting-delegations/{delegationID}/handoff", p.handleMeetingDelegationHandoff).Methods(http.MethodGet)
	api.HandleFunc("/live/meetings/{delegationID}", p.handleLiveMeeting).Methods(http.MethodGet)
	api.HandleFunc("/ooo", p.handleOOO).Methods(http.MethodPost)
	api.HandleFunc("/ooo/digest", p.handleOOODigest).Methods(http.MethodGet)
	api.HandleFunc("/demo/reset", p.handleDemoReset).Methods(http.MethodPost)
	return router
}

func (p *Plugin) handleChannelAgentReply(w http.ResponseWriter, r *http.Request) {
	var request channelAgentReplyRequest
	if err := decodeJSON(r, &request); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	request.Text = strings.TrimSpace(strings.NewReplacer("@noping", "", "@NoPing", "", "@nobs", "", "@NoBS", "").Replace(strings.TrimSpace(request.Text)))
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
		p.API.LogError("NoBS channel agent request failed", "error", err.Error())
		writeJSONError(w, http.StatusServiceUnavailable, "The NoBS agent is temporarily unavailable")
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
		writeJSONError(w, http.StatusBadGateway, "The NoBS agent returned an invalid response")
		return
	}
	if p.botUserID == "" {
		writeJSONError(w, http.StatusServiceUnavailable, "The NoBS agent identity is unavailable")
		return
	}
	if _, memberErr := p.API.GetTeamMember(channel.TeamId, p.botUserID); memberErr != nil {
		if _, addErr := p.API.CreateTeamMember(channel.TeamId, p.botUserID); addErr != nil {
			p.API.LogError("NoBS agent could not join team", "team_id", channel.TeamId, "error", addErr.Error())
			writeJSONError(w, http.StatusInternalServerError, "The NoBS agent could not join this workspace")
			return
		}
	}
	if _, memberErr := p.API.GetChannelMember(request.ChannelID, p.botUserID); memberErr != nil {
		if _, addErr := p.API.AddChannelMember(request.ChannelID, p.botUserID); addErr != nil {
			p.API.LogError("NoBS agent could not join channel", "channel_id", request.ChannelID, "error", addErr.Error())
			writeJSONError(w, http.StatusInternalServerError, "The NoBS agent could not join this channel")
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
			"noping_agent":                 true,
			"noping_state":                 result.Status,
			"noping_run_id":                result.RunID,
			"noping_source_post_id":        request.SourcePostID,
			"noping_represented_user_id":   "",
			"noping_represented_user_name": "",
			"noping_agent_kind":            "organization",
			"noping_route":                 strings.Join(routeNames, " → "),
			"noping_agents_consulted":      len(result.Route),
			"noping_people_interrupted":    result.PeopleInterrupted,
			"noping_model_name":            result.ModelName,
			"noping_delivery_mode":         "delegate",
			"noping_security_state":        map[bool]string{true: "denied", false: "allowed"}[result.Status == "refused"],
		},
	}
	created, createErr := p.API.CreatePost(agentPost)
	if createErr != nil {
		p.API.LogError("NoBS could not publish channel reply", "error", createErr.Error())
		writeJSONError(w, http.StatusInternalServerError, "The answer was generated but could not be posted")
		return
	}
	p.publishRunUpdate(channel.TeamId, userID, map[string]any{
		"run_id":   result.RunID,
		"status":   result.Status,
		"headline": result.Headline,
	})
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]any{"result": result, "post": created, "message": fmt.Sprintf("NoBS replied in %s", channel.DisplayName)})
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
		p.API.LogError("NoBS agent request failed", "path", path, "error", err.Error())
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

func (p *Plugin) handleMeetings(w http.ResponseWriter, r *http.Request) {
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	query := url.Values{}
	query.Set("user_id", actorKey)
	p.proxy(w, r, http.MethodGet, "/v1/meetings?"+query.Encode(), nil)
}

func (p *Plugin) handleMeeting(w http.ResponseWriter, r *http.Request) {
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	query := url.Values{}
	query.Set("user_id", actorKey)
	meetingID := url.PathEscape(mux.Vars(r)["meetingID"])
	p.proxy(w, r, http.MethodGet, "/v1/meetings/"+meetingID+"?"+query.Encode(), nil)
}

func (p *Plugin) handlePrepareMeeting(w http.ResponseWriter, r *http.Request) {
	var request meetingPreparationRequest
	if err := decodeJSON(r, &request); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	request.ActorID = actorKey
	if request.Trigger == "" {
		request.Trigger = "manual"
	}
	if request.Trigger != "manual" && request.Trigger != "scheduled" {
		writeJSONError(w, http.StatusBadRequest, "Invalid meeting preparation trigger")
		return
	}
	meetingID := url.PathEscape(mux.Vars(r)["meetingID"])
	p.proxy(w, r, http.MethodPost, "/v1/meetings/"+meetingID+"/prepare", request)
}

func (p *Plugin) handleMeetingAction(w http.ResponseWriter, r *http.Request) {
	var request meetingActionRequest
	if err := decodeJSON(r, &request); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	request.ActorID = actorKey
	if request.Action != "cancel" && request.Action != "shorten" && request.Action != "update_agenda" {
		writeJSONError(w, http.StatusBadRequest, "Invalid Calendar action")
		return
	}
	if request.Action == "shorten" && request.DurationMinutes == 0 {
		request.DurationMinutes = 15
	}
	if strings.TrimSpace(request.ExpectedETag) == "" {
		writeJSONError(w, http.StatusBadRequest, "The current Calendar version is required")
		return
	}
	meetingID := url.PathEscape(mux.Vars(r)["meetingID"])
	// The plugin never writes Calendar. It records organizer approval through
	// the gateway, which queues an idempotent command for the isolated executor.
	p.proxy(w, r, http.MethodPost, "/v1/meetings/"+meetingID+"/actions", request)
}

func (p *Plugin) handleOOO(w http.ResponseWriter, r *http.Request) {
	var request oooUpdateRequest
	if err := decodeJSON(r, &request); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	request.ActorID = actorKey
	p.proxy(w, r, http.MethodPost, "/v1/ooo", request)
}

func (p *Plugin) handleOOODigest(w http.ResponseWriter, r *http.Request) {
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	query := url.Values{}
	query.Set("user_id", actorKey)
	p.proxy(w, r, http.MethodGet, "/v1/ooo/digest?"+query.Encode(), nil)
}

func (p *Plugin) handleShareMeeting(w http.ResponseWriter, r *http.Request) {
	var request meetingShareRequest
	if err := decodeJSON(r, &request); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	userID := authenticatedUserID(r)
	if _, appErr := p.API.GetChannelMember(request.ChannelID, userID); appErr != nil {
		writeJSONError(w, http.StatusForbidden, "You do not have access to the selected conversation")
		return
	}
	meetingID := url.PathEscape(mux.Vars(r)["meetingID"])
	query := url.Values{}
	query.Set("user_id", actorKey)
	client, err := p.currentAgentClient()
	if err != nil {
		writeJSONError(w, http.StatusServiceUnavailable, err.Error())
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
	defer cancel()
	payload, statusCode, _, err := client.do(ctx, http.MethodGet, "/v1/meetings/"+meetingID+"?"+query.Encode(), nil)
	if err != nil || statusCode != http.StatusOK {
		writeJSONError(w, http.StatusBadGateway, "The meeting brief is temporarily unavailable")
		return
	}
	var detail meetingDetailResponse
	if err := json.Unmarshal(payload, &detail); err != nil || detail.Run == nil || detail.Run.Brief == nil {
		writeJSONError(w, http.StatusConflict, "Prepare the meeting before sharing its brief")
		return
	}
	brief := detail.Run.Brief
	message := fmt.Sprintf("### %s · agent-prepared brief\n%s\n\n**%d minutes returned · %d humans required**\nRecommended: **%s**", detail.Meeting.Title, brief.Summary, brief.MinutesSaved, brief.HumansRequired, brief.RecommendedDisposition)
	channel, channelErr := p.API.GetChannel(request.ChannelID)
	if channelErr != nil || channel == nil || p.ensureBotInChannel(channel) != nil {
		writeJSONError(w, http.StatusInternalServerError, "NoBS could not join the selected conversation")
		return
	}
	post, appErr := p.API.CreatePost(&model.Post{UserId: p.botUserID, ChannelId: request.ChannelID, Message: message, Props: model.StringInterface{"noping_agent": true, "noping_agent_kind": "meeting", "noping_meeting_id": detail.Meeting.ID, "noping_meeting_run_id": detail.Run.ID}})
	if appErr != nil {
		writeJSONError(w, http.StatusInternalServerError, "NoBS could not share the meeting brief")
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]any{"post": post})
}

func (p *Plugin) handleCreateMeetingDelegation(w http.ResponseWriter, r *http.Request) {
	var request meetingDelegationRequest
	if err := decodeJSON(r, &request); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	request.ActorID = actorKey
	if request.Mode == "" {
		request.Mode = "represent"
	}
	if request.Mode != "listen" && request.Mode != "represent" && request.Mode != "mission" {
		writeJSONError(w, http.StatusBadRequest, "Invalid meeting-agent mode")
		return
	}
	if strings.TrimSpace(request.ExpectedETag) == "" {
		writeJSONError(w, http.StatusBadRequest, "The current Calendar version is required")
		return
	}
	meetingID := url.PathEscape(mux.Vars(r)["meetingID"])
	p.proxy(w, r, http.MethodPost, "/v1/meetings/"+meetingID+"/delegations", request)
}

func (p *Plugin) handleMeetingAttendance(w http.ResponseWriter, r *http.Request) {
	var request meetingAttendanceRequest
	if err := decodeJSON(r, &request); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	request.ActorID = actorKey
	if request.Choice != "attend" && request.Choice != "agent" && request.Choice != "decline" {
		writeJSONError(w, http.StatusBadRequest, "Invalid attendance choice")
		return
	}
	meetingID := url.PathEscape(mux.Vars(r)["meetingID"])
	p.proxy(w, r, http.MethodPost, "/v1/meetings/"+meetingID+"/attendance", request)
}

func (p *Plugin) handleMeetingDelegation(w http.ResponseWriter, r *http.Request) {
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	delegationID := url.PathEscape(mux.Vars(r)["delegationID"])
	query := url.Values{}
	query.Set("user_id", actorKey)
	p.proxy(w, r, http.MethodGet, "/v1/meeting-delegations/"+delegationID+"?"+query.Encode(), nil)
}

func (p *Plugin) handleUpdateMeetingDelegation(w http.ResponseWriter, r *http.Request) {
	var request meetingDelegationRequest
	if err := decodeJSON(r, &request); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	request.ActorID = actorKey
	delegationID := url.PathEscape(mux.Vars(r)["delegationID"])
	p.proxy(w, r, http.MethodPatch, "/v1/meeting-delegations/"+delegationID+"/mission", request)
}

func (p *Plugin) meetingDelegationAction(w http.ResponseWriter, r *http.Request, action string) {
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	delegationID := url.PathEscape(mux.Vars(r)["delegationID"])
	p.proxy(w, r, http.MethodPost, "/v1/meeting-delegations/"+delegationID+"/"+action, meetingDelegationAction{ActorID: actorKey})
}

func (p *Plugin) handleStartMeetingDelegation(w http.ResponseWriter, r *http.Request) {
	p.meetingDelegationAction(w, r, "start")
}

func (p *Plugin) handleEndMeetingDelegation(w http.ResponseWriter, r *http.Request) {
	p.meetingDelegationAction(w, r, "end")
}

func (p *Plugin) handleRevokeMeetingDelegation(w http.ResponseWriter, r *http.Request) {
	p.meetingDelegationAction(w, r, "revoke")
}

func (p *Plugin) handleMeetingDelegationHandoff(w http.ResponseWriter, r *http.Request) {
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	delegationID := url.PathEscape(mux.Vars(r)["delegationID"])
	query := url.Values{}
	query.Set("user_id", actorKey)
	p.proxy(w, r, http.MethodGet, "/v1/meeting-delegations/"+delegationID+"/handoff?"+query.Encode(), nil)
}

func (p *Plugin) handleLiveMeeting(w http.ResponseWriter, r *http.Request) {
	actorKey, ok := p.actorKeyOrError(w, r)
	if !ok {
		return
	}
	if !websocket.IsWebSocketUpgrade(r) {
		writeJSONError(w, http.StatusBadRequest, "A WebSocket upgrade is required")
		return
	}
	if origin := r.Header.Get("Origin"); origin != "" {
		parsed, parseErr := url.Parse(origin)
		if parseErr != nil || !strings.EqualFold(parsed.Host, r.Host) {
			writeJSONError(w, http.StatusForbidden, "Cross-origin live connections are not allowed")
			return
		}
	}
	nonce := strings.TrimSpace(r.URL.Query().Get("nonce"))
	if len(nonce) < 16 || len(nonce) > 256 {
		writeJSONError(w, http.StatusUnauthorized, "Invalid live session")
		return
	}
	delegationID := url.PathEscape(mux.Vars(r)["delegationID"])
	query := url.Values{}
	query.Set("user_id", actorKey)
	query.Set("nonce", nonce)
	target := "/v1/live/meetings/" + delegationID + "?" + query.Encode()
	client, err := p.currentAgentClient()
	if err != nil {
		writeJSONError(w, http.StatusServiceUnavailable, err.Error())
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 16*time.Minute)
	defer cancel()
	upstream, response, err := client.dialLive(ctx, target)
	if err != nil {
		statusCode := http.StatusBadGateway
		if response != nil && response.StatusCode == http.StatusUnauthorized {
			statusCode = http.StatusUnauthorized
		}
		writeJSONError(w, statusCode, "The private live agent connection could not be opened")
		return
	}
	defer upstream.Close()
	upgrader := websocket.Upgrader{
		HandshakeTimeout: 10 * time.Second,
		CheckOrigin: func(request *http.Request) bool {
			origin := request.Header.Get("Origin")
			if origin == "" {
				return true
			}
			parsed, parseErr := url.Parse(origin)
			return parseErr == nil && strings.EqualFold(parsed.Host, request.Host)
		},
	}
	downstream, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer downstream.Close()
	downstream.SetReadLimit(1024 * 1024)
	upstream.SetReadLimit(1024 * 1024)
	errors := make(chan error, 2)
	copyMessages := func(destination, source *websocket.Conn) {
		for {
			messageType, reader, readErr := source.NextReader()
			if readErr != nil {
				errors <- readErr
				return
			}
			writer, writeErr := destination.NextWriter(messageType)
			if writeErr != nil {
				errors <- writeErr
				return
			}
			_, copyErr := io.Copy(writer, io.LimitReader(reader, 1024*1024))
			closeErr := writer.Close()
			if copyErr != nil {
				errors <- copyErr
				return
			}
			if closeErr != nil {
				errors <- closeErr
				return
			}
		}
	}
	go copyMessages(upstream, downstream)
	go copyMessages(downstream, upstream)
	select {
	case <-ctx.Done():
	case <-errors:
	}
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
