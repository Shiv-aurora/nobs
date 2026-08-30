# Executable agent catalog

The runtime accepts only approved version `1.0.0` manifests. Native Google Agent Registry discovery verifies that all four service IDs exist; the richer manifest below is also persisted in Firestore.

| ID | Kind | Runtime | Model | Tools / effects | Identity |
|---|---|---|---|---|---|
| `agent:meeting-mission-controller` | ADK `LlmAgent` | private Cloud Run | `gemini-3.5-flash` | bounded plan only; no writes | `noping-agent@…` |
| `agent:work-graph-specialist` | ADK `LlmAgent` | same runtime, parallel node | `gemini-3.5-flash` | authorized work/evidence reads | `noping-agent@…` |
| `agent:policy-evidence-specialist` | ADK `LlmAgent` | same runtime, parallel node | `gemini-3.5-flash` | policy, delegation, availability reads | `noping-agent@…` |
| `agent:meeting-resolution-synthesizer` | ADK `LlmAgent` | same runtime | `gemini-3.5-flash` | typed recommendation only; no writes | `noping-agent@…` |

Evidence Critic and Authority Gate are real executable workflow nodes but deterministic code, not independent LLM agents. The Live Representative remains a distinct executable feature on the disclosed secondary Gemini Live model; it is not part of the judged Gemini 3.5 meeting mission.

## Logical delegate directory

Employee, project, team, policy, and authority delegates are records used for model-free scope and authority resolution. They have represented entities, relationships, evidence boundaries, and availability, but no model, process, deployment, or runtime identity.

## Lifecycle

The application manifest records owner, stable ID, semantic version, deployment revision, schemas, capabilities, approved tools, scopes, identity, model, health, approval, and timestamps. A route can select only an approved healthy version. A release changes the deployed revision; schema/capability changes require a manifest version change.
