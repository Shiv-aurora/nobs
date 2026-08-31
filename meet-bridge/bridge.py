from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import signal
import time
from urllib import error, request

import websockets


class AgentAPI:
    def __init__(self) -> None:
        self.base_url = os.getenv("NOPING_AGENT_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
        self.signing_secret = os.getenv("NOPING_SERVICE_SIGNING_SECRET", "")
        self.bridge_token = os.getenv("NOPING_MEET_BRIDGE_TOKEN", "")
        if not self.signing_secret or not self.bridge_token:
            raise RuntimeError(
                "NOPING_SERVICE_SIGNING_SECRET and NOPING_MEET_BRIDGE_TOKEN are required"
            )

    def headers(self, method: str, target: str, body: bytes = b"") -> dict[str, str]:
        timestamp = str(int(time.time()))
        canonical = f"v1\n{timestamp}\n{method.upper()}\n{target}\n".encode() + body
        signature = hmac.new(self.signing_secret.encode(), canonical, hashlib.sha256).hexdigest()
        return {
            "Content-Type": "application/json",
            "X-NoPing-Timestamp": timestamp,
            "X-NoPing-Signature-Version": "v1",
            "X-NoPing-Signature": signature,
            "X-NoPing-Bridge-Token": self.bridge_token,
        }

    def post(self, target: str, payload: dict) -> dict | None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        outgoing = request.Request(
            self.base_url + target,
            data=body,
            method="POST",
            headers=self.headers("POST", target, body),
        )
        try:
            with request.urlopen(outgoing, timeout=20) as response:
                if response.status == 204:
                    return None
                return json.loads(response.read())
        except error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"Agent service returned {exc.code}: {detail}") from exc

    def websocket_url(self, job: dict) -> tuple[str, dict[str, str]]:
        target = (
            f"/v1/live/meetings/{job['delegation_id']}"
            f"?user_id={job['represented_user_id']}&nonce={job['session_nonce']}"
        )
        scheme = "wss" if self.base_url.startswith("https://") else "ws"
        authority = self.base_url.split("://", 1)[1]
        return f"{scheme}://{authority}{target}", self.headers("GET", target)


