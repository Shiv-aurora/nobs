package main

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	googleOAuthTokenEndpoint = "https://oauth2.googleapis.com/token"
	googleCalendarAPIBase    = "https://www.googleapis.com/calendar/v3"
)

type calendarIdentity struct {
	UserID         string   `json:"user_id"`
	EntityIDs      []string `json:"entity_ids"`
	DelegateUserID string   `json:"delegate_user_id,omitempty"`
}

type googleAuthorizedUser struct {
	ClientID     string `json:"client_id"`
	ClientSecret string `json:"client_secret"`
	RefreshToken string `json:"refresh_token"`
}

type calendarDateTime struct {
	Date     string `json:"date"`
	DateTime string `json:"dateTime"`
}

type googleCalendarEvent struct {
	ID          string           `json:"id"`
	ETag        string           `json:"etag"`
	Status      string           `json:"status"`
	EventType   string           `json:"eventType"`
	Summary     string           `json:"summary"`
	Description string           `json:"description"`
	Updated     time.Time        `json:"updated"`
	Start       calendarDateTime `json:"start"`
	End         calendarDateTime `json:"end"`
	Creator     struct {
		Email string `json:"email"`
	} `json:"creator"`
	Organizer struct {
		Email string `json:"email"`
	} `json:"organizer"`
	Attendees []struct {
		Email          string `json:"email"`
		ResponseStatus string `json:"responseStatus"`
		Organizer      bool   `json:"organizer"`
	} `json:"attendees"`
	ExtendedProperties struct {
		Private map[string]string `json:"private"`
	} `json:"extendedProperties"`
}

func (c *googleCalendarClient) upcomingMeetingEvents(ctx context.Context, now time.Time) ([]googleCalendarEvent, error) {
	token, err := c.tokens.Token(ctx)
	if err != nil {
		return nil, err
	}
	endpoint := fmt.Sprintf("%s/calendars/%s/events", googleCalendarAPIBase, url.PathEscape(c.calendarID))
	query := url.Values{}
	query.Set("singleEvents", "true")
	query.Set("showDeleted", "true")
	query.Set("orderBy", "startTime")
	query.Set("timeMin", now.Add(-time.Hour).UTC().Format(time.RFC3339))
	query.Set("timeMax", now.Add(14*24*time.Hour).UTC().Format(time.RFC3339))
	query.Set("fields", "items(id,etag,status,eventType,summary,description,updated,start,end,organizer/email,attendees(email,responseStatus,organizer),extendedProperties/private)")
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint+"?"+query.Encode(), nil)
	if err != nil {
		return nil, err
	}
	request.Header.Set("Authorization", "Bearer "+token)
	if c.quotaProject != "" {
		request.Header.Set("X-Goog-User-Project", c.quotaProject)
	}
	response, err := c.client.Do(request)
	if err != nil {
		return nil, fmt.Errorf("fetch Calendar meetings: %w", err)
	}
	defer response.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(response.Body, 1024*1024))
	if response.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("Calendar meetings API returned %s", response.Status)
	}
	var payload struct {
		Items []googleCalendarEvent `json:"items"`
	}
	if err := json.Unmarshal(body, &payload); err != nil {
		return nil, errors.New("Calendar meetings response is invalid JSON")
	}
	return payload.Items, nil
}

func meetingPreparationEligibility(event googleCalendarEvent) (string, string) {
	override := strings.ToLower(strings.TrimSpace(event.ExtendedProperties.Private["nobsPreparation"]))
	if override == "always" {
		return "eligible", "Organizer marked this meeting for agent preparation."
	}
	if override == "never" {
		return "skipped", "Organizer excluded this meeting from agent preparation."
	}
	text := strings.ToLower(event.Summary + " " + event.Description)
	for _, excluded := range []string{"coffee", "social", "welcome", "introduction", "intro ", "focus time", "birthday"} {
		if strings.Contains(text, excluded) {
			return "skipped", "Social, welcome, and focus-time events are intentionally left human."
		}
	}
	for _, work := range []string{"project", "status", "planning", "review", "incident", "decision", "launch", "engineering", "readiness", "sync"} {
		if strings.Contains(text, work) {
			return "eligible", "Work meeting matched deterministic preparation rules."
		}
	}
	return "ambiguous", "Meeting needs one lightweight eligibility classification before preparation."
}

