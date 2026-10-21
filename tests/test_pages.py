"""Сеть вымышленных страниц (REDESIGN-2026-10 §4): type, doc/stage, link(), проверки ссылок, шаблоны типов.

Тестовые страницы (театр, фонд, клуб, второй профиль, вторая статья) живут в tests/fixtures/pages и
добавляются в КОПИЮ content/ (tests/pages_fixture.py); в content/ их нет.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pages_fixture import add_fixture_pages, copy_content  # noqa: E402

from engine import ROOT, crypto  # noqa: E402
from engine import salts as salts_mod  # noqa: E402
from engine.build import build  # noqa: E402
from engine.content import ContentError, load_content  # noqa: E402
from engine.models import CallPage, NewsPage, SitePage, SocialPage, SocialStubPage  # noqa: E402
from engine.pages import check_links, cloud_password_norm, page_css, rendered_link_problems  # noqa: E402
from engine.qr import plan_cards, qr_url  # noqa: E402
from engine.templating import RenderError, TemplateRefError, make_context, make_link, render  # noqa: E402
from engine.util import b64u_encode  # noqa: E402


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return copy_content(tmp_path)


@pytest.fixture
def fx(tmp_path: Path) -> Path:
    c = copy_content(tmp_path)
    add_fixture_pages(c)
    return c


def edit_yaml(root: Path, rel: str, fn) -> None:
    p = root / rel
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    fn(data)
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def new_page(root: Path, slug: str, data: dict, body: dict[str, str] | None = None) -> None:
    d = root / "pages" / slug
    d.mkdir(parents=True)
    (d / "page.yaml").write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    for name, text in (body or {}).items():
        (d / name).write_text(text, encoding="utf-8")


def errors_of(root: Path) -> list[str]:
    with pytest.raises(ContentError) as exc:
        load_content(root)
    return [str(e) for e in exc.value.errors]


def has_error(errs: list[str], *parts: str) -> bool:
    return any(all(p in e for p in parts) for e in errs)


# ---------------------------------------------------------------- модели и type


def test_type_defaults_to_slug_and_gromov_is_social():
    c = load_content(ROOT / "content")
    assert [c.pages[s].type for s in ("call", "inna", "news", "pharma", "cloud", "video")] == \
        ["call", "inna", "news", "pharma", "cloud", "video"]
    assert isinstance(c.pages["gromov"], SocialPage) and c.pages["gromov"].doc == "1-12"
    assert isinstance(c.pages["krug-private"], SocialStubPage) and c.pages["krug-private"].doc is None
    assert c.pages["krug-private"].stage == 1


def test_unknown_type_and_foreign_slug_need_type(root):
    new_page(root, "news-x", {"slug": "news-x", "stage": 1, "locked": False})
    assert has_error(errors_of(root), "news-x", "нужно поле type")
    (root / "pages" / "news-x" / "page.yaml").write_text(
        'slug: news-x\ntype: nope\nstage: 1\nlocked: false\n', encoding="utf-8")
    assert has_error(errors_of(root), "типа «nope»")


def test_doc_or_stage_required(root):
    edit_yaml(root, "pages/krug-private/page.yaml", lambda d: d.pop("stage"))
    assert has_error(errors_of(root), "krug-private", "doc", "stage")


def test_qr_label_only_with_doc_and_required_with_doc(root):
    edit_yaml(root, "pages/krug-private/page.yaml", lambda d: d.update(qr_label="Подпись"))
    assert has_error(errors_of(root), "qr_label бывает только у страницы с doc")
    shutil.rmtree(root.parent / "c2", ignore_errors=True)
    root2 = copy_content(root.parent / "c2")
    edit_yaml(root2, "pages/call/page.yaml", lambda d: d.pop("qr_label"))
    assert has_error(errors_of(root2), "call", "qr_label")


def test_stage_must_match_doc(root):
    edit_yaml(root, "pages/call/page.yaml", lambda d: d.update(stage=3))
    assert has_error(errors_of(root), "call", "stage: 3")


def test_page_without_doc_but_document_points_to_it(root):
    edit_yaml(root, "documents.yaml", lambda d: d["documents"][0].update(page="krug-private"))
    assert has_error(errors_of(root), "krug-private", "doc")


def test_news_slug_and_type():
    with pytest.raises(ValidationError) as e:
        NewsPage.model_validate({"slug": "other", "doc": "1-13", "locked": False, "qr_label": "x", "brand": "b",
                                 "article": {"datetime": "2026-01-01T10:00", "headline": "h", "body": "b.md"}})
    assert "news-" in str(e.value)
    assert CallPage.model_fields["type"].default == "call"


def test_social_person_or_name(root):
    edit_yaml(root, "pages/gromov/page.yaml", lambda d: d["profile"].update(name="Кто-то"))
    assert has_error(errors_of(root), "profile", "ровно одно")


def test_site_models_validate_blocks(fx):
    c = load_content(fx)
    t = c.pages["theater"]
    assert isinstance(t, SitePage) and t.skin == "theater" and t.sections[0].blocks[0].kind == "notice"
    edit_yaml(fx, "pages/fund/page.yaml", lambda d: d.update(skin="rainbow"))
    assert has_error(errors_of(fx), "fund", "skin")
    edit_yaml(fx, "pages/fund/page.yaml", lambda d: d.update(skin="fund", sections=[{"id": "a", "title": "A", "blocks": [{"kind": "video"}]}]))
    assert errors_of(fx)


# ---------------------------------------------------------------- link()


def test_link_open_closed_and_qr_format(tmp_path):
    c = load_content(ROOT / "content")
    salts = salts_mod.load_or_init(tmp_path / "s.json", units=[], stages=[], pages=["inna", "pharma", "video"])
    link = make_link(c.pages, salts)
    assert link("gromov") == "/p/gromov/"
    key = b64u_encode(salts.page_key("inna"))
    assert link("inna") == f"/p/inna/#k={key}"
    # тот же адрес, что в QR (с доменом)
    assert qr_url("https://x.ru", "inna", key) == "https://x.ru" + link("inna")
    assert link("cloud") == "/p/cloud/"  # облако — пароль, без ключа в адресе
    with pytest.raises(TemplateRefError):
        link("nope")
    with pytest.raises(TemplateRefError):
        make_link(c.pages, None)("inna")  # ключей нет — подставить нечего


def test_link_in_context_and_render_errors():
    c = load_content(ROOT / "content")
    ctx = make_context(c)
    assert render("[x]({{ link('krug') }})", ctx) == "[x](/p/krug/)"
    with pytest.raises(RenderError) as e:
        render("{{ link('net-takoy') }}", ctx)
    assert "net-takoy" in str(e.value)


def test_unknown_link_target_in_content_fails(root):
    edit_yaml(root, "pages/gromov/page.yaml",
              lambda d: d["posts"][1].update(text="Смотрите [тут]({{ link('net-takoy') }})"))
    errs = errors_of(root)
    assert has_error(errs, "gromov", "net-takoy")


# ---------------------------------------------------------------- правила ссылок §4.1


def link_problem_messages(c) -> list[str]:
    rep = check_links(c.pages, c.documents, c.texts, c.characters, c.world, c.services)
    return [m for _, _, m in rep.errors]


def test_fixture_links_are_valid(fx):
    c = load_content(fx)
    assert link_problem_messages(c) == []
    assert not [w for w in c.warnings if "без входящих ссылок" in str(w)]


def test_page_field_unknown_target(root):
    edit_yaml(root, "pages/gromov/page.yaml", lambda d: d["posts"][1]["comments"][0].update(page="net-takoy"))
    assert has_error(errors_of(root), "gromov", "net-takoy", "нет в content/pages")


def test_open_page_may_link_only_to_stage_1(root):
    # inna — закрытая страница этапа 2: открытая gromov не может на неё ссылаться (ключ попал бы в открытый файл)
    edit_yaml(root, "pages/gromov/page.yaml",
              lambda d: d["posts"][1].update(link={"page": "inna", "text": "Фотосеть"}))
    errs = errors_of(root)
    assert has_error(errs, "gromov", "inna", "только на страницы этапа 1") or has_error(errs, "gromov", "inna", "этап 2")


def test_link_to_later_stage_is_error_even_from_closed(fx):
    # из закрытой страницы этапа 2 (inna) — на страницу этапа 4 (auction): игроки ещё не дошли
    new_page(fx, "inna-extra", {"slug": "inna-extra", "type": "social", "stage": 2, "locked": True, "brand": "b",
                                "profile": {"name": "Н"}, "posts": [
                                    {"datetime": "2026-01-01T10:00", "text": "x", "link": {"page": "auction", "text": "t"}}]})
    errs = errors_of(fx)
    assert has_error(errs, "inna-extra", "auction", "этап 4", "этапа 2")


def test_closed_page_may_link_to_earlier_stage_and_to_open(fx):
    edit_yaml(fx, "pages/auction/page.yaml", lambda d: d["sections"][0]["blocks"].append(
        {"kind": "text", "md": "[театр]({{ link('theater') }}) и [облако]({{ link('cloud') }})"}))
    # cloud — этап 4, auction — этап 4: можно; theater — этап 1: можно
    assert link_problem_messages(load_content(fx)) == []


def test_default_stub_and_home_are_required(root):
    shutil.rmtree(root / "pages" / "krug-private")
    errs = errors_of(root)
    assert has_error(errs, "krug-private", "нет в content/pages")


def test_orphan_page_without_doc_is_warning(root):
    new_page(root, "krug-orphan", {"slug": "krug-orphan", "type": "social_stub", "stage": 1, "locked": False,
                                   "brand": "Круг", "text": "Закрыто."})
    c = load_content(root)
    assert any("krug-orphan" in str(w) and "без входящих ссылок" in str(w) for w in c.warnings)


# ---------------------------------------------------------------- QR и соли


def test_qr_only_for_pages_with_doc(fx, tmp_path):
    c = load_content(fx)
    salts = salts_mod.ensure_for_content(c, tmp_path / "s.json")
    slugs = {card.slug for card in plan_cards(c, salts)}
    assert "gromov" in slugs and "inna" in slugs
    assert not slugs & {"krug", "krug-private", "theater", "fund", "auction", "krug-actor", "news-extra"}


def test_new_locked_page_key_is_appended_old_keys_untouched(fx, tmp_path):
    lock = tmp_path / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    before = json.loads(lock.read_text(encoding="utf-8"))
    # auction уже дописан в боевой lock-файл; проверяем сам механизм: убираем ключ и даём сборке дописать его
    before["pages"].pop("auction", None)
    lock.write_text(json.dumps(before, indent=2, sort_keys=True), encoding="utf-8")
    assert "auction" not in json.loads(lock.read_text(encoding="utf-8"))["pages"]
    salts_mod.ensure_for_content(load_content(fx), lock)
    after = json.loads(lock.read_text(encoding="utf-8"))
    assert "auction" in after["pages"] and len(salts_mod.read(lock).page_key("auction")) == 32
    for section in ("units", "stages", "pages"):
        for k, v in before.get(section, {}).items():
            assert after[section][k] == v, (section, k)
    assert after["start"] == before["start"] and after["cloud"] == before["cloud"]


# ---------------------------------------------------------------- сборка и шаблоны типов


@pytest.fixture(scope="module")
def built_fx(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pg")
    c = copy_content(tmp)
    add_fixture_pages(c)
    lock = tmp / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    dist = tmp / "dist"
    build(content_dir=c, dist=dist, salts_path=lock, log=lambda *_: None)
    return tmp, load_content(c), dist, lock


def read(dist: Path, slug: str) -> str:
    return (dist / "p" / slug / "index.html").read_text(encoding="utf-8")


def test_css_and_entry_by_type(built_fx):
    _, c, dist, _ = built_fx
    html = read(dist, "theater")
    assert "/assets/css/pages/site.css" in html and "/assets/css/pages/site-theater.css" in html
    assert "site-fund.css" not in html and "/assets/css/pages/_ui.css" in html
    assert 'data-type="site"' in html and "page--site" in html and "/assets/js/pages/open.js" in html
    krug = read(dist, "krug")
    assert "social_home.css" in krug and "page--social" in krug and "page--social_home" in krug
    assert 'data-type="social"' in read(dist, "gromov")
    assert [Path(h).name for h in page_css(c.pages["video"])] == []  # video — только стиль системы
    for name in ("_ui", "social", "social_home", "social_stub", "site", "site-theater", "site-fund", "site-auction"):
        assert (dist / "assets" / "css" / "pages" / f"{name}.css").is_file(), name


def test_closed_page_is_sealed_and_type_in_payload(built_fx):
    tmp, c, dist, lock = built_fx
    shell = read(dist, "auction")
    assert "Закрытые" not in shell and "Тестовое описание клуба" not in shell
    assert 'data-access="key"' in shell and 'data-type="site"' in shell
    salts = salts_mod.read(lock)
    box = json.loads((dist / "p/auction/payload.json").read_text(encoding="utf-8"))
    inner = json.loads(crypto.open_(salts.page_key("auction"), box, "page/auction"))
    assert inner["type"] == "site" and inner["slug"] == "auction" and "Тестовое описание клуба" in inner["html"]
    assert "Тестовое описание клуба" not in (dist / "p/auction/payload.json").read_text(encoding="utf-8")


def test_links_rendered_with_keys_and_open_pages_stay_open(built_fx):
    tmp, c, dist, lock = built_fx
    salts = salts_mod.read(lock)
    # открытые страницы ссылаются только на открытые (проверка и по выводу)
    fragments = {slug: read(dist, slug) for slug, p in c.pages.items() if p.locked is False}
    assert rendered_link_problems(c, salts, fragments) == []
    assert 'href="/p/theater/"' in read(dist, "news") and 'href="/p/news-extra/"' in read(dist, "news")
    assert 'href="/p/krug-private/"' in read(dist, "gromov") and 'href="/p/krug/"' in read(dist, "gromov")
    # из облака (закрыто паролем) — на auction с ключом во фрагменте, как в QR
    page = c.pages["cloud"]
    key = crypto.cloud_key(cloud_password_norm(page), salts.cloud, c.settings.crypto.iter_stage)
    box = json.loads((dist / "p/cloud/payload.json").read_text(encoding="utf-8"))["box"]
    html = json.loads(crypto.open_(key, box, "page/cloud"))["html"]
    assert f'href="/p/auction/#k={b64u_encode(salts.page_key("auction"))}"' in html
    assert rendered_link_problems(c, salts, {"cloud": html}) == []
    # подмена ключа в ссылке ловится
    bad = html.replace("#k=", "#k=X", 1)
    assert rendered_link_problems(c, salts, {"cloud": bad})


def test_rendered_link_check_catches_open_to_closed(built_fx):
    tmp, c, dist, lock = built_fx
    salts = salts_mod.read(lock)
    key = b64u_encode(salts.page_key("auction"))
    probs = rendered_link_problems(c, salts, {"theater": f'<a href="/p/auction/#k={key}">x</a>'})
    assert any("этапа 4" in p for p in probs)


def test_every_visible_control_is_wired(built_fx):
    """На страницах нет неактивных кнопок: каждая кнопка — окно, переключатель, фото или действие страницы."""
    tmp, c, dist, lock = built_fx
    salts = salts_mod.read(lock)
    pages_html = {slug: read(dist, slug) for slug, p in c.pages.items() if p.locked is False}
    # закрытые — расшифрованные фрагменты
    for slug, p in c.pages.items():
        if p.locked is True:
            box = json.loads((dist / "p" / slug / "payload.json").read_text(encoding="utf-8"))
            pages_html[slug] = json.loads(crypto.open_(salts.page_key(slug), box, f"page/{slug}"))["html"]
    wired = re.compile(r'data-(dialog-text|zoom|toggle|print|top|role|act|index|folder-link|section-link)|role="tab"|type="submit"|'
                       r'class="[^"]*(kd-tile__btn|tc-sort|kd-iconbtn)')
    for slug, html in pages_html.items():
        if slug in ("cloud", "video", "call"):
            continue  # у этих плеер/сортировка/загрузка — их собственные data-act; проверяются e2e
        for m in re.finditer(r"<button\b[^>]*>", html):
            tag = m.group(0)
            assert "disabled" not in tag, (slug, tag)
            assert wired.search(tag), (slug, tag)
        for m in re.finditer(r'<a\b[^>]*>', html):
            assert "href=" in m.group(0), (slug, m.group(0))


def test_service_footer_texts_come_from_content(built_fx):
    _, c, dist, _ = built_fx
    assert set(c.services) >= {"social", "photo", "news", "pharma", "cloud"}
    html = read(dist, "gromov")
    assert "О сервисе" in html and "Правила" in html and "Помощь" in html
    assert c.services["social"].about.split("\n")[0].replace("{{ w.brands.social }}", "Круг")[:20] in html.replace("&#34;", '"')


def test_sidebar_and_article_flags(built_fx):
    _, _, dist, _ = built_fx
    news, extra = read(dist, "news"), read(dist, "news-extra")
    assert "Срочно" in news and "Срочно" not in extra and "Город" in extra


def test_no_open_answer_leak_in_fixture_build(built_fx):
    """Закрытый текст фикстуры не лежит открытым в dist."""
    _, _, dist, _ = built_fx
    for p in dist.rglob("*"):
        if p.is_file() and p.suffix in (".html", ".json") and p.parent.name != "auction":
            assert "Тестовое описание клуба" not in p.read_text(encoding="utf-8", errors="replace"), p
