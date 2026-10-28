"""Фикстуры страниц для тестов и скриншотов: копия ``content/`` + тестовые страницы из ``tests/fixtures/pages``.

Тестовые страницы (театр, фонд, клуб, второй профиль «Круга», вторая статья) в ``content/`` не живут:
сюжетные страницы пишет сценарист. Здесь они нужны, чтобы проверять шаблоны, ссылки и достижимость.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "pages"


def copy_content(dst: Path, src: Path | None = None) -> Path:
    """Копия content/ (без .git и кэшей) в ``dst/content``; возвращает путь к копии."""
    out = Path(dst) / "content"
    shutil.copytree(src or ROOT / "content", out, ignore=shutil.ignore_patterns("__pycache__"))
    return out


def add_fixture_pages(content: Path) -> None:
    """Добавить в копию content/: theater, fund, auction (закрыт, этап 4), krug-actor (с голосовыми), krug-closed (закрыт, этап 4, голосовое), news-extra;
    ссылки: из облака на auction и krug-closed, из статьи news на theater, из боковой колонки news на news-extra."""
    pages = Path(content) / "pages"
    for name in ("theater", "fund", "auction", "krug-actor", "krug-closed", "news-extra"):
        d = pages / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "page.yaml").write_text((FIXTURES / f"{name}.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    shutil.copy(FIXTURES / "news-extra.md", pages / "news-extra" / "article.md")
    letter = pages / "cloud" / "if_you_read_this.md"
    letter.write_text(letter.read_text(encoding="utf-8").rstrip() + "\n\nАрхив: [клуб]({{ link('auction') }}). Запись: [круг]({{ link('krug-closed') }}).\n",
                      encoding="utf-8")
    art = pages / "news" / "article.md"
    art.write_text(art.read_text(encoding="utf-8").rstrip() + "\n\n[Театр]({{ link('theater') }}).\n", encoding="utf-8")
    news = pages / "news" / "page.yaml"
    text = news.read_text(encoding="utf-8")
    # первая запись боковой колонки (дата любая: берётся из контента, сдвиг дат сюжета не ломает фикстуру)
    text, n = re.subn(r'^  - \{ (datetime: "[^"]+", title:)', r'  - { page: news-extra, \1', text, count=1, flags=re.M)
    assert n == 1, "в news/page.yaml нет боковой колонки"
    news.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- профили закрытых этапов и «Кадр» (docs/02 §3.10; тип photo — фикстуры)

GATE_PAGES = ("krug-later", "krug-opener", "kadr-main", "kadr-friend", "kadr-late", "kadr-late-stub")
PHOTO_MAIN = "kadr-main"  # главный фотопрофиль фикстур (28.10: сюжетной страницы inna больше нет)


def add_gate_fixtures(content: Path) -> None:
    """Поверх копии content/: krug-later (social, этап 2, закрыт), krug-opener (открытый, ссылается на krug-later),
    kadr-main и kadr-friend (photo, этап 2), kadr-late (photo, этап 3, stub: kadr-late-stub), kadr-late-stub (photo_stub, этап 2).
    У kadr-main — подписчики, «Подписки» (kadr-friend, kadr-late, человек без страницы) и комментарий со ссылкой."""
    pages = Path(content) / "pages"
    for name in GATE_PAGES:
        d = pages / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "page.yaml").write_text((FIXTURES / f"{name}.yaml").read_text(encoding="utf-8"), encoding="utf-8")

    def main(d):
        d["profile"]["followers"] = 120
        d["profile"]["following"] = [{"name": "Фото Подруга", "page": "kadr-friend"},
                                     {"name": "Фото Поздняя", "page": "kadr-late"},
                                     {"name": "Подписка Без Страницы"}]
        d["posts"][0]["comments"] = [{"author": "Фото Подруга", "page": "kadr-friend", "text": "Тестовый комментарий к снимку"}]

    _edit_yaml(pages / PHOTO_MAIN / "page.yaml", main)


# ---------------------------------------------------------------- фото (site, lab, cloud, news)

# Пути фото-фикстур относительно media/. «absent» нарочно никогда не создаются: проверяют заглушку.
PHOTO_FILES = {
    "theater": ["theater/wide.jpg", "theater/inside.jpg", "theater/card.jpg"],
    "cloud": ["cloud/a.jpg", "cloud/b.jpg", "cloud/c.jpg"],
    "lab": ["lab/t1.jpg", "lab/t2.jpg", "lab/t3.jpg"],
    "news": ["news/photo.jpg"],
}
PHOTO_ABSENT = ["theater/absent.jpg", "cloud/absent.jpg"]
PHOTO_FOLDER_ID = "gallery"


def _edit_yaml(path: Path, fn) -> None:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def add_photo_fixtures(content: Path) -> None:
    """Поверх ``add_fixture_pages``: фото-блоки в театре (широкое, в колонке, без файла, фото карточки), папка
    ``gallery`` (kind: photos) в облаке, ``photos`` в lab.yaml (3 снимка) и подпись к фото статьи ``news``."""
    pages = Path(content) / "pages"

    def theater(d):
        about = next(s for s in d["sections"] if s["id"] == "about")
        about["blocks"] += [
            {"kind": "photo", "file": "theater/wide.jpg", "caption": "Тестовый фасад", "wide": True},
            {"kind": "photo", "file": "theater/inside.jpg", "caption": "Тестовый зал"},
            {"kind": "photo", "file": "theater/absent.jpg", "caption": "Тестовый снимок без файла"},
            {"kind": "cards", "items": [{"title": "Тестовая карточка с фото", "photo": "theater/card.jpg"},
                                         {"title": "Карточка без файла", "photo": "theater/absent.jpg"}]},
        ]

    def cloud(d):
        d["folders"].append({"id": PHOTO_FOLDER_ID, "title": "Тестовые снимки", "kind": "photos", "items": [
            {"file": "cloud/a.jpg", "caption": "Тестовая репетиция", "date": "2026-10-12"},
            {"file": "cloud/b.jpg", "caption": "Только подпись"},
            {"file": "cloud/c.jpg"},
            {"file": "cloud/absent.jpg", "caption": "Нет файла", "date": "2026-10-13"},
        ]})

    def news(d):
        d["article"]["photo"] = "news/photo.jpg"
        d["article"]["photo_caption"] = "Тестовая подпись к фото статьи"

    _edit_yaml(pages / "theater" / "page.yaml", theater)
    _edit_yaml(pages / "cloud" / "page.yaml", cloud)
    _edit_yaml(pages / "news" / "page.yaml", news)
    _edit_yaml(Path(content) / "lab.yaml", lambda d: d.update(photos=[
        {"file": "lab/t1.jpg", "caption": "Тестовый вход со двора"},
        {"file": "lab/t2.jpg", "caption": "Тестовый хроматограф"},
        {"file": "lab/t3.jpg"},
    ]))


# ---------------------------------------------------------------- почтовый ящик (type: mail)

MAIL_SLUG = "mail-sample"
MAIL_FILES = ["mail-sample/scan.jpg"]  # картинка-вложение (файл кладёт тест)
MAIL_ABSENT = ["mail-sample/absent.jpg"]  # вложение без файла: заглушка, без кнопки


def add_mail_fixture(content: Path) -> None:
    """Поверх копии content/: ``mail-sample`` (type: mail, этап 3, закрыт; три цепочки, вложения всех видов)
    и ссылка на неё из письма облака (иначе — предупреждение «страница без doc и без входящих ссылок»)."""
    pages = Path(content) / "pages"
    d = pages / MAIL_SLUG
    d.mkdir(parents=True, exist_ok=True)
    (d / "page.yaml").write_text((FIXTURES / f"{MAIL_SLUG}.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    letter = pages / "cloud" / "if_you_read_this.md"
    letter.write_text(letter.read_text(encoding="utf-8").rstrip()
                      + f"\n\nПочта: [ящик]({{{{ link('{MAIL_SLUG}') }}}}).\n", encoding="utf-8")
