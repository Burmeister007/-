#!/usr/bin/env python3
"""Собирает страницы сайта из шаблонов site/*.template.html.

В шаблонах поддерживаются две подстановки:

    {{INCLUDE:partials/base.css}}   вставляет файл как есть (можно вкладывать)
    {{ASSET:hero.webp}}             вставляет файл из site/assets как data URI

Артефакты Claude отдаются со строгим CSP — внешние шрифты, картинки и стили
заблокированы, поэтому страница должна быть полностью автономной.

Ассеты пересобираются из исходной картинки скриптом site/prepare_assets.py.

    python3 site/build.py                # собрать все шаблоны
    python3 site/build.py index          # собрать только site/index.html
"""

import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"

MIME = {
    ".woff2": "font/woff2",
    ".webp": "image/webp",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}

INCLUDE = re.compile(r"\{\{INCLUDE:([^}]+)\}\}")
ASSET = re.compile(r"\{\{ASSET:([^}]+)\}\}")
MAX_MB = 16
MAX_INCLUDE_DEPTH = 8


def fail(message: str) -> None:
    sys.exit(f"ошибка: {message}")


def data_uri(name: str) -> str:
    path = ASSETS / name
    if not path.is_file():
        fail(f"нет ассета {path.relative_to(ROOT.parent)}")
    mime = MIME.get(path.suffix)
    if mime is None:
        fail(f"неизвестный тип ассета {path.name}")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def expand_includes(text: str, depth: int = 0) -> str:
    if not INCLUDE.search(text):
        return text
    if depth >= MAX_INCLUDE_DEPTH:
        fail("include вложены слишком глубоко — похоже на цикл")

    def replace(match: re.Match[str]) -> str:
        path = ROOT / match.group(1)
        if not path.is_file():
            fail(f"нет файла для include: {match.group(1)}")
        return path.read_text(encoding="utf-8")

    return expand_includes(INCLUDE.sub(replace, text), depth + 1)


def build(template: Path) -> None:
    output = template.with_name(template.name.replace(".template.html", ".html"))
    html = expand_includes(template.read_text(encoding="utf-8"))

    used: list[str] = []

    def replace(match: re.Match[str]) -> str:
        used.append(match.group(1))
        return data_uri(match.group(1))

    output.write_text(ASSET.sub(replace, html), encoding="utf-8")

    size_mb = output.stat().st_size / 1024 / 1024
    unique = sorted(set(used))
    print(f"{output.relative_to(ROOT.parent)}: {size_mb:.2f} МБ, ассетов {len(unique)}")
    if size_mb > MAX_MB:
        fail(f"{output.name} больше лимита артефакта в {MAX_MB} МБ")


def main() -> None:
    names = sys.argv[1:]
    if names:
        templates = [ROOT / f"{name.removesuffix('.html')}.template.html" for name in names]
        missing = [t for t in templates if not t.is_file()]
        if missing:
            fail("нет шаблонов: " + ", ".join(t.name for t in missing))
    else:
        templates = sorted(ROOT.glob("*.template.html"))
        if not templates:
            fail("в site/ нет ни одного *.template.html")

    for template in templates:
        build(template)


if __name__ == "__main__":
    main()
