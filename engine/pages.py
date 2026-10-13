"""Вымышленные страницы (FORMATS §6, docs/02 §3.8–3.9).

Для каждой ``content/pages/<slug>``: фрагмент ``site/templates/pages/<slug>.html``
(контекст ``page``, ``people``, ``media``, фильтр ``dt``), затем

- ``locked: false`` → ``p/<slug>/index.html`` = ``page_open.html`` с фрагментом, прямые ``src``;
- ``locked: true`` → ``page_shell.html`` + ``payload.json`` (``Box`` на ключе ``K_p``, ``aad = page/<slug>``);
- ``locked: password`` → ``page_shell.html`` + ``{"salt", "iter", "box"}`` на ключе от пароля.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from markupsafe import Markup

from engine import crypto
from engine.content import Content
from engine.media import MediaCollector, MediaPlan
from engine.models import CloudPage, PageBase
from engine.normalize import normalize
from engine.templating import render, render_markdown, render_tree

STUB_BODY_HTML = "<p>Здесь будет текст.</p>"
HIDDEN_FIELDS = {"password", "forbidden", "qr_label", "doc"}
# Поля, видимые в открытой оболочке закрытой страницы или служебные — не «тексты страницы» для leak scan.
SHELL_FIELDS = {"slug", "locked", "brand", "account"}
# Скрипты интерактива открытых страниц (FORMATS §9.3: entry или null).
OPEN_ENTRY = {"call": "/assets/js/pages/audio-player.js"}
SHELL_ENTRY = "/assets/js/pages/shell.js"


@dataclass
class PageOut:
    slug: str
    access: str  # open | key | password
    index_html: str
    payload: dict | None = None
    fragment: str = ""  # отрендеренный фрагмент (для forbidden и тестов)
    media: list[dict] = field(default_factory=list)


def access_of(page: PageBase) -> str:
    return {False: "open", True: "key", "password": "password"}[page.locked]


def page_css(slug: str) -> list[str]:
    """Стили страницы сверх base.html (base, app, blank, print подключены всегда); у video — только app.css."""
    return [] if slug == "video" else [f"/assets/css/pages/{slug}.css"]


def page_data(content: Content, page: PageBase, ctx: dict) -> dict:
    """Модель страницы → dict с отрендеренными строками и ``body_html`` (FORMATS §6.1)."""
    data = page.model_dump(by_alias=True, exclude=HIDDEN_FIELDS)
    data = render_tree(data, ctx, f"content/pages/{page.slug}/page.yaml")

    def body_html(rel: str | None) -> Markup:
        text = content.texts.get(rel) if rel else None
        if text is None:
            return Markup(STUB_BODY_HTML)
        return Markup(render_markdown(render(text, ctx, f"content/{rel}: текст")))

    if "article" in data:
        data["article"]["body_html"] = body_html(data["article"].pop("body", None))
    for folder in data.get("folders", []):
        if folder.get("kind") == "letter":
            folder["body_html"] = body_html(folder.pop("body", None))
    return data


def page_people(content: Content, page: PageBase, ctx: dict) -> dict[str, dict]:
    ids: list[str] = []
    profile = getattr(page, "profile", None)
    if profile is not None:
        ids.append(profile.person)
    for f in getattr(page, "folders", None) or []:
        ids.extend(f.participants or [])
    c = ctx["c"]
    return {pid: {"full": getattr(c, pid).full(), "short": getattr(c, pid).short()} for pid in dict.fromkeys(ids)}


def page_title(page: PageBase, data: dict, chrome: dict) -> str:
    """``title`` payload и заголовок открытой страницы: у video — ``page.title``, иначе ``brand``."""
    if page.slug == "video" or "brand" not in data:
        return data.get("title") or chrome["system"]
    return data["brand"]


def build_page(content: Content, page: PageBase, ctx: dict, salts: Any, plan: MediaPlan, site_env: Any,
               base_ctx: dict) -> PageOut:
    slug = page.slug
    access = access_of(page)
    data = page_data(content, page, ctx)
    collector = MediaCollector(plan, "open" if access == "open" else "sealed")
    fragment = site_env.get_template(f"pages/{slug}.html").render(
        page=data, people=page_people(content, page, ctx), media=collector
    )
    title = page_title(page, data, base_ctx["chrome"])
    if access == "open":
        html = site_env.get_template("page_open.html").render(
            **base_ctx, title=title, entry=OPEN_ENTRY.get(slug), css=page_css(slug), body_class=f"page page--{slug}",
            slug=slug, brand=title, fragment=Markup(fragment),
        )
        return PageOut(slug, access, html, None, fragment)

    inner = {"v": 1, "slug": slug, "title": title, "html": fragment, "media": collector.refs}
    from engine.lab import dumps

    if access == "key":
        payload: dict = crypto.seal(salts.page_key(slug), dumps(inner), f"page/{slug}")
    else:
        assert isinstance(page, CloudPage)
        iters = content.settings.crypto.iter_stage
        key = crypto.cloud_key(cloud_password_norm(page), salts.cloud, iters)
        payload = {"salt": crypto.b64u_encode(salts.cloud), "iter": iters,
                   "box": crypto.seal(key, dumps(inner), f"page/{slug}")}
    shell_brand = base_ctx["chrome"]["system"] if slug == "video" else data.get("brand", base_ctx["chrome"]["system"])
    html = site_env.get_template("page_shell.html").render(
        **base_ctx, title=shell_brand, entry=SHELL_ENTRY, css=page_css(slug), body_class=f"page page--{slug} shell",
        slug=slug, access=access, brand=shell_brand, account=data.get("account") if access == "password" else None,
    )
    return PageOut(slug, access, html, payload, fragment, collector.refs)


def cloud_password_norm(page: CloudPage) -> str:
    pw = normalize("password", page.password)
    if not pw:
        raise ValueError("пароль облака пуст после нормализации")
    return pw


def locked_page_texts(content: Content, ctx: dict) -> list[tuple[str, str]]:
    """Строки закрытых страниц (для leak scan): ``[(источник, текст)]``, без полей оболочки."""
    out: list[tuple[str, str]] = []
    for slug, page in content.pages.items():
        if page.locked is False:
            continue
        data = page.model_dump(by_alias=True, exclude=HIDDEN_FIELDS | SHELL_FIELDS)
        rendered = render_tree(data, ctx)
        from engine.util import format_loc, iter_strings

        for loc, s in iter_strings(rendered):
            out.append((f"content/pages/{slug}/page.yaml: {format_loc(loc)}", s))
        for f in getattr(page, "folders", None) or []:
            if f.body and f.body in content.texts:
                out.append((f"content/{f.body}", render(content.texts[f.body], ctx)))
    return out
