# Google Meet bridge

This single-worker demo bridge turns a persisted NoBS meeting delegation into a
real, explicitly named Google Meet participant. It does not use the Calendar
action executor and never persists raw meeting audio.

The bridge polls the private agent service for one leased join, opens the
validated `meet.google.com` URL in a persistent Chrome profile, reports honest
join/admission states, and relays 16 kHz meeting audio to the existing Live
WebSocket. The service returns 24 kHz Gemini Live PCM, which the browser injects
into a synthetic microphone track used by Meet.

## Local demo

1. Start or rebuild the local NoBS stack.
2. Export the same `NOPING_SERVICE_SIGNING_SECRET` and
   `NOPING_MEET_BRIDGE_TOKEN` values used by `deploy/local/.env`.
3. Set `NOPING_MEET_PROFILE_DIR` to a private persistent directory for the
   dedicated agent's Chrome session. The launcher defaults to the ignored
   `.local/meet-bridge-profile` directory.
4. Install dependencies with `python -m pip install -e meet-bridge` and
   `npm --prefix e2e install`, then run `python meet-bridge/bridge.py` (or
   `scripts/start-meet-bridge.sh`). The bridge uses installed Google Chrome and
   does not download a second browser.
5. The first run opens Chrome. Sign in to the dedicated, visibly named agent
   Google account. Keep the bridge running.
6. Start a Google Calendar event's Meet call, then click **Send my Agent** in
   NoBS. If Meet requires admission, NoBS shows that state until the host admits
   the agent.

Set `NOPING_DEMO_MODE=false` for the local agent-service container when
demonstrating bidirectional voice. Deterministic demo mode validates the bridge
and policy state machine but intentionally does not transcribe raw audio or call
Gemini Live.

The Meet DOM is an external integration surface and can change. The bridge fails
with a visible reason instead of claiming attendance when it cannot prove the
participant joined.
