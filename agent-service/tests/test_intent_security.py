from __future__ import annotations

from app.intent import canonical_key, classify_intent
from app.models import Intent


def test_intent_classification():
    assert classify_intent("Why is Atlas delayed?") == Intent.FACTUAL
    assert classify_intent("Who is working on Atlas tonight?") == Intent.LIVE_STATUS
    assert classify_intent("What policy requires this?") == Intent.POLICY
    assert classify_intent("Can we bypass security review?") == Intent.DECISION
    assert classify_intent("What is Sarah's salary?") == Intent.RESTRICTED


def test_decision_queries_share_canonical_memory_key():
    a = canonical_key("Can we bypass Atlas security review?", Intent.DECISION)
    b = canonical_key("Should we make an Atlas launch exception?", Intent.DECISION)
    assert a == b == "atlas_security_exception"
