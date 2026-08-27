package main

import (
	"errors"
	"strings"
)

type configuration struct {
	AgentServiceURL      string
	ServiceSigningSecret string
	UseGoogleIdentity    bool
	CloudRunAudience     string
	DemoMode             bool
}

func (c *configuration) clone() *configuration {
	if c == nil {
		return &configuration{
			AgentServiceURL:      "http://agent-service:8080",
			ServiceSigningSecret: "dev-only-secret",
			DemoMode:             true,
		}
	}
	copy := *c
	return &copy
}

func (c *configuration) setDefaults() {
	if strings.TrimSpace(c.AgentServiceURL) == "" {
		c.AgentServiceURL = "http://agent-service:8080"
	}
	if strings.TrimSpace(c.ServiceSigningSecret) == "" && c.DemoMode {
		c.ServiceSigningSecret = "dev-only-secret"
	}
	if c.UseGoogleIdentity && strings.TrimSpace(c.CloudRunAudience) == "" {
		c.CloudRunAudience = c.AgentServiceURL
	}
}

func (c *configuration) validate() error {
	c.setDefaults()
	if !c.DemoMode && strings.TrimSpace(c.ServiceSigningSecret) == "" {
		return errors.New("ServiceSigningSecret is required when DemoMode is disabled")
	}
	if c.UseGoogleIdentity && !strings.HasPrefix(strings.TrimSpace(c.CloudRunAudience), "https://") {
		return errors.New("CloudRunAudience must be an HTTPS URL when Google identity is enabled")
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
