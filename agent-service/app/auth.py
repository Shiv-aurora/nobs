from __future__ import annotations

import hashlib
import hmac
import time


class SignatureVerifier:
    def __init__(self, secret: str, demo_mode: bool, max_skew_seconds: int = 300):
        self.secret = secret.encode()
        self.demo_mode = demo_mode
        self.max_skew_seconds = max_skew_seconds

    def verify(self, body: bytes, timestamp: str | None, signature: str | None) -> bool:
        if self.demo_mode and not timestamp and not signature:
            return True
        if not timestamp or not signature:
            return False
        try:
            ts = int(timestamp)
        except ValueError:
            return False
        if abs(int(time.time()) - ts) > self.max_skew_seconds:
            return False
        message = timestamp.encode() + b"." + body
        expected = hmac.new(self.secret, message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
