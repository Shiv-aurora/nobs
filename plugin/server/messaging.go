package main

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/mattermost/mattermost/server/public/model"
)

var mentionPattern = regexp.MustCompile(`(?:^|[^A-Za-z0-9._-])@([A-Za-z0-9._-]+)`)

type delegateTrigger struct {
	Kind              string
	RepresentedUserID string
	RepresentedActor  string
	RepresentedName   string
}

func displayName(user *model.User) string {
	name := strings.TrimSpace(strings.Join([]string{user.FirstName, user.LastName}, " "))
	if name == "" {
		name = user.Username
	}
	return name
}

func (p *Plugin) resolveMentionedUsers(message, authorID string) []*model.User {
	seen := map[string]bool{}
	users := []*model.User{}
	for _, match := range mentionPattern.FindAllStringSubmatch(message, -1) {
		username := strings.ToLower(match[1])
		if username == "noping" || username == "nobs" || username == "channel" || username == "all" || username == "here" || seen[username] {
			continue
		}
		user, appErr := p.API.GetUserByUsername(username)
		if appErr != nil || user == nil || user.Id == authorID || user.Id == p.botUserID || user.IsBot {
			continue
		}
		seen[username] = true
		users = append(users, user)
	}
	return users
}

func (p *Plugin) delegateTriggerFor(post *model.Post) (delegateTrigger, bool) {
	channel, appErr := p.API.GetChannel(post.ChannelId)
	if appErr != nil || channel == nil {
		return delegateTrigger{}, false
	}
	if channel.Type == model.ChannelTypeDirect {
		for _, userID := range strings.Split(channel.Name, "__") {
			if userID == "" || userID == post.UserId {
				continue
			}
			user, userErr := p.API.GetUser(userID)
			if userErr == nil && user != nil && !user.IsBot {
				return delegateTrigger{Kind: "personal", RepresentedUserID: user.Id, RepresentedActor: user.Username, RepresentedName: displayName(user)}, true
			}
		}
		return delegateTrigger{}, false
	}
	mentioned := p.resolveMentionedUsers(post.Message, post.UserId)
	if len(mentioned) == 1 {
		user := mentioned[0]
		return delegateTrigger{Kind: "personal", RepresentedUserID: user.Id, RepresentedActor: user.Username, RepresentedName: displayName(user)}, true
	}
	lowerMessage := strings.ToLower(post.Message)
	if len(mentioned) > 1 || strings.Contains(lowerMessage, "@noping") || strings.Contains(lowerMessage, "@nobs") {
		return delegateTrigger{Kind: "organization"}, true
	}
	return delegateTrigger{}, false
}

