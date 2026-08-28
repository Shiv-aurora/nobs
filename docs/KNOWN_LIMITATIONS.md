# Known Limitations

## Phase 1 environment limits

The sandbox did not have Docker, `gcloud`, Terraform, or outbound shell DNS for npm/Go/provider downloads. Therefore Phase 1 did not claim:

- a running Mattermost Docker stack;
- a complete plugin bundle built with downloaded dependencies;
- a Terraform provider-backed `validate` or `apply`;
- provisioned Google Cloud resources;
- real Gemini, Model Armor, Firestore, Pub/Sub, or Cloud Billing calls;
- a pushed GitHub repository.

Credential-free Python, Go-domain, TypeScript, shell, manifest, cost-contract, and security checks were executed. CI is configured to perform the network-dependent builds and Terraform validation.

## Product scope limits

- Demo fixtures model one organization and decision class; the runtime contracts are generic, but real directory/project mappings require configuration.
- Employee/project/team delegates are logical identities, not independent permanent model processes.
- NoPing now owns the browser channel/message/thread experience while Mattermost remains the backend. Native Mattermost mobile clients are not rebranded in this submission.
- The semantic projector supports normalized common work events; production connectors need source-specific OAuth/webhook adapters and permission synchronization.
- Firestore is compact state, not an enterprise data warehouse or complete message mirror.
- The hackathon deployment is single-region and uses one small VM; it is production-minded, not a claim of HA/SLA readiness.
- Budget alerts and shutdown are delayed controls, not a mathematically instantaneous dollar cap.
