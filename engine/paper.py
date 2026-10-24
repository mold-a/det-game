"""``python -m engine paper`` — бумажные документы дела (конверты 1–4) для печати.

Вход — ``content/paper/<id>.md`` (схема ``engine.models.PaperFrontMatter``, docs/03 «paper/»):
front matter и тело — шаблоны контента (``c``, ``w``), тело — Markdown (таблицы и HTML разрешены:
это печать, не сайт). Бланк — ``site/templates/print/paper/<form>.html``.

Выход (``print/paper/``, в ``.gitignore``):

- ``<id>.pdf`` — каждый документ, A4;
- ``envelope-<N>.pdf`` — все бумажные документы конверта N по порядку ``documents.yaml`` (заглушки
  тоже): склейка готовых ``<id>.pdf`` через ``pypdf``, поэтому у каждого документа своя нумерация
  «Лист 1…» (один общий HTML дал бы сквозной счётчик страниц Chromium); без ``--only``;
- ``preview/<id>.png`` — первая страница для просмотра.

Печать (``settings.print``, docs/05 §4):

- **подгонка** — если на последнюю страницу ушло меньше ``fit.last_page_min`` высоты листа (подпись,
  пара строк), документ печатается заново с масштабом ``fit.scales`` (по ступеням) — пока лишняя
  страница не исчезнет; не исчезла и на последней ступени — остаётся как был;
- **протоколы по одному** — документ ``form: protocol`` с разделами ``## N. …`` печатается
  по разделу: каждый протокол — своя «Лист 1…» и с новой страницы; метка
  ``<!-- person: <id> -->`` после заголовка (или в начале текста одиночного протокола) — портрет
  ``photo`` персонажа (по умолчанию ``media/portraits/<id>.jpg``) 3×4 в шапке, если файл есть;
- **duplex** — каждый документ и каждый протокол начинается с нечётной страницы: после нечётного
  числа страниц вставляется пустой оборот с пометкой ``blank_back``; номер листа дела «от руки» —
  на лицевых страницах (сквозной по конверту, только при полной сборке — без ``--only``).

QR-код страницы (та же ссылка, что у ``python -m engine qr``; у облака — без ключа) печатается в
углу документа с подписью ``qr_label``. Документы-переписки (``form: chat``) получают «скриншоты»
из ``content/chats/<id>.yaml`` (генерируются на лету, как ``python -m engine chatshot``).
Документ без текста — страница-заглушка; в ``--release`` это ошибка (как и TODO(content), нет
медиа, домен-заглушка у QR).

Сайт (``build``) бумагу не публикует; ``check`` ищет шинглы бумаги в ``dist/`` (``paper_texts``).
"""

from __future__ import annotations

import math
import re
import tempfile
import zlib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from markupsafe import Markup

from engine import ROOT
from engine import salts as salts_mod
from engine.content import TODO_MARK, Content, Todo, load_content, paper_todos
from engine.media import MEDIA_DIR
from engine.templating import make_context, render, render_tree
from engine.util import format_loc

PRINT_PAPER = ROOT / "print" / "paper"
TEMPLATE = "print/paper/_base.html"
# Превью: CSS-пиксели листа A4 при 96 dpi и масштаб снимка.
PREVIEW_W, PREVIEW_H, PREVIEW_SCALE = 794, 1123, 1.5
QR_SVG_SCALE = 10
STATUS_OK = "готов"
VERSO_TEMPLATE = "print/paper/_verso.html"
# Поля листа A4, мм (CSS @page берёт их отсюда; по ним же меряется заполнение последней страницы).
PAGE_MARGIN_MM = {"top": 16, "right": 16, "bottom": 18, "left": 22}
PT_PER_MM = 72 / 25.4
# Раздел протокола — заголовок второго уровня; метка опрашиваемого — HTML-комментарий.
SECTION_RE = re.compile(r"^## ")
FENCE_RE = re.compile(r"^(```|~~~)")
PERSON_RE = re.compile(r"<!--\s*person:\s*([A-Za-z0-9_-]+)\s*-->")


