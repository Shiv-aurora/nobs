# NoBS

**Fewer pings. Shorter meetings. More actual work.**

NoBS is an agent-native workplace communication layer built on Mattermost. It turns ordinary workplace events into durable, governed missions: real specialist agents resolve coordination work in parallel, deterministic policy protects identity/evidence/authority, human judgment pauses and resumes the same mission, and a separate least-privilege executor applies approved actions safely.

The judged meeting mission uses Google ADK and Vertex AI **`gemini-3.5-flash`**. Employee, project, team, policy, and authority delegates are logical organizational identities—not fake deployed agents.

## Architecture thesis

```text
Mattermost session + signed request
                 ↓
 Private NoBS Gateway — access, admission, Model Armor
                 ↓
 Meeting Mission Controller (Gemini 3.5)
             ↙ parallel ↘
 Work Graph Agent       Policy Evidence Agent
             ↘           ↙
      deterministic Evidence Critic
                 ↓
 Meeting Resolution Agent (Gemini 3.5)
                 ↓
 deterministic Authority Gate
          ↙ no action      human required ↘
     complete          durable checkpoint
                                ↓ approved live source
                  private idempotent Action Executor
```

Firestore owns mission/step/checkpoint/command state; Pub/Sub provides at-least-once work and command delivery; Google Agent Registry catalogs four versioned executable services; Agent Engine Sessions stores ADK context; Memory Bank stores explicit preferences only; Model Armor fails closed around every ADK call. Mattermost/PostgreSQL remains the collaboration source of truth.

See the [judge-focused architecture](docs/ARCHITECTURE.md), [agent catalog](docs/AGENT_CATALOG.md), and [architecture decisions](docs/ARCHITECTURE_DECISIONS.md).

## Product proof

- **Less Ping:** a normal channel question receives a permission-aware sourced reply without interrupting a coworker. Logical delegate resolution is deterministic; one Gemini synthesizer answers.
- **Restricted-data refusal:** compensation requests are denied before private evidence or Gemini.
- **Less Meeting:** a real bounded mission runs two specialist agents concurrently, validates evidence, and recommends cancel/shorten/keep.
- **Human authority:** a launch security decision persists one organizer checkpoint and resumes the same mission.
- **Action safety:** demo fixtures never generate external commands. A live Calendar source requires organizer approval, current ETag, a transactional lease, idempotency, and post-write verification in the separate executor.
- **Injection defense:** poisoned sources are quarantined before specialist context; Model Armor screens model input and output.
- **Memory isolation:** confirmed decisions stay fact/policy/authority-bound in Firestore; preference Memory Bank cannot widen access or approve work.

## Repository map

```text
plugin/                         Mattermost Go boundary + React/TypeScript NoBS UI
agent-service/                  private gateway + governed ADK mission runtime
executor-service/               private least-privilege action executor
seed/                           source fixtures only; no runtime transcripts/results
deploy/local/                   local Mattermost/PostgreSQL/agent stack
deploy/gcp/terraform/           bounded Google Cloud infrastructure
deploy/gcp/budget-guard/        independent 90% VM-stop control
deploy/gcp/vm/                  production collaboration VM stack
docs/                           architecture, security, data, evaluation, deployment
```

## Credential-free verification

```bash
./scripts/check.sh
```

Verified result: **87** agent-runtime tests, **8** budget-guard tests, **6** executor tests, all Go packages, strict TypeScript, Python compilation, shell/static validation, credential scan, and Git whitespace passed. Terraform with Google provider 8.0.0 also validates. Details: [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md).

## Local stack

Requires Docker, Docker Compose, Go, Node/npm, and Python 3.11+.

```bash
cp deploy/local/.env.example deploy/local/.env
./scripts/local-up.sh
```

Open messaging at `http://localhost:8065/acme/channels/project-atlas` or Calendar at `http://localhost:8065/acme/nobs/calendar`. Local demo mode uses deterministic executable programs and a fixed test clock; production uses real wall time, Model Armor, ADK, Gemini 3.5, Agent Registry discovery, Agent Engine Sessions, and Firestore.

## Google Cloud

The existing demo URL is [35-202-201-122.sslip.io](https://35-202-201-122.sslip.io/). The VM may be intentionally stopped between demo sessions. The bounded project is `noping-agentic-shiv-2026`; internal `noping-*` names remain for compatibility.

- one `e2-small` Compute Engine VM for Caddy/Mattermost/PostgreSQL;
- private agent and executor Cloud Run services, scale to zero, max one;
- Firestore Native, Pub/Sub + DLQs, Secret Manager, Artifact Registry;
- Vertex AI `gemini-3.5-flash`, Google ADK, Agent Registry, Agent Engine Sessions/Memory Bank;
- Model Armor, structured logging, OpenTelemetry to Cloud Trace;
- existing project-filtered **$25** budget and independent budget guard.

Deployment and honest platform disclosures are in [`docs/GOOGLE_CLOUD_DEPLOYMENT.md`](docs/GOOGLE_CLOUD_DEPLOYMENT.md) and live progress is in [`docs/STATUS.md`](docs/STATUS.md).

## License and attribution

NoBS original work is Apache-2.0. The build preserves upstream Mattermost notices. See [`UPSTREAM.md`](UPSTREAM.md), [`docs/OSS_DISCLOSURE.md`](docs/OSS_DISCLOSURE.md), and [`docs/CONTRIBUTION_MAP.md`](docs/CONTRIBUTION_MAP.md).
