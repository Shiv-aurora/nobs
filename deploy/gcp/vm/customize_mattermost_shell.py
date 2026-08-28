#!/usr/bin/env python3
"""Replace Mattermost's visible bootstrap branding without forking its web app."""

from __future__ import annotations

import re
import sys
from pathlib import Path


LOADER = """<div id="initialPageLoadingScreen" class="np-initial-loader">
<style>
.np-initial-loader{position:fixed;inset:0;z-index:9999;display:grid;place-items:center;overflow:hidden;background:radial-gradient(circle at 50% 36%,rgba(103,76,203,.09),transparent 28%),radial-gradient(circle at 12% 8%,rgba(50,194,225,.1),transparent 24%),#f7f8fc;font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.np-initial-loader::before{content:"";position:absolute;width:520px;height:520px;border:1px solid rgba(90,75,180,.06);border-radius:50%;box-shadow:0 0 0 78px rgba(90,75,180,.025),0 0 0 156px rgba(90,75,180,.016)}
.np-initial-loader__content{position:relative;display:flex;flex-direction:column;align-items:center;text-align:center}
.np-initial-loader__symbol{width:88px;height:88px;object-fit:contain;filter:drop-shadow(0 18px 30px rgba(75,122,214,.2));animation:np-loader-breathe 2s ease-in-out infinite}
.np-initial-loader__wordmark{width:136px;height:46px;margin-top:15px;object-fit:contain}
.np-initial-loader__copy{margin-top:13px;color:#737b8e;font-size:11px;font-weight:650;letter-spacing:.02em}
.np-initial-loader__track{width:96px;height:3px;margin-top:17px;overflow:hidden;border-radius:999px;background:#e4e5ed}
.np-initial-loader__track::after{content:"";display:block;width:44%;height:100%;border-radius:inherit;background:linear-gradient(90deg,#2aa6cf,#684fc4);animation:np-loader-progress 1.35s ease-in-out infinite}
@keyframes np-loader-breathe{50%{transform:translateY(-4px) scale(1.035);filter:drop-shadow(0 22px 38px rgba(103,76,203,.26))}}
@keyframes np-loader-progress{0%{transform:translateX(-125%)}100%{transform:translateX(250%)}}
@media(prefers-reduced-motion:reduce){.np-initial-loader__symbol,.np-initial-loader__track::after{animation:none}.np-initial-loader__track::after{width:100%}}
</style>
<div id="initialPageLoadingAnimation" class="np-initial-loader__content">
<img class="np-initial-loader__symbol" src="/noping-brand/logo.png" alt="NoPing">
<img class="np-initial-loader__wordmark" src="/noping-brand/text-logo.png" alt="">
<span class="np-initial-loader__copy">Mapping your organization</span>
<span class="np-initial-loader__track" aria-hidden="true"></span>
</div></div>"""


def customize(source: str) -> str:
    loader_start = source.find('<div id="initialPageLoadingScreen"')
    root_start = source.find('<div id="root"></div>')
    if loader_start < 0 or root_start < 0 or root_start <= loader_start:
        raise ValueError("Mattermost loading-screen markers were not found")

    result = source[:loader_start] + LOADER + source[root_start:]
    result = result.replace('content="Mattermost"', 'content="NoPing"')
    result = result.replace('content="Mattermost" />', 'content="NoPing" />')
    result = result.replace('To use Mattermost, please enable JavaScript.', 'To use NoPing, please enable JavaScript.')
    result = re.sub(
        r'<link rel="icon"[^>]+>',
        '<link rel="icon" type="image/png" href="/noping-brand/logo.png">',
        result,
    )
    result = re.sub(
        r'<link rel="apple-touch-icon"[^>]+>',
        '<link rel="apple-touch-icon" href="/noping-brand/logo.png">',
        result,
    )
    return result


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: customize_mattermost_shell.py INPUT_HTML OUTPUT_HTML")
    source_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    output_path.write_text(customize(source_path.read_text(encoding="utf-8")), encoding="utf-8")


if __name__ == "__main__":
    main()
