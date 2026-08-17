#!/usr/bin/env python3
"""Собирает страницы сайта из шаблонов site/*.template.html.

Каждый шаблон даёт два файла:

    site/<имя>.html         фрагмент для публикации артефактом Claude:
                            без <!doctype> и <head>, их подставляет сам артефакт
    site/dist/<имя>.html    самостоятельный документ для обычного хостинга:
                            с charset, viewport, описанием и иконкой

Внутри шаблонов работают подстановки:

    {{INCLUDE:partials/base.css}}   вставляет файл как есть (можно вкладывать)
    {{ASSET:hero.webp}}             вставляет файл из site/assets как data URI

Описание страницы для <meta name="description"> берётся из блока в начале
шаблона:

    <!-- meta
    description: текст
    -->

Ассеты пересобираются из исходной картинки скриптом site/prepare_assets.py.

    python3 site/build.py                # собрать все шаблоны
    python3 site/build.py index          # собрать только index
"""

import base64
import html
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"

MIME = {
    ".woff2": "font/woff2",
    ".webp": "image/webp",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}

INCLUDE = re.compile(r"\{\{INCLUDE:([^}]+)\}\}")
ASSET = re.compile(r"\{\{ASSET:([^}]+)\}\}")
META = re.compile(r"\A<!--\s*meta\s*\n(.*?)-->\s*\n", re.DOTALL)
TITLE = re.compile(r"<title>(.*?)</title>", re.DOTALL)

MAX_MB = 16
MAX_INCLUDE_DEPTH = 8

# Тёмно-синий фон и оранжевый контур дома — те же цвета, что на странице.
FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" fill="#04101f"/>'
    '<path d="M6 15.5 16 7l10 8.5V26H6z" fill="none" stroke="#f0a02c" stroke-width="2.4"/>'
    "</svg>"
)

GROUND_DARK = "#04101f"
GROUND_LIGHT = "#eceef2"


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


def take_meta(text: str) -> tuple[dict[str, str], str]:
    match = META.match(text)
    if match is None:
        return {}, text
    meta = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, text[match.end():]


def standalone(fragment: str, meta: dict[str, str]) -> str:
    title_match = TITLE.search(fragment)
    title = title_match.group(1).strip() if title_match else "Без названия"
    body = TITLE.sub("", fragment, count=1).lstrip("\n") if title_match else fragment
    description = meta.get("description", "")

    head = [
        "<!doctype html>",
        '<html lang="ru">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="color-scheme" content="dark light">',
        f'<meta name="theme-color" content="{GROUND_DARK}" media="(prefers-color-scheme: dark)">',
        f'<meta name="theme-color" content="{GROUND_LIGHT}" media="(prefers-color-scheme: light)">',
        f"<title>{title}</title>",
    ]
    if description:
        escaped = html.escape(description, quote=True)
        head.append(f'<meta name="description" content="{escaped}">')
        head.append(f'<meta property="og:description" content="{escaped}">')
    head += [
        f'<meta property="og:title" content="{html.escape(title, quote=True)}">',
        '<meta property="og:type" content="website">',
        "<!-- Для соцсетей допишите свой домен: -->",
        '<!-- <meta property="og:url" content="https://example.com/"> -->',
        '<!-- <meta property="og:image" content="https://example.com/og.jpg"> -->',
        f'<link rel="icon" href="data:image/svg+xml,{quote(FAVICON, safe="")}">',
        "</head>",
        "<body>",
    ]
    return "\n".join(head) + "\n" + body.rstrip() + "\n</body>\n</html>\n"


def report(path: Path) -> None:
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"  {path.relative_to(ROOT.parent)}: {size_mb:.2f} МБ")
    if size_mb > MAX_MB:
        fail(f"{path.name} больше лимита артефакта в {MAX_MB} МБ")


def build(template: Path) -> None:
    name = template.name.replace(".template.html", "")
    meta, source = take_meta(template.read_text(encoding="utf-8"))
    fragment = ASSET.sub(lambda m: data_uri(m.group(1)), expand_includes(source))

    print(f"{name}:")
    artifact = template.with_name(f"{name}.html")
    artifact.write_text(fragment, encoding="utf-8")
    report(artifact)

    DIST.mkdir(exist_ok=True)
    hosted = DIST / f"{name}.html"
    hosted.write_text(standalone(fragment, meta), encoding="utf-8")
    report(hosted)


def main() -> None:
    names = sys.argv[1:]
    if names:
        templates = [ROOT / f"{n.removesuffix('.html')}.template.html" for n in names]
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