func normalizeMeetingEvent(source googleCalendarEvent, identities map[string]calendarIdentity) (workEvent, bool, error) {
	if source.ID == "" || source.EventType != "default" {
		return workEvent{}, false, nil
	}
	organizerEmail := strings.ToLower(strings.TrimSpace(source.Organizer.Email))
	organizer, ok := identities[organizerEmail]
	if !ok {
		return workEvent{}, false, nil
	}
	start, err := calendarEventTime(source.Start)
	if err != nil {
		return workEvent{}, false, err
	}
	end, err := calendarEventTime(source.End)
	if err != nil {
		return workEvent{}, false, err
	}
	attendees := make([]map[string]any, 0, len(source.Attendees))
	entityIDs := []string{"calendar:" + source.ID}
	for _, item := range source.Attendees {
		identity, mapped := identities[strings.ToLower(strings.TrimSpace(item.Email))]
		if !mapped {
			continue
		}
		attendees = append(attendees, map[string]any{"user_id": identity.UserID, "response_status": item.ResponseStatus})
		entityIDs = append(entityIDs, identity.UserID)
	}
	if len(attendees) == 0 {
		attendees = append(attendees, map[string]any{"user_id": organizer.UserID, "response_status": "accepted"})
	}
	eligibility, reason := meetingPreparationEligibility(source)
	eventType := "calendar.meeting.upserted"
	if source.Status == "cancelled" {
		eventType = "calendar.meeting.cancelled"
	}
	payload := map[string]any{
		"calendar_event_id": source.ID, "etag": source.ETag, "title": source.Summary,
		"description": source.Description, "start_at": start.UTC().Format(time.RFC3339),
		"end_at": end.UTC().Format(time.RFC3339), "organizer_user_id": organizer.UserID,
		"attendees": attendees, "preparation_eligibility": eligibility, "preparation_reason": reason,
	}
	return workEvent{ID: "google_calendar:meeting:" + source.ID + ":" + source.Updated.UTC().Format(time.RFC3339Nano), Source: "google_calendar", EventType: eventType, ActorUserID: organizer.UserID, EntityIDs: entityIDs, OccurredAt: source.Updated, Payload: payload}, true, nil
}

func (c *googleCalendarClient) applyConfirmedAction(ctx context.Context, eventID string, request meetingActionRequest, startAt time.Time) (string, error) {
	token, err := c.tokens.Token(ctx)
	if err != nil {
		return "", err
	}
	endpoint := fmt.Sprintf("%s/calendars/%s/events/%s", googleCalendarAPIBase, url.PathEscape(c.calendarID), url.PathEscape(eventID))
	method := http.MethodPatch
	var body io.Reader
	if request.Action == "cancel" {
		method = http.MethodDelete
	} else {
		patch := map[string]any{}
		if request.Action == "shorten" {
			patch["end"] = map[string]string{"dateTime": startAt.Add(time.Duration(request.DurationMinutes) * time.Minute).UTC().Format(time.RFC3339)}
		} else {
			patch["description"] = strings.Join(request.Agenda, "\n")
		}
		encoded, _ := json.Marshal(patch)
		body = strings.NewReader(string(encoded))
	}
	httpRequest, err := http.NewRequestWithContext(ctx, method, endpoint, body)
	if err != nil {
		return "", err
	}
	httpRequest.Header.Set("Authorization", "Bearer "+token)
	httpRequest.Header.Set("If-Match", request.ExpectedETag)
	if body != nil {
		httpRequest.Header.Set("Content-Type", "application/json")
	}
	response, err := c.client.Do(httpRequest)
	if err != nil {
		return "", fmt.Errorf("apply confirmed Calendar action: %w", err)
	}
	defer response.Body.Close()
	if response.StatusCode == http.StatusPreconditionFailed {
		return "", errors.New("Calendar event changed after preparation")
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return "", fmt.Errorf("Calendar write returned %s", response.Status)
	}
	return response.Header.Get("ETag"), nil
}

