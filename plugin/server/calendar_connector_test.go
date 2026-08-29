package main

import (
	"context"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
)

func TestCalendarClientRequestsOnlyAvailabilityFields(t *testing.T) {
	requestCount := 0
	transport := publisherRoundTripFunc(func(request *http.Request) (*http.Response, error) {
		requestCount++
		query := request.URL.Query()
		if query.Get("singleEvents") != "true" {
			t.Fatalf("unexpected Calendar query: %s", request.URL.RawQuery)
		}
		switch requestCount {
		case 1:
			if query.Get("eventTypes") != "outOfOffice" || query.Get("privateExtendedProperty") != "" {
				t.Fatalf("unexpected native OOO query: %s", request.URL.RawQuery)
			}
		case 2:
			if query.Get("eventTypes") != "default" || query.Get("privateExtendedProperty") != "nopingAvailability=out_of_office" {
				t.Fatalf("unexpected tagged availability query: %s", request.URL.RawQuery)
			}
		default:
			t.Fatalf("unexpected extra Calendar request: %s", request.URL.RawQuery)
		}
		fields := query.Get("fields")
		for _, forbidden := range []string{"summary", "description", "location", "attendees", "attachments"} {
			if strings.Contains(fields, forbidden) {
				t.Fatalf("Calendar request leaks forbidden field %q", forbidden)
			}
		}
		if request.Header.Get("X-Goog-User-Project") != "noping-test" {
			t.Fatal("Calendar request must bill quota to the configured project")
		}
		return &http.Response{
			StatusCode: http.StatusOK,
			Status:     "200 OK",
			Header:     make(http.Header),
			Body:       io.NopCloser(strings.NewReader(`{"items":[]}`)),
			Request:    request,
		}, nil
	})
	client := &googleCalendarClient{
		calendarID:   "primary",
		quotaProject: "noping-test",
		tokens:       staticAccessToken("calendar-token"),
		client:       &http.Client{Transport: transport},
	}
	if _, err := client.outOfOfficeEvents(context.Background(), time.Now()); err != nil {
		t.Fatal(err)
	}
	if requestCount != 2 {
		t.Fatalf("expected two privacy-minimal Calendar requests, got %d", requestCount)
	}
}

func TestNormalizeCalendarEventEmitsPrivacyMinimalOOOState(t *testing.T) {
	now := time.Date(2026, 8, 27, 20, 0, 0, 0, time.UTC)
	source := googleCalendarEvent{
		ID:        "opaque-event-id",
		Status:    "confirmed",
		EventType: "outOfOffice",
		Updated:   now.Add(-time.Minute),
		Start:     calendarDateTime{DateTime: now.Add(-time.Hour).Format(time.RFC3339)},
		End:       calendarDateTime{DateTime: now.Add(2 * time.Hour).Format(time.RFC3339)},
	}
	source.Creator.Email = "person@example.com"
	identities := map[string]calendarIdentity{
		"person@example.com": {UserID: "maya", EntityIDs: []string{"atlas"}, DelegateUserID: "alex"},
	}
	event, accepted, err := normalizeCalendarEvent(source, identities, now)
	if err != nil || !accepted {
		t.Fatalf("accepted=%v err=%v", accepted, err)
	}
	if event.EventType != "calendar.out_of_office" || event.ActorUserID != "maya" {
		t.Fatalf("unexpected event: %#v", event)
	}
	if event.Payload["delegate_user_id"] != "alex" || event.Payload["until"] == "" {
		t.Fatalf("unexpected availability payload: %#v", event.Payload)
	}
	for _, forbidden := range []string{"summary", "description", "location", "attendees"} {
		if _, exists := event.Payload[forbidden]; exists {
			t.Fatalf("normalized Calendar event contains %q", forbidden)
		}
	}
}

func TestNormalizeCalendarEventWaitsUntilOOOStarts(t *testing.T) {
	now := time.Date(2026, 8, 27, 20, 0, 0, 0, time.UTC)
	source := googleCalendarEvent{
		ID:        "future-event",
		Status:    "confirmed",
		EventType: "outOfOffice",
		Updated:   now,
		Start:     calendarDateTime{DateTime: now.Add(time.Hour).Format(time.RFC3339)},
		End:       calendarDateTime{DateTime: now.Add(2 * time.Hour).Format(time.RFC3339)},
	}
	source.Creator.Email = "person@example.com"
	_, accepted, err := normalizeCalendarEvent(source, map[string]calendarIdentity{
		"person@example.com": {UserID: "maya"},
	}, now)
	if err != nil || accepted {
		t.Fatalf("future event must wait: accepted=%v err=%v", accepted, err)
	}
}

