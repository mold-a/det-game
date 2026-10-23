"""Вымышленные страницы (FORMATS §6, docs/02 §3.8–3.9, docs/REDESIGN-2026-10 §4).

Для каждой ``content/pages/<slug>``: фрагмент ``site/templates/pages/<type>.html`` (``type`` по
умолчанию равен ``slug``; контекст ``page``, ``people``, ``media``, ``link``, ``service``, фильтр
``dt``), затем

- ``locked: false`` → ``p/<slug>/index.html`` = ``page_open.html`` с фрагментом, прямые ``src``;
- ``locked: true`` → ``page_shell.html`` + ``payload.json`` (``Box`` на ключе ``K_p``, ``aad = page/<slug>``);
- ``locked: password`` → ``page_shell.html`` + ``{"salt", "iter", "box"}`` на ключе от пароля.

Здесь же — ссылки между страницами: ``page:`` в структурных полях и ``{{ link('slug') }}`` в текстах
(``engine.templating.make_link``), проверки §4.1 (``check_links``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from markupsafe import Markup

from engine import crypto
from engine.content import Content
from engine.media import MediaCollector, MediaPlan
from engine.models import CloudPage, Document, PageBase
from engine.normalize import normalize
from engine.templating import (
    RenderError,
    make_context,
    page_href,
    render,
    render_inline,
    render_markdown,
    render_tree,
)
from engine.util import format_loc, iter_strings

STUB_BODY_HTML = "<p>Здесь будет текст.</p>"
HIDDEN_FIELDS = {"password", "forbidden", "qr_label", "doc", "stage", "type"}
# Поля, видимые в открытой оболочке закрытой страницы или служебные — не «тексты страницы» для leak scan.
SHELL_FIELDS = {"slug", "locked", "brand", "account", "skin"}
# Скрипт открытых страниц: общие окна/вкладки/просмотр фото + модуль типа (PAGE_MODULES в page-modules.js).
OPEN_ENTRY = "/assets/js/pages/open.js"
SHELL_ENTRY = "/assets/js/pages/shell.js"

# Куда ведут логотип «Круга» и авторы без своей страницы (REDESIGN §4.1).
SOCIAL_TYPES = ("social", "social_home", "social_stub")
SOCIAL_HOME = "krug"
SOCIAL_STUB = "krug-private"
# Тексты подвала берутся из pages/_brands.yaml по ключу бренда.
SERVICE_OF_TYPE = {
    "social": "social", "social_home": "social", "social_stub": "social",
    "inna": "photo", "news": "news", "pharma": "pharma", "cloud": "cloud",
}
# Стили сверх base.html: общие окна — всегда (кроме video: его стиль — система расследования).
UI_CSS = "/assets/css/pages/_ui.css"
CSS_OF_TYPE: dict[str, list[str]] = {
    "social_home": ["social", "social_home"],
    "social_stub": ["social", "social_stub"],
}


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


def page_stage(page: PageBase, docs_by_id: dict[str, Document]) -> int:
    """Этап страницы: этап её документа ``doc`` или поле ``stage``."""
    if page.doc is not None:
        return docs_by_id[page.doc].stage
    assert page.stage is not None
    return page.stage


def body_classes(page: PageBase, extra: str = "") -> str:
    """Классы body: ``page``, ``page--<type>``, ``page--<slug>`` и семейство (``page--social`` у social_home и
    social_stub — общая палитра и шрифт)."""
    names = ["page", f"page--{page.type}", f"page--{page.slug}"]
    if page.type in SOCIAL_TYPES:
        names.append("page--social")
    if page.type == "site":
        names.append(f"skin-{page.skin}")  # скин нужен и оболочке закрытой страницы, до расшифровки
    out = " ".join(dict.fromkeys(names))
    return f"{out} {extra}".strip()


def page_css(page: PageBase) -> list[str]:
    """Стили страницы сверх base.html (base, app, blank, print подключены всегда); у video — только app.css."""
    t = page.type
    if t == "video":
        return []
    names = list(CSS_OF_TYPE.get(t, [t]))
    if t == "site":
        names.append(f"site-{page.skin}")
    return [UI_CSS, *(f"/assets/css/pages/{n}.css" for n in names)]


def inline_md_if_link(text: str) -> Markup | None:
    """Ячейка или реплика с Markdown-ссылкой ``[текст](адрес)`` → HTML; обычный текст — ``None`` (шаблон выведет как есть)."""
    return Markup(render_inline(text)) if "](" in text else None


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
        if folder.get("kind") == "table":
            folder["rows_html"] = [[inline_md_if_link(c) for c in row] for row in folder["rows"]]
        for m in folder.get("messages") or []:
            m["text_html"] = inline_md_if_link(m["text"])
    for post in data.get("posts", []):
        if "text" in post:  # social: Markdown в одну строку (ссылки link('…'))
            post["text_html"] = Markup(render_inline(post["text"]))
            for cm in post.get("comments", []):
                cm["text_html"] = Markup(render_inline(cm["text"])) if cm["text"] else ""
    for sec in data.get("sections", []):
        for block in sec["blocks"]:
            if block["kind"] == "text":
                block["html"] = Markup(render_markdown(block["md"]))
    return data


def page_people(content: Content, page: PageBase, ctx: dict) -> dict[str, dict]:
    ids: list[str] = []
    profile = getattr(page, "profile", None)
    if profile is not None:
        if profile.person:
            ids.append(profile.person)
        ids.extend(f.person for f in getattr(profile, "friends", None) or [] if f.person)
    for f in getattr(page, "folders", None) or []:
        ids.extend(f.participants or [])
    c = ctx["c"]
    return {pid: {"full": getattr(c, pid).full(), "short": getattr(c, pid).short()} for pid in dict.fromkeys(ids)}


def profile_name(profile: dict, people: dict[str, dict]) -> str:
    """Имя владельца профиля из отрендеренных данных страницы: персонаж (``person``) или ``name``."""
    return people[profile["person"]]["full"] if profile.get("person") else profile["name"]


def social_directory(content: Content, ctx: dict) -> list[dict]:
    """«Поиск людей» на главной сервиса: открытые профили ``social`` этапа 1 — имя, должность, страница."""
    docs = content.documents_by_id
    out = []
    for slug, p in content.pages.items():
        if p.type != "social" or p.locked is not False or page_stage(p, docs) != 1:
            continue
        pr = p.profile
        name = getattr(ctx["c"], pr.person).full() if pr.person else pr.name
        out.append({"name": render(name, ctx), "position": render(pr.position or "", ctx), "page": slug})
    return sorted(out, key=lambda e: e["name"])


def service_texts(content: Content, page: PageBase, ctx: dict) -> dict | None:
    """Тексты подвала сервиса страницы (``_brands.yaml``) или ``None``."""
    st = content.services.get(SERVICE_OF_TYPE.get(page.type, ""))
    if st is None:
        return None
    return {k: render(v, ctx, f"content/pages/_brands.yaml: {k}") for k, v in st.model_dump().items()}


def page_title(page: PageBase, data: dict, chrome: dict, people: dict[str, dict] | None = None) -> str:
    """``title`` payload и заголовок открытой страницы: у video — ``page.title``, иначе ``brand``
    (у профиля соцсети — «Имя — бренд»)."""
    if page.slug == "video" or "brand" not in data:
        return data.get("title") or chrome["system"]
    if page.type == "social" and people is not None:
        return f"{profile_name(data['profile'], people)} — {data['brand']}"
    return data["brand"]


def build_page(content: Content, page: PageBase, ctx: dict, salts: Any, plan: MediaPlan, site_env: Any,
               base_ctx: dict) -> PageOut:
    slug = page.slug
    ptype = page.type
    access = access_of(page)
    data = page_data(content, page, ctx)
    people = page_people(content, page, ctx)
    collector = MediaCollector(plan, "open" if access == "open" else "sealed")
    fragment = site_env.get_template(f"pages/{ptype}.html").render(
        page=data, people=people, media=collector, link=ctx["link"], service=service_texts(content, page, ctx),
        directory=social_directory(content, ctx) if ptype == "social_home" else [],
        social_home=SOCIAL_HOME, social_stub=SOCIAL_STUB,
    )
    title = page_title(page, data, base_ctx["chrome"], people)
    if access == "open":
        html = site_env.get_template("page_open.html").render(
            **base_ctx, title=title, entry=OPEN_ENTRY, css=page_css(page), body_class=body_classes(page),
            slug=slug, ptype=ptype, brand=title, fragment=Markup(fragment),
        )
        return PageOut(slug, access, html, None, fragment)

    inner = {"v": 1, "slug": slug, "type": ptype, "title": title, "html": fragment, "media": collector.refs}
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
        **base_ctx, title=shell_brand, entry=SHELL_ENTRY, css=page_css(page),
        body_class=body_classes(page, "shell"),
        slug=slug, ptype=ptype, access=access, brand=shell_brand,
        account=data.get("account") if access == "password" else None,
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


# ---------------------------------------------------------------- ссылки между страницами (REDESIGN §4.1)


@dataclass
class LinkReport:
    """Результат проверки ссылок: ``(slug страницы, место, сообщение)``."""

    errors: list[tuple[str, str, str]] = field(default_factory=list)
    warnings: list[tuple[str, str, str]] = field(default_factory=list)


def body_rels(page: PageBase) -> list[tuple[tuple, str]]:
    """Markdown-файлы страницы: ``[(путь до поля, относительный путь)]``."""
    out: list[tuple[tuple, str]] = []
    article = getattr(page, "article", None)
    if article is not None:
        out.append((("article", "body"), article.body))
    for fi, f in enumerate(getattr(page, "folders", None) or []):
        if f.body:
            out.append((("folders", fi, "body"), f.body))
    return out


def structural_links(obj: Any, loc: tuple = ()) -> list[tuple[str, str]]:
    """Все поля ``page: <slug>`` в дереве страницы: ``[(slug, путь до поля)]``."""
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "page" and isinstance(v, str):
                out.append((v, format_loc((*loc, k))))
            else:
                out += structural_links(v, (*loc, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += structural_links(v, (*loc, i))
    return out


def implicit_links(page: PageBase, social_profiles: list[str]) -> list[tuple[str, str]]:
    """Ссылки, которые шаблон ставит сам: логотип «Круга» → главная, авторы без страницы → заглушка,
    поиск людей на главной → открытые профили этапа 1, логотип ``news-*`` → ``news``."""
    out: list[tuple[str, str]] = []
    if page.type in SOCIAL_TYPES:
        out.append((SOCIAL_HOME, "логотип"))
        if page.type == "social":
            lacking = any(c.page is None for p in page.posts for c in p.comments) or \
                any(f.page is None for f in page.profile.friends)
            if lacking:
                out.append((SOCIAL_STUB, "автор без страницы"))
        if page.type == "social_home":
            out += [(s, "поиск людей") for s in social_profiles]
    if page.type == "news" and page.slug != "news":
        out.append(("news", "логотип"))
    return out


def check_links(pages: dict[str, PageBase], documents: list[Document], texts: dict[str, str],
                characters: list, world: dict, services: dict | None = None) -> LinkReport:
    """Проверки §4.1: цель существует; ``stage(B) ≤ stage(A)``; из открытой страницы — только на этап 1.

    Ссылки берутся из полей ``page:``, из вызовов ``link('slug')`` в строках страницы и её Markdown-файлов,
    а также из ссылок, которые ставит шаблон сам (``implicit_links``). Страница без ``doc`` (QR нет),
    на которую никто не ссылается, — предупреждение: игроки до неё не доберутся.
    """
    rep = LinkReport()
    docs_by_id = {d.id: d for d in documents}
    stage_of = {slug: page_stage(p, docs_by_id) for slug, p in pages.items() if p.doc in docs_by_id or p.doc is None}
    base = make_context(characters=characters, world=world)
    profiles = [s for s, p in pages.items() if p.type == "social" and p.locked is False and stage_of.get(s) == 1]
    inbound: dict[str, set[str]] = {}

    for slug, page in pages.items():
        if slug not in stage_of:
            continue
        edges: list[tuple[str, str]] = []
        dump = page.model_dump(by_alias=True)
        edges += structural_links(dump)
        cur: list[str] = []

        def rec(target: str, _cur=cur) -> str:
            edges.append((target, _cur[0]))
            return page_href(target)

        ctx = {**base, "link": rec}
        for loc, s in iter_strings(dump):
            if "link(" in s:
                cur[:] = [format_loc(loc)]
                try:
                    render(s, ctx)
                except RenderError:
                    pass  # ошибку шаблона покажет общая проверка шаблонов
        for loc, rel in body_rels(page):
            text = texts.get(rel)
            if text and "link(" in text:
                cur[:] = [f"{format_loc(loc)} → {rel}"]
                try:
                    render(text, ctx)
                except RenderError:
                    pass
        edges += implicit_links(page, profiles)

        a_open = page.locked is False
        seen: set[tuple[str, str]] = set()
        for target, where in edges:
            if (target, where) in seen:
                continue
            seen.add((target, where))
            if target not in pages:
                rep.errors.append((slug, where, f"ссылка на страницу «{target}», которой нет в content/pages/"))
                continue
            if target != slug:
                inbound.setdefault(target, set()).add(slug)
            sa, sb = stage_of[slug], stage_of.get(target)
            if sb is None:
                continue
            if sb > sa:
                rep.errors.append((slug, where, f"ссылка на «{target}» (этап {sb}) со страницы этапа {sa}: "
                                                "игроки могут ещё не дойти до этой страницы"))
            elif a_open and sb != 1:
                rep.errors.append((slug, where, f"открытая страница ссылается на «{target}» (этап {sb}): адрес с ключом "
                                                "попадёт в открытый файл; из открытых страниц можно ссылаться "
                                                "только на страницы этапа 1"))

    for slug, page in pages.items():
        if page.doc is None and slug not in inbound:
            rep.warnings.append((slug, "", "страница без doc и без входящих ссылок: QR не печатается, и никто на "
                                           "неё не ссылается — игроки до неё не доберутся"))
    return rep


_HREF_RE = re.compile(r'href="/p/([a-z0-9_-]+)/(#[^"]*)?"')


def rendered_link_problems(content: Content, salts: Any, fragments: dict[str, str]) -> list[str]:
    """Ссылки в готовом HTML (открытые страницы целиком, закрытые — расшифрованные фрагменты): цель есть
    в ``dist``-наборе страниц, адрес ключа точно такой же, как в QR, этапы подчиняются тем же правилам, что
    и в ``check_links``. Ловит расхождение между контентом и тем, что реально записано в страницы."""
    from engine.util import b64u_encode

    problems: list[str] = []
    docs = content.documents_by_id
    for slug, html in fragments.items():
        if slug not in content.pages:
            continue
        page = content.pages[slug]
        for m in _HREF_RE.finditer(html):
            target, frag = m.group(1), m.group(2) or ""
            tp = content.pages.get(target)
            if tp is None:
                problems.append(f"{slug}: ссылка на несуществующую страницу «{target}»")
                continue
            want = f"#k={b64u_encode(salts.page_key(target))}" if tp.locked is True else ""
            # якорь без ключа (``#search``) у открытой страницы допустим; ключ — только точь-в-точь как в QR
            if (want and frag != want) or (not want and frag.startswith("#k=")):
                problems.append(f"{slug}: адрес ссылки на «{target}» не совпадает с адресом из QR "
                                f"({'нужен ключ' if want else 'ключ не нужен'})")
            sa, sb = page_stage(page, docs), page_stage(tp, docs)
            if sb > sa:
                problems.append(f"{slug}: ссылка на «{target}» этапа {sb} со страницы этапа {sa}")
            elif page.locked is False and sb != 1:
                problems.append(f"{slug}: открытая страница ссылается на «{target}» этапа {sb} (ключ в открытом файле)")
    return problems
