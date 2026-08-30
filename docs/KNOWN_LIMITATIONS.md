# Known limitations

- The hackathon profile is bounded rather than highly available: one `e2-small` Mattermost/PostgreSQL VM and Cloud Run maximum one instance per service.
- Agent code executes on private Cloud Run. The deployed Agent Engine resource supplies Sessions and preference Memory Bank; NoBS does not claim an Agent Runtime deployment.
- Agent Gateway is not deployed because the current critical path has no A2A/MCP network hop to govern. It becomes relevant when an external A2A/MCP tool is added.
- Native Agent Registry verifies four executable service IDs; richer schema, tool, scope, identity, and approval fields remain in typed Firestore manifests.
- Memory Bank is integrated only for explicit allowlisted preferences and intentionally has no authority effect. Confirmed decision memory remains in Firestore.
- The current mission status enum is intentionally compact. Event waits, cancellation, and named manual-review substates are not yet exposed as first-class public statuses.
- Consequential write verification supports Google Calendar cancel/shorten/update-agenda commands only. Mattermost writes remain in the collaboration plugin boundary.
- Production Calendar execution must use the dedicated demo account and a real ingested Calendar event. Seeded demo meetings can never create commands.
- GitHub/Jira adapters use bounded normalized projections in the demo; Jira is not claimed as a live deployed connector.
- The source-poisoning scanner and Model Armor protect the demonstrated ingress/agent paths; this is not a claim that arbitrary future connectors are safe without their own parser and authorization review.
- Mattermost mobile clients are not rebranded; the submitted experience is the web client.
- The public URL uses `sslip.io` over the existing static IP, not a purchased custom domain.
- Final executor IAM/Cloud Run rollout and production trace/browser evidence are pending the explicit approval recorded in `STATUS.md`.
