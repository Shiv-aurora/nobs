#!/usr/bin/env python3
"""Credential-free repository validation for CI and the handoff bundle."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAILURES: list[str] = []


def fail(message: str) -> None:
    FAILURES.append(message)


def check_json(path: Path) -> None:
    try:
        json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001 - validation utility
        fail(f"invalid JSON {path.relative_to(ROOT)}: {exc}")


def check_yaml(path: Path) -> None:
    try:
        yaml.safe_load(path.read_text())
    except Exception as exc:  # noqa: BLE001 - validation utility
        fail(f"invalid YAML {path.relative_to(ROOT)}: {exc}")


def balanced_hcl(path: Path) -> None:
    text = path.read_text()
    stack: list[tuple[str, int]] = []
    pairs = {"}": "{", "]": "[", ")": "("}
    opening = set(pairs.values())
    in_string = False
    escape = False
    in_line_comment = False
    in_block_comment = False
    i = 0
    line = 1
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if ch == "\n":
            line += 1
            in_line_comment = False
        if in_line_comment:
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if not in_string and ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if not in_string and ((ch == "/" and nxt == "/") or ch == "#"):
            in_line_comment = True
            i += 2 if ch == "/" else 1
            continue
        if ch == '"':
            if not escape:
                in_string = not in_string
            escape = False
            i += 1
            continue
        if in_string:
            escape = ch == "\\" and not escape
            if ch != "\\":
                escape = False
            i += 1
            continue
        if ch in opening:
            stack.append((ch, line))
        elif ch in pairs:
            if not stack or stack[-1][0] != pairs[ch]:
                fail(f"unbalanced HCL {path.relative_to(ROOT)} line {line}: unexpected {ch}")
                return
            stack.pop()
        i += 1
    if in_string:
        fail(f"unterminated string in {path.relative_to(ROOT)}")
    if in_block_comment:
        fail(f"unterminated block comment in {path.relative_to(ROOT)}")
    if stack:
        fail(f"unclosed delimiter in {path.relative_to(ROOT)} opened line {stack[-1][1]}")


def extract_number(text: str, name: str, default: float | None = None) -> float | None:
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*([0-9.]+)", text, re.MULTILINE)
    return float(match.group(1)) if match else default


def check_cost_and_security_contract() -> None:
    tf_dir = ROOT / "deploy/gcp/terraform"
    all_tf = "\n".join(path.read_text() for path in sorted(tf_dir.glob("*.tf")))
    variables = (tf_dir / "variables.tf").read_text()
    cloud_run = (tf_dir / "cloud_run.tf").read_text()
    compute = (tf_dir / "compute.tf").read_text()
    firestore = (tf_dir / "firestore.tf").read_text()
    networking = (tf_dir / "networking.tf").read_text()

    budget = extract_number(variables, "default", None)
    budget_block = re.search(r'variable "budget_amount_usd"\s*\{(.*?)\n\}', variables, re.DOTALL)
    if not budget_block or extract_number(budget_block.group(1), "default") != 25:
        fail("budget_amount_usd must default to exactly 25")
    if "var.budget_amount_usd > 0 && var.budget_amount_usd <= 25" not in variables:
        fail("Terraform must reject budgets above $25")
    if cloud_run.count("max_instance_count = 1") < 2 or cloud_run.count("min_instance_count = 0") < 2:
        fail("both Cloud Run services must remain min=0/max=1")
    if 'default     = "e2-small"' not in variables:
        fail("Mattermost VM must default to e2-small")
    if 'contains(["e2-small", "e2-medium"]' not in variables:
        fail("VM type validation must restrict deployments to e2-small/e2-medium")
    if not re.search(r'type\s*=\s*"pd-standard"', compute):
        fail("Mattermost disk must use pd-standard")
    if 'point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_DISABLED"' not in firestore:
        fail("Firestore PITR must remain disabled in the hackathon cost profile")
    if 'source_ranges = ["35.235.240.0/20"]' not in networking:
        fail("SSH must be restricted to the IAP TCP forwarding range")
    if 'resource "google_compute_address" "mattermost"' not in networking:
        fail("Mattermost must use a stable Google Cloud address for judging")
    if 'billing_budget_publishes_updates' not in (tf_dir / "pubsub.tf").read_text():
        fail("Billing Budgets service agent must be able to publish budget notifications")
    if re.search(r'member\s*=\s*"(?:allUsers|allAuthenticatedUsers)"', all_tf):
        fail("Terraform grants a public Cloud Run IAM principal")
    for forbidden in ("railway", "vercel", "supabase", "cloud sql", "gke", "redis"):
        if forbidden in all_tf.lower():
            fail(f"forbidden production dependency found in Terraform: {forbidden}")
    required_limits = {
        "NOPING_MAX_USER_PER_MINUTE": "3",
        "NOPING_MAX_USER_PER_DAY": "20",
        "NOPING_MAX_ORG_PER_DAY": "60",
        "NOPING_MODEL_MAX_CALLS_PER_QUERY": "4",
        "NOPING_MODEL_MAX_CALLS_PER_DAY": "200",
        "NOPING_MODEL_MAX_INPUT_TOKENS_PER_DAY": "1000000",
        "NOPING_MODEL_MAX_OUTPUT_TOKENS_PER_DAY": "100000",
    }
    for name, value in required_limits.items():
        pattern = rf'name\s*=\s*"{re.escape(name)}".*?value\s*=\s*"{re.escape(value)}"'
        if not re.search(pattern, cloud_run, re.DOTALL):
            fail(f"missing enforced Cloud Run limit {name}={value}")



def check_markdown_links() -> None:
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for path in ROOT.glob("**/*.md"):
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        for raw_target in pattern.findall(path.read_text()):
            target = raw_target.strip().split()[0].strip("<>\"")
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            relative = target.split("#", 1)[0].split("?", 1)[0]
            if not relative:
                continue
            candidate = (path.parent / relative).resolve()
            try:
                candidate.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"Markdown link escapes repository in {path.relative_to(ROOT)}: {target}")
                continue
            if not candidate.exists():
                fail(f"broken local Markdown link in {path.relative_to(ROOT)}: {target}")


def check_required_files() -> None:
    required = [
        "README.md",
        "VISION.md",
        "IMPLEMENTATION.md",
        "docs/ARCHITECTURE.md",
        "docs/SECURITY_MODEL.md",
        "docs/COST_MODEL.md",
        "docs/CODEX_HANDOFF.md",
        "docs/DEMO_SCRIPT.md",
        "docs/architecture.png",
        "deploy/gcp/scripts/deploy-all.sh",
        "deploy/gcp/terraform/versions.tf",
        "plugin/plugin.json",
        "agent-service/app/main.py",
    ]
    for relative in required:
        if not (ROOT / relative).is_file():
            fail(f"required handoff file missing: {relative}")


def check_noping_shell_contract() -> None:
    transformer = (ROOT / "deploy/gcp/vm/customize_mattermost_shell.py").read_text()
    login = (ROOT / "deploy/gcp/vm/login/index.html").read_text()
    caddy = (ROOT / "deploy/gcp/vm/Caddyfile").read_text()
    required_brand_markers = (
        "/noping-brand/logo.png",
        "/noping-brand/text-logo.png",
    )
    for marker in required_brand_markers:
        if marker not in transformer:
            fail(f"NoPing startup shell is missing {marker}")
    required_browser_markers = (
        "__landingPageSeen__",
        "__landing-preference__",
        "'browser'",
        "response.headers.get('Token')",
        "MMAUTHTOKEN=",
        "MMUSERID=",
        "Secure; SameSite=Lax",
    )
    for marker in required_browser_markers:
        if marker not in login:
            fail(f"NoPing sign-in is missing browser preference marker {marker}")
    required_proxy_markers = ("@authenticatedNoPing", "MMAUTHTOKEN", "rewrite * /app-shell.html", "/login?redirect_to=/noping", "@legacyLanding")
    for marker in required_proxy_markers:
        if marker not in caddy:
            fail(f"Caddy NoPing authentication boundary is missing {marker}")


def iter_files(patterns: Iterable[str]) -> Iterable[Path]:
    for pattern in patterns:
        yield from ROOT.glob(pattern)


def main() -> int:
    for path in iter_files(("**/*.json",)):
        if "/.git/" not in str(path) and "node_modules" not in path.parts:
            check_json(path)
    for path in [ROOT / "deploy/local/docker-compose.yml", ROOT / "deploy/gcp/vm/docker-compose.yml", ROOT / ".github/workflows/ci.yml"]:
        if path.exists():
            check_yaml(path)
    for path in sorted((ROOT / "deploy/gcp/terraform").glob("*.tf")):
        balanced_hcl(path)
    check_cost_and_security_contract()
    check_required_files()
    check_noping_shell_contract()
    check_markdown_links()

    if FAILURES:
        for item in FAILURES:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1
    print("Static repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
