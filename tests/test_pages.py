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
from engine.media import src_file  # noqa: E402
from engine.content import ContentError, load_content  # noqa: E402
from engine.models import CallPage, NewsPage, SitePage, SocialPage, SocialStubPage  # noqa: E402
from engine.pages import check_links, open_password_payload, page_css, rendered_link_problems  # noqa: E402
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
        ["call", "photo", "news", "pharma", "cloud", "video"]  # inna без type — фотосеть «Кадр» (type photo)
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
    edit_yaml(root, "documents.yaml",
              lambda d: next(x for x in d["documents"] if x["id"] == "1-02").update(page="krug-private"))
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
    salts = salts_mod.load_or_init(tmp_path / "s.json", units=[], stages=[], pages=["inna", "pharma", "video", "cloud"])
    link = make_link(c.pages, salts)
    assert link("gromov") == "/p/gromov/"
    key = b64u_encode(salts.page_key("inna"))
    assert link("inna") == f"/p/inna/#k={key}"
    # тот же адрес, что в QR (с доменом)
    assert qr_url("https://x.ru", "inna", key) == "https://x.ru" + link("inna")
    # облако: два замка (locked: true) — ключ в адресе, как в QR записки; один замок (password) — без ключа
    if c.pages["cloud"].locked is True:
        assert link("cloud") == f"/p/cloud/#k={b64u_encode(salts.page_key('cloud'))}"
    else:
        assert link("cloud") == "/p/cloud/"
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
    box = json.loads((dist / "p/cloud/payload.json").read_text(encoding="utf-8"))
    html = open_password_payload(page, box, salts.page_key("cloud") if page.locked is True else None)[0]["html"]
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


# Подписи кнопок аккаунта и окон-заглушек: на вымышленных страницах их быть не должно (REDESIGN §4.1).
DEAD_END_LABELS = ("Подписаться", "Написать", "Нравится", "Поделиться", "Войти", "Отметить", "Печать", "Ввести пароль",
                   "Добавить в друзья", "Понятно")


def test_every_visible_control_is_wired(built_fx):
    """Кликабельно только то, что ведёт к содержимому: нет кнопок без действия, нет окон-заглушек."""
    tmp, c, dist, lock = built_fx
    salts = salts_mod.read(lock)
    pages_html = {slug: read(dist, slug) for slug, p in c.pages.items() if p.locked is False}
    # закрытые — расшифрованные фрагменты
    for slug, p in c.pages.items():
        if p.locked is True:
            box = json.loads((dist / "p" / slug / "payload.json").read_text(encoding="utf-8"))
            pages_html[slug] = json.loads(crypto.open_(salts.page_key(slug), box, f"page/{slug}"))["html"]
    wired = re.compile(r'data-(zoom|toggle|role|act|index|folder-link|section-link)|role="tab"|type="submit"|'
                       r'class="[^"]*(kd-tile__btn|tc-sort|kd-iconbtn)')
    for slug, html in pages_html.items():
        # окон-заглушек нет: ни диалогов сервиса, ни кнопок, открывающих их
        assert "data-dialog-text" not in html and "svc-dialog" not in html, slug
        if slug in ("cloud", "video", "call"):
            continue  # у этих плеер/сортировка/загрузка — их собственные data-act; проверяются e2e
        for m in re.finditer(r"<button\b[^>]*>(.*?)</button>", html, re.S):
            tag = html[m.start():html.index(">", m.start()) + 1]
            label = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            assert "disabled" not in tag, (slug, tag)
            assert wired.search(tag), (slug, tag)
            assert not any(label.startswith(x) for x in DEAD_END_LABELS), (slug, label)
        for m in re.finditer(r'<a\b[^>]*>', html):
            assert "href=" in m.group(0), (slug, m.group(0))
    # облако: у замка папки нет кнопки «Ввести пароль»
    if "cloud" in pages_html:
        assert "Ввести пароль" not in pages_html["cloud"] and "tc-locked__btn" not in pages_html["cloud"]


def test_service_footer_texts_come_from_content(built_fx):
    """Подвал — раскрывающийся <details> с текстами из _brands.yaml, без окон."""
    _, c, dist, _ = built_fx
    assert set(c.services) >= {"social", "photo", "news", "pharma", "cloud"}
    html = read(dist, "gromov")
    assert "<details" in html and "Сведения о сервисе" in html and "Правила." in html and "Помощь." in html
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


