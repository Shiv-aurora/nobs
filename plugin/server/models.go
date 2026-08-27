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
