package main

import (
	"sync"

	"github.com/gorilla/mux"
	"github.com/mattermost/mattermost/server/public/plugin"
	"github.com/mattermost/mattermost/server/public/pluginapi"
)

// Plugin is the server-side boundary between Mattermost and the NoPing agent runtime.
type Plugin struct {
	plugin.MattermostPlugin
	client            *pluginapi.Client
	router            *mux.Router
	configurationLock sync.RWMutex
	configuration     *configuration
}

func (p *Plugin) OnActivate() error {
	p.client = pluginapi.NewClient(p.API, p.Driver)
	if err := p.OnConfigurationChange(); err != nil {
		return err
	}
	p.router = p.initRouter()
	return nil
}