func TestNormalizeTaggedPersonalCalendarWorkState(t *testing.T) {
	now := time.Date(2026, 8, 28, 4, 30, 0, 0, time.UTC)
	source := googleCalendarEvent{
		ID:        "tagged-event",
		Status:    "confirmed",
		EventType: "default",
		Updated:   now.Add(-time.Minute),
		Start:     calendarDateTime{DateTime: now.Add(-time.Hour).Format(time.RFC3339)},
		End:       calendarDateTime{DateTime: now.Add(3 * time.Hour).Format(time.RFC3339)},
	}
	source.Creator.Email = "person@example.com"
	source.ExtendedProperties.Private = map[string]string{"nopingAvailability": "out_of_office"}
	event, accepted, err := normalizeCalendarEvent(source, map[string]calendarIdentity{
		"person@example.com": {UserID: "maya"},
	}, now)
	if err != nil || !accepted {
		t.Fatalf("accepted=%v err=%v", accepted, err)
	}
	if event.EventType != "calendar.out_of_office" || event.ActorUserID != "maya" {
		t.Fatalf("unexpected event: %#v", event)
	}
}

func TestNormalizeMeetingEventUsesMappedAttendeesAndDeterministicEligibility(t *testing.T) {
	now := time.Date(2026, 8, 29, 13, 0, 0, 0, time.UTC)
	source := googleCalendarEvent{ID: "atlas-review", ETag: "etag-1", Status: "confirmed", EventType: "default", Summary: "Atlas launch readiness", Description: "Engineering readiness", Updated: now, Start: calendarDateTime{DateTime: now.Add(time.Hour).Format(time.RFC3339)}, End: calendarDateTime{DateTime: now.Add(2 * time.Hour).Format(time.RFC3339)}}
	source.Organizer.Email = "shivam@example.com"
	source.Attendees = append(source.Attendees, struct {
		Email          string `json:"email"`
		ResponseStatus string `json:"responseStatus"`
		Organizer      bool   `json:"organizer"`
	}{Email: "maya@example.com", ResponseStatus: "accepted"})
	event, accepted, err := normalizeMeetingEvent(source, map[string]calendarIdentity{"shivam@example.com": {UserID: "shivam"}, "maya@example.com": {UserID: "maya"}})
	if err != nil || !accepted {
		t.Fatalf("accepted=%v err=%v", accepted, err)
	}
	if event.EventType != "calendar.meeting.upserted" || event.Payload["preparation_eligibility"] != "eligible" || event.Payload["etag"] != "etag-1" {
		t.Fatalf("unexpected meeting event: %#v", event)
	}
}

func TestConfirmedCalendarWriteUsesIfMatch(t *testing.T) {
	transport := publisherRoundTripFunc(func(request *http.Request) (*http.Response, error) {
		if request.Method != http.MethodPatch || request.Header.Get("If-Match") != "etag-1" {
			t.Fatalf("unsafe Calendar write: %s If-Match=%q", request.Method, request.Header.Get("If-Match"))
		}
		body, _ := io.ReadAll(request.Body)
		if !strings.Contains(string(body), `"dateTime":"2026-08-29T13:15:00Z"`) {
			t.Fatalf("unexpected Calendar patch: %s", body)
		}
		headers := make(http.Header)
		headers.Set("ETag", "etag-2")
		return &http.Response{StatusCode: http.StatusOK, Status: "200 OK", Header: headers, Body: io.NopCloser(strings.NewReader(`{}`)), Request: request}, nil
	})
	client := &googleCalendarClient{calendarID: "primary", tokens: staticAccessToken("calendar-token"), client: &http.Client{Transport: transport}}
	etag, err := client.applyConfirmedAction(context.Background(), "event-1", meetingActionRequest{Action: "shorten", ExpectedETag: "etag-1", DurationMinutes: 15}, time.Date(2026, 8, 29, 13, 0, 0, 0, time.UTC))
	if err != nil || etag != "etag-2" {
		t.Fatalf("etag=%q err=%v", etag, err)
	}
}
