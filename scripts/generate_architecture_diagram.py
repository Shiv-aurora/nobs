#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
W, H = 1800, 1120
img = Image.new("RGB", (W, H), "#F7F8FA")
d = ImageDraw.Draw(img)
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
try:
    title = ImageFont.truetype(bold_path, 48)
    subtitle = ImageFont.truetype(font_path, 22)
    label = ImageFont.truetype(bold_path, 25)
    body = ImageFont.truetype(font_path, 19)
    tiny = ImageFont.truetype(font_path, 16)
except OSError:
    title = subtitle = label = body = tiny = ImageFont.load_default()

INK = "#172033"
MUTED = "#596579"
BLUE = "#DCEBFF"
BLUE_EDGE = "#3977D5"
GREEN = "#DFF5E8"
GREEN_EDGE = "#2A8A58"
PURPLE = "#ECE4FF"
PURPLE_EDGE = "#7251B5"
ORANGE = "#FFF0DA"
ORANGE_EDGE = "#C7771C"
RED = "#FFE4E2"
RED_EDGE = "#B84B46"
WHITE = "#FFFFFF"


def rounded_box(x1, y1, x2, y2, fill, edge, header, lines, radius=24):
    d.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=fill, outline=edge, width=3)
    d.text((x1 + 24, y1 + 20), header, font=label, fill=INK)
    y = y1 + 62
    for line in lines:
        d.text((x1 + 24, y), line, font=body, fill=MUTED)
        y += 29


def arrow(x1, y1, x2, y2, text=None, curve=0):
    # horizontal/vertical polyline with a clear arrowhead
    if curve:
        midx = (x1 + x2) // 2
        points = [(x1, y1), (midx, y1 + curve), (x2, y2)]
        d.line(points, fill=INK, width=4, joint="curve")
    else:
        d.line((x1, y1, x2, y2), fill=INK, width=4)
    import math
    ang = math.atan2(y2 - (y1 + curve if curve else y1), x2 - ((x1 + x2)//2 if curve else x1))
    size = 13
    left = (x2 - size * math.cos(ang - 0.55), y2 - size * math.sin(ang - 0.55))
    right = (x2 - size * math.cos(ang + 0.55), y2 - size * math.sin(ang + 0.55))
    d.polygon([(x2, y2), left, right], fill=INK)
    if text:
        tx = (x1 + x2) // 2
        ty = (y1 + y2) // 2 - 25
        bbox = d.textbbox((0,0), text, font=tiny)
        pad = 7
        d.rounded_rectangle((tx-(bbox[2]-bbox[0])//2-pad, ty-pad, tx+(bbox[2]-bbox[0])//2+pad, ty+(bbox[3]-bbox[1])+pad), radius=8, fill=WHITE)
        d.text((tx-(bbox[2]-bbox[0])//2, ty), text, font=tiny, fill=MUTED)


d.text((80, 46), "NoPing — Fortified Enterprise Fleet Architecture", font=title, fill=INK)
d.text((82, 108), "Ask the company, not a coworker · permission-aware delegates · human attention only for authority-bound work", font=subtitle, fill=MUTED)

# User and collaboration plane
rounded_box(70, 200, 350, 390, BLUE, BLUE_EDGE, "Employee", ["Ask Your Company", "Needs You decisions", "Rooms when humans talk"])
rounded_box(440, 180, 840, 420, BLUE, BLUE_EDGE, "Mattermost + NoPing", ["React/TypeScript full-screen route", "Go plugin trust boundary", "users · teams · sessions · rooms", "PostgreSQL collaboration state"])
arrow(350, 295, 440, 295, "session")

# Agent runtime
rounded_box(960, 170, 1400, 450, PURPLE, PURPLE_EDGE, "Private Cloud Run agent service", ["organization router + registry", "policy before retrieval", "evidence + work-state projector", "authority / OOO delegation", "decision memory + audit", "hard rate and token admission"])
arrow(840, 295, 960, 295, "IAM + HMAC")

# Google AI services
rounded_box(1480, 160, 1730, 310, GREEN, GREEN_EDGE, "Google ADK", ["Gemini 3.5+", "bounded synthesis"])
rounded_box(1480, 345, 1730, 495, RED, RED_EDGE, "Model Armor", ["prompt screening", "response screening"])
arrow(1400, 250, 1480, 235)
arrow(1400, 365, 1480, 420)

# Event and state plane
rounded_box(80, 570, 400, 800, ORANGE, ORANGE_EDGE, "Enterprise signals", ["GitHub pull requests", "Google Calendar OOO", "tickets / policies", "Mattermost evidence", "normalized WorkEvent"])
rounded_box(500, 590, 790, 780, ORANGE, ORANGE_EDGE, "Pub/Sub", ["OIDC push", "idempotency keys", "retry + dead-letter", "bounded retention"])
arrow(400, 685, 500, 685)
arrow(790, 685, 960, 400, "authenticated event")

rounded_box(960, 560, 1240, 790, GREEN, GREEN_EDGE, "Firestore", ["decisions", "scoped memory", "semantic work state", "audit + counters", "compact references"])
arrow(1180, 450, 1100, 560)

rounded_box(1320, 570, 1730, 790, GREEN, GREEN_EDGE, "Cloud observability", ["structured redacted logs", "traces and latency", "model token accounting", "security + escalation events", "no prompt/evidence bodies"])
arrow(1400, 450, 1510, 570)

# Infra/cost plane
rounded_box(80, 900, 500, 1055, BLUE, BLUE_EDGE, "Compute Engine", ["one e2-small VM · 20 GB pd-standard", "stable IP · Caddy · Mattermost · PostgreSQL", "daily self-shutdown · IAP-only SSH"])
rounded_box(650, 900, 1040, 1055, ORANGE, ORANGE_EDGE, "Cloud Billing budget", ["$25 project budget", "25 / 50 / 75 / 90 / 100% alerts", "budget notifications via Pub/Sub"])
rounded_box(1190, 880, 1730, 1070, RED, RED_EDGE, "Independent budget guard", ["private Cloud Run · min 0 / max 1", "starts in dry-run; explicit ARM required", "custom role: instances.get + instances.stop", "cannot access business data or create infrastructure"])
arrow(500, 977, 650, 977, "fixed compute cost")
arrow(1040, 977, 1190, 977, "90% notification")

# footer
footer = "Cloud Run agent: 1 CPU · 1 GiB · min 0 · max 1 · concurrency 4  |  Per user: 3/min, 20/hour, 20/day  |  Gemini: 4 calls/query, 200/day"
d.text((80, 1080), footer, font=tiny, fill=MUTED)

OUT.mkdir(exist_ok=True)
img.save(OUT / "architecture.png", optimize=True)

# Accessible SVG companion, kept simple and exact.
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1120" viewBox="0 0 1800 1120">
  <image href="architecture.png" width="1800" height="1120"/>
  <title>NoPing Fortified Enterprise Fleet architecture</title>
  <desc>Mattermost and the NoPing plugin invoke a private Cloud Run organizational agent service using Google identity and HMAC. The service uses Google ADK, Gemini, Model Armor, Firestore, Pub/Sub, and Cloud observability. A separate budget guard may stop the small Mattermost VM at 90 percent of a 25 dollar budget.</desc>
</svg>'''
(OUT / "architecture.svg").write_text(svg)
print(OUT / "architecture.png")
