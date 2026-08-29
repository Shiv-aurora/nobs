from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .pubsub import PubSubTokenVerifier

from starlette.responses import JSONResponse


SIGNATURE_VERSION = "v1"


@dataclass(frozen=True)
class SignatureVerifier:
    secret: str
    demo_mode: bool
    max_skew_seconds: int = 300

    @staticmethod
    def canonical_message(timestamp: str, method: str, target: str, body: bytes) -> bytes:
        prefix = f"{SIGNATURE_VERSION}\n{timestamp}\n{method.upper()}\n{target}\n".encode()
        return prefix + body

    def sign(self, timestamp: str, method: str, target: str, body: bytes) -> str:
        message = self.canonical_message(timestamp, method, target, body)
        return hmac.new(self.secret.encode(), message, hashlib.sha256).hexdigest()

    def verify(
        self,
        *,
        body: bytes,
        timestamp: str | None,
        signature: str | None,
        version: str | None,
        method: str,
        target: str,
    ) -> bool:
        # Local UI and test harnesses remain frictionless in explicit demo mode.
        if self.demo_mode and not timestamp and not signature and not version:
            return True
        if version != SIGNATURE_VERSION or not timestamp or not signature:
            return False
        try:
            ts = int(timestamp)
        except ValueError:
            return False
        if abs(int(time.time()) - ts) > self.max_skew_seconds:
            return False
        expected = self.sign(timestamp, method, target, body)
        return hmac.compare_digest(expected, signature)


class SignedServiceMiddleware:
    """Authenticates Mattermost plugin-to-agent-service requests.

    This is a pure ASGI middleware so request bodies are buffered once and then
    replayed exactly to FastAPI. Signatures bind the HTTP method and request
    target in addition to the body, preventing cross-endpoint replay.
    """

    def __init__(
        self,
        app: Any,
        verifier: SignatureVerifier,
        pubsub_verifier: PubSubTokenVerifier | None = None,
        pubsub_path: str = "/v1/events/pubsub",
        unauthenticated_paths: frozenset[str] = frozenset({"/healthz"}),
    ):
        self.app = app
        self.verifier = verifier
        self.pubsub_verifier = pubsub_verifier
        self.pubsub_path = pubsub_path
        self.unauthenticated_paths = unauthenticated_paths

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if (
            scope.get("type") != "http"
            or scope.get("method") == "OPTIONS"
            or scope.get("path") in self.unauthenticated_paths
        ):
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        more_body = True
        while more_body:
            message = await receive()
            if message.get("type") == "http.disconnect":
                await self.app(scope, receive, send)
                return
            chunks.append(message.get("body", b""))
            more_body = bool(message.get("more_body", False))
        body = b"".join(chunks)

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_path = scope.get("raw_path") or scope.get("path", "").encode()
        query = scope.get("query_string", b"")
        target = raw_path.decode("latin-1") + ("?" + query.decode("latin-1") if query else "")

        if scope.get("path") == self.pubsub_path and self.pubsub_verifier is not None:
            valid = self.pubsub_verifier.verify(_decode_header(headers.get(b"authorization")))
            auth_challenge = "Bearer"
            detail = "Invalid Pub/Sub push identity"
        else:
            valid = self.verifier.verify(
                body=body,
                timestamp=_decode_header(headers.get(b"x-noping-timestamp")),
                signature=_decode_header(headers.get(b"x-noping-signature")),
                version=_decode_header(headers.get(b"x-noping-signature-version")),
                method=scope.get("method", "GET"),
                target=target,
            )
            auth_challenge = "NoPing-HMAC"
            detail = "Invalid or expired NoPing service signature"
        if not valid:
            response = JSONResponse(
                status_code=401,
                content={"detail": detail},
                headers={"WWW-Authenticate": auth_challenge},
            )
            await response(scope, receive, send)
            return

        delivered = False

        async def replay_receive() -> dict[str, Any]:
            nonlocal delivered
            if delivered:
                # Streaming responses keep a disconnect listener alive after
                # the request body has been replayed. Delegate subsequent
                # receives instead of returning an endless series of empty
                # request frames, which would starve the response stream.
                return await receive()
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_receive, send)


def _decode_header(value: bytes | None) -> str | None:
    return value.decode("latin-1") if value is not None else None
