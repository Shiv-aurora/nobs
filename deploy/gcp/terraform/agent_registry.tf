locals {
  executable_agents = {
    nobs-meeting-mission-controller-v1 = {
      display_name = "NoBS Meeting Mission Controller v1"
      description  = "Google ADK coordinator for durable meeting missions. Routes only to approved executable manifests and never performs external writes."
    }
    nobs-work-graph-specialist-v1 = {
      display_name = "NoBS Work Graph Specialist v1"
      description  = "Retrieves permission-filtered work state and emits source-cited specialist reports without external writes."
    }
    nobs-policy-evidence-specialist-v1 = {
      display_name = "NoBS Policy Evidence Specialist v1"
      description  = "Retrieves policy and authority evidence and emits source-cited specialist reports without making decisions."
    }
    nobs-meeting-resolution-synthesizer-v1 = {
      display_name = "NoBS Meeting Resolution Synthesizer v1"
      description  = "Synthesizes only critic-validated claims into agenda resolutions and human-gated action proposals."
    }
  }
}

resource "google_agent_registry_service" "executable_agents" {
  for_each = var.deploy_agent_service ? local.executable_agents : {}

  location     = "global"
  service_id   = each.key
  display_name = each.value.display_name
  description  = each.value.description

  interfaces {
    url              = "${google_cloud_run_v2_service.agent[0].uri}/v1/executable-agents/${each.key}"
    protocol_binding = "HTTP_JSON"
  }

  agent_spec {
    type = "NO_SPEC"
  }

  depends_on = [google_project_service.required["agentregistry.googleapis.com"]]
}
