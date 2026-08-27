package main

import (
	"errors"
	"os"
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

func (c *configuration) applyEnvironment() {
	// Environment overrides let immutable Compute Engine/Docker deployments inject
	// Cloud Run identity and secrets without writing them into Mattermost's database.
	if value := strings.TrimSpace(os.Getenv("NOPING_AGENT_SERVICE_URL")); value != "" {
		c.AgentServiceURL = value
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_SERVICE_SIGNING_SECRET")); value != "" {
		c.ServiceSigningSecret = value
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_CLOUD_RUN_AUDIENCE")); value != "" {
		c.CloudRunAudience = value
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_USE_GOOGLE_IDENTITY")); value != "" {
		c.UseGoogleIdentity = parseBool(value, c.UseGoogleIdentity)
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_DEMO_MODE")); value != "" {
		c.DemoMode = parseBool(value, c.DemoMode)
	}
}

func parseBool(value string, fallback bool) bool {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return fallback
	}
}

func (c *configuration) setDefaults() {
	c.applyEnvironment()
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