# ---------------------------------------------------------------- голосовые в «Круге» и «Внешний вид» в pharma

FAKE_MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + bytes(range(64)) * 4
FAKE_MP4 = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 8
FAKE_JPG = b"\xff\xd8\xff\xe0" + bytes(range(100)) * 3


@pytest.fixture(scope="module")
def built_voice(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("voice")
    c = copy_content(tmp)
    add_fixture_pages(c)
    edit_yaml(c, "pages/pharma/page.yaml", lambda d: d["drugs"][0].update(appearance="Белые круглые таблетки, ТЕСТ-ВИД"))
    media = tmp / "media"
    for rel in ("krug-actor/voice-01.mp3", "krug-closed/voice-01.mp3",  # voice-missing.mp3 нарочно нет
                "krug-actor/comment-voice-01.mp3", "krug-closed/comment-voice-01.mp3"):
        (media / rel).parent.mkdir(parents=True, exist_ok=True)
        (media / rel).write_bytes(FAKE_MP3 + rel.encode())  # у закрытых и открытых файлов содержимое разное
    for page in ("krug-actor", "krug-closed"):  # video-missing.mp4 и comment-voice-missing.mp3 нарочно нет
        (media / page / "video-01.mp4").write_bytes(FAKE_MP4 + page.encode())
        (media / page / "video-01.jpg").write_bytes(FAKE_JPG + page.encode())
    lock = tmp / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    dist = tmp / "dist"
    rep = build(content_dir=c, dist=dist, media_dir=media, salts_path=lock, log=lambda *_: None)
    return tmp, dist, lock, rep


def sealed_inner(built, slug: str) -> dict:
    _, dist, lock, _ = built
    box = json.loads((dist / "p" / slug / "payload.json").read_text(encoding="utf-8"))
    return json.loads(crypto.open_(salts_mod.read(lock).page_key(slug), box, f"page/{slug}"))


def test_post_audio_model():
    from engine.models import PostAudio, SocialPost

    p = SocialPost(datetime="2026-10-01T10:00", audio={"file": "x/v.mp3", "duration": "0:12"})  # без text — можно
    assert p.text == "" and p.audio.transcript is None
    assert PostAudio(file="x/v.m4a", duration="12:05", transcript="…").transcript == "…"
    for bad in ({"file": "x/v.jpg", "duration": "0:12"}, {"file": "x/v.mp3", "duration": "12 сек"},
                {"file": "x/v.mp3", "duration": "0:75"}, {"file": "x/v.mp3", "duration": "0:12", "lang": "ru"}):
        with pytest.raises(ValidationError):
            PostAudio(**bad)
    with pytest.raises(ValidationError, match="text, photo, audio или video"):
        SocialPost(datetime="2026-10-01T10:00")


def test_drug_appearance_is_optional():
    from engine.models import Drug

    base = dict(name="Х", trade=["Т"], group="г", indications="и", contraindications="к", side_effects="п")
    assert Drug(**base).appearance is None
    assert Drug(**base, appearance="Белые таблетки").appearance == "Белые таблетки"


def test_voice_media_refs_and_bad_extension(root):
    from engine.content import media_refs

    add_fixture_pages(root)
    c = load_content(root)
    uses = [u for u in media_refs(c.characters, c.pages, c.docs) if u.path.startswith(("krug-actor/", "krug-closed/"))]
    assert {(u.path, u.context) for u in uses} == {
        ("krug-actor/voice-01.mp3", "open"), ("krug-actor/voice-missing.mp3", "open"),
        ("krug-actor/comment-voice-01.mp3", "open"), ("krug-actor/comment-voice-missing.mp3", "open"),
        ("krug-actor/video-01.mp4", "open"), ("krug-actor/video-01.jpg", "open"),
        ("krug-actor/video-missing.mp4", "open"),
        ("krug-closed/voice-01.mp3", "locked"), ("krug-closed/comment-voice-01.mp3", "locked"),
        ("krug-closed/video-01.mp4", "locked"), ("krug-closed/video-01.jpg", "locked")}
    by_path = {u.path: u.loc for u in uses}
    assert re.fullmatch(r"posts\[\d+\]\.audio\.file", by_path["krug-actor/voice-01.mp3"])
    assert re.fullmatch(r"posts\[\d+\]\.comments\[\d+\]\.audio\.file", by_path["krug-actor/comment-voice-01.mp3"])
    assert re.fullmatch(r"posts\[\d+\]\.video\.file", by_path["krug-actor/video-01.mp4"])
    assert re.fullmatch(r"posts\[\d+\]\.video\.poster", by_path["krug-actor/video-01.jpg"])
    edit_yaml(root, "pages/krug-actor/page.yaml", lambda d: d["posts"][1]["audio"].update(file="../v.mp3"))
    assert has_error(errors_of(root), "krug-actor", "относительным")


def test_missing_voice_file_warns_and_renders_inactive_player(built_voice):
    _, dist, _, rep = built_voice
    assert "krug-actor/voice-missing.mp3" in rep.missing_media
    assert "krug-actor/voice-01.mp3" not in rep.missing_media
    html = read(dist, "krug-actor")
    posts = re.findall(r'<article class="kr-post.*?</article>', html, re.S)
    blocks = [b for b in (re.search(r'<div class="kr-voice".*', p, re.S) for p in posts) if b]
    assert len(blocks) == 2
    missing, present = blocks[0].group(0), blocks[1].group(0)  # лента: новые сверху
    assert 'data-missing="1"' not in present and re.search(r'<audio[^>]+src="/m/[0-9a-f]{32}\.mp3"', present)
    assert 'data-missing="1"' in missing and "<audio" not in missing and "src=" not in missing
    assert "Голосовое сообщение" in missing and "0:12" in missing
    assert 'data-act="play"' in missing  # кнопку отключает audio-player.js (без файла неактивна; e2e)
    assert "<details" not in missing  # расшифровки нет — блока нет
    assert "audio controls" not in html and "<audio controls" not in html


def test_voice_transcript_is_details_and_audio_only_post_has_no_text(built_voice):
    _, dist, _, _ = built_voice
    html = read(dist, "krug-actor")
    assert '<summary class="kr-voice__tr-summary">Расшифровка</summary>' in html
    assert "Тестовая расшифровка голосового сообщения." in html
    post = re.search(r'<article class="kr-post[^"]*" data-datetime="2026-10-02T09:15">.*?</article>', html, re.S).group(0)
    assert "kr-post__text" not in post and "kr-voice" in post
    other = re.search(r'<article class="kr-post[^"]*" data-datetime="2026-10-03T09:15">.*?</article>', html, re.S).group(0)
    assert "kr-post__text" in other and "kr-voice" in other


def test_voice_on_locked_page_is_encrypted(built_voice):
    _, dist, _, _ = built_voice
    inner = sealed_inner(built_voice, "krug-closed")
    assert 'class="kr-voice"' in inner["html"] and "Расшифровка закрытого голосового." in inner["html"]
    assert "data-media=" in inner["html"] and "src=" not in re.search(r"<audio[^>]*>", inner["html"]).group(0)
    refs = [r for r in inner["media"] if r["mime"] == "audio/mpeg"]
    assert len(refs) == 2  # голосовое поста и голосовое комментария
    for ref in refs:
        assert ref["key"] and src_file(ref["src"]).endswith(".bin") and ref["aad"].startswith("media/")
        name = src_file(ref["src"]).rsplit("/", 1)[1]
        assert (dist / "m" / name).is_file()
        raw = (dist / "m" / name).read_bytes()
        assert FAKE_MP3 not in raw and not raw.startswith(b"ID3")
        opened = crypto.open_media(crypto.b64u_decode(ref["key"]), raw, ref["aad"])
        assert opened.startswith(FAKE_MP3 + b"krug-closed/")
    shell = (dist / "p" / "krug-closed" / "payload.json").read_text(encoding="utf-8")
    assert "Расшифровка закрытого" not in shell and "ID3" not in shell


# ---------------------------------------------------------------- голосовое у комментария и видео в посте


def test_comment_model_text_or_audio():
    from engine.models import PostComment

    c = PostComment(author="А", audio={"file": "x/c.mp3", "duration": "0:07"})  # без text — можно
    assert c.text == "" and c.audio.duration == "0:07" and c.page is None
    assert PostComment(author="А", text="Привет").audio is None
    assert PostComment(author="А", text="Привет", audio={"file": "x/c.m4a", "duration": "1:07", "transcript": "…"}).audio.transcript
    with pytest.raises(ValidationError, match="text или audio"):
        PostComment(author="А")
    with pytest.raises(ValidationError, match="text или audio"):
        PostComment(author="А", text="  ")
    with pytest.raises(ValidationError):  # те же правила, что у голосового поста
        PostComment(author="А", audio={"file": "x/c.wav", "duration": "0:07"})
    with pytest.raises(ValidationError):
        PostComment(author="А", audio={"file": "x/c.mp3", "duration": "7 сек"})


def test_post_video_model():
    from engine.models import PostVideo, SocialPost

    v = PostVideo(file="p/video-01.mp4", poster="p/video-01.jpg", duration="0:15")
    p = SocialPost(datetime="2026-10-01T10:00", video=v.model_dump())  # пост только с видео — можно
    assert p.text == "" and p.video.poster == "p/video-01.jpg"
    assert PostVideo(file="p/v.MP4", poster="p/v.webp", duration="12:05").duration == "12:05"
    for bad in (dict(file="p/v.mov", poster="p/v.jpg", duration="0:15"),
                dict(file="p/v.webm", poster="p/v.jpg", duration="0:15"),
                dict(file="p/v.mp4", poster="p/v.mp3", duration="0:15"),
                dict(file="p/v.mp4", poster="p/v.jpg", duration="15 сек"),
                dict(file="p/v.mp4", poster="p/v.jpg", duration="0:75"),
                dict(file="p/v.mp4", duration="0:15"),  # постер обязателен
                dict(file="p/v.mp4", poster="p/v.jpg", duration="0:15", autoplay=True)):
        with pytest.raises(ValidationError):
            PostVideo(**bad)


def test_comment_audio_and_video_bad_paths_are_content_errors(root):
    add_fixture_pages(root)
    edit_yaml(root, "pages/krug-actor/page.yaml",
              lambda d: d["posts"][3]["comments"][0]["audio"].update(file="../c.mp3"))
    assert has_error(errors_of(root), "krug-actor", "comments[0].audio.file", "относительным")


def test_video_poster_bad_extension_is_error(root):
    add_fixture_pages(root)
    edit_yaml(root, "pages/krug-actor/page.yaml", lambda d: d["posts"][3]["video"].update(poster="krug-actor/p.gif"))
    assert errors_of(root)


def test_open_page_video_and_comment_voice_markup(built_voice):
    _, dist, _, rep = built_voice
    html = read(dist, "krug-actor")
    post = re.search(r'<article class="kr-post[^"]*" data-datetime="2026-10-04T12:00">.*?</article>', html, re.S).group(0)
    # Видео: плеер браузера, без автозапуска, постер, длительность на постере.
    video = re.search(r"<video[^>]*>", post).group(0)
    for needle in ('playsinline', 'preload="none"', "controls", 'poster="/m/'):
        assert needle in video, needle
    assert re.search(r'src="/m/[0-9a-f]{32}\.mp4"', video)
    assert "autoplay" not in html
    assert '<span class="kr-video__dur" aria-hidden="true">0:02</span>' in post
    assert "kr-post__text" not in post  # пост только с видео
    # Голосовые в комментариях: компактный вариант того же плеера.
    comments = re.search(r'<ul class="kr-comments".*?</ul>', post, re.S).group(0)
    voices = re.findall(r'<div class="kr-voice kr-voice--compact"[^>]*>', comments)
    assert len(voices) == 2
    assert 'data-missing="1"' not in voices[0] and 'data-missing="1"' in voices[1]
    assert "Комментарий с текстом и голосовым." in comments
    assert "Расшифровка голосового комментария." in comments
    assert re.search(r'<audio[^>]+src="/m/[0-9a-f]{32}\.mp3"', comments)
    # Комментарий без текста: подписи text нет.
    second = comments.split('<li class="kr-comment">')[2]
    assert "kr-comment__text" not in second and "kr-voice" in second
    assert "krug-actor/video-missing.mp4" in rep.missing_media and "krug-actor/comment-voice-missing.mp3" in rep.missing_media
    assert "krug-actor/video-01.mp4" not in rep.missing_media


def test_missing_video_file_renders_unavailable_stub(built_voice):
    _, dist, _, rep = built_voice
    html = read(dist, "krug-actor")
    post = re.search(r'<article class="kr-post[^"]*" data-datetime="2026-10-06T12:00">.*?</article>', html, re.S).group(0)
    box = re.search(r'<div class="kr-video is-missing".*?</div>', post, re.S).group(0)
    assert "Видео недоступно" in box and "0:15" in box
    assert "<video" not in post and "video-missing" not in post  # ни <video>, ни ссылки на файл
    assert "<button" not in box and "src=\"/m/" in box  # кнопки нет; постер (он существует) остаётся
    assert any("video-missing.mp4" in w for w in rep.warnings)  # предупреждение сборки
    assert not any("krug-actor/video-01.mp4" in w for w in rep.warnings), rep.warnings


def test_video_without_poster_file_has_stub_without_image(tmp_path):
    c = copy_content(tmp_path)
    add_fixture_pages(c)
    media = tmp_path / "media"
    media.mkdir()  # вообще никаких файлов
    lock = tmp_path / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    dist = tmp_path / "dist"
    rep = build(content_dir=c, dist=dist, media_dir=media, salts_path=lock, log=lambda *_: None)
    html = read(dist, "krug-actor")
    post = re.search(r'<article class="kr-post[^"]*" data-datetime="2026-10-04T12:00">.*?</article>', html, re.S).group(0)
    box = re.search(r'<div class="kr-video is-missing".*?</div>', post, re.S).group(0)
    assert "<video" not in post and "Видео недоступно" in box and "<img" not in box
    assert "krug-actor/video-01.mp4" in rep.missing_media and "krug-actor/video-01.jpg" in rep.missing_media


def test_closed_page_video_and_poster_are_encrypted(built_voice):
    _, dist, _, _ = built_voice
    inner = sealed_inner(built_voice, "krug-closed")
    html = inner["html"]
    video = re.search(r"<video[^>]*>", html).group(0)
    assert "src=" not in video and "poster=" not in video  # ни файла, ни постера в открытом виде
    vi = int(re.search(r'data-video-media="(\d+)"', video).group(1))
    pi = int(re.search(r'data-poster-media="(\d+)"', video).group(1))
    assert " data-media=" not in video  # hydrateMedia не должен качать видео сам
    vref, pref = inner["media"][vi], inner["media"][pi]
    assert vref["mime"] == "video/mp4" and pref["mime"] == "image/jpeg"
    for ref, plain in ((vref, FAKE_MP4 + b"krug-closed"), (pref, FAKE_JPG + b"krug-closed")):
        assert ref["key"] and src_file(ref["src"]).endswith(".bin")
        raw = (dist / "m" / src_file(ref["src"]).rsplit("/", 1)[1]).read_bytes()
        assert plain not in raw and not raw.startswith(b"\x00\x00\x00\x18ftyp")
        assert crypto.open_media(crypto.b64u_decode(ref["key"]), raw, ref["aad"]) == plain
        assert ref["size"] == len(raw)  # по size играет индикатор загрузки
    assert not any(p.read_bytes().endswith(b"krug-closed") for p in (dist / "m").iterdir())  # открытых копий нет
    assert 'class="kr-voice kr-voice--compact"' in html  # голосовое комментария тоже внутри шифрованной части


def test_identical_media_under_two_paths_shares_one_file(tmp_path):
    """Одинаковое содержимое под двумя путями (открытая и закрытая страница) — один файл в dist/m/: открытый;
    два закрытых пути — один файл с одним ключом (раньше второй затирал первый вместе с его ключом)."""
    from engine.content import MediaUse
    from engine.media import MediaPlan

    media = tmp_path / "media"
    (media / "a").mkdir(parents=True)
    for rel in ("a/1.mp3", "a/2.mp3", "a/3.mp3"):
        (media / rel).write_bytes(FAKE_MP3)
    c = type("C", (), {"characters": [], "pages": {}, "docs": {}})()
    import engine.media as media_mod

    uses = {"a/1.mp3": "locked", "a/2.mp3": "locked", "a/3.mp3": "open"}
    orig = media_mod.media_refs
    media_mod.media_refs = lambda *_a, **_k: [MediaUse("f", "loc", p, ctx) for p, ctx in uses.items()]
    try:
        plan = MediaPlan(c, media)
        assert all(not f.encrypted for f in plan.files.values())  # третий путь открыт — файл уже публичен
        uses["a/3.mp3"] = "locked"
        plan = MediaPlan(c, media)
    finally:
        media_mod.media_refs = orig
    assert len({f.key for f in plan.files.values()}) == 1 and all(f.encrypted for f in plan.files.values())
    out = plan.emit(tmp_path / "dist")
    assert len(out) == 1
    f = plan.files["a/1.mp3"]
    assert crypto.open_media(f.key, out[0].read_bytes(), f"media/{f.hash}") == FAKE_MP3


def test_sealed_video_over_limit_is_build_error(tmp_path, monkeypatch):
    import engine.media as media_mod

    c = copy_content(tmp_path)
    add_fixture_pages(c)
    media = tmp_path / "media"
    (media / "krug-closed").mkdir(parents=True)
    (media / "krug-actor").mkdir(parents=True)
    (media / "krug-closed" / "video-01.mp4").write_bytes(FAKE_MP4)
    (media / "krug-actor" / "video-01.mp4").write_bytes(FAKE_MP4 + b"open")
    lock = tmp_path / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    from engine.build import BuildError

    monkeypatch.setattr(media_mod, "MAX_SEALED_VIDEO_BYTES", len(FAKE_MP4) - 1)
    monkeypatch.setattr(media_mod, "WARN_VIDEO_BYTES", len(FAKE_MP4) - 1)
    with pytest.raises(BuildError) as e:
        build(content_dir=c, dist=tmp_path / "dist", media_dir=media, salts_path=lock, log=lambda *_: None)
    msgs = "\n".join(e.value.problems)
    assert "krug-closed/video-01.mp4" in msgs and "закрытых страницах" in msgs
    assert "krug-actor/video-01.mp4" not in msgs  # открытая страница — не ошибка, только предупреждение
    # Тот же файл на открытой странице: сборка проходит, предупреждение о весе.
    (media / "krug-closed" / "video-01.mp4").unlink()
    rep = build(content_dir=c, dist=tmp_path / "dist", media_dir=media, salts_path=lock, log=lambda *_: None)
    assert any("krug-actor/video-01.mp4" in w and "лучше до" in w for w in rep.warnings)


def test_pharma_appearance_row_after_active_substance(built_voice):
    inner = sealed_inner(built_voice, "pharma")
    html = inner["html"]
    cards = [c for c in html.split("<article") if "ТЕСТ-ВИД" in c]
    assert len(cards) == 1 and cards[0].count("Внешний вид") == 1
    card = cards[0]
    assert card.index("Действующее вещество") < card.index("Внешний вид") < card.index("Фармакологическая группа")
    assert "Белые круглые таблетки, ТЕСТ-ВИД" in html


# ---------------------------------------------------------------- достижимость через тексты результатов и этапов


def orphan_page(root: Path, slug: str, stage: int) -> None:
    new_page(root, slug, {"slug": slug, "type": "site", "stage": stage, "locked": stage > 1, "brand": "Тестовый", "skin": "fund",
                          "sections": [{"id": "a", "title": "A", "blocks": [{"kind": "text", "md": "Текст."}]}]})


def unreachable_warnings(c) -> list[str]:
    return [str(w) for w in c.warnings if "без входящих ссылок" in str(w)]


def test_page_without_doc_is_unreachable_without_links(root):
    orphan_page(root, "orphan", 1)
    assert any("orphan" in w for w in unreachable_warnings(load_content(root)))


def test_link_from_expertise_result_text_makes_page_reachable(root):
    # результат 3-05 (этап 3): открытая страница этапа 1 достижима по ссылке из его текста
    orphan_page(root, "orphan", 1)
    p = root / "documents" / "3-05.md"
    p.write_text(p.read_text(encoding="utf-8") + "\n\nСм. [тут]({{ link('orphan') }}).\n", encoding="utf-8")
    assert not any("orphan" in w for w in unreachable_warnings(load_content(root)))


def test_link_from_stage_text_makes_page_reachable(root):
    orphan_page(root, "orphan", 1)
    edit_yaml(root, "stages.yaml", lambda d: d["stages"][1].update(
        on_complete=d["stages"][1]["on_complete"] + " [тут]({{ link('orphan') }})"))
    assert not any("orphan" in w for w in unreachable_warnings(load_content(root)))


def test_link_from_result_text_to_later_stage_is_error(root):
    # страница этапа 4 из результата этапа 3: игроки ещё не дошли
    orphan_page(root, "orphan", 4)
    p = root / "documents" / "3-05.md"
    p.write_text(p.read_text(encoding="utf-8") + "\n\nСм. [тут]({{ link('orphan') }}).\n", encoding="utf-8")
    errs = errors_of(root)
    assert has_error(errs, "3-05.md", "orphan", "этап 4", "этапа 3")


def test_link_from_result_text_to_unknown_page_is_error(root):
    p = root / "documents" / "3-05.md"
    p.write_text(p.read_text(encoding="utf-8") + "\n\nСм. [тут]({{ link('net-takoy') }}).\n", encoding="utf-8")
    assert has_error(errors_of(root), "3-05.md", "net-takoy")
