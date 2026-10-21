"""Фикстуры страниц для тестов и скриншотов: копия ``content/`` + тестовые страницы из ``tests/fixtures/pages``.

Тестовые страницы (театр, фонд, клуб, второй профиль «Круга», вторая статья) в ``content/`` не живут:
сюжетные страницы пишет сценарист. Здесь они нужны, чтобы проверять шаблоны, ссылки и достижимость.
"""

from __future__ import annotations

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
    news.write_text(text.replace('  - { datetime: "2026-11-11T07:30", title:',
                                 '  - { page: news-extra, datetime: "2026-11-11T07:30", title:', 1), encoding="utf-8")
