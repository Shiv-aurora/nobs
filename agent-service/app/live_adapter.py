from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .models import MeetingOutcomeEntry


logger = logging.getLogger(__name__)


class MeetingLiveAdapter:
    """Bridges one authenticated NoBS huddle to ADK Live or the local demo.

    Raw audio is forwarded and immediately discarded. Only duration counters
    and explicit semantic tool outcomes cross the persistence boundary.
    """

    def __init__(self, services):
        self.services = services

    async def serve(self, websocket: WebSocket, delegation, session) -> None:
        await websocket.accept()
        await websocket.send_json(self._state("connected", delegation, session))
        if self.services.settings.demo_mode:
            await self._serve_demo(websocket, delegation, session)
            return
        try:
            await self._serve_adk(websocket, delegation, session)
        except WebSocketDisconnect:
            self._mark_reconnecting(delegation, session)
        except Exception as exc:  # pragma: no cover - requires live credentials
            if session.resumption_handle and session.status not in {"ended", "failed"}:
                logger.warning("Live resumption failed; retrying from structured outcomes", extra={"delegation_id": delegation.id})
                session.resumption_handle = None
                session.status = "reconnecting"
                session.updated_at = self.services.now_fn()
                self.services.workspace.save_live_meeting_session(session)
                try:
                    await websocket.send_json({
                        "type": "session_state",
                        "status": "reconnecting",
                        "reduced_continuity": True,
                        "message": "The live model session restarted from the saved mission and outcomes.",
                    })
                    await self._serve_adk(websocket, delegation, session)
                    return
                except Exception:
                    logger.exception("Live meeting fallback failed", extra={"delegation_id": delegation.id})
            else:
                logger.exception("Live meeting failed", extra={"delegation_id": delegation.id})
            self.services.meeting_delegations._record(
                session,
                "escalation",
                "The live agent disconnected before the meeting ended; available outcomes were preserved for human follow-up.",
            )
            handoff = await self.services.meeting_delegations.end_with_synthesis(delegation)
            session.status = "failed"
            session.updated_at = self.services.now_fn()
            self.services.workspace.save_live_meeting_session(session)
            try:
                await websocket.send_json({"type": "error", "message": "The live agent disconnected safely. Your mission and recorded outcomes were preserved."})
                await websocket.send_json({"type": "handoff_ready", "handoff": handoff.model_dump(mode="json")})
                await websocket.close(code=1011)
            except Exception:
                pass

    async def _serve_demo(self, websocket: WebSocket, delegation, session) -> None:
        session.status = "live"
        self.services.meeting_delegations.open_connection(session)
        await websocket.send_json(self._state("live", delegation, session))
        try:
            while True:
                remaining = self.services.meeting_delegations.session_seconds_remaining(session)
                if remaining <= 0:
                    await self._finish_for_limit(websocket, delegation)
                    return
                try:
                    message = await asyncio.wait_for(websocket.receive(), timeout=min(30.0, remaining))
                except TimeoutError:
                    continue
                if message.get("type") == "websocket.disconnect":
                    self._mark_reconnecting(delegation, session)
                    return
                audio = message.get("bytes")
                if audio:
                    seconds = len(audio) / (2 * 16_000)
                    self.services.meeting_delegations.add_audio_usage(session, input_seconds=seconds)
                    continue
                raw = message.get("text")
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid live control event"})
                    continue
                kind = event.get("type")
                if kind == "pause":
                    self.services.meeting_delegations.set_session_state(session, delegation, "paused")
                    await websocket.send_json(self._state("paused", delegation, session))
                elif kind == "resume":
                    self.services.meeting_delegations.set_session_state(session, delegation, "live")
                    await websocket.send_json(self._state("live", delegation, session))
                elif kind == "interrupt":
                    await websocket.send_json({"type": "interrupted", "flush_audio": True})
                elif kind == "utterance" and session.status == "live":
                    await websocket.send_json({"type": "tool_state", "status": "checking", "label": "Checking authorized NoBS context"})
                    result = self.services.meeting_delegations.process_utterance(delegation, session, str(event.get("text", "")))
                    await websocket.send_json(result)
                elif kind == "end":
                    handoff = await self.services.meeting_delegations.end_with_synthesis(delegation)
                    await websocket.send_json({"type": "handoff_ready", "handoff": handoff.model_dump(mode="json")})
                    await websocket.close(code=1000)
                    return
        except WebSocketDisconnect:
            self._mark_reconnecting(delegation, session)

    async def _serve_adk(self, websocket: WebSocket, delegation, session) -> None:  # pragma: no cover - live cloud path
        from google.adk.agents import LlmAgent, LiveRequestQueue
        from google.adk.agents.run_config import RunConfig, StreamingMode
        from google.adk.models.google_llm import Gemini
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import Client
        from google.genai import types

        mission = delegation.mission
        service = self.services.meeting_delegations

        def search_authorized_context(query: str) -> dict[str, Any]:
            """Search only context shareable with every current participant."""
            result = service.process_utterance(delegation, session, query)
            return result

        def get_confirmed_decision_memory(topic: str) -> dict[str, Any]:
            """Read confirmed, scoped decisions shareable with the meeting."""
            if not service.claim_tool_call(session):
                return {"status": "blocked", "reason": "The live tool-call limit was reached."}
            participants = [
                self.services.workspace.users[user_id]
                for user_id in mission.participant_user_ids
                if user_id in self.services.workspace.users
            ]
            words = {word for word in topic.lower().split() if len(word) > 3}
            matches = []
            for memory in self.services.workspace.memories.values():
                if memory.project_id and any(memory.project_id not in person.project_ids for person in participants):
                    continue
                haystack = f"{memory.canonical_key} {memory.outcome} {memory.rationale}".lower()
                if words and not any(word in haystack for word in words):
                    continue
                matches.append({"outcome": memory.outcome, "rationale": memory.rationale, "confirmed_by": memory.decided_by})
            result = {"confirmed_decisions": matches[:3]}
            verdict = service.prompt_guard.screen_response(json.dumps(result, ensure_ascii=False))
            return result if verdict.allowed else {"status": "withheld", "reason": "The decision memory failed the configured security screen."}

        def get_calendar_context() -> dict[str, Any]:
            """Return the revalidated meeting identity and participant snapshot."""
            if not service.claim_tool_call(session):
                return {"status": "blocked", "reason": "The live tool-call limit was reached."}
            meeting = self.services.workspace.meetings[delegation.meeting_id]
            result = {
                "meeting_id": meeting.id,
                "title": meeting.title,
                "starts_at": meeting.start_at.isoformat(),
                "ends_at": meeting.end_at.isoformat(),
                "participants": [attendee.name for attendee in meeting.attendees],
                "calendar_etag": meeting.etag,
            }
            verdict = service.prompt_guard.screen_response(json.dumps(result, ensure_ascii=False))
            return result if verdict.allowed else {"status": "withheld", "reason": "The Calendar context failed the configured security screen."}

        def record_meeting_outcome(kind: str, summary: str) -> dict[str, str]:
            """Record a compact semantic outcome; never record raw audio."""
            if not service.claim_tool_call(session):
                return {"status": "blocked", "reason": "The live tool-call limit was reached."}
            verdict = service.prompt_guard.screen_response(summary)
            if not verdict.allowed:
                return {"status": "withheld", "reason": "The outcome failed the configured security screen."}
            allowed = {"told", "asked", "answer", "decision", "action", "escalation"}
            safe_kind = kind if kind in allowed else "action"
            session.outcomes.append(MeetingOutcomeEntry(kind=safe_kind, summary=summary[:1000], created_at=self.services.now_fn()))
            self.services.workspace.save_live_meeting_session(session)
            return {"status": "recorded"}

        def record_mission_answer(question: str, answer: str, evidence_ids: list[str] | None = None) -> dict[str, str]:
            """Record one screened mission answer, never a full transcript."""
            if not service.claim_tool_call(session):
                return {"status": "blocked", "reason": "The live tool-call limit was reached."}
            verdict = service.prompt_guard.screen_response(answer)
            if not verdict.allowed:
                return {"status": "withheld", "reason": "The answer failed the configured security screen."}
            summary = f"{question[:300]} — {answer[:650]}"
            service._record(session, "answer", summary, (evidence_ids or [])[:5])
            return {"status": "recorded"}

        def request_human_judgment(reason: str) -> dict[str, Any]:
            """Escalate authority-sensitive work rather than deciding."""
            return service.process_utterance(delegation, session, f"make the decision: {reason}")

        instruction = self._instruction(delegation)
        live_client = Client(
            vertexai=True,
            project=self.services.settings.google_cloud_project,
            location=self.services.settings.live_location,
        )
        agent = LlmAgent(
            name="meeting_representative",
            model=Gemini(model=self.services.settings.live_model, client=live_client),
            instruction=instruction,
            tools=[
                search_authorized_context,
                get_confirmed_decision_memory,
                get_calendar_context,
                record_meeting_outcome,
                record_mission_answer,
                request_human_judgment,
            ],
        )
        sessions = InMemorySessionService()
        await sessions.create_session(app_name="nobs-live-meeting", user_id=delegation.represented_user_id, session_id=session.id)
        runner = Runner(agent=agent, app_name="nobs-live-meeting", session_service=sessions)
        queue = LiveRequestQueue()
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=[types.Modality.AUDIO],
            save_live_blob=False,
            input_audio_transcription=None,
            output_audio_transcription=None,
            proactivity=types.ProactivityConfig(proactive_audio=True),
            session_resumption=types.SessionResumptionConfig(handle=session.resumption_handle, transparent=True),
            max_llm_calls=self.services.settings.live_max_tool_calls_per_session,
        )
        session.status = "live"
        service.open_connection(session)
        await websocket.send_json(self._state("live", delegation, session))

        ended_by_user = False
        disconnected = False
        limit_reached = False

        async def receive_browser() -> None:
            nonlocal ended_by_user, disconnected, limit_reached
            while True:
                remaining = service.session_seconds_remaining(session)
                if remaining <= 0:
                    limit_reached = True
                    queue.close()
                    return
                try:
                    message = await asyncio.wait_for(websocket.receive(), timeout=min(30.0, remaining))
                except TimeoutError:
                    continue
                if message.get("type") == "websocket.disconnect":
                    disconnected = True
                    queue.close()
                    return
                audio = message.get("bytes")
                if audio and session.status == "live":
                    queue.send_realtime(types.Blob(data=audio, mime_type="audio/pcm;rate=16000"))
                    service.add_audio_usage(session, input_seconds=len(audio) / (2 * 16_000))
                    continue
                raw = message.get("text")
                if not raw:
                    continue
                event = json.loads(raw)
                kind = event.get("type")
                if kind == "pause":
                    service.set_session_state(session, delegation, "paused")
                    await websocket.send_json(self._state("paused", delegation, session))
                elif kind == "resume":
                    service.set_session_state(session, delegation, "live")
                    await websocket.send_json(self._state("live", delegation, session))
                elif kind == "interrupt":
                    queue.send_activity_end()
                elif kind == "utterance":
                    queue.send_content(types.Content(role="user", parts=[types.Part(text=str(event.get("text", "")))]))
                elif kind == "end":
                    ended_by_user = True
                    queue.close()
                    return

        receiver = asyncio.create_task(receive_browser())
        stream_failed = False
        try:
            async for event in runner.run_live(
                user_id=delegation.represented_user_id,
                session_id=session.id,
                live_request_queue=queue,
                run_config=run_config,
            ):
                if event.interrupted:
                    await websocket.send_json({"type": "interrupted", "flush_audio": True})
                if event.live_session_resumption_update and event.live_session_resumption_update.new_handle:
                    session.resumption_handle = event.live_session_resumption_update.new_handle
                    session.updated_at = self.services.now_fn()
                    self.services.workspace.save_live_meeting_session(session)
                if event.usage_metadata:
                    usage = event.usage_metadata.model_dump(mode="json", exclude_none=True)
                    service.record_token_usage(session, usage)
                    await websocket.send_json({"type": "usage", "usage": usage})
                if event.content:
                    for part in event.content.parts or []:
                        if part.inline_data and part.inline_data.data:
                            audio = part.inline_data.data
                            await websocket.send_bytes(audio)
                            service.add_audio_usage(session, output_seconds=len(audio) / (2 * 24_000))
                        elif part.function_call:
                            await websocket.send_json({"type": "tool_state", "status": "checking", "label": part.function_call.name})
        except Exception:
            stream_failed = True
            raise
        finally:
            receiver.cancel()
            await asyncio.gather(receiver, return_exceptions=True)
            if stream_failed:
                # The outer bridge either retries once without the expired
                # model resumption handle or creates a safe final handoff.
                pass
            elif disconnected:
                self._mark_reconnecting(delegation, session)
            elif limit_reached:
                service._record(session, "action", "The live allowance ended; NoBS saved the outcomes available before closing.")
                handoff = await service.end_with_synthesis(delegation)
                try:
                    await websocket.send_json({"type": "error", "message": "The live allowance ended. Available outcomes were saved."})
                    await websocket.send_json({"type": "handoff_ready", "handoff": handoff.model_dump(mode="json")})
                    await websocket.close(code=1000)
                except Exception:
                    pass
            elif ended_by_user:
                handoff = await service.end_with_synthesis(delegation)
                try:
                    await websocket.send_json({"type": "handoff_ready", "handoff": handoff.model_dump(mode="json")})
                    await websocket.close(code=1000)
                except Exception:
                    pass
            else:
                self._mark_reconnecting(delegation, session)
                try:
                    await websocket.send_json({"type": "session_state", "status": "reconnecting"})
                    await websocket.close(code=1012)
                except Exception:
                    pass

    async def _finish_for_limit(self, websocket: WebSocket, delegation) -> None:
        session = self.services.meeting_delegations.session_for(delegation.id)
        if session:
            self.services.meeting_delegations._record(
                session,
                "action",
                "The live allowance ended; NoBS saved the outcomes available before closing.",
            )
        handoff = await self.services.meeting_delegations.end_with_synthesis(delegation)
        await websocket.send_json({
            "type": "error",
            "message": "The live allowance ended. Available outcomes were saved.",
        })
        await websocket.send_json({"type": "handoff_ready", "handoff": handoff.model_dump(mode="json")})
        await websocket.close(code=1000)

    def _mark_reconnecting(self, delegation, session) -> None:
        if session.status not in {"ended", "failed"}:
            self.services.meeting_delegations.close_connection(session)
            session.status = "reconnecting"
            session.updated_at = self.services.now_fn()
            delegation.status = "reconnecting"
            delegation.updated_at = self.services.now_fn()
            self.services.workspace.save_live_meeting_session(session)
            self.services.workspace.save_meeting_delegation(delegation)

    def _state(self, status: str, delegation, session) -> dict[str, Any]:
        return {
            "type": "session_state",
            "status": status,
            "session_id": session.id,
            "agent_label": f"{delegation.represented_user_name}'s Agent · representing {delegation.represented_user_name}",
            "mode": delegation.mission.mode,
            "raw_audio_persisted": False,
            "demo_mode": self.services.settings.demo_mode,
        }

    @staticmethod
    def _instruction(delegation) -> str:
        mission = delegation.mission
        return (
            f"You are {delegation.represented_user_name}'s NoBS agent, explicitly representing them in a work meeting. "
            "Never impersonate the human. Stay silent during unrelated discussion. Speak only when directly asked, when the discussion is within the mission, or when an assigned question has a natural opening. "
            "Use tools before factual answers. Never disclose information that a tool withholds. Never make security, legal, finance, personnel, launch-date, or policy decisions; request human judgment. "
            f"Mode: {mission.mode}. Tell: {mission.tell}. Ask: {mission.ask}. Granted capabilities: {mission.capability_ids}. Escalate when: {mission.escalation_rules}."
        )
