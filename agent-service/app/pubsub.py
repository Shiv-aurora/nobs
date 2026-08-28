import base64
import binascii
import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import WorkEvent


class PubSubMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    data: str
    message_id: str = Field(alias="messageId")
    attributes: dict[str, str] = Field(default_factory=dict)
    publish_time: str | None = Field(default=None, alias="publishTime")
    ordering_key: str | None = Field(default=None, alias="orderingKey")


class PubSubPushEnvelope(BaseModel):
    message: PubSubMessage
    subscription: str
    deliveryAttempt: int | None = None

    def decode_work_event(self) -> WorkEvent:
        try:
            raw = base64.b64decode(self.message.data, validate=True)
            payload: Any = json.loads(raw)
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Pub/Sub message data must be base64-encoded JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("Pub/Sub event payload must be a JSON object")
        return WorkEvent.model_validate(payload)


class PubSubTokenVerifier:
    """Verifies Google-signed OIDC tokens on authenticated Pub/Sub push.

    The validator is injectable for deterministic tests. Production lazily uses
    google-auth and additionally pins the service-account email to prevent a
    valid token from an unrelated principal being accepted.
    """

    def __init__(
        self,
        *,
        audience: str,
        service_account_email: str,
        demo_mode: bool,
        token_validator: Callable[[str, str], dict[str, Any]] | None = None,
    ) -> None:
        self.audience = audience
        self.service_account_email = service_account_email
        self.demo_mode = demo_mode
        self._token_validator = token_validator

    def verify(self, authorization: str | None) -> bool:
        if self.demo_mode and not authorization:
            return True
        if not authorization or not authorization.startswith("Bearer "):
            return False
        token = authorization.removeprefix("Bearer ").strip()
        if not token or not self.audience or not self.service_account_email:
            return False
        try:
            claims = self._validate(token)
        except Exception:
            return False
        email = claims.get("email")
        verified = claims.get("email_verified")
        return email == self.service_account_email and verified in {True, "true"}

    def _validate(self, token: str) -> dict[str, Any]:
        if self._token_validator is not None:
            return self._token_validator(token, self.audience)
        try:
            from google.auth.transport.requests import Request  # type: ignore[import-not-found]
            from google.oauth2 import id_token  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - deployment-only path
            raise RuntimeError("Install noping-agent-service[google] for Pub/Sub OIDC verification") from exc
        return id_token.verify_oauth2_token(token, Request(), audience=self.audience)
