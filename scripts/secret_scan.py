#!/usr/bin/env python3
"""Small fail-closed scanner for credentials accidentally committed to the handoff."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW_MARKERS = {
    "dev-only-secret",
    "from-secret-manager",
    "replace-me",
    "change-me",
    "example",
    "dummy",
    "test-secret",
    "your-",
    "<",
    "$(",
    "${",
}
PATTERNS = {
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "GitHub token": re.compile(r"gh[pousr]_[0-9A-Za-z]{30,}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "generic secret assignment": re.compile(
        r"(?i)(?:api[_-]?key|client[_-]?secret|password|signing[_-]?secret)\s*[:=]\s*['\"]([^'\"\n]{12,})['\"]"
    ),
}


def tracked_files() -> list[Path]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
        return [ROOT / item.decode() for item in output.split(b"\0") if item]
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Source archives intentionally omit .git. Scan the extracted tree instead
        # so `make check` remains a valid distribution-level verification command.
        ignored = {".git", ".pytest_cache", "__pycache__", "node_modules", ".terraform", "dist"}
        return [path for path in ROOT.rglob("*") if path.is_file() and not any(part in ignored for part in path.parts)]


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        if not path.is_file() or path.stat().st_size > 2_000_000 or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".zip", ".gz"}:
            continue
        try:
            text = path.read_text(errors="strict")
        except UnicodeDecodeError:
            continue
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                candidate = match.group(1) if match.lastindex else match.group(0)
                lowered = candidate.lower()
                if any(marker in lowered for marker in ALLOW_MARKERS):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(ROOT)}:{line}: possible {name}")
    if findings:
        print("Credential scan failed:", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("Credential scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
