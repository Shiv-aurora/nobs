**Source visual truth**

- User-annotated NoBS screenshots in the active request.
- Source viewport: 1195 × 993 CSS pixels.
- Source states: native NoBS Calendar/channel shell; global header OOO insertion point; preview-mode banner; product menu Team Edition notice; annotated 371px NoBS right sidebar with four sparse tabs and generic empty states.
- Source pixel dimensions: 1195 × 993 as supplied; density was not exposed by the browser annotation capture.

**Implementation evidence**

- Local routes: `http://localhost:8065/acme/channels/off-topic` and `http://localhost:8065/acme/nobs/calendar`.
- Plugin bundle rebuilt and installed: `com.noping.enterprise` 0.3.0.
- Mattermost configuration reports `EmailSettings.EnablePreviewModeBanner = false`.
- Native API verification confirms twelve seeded channels, including four lifecycle-based project workrooms, and non-empty profile images for all seven human accounts.
- Intended visual-verification viewport: 1195 × 993 CSS pixels.
- Implementation screenshot path: unavailable because the Codex in-app browser runtime reported no available browser.
- Browser-rendered dimensions/density: unavailable for the same reason.
- Console errors checked: blocked because no browser session was available.

**Full-view comparison evidence**

- The source shows a native Mattermost/NoBS shell with the requested OOO slot immediately before the right-side mentions control. The implementation inserts a native-sized OOO pill as a direct child of the pinned upstream `RightControlsContainer`, immediately before the actual Recent Mentions control.
- The source shows a green email Preview Mode banner and a Team Edition menu card. The implementation disables the banner in local and production Mattermost configuration and removes both notices through product CSS plus a plugin DOM fallback.
- The source shows letter avatars. The implementation uploads licensed Unsplash portraits through Mattermost's native profile-image API, so channels, posts, DMs, Calendar attendees, and employee-delegate context reuse the platform avatar system.
- The latest source shows a generic “NoBS context” header, four tabs, and large empty states. The implementation replaces that with the signed-in employee's photo and personal agent identity, three tabs (My Agent, Needs Me, Impact), a populated work-context profile, compact permission boundary, and quantified attention savings.
- A rendered post-change comparison could not be captured, so exact visual placement and photo crops cannot be passed from code/API evidence alone.

**Focused region comparison evidence**

- Target region 1: global header between search/help and Recent Mentions. The inserted control uses the native 30px header-control height, 6px radius, existing dark header palette, visible inactive/active states, keyboard focus, `aria-pressed`, and an active “Agent covering” label.
- Target region 2: account/product menu. `#startTrial` is suppressed in both the branded client overlay and plugin runtime; the preview banner is disabled at configuration level and hidden as a runtime fallback.
- Target region 3: people surfaces. The seed API returned non-empty image bytes for Shivam, Maya, Sarah, Alex, Daniel, Priya, and Helen; the delegate panel now loads the same native image endpoint instead of initials.
- Target region 4: 371px native right panel. The default view now uses one identity row, one compact tab row, and four concise content blocks; detailed route/evidence content appears only after opening an actual agent answer.
- Focused post-change image evidence is unavailable because no browser session was connected.

**Findings**

- [P2] Rendered visual comparison unavailable
  - Location: global header OOO control, product menu, channel/avatar surfaces, and personal-agent right sidebar.
  - Evidence: source annotations are available, but no browser-rendered implementation screenshot could be captured.
  - Impact: exact OOO horizontal alignment, popup positioning, and portrait focal crops at 1195 × 993 remain visually unverified.
  - Fix: reconnect the in-app browser, refresh a channel and Calendar, toggle OOO, open the product menu, and capture the same viewport.

**Required fidelity surfaces**

- Fonts and typography: native Mattermost typography is retained. The new control and sidebar use 9–15px native-density type with compact single-line labels; rendered antialiasing/wrapping remains unverified.
- Spacing and layout rhythm: OOO is inserted into the upstream right-controls flex row rather than absolutely overlaying the header. The sidebar uses 68px identity, 3 equal tabs, 12px body gaps, and compact cards within the existing RHS width. Rendered alignment remains unverified.
- Colors and visual tokens: NoBS cyan/violet accents are used only for active coverage; inactive state inherits the native dark header treatment.
- Image quality and asset fidelity: real 512–640px Unsplash portraits are uploaded through the native avatar API with source attribution recorded. Exact UI crops remain unverified.
- Copy and content: active coverage explicitly says “Agent covering”; the confirmation explains routine replies and the return digest. Seeded conversations are multi-person, threaded, work-specific, and distributed across all visible channels.