class PaperError(Exception):
    """Печать бумаги невозможна (``--release``, неизвестный ``--only``)."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join([f"Бумажные документы: ошибок {len(problems)}", *(f"  {p}" for p in problems)]))


@dataclass
class PaperRow:
    id: str
    form: str
    stage: int
    pdf: Path | None = None
    preview: Path | None = None
    pages: int | None = None
    pages_hint: int | None = None
    blanks: int = 0          # пустые обороты внутри документа (duplex, между протоколами)
    scale: float = 1.0       # наименьший масштаб подгонки среди частей документа (1 — как есть)
    notes: list[str] = field(default_factory=list)  # пусто — «готов»

    @property
    def status(self) -> str:
        return "; ".join(self.notes) if self.notes else STATUS_OK


@dataclass
class PaperReport:
    rows: list[PaperRow] = field(default_factory=list)
    envelopes: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def table(self) -> str:
        head = ("id", "бланк", "страниц", "подгонка", "статус")

        def pages(r: PaperRow) -> str:
            if r.pages is None:
                return "—"
            return f"{r.pages - r.blanks} + {r.blanks} об." if r.blanks else str(r.pages)

        body = [(r.id, r.form, pages(r), "" if r.scale == 1 else f"{round(r.scale * 100)} %", r.status)
                for r in self.rows]
        w = [max(len(x[i]) for x in [head, *body]) for i in range(4)]
        line = lambda x: "  ".join([x[0].ljust(w[0]), x[1].ljust(w[1]), x[2].rjust(w[2]), x[3].rjust(w[3]),  # noqa: E731
                                    x[4]])
        return "\n".join([line(head), line(tuple("-" * n for n in (*w, 6))), *(line(x) for x in body)])


# ---------------------------------------------------------------- Markdown для печати


@lru_cache(maxsize=1)
def _md():
    from markdown_it import MarkdownIt

    # Печать, не сайт: сырой HTML разрешён (сложные бланки), таблицы GFM включены.
    return MarkdownIt("commonmark", {"html": True, "typographer": False}).enable("table")


def paper_markdown(md: str) -> str:
    return _md().render(md)


def split_sections(source: str) -> tuple[str, list[str]]:
    """Текст протокола → (вступление до первого «## », [разделы, каждый — со своим заголовком]).
    Строки внутри блоков кода (```, ~~~) не режутся."""
    intro: list[str] = []
    sections: list[list[str]] = []
    fence = False
    for line in source.splitlines(keepends=True):
        if FENCE_RE.match(line):
            fence = not fence
        if not fence and SECTION_RE.match(line):
            sections.append([])
        (sections[-1] if sections else intro).append(line)
    return "".join(intro), ["".join(x) for x in sections]


def person_marks(text: str) -> list[str]:
    """ID персонажей из меток ``<!-- person: <id> -->`` по порядку."""
    return PERSON_RE.findall(text)


def portrait(content: Content, ctx: dict, cid: str, media_dir: Path = MEDIA_DIR) -> dict[str, Any]:
    """Фото опрашиваемого для шапки протокола: ``photo`` персонажа или ``portraits/<id>.jpg``."""
    ch = content.characters_by_id.get(cid)
    if ch is None:
        return {"id": cid, "known": False, "exists": False, "src": None, "name": cid, "path": None}
    rel = ch.photo or f"portraits/{cid}.jpg"
    p = Path(media_dir) / rel
    return {"id": cid, "known": True, "exists": p.is_file(), "src": p.as_uri() if p.is_file() else None,
            "name": ctx["c"][cid].short(), "path": rel}


# ---------------------------------------------------------------- оформление: штрихкод, подписи

# Code 39: 9 элементов (полоса, пробел, …, полоса), 1 — широкий; у каждого знака ровно 3 широких.
_CODE39 = {
    "0": "000110100", "1": "100100001", "2": "001100001", "3": "101100000", "4": "000110001",
    "5": "100110000", "6": "001110000", "7": "000100101", "8": "100100100", "9": "001100100",
    "A": "100001001", "B": "001001001", "C": "101001000", "D": "000011001", "E": "100011000",
    "F": "001011000", "G": "000001101", "H": "100001100", "I": "001001100", "J": "000011100",
    "K": "100000011", "L": "001000011", "M": "101000010", "N": "000010011", "O": "100010010",
    "P": "001010010", "Q": "000000111", "R": "100000110", "S": "001000110", "T": "000010110",
    "U": "110000001", "V": "011000001", "W": "111000000", "X": "010010001", "Y": "110010000",
    "Z": "011010000", "-": "010000101", ".": "110000100", " ": "011000100", "*": "010010100",
    "$": "010101000", "/": "010100010", "+": "010001010", "%": "000101010",
}
CODE39_WIDE = 2.5  # ширина широкого элемента в узких


def barcode_svg(text: str, *, height: float = 12) -> Markup:
    """Штрихкод Code 39 (``*текст*``) как inline SVG; знаки вне алфавита Code 39 отбрасываются."""
    data = "".join(ch for ch in text.upper() if ch in _CODE39 and ch != "*")
    x = 0.0
    bars: list[str] = []
    for ch in f"*{data}*":
        for i, el in enumerate(_CODE39[ch]):
            wdt = CODE39_WIDE if el == "1" else 1.0
            if i % 2 == 0:
                bars.append(f'<rect x="{x:g}" y="0" width="{wdt:g}" height="{height:g}"/>')
            x += wdt
        x += 1.0  # межзнаковый пробел
    return Markup(f'<svg class="barcode__bars" viewBox="0 0 {x - 1:g} {height:g}" preserveAspectRatio="none" '
                  f'aria-hidden="true">{"".join(bars)}</svg>')


_SIGN_RE = re.compile(r'(<span class="line">)(<span class="hint">\(подпись\)</span>)(</span>\s*<span class="name">)'
                      r'([^<]*)(</span>)')


def _surname(name: str) -> str:
    """Фамилия из «Ковалёв Д. О.» / «Д. О. Ковалёв»: самое длинное слово без точки."""
    words = [w.strip(",;") for w in name.split() if "." not in w]
    return max(words, key=len) if words else name.strip()


def autograph(name: str) -> str:
    """Подпись «от руки»: первые буквы фамилии и росчерк (форма — от хеша имени, повторяется)."""
    from markupsafe import escape

    sur = _surname(name)
    if not sur:
        return ""
    k = max(3, math.ceil(len(sur) * 0.55))
    h = zlib.crc32(name.encode("utf-8"))
    r = lambda lo, hi, sh: lo + (h >> sh) % (hi - lo + 1)  # noqa: E731
    # Хвост уходит вправо волной и возвращается росчерком под буквы.
    # Координаты: 0…38 по ширине хвоста, y = 14 — линия букв; обратный росчерк идёт ниже букв (y 16…19).
    path = (f"M0,{r(11, 13, 0)} C{r(4, 8, 3)},{r(3, 6, 6)} {r(9, 13, 9)},{r(14, 17, 12)} {r(16, 20, 15)},{r(6, 10, 18)} "
            f"S{r(26, 32, 21)},{r(2, 6, 24)} {r(30, 36, 27)},{r(12, 15, 2)} "
            f"C{r(20, 26, 5)},{r(17, 19, 8)} -{r(20, 32, 11)},{r(18, 20, 14)} -{r(40, 52, 17)},{r(16, 18, 20)}")
    rot = -2 - (h >> 23) % 6
    return (f'<span class="autograph" style="--rot:{rot}deg" aria-hidden="true">'
            f'<span class="autograph__text">{escape(sur[:k])}</span>'
            f'<svg class="autograph__tail" viewBox="0 0 38 20"><path d="{path}"/></svg></span>')


def add_autographs(html: str) -> str:
    """Каждой подписи бланка (``.paper__sign``: линия «(подпись)» и фамилия) — росчерк над линией."""
    return _SIGN_RE.sub(lambda m: m[1] + autograph(m[4]) + m[2] + m[3] + m[4] + m[5], html)


# ---------------------------------------------------------------- PDF: заполнение последней страницы


def last_page_fill(path: Path, margins: dict[str, float] = PAGE_MARGIN_MM) -> float:
    """Доля высоты полосы набора, занятая текстом на последней странице PDF (0…1): от верхнего поля
    до самой нижней строки текста. Колонтитулы (в полях листа) не считаются; страница без текста — 0."""
    page = _pypdf().PdfReader(Path(path)).pages[-1]
    height = float(page.mediabox.height)
    top = height - margins["top"] * PT_PER_MM
    bottom = margins["bottom"] * PT_PER_MM
    ys: list[float] = []

    def visit(text, cm, tm, _font, _size):
        if text.strip():
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            if bottom < y < top:
                ys.append(y)

    page.extract_text(visitor_text=visit)
    return 0.0 if not ys else min(1.0, (top - min(ys)) / (top - bottom))


# ---------------------------------------------------------------- данные документов


def paper_ids(content: Content) -> list[str]:
    """Все бумажные документы по порядку documents.yaml."""
    return [d.id for d in content.documents if d.kind == "paper"]


def qr_cards(content: Content, salts) -> dict[str, Any]:
    """slug → карточка QR (ссылка и подпись — как у ``python -m engine qr``)."""
    from engine.qr import plan_cards

    return {c.slug: c for c in plan_cards(content, salts)}


def wants_qr(content: Content, doc_id: str) -> bool:
    d = content.documents_by_id[doc_id]
    pf = content.paper.get(doc_id)
    flag = pf.meta.qr if pf is not None else None
    return d.page is not None and (flag if flag is not None else True)


def paper_texts(content: Content, ctx: dict | None = None) -> list[tuple[str, str, int]]:
    """Отрендеренные тексты бумаги ``[(источник, текст, конверт)]`` — иголки leak scan (шинглы, как у
    закрытых текстов: бумага не публикуется). Тело и каждое строковое поле front matter — отдельно
    (шинглы не идут через границы полей)."""
    from engine.util import iter_strings

    ctx = ctx or make_context(content)
    out: list[tuple[str, str, int]] = []
    docs = content.documents_by_id
    for doc_id, pf in content.paper.items():
        src = f"content/{pf.path}"
        stage = docs[doc_id].stage
        out.append((src, render(pf.body, ctx, f"{src}: текст"), stage))
        fields = {k: v for k, v in pf.meta_raw.items() if k not in ("id", "form", "media")}
        for loc, s in iter_strings(fields, ("front matter",)):
            out.append((src, render(s, ctx, f"{src}: {format_loc(loc)}"), stage))
    return out


def doc_data(content: Content, doc_id: str, ctx: dict, *, cards: dict[str, Any] | None = None,
             chat_pngs: dict[str, list[Path]] | None = None, media_dir: Path = MEDIA_DIR) -> dict[str, Any]:
    """Контекст одного документа для бланка (описание полей — в _base.html)."""
    import segno

    from engine.qr import ERROR_LEVEL

    d = content.documents_by_id[doc_id]
    pf = content.paper.get(doc_id)
    doc_title = render(d.title, ctx, f"content/documents.yaml: {doc_id}.title")
    data: dict[str, Any] = {
        "id": doc_id, "stage": d.stage, "doc_title": doc_title, "title": doc_title, "form": "stub",
        "stub": pf is None, "date": None, "place": None, "signed": [], "media": [], "meta": {},
        "body_html": Markup(""), "source": "", "qr": None, "chats": [], "pages_hint": None,
        "person": None, "intro_html": Markup(""), "sections": [], "persons_unknown": [],
        "part": 0, "parts": 1, "part_sections": [], "sheet_start": None,
    }
    if wants_qr(content, doc_id) and cards is not None:
        card = cards[d.page]
        qr = segno.make(card.url, error=ERROR_LEVEL, micro=False, boost_error=False)
        data["qr"] = {"svg": Markup(qr.svg_inline(scale=QR_SVG_SCALE, border=0, omitsize=True)),
                      "label": card.label, "url": card.url, "slug": d.page}
    if pf is None:
        return data
    where = f"content/{pf.path}"
    m = pf.meta
    r = lambda v, loc: None if v is None else render(v, ctx, f"{where}: front matter.{loc}")  # noqa: E731
    source = render(pf.body, ctx, f"{where}: текст")
    media = []
    for mi, rel in enumerate(m.media):
        p = Path(media_dir) / rel
        media.append({"path": rel, "src": p.as_uri() if p.is_file() else None, "exists": p.is_file(), "n": mi + 1})
    data.update({
        "form": m.form, "stub": False,
        "title": r(m.title, "title") if m.title is not None else doc_title,
        "date": r(m.date, "date"), "place": r(m.place, "place"),
        "signed": [{"role": r(s.role, f"signed[{i}].role"), "name": r(s.name, f"signed[{i}].name")}
                   for i, s in enumerate(m.signed)],
        "media": media,
        "meta": render_tree(m.meta, ctx, where, ("front matter", "meta")),
        "body_html": Markup(paper_markdown(source)),
        "source": source,
        "chats": [p.as_uri() for p in (chat_pngs or {}).get(doc_id, [])],
        "pages_hint": m.pages_hint,
    })
    if m.form == "protocol":
        intro, secs = split_sections(source)
        lead = person_marks(intro)
        data["person"] = portrait(content, ctx, lead[0], media_dir) if lead else None
        data["intro_html"] = Markup(paper_markdown(intro))
        sections = []
        for si, sec in enumerate(secs):
            head, _, rest = sec.partition("\n")
            marks = person_marks(rest)
            sections.append({"n": si + 1, "heading_html": Markup(paper_markdown(head)),
                             "body_html": Markup(paper_markdown(rest)),
                             "person": portrait(content, ctx, marks[0], media_dir) if marks else None})
        data["sections"] = sections
        people = [x for x in [data["person"], *(s["person"] for s in sections)] if x]
        data["persons_unknown"] = [x["id"] for x in people if not x["known"]]
    return data


def _file_todos(content: Content) -> dict[str, list[Todo]]:
    """TODO(content) в файлах content/paper/<id>.md по id (без missing-paper)."""
    out: dict[str, list[Todo]] = {}
    for t in paper_todos(content):
        if t.kind != "missing-paper":
            out.setdefault(t.file.rsplit("/", 1)[-1].removesuffix(".md"), []).append(t)
    return out


def _rendered_todo(d: dict) -> bool:
    return not d["stub"] and TODO_MARK in "\n".join([d["source"], d["title"], repr(d["meta"]), repr(d["signed"]),
                                                      d["date"] or "", d["place"] or ""])


def release_problems(content: Content, ids: list[str], docs: dict[str, dict], qr_warnings: list[str]) -> list[str]:
    """Что запрещено в ``paper --release``: нет текста, TODO(content), нет медиа, домен-заглушка у QR."""
    todos = _file_todos(content)
    problems: list[str] = []
    for i in ids:
        d = docs[i]
        if d["stub"]:
            problems.append(f"{i}: нет текста бумажного документа content/paper/{i}.md")
            continue
        problems += [f"TODO(content): {t}" for t in todos.get(i, [])]
        if not todos.get(i) and _rendered_todo(d):
            problems.append(f"{i}: после подстановки имён и мира в тексте есть TODO(content) "
                            "(не заполнен персонаж в characters.yaml или значение world.yaml)")
        problems += [f"{i}: нет медиафайла media/{m['path']}" for m in d["media"] if not m["exists"]]
        problems += [f"{i}: метка <!-- person: {x} --> — нет такого персонажа в characters.yaml"
                     for x in d.get("persons_unknown", [])]
    problems += qr_warnings
    return problems


def _pypdf():
    """Модуль ``pypdf`` (число страниц и склейка сборников) или ``PrintError`` с подсказкой."""
    from engine.printing import PrintError

    try:
        import pypdf
    except ImportError as e:
        raise PrintError(f"нет Python-пакета pypdf ({e}): он считает страницы и склеивает сборники "
                         "конвертов; установите зависимости: pip install -e \".[dev]\"") from None
    return pypdf


def pdf_pages(path: Path) -> int:
    """Число страниц PDF (по дереву страниц, через ``pypdf``)."""
    return len(_pypdf().PdfReader(Path(path)).pages)


def merge_pdfs(parts: list[Path], out: Path, *, title: str | None = None, verso: Path | None = None) -> Path:
    """Склеить PDF по порядку в ``out`` (через временный файл рядом — без полузаписанного сборника).
    Нумерация «Лист N» каждого документа сохраняется: она уже нарисована на его страницах.
    ``verso`` — одностраничный PDF пустого оборота: после части с нечётным числом страниц (кроме
    последней) вставляется он, и следующая часть начинается с лицевой стороны листа (duplex)."""
    pypdf = _pypdf()
    out = Path(out)
    writer = pypdf.PdfWriter()
    for i, p in enumerate(parts):
        writer.append(Path(p))
        if verso is not None and i < len(parts) - 1 and len(writer.pages) % 2:
            writer.append(Path(verso))
    if title is not None:
        writer.add_metadata({"/Title": title})
    tmp = out.with_name(f".{out.name}.tmp")
    with tmp.open("wb") as fh:
        writer.write(fh)
    tmp.replace(out)
    return out


# ---------------------------------------------------------------- печать


def doc_parts(d: dict[str, Any]) -> list[dict[str, Any]]:
    """Части документа для печати: протокол с разделами «## …» — по протоколу на часть (первая —
    с шапкой документа и вступлением), остальное — одной частью. Копии ``d`` с ``part``/``parts``."""
    secs = d.get("sections") or []
    if d["form"] != "protocol" or not secs:
        return [dict(d)]
    return [dict(d, part=k, parts=len(secs), part_sections=[s]) for k, s in enumerate(secs)]


def fit_pdf(b: object, html: str, out: Path, fit, to_pdf) -> tuple[Path, int, float]:
    """Напечатать ``html`` в ``out``; если на последнюю страницу ушло меньше ``fit.last_page_min``
    полосы — перепечатать с масштабом ``fit.scales`` по ступеням, пока страниц не станет меньше.
    Не вышло и на последней ступени — остаётся исходный PDF. → (путь, страниц, масштаб)."""
    out = Path(out)
    to_pdf(b, html, out)
    pages = pdf_pages(out)
    if pages < 2 or not fit.scales or last_page_fill(out) >= fit.last_page_min:
        return out, pages, 1.0
    trial = out.with_name(f".{out.stem}.fit.pdf")
    try:
        for scale in fit.scales:
            to_pdf(b, html, trial, scale=scale)
            n = pdf_pages(trial)
            if n < pages:
                trial.replace(out)
                return out, n, scale
    finally:
        trial.unlink(missing_ok=True)
    return out, pages, 1.0



def render_paper(content: Content, out: Path = PRINT_PAPER, *, salts=None, only: list[str] | None = None,
                 release: bool = False, media_dir: Path = MEDIA_DIR, preview: bool = True) -> PaperReport:
    from engine.chatshot import render_chats
    from engine.printing import browser, html_to_pdf, html_to_png, print_env
    from engine.qr import PLACEHOLDER_DOMAINS

    all_ids = paper_ids(content)
    if only:
        unknown = [i for i in only if i not in all_ids]
        if unknown:
            raise PaperError([f"--only {i}: бумажного документа с таким id нет в documents.yaml" for i in unknown])
    ids = [i for i in all_ids if not only or i in only]
    _pypdf()  # нет pypdf — понятная ошибка до запуска браузера
    rep = PaperReport()
    ctx = make_context(content)

    need_qr = [i for i in ids if wants_qr(content, i)]
    cards = None
    if need_qr:
        if salts is None:
            from engine.build import BuildError

            raise BuildError(["нет engine/salts.lock.json — сначала python -m engine build (ключи страниц для QR)"])
        cards = qr_cards(content, salts)
        host = content.settings.domain.split("//", 1)[-1].split(":")[0].lower()
        if any(host == d or host.endswith("." + d) for d in PLACEHOLDER_DOMAINS):
            rep.warnings.append(f"settings.domain = {content.settings.domain} — домен-заглушка: QR-коды на "
                                f"документах {', '.join(need_qr)} не для печати")

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    chat_ids = [i for i in ids if i in content.paper and content.paper[i].meta.form == "chat"]
    with tempfile.TemporaryDirectory(prefix=".chats-", dir=out) as tmp:
        chat_pngs: dict[str, list[Path]] = {}
        if chat_ids:
            for p in render_chats(content, Path(tmp), media_dir=media_dir, only=chat_ids):
                chat_pngs.setdefault(p.name.rsplit("-", 1)[0], []).append(p)
        docs = {i: doc_data(content, i, ctx, cards=cards, chat_pngs=chat_pngs, media_dir=media_dir) for i in ids}
        if release:
            problems = release_problems(content, ids, docs, rep.warnings)
            if problems:
                raise PaperError(problems)

        env = print_env()
        tpl = env.get_template(TEMPLATE)
        pcfg = content.settings.print
        common = {"w": ctx["w"], "c": ctx["c"], "game_title": content.settings.title, "print_cfg": pcfg,
                  "page_margin": " ".join(f"{PAGE_MARGIN_MM[k]}mm" for k in ("top", "right", "bottom", "left")),
                  "case_barcode": barcode_svg(str(ctx["w"].police.case_no))}

        def html(items: list[dict], title: str) -> str:
            return add_autographs(tpl.render(docs=items, title=title, **common))

        def sheets(pages: int) -> int:
            return math.ceil(pages / 2) if pcfg.duplex else pages

        work = Path(tmp)
        verso = None
        todos = _file_todos(content)
        # Номер листа дела — сквозной по конверту; известен только при полной сборке (не --only).
        next_sheet: dict[int, int] = {}
        with browser() as b:
            if pcfg.duplex:
                verso = html_to_pdf(b, env.get_template(VERSO_TEMPLATE).render(**common), work / "verso.pdf")
            for i in ids:
                d = docs[i]
                row = PaperRow(i, d["form"], d["stage"], pages_hint=d["pages_hint"])
                parts = doc_parts(d)
                pdfs: list[Path] = []
                for k, part in enumerate(parts):
                    if not only:
                        part["sheet_start"] = next_sheet.get(d["stage"], 1)
                    part_html = html([part], f"{i} — {d['title']}")
                    target = out / f"{i}.pdf" if len(parts) == 1 else work / f"{i}.part{k}.pdf"
                    pdf, pages, scale = fit_pdf(b, part_html, target, pcfg.fit, html_to_pdf)
                    pdfs.append(pdf)
                    row.scale = min(row.scale, scale)
                    if not only:
                        next_sheet[d["stage"]] = part["sheet_start"] + sheets(pages)
                    if k == 0 and preview:
                        row.preview = html_to_png(b, part_html, out / "preview" / f"{i}.png",
                                                  width=PREVIEW_W, height=PREVIEW_H, scale=PREVIEW_SCALE)
                if len(pdfs) > 1:
                    merge_pdfs(pdfs, out / f"{i}.pdf", title=d["title"], verso=verso)
                    row.blanks = sum(pdf_pages(x) % 2 for x in pdfs[:-1]) if verso else 0
                row.pdf = out / f"{i}.pdf"
                row.pages = pdf_pages(row.pdf)
                if d["stub"]:
                    row.notes.append("нет текста — заглушка")
                if todos.get(i) or _rendered_todo(d):
                    row.notes.append("TODO(content)")
                missing_media = [m["path"] for m in d["media"] if not m["exists"]]
                if missing_media:
                    row.notes.append("нет медиа: " + ", ".join(missing_media))
                if d["persons_unknown"]:
                    row.notes.append("нет персонажа: " + ", ".join(f"person: {x}" for x in d["persons_unknown"]))
                printed = row.pages - row.blanks
                if row.pages_hint is not None and printed != row.pages_hint:
                    row.notes.append(f"страниц {printed}, ожидалось {row.pages_hint} (pages_hint)")
                rep.rows.append(row)
        if not only:
            # Сборник = склейка отдельных PDF (своя нумерация «Лист N» у каждого документа); при duplex
            # каждый документ — с лицевой стороны листа.
            for n in sorted({r.stage for r in rep.rows}):
                parts = [r.pdf for r in rep.rows if r.stage == n]
                rep.envelopes.append(merge_pdfs(parts, out / f"envelope-{n}.pdf", title=f"Конверт {n}", verso=verso))
    return rep


def run(root: Path = ROOT, *, out: Path = PRINT_PAPER, only: list[str] | None = None, release: bool = False,
        salts_path: Path | None = None) -> PaperReport:
    content = load_content(Path(root) / "content")
    salts = salts_mod.read(Path(salts_path or salts_mod.SALTS_LOCK))
    return render_paper(content, out, salts=salts, only=only, release=release, media_dir=Path(root) / "media")
