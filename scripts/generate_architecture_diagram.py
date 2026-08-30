#!/usr/bin/env python3
from __future__ import annotations

import math
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
W, H = 1920, 1080

INK = "#17233F"
MUTED = "#42526B"
CANVAS = "#FFFFFF"
PANEL = "#F7F9FC"
PANEL_EDGE = "#AEBBCF"
BLUE = "#E8F0FE"
BLUE_EDGE = "#4285F4"
GREEN = "#E6F4EA"
GREEN_EDGE = "#34A853"
AMBER = "#FEF7E0"
AMBER_EDGE = "#F9AB00"
PURPLE = "#F3E8FD"
PURPLE_EDGE = "#A142F4"
RED = "#FCE8E6"
RED_EDGE = "#EA4335"
GRAY = "#EEF2F7"
GRAY_EDGE = "#8091A8"


def font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE = font(34, True)
SUBTITLE = font(17)
SECTION = font(21, True)
BOX_TITLE = font(16, True)
BOX_BODY = font(13)
EDGE_LABEL = font(12)
FOOTER = font(15)

image = Image.new("RGB", (W, H), CANVAS)
draw = ImageDraw.Draw(image)


def center_text(text: str, y: int, x1: int, x2: int, selected_font, fill: str) -> None:
    width = draw.textlength(text, font=selected_font)
    draw.text((x1 + ((x2 - x1) - width) / 2, y), text, font=selected_font, fill=fill)


def panel(x1: int, y1: int, x2: int, y2: int, title: str) -> None:
    draw.rounded_rectangle((x1, y1, x2, y2), radius=16, fill=PANEL, outline=PANEL_EDGE, width=2)
    draw.text((x1 + 20, y1 + 16), title, font=SECTION, fill=INK)


def box(x1: int, y1: int, x2: int, y2: int, title: str, body: str = "", *, fill: str = GRAY, edge: str = GRAY_EDGE, dashed: bool = False) -> None:
    if dashed:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=10, fill=fill)
        dash = 8
        for x in range(x1 + 10, x2 - 10, dash * 2):
            draw.line((x, y1, min(x + dash, x2 - 10), y1), fill=edge, width=2)
            draw.line((x, y2, min(x + dash, x2 - 10), y2), fill=edge, width=2)
        for y in range(y1 + 10, y2 - 10, dash * 2):
            draw.line((x1, y, x1, min(y + dash, y2 - 10)), fill=edge, width=2)
            draw.line((x2, y, x2, min(y + dash, y2 - 10)), fill=edge, width=2)
    else:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=10, fill=fill, outline=edge, width=2)
    title_font = BOX_TITLE
    if draw.textlength(title, font=title_font) > (x2 - x1 - 14):
        title_font = font(13, True)
    if draw.textlength(title, font=title_font) > (x2 - x1 - 14):
        title_font = font(11, True)
    center_text(title, y1 + 14, x1, x2, title_font, INK)
    if body:
        lines = textwrap.wrap(body, width=max(18, int((x2 - x1) / 8.2)))[:2]
        for index, line in enumerate(lines):
            center_text(line, y1 + 39 + (index * 17), x1 + 6, x2 - 6, BOX_BODY, MUTED)


def arrow(points: list[tuple[int, int]], label: str = "") -> None:
    draw.line(points, fill=MUTED, width=3, joint="curve")
    (x1, y1), (x2, y2) = points[-2], points[-1]
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 11
    left = (x2 - size * math.cos(angle - 0.55), y2 - size * math.sin(angle - 0.55))
    right = (x2 - size * math.cos(angle + 0.55), y2 - size * math.sin(angle + 0.55))
    draw.polygon([(x2, y2), left, right], fill=MUTED)
    if label:
        longest = max(points, key=lambda point: point[0])
        tx = (points[0][0] + longest[0]) // 2
        ty = (points[0][1] + longest[1]) // 2 - 19
        width = draw.textlength(label, font=EDGE_LABEL)
        draw.rounded_rectangle((tx - width / 2 - 5, ty - 3, tx + width / 2 + 5, ty + 16), radius=5, fill=CANVAS)
        draw.text((tx - width / 2, ty), label, font=EDGE_LABEL, fill=MUTED)


