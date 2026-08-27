package main

import (
	"errors"
	"strings"
)

type configuration struct {
	AgentServiceURL      string
	ServiceSigningSecret string
	DemoMode             bool
}

func (c *configuration) clone() *configuration {
	if c == nil {
		return &configuration{DemoMode: true}
	}
	copy := *c
	return &copy
}

func (c *configuration) validate() error {
	if c.DemoMode {
		return nil
	}
	if strings.TrimSpace(c.AgentServiceURL) == "" {
		return errors.New("AgentServiceURL is required when DemoMode is disabled")
	}
	if strings.TrimSpace(c.ServiceSigningSecret) == "" {
		return errors.New("ServiceSigningSecret is required when DemoMode is disabled")
	}
	return nil
}

func (p *Plugin) getConfiguration() *configuration {
	p.configurationLock.RLock()
	defer p.configurationLock.RUnlock()
	return p.configuration.clone()
}

func (p *Plugin) OnConfigurationChange() error {
	var next configuration
	if err := p.API.LoadPluginConfiguration(&next); err != nil {
		return err
	}
	if err := next.validate(); err != nil {
		return err
	}
	p.configurationLock.Lock()
	p.configuration = &next
	p.configurationLock.Unlock()
	return nil
}
