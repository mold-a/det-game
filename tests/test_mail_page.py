"""Почтовый ящик ``type: mail`` (решение автора 25.10.2026; docs/03 §8, docs/04 «mail»): модель, рендер,
шифрование закрытой страницы и её вложений, leak scan текстов писем.

Тестовая страница — ``tests/fixtures/pages/mail-sample.yaml`` (три цепочки, нейтральный текст), кладётся в КОПИЮ
content/ (``pages_fixture.add_mail_fixture``) с копией ``engine/salts.lock.json``; в content/ её нет.
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
from pages_fixture import FIXTURES, MAIL_FILES, MAIL_SLUG, add_mail_fixture, copy_content  # noqa: E402

from engine import ROOT, crypto  # noqa: E402
from engine import salts as salts_mod  # noqa: E402
from engine.build import build  # noqa: E402
from engine.check import check  # noqa: E402
from engine.content import ContentError, load_content  # noqa: E402
from engine.models import PAGE_MODELS, MailPage  # noqa: E402
from engine.pages import mail_preview, page_css  # noqa: E402

FAKE_JPG = b"\xff\xd8\xff\xe0" + bytes(range(100)) * 3
SAMPLE = yaml.safe_load((FIXTURES / f"{MAIL_SLUG}.yaml").read_text(encoding="utf-8"))
# Фраза из письма закрытой страницы (тексты писем — секрет, обычный режим leak scan)
SECRET = "Тестовое личное письмо про пирог и прогулку в парке."


def sample(**over) -> dict:
    d = json.loads(json.dumps(SAMPLE))
    d.update(over)
    return d


# ---------------------------------------------------------------- модель


def test_type_registered_and_fixture_validates():
    assert PAGE_MODELS["mail"] is MailPage
    p = MailPage.model_validate(sample())
    assert p.type == "mail" and p.brand == "Почта «Тестовая»"
    assert [t.id for t in p.threads] == ["work", "personal", "odd"]
    odd = p.threads[2]
    assert odd.messages[1].read is False and odd.messages[0].read is True  # read по умолчанию true
    assert odd.messages[0].to[1].name is None and odd.messages[0].to[1].person is None  # адрес без имени
    assert odd.messages[0].attachments[0].page == "news"


def test_defaults_brand_and_folders():
    d = sample()
    del d["brand"], d["folders"], d["notice"]
    for t in d["threads"]:
        t["folder"] = "Входящие"
    p = MailPage.model_validate(d)
    assert p.brand == "Почта" and p.folders == ["Входящие", "Отправленные"] and p.notice is None


def _bad(fn) -> str:
    d = sample()
    fn(d)
    with pytest.raises(ValidationError) as e:
        MailPage.model_validate(d)
    return str(e.value)


def test_model_errors():
    msg0 = lambda d: d["threads"][0]["messages"][0]  # noqa: E731
    assert "не больше одного" in _bad(lambda d: msg0(d)["from"].update(person="voroncov"))
    assert "настоящему сервису" in _bad(lambda d: msg0(d)["from"].update(address="someone@gmail.com"))
    assert "не адрес почты" in _bad(lambda d: msg0(d)["from"].update(address="без собаки"))
    assert "ISO" in _bad(lambda d: msg0(d).update(date="5 октября"))
    assert "media" in _bad(lambda d: msg0(d)["attachments"][0].update(page="news"))
    assert ".jpg" in _bad(lambda d: msg0(d)["attachments"][0].update(media="mail-sample/file.pdf"))
    assert "ровно одно" in _bad(lambda d: d["account"].pop("name"))
    assert "to" in _bad(lambda d: msg0(d).update(to=[]))
    assert "threads" in _bad(lambda d: d.update(threads=[]))
    assert "from" in _bad(lambda d: msg0(d).pop("from"))
    assert "extra" in _bad(lambda d: d["threads"][0].update(pinned=True)).lower() or "Extra" in _bad(
        lambda d: d["threads"][0].update(pinned=True))


def test_todo_placeholders_allowed_in_date_and_address():
    d = sample()
    d["threads"][0]["messages"][0]["date"] = "TODO(content): дата письма"
    d["threads"][0]["messages"][0]["from"]["address"] = "TODO(content): адрес"
    MailPage.model_validate(d)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    c = copy_content(tmp_path)
    add_mail_fixture(c)
    return c


def _errors(root: Path, fn) -> str:
    path = root / "pages" / MAIL_SLUG / "page.yaml"
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(d)
    path.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    with pytest.raises(ContentError) as e:
        load_content(root)
    return str(e.value)


def test_content_checks_folder_ids_and_people(root):
    load_content(root)  # фикстура валидна вместе с остальным контентом
    assert "папки «Архив» нет в folders" in _errors(root, lambda d: d["threads"][0].update(folder="Архив"))


def test_content_checks_duplicates_and_unknown_person(root):
    def dupes(d):
        d["threads"][1]["id"] = "work"
        d["folders"].append("Входящие")
        d["threads"][2]["messages"][0]["to"][0] = {"person": "nobody_here", "address": "x@pochta-test.test"}

    errs = _errors(root, dupes)
    assert "дубликат ID цепочки «work»" in errs
    assert "папка «Входящие» уже есть" in errs
    assert "персонажа «nobody_here» нет" in errs


def test_preview_is_plain_and_short():
    assert mail_preview("<p>Раз <a href='/p/x/'>два</a></p>\n<p>три &amp; четыре</p>") == "Раз два три & четыре"
    long = mail_preview("<p>" + "слово " * 60 + "</p>", limit=30)
    assert len(long) <= 30 and long.endswith("…")


# ---------------------------------------------------------------- сборка: рендер и шифрование


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("mail")
    c = copy_content(tmp)
    add_mail_fixture(c)
    media = tmp / "media"
    shutil.copytree(ROOT / "media", media)
    for rel in MAIL_FILES:
        (media / rel).parent.mkdir(parents=True, exist_ok=True)
        (media / rel).write_bytes(FAKE_JPG)
    lock = tmp / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    dist = tmp / "dist"
    build(content_dir=c, dist=dist, media_dir=media, salts_path=lock, log=lambda *_: None)
    salts = salts_mod.read(lock)
    box = json.loads((dist / "p" / MAIL_SLUG / "payload.json").read_text(encoding="utf-8"))
    inner = json.loads(crypto.open_(salts.page_key(MAIL_SLUG), box, f"page/{MAIL_SLUG}"))
    return tmp, c, dist, salts, inner


def test_shell_is_sealed_and_has_no_letters(built):
    _, c, dist, salts, inner = built
    shell = (dist / "p" / MAIL_SLUG / "index.html").read_text(encoding="utf-8")
    assert 'data-type="mail"' in shell and 'data-access="key"' in shell
    assert "/assets/css/pages/mail.css" in shell and "/assets/js/pages/shell.js" in shell
    assert "Почта «Тестовая»" in shell  # бренд виден до расшифровки
    for secret in ("Тестовая рабочая тема", "owner@pochta-test.test", "пирог", "Выгрузка ящика"):
        assert secret not in shell
    assert inner["type"] == "mail" and inner["slug"] == MAIL_SLUG and inner["title"] == "Почта «Тестовая»"
    assert page_css(load_content(c).pages[MAIL_SLUG]) == ["/assets/css/pages/_ui.css", "/assets/css/pages/mail.css"]
    key = crypto.b64u_encode(salts.page_key(MAIL_SLUG))
    for p in dist.rglob("*"):  # ключ страницы этапа 3 не лежит открытым (ссылка на неё — только в облаке)
        if p.is_file() and p.suffix in (".html", ".json", ".js"):
            assert key not in p.read_text(encoding="utf-8", errors="replace"), p


def test_fragment_layout(built):
    html = built[4]["html"]
    assert "Выгрузка ящика по запросу № 00-000 от 01.01.2026" in html
    assert "owner@pochta-test.test" in html and "Тестовый Владелец" in html
    # папки с числом цепочек; у «Проекты» — непрочитанное
    folders = re.findall(r'data-folder-link="(\d)".*?ml-folder__title">([^<]+)<.*?ml-folder__count[^>]*>(\d+)<', html, re.S)
    assert folders == [("0", "Входящие", "2"), ("1", "Отправленные", "0"), ("2", "Проекты", "1"), ("3", "Черновики", "0")]
    assert 'aria-label="непрочитанных: 1"' in html
    assert "В папке нет писем" in html
    # список: новые сверху; непрочитанная цепочка — жирным (is-unread); «Кому:» у цепочки, где писал только владелец
    rows = re.findall(r'class="ml-row( is-unread)?" href="#mt-([a-z]+)"', html)
    assert rows == [("", "personal"), ("", "work"), (" is-unread", "odd")]
    assert "Коллега Проверочный" in html and '<span class="ml-row__n" aria-label="писем в цепочке: 2">2</span>' in html
    assert re.search(r'ml-row__who">Подрядчик Условный<', html)  # писал и подрядчик — он и в списке
    assert '07.10.2026</time>' in html and "05.10.2026, 11:26" in html
    # цепочка: письма по порядку, «Не прочитано», цитата, ссылка из Markdown
    odd = html[html.index('id="mt-odd"'):]
    assert odd.index("2026-10-09T13:31") < odd.index("2026-10-10T08:14")
    assert "Не прочитано" in odd and "<blockquote>" in odd
    assert 'href="/p/news/">на странице</a>' in html
    assert "buh@masterskaya-test.test" in html  # адрес без имени — только адрес
    assert html.count('data-act="back"') == 3
    assert "·" not in html  # решение автора 24.10: без средних точек


def test_attachments_and_sealed_media(built):
    _, _, dist, _, inner = built
    html, refs = inner["html"], inner["media"]
    # картинка: кнопка «крупно» с миниатюрой, файл зашифрован (ключ — внутри payload)
    m = re.search(r'<button class="ml-file ml-file--img"[^>]*data-zoom[^>]*>(.*?)</button>', html, re.S)
    assert m and 'data-media="0"' in m.group(1) and "график-тест.jpg" in m.group(1) and "120 КБ" in m.group(1)
    assert len(refs) == 1 and refs[0]["key"] and refs[0]["src"].endswith(".bin") and refs[0]["mime"] == "image/jpeg"
    blob = (dist / refs[0]["src"].lstrip("/")).read_bytes()
    assert FAKE_JPG not in blob
    assert crypto.open_media(crypto.b64u_decode(refs[0]["key"]), blob, refs[0]["aad"]) == FAKE_JPG
    # картинка без файла — заглушка, без кнопки
    assert re.search(r'<span class="ml-file ml-file--missing"><span class="ph ph--img ml-file__thumb"', html)
    # ссылка на страницу и просто файл
    assert '<a class="ml-file ml-file--page" href="/p/news/">' in html
    assert re.search(r'ml-file--plain">.*?таблица-тест\.xlsx.*?18 КБ', html, re.S)


def test_every_button_is_wired_and_no_account_actions(built):
    html = built[4]["html"]
    for m in re.finditer(r"<button\b[^>]*>", html):
        assert "data-act=" in m.group(0) or "data-zoom" in m.group(0), m.group(0)
    for word in ("Написать", "Ответить", "Переслать", "Удалить", "Войти"):
        assert word not in html


# ---------------------------------------------------------------- leak scan: тексты писем — секрет


def _check_with(tmp_path: Path, insert: str | None):
    content = copy_content(tmp_path)
    add_mail_fixture(content)
    if insert is not None:
        page = content / "pages" / "krug-kirill" / "page.yaml"
        d = yaml.safe_load(page.read_text(encoding="utf-8"))
        d["posts"][0]["text"] = f"{insert} " + d["posts"][0].get("text", "")
        page.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    lock = tmp_path / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    dist = tmp_path / "dist"
    build(content_dir=content, dist=dist, salts_path=lock, media_dir=ROOT / "media", log=lambda *_: None)
    return check(content_dir=content, dist=dist, salts_path=lock, media_dir=ROOT / "media")


def test_check_has_no_mail_problems(tmp_path):
    """Ящик сам по себе check не роняет: ни утечек из писем, ни ошибок ссылок и ключей. (Сравнивается только то,
    что касается ящика: остальной контент правит сценарист, и его незаконченные правки — не предмет теста.)"""
    rep = _check_with(tmp_path, None)
    assert not [p for p in rep.problems if MAIL_SLUG in p], rep.problems


def test_letter_text_on_open_page_is_a_leak(tmp_path):
    rep = _check_with(tmp_path, SECRET)
    assert not rep.ok
    probs = [p for p in rep.problems if p.startswith("[7.") and MAIL_SLUG in p]
    assert probs and all("p/krug-kirill/index.html" in p and "shingle" in p for p in probs), probs
