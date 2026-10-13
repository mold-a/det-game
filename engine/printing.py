"""HTML → PDF/PNG через Python ``playwright`` (P07). Без вызова ``npx``.

Браузер: если задана переменная окружения ``PW_CHROMIUM_PATH`` — Chromium по этому пути
(``chromium.launch(executable_path=…)``, как в ``playwright.config``), иначе — Chromium,
установленный ``python -m playwright install chromium``. Нет браузера — ``PrintError``
с подсказкой (docs/DEV.md).

HTML пишется во временный файл рядом с результатом и открывается по ``file://``:
так шаблоны подключают шрифты и картинки абсолютными ``file://``-ссылками.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from engine import ROOT

SITE = ROOT / "site"
ENV_CHROMIUM = "PW_CHROMIUM_PATH"


class PrintError(Exception):
    """Печать невозможна (нет браузера или Playwright)."""


@contextmanager
def browser() -> Iterator[object]:
    try:
        from playwright.sync_api import Error as PwError
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # pragma: no cover — playwright в зависимостях проекта
        raise PrintError(f"нет Python-пакета playwright ({e}); pip install -e .") from None
    exe = os.environ.get(ENV_CHROMIUM) or None
    with sync_playwright() as pw:
        try:
            b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        except PwError as e:
            first = str(e).strip().splitlines()[0] if str(e).strip() else repr(e)
            raise PrintError(
                "не удалось запустить Chromium для печати"
                + (f" ({ENV_CHROMIUM}={exe})" if exe else "")
                + f": {first}. Установите браузер: python -m playwright install chromium "
                f"или задайте {ENV_CHROMIUM} (docs/DEV.md)."
            ) from None
        try:
            yield b
        finally:
            b.close()


def _with_tmp_html(html: str, near: Path):
    near.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(suffix=".html", prefix=".print-", dir=near.parent)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    return Path(name)


def html_to_pdf(b: object, html: str, out: Path, *, landscape: bool = False, footer: str | None = None) -> Path:
    """A4, поля задаёт CSS (``@page``), фоны печатаются. ``footer`` — HTML нижнего колонтитула
    Chromium (классы ``pageNumber``, ``totalPages``); нужен нижний отступ ``@page`` под него."""
    out = Path(out)
    tmp = _with_tmp_html(html, out)
    try:
        page = b.new_page()
        page.goto(tmp.as_uri(), wait_until="load")
        page.evaluate("document.fonts.ready")
        extra = {"display_header_footer": True, "header_template": "<span></span>",
                 "footer_template": footer} if footer else {}
        page.pdf(path=str(out), format="A4", landscape=landscape, print_background=True,
                 prefer_css_page_size=True, **extra)
        page.close()
    finally:
        tmp.unlink(missing_ok=True)
    return out


def html_to_png(b: object, html: str, out: Path, *, width: int, height: int, scale: float = 1) -> Path:
    """Снимок окна ``width × height`` CSS-пикселей; файл — ``width·scale × height·scale`` пикселей
    (по умолчанию ``scale`` = 1: ровно ``width × height``)."""
    out = Path(out)
    tmp = _with_tmp_html(html, out)
    try:
        page = b.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
        page.goto(tmp.as_uri(), wait_until="load")
        page.evaluate("document.fonts.ready")
        page.screenshot(path=str(out), full_page=False)
        page.close()
    finally:
        tmp.unlink(missing_ok=True)
    return out


def print_env():
    """Jinja для ``site/templates/print/`` (автоэкранирование, фильтр ``dt``) и ``assets`` — file:// URL."""
    from engine.templating import make_site_env

    env = make_site_env(SITE / "templates")
    env.globals["assets"] = (SITE / "assets").as_uri()
    return env