draw.text((54, 24), "NoBS · Governed Mission with Separate Business and Calendar Authority", font=TITLE, fill=INK)
draw.text((55, 69), "Solid boxes are deployed/code-complete. Models synthesize evidence; deterministic gates own permissions, approvals, and effects.", font=SUBTITLE, fill=MUTED)

panel(34, 108, 465, 935, "A · Experience + collaboration")
panel(500, 108, 930, 935, "B · Private gateway · read-only")
panel(965, 108, 1395, 935, "C · Durable governed mission")
panel(1430, 108, 1886, 935, "D · Consequential actions")

box(142, 178, 356, 240, "Employee", "Mattermost session")
box(108, 285, 390, 358, "NoBS React UI", "Mission Inspector · untrusted browser")
box(84, 410, 415, 482, "Mattermost + Caddy", "sessions · channels · realtime")
box(68, 535, 272, 605, "NoBS Go plugin", "server-derived identity")
box(292, 535, 440, 605, "PostgreSQL", "collaboration truth", fill=AMBER, edge=AMBER_EDGE)
box(84, 774, 416, 850, "$25 budget + independent guard", "may stop only the demo VM")
arrow([(249, 240), (249, 285)])
arrow([(249, 358), (249, 410)], "HTTPS · WebSocket")
arrow([(190, 482), (190, 535)])
arrow([(330, 482), (330, 535)])

box(566, 170, 864, 240, "Pub/Sub work events", "OIDC · retry · dead-letter", fill=AMBER, edge=AMBER_EDGE)
box(550, 295, 880, 370, "NoBS Gateway", "IAM · HMAC · replay · trace")
box(550, 420, 880, 492, "Admission", "rate · concurrency · calls · tokens", fill=GREEN, edge=GREEN_EDGE)
box(526, 550, 700, 620, "Delegate Directory", "logical identities")
box(720, 550, 904, 620, "Access Gate", "tenant · scope · evidence", fill=GREEN, edge=GREEN_EDGE)
box(550, 700, 880, 780, "Model Armor", "every ADK input/output · fail closed")
arrow([(715, 240), (715, 295)])
arrow([(715, 370), (715, 420)])
arrow([(715, 492), (812, 492), (812, 550)])
arrow([(700, 585), (720, 585)])
arrow([(812, 620), (812, 700)])
arrow([(272, 570), (480, 570), (480, 333), (550, 333)])

box(1000, 160, 1164, 220, "Agent Registry", "4 services · v1", fill=AMBER, edge=AMBER_EDGE)
box(1190, 160, 1360, 220, "Vertex Sessions", "ADK context", fill=AMBER, edge=AMBER_EDGE)
box(1005, 257, 1355, 322, "Meeting Mission Controller", "Google ADK · Gemini 3.5 Flash", fill=BLUE, edge=BLUE_EDGE)
box(988, 365, 1173, 430, "Work Graph Agent", "parallel · Gemini 3.5", fill=BLUE, edge=BLUE_EDGE)
box(1190, 365, 1377, 430, "Policy Evidence", "parallel · Gemini 3.5", fill=BLUE, edge=BLUE_EDGE)
box(1025, 470, 1340, 528, "Evidence Critic", "deterministic provenance checks", fill=GREEN, edge=GREEN_EDGE)
box(1025, 568, 1340, 628, "Meeting Resolution", "accepted claims · Gemini 3.5", fill=BLUE, edge=BLUE_EDGE)
box(990, 670, 1168, 732, "Business Decision Gate", "PolicyEngine · deterministic", fill=GREEN, edge=GREEN_EDGE)
box(1190, 670, 1374, 732, "Business checkpoint", "Sarah · acting Alex", fill=PURPLE, edge=PURPLE_EDGE)
box(990, 766, 1168, 828, "Calendar Action Gate", "organizer only", fill=GREEN, edge=GREEN_EDGE)
box(1190, 766, 1374, 828, "Calendar checkpoint", "separate event", fill=PURPLE, edge=PURPLE_EDGE)
box(1000, 850, 1365, 920, "Firestore mission authority", "steps · checkpoints · commands · attempts · audit", fill=AMBER, edge=AMBER_EDGE)
arrow([(880, 740), (945, 740), (945, 289), (1005, 289)], "screened context")
arrow([(1082, 220), (1082, 257)])
arrow([(1275, 220), (1275, 257)])
arrow([(1120, 322), (1120, 345), (1080, 345), (1080, 365)])
arrow([(1240, 322), (1240, 345), (1284, 345), (1284, 365)], "parallel")
arrow([(1080, 430), (1080, 450), (1130, 450), (1130, 470)])
arrow([(1284, 430), (1284, 450), (1238, 450), (1238, 470)])
arrow([(1182, 528), (1182, 568)])
arrow([(1182, 628), (1080, 628), (1080, 670)])
arrow([(1168, 701), (1190, 701)])
arrow([(1282, 732), (1282, 749), (1080, 749), (1080, 766)])
arrow([(1168, 797), (1190, 797)])
arrow([(1282, 828), (1282, 850)])

