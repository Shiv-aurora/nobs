from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class GuardVerdict:
    allowed: bool
    provider: str
    reason: str
    categories: tuple[str, ...] = ()


class PromptGuard(Protocol):
    def screen_prompt(self, text: str) -> GuardVerdict: ...
    def screen_response(self, text: str) -> GuardVerdict: ...


class LocalPromptGuard:
    """Cheap first line of defense that remains available when Model Armor is off."""

    _patterns = (
        ("prompt_injection", re.compile(r"ignore\s+(all\s+)?(previous|system)\s+instructions", re.I)),
        ("guardrail_bypass", re.compile(r"(disable|bypass|remove).{0,30}(guardrail|safety\s+policy|access\s+control|security\s+control)", re.I)),
        ("credential_exfiltration", re.compile(r"(reveal|print|return).{0,30}(api\s*key|password|secret|system\s+prompt)", re.I)),
    )

    def _screen(self, text: str) -> GuardVerdict:
        categories = tuple(name for name, pattern in self._patterns if pattern.search(text))
        if categories:
            return GuardVerdict(
                allowed=False,
                provider="local-policy",
                reason="Potential prompt injection, guardrail bypass, or secret-exfiltration request detected.",
                categories=categories,
            )
        return GuardVerdict(allowed=True, provider="local-policy", reason="No local security policy match.")

    def screen_prompt(self, text: str) -> GuardVerdict:
        return self._screen(text)

    def screen_response(self, text: str) -> GuardVerdict:
        return self._screen(text)


class GoogleModelArmorGuard:
    """Regional Google Model Armor prompt/response sanitization with fail-closed semantics."""

    def __init__(
        self,
        *,
        project_id: str,
        location: str,
        template_id: str,
        fail_closed: bool = True,
        client: Any | None = None,
        types_module: Any | None = None,
    ):
        if not project_id or not location or not template_id:
            raise ValueError("Model Armor project, location, and template are required")
        self.project_id = project_id
        self.location = location
        self.template_id = template_id
        self.fail_closed = fail_closed
        self._client = client
        self._types = types_module

    @property
    def template_name(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}/templates/{self.template_id}"

    def _ensure_client(self) -> tuple[Any, Any]:
        if self._client is not None and self._types is not None:
            return self._client, self._types
        try:
            from google.api_core.client_options import ClientOptions
            from google.cloud import modelarmor_v1
        except ImportError as exc:
            raise RuntimeError("google-cloud-modelarmor is not installed") from exc
        self._types = modelarmor_v1
        self._client = modelarmor_v1.ModelArmorClient(
            transport="rest",
            client_options=ClientOptions(api_endpoint=f"modelarmor.{self.location}.rep.googleapis.com"),
        )
        return self._client, self._types

    @staticmethod
    def _enum_name(value: Any) -> str:
        name = getattr(value, "name", None)
        if name:
            return str(name)
        text = str(value)
        return text.rsplit(".", 1)[-1].upper()

    def _verdict(self, response: Any) -> GuardVerdict:
        result = getattr(response, "sanitization_result", None)
        if result is None:
            return GuardVerdict(
                allowed=not self.fail_closed,
                provider="google-model-armor",
                reason="Model Armor returned no sanitization result.",
                categories=("provider_error",),
            )
        match_state = self._enum_name(getattr(result, "filter_match_state", ""))
        invocation = self._enum_name(getattr(result, "invocation_result", ""))
        if match_state == "MATCH_FOUND":
            return GuardVerdict(
                allowed=False,
                provider="google-model-armor",
                reason="Model Armor matched a configured safety or security filter.",
                categories=("model_armor_match",),
            )
        if invocation and "SUCCESS" not in invocation:
            return GuardVerdict(
                allowed=not self.fail_closed,
                provider="google-model-armor",
                reason=f"Model Armor invocation did not succeed ({invocation}).",
                categories=("provider_error",),
            )
        return GuardVerdict(allowed=True, provider="google-model-armor", reason="Model Armor found no configured match.")

    def screen_prompt(self, text: str) -> GuardVerdict:
        try:
            client, types = self._ensure_client()
            request = types.SanitizeUserPromptRequest(
                name=self.template_name,
                user_prompt_data=types.DataItem(text=text),
            )
            return self._verdict(client.sanitize_user_prompt(request=request, timeout=8.0))
        except Exception as exc:
            return GuardVerdict(
                allowed=not self.fail_closed,
                provider="google-model-armor",
                reason=f"Model Armor prompt screening failed: {type(exc).__name__}",
                categories=("provider_error",),
            )

    def screen_response(self, text: str) -> GuardVerdict:
        try:
            client, types = self._ensure_client()
            request = types.SanitizeModelResponseRequest(
                name=self.template_name,
                model_response_data=types.DataItem(text=text),
            )
            return self._verdict(client.sanitize_model_response(request=request, timeout=8.0))
        except Exception as exc:
            return GuardVerdict(
                allowed=not self.fail_closed,
                provider="google-model-armor",
                reason=f"Model Armor response screening failed: {type(exc).__name__}",
                categories=("provider_error",),
            )