type calendarTokenSource struct {
	credentials googleAuthorizedUser
	client      *http.Client
	now         func() time.Time

	mu        sync.Mutex
	token     string
	expiresAt time.Time
}

func newCalendarTokenSource(encodedCredentials string) (*calendarTokenSource, error) {
	raw, err := base64.StdEncoding.DecodeString(strings.TrimSpace(encodedCredentials))
	if err != nil {
		return nil, errors.New("Google Calendar credentials are not valid base64")
	}
	var credentials googleAuthorizedUser
	if err := json.Unmarshal(raw, &credentials); err != nil {
		return nil, errors.New("Google Calendar credentials are not valid authorized-user JSON")
	}
	if credentials.ClientID == "" || credentials.ClientSecret == "" || credentials.RefreshToken == "" {
		return nil, errors.New("Google Calendar authorized-user credentials are incomplete")
	}
	return &calendarTokenSource{
		credentials: credentials,
		client:      &http.Client{Timeout: 10 * time.Second},
		now:         time.Now,
	}, nil
}

func (s *calendarTokenSource) Token(ctx context.Context) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.token != "" && s.expiresAt.After(s.now().Add(90*time.Second)) {
		return s.token, nil
	}
	form := url.Values{}
	form.Set("client_id", s.credentials.ClientID)
	form.Set("client_secret", s.credentials.ClientSecret)
	form.Set("refresh_token", s.credentials.RefreshToken)
	form.Set("grant_type", "refresh_token")
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, googleOAuthTokenEndpoint, strings.NewReader(form.Encode()))
	if err != nil {
		return "", fmt.Errorf("create Calendar token request: %w", err)
	}
	request.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	response, err := s.client.Do(request)
	if err != nil {
		return "", fmt.Errorf("refresh Calendar token: %w", err)
	}
	defer response.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(response.Body, 16*1024))
	if response.StatusCode != http.StatusOK {
		return "", fmt.Errorf("Calendar token refresh returned %s", response.Status)
	}
	var payload struct {
		AccessToken string `json:"access_token"`
		ExpiresIn   int64  `json:"expires_in"`
	}
	if err := json.Unmarshal(body, &payload); err != nil || payload.AccessToken == "" || payload.ExpiresIn <= 0 {
		return "", errors.New("Calendar token refresh response is incomplete")
	}
	s.token = payload.AccessToken
	s.expiresAt = s.now().Add(time.Duration(payload.ExpiresIn) * time.Second)
	return s.token, nil
}

type googleCalendarClient struct {
	calendarID   string
	quotaProject string
	tokens       accessTokenProvider
	client       *http.Client
}

func calendarClientFromConfig(config *configuration) (*googleCalendarClient, error) {
	if strings.TrimSpace(config.GoogleCalendarCredentialsB64) == "" {
		return nil, errors.New("Google Calendar is not connected")
	}
	tokens, err := newCalendarTokenSource(config.GoogleCalendarCredentialsB64)
	if err != nil {
		return nil, err
	}
	calendarID := strings.TrimSpace(config.GoogleCalendarID)
	if calendarID == "" {
		calendarID = "primary"
	}
	return &googleCalendarClient{calendarID: calendarID, quotaProject: config.GoogleCloudProject, tokens: tokens, client: &http.Client{Timeout: 15 * time.Second}}, nil
}

