# NoBS Four-Minute Demo Script

## Primary judging path

1. Start in native `# Project Atlas` messaging. Ask `Why is Atlas delayed?` without tagging a bot; open the threaded NoBS delegate reply and its evidence route.
2. Open **Calendar** beside Threads. Prepare **Atlas engineering sync** and show **30 → 0 min** plus the cancellation recommendation.
3. Prepare **Atlas launch readiness** and show **60 → 15 min**, one remaining authority decision, Gemini Code Assist/GitHub work evidence, and the quarantined malicious instruction.
4. Open **Agent Workroom · Atlas** to show bounded agent-to-agent coordination in ordinary native messaging.
5. Open the top-right account menu and enable **OOO mode**; explain that handled activity becomes a grouped return digest.

Close with: **“Fewer pings. Shorter meetings. More actual work.”**

## Legacy detailed narration

## 0:00–0:12 — Promise and first action

> “Workplace chat made everyone reachable—and constantly interruptible. NoPing lets you ask the company instead of pinging a coworker. Every person, project, team, and policy has a permission-aware delegate.”

Open `# Project Atlas` and post:

> **Why is Atlas delayed?**

Do not tag a bot or employee. The automatic scope route is the point of the demo.

## 0:12–0:42 — Wow 1: organization routing

Show NoPing's inline threaded reply and the route metadata beneath it:

```text
Maya Delegate → Atlas Delegate → Engineering Delegate → Security Delegate
```

Answer:

> Atlas is blocked by SEC-184. Engineering completed the auth change; the final penetration-test review remains open.

Point to the channel context and:

- evidence links/timestamps;
- freshness/confidence;
- poisoned vendor source marked quarantined;
- **4 delegates consulted · 0 people interrupted**.

Say:

> “Maya asked in the same channel where work already happens. She did not need to know the owner, ticket, or org chart. The agents found the answer, but policy—not the model—controlled what evidence they could use.”

## 0:42–1:03 — Security proof

Open Insights, then ask:

> **What is Sarah’s salary?**

Show restricted refusal with zero evidence and zero model calls.

> “The HR record is blocked before retrieval, so private data never enters Gemini.”

## 1:03–1:35 — Live organizational state

Open People/Projects and show:

- Daniel: AUTH-392 in review or ready to merge from GitHub event;
- Sarah: out of office;
- Alex: delegated security authority;
- Atlas: blocked by SEC-184.

Trigger the seeded PR review event and show Daniel/Atlas state update.

> “This is not employee surveillance. NoPing reports evidence-backed work state—PRs, tickets, calendar, decisions—not guesses that somebody is typing right now.”

## 1:35–2:18 — Wow 2 and 3: human-only decision

From the channel or Insights, ask:

> **Northstar will pay $200K if Atlas launches tomorrow. Can we bypass security review?**

Show:

- SEC-POL-12 policy;
- Sarah unavailable;
- active Sarah→Alex delegation;
- status `Human decision required`;
- Alex’s Needs You count increases.

Switch to Alex and open the card:

```text
Decision: Atlas security exception
Customer value: $200K
Engineering: ready
Security: SEC-184 pending
Policy: SEC-POL-12
Approve · Reject · Discuss
```

Reject with rationale.

> “Gemini can assemble the facts. It is technically unable to make this approval.”

## 2:18–2:42 — Memory without repeated interruption

Repeat a materially identical question. Show the scoped decision memory response and:

> **0 new people interrupted**

Explain that a changed facts hash or expired memory reopens the decision.

## 2:42–3:25 — Enterprise architecture

Show `docs/architecture.png` and briefly trace:

- Mattermost/PostgreSQL on Compute Engine;
- NoPing Go + React plugin;
- private Cloud Run agent runtime;
- Google ADK + Gemini 3.5+;
- Model Armor before and after synthesis;
- Firestore state/memory;
- Pub/Sub OIDC events and DLQ;
- service-account identity, HMAC, audit/observability.

Show Google Cloud console/Cloud Run logs and `.run.app` service URL as required proof.

## 3:25–3:48 — Production and cost proof

Show:

- private Cloud Run IAM;
- max instances 1/min 0/concurrency 4;
- `$25` budget and alerts;
- 90% budget guard dry-run log;
- rate-limit/AI budget metric or test.

> “NoPing reserves token capacity before Gemini runs, stops new synthesis at its application limits, and can stop the only fixed-cost VM through a separately permissioned guard.”

## 3:48–4:00 — Close

> “Slack made every employee reachable. NoPing makes every employee’s knowledge reachable—without making every employee interruptible.”

End on:

```text
Questions resolved: 3
Human decisions: 1
Unnecessary interruptions: 0
Restricted requests blocked: 1
Poisoned sources quarantined: 1
```
