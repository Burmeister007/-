#!/usr/bin/env python3
"""Готовит ассеты для страницы процесса из исходной картинки с пятью кадрами.

Что делает:
  · режет полосу на пять квадратных кадров и сохраняет их в webp;
  · делает уменьшенную полосу целиком для героя;
  · урезает системные шрифты до латиницы с кириллицей и жмёт в woff2.

Зависимости: pillow, fonttools, brotli.

    python3 site/prepare_assets.py
"""

import sys
from pathlib import Path

from PIL import Image
from fontTools import subset

ROOT = Path(__file__).resolve().parent
SOURCE_NAME = "d0d8d2e4-4e0a-43b1-b3c8-8631ad6672c6.png"
# В репозитории картинка лежит на уровень выше, в архиве с исходниками — рядом.
SOURCE_CANDIDATES = (ROOT.parent / SOURCE_NAME, ROOT / SOURCE_NAME)
ASSETS = ROOT / "assets"

# Кадры в исходнике: пять квадратов 418×417 с шагом 440, верх на y=161.
# Последний кадр обрезан правым краем картинки — берём сколько есть.
PANEL_X = (29, 469, 909, 1349, 1789)
PANEL_Y = 161
PANEL_W = 418
PANEL_H = 417
PANEL_OUT_W = 700
HERO_OUT_W = 1800

# Латиница, кириллица, типографская пунктуация, знаки градуса/номера/умножения.
UNICODES = (
    "U+0020-007E,U+00A0,U+00AB,U+00BB,U+00B0,U+00D7,U+2010-2015,"
    "U+2018-201A,U+201C-201E,U+2026,U+2116,U+2192,U+0400-045F,"
    "U+2212,U+00A9"
)

FACES = {
    "display": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "body": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "bodyb": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
}


def source_image() -> Path:
    for path in SOURCE_CANDIDATES:
        if path.is_file():
            return path
    sys.exit("нет исходной картинки " + SOURCE_NAME + ", искал в: "
             + ", ".join(str(p.parent) for p in SOURCE_CANDIDATES))


def cut_panels() -> None:
    src = Image.open(source_image()).convert("RGB")
    width, height = src.size

    for index, left in enumerate(PANEL_X, start=1):
        panel = src.crop((left, PANEL_Y, min(left + PANEL_W, width), PANEL_Y + PANEL_H))
        scale = PANEL_OUT_W / panel.width
        panel = panel.resize((PANEL_OUT_W, round(panel.height * scale)), Image.LANCZOS)
        out = ASSETS / f"step{index}.webp"
        panel.save(out, "WEBP", quality=82, method=6)
        print(f"  · {out.name}: {panel.width}×{panel.height}, {out.stat().st_size // 1024} КБ")

    hero = src.resize((HERO_OUT_W, round(HERO_OUT_W * height / width)), Image.LANCZOS)
    out = ASSETS / "hero.webp"
    hero.save(out, "WEBP", quality=80, method=6)
    print(f"  · {out.name}: {hero.width}×{hero.height}, {out.stat().st_size // 1024} КБ")


def cut_fonts() -> None:
    for name, path in FACES.items():
        if not Path(path).is_file():
            sys.exit(f"нет шрифта: {path}")
        out = ASSETS / f"{name}.woff2"
        subset.main([
            path,
            f"--unicodes={UNICODES}",
            "--layout-features=kern,liga",
            "--flavor=woff2",
            "--desubroutinize",
            "--no-hinting",
            f"--output-file={out}",
        ])
        print(f"  · {out.name}: {out.stat().st_size // 1024} КБ")


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    print("кадры:")
    cut_panels()
    print("шрифты:")
    cut_fonts()
    print(f"готово — дальше: python3 {ROOT.name}/build.py")


if __name__ == "__main__":
    main()
