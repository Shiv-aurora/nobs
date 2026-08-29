package main

import (
	"encoding/json"
	"time"
)

const maxRequestBodyBytes int64 = 64 * 1024

type queryRequest struct {
	RequesterID         string         `json:"requester_id"`
	Text                string         `json:"text"`
	TeamID              string         `json:"team_id,omitempty"`
	DelegateForUserID   string         `json:"delegate_for_user_id,omitempty"`
	ConversationContext map[string]any `json:"conversation_context,omitempty"`
	Context             map[string]any `json:"context,omitempty"`
}

type delegationResolutionRequest struct {
	RequesterID         string         `json:"requester_id"`
	Text                string         `json:"text"`
	ConversationContext map[string]any `json:"conversation_context,omitempty"`
}

type delegationResolution struct {
	Eligible            bool    `json:"eligible"`
	Kind                string  `json:"kind,omitempty"`
	RepresentedUserID   string  `json:"represented_user_id,omitempty"`
	RepresentedUserName string  `json:"represented_user_name,omitempty"`
	Scope               string  `json:"scope,omitempty"`
	Reason              string  `json:"reason"`
	Confidence          float64 `json:"confidence"`
}

type decisionResolution struct {
	ActorID   string `json:"actor_id"`
	Status    string `json:"status"`
	Rationale string `json:"rationale"`
}

type workEvent struct {
	ID          string         `json:"id"`
	Source      string         `json:"source"`
	EventType   string         `json:"event_type"`
	ActorUserID string         `json:"actor_user_id"`
	EntityIDs   []string       `json:"entity_ids"`
	OccurredAt  time.Time      `json:"occurred_at"`
	Payload     map[string]any `json:"payload"`
}

type agentServiceError struct {
	Detail any `json:"detail"`
}

type bootstrapContext struct {
	UserID string `json:"user_id"`
	TeamID string `json:"team_id,omitempty"`
}

type queryResultNotification struct {
	RunID              string `json:"run_id"`
	Status             string `json:"status"`
	Headline           string `json:"headline"`
	DecisionID         string `json:"decision_id,omitempty"`
	DecisionAssigneeID string `json:"decision_assignee_id,omitempty"`
	PeopleInterrupted  int    `json:"people_interrupted"`
}

type channelAgentReplyRequest struct {
	Text         string `json:"text"`
	ChannelID    string `json:"channel_id"`
	SourcePostID string `json:"source_post_id,omitempty"`
	RootID       string `json:"root_id,omitempty"`
}

type channelAgentResult struct {
	RunID             string `json:"run_id"`
	Status            string `json:"status"`
	Answer            string `json:"answer"`
	Headline          string `json:"headline"`
	PeopleInterrupted int    `json:"people_interrupted"`
	Route             []struct {
		DelegateName string `json:"delegate_name"`
	} `json:"route"`
}

type queryStreamEvent struct {
	Event string          `json:"event"`
	Data  json.RawMessage `json:"data"`
}

type meetingPreparationRequest struct {
	ActorID string `json:"actor_id"`
	Trigger string `json:"trigger"`
}

type meetingActionRequest struct {
	ActorID         string   `json:"actor_id"`
	Action          string   `json:"action"`
	ExpectedETag    string   `json:"expected_etag"`
	AppliedETag     string   `json:"applied_etag,omitempty"`
	DurationMinutes int      `json:"duration_minutes,omitempty"`
	Agenda          []string `json:"agenda,omitempty"`
}

type oooUpdateRequest struct {
	ActorID        string `json:"actor_id"`
	Enabled        bool   `json:"enabled"`
	Until          string `json:"until,omitempty"`
	DelegateUserID string `json:"delegate_user_id,omitempty"`
}

type meetingShareRequest struct {
	ChannelID string `json:"channel_id"`
}

type meetingDetailResponse struct {
	Meeting struct {
		ID              string `json:"id"`
		Title           string `json:"title"`
		CalendarEventID string `json:"calendar_event_id"`
		OrganizerUserID string `json:"organizer_user_id"`
		StartAt         string `json:"start_at"`
		Source          string `json:"source"`
	} `json:"meeting"`
	Run *struct {
		ID    string `json:"id"`
		Brief *struct {
			Summary                    string   `json:"summary"`
			ResolvedItems              []string `json:"resolved_items"`
			RemainingItems             []string `json:"remaining_items"`
			RecommendedDisposition     string   `json:"recommended_disposition"`
			RecommendedDurationMinutes int      `json:"recommended_duration_minutes"`
			MinutesSaved               int      `json:"minutes_saved"`
			HumansRequired             int      `json:"humans_required"`
		} `json:"brief"`
	} `json:"run"`
}
