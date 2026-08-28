package main

import "time"

const maxRequestBodyBytes int64 = 64 * 1024

type queryRequest struct {
	RequesterID string         `json:"requester_id"`
	Text        string         `json:"text"`
	TeamID      string         `json:"team_id,omitempty"`
	Context     map[string]any `json:"context,omitempty"`
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
