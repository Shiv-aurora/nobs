#!/usr/bin/env python3
"""Create a reproducible Mattermost plugin archive on macOS and Linux."""
from __future__ import annotations

import gzip
import sys
import tarfile
from pathlib import Path

FIXED_MTIME = 1_785_715_200  # 2026-08-03T00:00:00Z
ARCHIVE_ROOTS = ("plugin.json", "assets", "server/dist", "webapp/dist")


def normalize(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = FIXED_MTIME
    return info


def members(root: Path) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()

    def append(path: Path) -> None:
        if path not in seen:
            paths.append(path)
            seen.add(path)

    for relative in ARCHIVE_ROOTS:
        path = root / relative
        if not path.exists():
            raise FileNotFoundError(f"required plugin bundle path is missing: {relative}")
        relative_path = Path(relative)
        for parent in reversed(relative_path.parents):
            if parent != Path("."):
                append(root / parent)
        append(path)
        if path.is_dir():
            for child in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
                append(child)
    return paths


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: package_plugin.py OUTPUT.tar.gz", file=sys.stderr)
        return 2
    root = Path.cwd()
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=FIXED_MTIME) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive:
                for path in members(root):
                    archive.add(path, arcname=path.relative_to(root), recursive=False, filter=normalize)
    print(f"Built {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
