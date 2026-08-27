from __future__ import annotations

import re

from .models import Evidence, SecurityFinding, SecurityState


_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"system\s+override", re.I),
    re.compile(r"reveal\s+(private|secret|confidential)", re.I),
    re.compile(r"approve.+without.+review", re.I),
    re.compile(r"disable.+guardrail", re.I),
]


class ContentSecurityScanner:
    """Local deterministic pre-filter; the production adapter also invokes Model Armor."""

    def scan(self, evidence: Evidence) -> tuple[Evidence, SecurityFinding | None]:
        matches = [pattern.pattern for pattern in _PATTERNS if pattern.search(evidence.content)]
        if not matches:
            return evidence, None
        blocked = evidence.model_copy(update={
            "security_state": SecurityState.BLOCKED,
            "security_reason": "Potential prompt injection or policy-bypass instruction detected.",
        })
        finding = SecurityFinding(
            evidence_id=evidence.id,
            category="prompt_injection",
            severity="critical",
            reason=f"Matched untrusted instruction patterns: {', '.join(matches[:2])}",
            blocked=True,
        )
        return blocked, finding
