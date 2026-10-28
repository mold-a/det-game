"""Профили закрытых этапов (docs/02 §3.10, docs/04 «Профили закрытых этапов») и фотосеть «Кадр» (type photo,
photo_stub). Страницы-фикстуры — tests/fixtures/pages (krug-later, krug-opener, kadr-*), в КОПИИ content/."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pages_fixture import PHOTO_MAIN, add_fixture_pages, add_gate_fixtures, copy_content  # noqa: E402

from engine import ROOT, crypto  # noqa: E402
from engine import salts as salts_mod  # noqa: E402
from engine.build import build  # noqa: E402
from engine.check import page_segments  # noqa: E402
from engine.content import ContentError, load_content  # noqa: E402
from engine.models import PhotoPage  # noqa: E402
from engine.pages import check_links, page_key_leaks, rendered_link_problems  # noqa: E402
from engine.util import b64u_encode  # noqa: E402


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("gate")
    c = copy_content(tmp)
    add_fixture_pages(c)
    add_gate_fixtures(c)
    lock = tmp / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    dist = tmp / "dist"
    build(content_dir=c, dist=dist, salts_path=lock, log=lambda *_: None)
    content = load_content(c)
    salts = salts_mod.read(lock)
    return content, dist, salts, c


def read(dist: Path, slug: str) -> str:
    return (dist / "p" / slug / "index.html").read_text(encoding="utf-8")


def key_of(salts, slug: str) -> str:
    return b64u_encode(salts.page_key(slug))


def sealed_html(dist: Path, salts, slug: str) -> str:
    box = json.loads((dist / "p" / slug / "payload.json").read_text(encoding="utf-8"))
    return json.loads(crypto.open_(salts.page_key(slug), box, f"page/{slug}"))["html"]


def stage_key(c: Path, lock: Path, n: int) -> bytes:
    from engine.build import prepare

    return prepare(c, lock, create_salts=False, lab_checks=False).keys[n]


def open_pack(dist: Path, key: bytes, n: int) -> dict:
    box = json.loads((dist / "data" / f"pack-{n}.json").read_text(encoding="utf-8"))
    return json.loads(crypto.open_(crypto.hkdf(key, crypto.pack_info(n)), box, f"pack/{n}"))


# ---------------------------------------------------------------- модели


def test_photo_profile_any_slug_allowed(built):
    content, *_ = built
    assert "inna" not in content.pages  # 28.10: «Кадр» в сюжете не используется, тип photo — в движке
    assert isinstance(content.pages[PHOTO_MAIN], PhotoPage) and content.pages[PHOTO_MAIN].type == "photo"
    assert content.pages["kadr-friend"].type == "photo" and content.pages["kadr-late-stub"].type == "photo_stub"
    assert content.pages["kadr-late"].stub == "kadr-late-stub"


# ---------------------------------------------------------------- пакет этапа: ключи и строки поиска


def test_stage_pack_holds_keys_of_its_gated_profiles(built):
    content, dist, salts, c = built
    lock = c.parent / "salts.lock.json"
    pack2 = open_pack(dist, stage_key(c, lock, 2), 2)
    pack3 = open_pack(dist, stage_key(c, lock, 3), 3)
    by2 = {e["slug"]: e for e in pack2["pages"]}
    assert {"krug-later", "kadr-friend"} <= set(by2) and "kadr-late" not in by2
    assert "kadr-late-stub" not in by2  # заглушка — не профиль закрытого этапа
    later = by2["krug-later"]
    assert later == {"slug": "krug-later", "type": "social", "key": key_of(salts, "krug-later"),
                     "name": "Поздний Тестовый", "position": "тестовая должность позднего профиля"}
    assert {e["slug"] for e in pack3["pages"]} >= {"kadr-late"}
    # ключ из пакета открывает страницу
    assert "Секретная фраза" in sealed_html(dist, salts, "krug-later")
    pack1 = open_pack(dist, stage_key(c, lock, 1), 1)
    assert all(e["slug"] not in ("krug-later", "kadr-late") for e in pack1["pages"])


# ---------------------------------------------------------------- открытые страницы: заглушка, без ключей


def test_open_page_links_to_stub_with_slug_not_key(built):
    content, dist, salts, _ = built
    html = read(dist, "krug-opener")
    links = re.findall(r'<a [^>]*href="(/p/krug-private/#to=krug-later)"[^>]*data-gate="krug-later"', html)
    assert len(links) >= 3  # друг, автор комментария, Markdown-ссылка в посте
    assert "/p/krug-later/" not in html and key_of(salts, "krug-later") not in html
    assert "Секретная фраза" not in html and "тестовая должность позднего" not in html


def test_open_search_index_lists_visible_gated_name_without_position(built):
    _, dist, salts, _ = built
    html = read(dist, "krug")
    li = re.search(r'<li class="kr-person" data-name="Поздний Тестовый" data-slug="krug-later" hidden>.*?</li>', html, re.S)
    assert li, "профиль закрытого этапа, на который ведёт ссылка с открытой страницы, есть в поиске"
    assert 'href="/p/krug-private/#to=krug-later"' in li.group(0) and "Профиль закрыт" in li.group(0)
    assert "тестовая должность позднего" not in html and key_of(salts, "krug-later") not in html


def test_no_gated_key_in_any_open_file_and_rendered_links_ok(built):
    content, dist, salts, _ = built
    files = {p.relative_to(dist).as_posix(): p.read_text(encoding="utf-8", errors="replace")
             for p in dist.rglob("*") if p.is_file() and p.suffix in (".html", ".js", ".json", ".css")}
    assert page_key_leaks(content, salts, files) == []
    fragments = {slug: read(dist, slug) for slug, p in content.pages.items() if p.locked is False}
    fragments[PHOTO_MAIN] = sealed_html(dist, salts, PHOTO_MAIN)
    assert rendered_link_problems(content, salts, fragments) == []


def test_key_leak_and_direct_link_from_open_page_are_caught(built):
    content, dist, salts, _ = built
    key = key_of(salts, "krug-later")
    assert page_key_leaks(content, salts, {"p/krug-opener/index.html": f'<a href="/p/krug-later/#k={key}">'})
    probs = rendered_link_problems(content, salts, {"krug-opener": f'<a href="/p/krug-later/#k={key}">x</a>'})
    assert any("этапа 2" in p for p in probs)
    # заглушка не своя / заглушка там, где она не нужна
    assert rendered_link_problems(content, salts, {"krug-opener": '<a href="/p/krug/#to=krug-later">x</a>'})
    main_html = '<a href="/p/krug-private/#to=kadr-friend">x</a>'
    assert rendered_link_problems(content, salts, {PHOTO_MAIN: main_html})


# ---------------------------------------------------------------- закрытая страница этапа 2: «Кадр»


def test_photo_main_follows_comments_and_gated_photo_link(built):
    content, dist, salts, _ = built
    html = sealed_html(dist, salts, PHOTO_MAIN)
    # тот же этап — прямая ссылка с ключом, как в QR
    assert f'href="/p/kadr-friend/#k={key_of(salts, "kadr-friend")}"' in html
    # этап 3 — через закрытую заглушку «Кадра» (её ключ + to=), ключа kadr-late нет
    stub = f'href="/p/kadr-late-stub/#k={key_of(salts, "kadr-late-stub")}&amp;to=kadr-late" data-gate="kadr-late"'
    assert stub in html and key_of(salts, "kadr-late") not in html
    assert 'class="kd-follow"' in html and "Подписки <b>3</b>" in html and "Подписка Без Страницы" in html
    assert re.search(r"<b class=\"kd-num\">120</b> подписчиков", html)
    assert "Тестовый комментарий к снимку" in html and 'class="kd-comment__author" href="/p/kadr-friend/#k=' in html


def test_photo_profile_and_stub_markup(built):
    _, dist, salts, _ = built
    friend = sealed_html(dist, salts, "kadr-friend")
    assert "Фото Подруга" in friend and "Тестовая подпись профиля" in friend
    assert '<b class="kd-num">21</b> подписчик' in friend and '<b class="kd-num">2</b> подписки' in friend
    assert 'Тестовый снимок со ссылкой на <a href="/p/kadr-late-stub/#k=' in friend  # Markdown в подписи
    assert '<b class="kd-comment__author">Гость Без Страницы</b>' in friend
    stub = sealed_html(dist, salts, "kadr-late-stub")
    assert "Это закрытый аккаунт" in stub and "Снимки видят только подписчики." in stub
    assert '<b class="kd-num">48</b> снимков' in stub and '<b class="kd-num">112</b> подписчиков' in stub
    assert '<b class="kd-num">87</b> подписок' in stub and "kd-grid" not in stub
    assert "·" not in stub and "·" not in friend  # решение автора 24.10: без средних точек
    shell = read(dist, "kadr-late-stub")
    assert "page--photo" in shell and "/assets/css/pages/photo.css" in shell and 'data-type="photo_stub"' in shell


# ---------------------------------------------------------------- правила ссылок


def _edit(c: Path, slug: str, fn) -> None:
    p = c / "pages" / slug / "page.yaml"
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    fn(d)
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _errors(c: Path) -> list[str]:
    with pytest.raises(ContentError) as exc:
        load_content(c)
    return [str(e) for e in exc.value.errors]


@pytest.fixture
def gx(tmp_path: Path) -> Path:
    c = copy_content(tmp_path)
    add_fixture_pages(c)
    add_gate_fixtures(c)
    return c


def test_fixture_gate_links_are_valid(gx):
    c = load_content(gx)
    rep = check_links(c.pages, c.documents, c.texts, c.characters, c.world, c.services)
    assert rep.errors == []


def test_gated_photo_without_stub_is_error(gx):
    _edit(gx, "kadr-late", lambda d: d.pop("stub"))
    assert any("kadr-late" in e and "stub" in e for e in _errors(gx))


def test_gated_profile_must_be_locked(gx):
    _edit(gx, "krug-later", lambda d: d.update(locked=False))
    assert any("krug-later" in e and "locked: true" in e for e in _errors(gx))


def test_non_profile_late_page_is_still_an_error_from_open_page(gx):
    # auction (site, этап 4) — не профиль: ссылка с открытой страницы по-прежнему ошибка, заглушки нет
    _edit(gx, "krug-opener", lambda d: d["posts"][0].update(text="[клуб]({{ link('auction') }})"))
    assert any("krug-opener" in e and "auction" in e for e in _errors(gx))


def test_stub_field_must_point_to_stub_page(gx):
    _edit(gx, "kadr-late", lambda d: d.update(stub="krug"))
    assert any("kadr-late" in e and "не заглушка" in e for e in _errors(gx))


# ---------------------------------------------------------------- leak scan


def test_page_segments_split_template_but_not_markdown():
    html = ('<header><a class="kr-logo" href="/">круг</a> <a class="s" href="#">Поиск людей</a></header>'
            '<p>Текст <a href="/p/x/">ссылка</a> <em>дальше</em></p><p><b class="h">Помощь.</b> Чтобы</p>')
    assert page_segments(html) == ["круг", "Поиск людей", "Текст ссылка дальше", "Помощь.", "Чтобы"]


def test_gated_profile_text_on_open_page_is_leak(tmp_path):
    from engine.check import check

    c = copy_content(tmp_path)
    add_fixture_pages(c)
    add_gate_fixtures(c)
    _edit(c, "krug-opener", lambda d: d["posts"][0].update(
        text="Секретная фраза позднего тестового профиля про синий зонтик."))
    lock = tmp_path / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    dist = tmp_path / "dist"
    build(content_dir=c, dist=dist, salts_path=lock, log=lambda *_: None)
    rep = check(content_dir=c, dist=dist, salts_path=lock)
    text = "\n".join(rep.problems)
    assert "p/krug-opener/index.html" in text and "страница krug-later" in text
    assert "ключ страницы" not in text


def test_pacing_gate_text_is_not_secret_but_key_is(tmp_path):
    """gate: pacing (docs/02 §3.10): профиль закрыт ради темпа — его фраза на открытой странице не утечка,
    а ключ профиля в открытом файле — по-прежнему ошибка check."""
    from engine.check import check

    c = copy_content(tmp_path)
    add_fixture_pages(c)
    add_gate_fixtures(c)
    _edit(c, "krug-later", lambda d: d.update(gate="pacing"))
    _edit(c, "krug-opener", lambda d: d["posts"][0].update(
        text="Секретная фраза позднего тестового профиля про синий зонтик."))
    lock = tmp_path / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    dist = tmp_path / "dist"
    build(content_dir=c, dist=dist, salts_path=lock, log=lambda *_: None)
    rep = check(content_dir=c, dist=dist, salts_path=lock)
    assert not [p for p in rep.problems if "krug-later" in p]
    # ключ профиля, подброшенный в открытый файл, ловится
    key = key_of(salts_mod.read(lock), "krug-later")
    f = dist / "p" / "krug-opener" / "index.html"
    f.write_text(f.read_text(encoding="utf-8") + f"<!-- {key} -->", encoding="utf-8")
    rep = check(content_dir=c, dist=dist, salts_path=lock)
    assert any("ключ страницы «krug-later»" in p for p in rep.problems)


def test_pacing_gate_only_on_locked_page(gx):
    _edit(gx, "krug-opener", lambda d: d.update(gate="pacing"))
    assert any("krug-opener" in e and "gate: pacing" in e for e in _errors(gx))