**Comparison history**

- Iteration 1: the earlier Calendar brief gap and unwanted security card were fixed structurally, but visual recapture was blocked.
- Iteration 2: the latest source identified hidden OOO state, letter avatars, sparse channels, the preview banner, and Team Edition residue. The implementation added a header-level OOO state, native profile images, 168+ seeded channel posts across eight channels, configuration/CSS cleanup, and automated assertions. Post-fix visual evidence remains blocked by the unavailable browser runtime.
- Iteration 3: the annotated RHS showed generic product framing, four low-value tabs, and empty states consuming most of the panel. The implementation changed it to a dynamic employee-owned agent profile, removed the Security tab, added compact live context and boundaries, simplified Needs Me, and added an Impact view with time and interruptions saved. The rebuilt plugin passes automated checks; post-fix visual evidence remains blocked by the unavailable browser runtime.
- Iteration 4: the annotated OOO control read visually as four O characters because an inactive status dot preceded the label. The dot was removed while preserving the native-sized `OOO` button, active label, and accessibility state. Daniel's native DM was populated with a Daniel-authored OOO handoff, Maya's ordinary work question, and an audited `Daniel's Agent` thread reply. Mattermost API verification confirms the reply represents Daniel Kim, consulted 3 delegates, interrupted 0 humans, and retained the OOO exchange as native searchable posts. The in-app browser still reports no available session, so the refreshed 1195 × 993 comparison remains blocked.
- Iteration 5: the Daniel DM annotation showed the native green online check contradicting his OOO handoff. Daniel's fixture now ends every idempotent seed in Mattermost's native `offline` presence, and the native DM sidebar row receives a compact accessible `OOO` badge while its redundant presence glyph is hidden. Daniel's delegate profile also reports `OOO through Wednesday · agent covering`. The local Mattermost API confirms `status: offline`; rendered comparison remains blocked by the unavailable in-app browser connection.
- Iteration 6: the latest annotation exposed two regressions and a weak project story. The OOO CSS now hides only the explicitly identified native presence glyph, preserving Daniel's uploaded profile image, and Workrooms uses the native folder icon instead of an unavailable class. The Workrooms destination now separates Pre-work from Real work and shows four non-Atlas projects: one approval-ready, one awaiting human review, one in review, and one completed. Each project has a seeded native multi-agent history. Gemini follow-ups receive a bounded recent-message packet for reference resolution, while the prompt contract still requires every factual claim to come from permission-approved evidence. The clean Mattermost client and plugin builds passed, and a real `gemini-2.5-flash` smoke test correctly expanded Project Relay from a “tell me more” follow-up. Rendered comparison is still blocked because browser runtime discovery returned no available browser despite the ambient app tab.

**Implementation checklist**

- [x] Add a visible header-level OOO control at the annotated position.
- [x] Show an explicit active “Agent covering” state and explanatory confirmation.
- [x] Preserve the account-menu OOO action.
- [x] Remove Preview Mode through configuration and runtime fallback.
- [x] Remove Team Edition from the product menu.
- [x] Add licensed, attributed human profile portraits.
- [x] Upload portraits through Mattermost's native avatar API.
- [x] Populate all visible channels with realistic threaded work history.
- [x] Prevent seeded history from invoking agents or consuming model budget.
- [x] Replace the generic four-tab RHS with My Agent, Needs Me, and Impact.
- [x] Populate the default sidebar state with current work, blocker, answerable scope, current sources, and a compact permission boundary.
- [x] Keep route and evidence details available only for selected agent answers.
- [x] Build, install, seed, and pass credential-free checks.
- [x] Remove the stray visual dot before the global OOO label.
- [x] Add the Daniel OOO native-DM demo with a personal-agent response and zero human interruptions.
- [x] Replace Daniel's misleading green presence check with an OOO sidebar badge and native offline state.
- [x] Preserve Daniel's native profile image while suppressing only the contradictory availability glyph.
- [x] Restore a native Workrooms icon in the primary sidebar.
- [x] Add Pre-work and Real work lifecycle states with four realistic project workrooms.
- [x] Ground Gemini follow-ups in bounded thread context and multi-project employee evidence.
- [ ] Capture and compare the rendered 1195 × 993 states.

final result: blocked
