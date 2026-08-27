# NoPing Vision

## Promise

**Slack made every employee reachable. NoPing makes every employee’s knowledge reachable without making every employee interruptible.**

NoPing is an AI-native workplace communication system where every employee, project, team, and policy has a permission-aware delegate. Those delegates resolve routine organizational questions between themselves and surface only the work that genuinely requires a human’s judgment, authority, or private knowledge.

## Product thesis

Existing workplace tools organize the company around channels and unread messages. NoPing organizes it around:

- **intent** — what someone needs to know or decide;
- **entities** — people, projects, teams, policies, work items, and decisions;
- **evidence** — the authorized facts behind each claim;
- **authority** — who may answer, approve, or delegate;
- **attention** — whether a person needs to be interrupted;
- **memory** — whether the organization has already resolved the same decision class.

The default flow is:

```text
employee → personal delegate → organization router → entity delegates → sourced answer
```

Only unresolved or authority-bound work continues to:

```text
correct human → structured decision → scoped organizational memory
```

## Why Mattermost remains underneath

NoPing does not throw away years of company-product engineering. Mattermost remains the mature substrate for identities, teams, sessions, permissions, rooms, direct messages, files, search, notifications, realtime delivery, and PostgreSQL persistence. NoPing replaces the default interaction and attention model through a first-class full-screen plugin.

Rooms still exist when humans actually need conversation. They are no longer the first tool used merely because somebody needs a fact.

## Hackathon slice

The long-term company is an AI-native replacement for Slack. The hackathon proves one narrow job extremely well:

> A frontline employee gets a trustworthy cross-department answer or decision without knowing the org chart and without waking the wrong people.

This makes the “unlikely hero” Maya, an overnight support representative—not an executive or developer.

## Three immediate wow moments

1. **Ask the organization.** Maya asks why Atlas has not shipped. NoPing discovers project, engineering, and security context without Maya choosing a channel or person.
2. **Agents communicate so humans do not have to.** A sourced answer appears with the visible delegate route and `0 people interrupted`; a poisoned source is quarantined.
3. **Human attention is treated as authority, not fallback.** A $200K security exception becomes exactly one complete Needs You card for Alex, the active delegated approver, because the model is prohibited from making the decision.

## What every employee “agent” really means

NoPing does not allocate a separate foundation model or permanent process per employee. Each delegate is a logical, isolated operating boundary composed of:

- entity identity;
- roles and permissions;
- authorized data scopes;
- current semantic work state;
- decision authority and delegation;
- memory references;
- approved tools;
- audit identity.

The underlying Gemini model can be shared, but Sarah’s delegate and Maya’s delegate cannot retrieve the same data or exercise the same authority. That separation is functional, testable, and auditable—not a collection of cosmetic system prompts.

## Product principles

1. **No unsupported claims.** Say “Daniel opened PR #892 twenty minutes ago,” not “Daniel is coding right now.”
2. **Policy before generation.** Permission and authority decisions are deterministic and happen before Gemini receives evidence.
3. **Evidence is part of the answer.** Claims include source, timestamp, freshness, and confidence.
4. **Human attention is scarce.** Escalation is a deliberate product outcome with one compact decision card.
5. **Decisions become memory, not permanent truth.** Memory is scoped, fact-bound, attributable, and expiring.
6. **Agents are bounded.** Models cannot grant themselves permissions, mutate policy, or approve authority-bound work.
7. **Enterprise means recoverable.** Events are idempotent, routes are traceable, failures do not silently trigger unsafe fallbacks, and cost limits fail closed.

## Success metric

The primary metric is **interruptions avoided without reducing answer quality or violating authority**.

Supporting metrics:

- percentage of questions resolved without humans;
- evidence coverage and freshness;
- repeated-question cache/memory reuse;
- number of human escalations correctly routed on first attempt;
- restricted requests stopped before retrieval;
- poisoned sources quarantined;
- cost per resolved organizational request.

## Out of scope for the hackathon

- replacing every Mattermost screen or native mobile client;
- autonomous employment, compensation, legal, or security decisions;
- covert employee surveillance or claims of real-time physical activity;
- ingesting entire corporate histories without retention controls;
- unrestricted model-to-model conversations;
- production-scale multi-region high availability;
- billing beyond the bounded hackathon profile.
