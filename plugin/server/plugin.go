package main

import (
	"sync"

	"github.com/gorilla/mux"
	"github.com/mattermost/mattermost/server/public/model"
	"github.com/mattermost/mattermost/server/public/plugin"
	"github.com/mattermost/mattermost/server/public/pluginapi"
	"github.com/pkg/errors"
)

// Plugin is the server-side boundary between Mattermost and the NoPing agent runtime.
type Plugin struct {
	plugin.MattermostPlugin
	client            *pluginapi.Client
	router            *mux.Router
	configurationLock sync.RWMutex
	configuration     *configuration
	calendarCancel    func()
	calendarWG        sync.WaitGroup
	botUserID         string
	activeSources     sync.Map
}

func (p *Plugin) OnActivate() error {
	p.client = pluginapi.NewClient(p.API, p.Driver)
	botUserID, err := p.client.Bot.EnsureBot(&model.Bot{
		Username:    "nobs",
		DisplayName: "NoBS Agent",
		Description: "Handles routine questions and meeting coordination without wasting human attention.",
	}, pluginapi.ProfileImagePath("assets/logo.png"))
	if err != nil {
		return errors.Wrap(err, "failed to provision NoBS bot")
	}
	p.botUserID = botUserID
	if err := p.OnConfigurationChange(); err != nil {
		return err
	}
	p.router = p.initRouter()
	p.startCalendarPoller()
	return nil
}

func (p *Plugin) OnDeactivate() error {
	if p.calendarCancel != nil {
		p.calendarCancel()
		p.calendarWG.Wait()
	}
	return nil
}
