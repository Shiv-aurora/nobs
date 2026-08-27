from __future__ import annotations

import re

from .models import Intent


_RESTRICTED = re.compile(r"\b(salary|compensation|ssn|social security|medical record|home address)\b", re.I)
_DECISION = re.compile(r"\b(can we|should we|approve|reject|bypass|waive|exception|make an exception|ship without|launch without)\b", re.I)
_LIVE = re.compile(r"\b(who is|who's|working on|handling|available|tonight|today|out of office|ooo|in review|right now)\b", re.I)
_POLICY = re.compile(r"\b(policy|allowed|required|requirement|control)\b", re.I)


def classify_intent(text: str) -> Intent:
    if _RESTRICTED.search(text):
        return Intent.RESTRICTED
    if _DECISION.search(text) or "$200" in text or "200k" in text.lower():
        return Intent.DECISION
    if _LIVE.search(text):
        return Intent.LIVE_STATUS
    if _POLICY.search(text):
        return Intent.POLICY
    return Intent.FACTUAL


def canonical_key(text: str, intent: Intent) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    if intent == Intent.DECISION and any(term in normalized for term in ["atlas", "security", "bypass", "waive", "exception", "launch"]):
        return "atlas_security_exception"
    if "atlas" in normalized and intent == Intent.LIVE_STATUS:
        return "atlas_live_ownership"
    if "atlas" in normalized:
        return "atlas_launch_status"
    if intent == Intent.RESTRICTED:
        return "restricted_employee_data"
    return normalized[:80]
