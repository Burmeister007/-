#!/usr/bin/env python3
"""Собирает site/process.html: подставляет ассеты из site/assets как data URI.

Артефакты Claude отдаются со строгим CSP — внешние шрифты, картинки и стили
заблокированы, поэтому страница должна быть полностью автономной.

Ассеты пересобираются из исходной картинки скриптом site/prepare_assets.py.

    python3 site/build.py
"""

import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "process.template.html"
OUTPUT = ROOT / "process.html"
ASSETS = ROOT / "assets"

MIME = {
    ".woff2": "font/woff2",
    ".webp": "image/webp",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}

PLACEHOLDER = re.compile(r"\{\{ASSET:([^}]+)\}\}")


def data_uri(name: str) -> str:
    path = ASSETS / name
    if not path.is_file():
        sys.exit(f"нет ассета: {path.relative_to(ROOT.parent)}")
    mime = MIME.get(path.suffix)
    if mime is None:
        sys.exit(f"неизвестный тип ассета: {path.name}")
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def main() -> None:
    html = TEMPLATE.read_text(encoding="utf-8")
    used: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        used.append(name)
        return data_uri(name)

    html = PLACEHOLDER.sub(replace, html)
    OUTPUT.write_text(html, encoding="utf-8")

    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f"{OUTPUT.relative_to(ROOT.parent)}: {size_mb:.2f} МБ, ассетов вшито: {len(used)}")
    for name in used:
        print(f"  · {name}")
    if size_mb > 16:
        sys.exit("страница больше лимита артефакта в 16 МБ")


if __name__ == "__main__":
    main()
