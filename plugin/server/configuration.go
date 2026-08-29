package main

import (
	"errors"
	"os"
	"strings"
)

type configuration struct {
	AgentServiceURL              string
	ServiceSigningSecret         string
	UseGoogleIdentity            bool
	CloudRunAudience             string
	DemoMode                     bool
	PublicDemoLogin              bool
	DemoLoginUsername            string
	GitHubWebhookSecret          string
	GitHubIdentityMap            string
	GitHubRepositoryMap          string
	GoogleCloudProject           string
	PubSubTopic                  string
	GoogleCalendarCredentialsB64 string
	GoogleCalendarIdentityMap    string
	GoogleCalendarID             string
	GoogleCalendarPollMinutes    string
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
	if value := strings.TrimSpace(os.Getenv("NOPING_PUBLIC_DEMO_LOGIN")); value != "" {
		c.PublicDemoLogin = parseBool(value, c.PublicDemoLogin)
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_DEMO_LOGIN_USERNAME")); value != "" {
		c.DemoLoginUsername = value
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_GITHUB_WEBHOOK_SECRET")); value != "" {
		c.GitHubWebhookSecret = value
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_GITHUB_IDENTITY_MAP")); value != "" {
		c.GitHubIdentityMap = value
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_GITHUB_REPOSITORY_MAP")); value != "" {
		c.GitHubRepositoryMap = value
	}
	if value := strings.TrimSpace(os.Getenv("GOOGLE_CLOUD_PROJECT")); value != "" {
		c.GoogleCloudProject = value
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_PUBSUB_TOPIC")); value != "" {
		c.PubSubTopic = value
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_GOOGLE_CALENDAR_CREDENTIALS_B64")); value != "" {
		c.GoogleCalendarCredentialsB64 = value
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_GOOGLE_CALENDAR_IDENTITY_MAP")); value != "" {
		c.GoogleCalendarIdentityMap = value
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_GOOGLE_CALENDAR_ID")); value != "" {
		c.GoogleCalendarID = value
	}
	if value := strings.TrimSpace(os.Getenv("NOPING_GOOGLE_CALENDAR_POLL_MINUTES")); value != "" {
		c.GoogleCalendarPollMinutes = value
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
	if strings.TrimSpace(c.DemoLoginUsername) == "" {
		c.DemoLoginUsername = "maya"
	}
	if c.UseGoogleIdentity && strings.TrimSpace(c.CloudRunAudience) == "" {
		c.CloudRunAudience = c.AgentServiceURL
	}
	if strings.TrimSpace(c.PubSubTopic) == "" {
		c.PubSubTopic = "noping-work-events"
	}
	if strings.TrimSpace(c.GoogleCalendarID) == "" {
		c.GoogleCalendarID = "primary"
	}
	if strings.TrimSpace(c.GoogleCalendarPollMinutes) == "" {
		c.GoogleCalendarPollMinutes = "5"
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
	if strings.TrimSpace(c.GitHubWebhookSecret) != "" {
		if len(c.GitHubWebhookSecret) < 32 {
			return errors.New("GitHubWebhookSecret must be at least 32 characters")
		}
		if strings.TrimSpace(c.GoogleCloudProject) == "" || strings.TrimSpace(c.GitHubIdentityMap) == "" {
			return errors.New("GoogleCloudProject and GitHubIdentityMap are required when GitHub webhooks are enabled")
		}
		if _, err := parseIdentityMap(c.GitHubIdentityMap); err != nil {
			return err
		}
		if _, err := parseRepositoryMap(c.GitHubRepositoryMap); err != nil {
			return err
		}
	}
	if strings.TrimSpace(c.GoogleCalendarCredentialsB64) != "" {
		if strings.TrimSpace(c.GoogleCloudProject) == "" || strings.TrimSpace(c.GoogleCalendarIdentityMap) == "" {
			return errors.New("GoogleCloudProject and GoogleCalendarIdentityMap are required when Calendar sync is enabled")
		}
		if _, err := newCalendarTokenSource(c.GoogleCalendarCredentialsB64); err != nil {
			return err
		}
		identities, err := parseCalendarIdentityMap(c.GoogleCalendarIdentityMap)
		if err != nil || len(identities) == 0 {
			return errors.New("GoogleCalendarIdentityMap must contain at least one valid identity")
		}
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
