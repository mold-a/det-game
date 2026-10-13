"""``python -m engine paper`` — бумажные документы дела (конверты 1–4) для печати.

Вход — ``content/paper/<id>.md`` (схема ``engine.models.PaperFrontMatter``, docs/03 «paper/»):
front matter и тело — шаблоны контента (``c``, ``w``), тело — Markdown (таблицы и HTML разрешены:
это печать, не сайт). Бланк — ``site/templates/print/paper/<form>.html``.

Выход (``print/paper/``, в ``.gitignore``):

- ``<id>.pdf`` — каждый документ, A4;
- ``envelope-<N>.pdf`` — все бумажные документы конверта N по порядку ``documents.yaml``, каждый
  с новой страницы (один HTML → один PDF); без ``--only``;
- ``preview/<id>.png`` — первая страница для просмотра.

QR-код страницы (та же ссылка, что у ``python -m engine qr``; у облака — без ключа) печатается в
углу документа с подписью ``qr_label``. Документы-переписки (``form: chat``) получают «скриншоты»
из ``content/chats/<id>.yaml`` (генерируются на лету, как ``python -m engine chatshot``).
Документ без текста — страница-заглушка; в ``--release`` это ошибка (как и TODO(content), нет
медиа, домен-заглушка у QR).

Сайт (``build``) бумагу не публикует; ``check`` ищет шинглы бумаги в ``dist/`` (``paper_texts``).
"""

from __future__ import annotations

import re
import tempfile
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
_PDF_PAGE = re.compile(rb"/Type\s*/Page(?![a-zA-Z])")
STATUS_OK = "готов"


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
        head = ("id", "бланк", "страниц", "статус")
        body = [(r.id, r.form, "—" if r.pages is None else str(r.pages), r.status) for r in self.rows]
        w = [max(len(x[i]) for x in [head, *body]) for i in range(3)]
        line = lambda x: "  ".join([x[0].ljust(w[0]), x[1].ljust(w[1]), x[2].rjust(w[2]), x[3]])  # noqa: E731
        return "\n".join([line(head), line(tuple("-" * n for n in (*w, 6))), *(line(x) for x in body)])


# ---------------------------------------------------------------- Markdown для печати


@lru_cache(maxsize=1)
def _md():
    from markdown_it import MarkdownIt

    # Печать, не сайт: сырой HTML разрешён (сложные бланки), таблицы GFM включены.
    return MarkdownIt("commonmark", {"html": True, "typographer": False}).enable("table")


def paper_markdown(md: str) -> str:
    return _md().render(md)


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
    problems += qr_warnings
    return problems


def pdf_pages(path: Path) -> int:
    """Число страниц PDF Chromium (объекты ``/Type /Page``)."""
    return len(_PDF_PAGE.findall(Path(path).read_bytes()))


# ---------------------------------------------------------------- печать


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
        common = {"w": ctx["w"], "c": ctx["c"], "game_title": content.settings.title}

        def html(items: list[dict], title: str) -> str:
            return tpl.render(docs=items, title=title, **common)

        todos = _file_todos(content)
        with browser() as b:
            for i in ids:
                d = docs[i]
                row = PaperRow(i, d["form"], d["stage"], pages_hint=d["pages_hint"])
                page_html = html([d], f"{i} — {d['title']}")
                row.pdf = html_to_pdf(b, page_html, out / f"{i}.pdf")
                row.pages = pdf_pages(row.pdf)
                if preview:
                    row.preview = html_to_png(b, page_html, out / "preview" / f"{i}.png",
                                              width=PREVIEW_W, height=PREVIEW_H, scale=PREVIEW_SCALE)
                if d["stub"]:
                    row.notes.append("нет текста — заглушка")
                if todos.get(i) or _rendered_todo(d):
                    row.notes.append("TODO(content)")
                missing_media = [m["path"] for m in d["media"] if not m["exists"]]
                if missing_media:
                    row.notes.append("нет медиа: " + ", ".join(missing_media))
                if row.pages_hint is not None and row.pages != row.pages_hint:
                    row.notes.append(f"страниц {row.pages}, ожидалось {row.pages_hint} (pages_hint)")
                rep.rows.append(row)
            if not only:
                for n in sorted({docs[i]["stage"] for i in ids}):
                    items = [docs[i] for i in ids if docs[i]["stage"] == n]
                    rep.envelopes.append(html_to_pdf(b, html(items, f"Конверт {n}"), out / f"envelope-{n}.pdf"))
    return rep


def run(root: Path = ROOT, *, out: Path = PRINT_PAPER, only: list[str] | None = None, release: bool = False,
        salts_path: Path | None = None) -> PaperReport:
    content = load_content(Path(root) / "content")
    salts = salts_mod.read(Path(salts_path or salts_mod.SALTS_LOCK))
    return render_paper(content, out, salts=salts, only=only, release=release, media_dir=Path(root) / "media")
