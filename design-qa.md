# NoBS Calendar Native-Shell Design QA

## Evidence

- Source visual truth: `/Users/shivamarora/Documents/Code/noping/output/design-qa/messaging-native-reference.png`
- Implementation: `/Users/shivamarora/Documents/Code/noping/output/design-qa/calendar-native-final.png`
- Latest implementation: `/Users/shivamarora/Documents/Code/noping/output/design-qa/calendar-agent-meeting-final.jpg`
- Annotated-layout implementation: `/Users/shivamarora/Documents/Code/noping/output/design-qa/calendar-agent-meeting-30-final.jpg`
- Full-view comparison: `/Users/shivamarora/Documents/Code/noping/output/design-qa/native-shell-comparison.png`
- Focused shell/header comparison: `/Users/shivamarora/Documents/Code/noping/output/design-qa/native-shell-header-comparison.png`
- Viewport and state: authenticated Acme workspace, light center channel, 1327 × 1103 CSS px, device pixel ratio 1.7
- Source pixels: 1327 × 1103
- Implementation pixels: 1327 × 1103
- Density normalization: none required; both captures came from the same in-app browser tab, viewport, and DPR
- Latest capture: 1327 × 1103 CSS px at DPR 4 (5308 × 4412 output pixels); compared against the prior 1327 × 1103 Calendar capture in one review pass

## Full-view comparison

The post-fix Calendar keeps the native global header, Acme workspace sidebar, Threads and Calendar destinations, channel list, direct-message list, and app bar in exactly the same shell as Project Atlas. Calendar replaces only the center region. Its list/detail split uses the same compact density, border rhythm, typography, theme colors, and control treatment as the native messaging surface.

## Focused-region comparison

The focused comparison confirms that the global bar height, sidebar width, workspace selector, search field, navigation rows, channel rows, active-state treatment, center header height, icon sizing, and title typography remain aligned. Calendar uses the upstream icon font and existing logo assets; no replacement CSS art or improvised brand asset was introduced.

## Required fidelity surfaces

- Fonts and typography: inherited native font stack; center title, metadata, list labels, and buttons follow the messaging hierarchy and optical weights.
- Spacing and layout rhythm: native 56 px center header, persistent 264 px sidebar, compact meeting rows, 4–5 px radii, 1 px dividers, and no elevated dashboard cards.
- Colors and visual tokens: Calendar now uses `--center-channel-*`, `--button-*`, and `--link-color` theme tokens. Status colors remain semantic and restrained.
- Image quality and assets: the supplied NoBS logo remains limited to existing identity/empty states; Calendar uses the native calendar and refresh icons. The official Gemini asset is unchanged in the detailed activity feed.
- Copy and content: AI-marketing language was replaced by workplace labels such as “Meeting brief,” “Preparation activity,” “Related work,” “Recommendation,” and “Share brief.”

## Comparison history

1. P1 — Calendar replaced the native channel controller, so the workspace sidebar disappeared.
   - Fix: the pinned Mattermost team route now mounts the real upstream `Sidebar` alongside the team-scoped Calendar pluggable.
   - Post-fix evidence: both comparison images show the identical Acme sidebar; Calendar remains highlighted beside Threads.
2. P1 — The first Calendar treatment looked like a separate AI dashboard because it used gradients, large promotional metrics, pill-heavy cards, broad rounded corners, and marketing copy.
   - Fix: removed gradients and shadows, tightened spacing and type, adopted native theme tokens, flattened surfaces, and rewrote section labels as ordinary work UI.
   - Post-fix evidence: the full and focused comparisons show matching visual density and hierarchy.
3. P2 — The native Threads link inherited the plugin route and resolved under `/com.noping.enterprise/calendar/threads`.
   - Fix: anchor the native link to the current team’s `/acme/threads` route.
   - Post-fix evidence: Calendar → Threads → Calendar → Project Atlas navigation completed successfully.
4. P2 — The attendee strip exposed a desktop horizontal scrollbar.
   - Fix: preserve horizontal access while hiding the decorative scrollbar chrome.
   - Post-fix evidence: final Calendar capture has no visible strip scrollbar or document-level overflow.
5. P1 — The preparation activity was the product's main story but occupied only the narrow main-column card and read like four status rows.
   - Fix: promoted it to a full-width **Agent meeting** surface spanning both detail columns, added a participant roster, ten timestamped turns over 15 minutes, explicit questions, evidence, conclusions, and handoffs.
   - Post-fix evidence: the latest capture shows the agent conversation using the entire center width below the decision summary while the native workspace shell remains intact.
6. P2 — The meeting brief and related work had the wrong hierarchy for the demo story.
   - Fix: moved Meeting brief into the right decision rail, retained Related work directly below it, and left the main column available for time saved and the full conversation.
7. P2 — Agent identities were abstract initials and GitHub had no recognizable identity.
   - Fix: mapped personal delegates to native Mattermost profile-image endpoints, used the existing project icon for Atlas, the native GitHub icon, and the official Gemini asset already used by the integration.
8. P1 — Related work, recommendation, and sharing were isolated in the right rail instead of reading as outcomes of time saved.
   - Fix: moved all three beneath the Time saved summary in the left column and changed the summary grid to two equal tracks. Meeting brief now owns the opposite column by itself.
   - Post-fix evidence: the annotated-layout capture shows a balanced 50/50 summary with the requested outcome hierarchy and the agent meeting beginning only after the taller column ends.
9. P1 — Ten short status turns did not feel like agents actually held an engineering meeting.
   - Fix: expanded the seeded engineering sync to 30 evidence-backed turns across Atlas, Daniel, GitHub, Gemini Code Assist, Shivam, Maya, and Priya over 15 minutes. The exchange now covers branch state, missing review, diff inspection, background-resume testing, CI retry classification, artifact verification, customer impact, rollback ownership, and code-owner review.
   - Post-fix evidence: the final capture and live DOM show **30 messages · 7 agents** with questions, replies, tool updates, handoffs, disagreement resolution, and a bounded final recommendation.

## Verification

- Primary interactions: Calendar → Threads → Calendar → Project Atlas; all routes resolved correctly.
- Meeting preparation: cancellation and shortened-meeting proof cases passed.
- Revised seeded engineering-sync preparation: 30 turns, 7 agents/integrations, 15-minute timeline, realistic software-delivery evidence, and final cancellation recommendation verified in the live DOM.
- Demo access: the native login page exposes **Enter demo workspace · No password needed** and returns directly to Project Atlas.
- Messaging density: Project Atlas now contains three substantial multi-person threads plus six additional realistic status, OOO, security, ownership, and delegate-saved-time updates.
- Responsive checks: 1440 × 900, 1024 × 600, 768 × 1024, and 390 × 844 passed with no document-level horizontal overflow.
- Console errors: no new Calendar application error observed; the deliberate logout/login test produced only the expected expired-session requests and a pre-existing autoplay warning.
- Automated result: focused Calendar browser suite 2/2 passed; TypeScript and static validation passed.

## Findings

No actionable P0, P1, or P2 mismatch remains. The center region is necessarily denser than a message timeline because it presents an agenda and meeting brief, but it now behaves and reads as a native destination inside the same product.

## Follow-up polish

- P3: upload photographic seed avatars if the demo needs recognizable faces instead of Mattermost's generated user images. The UI now uses the native image pipeline, so no component change is required.

final result: passed
