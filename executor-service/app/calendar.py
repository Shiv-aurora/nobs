from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from threading import RLock
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from .models import ActionCommand, ProviderResult


class StaleETag(RuntimeError):
    pass


class AuthorizedUser(BaseModel):
    client_id: str
    client_secret: str
    refresh_token: str
    token_uri: str = "https://oauth2.googleapis.com/token"


class CalendarAdapter:
    def apply(self, command: ActionCommand) -> ProviderResult:
        raise NotImplementedError


class GoogleCalendarAdapter(CalendarAdapter):
    API = "https://www.googleapis.com/calendar/v3"

    def __init__(self, credentials_b64: str, calendar_id: str = "primary", client: httpx.Client | None = None):
        try:
            raw = base64.b64decode(credentials_b64.strip(), validate=True)
            self.credentials = AuthorizedUser.model_validate_json(raw)
        except Exception as exc:
            raise ValueError("Google Calendar credentials are not valid authorized-user JSON") from exc
        self.calendar_id = calendar_id
        self.client = client or httpx.Client(timeout=15.0)
        self._lock = RLock()
        self._token = ""
        self._expires_at = datetime.min.replace(tzinfo=timezone.utc)

    def _access_token(self) -> str:
        now = datetime.now(timezone.utc)
        with self._lock:
            if self._token and self._expires_at > now + timedelta(seconds=90):
                return self._token
            response = self.client.post(self.credentials.token_uri, data={
                "client_id": self.credentials.client_id,
                "client_secret": self.credentials.client_secret,
                "refresh_token": self.credentials.refresh_token,
                "grant_type": "refresh_token",
            })
            response.raise_for_status()
            payload = response.json()
            self._token = str(payload["access_token"])
            self._expires_at = now + timedelta(seconds=int(payload["expires_in"]))
            return self._token

    def apply(self, command: ActionCommand) -> ProviderResult:
        if not command.target_ref.startswith("calendar:"):
            raise ValueError("Executor received a non-Calendar target")
        event_id = command.target_ref.split(":", 1)[1]
        endpoint = f"{self.API}/calendars/{quote(self.calendar_id, safe='')}/events/{quote(event_id, safe='')}"
        headers = {"Authorization": f"Bearer {self._access_token()}", "If-Match": command.expected_etag}
        if command.command_type == "calendar.cancel":
            response = self.client.delete(endpoint, headers=headers)
        elif command.command_type == "calendar.shorten":
            current = self.client.get(endpoint, headers={"Authorization": headers["Authorization"]})
            current.raise_for_status()
            start = datetime.fromisoformat(str(current.json()["start"]["dateTime"]).replace("Z", "+00:00"))
            end = start + timedelta(minutes=int(command.payload["duration_minutes"]))
            response = self.client.patch(endpoint, headers=headers, json={"end": {"dateTime": end.isoformat()}})
        else:
            response = self.client.patch(endpoint, headers=headers, json={"description": "\n".join(command.payload.get("agenda", []))})
        if response.status_code == 412:
            raise StaleETag("Calendar event changed after approval")
        response.raise_for_status()
        response_hash = hashlib.sha256(response.content).hexdigest()
        if command.command_type == "calendar.cancel":
            verify = self.client.get(endpoint, headers={"Authorization": headers["Authorization"]})
            verified = verify.status_code in {404, 410} or verify.json().get("status") == "cancelled"
        else:
            verify = self.client.get(endpoint, headers={"Authorization": headers["Authorization"]})
            verify.raise_for_status()
            verified = bool(verify.json().get("etag"))
        return ProviderResult(applied_etag=response.headers.get("etag"), response_hash=response_hash, verified=verified)