func (c *googleCalendarClient) outOfOfficeEvents(ctx context.Context, now time.Time) ([]googleCalendarEvent, error) {
	token, err := c.tokens.Token(ctx)
	if err != nil {
		return nil, err
	}
	endpoint := fmt.Sprintf("%s/calendars/%s/events", googleCalendarAPIBase, url.PathEscape(c.calendarID))
	fetch := func(eventType, privateFilter string) ([]googleCalendarEvent, error) {
		query := url.Values{}
		query.Set("eventTypes", eventType)
		if privateFilter != "" {
			query.Set("privateExtendedProperty", privateFilter)
		}
		query.Set("singleEvents", "true")
		query.Set("showDeleted", "true")
		query.Set("timeMin", now.Add(-24*time.Hour).UTC().Format(time.RFC3339))
		query.Set("timeMax", now.Add(30*24*time.Hour).UTC().Format(time.RFC3339))
		// Deliberately exclude summary, description, location, attendees, and attachments.
		query.Set("fields", "items(id,status,eventType,updated,start,end,creator/email,organizer/email,extendedProperties/private)")
		request, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint+"?"+query.Encode(), nil)
		if err != nil {
			return nil, err
		}
		request.Header.Set("Authorization", "Bearer "+token)
		if c.quotaProject != "" {
			request.Header.Set("X-Goog-User-Project", c.quotaProject)
		}
		response, err := c.client.Do(request)
		if err != nil {
			return nil, fmt.Errorf("fetch Calendar availability events: %w", err)
		}
		defer response.Body.Close()
		body, _ := io.ReadAll(io.LimitReader(response.Body, 1024*1024))
		if response.StatusCode != http.StatusOK {
			return nil, fmt.Errorf("Calendar events API returned %s", response.Status)
		}
		var payload struct {
			Items []googleCalendarEvent `json:"items"`
		}
		if err := json.Unmarshal(body, &payload); err != nil {
			return nil, errors.New("Calendar events response is invalid JSON")
		}
		return payload.Items, nil
	}
	native, err := fetch("outOfOffice", "")
	if err != nil {
		return nil, err
	}
	// Personal Google accounts cannot create native out-of-office events. A
	// private marker provides the same work-state signal without reading content.
	tagged, err := fetch("default", "nopingAvailability=out_of_office")
	if err != nil {
		return nil, err
	}
	return append(native, tagged...), nil
}

func parseCalendarIdentityMap(raw string) (map[string]calendarIdentity, error) {
	values := map[string]calendarIdentity{}
	if err := json.Unmarshal([]byte(raw), &values); err != nil {
		return nil, errors.New("GoogleCalendarIdentityMap must be a JSON object")
	}
	normalized := make(map[string]calendarIdentity, len(values))
	for email, identity := range values {
		email = strings.ToLower(strings.TrimSpace(email))
		identity.UserID = strings.TrimSpace(identity.UserID)
		if email != "" && identity.UserID != "" {
			normalized[email] = identity
		}
	}
	return normalized, nil
}

func calendarEventTime(value calendarDateTime) (time.Time, error) {
	if value.DateTime != "" {
		return time.Parse(time.RFC3339, value.DateTime)
	}
	if value.Date != "" {
		return time.Parse("2006-01-02", value.Date)
	}
	return time.Time{}, errors.New("Calendar event has no start or end time")
}

func normalizeCalendarEvent(source googleCalendarEvent, identities map[string]calendarIdentity, now time.Time) (workEvent, bool, error) {
	taggedOutOfOffice := source.EventType == "default" && source.ExtendedProperties.Private["nopingAvailability"] == "out_of_office"
	if (source.EventType != "outOfOffice" && !taggedOutOfOffice) || source.ID == "" {
		return workEvent{}, false, nil
	}
	email := strings.ToLower(strings.TrimSpace(source.Creator.Email))
	if email == "" {
		email = strings.ToLower(strings.TrimSpace(source.Organizer.Email))
	}
	identity, ok := identities[email]
	if !ok {
		return workEvent{}, false, nil
	}
	start, err := calendarEventTime(source.Start)
	if err != nil {
		return workEvent{}, false, err
	}
	end, err := calendarEventTime(source.End)
	if err != nil {
		return workEvent{}, false, err
	}
	eventType := "calendar.out_of_office"
	if source.Status == "cancelled" || !end.After(now) {
		eventType = "calendar.out_of_office.ended"
	} else if start.After(now) {
		// Future OOO entries are not availability facts yet; a later poll emits them.
		return workEvent{}, false, nil
	}
	stateKey := eventType + "\n" + source.Updated.UTC().Format(time.RFC3339Nano) + "\n" + end.UTC().Format(time.RFC3339Nano)
	digest := sha256.Sum256([]byte(stateKey))
	payload := map[string]any{
		"starts_at": start.UTC().Format(time.RFC3339),
		"until":     end.UTC().Format(time.RFC3339),
	}
	if identity.DelegateUserID != "" {
		payload["delegate_user_id"] = identity.DelegateUserID
	}
	entityIDs := append([]string(nil), identity.EntityIDs...)
	return workEvent{
		ID:          "google_calendar:" + source.ID + ":" + hex.EncodeToString(digest[:8]),
		Source:      "google_calendar",
		EventType:   eventType,
		ActorUserID: identity.UserID,
		EntityIDs:   entityIDs,
		OccurredAt:  source.Updated,
		Payload:     payload,
	}, true, nil
}