box(1495, 165, 1820, 230, "Command builder", "approved live source only", fill=GREEN, edge=GREEN_EDGE)
box(1495, 278, 1820, 338, "Approved command outbox", "Firestore transaction", fill=AMBER, edge=AMBER_EDGE)
box(1495, 385, 1820, 445, "Pub/Sub command ID", "OIDC · retry · DLQ", fill=AMBER, edge=AMBER_EDGE)
box(1495, 500, 1820, 568, "Private Action Executor", "separate service account · max 1", fill=RED, edge=RED_EDGE)
box(1495, 620, 1820, 688, "Google Calendar", "external source of truth", fill=RED, edge=RED_EDGE)
box(1495, 740, 1820, 808, "ETag + result verifier", "post-write read · hashed outcome", fill=GREEN, edge=GREEN_EDGE)
box(1468, 850, 1658, 910, "Logging · Trace", "safe IDs and timings")
box(1680, 850, 1855, 910, "Agent Gateway", "future A2A/MCP", fill=CANVAS, edge=GRAY_EDGE, dashed=True)
arrow([(1374, 797), (1415, 797), (1415, 198), (1495, 198)])
arrow([(1658, 230), (1658, 278)])
arrow([(1658, 338), (1658, 385)])
arrow([(1658, 445), (1658, 500)])
arrow([(1658, 568), (1658, 620)])
arrow([(1658, 688), (1658, 740)])

box(430, 958, 790, 1025, "Memory Bank · preferences only", "never policy, evidence, authority, or approval", fill=AMBER, edge=AMBER_EDGE)
box(815, 958, 1135, 1025, "Dedicated service accounts", "gateway ≠ executor ≠ budget guard")
box(1160, 958, 1510, 1025, "OpenTelemetry · Cloud observability", "safe IDs, versions, attempts, timings, usage")
draw.text((54, 1043), "Logical delegates define organizational scope. Executable agents perform bounded knowledge work. Deterministic nodes own access, evidence validation, business authority, Calendar consent, idempotency, and effects.", font=FOOTER, fill=MUTED)

OUT.mkdir(exist_ok=True)
image.save(OUT / "architecture.png", optimize=True)
(OUT / "architecture.svg").write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <image href="architecture.png" width="1920" height="1080"/>
  <title>NoBS governed mission architecture</title>
  <desc>NoBS uses a private read-only gateway, four bounded Gemini agent services, deterministic evidence validation, a business decision gate for Sarah or valid acting Alex, a separate organizer-only Calendar gate, Firestore mission authority, and an isolated least-privilege Calendar action executor.</desc>
</svg>''')
print(OUT / "architecture.png")