func (p *Plugin) automaticDelegateTriggerFor(post *model.Post, requesterActor string) (delegateTrigger, bool) {
	channel, appErr := p.API.GetChannel(post.ChannelId)
	if appErr != nil || channel == nil || channel.Type == model.ChannelTypeDirect {
		return delegateTrigger{}, false
	}
	client, err := p.currentAgentClient()
	if err != nil {
		p.API.LogWarn("NoBS could not create automatic delegation client", "error", err.Error())
		return delegateTrigger{}, false
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	resolution, err := client.resolveDelegation(ctx, delegationResolutionRequest{
		RequesterID: requesterActor,
		Text:        post.Message,
		ConversationContext: map[string]any{
			"channel_id":           channel.Id,
			"channel_name":         channel.Name,
			"channel_display_name": channel.DisplayName,
			"channel_purpose":      channel.Purpose,
			"channel_header":       channel.Header,
			"channel_type":         channel.Type,
			"root_id":              post.RootId,
		},
	})
	if err != nil {
		p.API.LogWarn("NoBS automatic delegation preflight failed", "post_id", post.Id, "error", err.Error())
		return delegateTrigger{}, false
	}
	if !resolution.Eligible {
		return delegateTrigger{}, false
	}
	if resolution.Kind != "personal" || strings.TrimSpace(resolution.RepresentedUserID) == "" {
		return delegateTrigger{Kind: "organization"}, true
	}
	user, userErr := p.API.GetUserByUsername(resolution.RepresentedUserID)
	if userErr != nil || user == nil || user.IsBot || user.Id == post.UserId {
		return delegateTrigger{Kind: "organization"}, true
	}
	name := strings.TrimSpace(resolution.RepresentedUserName)
	if name == "" {
		name = displayName(user)
	}
	return delegateTrigger{
		Kind:              "personal",
		RepresentedUserID: user.Id,
		RepresentedActor:  user.Username,
		RepresentedName:   name,
	}, true
}

func (p *Plugin) hasAgentReply(sourcePostID string) bool {
	thread, appErr := p.API.GetPostThread(sourcePostID)
	if appErr != nil || thread == nil {
		return false
	}
	for _, post := range thread.Posts {
		if post.Props != nil && post.Props["noping_source_post_id"] == sourcePostID {
			return true
		}
	}
	return false
}

func (p *Plugin) ensureBotInChannel(channel *model.Channel) error {
	// A native one-to-one DM is intentionally limited to its two participants.
	// Plugin-authored delegate replies may still be written to that conversation,
	// but adding the audited bot as a third member would convert/break the DM.
	if channel.Type == model.ChannelTypeDirect {
		return nil
	}
	if channel.TeamId != "" {
		if _, appErr := p.API.GetTeamMember(channel.TeamId, p.botUserID); appErr != nil {
			if _, addErr := p.API.CreateTeamMember(channel.TeamId, p.botUserID); addErr != nil {
				return fmt.Errorf("join team: %s", addErr.Error())
			}
		}
	}
	if _, appErr := p.API.GetChannelMember(channel.Id, p.botUserID); appErr != nil {
		if _, addErr := p.API.AddChannelMember(channel.Id, p.botUserID); addErr != nil {
			return fmt.Errorf("join channel: %s", addErr.Error())
		}
	}
	return nil
}

func (p *Plugin) answerTriggeredPost(source *model.Post, requesterActor string, trigger delegateTrigger) {
	if p.hasAgentReply(source.Id) || p.botUserID == "" {
		return
	}
	channel, appErr := p.API.GetChannel(source.ChannelId)
	if appErr != nil || channel == nil || p.ensureBotInChannel(channel) != nil {
		return
	}
	rootID := source.RootId
	if rootID == "" {
		rootID = source.Id
	}
	pendingMessage := "NoBS is checking the relevant organizational context…"
	if trigger.Kind == "personal" {
		pendingMessage = trigger.RepresentedName + "'s agent is checking the relevant context…"
	}
	created, createErr := p.API.CreatePost(&model.Post{UserId: p.botUserID, ChannelId: source.ChannelId, RootId: rootID, Message: pendingMessage, Props: model.StringInterface{
		"noping_agent": true, "noping_state": "accepted", "noping_source_post_id": source.Id,
		"noping_represented_user_id": trigger.RepresentedUserID, "noping_represented_user_name": trigger.RepresentedName,
		"noping_agent_kind": trigger.Kind, "noping_route": "", "noping_agents_consulted": 0,
		"noping_people_interrupted": 0, "noping_delivery_mode": "delegate", "noping_security_state": "screening"}})
	if createErr != nil {
		p.API.LogError("NoBS could not create pending delegate reply", "source_post_id", source.Id, "error", createErr.Error())
		return
	}
	client, err := p.currentAgentClient()
	if err != nil {
		p.failPendingPost(created, "NoBS could not reach the delegate service.")
		return
	}
	queryText := strings.TrimSpace(strings.NewReplacer("@noping", "", "@NoPing", "", "@nobs", "", "@NoBS", "").Replace(source.Message))
	query := queryRequest{RequesterID: requesterActor, Text: queryText, TeamID: channel.TeamId, DelegateForUserID: trigger.RepresentedActor,
		ConversationContext: map[string]any{"channel_id": source.ChannelId, "root_id": rootID, "source_post_id": source.Id},
		Context:             map[string]any{"channel_id": source.ChannelId, "source_post_id": source.Id}}
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()
	result, _, _, streamErr := client.streamQuery(ctx, query, func(event queryStreamEvent) {
		if event.Event == "completed" || event.Event == "failed" {
			return
		}
		created.Props["noping_state"] = event.Event
		created.Message = pendingMessageForPhase(trigger, event.Event)
		if event.Event == "routed" {
			var data struct {
				Route []struct {
					DelegateName string `json:"delegate_name"`
				} `json:"route"`
			}
			if json.Unmarshal(event.Data, &data) == nil {
				names := make([]string, 0, len(data.Route))
				for _, step := range data.Route {
					names = append(names, step.DelegateName)
				}
				created.Props["noping_route"] = strings.Join(names, " → ")
				created.Props["noping_agents_consulted"] = len(names)
			}
		}
		_, _ = p.API.UpdatePost(created)
	})
	if streamErr != nil || result == nil {
		p.failPendingPost(created, "NoBS could not complete this delegate request. No human was interrupted.")
		return
	}
	routeNames := make([]string, 0, len(result.Route))
	for _, step := range result.Route {
		if step.DelegateName != "" {
			routeNames = append(routeNames, step.DelegateName)
		}
	}
	created.Message = result.Answer
	if created.Message == "" {
		created.Message = result.Headline
	}
	created.Props["noping_state"] = result.Status
	created.Props["noping_run_id"] = result.RunID
	created.Props["noping_route"] = strings.Join(routeNames, " → ")
	created.Props["noping_agents_consulted"] = len(routeNames)
	created.Props["noping_people_interrupted"] = result.PeopleInterrupted
	if result.Status == "refused" {
		created.Props["noping_security_state"] = "denied"
	} else {
		created.Props["noping_security_state"] = "allowed"
	}
	if _, updateErr := p.API.UpdatePost(created); updateErr != nil {
		p.API.LogError("NoBS could not finalize delegate reply", "post_id", created.Id, "error", updateErr.Error())
	}
	if trigger.Kind == "personal" && trigger.RepresentedActor != "" {
		title := strings.TrimSpace(source.Message)
		if len(title) > 120 {
			title = title[:120] + "…"
		}
		_, _, _, queueErr := client.do(ctx, "POST", "/v1/ooo/queue", map[string]any{
			"user_id": trigger.RepresentedActor, "source_type": "message", "source_id": source.Id,
			"title": title, "summary": created.Message, "urgent": false, "handled_by_agent": true,
		})
		if queueErr != nil {
			p.API.LogWarn("NoBS could not add the answered message to the OOO return digest", "post_id", source.Id)
		}
	}
	p.publishRunUpdate(channel.TeamId, source.UserId, map[string]any{"run_id": result.RunID, "status": result.Status, "headline": result.Headline})
}

func pendingMessageForPhase(trigger delegateTrigger, phase string) string {
	actor := "NoBS"
	if trigger.Kind == "personal" {
		actor = trigger.RepresentedName + "'s agent"
	}
	switch phase {
	case "screened":
		return actor + " passed the security boundary and is selecting delegates…"
	case "routed":
		return actor + " is consulting the relevant delegates…"
	case "retrieved":
		return actor + " found permission-approved evidence…"
	case "synthesizing":
		return actor + " is preparing a concise answer…"
	default:
		return actor + " is checking the relevant context…"
	}
}

func (p *Plugin) failPendingPost(post *model.Post, message string) {
	post.Message = message
	post.Props["noping_state"] = "failed"
	post.Props["noping_security_state"] = "closed"
	_, _ = p.API.UpdatePost(post)
}
