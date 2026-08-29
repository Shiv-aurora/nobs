# NoBS Vision

## Promise

**Saving corporate from corporate BS.**

Modern work wastes attention in two places: constant pings and meetings that spend most of their time discovering context. NoBS gives every employee a permission-aware personal agent so routine coordination can happen without interrupting people.

> Ask my context, not my attention.

> Agents do the coordination. Humans do the judgment.

## Less Ping

Messaging remains the product's default experience. When someone asks a work question in a DM or channel, NoBS deterministically identifies the responsible scope and gives the appropriate personal, project, team, policy, or authority delegate the first chance to respond. People do not need to mention a bot.

Delegates may answer only from evidence the requester is authorized to access. Restricted requests stop before retrieval, poisoned content is quarantined, and genuine judgment becomes one structured human handoff. A leading `--direct` bypasses delegation and consumes no model budget.

## Less Meeting

Calendar is a major secondary destination. Before an eligible work meeting, attendee agents form a private bounded swarm. They gather current evidence, compare updates, resolve routine agenda items, expose work actions, and produce a brief that contains:

- what happened;
- what agents resolved;
- work completed or investigated;
- remaining disputes or authority decisions;
- proposed actions and owners;
- the recommended meeting disposition;
- human attention and meeting time saved.

If every agenda item is resolved and no authority or policy boundary remains, NoBS recommends cancellation. Otherwise it preserves only the unresolved human decisions and recommends a shorter meeting. Agents never modify Google Calendar without the organizer's explicit confirmation.

## Product foundation

Mattermost remains the mature collaboration substrate for identities, sessions, permissions, channels, DMs, threads, reactions, files, search, notifications, realtime delivery, accessibility, and PostgreSQL persistence. It is an implementation dependency, not visible co-branding. NoBS adds the agent layer through a pinned client overlay, plugin hooks, native extension surfaces, and a separate bounded agent runtime.

Internal plugin IDs, environment variables, Firestore collections, and deployment resource names retain `noping` for compatibility. Visible product text, routes, titles, and agent identities say NoBS. The current gradient N is temporary and centralized for later replacement.

## Demo proof

1. Maya asks why Atlas is delayed in an ordinary channel message. Four delegates answer in a native thread with zero humans interrupted.
2. A salary request is denied before private data is retrieved.
3. The Atlas engineering sync is fully resolved and recommended for cancellation, returning 30 minutes to every attendee.
4. Atlas launch readiness is compressed from 60 to 15 minutes for one security authority decision; malicious agenda content is quarantined before Gemini sees it.
5. The private Agent Workroom shows attendee, project, Gemini Enterprise, Gemini Code Assist, and GitHub coordination without claiming that NoBS edits, merges, or deploys code.
6. OOO mode lets the delegate handle routine work and prepares a grouped return digest.

## Product principles

1. Messaging stays primary; analytics and meeting preparation never replace conversation.
2. Permission and authority checks happen before model retrieval or synthesis.
3. Agent turns show evidence, conclusions, open questions, and handoffs—not hidden chain-of-thought.
4. Calendar and code mutations remain human-confirmed.
5. Confirmed answers and outcomes become scoped, attributable, expiring memory.
6. Integrations are named accurately and never imply unsupported execution or endorsement.
7. Cost and failure boundaries remain explicit: Cloud Run `min=0`, `max=1`, bounded calls, rate limits, and the existing `$25` guard.

## Success metric

The core metric is **human attention saved without reducing answer quality or violating authority**.

Supporting metrics include interruptions avoided, meeting minutes returned, requests resolved without another employee, evidence coverage, correctly routed escalations, restricted requests stopped before retrieval, quarantined sources, and cost per resolved request or meeting.

## Out of scope

- native mobile apps;
- autonomous compensation, legal, employment, or security decisions;
- unrestricted background agent conversations;
- covert employee surveillance;
- autonomous code editing, merging, or deployment by the demo adapter;
- production-scale multi-region infrastructure;
- higher fixed cost or removal of the existing budget guard.
