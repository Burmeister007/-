#!/usr/bin/env python3
"""Складывает архив для передачи заказчику: kontur-site.zip в корне репозитория.

Внутри архива:

    kontur-site/index.html      готовые страницы для хостинга (из site/dist)
    kontur-site/process.html
    kontur-site/README.txt      что заменить перед публикацией
    kontur-site/source/         шаблоны, партиалы, ассеты и скрипты сборки

Папка source устроена как site/ в репозитории, поэтому сборка работает и
внутри распакованного архива: python3 source/build.py.

Перед упаковкой запустите site/build.py — архив берёт уже собранные файлы.

    python3 site/pack.py
"""

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
OUT = REPO / "kontur-site.zip"
TOP = "kontur-site"
SOURCE_IMAGE = "d0d8d2e4-4e0a-43b1-b3c8-8631ad6672c6.png"

README = """КОНТУР — одностраничник и страница этапов
=========================================

Что лежит в корне архива
------------------------
index.html     одностраничник: герой, комплектации, этапы, конструктив,
               вопросы, форма заявки
process.html   только этапы стройки — короткая страница под КП или рассылку

Оба файла самодостаточные: шрифты и картинки вшиты внутрь, внешних запросов
нет. Заливаются на любой хостинг как есть, открываются и просто двойным
щелчком. Ничего собирать не нужно.

Печать
------
Обе страницы рассчитаны на «печать в PDF»: лист белый, навигация, кнопки и
форма скрыты, вопросы раскрыты. Одностраничник выходит на 9 листах A4,
страница этапов — на 4.

Что заменить перед публикацией
------------------------------
1. Название «Контур», телефон, почту и адрес цеха в подвале.
2. Цены за м², сроки в комплектациях и на полосе графика.
3. Показатели конструктива: сечения, толщины утепления, значения R,
   влажность бруса, марку бетона.
4. Гарантийные условия в блоке вопросов.
5. Форму заявки — она пока не отправляется и честно пишет об этом при
   нажатии. Подключите обработчик и удалите этот блок в <script>.
6. Пометку-черновик в подвале — когда данные станут настоящими.
7. В <head> закомментированы og:url и og:image для соцсетей — подставьте
   свой домен и раскомментируйте.

Правки
------
Мелкое можно править прямо в index.html: файл читаемый, стили лежат в <style>
в начале. Для системных изменений берите папку source — там разметка разбита
на части, а картинки и шрифты не вшиты:

    python3 source/build.py            собрать обе страницы заново
    python3 source/prepare_assets.py   если поменялась исходная картинка

Собранные файлы появятся в source/dist/ — их и класть на хостинг. Для
build.py нужен только Python, для prepare_assets.py ещё pillow, fonttools и
brotli. Подробности — в source/README.md.

Шрифты системные, лицензии свободные: DejaVu Sans, Liberation Sans,
DejaVu Sans Mono.
"""


def main() -> None:
    pages = [ROOT / "dist" / "index.html", ROOT / "dist" / "process.html"]
    missing = [p for p in pages if not p.is_file()]
    if missing:
        sys.exit("сначала соберите страницы: python3 site/build.py")

    files = ["README.md", "build.py", "prepare_assets.py", "pack.py",
             "index.template.html", "process.template.html"]
    files += [f"partials/{p.name}" for p in sorted((ROOT / "partials").iterdir())]
    files += [f"assets/{p.name}" for p in sorted((ROOT / "assets").iterdir())]

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(f"{TOP}/README.txt", README)
        for page in pages:
            z.write(page, f"{TOP}/{page.name}")
        for rel in files:
            z.write(ROOT / rel, f"{TOP}/source/{rel}")
        # Кадры этапов режутся из неё, поэтому кладём рядом с исходниками.
        z.write(REPO / SOURCE_IMAGE, f"{TOP}/source/{SOURCE_IMAGE}")

    size_mb = OUT.stat().st_size / 1024 / 1024
    with zipfile.ZipFile(OUT) as z:
        count = len(z.infolist())
        broken = z.testzip()
    if broken is not None:
        sys.exit(f"архив собрался битым на файле {broken}")
    print(f"{OUT.relative_to(REPO)}: {size_mb:.2f} МБ, файлов {count}")


if __name__ == "__main__":
    main()
