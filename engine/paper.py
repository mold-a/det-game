"""``python -m engine paper`` — бумажные документы дела (конверты 1–4) для печати.

Вход — ``content/paper/<id>.md`` (схема ``engine.models.PaperFrontMatter``, docs/03 «paper/»):
front matter и тело — шаблоны контента (``c``, ``w``), тело — Markdown (таблицы и HTML разрешены:
это печать, не сайт). Бланк — ``site/templates/print/paper/<form>.html``.

Выход (``print/paper/``, в ``.gitignore``):

- ``<id>.pdf`` — каждый документ, A4;
- ``envelope-<N>.pdf`` — все бумажные документы конверта N по порядку ``documents.yaml`` (заглушки
  тоже): склейка готовых ``<id>.pdf`` через ``pypdf``, поэтому у каждого документа своя нумерация
  «Лист 1…» (один общий HTML дал бы сквозной счётчик страниц Chromium); без ``--only``;
- ``preview/<id>.png`` — первая страница для просмотра;
- ``cards-<N>.pdf`` — фото-карточки (полароиды, 3 × 3 на лист A4 с линиями реза) персонажей, впервые
  появившихся в протоколах конверта N (метки ``<!-- person -->``): ФИО и роль из строки «Опрошен(а)»
  этого протокола; без ``--only``.

Оформление — стиль «Департамент» (docs/05 §4): заголовок ``headline``, круглый знак организации,
поля «МЕТКА: значение»; средняя точка как разделитель заменяется запятой (``no_middot``).

Печать (``settings.print``, docs/05 §4):

- **подгонка** — если на последнюю страницу ушло меньше ``fit.last_page_min`` полосы (подпись,
  пара строк), документ печатается с масштабом из ``fit.scales`` — самым крупным, при котором лишняя
  страница исчезает (``fit_scales``: доля оценивается по масштабу, без разбора PDF); не исчезла —
  документ остаётся как был;
- **протоколы по одному** — документ ``form: protocol`` с разделами ``## N. …`` печатается
  по частям: сводный лист «Опись протоколов», затем каждый протокол — своя «Лист 1…» и с новой
  страницы; метка ``<!-- person: <id> -->`` после заголовка (или в начале текста одиночного
  протокола) — крупное фото ``photo`` персонажа (по умолчанию ``media/portraits/<id>.jpg``) справа
  от полей, если файл есть; поля «МЕТКА: значение» и реплики с фамилиями — ``interview``;
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
LANDSCAPE_FORMS = frozenset({"chat"})   # альбомный лист (page_rule в _doc.html)
STATUS_OK = "готов"
VERSO_TEMPLATE = "print/paper/_verso.html"
# Поля листа A4, мм (CSS @page берёт их отсюда).
PAGE_MARGIN_MM = {"top": 13, "right": 12, "bottom": 14, "left": 16}
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
class CardsRow:
    """Сборник фото-карточек конверта: ``cards-<N>.pdf``."""
    stage: int
    pdf: Path
    people: list[str]
    pages: int
    no_photo: list[str] = field(default_factory=list)


@dataclass
class PaperReport:
    rows: list[PaperRow] = field(default_factory=list)
    envelopes: list[Path] = field(default_factory=list)
    cards: list[CardsRow] = field(default_factory=list)
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


# ---------------------------------------------------------------- айдентика организаций

# Бренд бланка — у каждой вымышленной организации своя эмблема, цвет и шапка (docs/05 §4; цвета и
# эмблемы — site/templates/print/paper/_brand.html). Бренд выбирается: ``meta.brand`` → первое правило,
# чей признак есть в названии организации (``meta.org``; ``{путь}`` — значение из world.yaml) →
# умолчание бланка. Организация, которой нет в правилах (частный эксперт), — ``private``.
BRAND_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("police", ("{police.duty}", "ОП «")),                     # отдел полиции, дежурная часть
    ("so", ("{police.department}", "Следственн")),             # следственный отдел
    ("sme", ("судебно-медицинской",)),                         # бюро СМЭ
    ("smp", ("скорой медицинской",)),                          # станция скорой помощи
    ("theater", ("{theater.full}", "{theater.short}")),
    ("admin", ("Администрация",)),                             # администрация города, пресс-служба
    ("pharmacy", ("{brands.pharmacy}", "Аптека")),
    ("registry", ("реестр", "регистрации")),
    ("railway", ("{brands.railway}",)),
    ("llc", ("{money.llc}",)),
    ("fund", ("{money.fund}",)),
    ("lab", ("{brands.lab}",)),
)
# Умолчание бланка без meta.org (как шапка в _macros.html: org(doc, w, default)).
FORM_BRAND = {"plan": "theater", "program": "theater", "journal": "theater", "memo": "theater",
              "inventory": "theater", "ambulance": "smp", "forensic": "sme", "note": "none"}
BRANDS = ("so", "police", "sme", "smp", "theater", "admin", "pharmacy", "registry", "railway", "llc", "fund",
          "lab", "private", "none")


def _world_value(world: dict, path: str) -> str:
    cur: Any = world
    for k in path.split("."):
        cur = cur.get(k) if isinstance(cur, dict) else None
    return cur if isinstance(cur, str) else ""


def org_brand(org: Any, form: str, world: dict, override: Any = None) -> str:
    """Бренд бланка по ``meta.brand`` / названию организации / бланку (см. ``BRAND_RULES``)."""
    if isinstance(override, str) and override in BRANDS:
        return override
    text = " ".join(org) if isinstance(org, list) else (org or "")
    if text:
        for brand, marks in BRAND_RULES:
            for mark in marks:
                needle = _world_value(world, mark[1:-1]) if mark.startswith("{") else mark
                if needle and needle in text:
                    return brand
        return "private"
    return FORM_BRAND.get(form, "so")


# ---------------------------------------------------------------- схема тела (заключение СМЭ)

# Силуэт для схемы тела — правая половина контура взрослого мужчины в анатомической позиции (x от оси 30,
# y вниз, рост 148, голова — эллипс, около 1/8 роста); левая — зеркально; кривая Catmull-Rom через
# точки. Нарисовано для игры, без чужих изображений.
_BODY_RIGHT = [
    # шея и надплечье
    (32.8, 14.0), (33.5, 18.8), (33.9, 23.0), (37.6, 25.0), (42.2, 26.4), (45.7, 28.4), (47.5, 32.3), (48.0, 37.5),
    # рука снаружи: плечо, локоть, предплечье, кисть
    (48.4, 44.0), (49.3, 52.5), (50.4, 60.0), (51.2, 67.5), (51.4, 74.0), (52.6, 78.4), (53.0, 83.0),
    (52.1, 87.6), (50.2, 88.4), (48.9, 85.0), (48.5, 79.8), (48.3, 74.8),
    # рука изнутри
    (47.3, 67.0), (46.0, 59.5), (45.0, 52.5), (44.4, 45.0), (43.1, 38.6),
    # корпус: грудная клетка, талия, таз
    (41.8, 44.0), (41.1, 50.0), (39.7, 57.0), (40.1, 63.0), (41.4, 70.0), (42.0, 76.0),
    # нога снаружи: бедро, колено, голень, стопа
    (41.6, 84.0), (40.6, 92.0), (39.1, 100.5), (38.9, 106.0), (39.7, 113.0), (39.4, 120.0), (37.7, 130.0),
    (36.3, 138.5), (37.5, 142.0), (39.5, 145.4), (39.1, 147.7), (32.7, 148.1), (32.0, 145.4), (32.2, 139.0),
    # нога изнутри
    (31.9, 130.0), (32.1, 117.0), (32.4, 104.0), (32.1, 98.5), (31.6, 90.0), (31.0, 83.0), (30.0, 80.4),
]
BODY_W, BODY_H, BODY_GAP = 60.0, 150.0, 14.0
# Зоны отметок: вид (front | back) и полоса по высоте (y от, y до); отметка — штриховка силуэта в полосе.
BODY_ZONES: dict[str, tuple[str, float, float]] = {
    "front": ("front", 0, 150), "back": ("back", 0, 150),
    "head-front": ("front", 0, 20.5), "head-back": ("back", 0, 20.5),
    "neck-front": ("front", 18, 25), "neck-back": ("back", 18, 25),
    "chest": ("front", 25, 52), "abdomen": ("front", 52, 80),
    "back-upper": ("back", 25, 55), "back-lower": ("back", 55, 82),
    "legs-front": ("front", 82, 150), "legs-back": ("back", 82, 150),
}


def _catmull(pts: list[tuple[float, float]]) -> str:
    n = len(pts)
    d = [f"M{pts[0][0]:.2f},{pts[0][1]:.2f}"]
    for i in range(n):
        p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p2[0]:.2f},{p2[1]:.2f}")
    return " ".join(d) + " Z"


def body_outline() -> str:
    """Контур силуэта (без головы) — путь SVG в координатах одной фигуры ``BODY_W × BODY_H``."""
    left = [(BODY_W - x, y) for x, y in reversed(_BODY_RIGHT[:-1])]
    return _catmull(_BODY_RIGHT + left)


class BodyChartError(ValueError):
    """Неверная разметка ``meta.body_chart`` (неизвестная зона)."""


def body_chart(spec: Any, uid: str = "bc") -> dict[str, Any] | None:
    """Схема тела спереди и сзади для заключения СМЭ: ``meta.body_chart`` →
    ``{"svg": Markup, "marks": [{n, zone, label}], "note": str|None}``.

    ``spec``: ``{marks: [{zone, label}], note}``; ``zone`` — из ``BODY_ZONES``. Отметка — штриховка
    силуэта в зоне и номер в кружке; подписи — в легенде бланка. Только то, что есть в тексте заключения:
    шаблон ничего не добавляет."""
    if not spec:
        return None
    if not isinstance(spec, dict):
        raise BodyChartError("meta.body_chart: ожидается словарь {marks, note}")
    marks = []
    for i, mk in enumerate(spec.get("marks") or []):
        zone = (mk or {}).get("zone") if isinstance(mk, dict) else None
        if zone not in BODY_ZONES:
            raise BodyChartError(f"meta.body_chart.marks[{i}].zone = {zone!r}: допустимо {', '.join(BODY_ZONES)}")
        marks.append({"n": i + 1, "zone": zone, "label": str(mk.get("label") or "")})
    outline = body_outline()
    head = '<ellipse cx="30" cy="10" rx="6.6" ry="8.9"/>'
    head_white = '<ellipse fill="#fff" cx="30" cy="10" rx="6.6" ry="8.9"/>'
    details = {
        # спереди — ключицы, грудь, пупок, колени; сзади — позвоночник, лопатки, ягодичная складка, подколенные
        # ямки (только форма бланка)
        "front": '<path class="bc__detail" d="M24.3 25.6 Q27.2 27.2 29.6 26.6 M35.7 25.6 Q32.8 27.2 30.4 26.6 '
                 'M24.6 38.6 Q27.4 40.6 29.6 39.4 M35.4 38.6 Q32.6 40.6 30.4 39.4 '
                 'M26.4 101.5 Q27.6 103.4 29 101.8 M33.6 101.5 Q32.4 103.4 31 101.8"/>'
                 '<circle class="bc__detail" cx="30" cy="58" r=".55"/>',
        "back": '<path class="bc__detail bc__spine" d="M30 21 V74"/>'
                '<path class="bc__detail" d="M24 30.5 Q22.6 36.5 25.6 41.5 M36 30.5 Q37.4 36.5 34.4 41.5 '
                'M22.4 79.4 Q26 82.2 29.6 80.6 M37.6 79.4 Q34 82.2 30.4 80.6 '
                'M26.2 104 Q27.6 102.6 29 104 M33.8 104 Q32.4 102.6 31 104"/>',
    }
    parts = [f'<svg class="bodychart__svg" viewBox="0 0 {2 * BODY_W + BODY_GAP:g} {BODY_H + 8:g}" aria-hidden="true">',
             f'<defs><pattern id="{uid}-hatch" width="2.2" height="2.2" patternUnits="userSpaceOnUse" '
             'patternTransform="rotate(45)"><path d="M0 0 V2.2" class="bc__hatchline"/></pattern>',
             f'<clipPath id="{uid}-clip">{head}<path d="{outline}"/></clipPath></defs>']
    for k, view in enumerate(("front", "back")):
        x0 = k * (BODY_W + BODY_GAP)
        parts.append(f'<g transform="translate({x0:g},0)" class="bc__fig bc__fig--{view}">')
        # голова поверх шеи (белая заливка закрывает стык контура), штриховка отметок — поверх контура
        parts.append(f'<g class="bc__line"><path d="{outline}"/>{head_white}{details[view]}</g>')
        for mk in marks:
            v, y1, y2 = BODY_ZONES[mk["zone"]]
            if v == view:
                parts.append(f'<rect class="bc__zone" x="0" y="{y1:g}" width="{BODY_W:g}" height="{y2 - y1:g}" '
                             f'fill="url(#{uid}-hatch)" clip-path="url(#{uid}-clip)" data-zone="{mk["zone"]}"/>')
        for mk in marks:
            v, y1, y2 = BODY_ZONES[mk["zone"]]
            if v == view:
                cy = y1 + (y2 - y1) * (0.32 if y2 - y1 > 60 else 0.5)
                parts.append(f'<g class="bc__pin"><circle cx="{BODY_W - 4.5:g}" cy="{cy:.1f}" r="3.6"/>'
                             f'<text x="{BODY_W - 4.5:g}" y="{cy + 1.45:.1f}" text-anchor="middle">{mk["n"]}</text></g>')
        label = "Спереди" if view == "front" else "Сзади"
        parts.append(f'<text class="bc__cap" x="30" y="{BODY_H + 6:g}" text-anchor="middle">{label}</text></g>')
    parts.append("</svg>")
    note = spec.get("note")
    return {"svg": Markup("".join(parts)), "marks": marks, "note": str(note) if note else None}


# ---------------------------------------------------------------- фото-карточки персонажей

CARDS_TEMPLATE = "print/paper/_cards.html"
CARDS_PER_SHEET = 9   # 3 × 3 полароида на лист A4
_WHO_LABEL_RE = re.compile(r'<span class="fld__label">\s*((?:Опрош|Объяснени)[^<]*)</span>\s*'
                           r'<span class="fld__value">(.*?)</span>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")
BIRTH_MARK = "г. р., "


def _plain(html: str) -> str:
    from html import unescape

    return " ".join(unescape(_TAG_RE.sub(" ", html.replace("<br>", ", "))).split()).replace(" ,", ",")


def interviewee_role(who: Any) -> str:
    """Роль опрошенного из строки «Опрошен(а)» его протокола — как записано, без новых сведений:
    после «… г. р., »; список строк без года — вторая строка; иначе — пусто."""
    lines = who if isinstance(who, list) else [who or ""]
    text = ", ".join(str(x).strip() for x in lines if str(x).strip())
    if BIRTH_MARK in text:
        return text.split(BIRTH_MARK, 1)[1].strip()
    return str(lines[1]).strip() if len(lines) > 1 else ""


def protocol_people(d: dict[str, Any]) -> list[tuple[str, str]]:
    """[(id персонажа, строка «Опрошен(а)»)] протокола по меткам ``<!-- person -->`` по порядку."""
    if d.get("form") != "protocol" or d.get("stub"):
        return []
    out: list[tuple[str, str]] = []
    if d.get("person"):
        who = d["meta"].get("person") if isinstance(d.get("meta"), dict) else None
        if not who:
            m = _WHO_LABEL_RE.search(str(d["intro_html"]))
            who = _plain(m[2]) if m else ""
        out.append((d["person"]["id"], who))
    for s in d.get("sections") or []:
        if s["person"]:
            m = _WHO_LABEL_RE.search(str(s["body_html"]))
            out.append((s["person"]["id"], _plain(m[2]) if m else ""))
    return out


def cast_cards(content: Content, docs: dict[str, dict[str, Any]], ctx: dict,
               media_dir: Path = MEDIA_DIR) -> dict[int, list[dict[str, Any]]]:
    """Конверт → карточки персонажей, впервые появившихся в протоколах этого конверта (порядок
    documents.yaml, затем разделов): ``{id, name (ФИО), role, src, exists}``. Роль — из строки
    «Опрошен(а)» первого протокола человека (``interviewee_role``)."""
    seen: set[str] = set()
    out: dict[int, list[dict[str, Any]]] = {}
    for doc_id in paper_ids(content):
        d = docs.get(doc_id)
        if d is None:
            continue
        for cid, who in protocol_people(d):
            if cid in seen or cid not in content.characters_by_id:
                continue
            seen.add(cid)
            p = portrait(content, ctx, cid, media_dir)
            out.setdefault(d["stage"], []).append({
                "id": cid, "name": ctx["c"][cid].full(), "role": interviewee_role(who),
                "src": p["src"], "exists": p["exists"], "path": p["path"], "doc": doc_id})
    return out


# ---------------------------------------------------------------- стиль «Департамент»: заголовок, средняя точка

# Средняя точка (U+00B7) как разделитель запрещена везде (CLAUDE.md, решение автора 24.10.2026). Шаблоны
# бумаги её не содержат; если она есть в тексте content/paper — при печати заменяется запятой
# (в начале значения — убирается), а в отчёте `paper` — предупреждение: поправить текст.
MIDDOT = "\u00b7"
_MIDDOT_RE = re.compile("[ \t\u00a0]*\u00b7[ \t\u00a0]*")
_LEAD_COMMA_RE = re.compile(r"(^|>|\n)([ \t ]*), ")


def no_middot(text: str) -> str:
    """Средняя точка с пробелами → «, »; разделитель в начале строки или элемента HTML — без запятой."""
    if MIDDOT not in text:
        return text
    return _LEAD_COMMA_RE.sub(r"\1\2", _MIDDOT_RE.sub(", ", text))


# Крупный заголовок бланка в стиле «Департамент» (docs/05 §4): 1–2 строки прописными, Tektur 800.
# Порядок: meta.headline (строка — строки через «/» или перевод строки — или список) → из названия
# документа, если оно короткое (первое слово — первая строка, остальное — вторая, не длиннее
# HEADLINE_REST; хвост после «:» и «Фамилия И. О.» отбрасывается) → умолчание бланка HEADLINES.
# Если заголовок не из названия, полное официальное название печатается мелко в правом мини-блоке.
HEADLINES: dict[str, tuple[str, ...]] = {
    "protocol": ("Протокол", "опроса"), "inspection": ("Протокол", "осмотра"), "report": ("Рапорт",),
    "ambulance": ("Карта вызова", "скорой помощи"), "forensic": ("Заключение", "судмедэксперта"),
    "certificate": ("Справка",), "phototable": ("Фототаблица",), "journal": ("Журнал",), "inventory": ("Опись",),
    "press": ("Ответ", "на запрос"), "pharmacy": ("Ответ", "на запрос"), "memo": ("Служебная", "записка"),
    "estimate": ("Смета",), "registry": ("Выписка", "из реестра"), "chat": ("Снимок", "экрана"),
}
HEADLINE_FROM_TITLE = frozenset(HEADLINES) - {"report"}   # рапорт — всегда «РАПОРТ»
HEADLINE_REST = 20            # вторая строка из названия — не длиннее (знаков)
SUMMARY_HEADLINE = ("Опись", "протоколов")   # сводный лист протокола с разделами (1-08)
# Кегль заголовка: ширина колонки заголовка (мм) / (средняя ширина знака Tektur 800 на 1 pt × знаков).
HEADLINE_PT, HEADLINE_MIN_PT, HEADLINE_COL_MM, HEADLINE_EM_MM = 30.0, 17.0, 106.0, 0.232
_NAME_TAIL_RE = re.compile(r"\s+[А-ЯЁ][а-яё-]+\s+[А-ЯЁ]\.\s?[А-ЯЁ]\..*$")


def headline(form: str, title: str, meta: dict | None = None) -> dict[str, Any]:
    """Крупный заголовок бланка: ``{"lines": [...], "official": str | None, "size": pt}``."""
    meta = meta or {}
    raw = meta.get("headline")
    official: str | None = None
    if raw:
        lines = [str(x).strip() for x in (raw if isinstance(raw, list) else re.split(r"\s*(?:\n|/)\s*", str(raw)))]
        lines = [x for x in lines if x]
    else:
        base = str(meta.get("tag") or "") if form == "press" else ""
        base = base or re.split(r"\s*(?::|\u00b7| — )\s*", title or "")[0]
        words = _NAME_TAIL_RE.sub("", base).split()
        rest = " ".join(words[1:])
        if form in HEADLINE_FROM_TITLE and words and len(rest) <= HEADLINE_REST:
            lines = [words[0]] + ([rest] if rest else [])
        else:
            lines = list(HEADLINES.get(form, ()))
        if " ".join(lines).lower() != (title or "").strip().lower():
            official = title or None
    lines = [x.upper() for x in lines]
    longest = max((len(x) for x in lines), default=1)
    size = max(HEADLINE_MIN_PT, min(HEADLINE_PT, HEADLINE_COL_MM / (HEADLINE_EM_MM * longest)))
    return {"lines": lines, "official": official, "size": round(size, 1)}


# ---------------------------------------------------------------- протокол: поля, реплики, сводный лист

# Поля протокола «МЕТКА: значение». Одиночный протокол — из front matter (meta.person, by, present, place,
# date/start/end); протоколы 1-08 — из HTML макроса head() в тексте (классы proto__fields, fld, fld__label,
# fld__value): блок вынимается из текста и печатается в шапке листа рядом с фото.
_FIELDS_RE = re.compile(r'<div class="proto__fields[^"]*">\s*((?:<div class="fld[^"]*">\s*<span class="fld__label">'
                        r'.*?</span>\s*<span class="fld__value">.*?</span>\s*</div>\s*)*)</div>\s*', re.S)
_FIELD_RE = re.compile(r'<div class="fld[^"]*">\s*<span class="fld__label">(.*?)</span>\s*'
                       r'<span class="fld__value">(.*?)</span>\s*</div>', re.S)
_WHO_RE = re.compile(r"^(.*?),\s*(\d{4})\s*г\.\s*р\.\s*(?:,\s*(.*))?$", re.S)
_SURNAME_RE = re.compile(r"([А-ЯЁ][а-яё\-]+)\s+[А-ЯЁ]\.\s?[А-ЯЁ]\.")
_P_RE = re.compile(r"<p>(.*?)</p>", re.S)
_QA_LABEL_RE = re.compile(r"\s*<strong>(Вопрос|Ответ):</strong>\s*")
_NOTE_LABEL_RE = re.compile(r"((?:Служебная )?[Оо]тметка[^:<]{0,60}):\s*")
_EM_ONLY_RE = re.compile(r"<em>((?:(?!</?em>).)*)</em>", re.S)
PROTO_LABELS = {"year": "Год рождения", "info": "Сведения", "present": "При опросе", "by": "Опросил",
                "when": "Дата, время", "where": "Место", "note": "Примечание опросившего"}


def split_fields(html: str) -> tuple[list[tuple[str, str]], str]:
    """Блок ``.proto__fields`` из HTML раздела → ([(подпись, значение HTML)], HTML без блока)."""
    m = _FIELDS_RE.search(html)
    if not m:
        return [], html
    return [(_plain(a), b.strip()) for a, b in _FIELD_RE.findall(m[1])], html[:m.start()] + html[m.end():]


def _field_kind(label: str) -> str:
    low = label.lower()
    if low.startswith(("опрош", "объяснени", "допрош")):
        return "who"
    if low.startswith(("опросил", "составил", "допросил", "принял")):
        return "by"
    if low.startswith(("при опросе", "присутств")):
        return "present"
    if low.startswith("дата"):
        return "when"
    if low.startswith("место"):
        return "where"
    return "other"


def _lines_html(v: Any) -> str:
    from markupsafe import escape

    if isinstance(v, list):
        return ", ".join(str(escape(x)) for x in v if str(x).strip())
    return str(escape(v or ""))


def interview_rows(pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """Поля протокола (подпись, значение HTML) → строки «МЕТКА: значение» в порядке бланка: кто (ФИО,
    год рождения, сведения), пробел, дата и время, место, кто опросил, кто присутствовал, прочее.
    Строка «Опрошен(а)» ``ФИО, 1981 г. р., должность`` делится на три поля; без года — как есть."""
    by_kind: dict[str, list[tuple[str, str]]] = {}
    for label, value in pairs:
        if value and value.strip():
            by_kind.setdefault(_field_kind(label), []).append((label, value))
    rows: list[dict[str, Any]] = []
    for label, value in by_kind.get("who", []):
        m = _WHO_RE.match(value.strip())
        if m:
            rows.append({"label": label, "value": Markup(m[1].strip())})
            rows.append({"label": PROTO_LABELS["year"], "value": Markup(m[2])})
            if m[3] and m[3].strip():
                rows.append({"label": PROTO_LABELS["info"], "value": Markup(m[3].strip())})
        else:
            rows.append({"label": label, "value": Markup(value)})
    if rows:
        rows.append({"gap": True})
    for kind in ("when", "where", "by", "present", "other"):
        for label, value in by_kind.get(kind, []):
            rows.append({"label": PROTO_LABELS["present"] if kind == "present" else label, "value": Markup(value)})
    return rows


def surname_in(text: str) -> str | None:
    """Фамилия из «сержант полиции Ковалёв Д. О.» (слово перед инициалами)."""
    m = _SURNAME_RE.search(_plain(text))
    return m[1] if m else None


def dialog_html(html: str, asker: str | None, answerer: str | None) -> str:
    """Реплики протокола: «**Вопрос:**» / «**Ответ:**» → фамилия опросившего / опрашиваемого
    (``.who--q`` / ``.who--a``); абзац без метки после реплики — её продолжение (``.qa-cont``, без
    повторной фамилии); курсивные абзацы после последней реплики (пояснение присутствовавшего, запись
    опросившего) — блоком под одной меткой «Примечание опросившего:» обычным текстом; курсивные абзацы
    между репликами — ``.rem`` без курсива. Без реплик (объяснение от первого лица) текст не меняется."""
    from markupsafe import escape

    paras = list(_P_RE.finditer(html))
    kinds: list[tuple[str, re.Match | None]] = []
    for m in paras:
        q = _QA_LABEL_RE.match(m[1])
        kinds.append(("qa", q) if q else ("em", None) if _EM_ONLY_RE.fullmatch(m[1].strip()) else ("p", None))
    qa = [i for i, (k, _) in enumerate(kinds) if k == "qa"]
    if not qa:
        return html
    last = qa[-1]
    note = [i for i in range(last + 1, len(paras)) if kinds[i][0] == "em"]
    # примечание — подряд идущие курсивные абзацы (между ними только пробелы)
    run: list[int] = []
    for i in note:
        if run and (i != run[-1] + 1 or html[paras[run[-1]].end():paras[i].start()].strip()):
            break
        run.append(i)
    # абзацы без метки — продолжение реплики, если стоят между репликами или перед примечанием; после
    # последней реплики без примечания («С моих слов записано верно», объяснение от первого лица) — текст
    cont_end = run[0] if run else last
    out: list[str] = []
    pos = 0
    in_note = False
    for i, m in enumerate(paras):
        out.append(html[pos:m.start()])
        pos = m.end()
        kind, q = kinds[i]
        if kind == "qa":
            k = "q" if q[1] == "Вопрос" else "a"
            name = (asker if k == "q" else answerer) or q[1]
            out.append(f'<p class="qa qa--{k}"><span class="who who--{k}">{escape(name)}:</span> {m[1][q.end():]}</p>')
        elif i in run:
            inner = _EM_ONLY_RE.fullmatch(m[1].strip())[1]
            own = _NOTE_LABEL_RE.match(inner)
            if own or not in_note:
                if in_note:
                    out.append("</div>")
                label = own[1] if own else PROTO_LABELS["note"]
                out.append(f'<div class="proto__note"><div class="proto__note-label">{label}:</div>')
                in_note = True
                if own:
                    inner = inner[own.end():]
                    inner = inner[:1].upper() + inner[1:]
            out.append(f"<p>{inner}</p>")
            if i == run[-1]:
                out.append("</div>")
                in_note = False
        elif kind == "em":
            out.append(f'<p class="rem">{_EM_ONLY_RE.fullmatch(m[1].strip())[1]}</p>')
        elif qa[0] < i < cont_end:
            out.append(f'<p class="qa-cont">{m[1]}</p>')
        else:
            out.append(m[0])
    out.append(html[pos:])
    return "".join(out)


ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")
# Разделы «## …» в строку с первым абзацем (заключение СМЭ — с римским номером, карта СМП — без):
# «I. ОСНОВАНИЕ. Направление …». Раздел, за которым идёт не абзац (список выводов), — отдельный
# заголовок ``.sec-h`` без номера.
RUNIN_FORMS = {"forensic": True, "ambulance": False}
_H2_RE = re.compile(r"<h2>(.*?)</h2>\s*(<p>)?", re.S)


def runin_sections(html: str, roman: bool = False) -> str:
    n = 0

    def rep(m: re.Match) -> str:
        nonlocal n
        head = m[1].strip()
        if not m[2]:
            return f'<h2 class="sec-h">{head}</h2>\n'
        n += 1
        num = f"{ROMAN[n - 1]}. " if roman and n <= len(ROMAN) else ""
        dot = "" if head.endswith((".", "?", "!", ":")) else "."
        return f'<p class="runin"><span class="rh">{num}{head}{dot}</span> '

    return _H2_RE.sub(rep, html)


def _ddmmyyyy(s: str | None) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    return f"{m[3]}.{m[2]}.{m[1]}" if m else (s or "")


def interview(d: dict[str, Any], body_html: str, person: dict | None, ctx: dict,
              pairs: list[tuple[str, str]] | None = None) -> dict[str, Any]:
    """Данные листа протокола: поля, фамилии для реплик, преобразованный текст. ``pairs`` — поля из
    макроса head() (раздел 1-08); без них — из front matter одиночного протокола."""
    meta = d.get("meta") or {}
    if pairs is None:
        pairs = []
        who = meta.get("person")
        if who:
            pairs.append((meta.get("person_label") or "Опрошен(а)", _lines_html(who)))
        iso = d.get("date") or ""
        start = meta.get("start") or (iso[11:16] if len(iso) >= 16 and iso[10] == "T" else "")
        end = meta.get("end") or ""
        when = ", ".join(x for x in (_ddmmyyyy(iso), "–".join(x for x in (start, end) if x)) if x)
        if when:
            pairs.append((PROTO_LABELS["when"], when))
        if d.get("place"):
            pairs.append((PROTO_LABELS["where"], _lines_html(d["place"])))
        if meta.get("by"):
            pairs.append((meta.get("by_label") or PROTO_LABELS["by"], _lines_html(meta["by"])))
        if meta.get("present"):
            pairs.append((PROTO_LABELS["present"], _lines_html(meta["present"])))
    by = next((v for k, v in pairs if _field_kind(k) == "by"), "")
    who = next((v for k, v in pairs if _field_kind(k) == "who"), "")
    when = next((_plain(v) for k, v in pairs if _field_kind(k) == "when"), "")
    answerer = None
    if person and person.get("known"):
        answerer = ctx["c"][person["id"]].last()
    if not answerer and who:
        answerer = (_plain(who).split() or [None])[0]
        answerer = answerer.rstrip(",") if answerer else None
    asker = surname_in(by) if by else None
    return {"rows": interview_rows(pairs), "asker": asker, "answerer": answerer,
            "who": _WHO_RE.sub(r"\1", _plain(who)) if who else "", "when": when,
            "where": next((_plain(v) for k, v in pairs if _field_kind(k) == "where"), ""),
            "date": when[:10] if re.match(r"\d\d\.\d\d\.\d{4}", when) else "",
            "body": Markup(dialog_html(body_html, asker, answerer))}


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
    # Координаты: 0…38 по ширине хвоста, y = 14 — линия букв; росчерк под буквами уходит в минус по x.
    tails = [
        # волна вправо и петля обратно под буквы
        f"M0,{r(11, 13, 0)} C{r(4, 8, 3)},{r(3, 6, 6)} {r(9, 13, 9)},{r(14, 17, 12)} {r(16, 20, 15)},{r(6, 10, 18)} "
        f"S{r(26, 32, 21)},{r(2, 6, 24)} {r(30, 36, 27)},{r(12, 15, 2)} "
        f"C{r(20, 26, 5)},{r(17, 19, 8)} -{r(20, 32, 11)},{r(18, 20, 14)} -{r(40, 52, 17)},{r(16, 18, 20)}",
        # пила и подчёркивание
        f"M0,13 L{r(3, 5, 1)},{r(5, 8, 4)} L{r(7, 9, 7)},14 L{r(11, 13, 10)},{r(4, 7, 13)} L{r(15, 17, 16)},14 "
        f"C{r(20, 24, 19)},{r(16, 19, 22)} {r(28, 32, 25)},{r(6, 9, 3)} {r(34, 38, 6)},{r(9, 12, 9)} "
        f"M-{r(44, 54, 12)},{r(17, 19, 15)} C-{r(20, 28, 18)},{r(19, 21, 21)} {r(4, 10, 24)},{r(19, 21, 27)} {r(30, 36, 2)},{r(15, 17, 5)}",
        # подъём вверх и длинный хвост вниз-влево
        f"M0,12 C{r(5, 8, 2)},{r(14, 16, 5)} {r(10, 13, 8)},{r(2, 5, 11)} {r(15, 18, 14)},{r(8, 11, 17)} "
        f"S{r(22, 26, 20)},{r(16, 18, 23)} {r(28, 32, 26)},{r(4, 7, 1)} "
        f"C{r(30, 34, 4)},{r(16, 19, 7)} {r(6, 10, 10)},{r(20, 22, 13)} -{r(36, 48, 16)},{r(17, 19, 19)}",
    ]
    path = tails[(h >> 28) % len(tails)]
    rot = -2 - (h >> 23) % 6
    return (f'<span class="autograph" style="--rot:{rot}deg" aria-hidden="true">'
            f'<span class="autograph__text">{escape(sur[:k])}</span>'
            f'<svg class="autograph__tail" viewBox="0 0 38 22"><path d="{path}"/></svg></span>')


def add_autographs(html: str) -> str:
    """Каждой подписи бланка (``.paper__sign``: линия «(подпись)» и фамилия) — росчерк над линией."""
    return _SIGN_RE.sub(lambda m: m[1] + autograph(m[4]) + m[2] + m[3] + m[4] + m[5], html)


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
        "brand": org_brand(None, "stub", content.world), "body_chart": None, "problems": [],
        "headline": headline("stub", doc_title), "proto": None, "part_kind": "whole", "summary": None,
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
        "brand": None,
    })
    data["brand"] = org_brand(data["meta"].get("org"), m.form, content.world, data["meta"].get("brand"))
    data["headline"] = headline(m.form, data["title"], data["meta"])
    if m.form in RUNIN_FORMS:
        data["body_html"] = Markup(runin_sections(str(data["body_html"]), RUNIN_FORMS[m.form]))
    try:
        data["body_chart"] = body_chart(data["meta"].get("body_chart"), f"bc-{doc_id}")
    except BodyChartError as e:
        data["problems"].append(f"{doc_id}: {e}")
    if m.form == "protocol":
        intro, secs = split_sections(source)
        lead = person_marks(intro)
        data["person"] = portrait(content, ctx, lead[0], media_dir) if lead else None
        data["intro_html"] = Markup(paper_markdown(intro))
        sections = []
        for si, sec in enumerate(secs):
            head, _, rest = sec.partition("\n")
            marks = person_marks(rest)
            body = paper_markdown(rest)
            person = portrait(content, ctx, marks[0], media_dir) if marks else None
            pairs, body_wo = split_fields(body)
            sections.append({"n": si + 1, "heading_html": Markup(paper_markdown(head)), "body_html": Markup(body),
                             "person": person, "proto": interview(data, body_wo, person, ctx, pairs)})
        data["sections"] = sections
        if not sections:
            data["proto"] = interview(data, str(data["body_html"]), data["person"], ctx)
        note = data["meta"].get("note")
        data["summary"] = {
            "note": Markup(paper_markdown(str(note))) if note else (data["intro_html"] if intro.strip() else None),
            "rows": [{"n": x["n"], "who": x["proto"]["who"] or _plain(str(x["heading_html"])),
                      "when": x["proto"]["when"], "where": x["proto"]["where"]} for x in sections]}
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
        problems += d.get("problems", [])
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
    """Части документа для печати: протокол с разделами «## …» — по протоколу на часть, а перед ними
    (если разделов больше одного) — сводный лист «Опись протоколов» (``part_kind == "summary"``,
    заголовок — ``meta.cover_headline``, счётчик — ``meta.count_label``; заголовок раздела —
    ``meta.section_headline`` или ``meta.headline``:
    №, ФИО, дата и время, место из полей разделов; внизу meta.note или вступление документа);
    остальное — одной частью. Копии ``d`` с ``part``/``parts``/``part_kind``/``headline``."""
    secs = d.get("sections") or []
    if d["form"] != "protocol" or not secs:
        return [dict(d)]
    title = re.sub(r"^Протоколы\b", "Протокол", d["title"])
    meta = d["meta"]
    # заголовок листа раздела — в единственном числе: meta.section_headline → meta.headline → из названия
    sec_meta = dict(meta, headline=meta.get("section_headline") or meta.get("headline"))
    sec_head = headline("protocol", title, sec_meta)
    parts: list[dict[str, Any]] = []
    if len(secs) > 1:
        cover = d["meta"].get("cover_headline") or list(SUMMARY_HEADLINE)
        parts.append(dict(d, part_kind="summary", part_sections=[],
                          headline=headline("protocol", d["title"], {"headline": cover})))
    parts += [dict(d, part_kind="section", part_sections=[s], headline=sec_head) for s in secs]
    for k, x in enumerate(parts):
        x.update(part=k, parts=len(parts))
    return parts


# Наименьшая ступень подгонки по бланку (решение автора 24.10): протоколы (и осмотра) и заключение СМЭ не ужимаются
# сильнее 0,94 — два листа на опрос или заключение — норма, мелкий текст — нет.
FIT_MIN_SCALE = {"protocol": 0.94, "inspection": 0.94, "forensic": 0.94}


def fit_scales(pages: int, fit, min_scale: float = 0.0) -> list[float]:
    """Ступени масштаба, которые можно пробовать для документа в ``pages`` страниц: при масштабе
    ``s`` в ``pages − 1`` страниц помещается не больше ``(pages − 1) × (1/s − 1)`` страницы «лишнего»
    текста — это и есть оценка заполнения последней страницы. Берём только ступени, где она не больше
    ``fit.last_page_min``: ужимается документ, у которого на последней странице несколько строк."""
    if pages < 2:
        return []
    return sorted((x for x in fit.scales
                   if min_scale - 1e-9 <= x < 1 and (pages - 1) * (1 / x - 1) <= fit.last_page_min + 1e-9),
                  reverse=True)


def fit_pdf(b: object, html: str, out: Path, fit, to_pdf, min_scale: float = 0.0) -> tuple[Path, int, float]:
    """Напечатать ``html`` в ``out``; если документ на ступени ``fit_scales`` становится на страницу
    короче — оставить самый крупный такой масштаб. Сначала пробуется самая мелкая допустимая ступень:
    не помогла она — не помогут и остальные (одна лишняя печать). → (путь, страниц, масштаб)."""
    out = Path(out)
    to_pdf(b, html, out)
    pages = pdf_pages(out)
    scales = fit_scales(pages, fit, min_scale)
    if not scales:
        return out, pages, 1.0
    best = out.with_name(f".{out.stem}.fit.pdf")
    trial = out.with_name(f".{out.stem}.try.pdf")
    try:
        to_pdf(b, html, best, scale=scales[-1])
        if pdf_pages(best) >= pages:
            return out, pages, 1.0
        chosen = scales[-1]
        for scale in scales[:-1]:  # от крупной к мелкой: первая подходящая — самая крупная
            to_pdf(b, html, trial, scale=scale)
            if pdf_pages(trial) < pages:
                trial.replace(best)
                chosen = scale
                break
        best.replace(out)
        return out, pdf_pages(out), chosen
    finally:
        best.unlink(missing_ok=True)
        trial.unlink(missing_ok=True)



def _common(content: Content, ctx: dict) -> dict[str, Any]:
    """Общий контекст бланков (_base.html)."""
    return {"w": ctx["w"], "c": ctx["c"], "game_title": content.settings.title, "print_cfg": content.settings.print,
            "page_margin": " ".join(f"{PAGE_MARGIN_MM[k]}mm" for k in ("top", "right", "bottom", "left")),
            "case_barcode": barcode_svg(str(ctx["w"].police.case_no))}


def render_part(tpl, items: list[dict], title: str, common: dict) -> str:
    """HTML печатаемой части: бланк, росчерки подписей, без средних точек."""
    return no_middot(add_autographs(tpl.render(docs=items, title=title, **common)))


def paper_html(content: Content, ids: list[str] | None = None, *, salts=None,
               media_dir: Path = MEDIA_DIR) -> dict[str, list[str]]:
    """HTML каждой печатаемой части документов без браузера (для проверок): id → [HTML части]."""
    from engine.printing import print_env

    ctx = make_context(content)
    ids = ids or paper_ids(content)
    cards = qr_cards(content, salts) if salts is not None else None
    tpl = print_env().get_template(TEMPLATE)
    common = _common(content, ctx)
    out: dict[str, list[str]] = {}
    for i in ids:
        d = doc_data(content, i, ctx, cards=cards if wants_qr(content, i) else None, media_dir=media_dir)
        out[i] = [render_part(tpl, [x], f"{i} — {d['title']}", common) for x in doc_parts(d)]
    return out


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
            for p in render_chats(content, Path(tmp), media_dir=media_dir, only=chat_ids, paper=True):
                chat_pngs.setdefault(p.name.rsplit("-", 1)[0], []).append(p)
        docs = {i: doc_data(content, i, ctx, cards=cards, chat_pngs=chat_pngs, media_dir=media_dir) for i in ids}
        if release:
            problems = release_problems(content, ids, docs, rep.warnings)
            if problems:
                raise PaperError(problems)

        env = print_env()
        tpl = env.get_template(TEMPLATE)
        pcfg = content.settings.print
        common = _common(content, ctx)

        def html(items: list[dict], title: str) -> str:
            return render_part(tpl, items, title, common)

        for i in ids:
            d = docs[i]
            if not d["stub"] and MIDDOT in "\n".join([d["source"], d["title"], repr(d["meta"]), repr(d["signed"]),
                                                       d["date"] or "", d["place"] or ""]):
                rep.warnings.append(f"content/paper/{i}.md: средняя точка «{MIDDOT}» как разделитель запрещена — при печати "
                                    "заменена запятой; поправить текст")

        def sheets(pages: int) -> int:
            return math.ceil(pages / 2) if pcfg.duplex else pages

        work = Path(tmp)
        verso = None
        todos = _file_todos(content)
        # Номер листа дела — сквозной по конверту; известен только при полной сборке (не --only).
        next_sheet: dict[int, int] = {}
        with browser() as b:
            if pcfg.duplex:
                verso = html_to_pdf(b, no_middot(env.get_template(VERSO_TEMPLATE).render(**common)), work / "verso.pdf")
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
                    pdf, pages, scale = fit_pdf(b, part_html, target, pcfg.fit, html_to_pdf,
                                                FIT_MIN_SCALE.get(d["form"], 0.0))
                    pdfs.append(pdf)
                    row.scale = min(row.scale, scale)
                    if not only:
                        next_sheet[d["stage"]] = part["sheet_start"] + sheets(pages)
                    if k == 0 and preview:
                        land = d["form"] in LANDSCAPE_FORMS
                        row.preview = html_to_png(b, part_html, out / "preview" / f"{i}.png",
                                                  width=PREVIEW_H if land else PREVIEW_W,
                                                  height=PREVIEW_W if land else PREVIEW_H, scale=PREVIEW_SCALE)
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
                row.notes += [x.split(": ", 1)[-1] for x in d.get("problems", [])]
                printed = row.pages - row.blanks
                if row.pages_hint is not None and printed != row.pages_hint:
                    row.notes.append(f"страниц {printed}, ожидалось {row.pages_hint} (pages_hint)")
                rep.rows.append(row)
            if not only:
                # Фото-карточки персонажей (полароиды) — отдельный сборник cards-<N>.pdf на конверт.
                cards_tpl = env.get_template(CARDS_TEMPLATE)
                for n, cast in sorted(cast_cards(content, docs, ctx, media_dir).items()):
                    sheets_ = [cast[k:k + CARDS_PER_SHEET] for k in range(0, len(cast), CARDS_PER_SHEET)]
                    pdf = html_to_pdf(b, no_middot(cards_tpl.render(sheets=sheets_, stage=n, **common)),
                                      out / f"cards-{n}.pdf")
                    rep.cards.append(CardsRow(n, pdf, [x["id"] for x in cast], pdf_pages(pdf),
                                              [x["id"] for x in cast if not x["exists"]]))
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
