package main

import (
	"context"
	"net/http"
	"time"

	"github.com/mattermost/mattermost/server/public/model"
	"github.com/mattermost/mattermost/server/public/plugin"
)

// MessageHasBeenPosted emits a metadata-first work event. Full message bodies remain in Mattermost
// and are retrieved only through permission-aware evidence adapters at query time.
func (p *Plugin) MessageHasBeenPosted(_ *plugin.Context, post *model.Post) {
	if post == nil || post.UserId == "" || post.Type != "" {
		return
	}
	user, appErr := p.API.GetUser(post.UserId)
	if appErr != nil || user == nil || user.Username == "" {
		p.API.LogWarn("NoPing could not resolve Mattermost actor", "user_id", post.UserId)
		return
	}
	config := p.getConfiguration()
	client, err := newAgentClient(config.AgentServiceURL, config.ServiceSigningSecret)
	if err != nil {
		return
	}
	event := workEvent{
		ID:          "mattermost-post-" + post.Id,
		Source:      "mattermost",
		EventType:   "post.created",
		ActorUserID: user.Username,
		EntityIDs:   []string{post.ChannelId},
		OccurredAt:  time.UnixMilli(post.CreateAt),
		Payload: map[string]any{
			"post_id":       post.Id,
			"channel_id":    post.ChannelId,
			"root_id":       post.RootId,
			"metadata_only": true,
		},
	}
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_, statusCode, _, requestErr := client.do(ctx, http.MethodPost, "/v1/events", event)
		if requestErr != nil || statusCode >= 300 {
			p.API.LogWarn("NoPing work event was not accepted", "event_id", event.ID, "status", statusCode)
		}
	}()
}
