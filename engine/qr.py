"""``python -m engine qr`` — QR-коды страниц для печати (P07 п.1).

Для каждой ``content/pages/<slug>``: ссылка ``settings.domain + /p/<slug>/`` (+ ``#k=<K_p>`` у
закрытых по ключу; у облака — без ключа, пароль в записке 4-13). ``segno``, коррекция H,
``print/qr/<slug>.png`` (≈ 1200 px) и ``.svg``; ``print/qr/sheet.pdf`` — лист A4 с карточками
40 × 40 мм, подписью ``qr_label`` и линиями реза. Самопроверка декодированием — если
установлен extra ``qrcheck`` (``zxing-cpp`` + ``pillow``), иначе предупреждение.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import segno

from engine import ROOT
from engine import salts as salts_mod
from engine.content import Content, load_content
from engine.pages import access_of
from engine.templating import make_context, render
from engine.util import b64u_encode

PRINT_QR = ROOT / "print" / "qr"
PNG_PX = 1200
QUIET_ZONE = 4  # модуля, стандарт QR
ERROR_LEVEL = "h"
PLACEHOLDER_DOMAINS = ("example.ru", "example.com", "example.org", "example.net")


@dataclass
class QrCard:
    slug: str
    url: str
    access: str
    label: str
    docs: list[str]  # документы, к которым кладётся карточка
    envelope: int
    png: Path | None = None
    svg: Path | None = None
    svg_inline: str = ""
    verified: bool | None = None  # None — декодер недоступен


@dataclass
class QrReport:
    cards: list[QrCard] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sheet: Path | None = None


def qr_url(domain: str, slug: str, key_b64: str | None) -> str:
    url = f"{domain.rstrip('/')}/p/{slug}/"
    return f"{url}#k={key_b64}" if key_b64 else url


def plan_cards(content: Content, salts) -> list[QrCard]:
    ctx = make_context(content)
    cards: list[QrCard] = []
    for slug, page in content.pages.items():
        access = access_of(page)
        key = b64u_encode(salts.page_key(slug)) if access == "key" else None
        # куда кладётся карточка: бумажные документы со ссылкой на страницу, иначе сам документ страницы
        docs = [d for d in content.documents if d.page == slug and d.kind == "paper"]
        if not docs:
            docs = [content.documents_by_id[page.doc]]
        cards.append(QrCard(
            slug=slug,
            url=qr_url(content.settings.domain, slug, key),
            access=access,
            label=render(page.qr_label, ctx, f"content/pages/{slug}/page.yaml: qr_label"),
            docs=[d.id for d in docs],
            envelope=min(d.stage for d in docs),
        ))
    cards.sort(key=lambda c: (c.envelope, c.docs))
    return cards


def png_scale(qr: segno.QRCode, px: int = PNG_PX) -> int:
    modules = qr.symbol_size(scale=1, border=QUIET_ZONE)[0]
    return max(1, px // modules)


def decoder():
    """Функция ``png → текст`` или ``None``, если extra ``qrcheck`` не установлен."""
    try:
        import zxingcpp
        from PIL import Image
    except ImportError:
        return None

    def decode(path: Path) -> str | None:
        with Image.open(path) as im:
            res = zxingcpp.read_barcodes(im.convert("L"))
        return res[0].text if res else None

    return decode


def make_qr_set(content: Content, salts, out: Path = PRINT_QR, *, sheet: bool = True) -> QrReport:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rep = QrReport(cards=plan_cards(content, salts))
    host = content.settings.domain.split("//", 1)[-1].split(":")[0].lower()
    if any(host == d or host.endswith("." + d) for d in PLACEHOLDER_DOMAINS):
        rep.warnings.append(
            f"settings.domain = {content.settings.domain} — домен-заглушка: эти QR-коды не для печати"
        )
    decode = decoder()
    if decode is None:
        rep.warnings.append("самопроверка QR пропущена: нет zxing-cpp и pillow (pip install -e \".[qrcheck]\")")
    for card in rep.cards:
        qr = segno.make(card.url, error=ERROR_LEVEL, micro=False, boost_error=False)
        card.png = out / f"{card.slug}.png"
        card.svg = out / f"{card.slug}.svg"
        qr.save(card.png, kind="png", scale=png_scale(qr), border=QUIET_ZONE)
        qr.save(card.svg, kind="svg", scale=10, border=QUIET_ZONE, xmldecl=False)
        card.svg_inline = qr.svg_inline(scale=10, border=0, omitsize=True)
        if decode is not None:
            got = decode(card.png)
            card.verified = got == card.url
            if not card.verified:
                rep.warnings.append(f"QR {card.slug}: декодируется в {got!r}, ожидалось {card.url!r}")
    if sheet:
        rep.sheet = render_sheet(content, rep.cards, out / "sheet.pdf")
    return rep


def render_sheet(content: Content, cards: list[QrCard], out: Path) -> Path:
    from markupsafe import Markup

    from engine.printing import browser, html_to_pdf, print_env

    html = print_env().get_template("print/qr_sheet.html").render(
        title=content.settings.title,
        cards=[{"label": c.label, "docs": c.docs, "envelope": c.envelope, "svg": Markup(c.svg_inline),
                "access": c.access} for c in cards],
    )
    with browser() as b:
        return html_to_pdf(b, html, out)


def run(root: Path = ROOT, *, salts_path: Path | None = None, out: Path = PRINT_QR) -> QrReport:
    content = load_content(Path(root) / "content")
    salts = salts_mod.read(Path(salts_path or salts_mod.SALTS_LOCK))
    if salts is None:
        from engine.build import BuildError

        raise BuildError(["нет engine/salts.lock.json — сначала python -m engine build (ключи страниц)"])
    missing = [s for s in content.pages if content.pages[s].locked is True and s not in salts.data.get("pages", {})]
    if missing:
        from engine.build import BuildError

        raise BuildError([f"в salts.lock.json нет ключей страниц {', '.join(missing)} — сначала python -m engine build"])
    return make_qr_set(content, salts, out)