class MeetBridge:
    def __init__(self) -> None:
        self.api = AgentAPI()
        self.bridge_id = os.getenv("NOPING_MEET_BRIDGE_ID", "demo-meet-bridge")
        self.poll_seconds = float(os.getenv("NOPING_MEET_BRIDGE_POLL_SECONDS", "1"))
        self.runner = Path(__file__).with_name("meet_browser.cjs")
        self.stopping = False

    def update(self, job: dict, status: str, **extra) -> None:
        payload = {"bridge_id": self.bridge_id, "status": status, **extra}
        self.api.post(f"/v1/meeting-bridge/sessions/{job['session_id']}/status", payload)

    async def run_job(self, job: dict) -> None:
        environment = os.environ.copy()
        environment["NOPING_MEET_JOB"] = json.dumps(job, separators=(",", ":"))
        process = await asyncio.create_subprocess_exec(
            "node",
            str(self.runner),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=environment,
        )
        audio_in: asyncio.Queue[bytes] = asyncio.Queue(maxsize=32)
        live = asyncio.Event()
        ended = asyncio.Event()
        terminal_status: str | None = None

        async def read_browser() -> None:
            nonlocal terminal_status
            assert process.stdout is not None
            while line := await process.stdout.readline():
                message = json.loads(line)
                if encoded := message.get("audio_in"):
                    try:
                        audio_in.put_nowait(base64.b64decode(encoded))
                    except asyncio.QueueFull:
                        _ = audio_in.get_nowait()
                        audio_in.put_nowait(base64.b64decode(encoded))
                    continue
                if notice := message.get("notice"):
                    print(notice, flush=True)
                    continue
                status = message.get("status")
                if status in {"joining", "awaiting_admission", "live", "ended", "failed"}:
                    extra = {}
                    if message.get("participant_display_name"):
                        extra["participant_display_name"] = message["participant_display_name"]
                    if message.get("error"):
                        extra["error"] = message["error"]
                    await asyncio.to_thread(self.update, job, status, **extra)
                    print(f"{job['meeting_title']}: {status.replace('_', ' ')}", flush=True)
                    if status == "live":
                        live.set()
                    if status in {"ended", "failed"}:
                        terminal_status = status
                        ended.set()

        async def read_stderr() -> None:
            assert process.stderr is not None
            while line := await process.stderr.readline():
                print(f"[meet-browser] {line.decode(errors='replace').rstrip()}", flush=True)

        browser_reader = asyncio.create_task(read_browser())
        stderr_reader = asyncio.create_task(read_stderr())
        wait_live = asyncio.create_task(live.wait())
        wait_process = asyncio.create_task(process.wait())
        completed, _ = await asyncio.wait({wait_live, wait_process}, return_when=asyncio.FIRST_COMPLETED)
        if wait_process in completed and not live.is_set():
            await browser_reader
            await stderr_reader
            if terminal_status is None:
                await asyncio.to_thread(
                    self.update,
                    job,
                    "failed",
                    error="The Meet browser exited before the participant joined.",
                )
            return

        websocket_url, headers = self.api.websocket_url(job)
        async with websockets.connect(websocket_url, additional_headers=headers, max_size=2**20) as socket:
            async def send_audio() -> None:
                while not ended.is_set():
                    await socket.send(await audio_in.get())

            async def receive_agent() -> None:
                nonlocal terminal_status
                async for message in socket:
                    if isinstance(message, bytes):
                        assert process.stdin is not None
                        encoded = base64.b64encode(message).decode()
                        process.stdin.write(json.dumps({"audio_out": encoded}).encode() + b"\n")
                        await process.stdin.drain()
                        continue
                    event = json.loads(message)
                    if event.get("type") == "handoff_ready":
                        if terminal_status is None:
                            await asyncio.to_thread(self.update, job, "ended")
                            terminal_status = "ended"
                        ended.set()
                        return

            sender = asyncio.create_task(send_audio())
            receiver = asyncio.create_task(receive_agent())
            end_waiter = asyncio.create_task(ended.wait())
            await asyncio.wait({receiver, end_waiter, wait_process}, return_when=asyncio.FIRST_COMPLETED)
            sender.cancel()
            receiver.cancel()
            end_waiter.cancel()

        if process.returncode is None:
            process.terminate()
            await process.wait()
        await browser_reader
        await stderr_reader
        if terminal_status is None:
            await asyncio.to_thread(
                self.update,
                job,
                "failed",
                error="The live media connection ended before Meet reported that the call ended.",
            )

    async def run(self) -> None:
        print(f"Meet bridge {self.bridge_id} is ready at {self.api.base_url}", flush=True)
        while not self.stopping:
            try:
                job = await asyncio.to_thread(
                    self.api.post,
                    "/v1/meeting-bridge/jobs/claim",
                    {"bridge_id": self.bridge_id},
                )
            except Exception as exc:
                print(f"Meet bridge cannot reach the local agent service: {exc}", flush=True)
                await asyncio.sleep(self.poll_seconds)
                continue
            if not job:
                await asyncio.sleep(self.poll_seconds)
                continue
            try:
                await self.run_job(job)
            except Exception as exc:
                try:
                    await asyncio.to_thread(self.update, job, "failed", error=str(exc))
                except Exception as update_exc:
                    print(f"Bridge could not persist its failure state: {update_exc}", flush=True)
                print(f"Bridge job failed: {exc}", flush=True)


async def main() -> None:
    bridge = MeetBridge()
    loop = asyncio.get_running_loop()
    for name in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(name, setattr, bridge, "stopping", True)
    await bridge.run()


if __name__ == "__main__":
    asyncio.run(main())
