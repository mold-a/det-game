"""Документы ``content/documents/*.md``: front matter + Markdown → HTML в бланке.

Front matter и тело — шаблоны контента (``c``, ``w``); тело затем Markdown → HTML
(``markdown-it-py``, ``html=False``) и оборачивается в ``site/templates/blanks/<form>.html``.
Медиа из ``media:`` — через ``data-media`` (FORMATS §3.2). Отсутствующий файл — заглушка.

Протокол (``form: protocol``) с полями шапки во front matter (``date``, ``place``, ``meta``, ``signed`` —
как у бумажного протокола) выводится тем же разбором, что и бумага (``engine/protocol.py``): поля
«метка — значение», реплики с фамилиями, подписи. Метки ``<!-- person: <id> -->`` из текста убираются
(Markdown сайта не пропускает сырой HTML) и называют допрашиваемого.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from markupsafe import Markup

from engine.content import DocFile
from engine.media import MediaCollector, MediaPlan
from engine.protocol import interview, person_marks, strip_person_marks
from engine.templating import render, render_markdown, render_tree

STUB_HTML = "<p>Здесь будет текст документа.</p>"


@dataclass
class RenderedDoc:
    doc: str | None
    title: str
    form: str | None
    html: str
    media: list[dict] = field(default_factory=list)
    source: str = ""  # отрендеренный Markdown — для leak scan

    def record(self) -> dict[str, Any]:
        """Внутренний JSON записи экспертизы / развязки (FORMATS §3.2, §4) без ``v``/``doc``."""
        return {"title": self.title, "form": self.form, "html": self.html, "media": self.media}


def render_document(df: DocFile | None, ctx: dict, plan: MediaPlan, site_env: Any, *,
                    doc_id: str | None = None, fallback_title: str = "") -> RenderedDoc:
    if df is None:
        return RenderedDoc(doc=doc_id, title=fallback_title, form=None, html=STUB_HTML, source="")
    where = f"content/{df.path}"
    meta = df.meta
    title = render(meta.title, ctx, f"{where}: front matter.title")
    source = render(df.body, ctx, f"{where}: текст")
    marks = person_marks(source)
    source = strip_person_marks(source)
    body_html = render_markdown(source)
    collector = MediaCollector(plan, "sealed")
    media_attrs = [{"attrs": collector(m, title), "kind": plan.files[m].mime.split("/")[0]} for m in meta.media]
    proto, signed = None, []
    if meta.form == "protocol" and (meta.meta or meta.date or meta.place or meta.signed):
        r = lambda v, loc: None if v is None else render(v, ctx, f"{where}: front matter.{loc}")  # noqa: E731
        head = {"date": r(meta.date, "date"), "place": r(meta.place, "place"),
                "meta": render_tree(meta.meta, ctx, where, ("front matter", "meta"))}
        proto = interview(head, body_html, _person(ctx, marks[0]) if marks else None, ctx)
        signed = [{"role": r(x.role, f"signed[{i}].role"), "name": r(x.name, f"signed[{i}].name")}
                  for i, x in enumerate(meta.signed)]
    html = site_env.get_template(f"blanks/{meta.form}.html").render(
        doc_id=doc_id or meta.id,
        title=title,
        form=meta.form,
        body_html=Markup(body_html),
        media=media_attrs,
        proto=proto,
        signed=signed,
    )
    return RenderedDoc(doc=doc_id, title=title, form=meta.form, html=html, media=collector.refs, source=source)


def _person(ctx: dict, cid: str) -> dict[str, Any]:
    """Допрашиваемый по метке ``<!-- person -->``: известен ли персонаж (тогда фамилия в репликах — его)."""
    from engine.templating import TemplateRefError

    try:
        ctx["c"][cid]
    except (KeyError, AttributeError, TemplateRefError):
        return {"id": cid, "known": False}
    return {"id": cid, "known": True}
