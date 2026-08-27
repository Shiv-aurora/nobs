package main

import "github.com/mattermost/mattermost/server/public/model"

func (p *Plugin) publishRunUpdate(teamID, userID string, payload map[string]any) {
	broadcast := &model.WebsocketBroadcast{UserId: userID}
	if teamID != "" {
		broadcast.TeamId = teamID
	}
	p.API.PublishWebSocketEvent("run_update", payload, broadcast)
}

func (p *Plugin) publishDecisionUpdate(userID string, payload map[string]any) {
	p.API.PublishWebSocketEvent("decision_update", payload, &model.WebsocketBroadcast{UserId: userID})
}