func calendarPollInterval(raw string) time.Duration {
	minutes, err := strconv.Atoi(strings.TrimSpace(raw))
	if err != nil || minutes < 2 || minutes > 60 {
		minutes = 5
	}
	return time.Duration(minutes) * time.Minute
}

func (p *Plugin) startCalendarPoller() {
	config := p.getConfiguration()
	if strings.TrimSpace(config.GoogleCalendarCredentialsB64) == "" {
		return
	}
	client, err := calendarClientFromConfig(config)
	if err != nil {
		p.API.LogError("NoBS Calendar connector is disabled", "error", err.Error())
		return
	}
	identities, err := parseCalendarIdentityMap(config.GoogleCalendarIdentityMap)
	if err != nil || len(identities) == 0 {
		p.API.LogError("NoBS Calendar connector is disabled", "error", "calendar identity map is invalid or empty")
		return
	}
	publisher, err := newPubSubPublisher(config.GoogleCloudProject, config.PubSubTopic)
	if err != nil {
		p.API.LogError("NoBS Calendar connector is disabled", "error", err.Error())
		return
	}
	ctx, cancel := context.WithCancel(context.Background())
	p.calendarCancel = cancel
	p.calendarWG.Add(1)
	go func() {
		defer p.calendarWG.Done()
		interval := calendarPollInterval(config.GoogleCalendarPollMinutes)
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		for {
			p.pollCalendar(ctx, client, publisher, identities)
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
			}
		}
	}()
}

func (p *Plugin) pollCalendar(ctx context.Context, client *googleCalendarClient, publisher workEventPublisher, identities map[string]calendarIdentity) {
	now := time.Now()
	events, err := client.outOfOfficeEvents(ctx, now)
	if err != nil {
		p.API.LogError("NoBS Calendar poll failed", "error", err.Error())
		return
	}
	published := 0
	for _, source := range events {
		event, accepted, err := normalizeCalendarEvent(source, identities, now)
		if err != nil {
			p.API.LogWarn("NoBS skipped malformed Calendar event", "event_id", source.ID, "error", err.Error())
			continue
		}
		if !accepted {
			continue
		}
		publishCtx, cancel := context.WithTimeout(ctx, 12*time.Second)
		err = publisher.Publish(publishCtx, event)
		cancel()
		if err != nil {
			p.API.LogError("NoBS Calendar event publish failed", "event_id", event.ID, "error", err.Error())
			continue
		}
		published++
	}
	meetings, err := client.upcomingMeetingEvents(ctx, now)
	if err != nil {
		p.API.LogError("NoBS Calendar meeting sync failed", "error", err.Error())
		return
	}
	for _, source := range meetings {
		event, accepted, normalizeErr := normalizeMeetingEvent(source, identities)
		if normalizeErr != nil {
			p.API.LogWarn("NoBS skipped malformed Calendar meeting", "event_id", source.ID, "error", normalizeErr.Error())
			continue
		}
		if !accepted {
			continue
		}
		publishCtx, cancel := context.WithTimeout(ctx, 12*time.Second)
		publishErr := publisher.Publish(publishCtx, event)
		cancel()
		if publishErr != nil {
			p.API.LogError("NoBS Calendar meeting publish failed", "event_id", event.ID, "error", publishErr.Error())
			continue
		}
		published++
	}
	if published > 0 {
		p.API.LogInfo("NoBS Calendar availability and meetings synchronized", "events", published)
	}
}
