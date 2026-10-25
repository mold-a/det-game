"""P07: QR-коды, «скриншоты» переписок, аварийный конверт. Всё — в tmp_path.

Тесты с браузером пропускаются с понятной причиной, если Chromium для Playwright недоступен
(``python -m playwright install chromium`` или переменная ``PW_CHROMIUM_PATH``, docs/DEV.md).
"""

from __future__ import annotations

import shutil
import struct
from pathlib import Path

import pytest

from engine import ROOT
from engine import salts as salts_mod
from engine.content import ContentError, load_content, units
from engine.emergency import emergency_data
from engine.qr import decoder, make_qr_set, plan_cards

CONTENT = ROOT / "content"


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


@pytest.fixture(scope="module")
def content():
    return load_content(CONTENT)


@pytest.fixture(scope="module")
def salts(content, tmp_path_factory):
    return salts_mod.ensure_for_content(content, tmp_path_factory.mktemp("s") / "salts.lock.json")


@pytest.fixture(scope="module")
def chromium():
    """Проверить, что браузер для печати запускается; иначе — пропуск с причиной."""
    from engine.printing import PrintError, browser

    try:
        with browser():
            pass
    except PrintError as e:
        pytest.skip(f"Chromium для печати недоступен: {e}")
    return True


# ---------------------------------------------------------------- QR без браузера


def test_qr_urls(content, salts):
    cards = {c.slug: c for c in plan_cards(content, salts)}
    assert set(cards) == {s for s, p in content.pages.items() if p.doc}  # QR — только страницам с документом
    dom = content.settings.domain
    for slug, c in cards.items():
        access = c.access
        if access == "key":
            key = salts_mod.b64u_encode(salts.page_key(slug))
            assert c.url == f"{dom}/p/{slug}/#k={key}"
        else:
            assert c.url == f"{dom}/p/{slug}/" and "#k=" not in c.url
        assert c.label and "{{" not in c.label
    assert cards["cloud"].access == "password" and cards["cloud"].docs == ["4-13"]
    assert cards["gromov"].docs == ["1-12"] and cards["inna"].envelope == 2


def test_qr_cards_cover_every_page_of_every_document(content, salts):
    """Документ с несколькими страницами (``pages``) попадает в ``docs`` карточки каждой из них."""
    cards = {c.slug: c for c in plan_cards(content, salts)}
    multi = [d for d in content.documents if len(d.page_slugs) > 1]
    for d in multi:
        for slug in d.page_slugs:
            assert slug in cards and d.id in cards[slug].docs, (d.id, slug)
    for d in content.documents:
        if d.kind == "paper":
            for slug in d.page_slugs:
                assert d.id in cards[slug].docs


def test_qr_files_and_selfcheck(content, salts, tmp_path):
    rep = make_qr_set(content, salts, tmp_path, sheet=False)
    for c in rep.cards:
        w, h = png_size(c.png)
        assert w == h and 1100 <= w <= 1200
        assert c.svg.read_text(encoding="utf-8").lstrip().startswith("<svg")
    assert not any("example.ru" in w for w in rep.warnings)  # домен задан (mydetgame.ru)
    if decoder() is None:
        assert any("самопроверка QR пропущена" in w for w in rep.warnings)
        pytest.skip("нет extra qrcheck (zxing-cpp, pillow): декодирование не проверено")
    assert all(c.verified is True for c in rep.cards)


# ---------------------------------------------------------------- chats: схема


def _copy(tmp_path: Path) -> Path:
    dst = tmp_path / "content"
    shutil.copytree(CONTENT, dst)
    return dst


def test_chats_loaded(content):
    assert set(content.chats) == {"3-03", "4-06", "4-12"}
    kinds = [s.kind for s in content.chats["3-03"].screens]
    assert kinds == ["chat", "notification", "calls", "chat"]


def test_chat_validation_errors(tmp_path):
    root = _copy(tmp_path)
    p = root / "chats" / "4-12.yaml"
    s = p.read_text(encoding="utf-8")
    s = s.replace("{ from: voroncov, time", "{ from: gromov, time", 1)
    s = s.replace("with: voroncov", "with: voroncov\n    extra: 1")
    p.write_text(s, encoding="utf-8")
    (root / "chats" / "9-99.yaml").write_text('id: "9-98"\nscreens: []\n', encoding="utf-8")
    with pytest.raises(ContentError) as exc:
        load_content(root)
    errs = [str(e) for e in exc.value.errors]
    assert any("content/chats/4-12.yaml: screens[0]" in e and "extra" in e and "лишнее поле" in e for e in errs)
    assert any("content/chats/9-99.yaml: screens" in e and "пуст" in e for e in errs)


def test_chat_sender_not_in_private_chat(tmp_path):
    root = _copy(tmp_path)
    p = root / "chats" / "4-12.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("{ from: voroncov, time", "{ from: gromov, time", 1),
                 encoding="utf-8")
    with pytest.raises(ContentError) as exc:
        load_content(root)
    assert any("screens[0].messages[4].from" in str(e) and "не участвует" in str(e) for e in exc.value.errors)


def test_chat_template_typo(tmp_path):
    root = _copy(tmp_path)
    p = root / "chats" / "3-03.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("w.brands.cloud", "w.brands.clod"), encoding="utf-8")
    with pytest.raises(ContentError) as exc:
        load_content(root)
    assert any("content/chats/3-03.yaml: screens[1].items[0].app" in str(e) for e in exc.value.errors)


# ---------------------------------------------------------------- аварийный конверт: данные


def test_emergency_data_complete(content):
    data = emergency_data(content)
    paths = [q["path"] for st in data["stages"] for q in st["questions"]]
    qpaths = {u.path.rsplit(".", 1)[0] if u.field else u.path for u in units(content)}
    assert set(paths) == qpaths
    assert "s3.b3" in paths and "s4.fb2" in paths
    fb2 = next(q for st in data["stages"] for q in st["questions"] if q["path"] == "s4.fb2")
    cs = {c.id: c for c in content.characters}
    assert cs["voroncov"].last in fb2["rows"][0]["answer"] and cs["zavyalov"].last in fb2["rows"][0]["answer"]
    assert len(data["lab"]) == len(content.expertise.results)
    assert all(x["bases"] for x in data["lab"])
    sv = next(x for x in data["lab"] if any(p["label"] == "Время" for p in x["params"]))
    # дата и время вокзальной камеры берутся из контента (сдвиг дат сюжета не должен ломать тест)
    res = next(r for r in content.expertise.results if r.params_answer and "date" in r.params_answer)
    want = {res.params_answer["date"].canon, res.params_answer["time"].canon}
    assert {p["value"] for p in sv["params"]} >= want
    assert data["stages"][0]["next"] and data["stages"][-1]["next"] is None


# ---------------------------------------------------------------- с браузером


def test_qr_sheet_pdf(chromium, content, salts, tmp_path):
    rep = make_qr_set(content, salts, tmp_path)
    assert rep.sheet.read_bytes()[:5] == b"%PDF-"


def test_chatshot_pngs(chromium, content, tmp_path):
    from engine.chatshot import render_chats

    paths = render_chats(content, tmp_path)
    names = sorted(p.name for p in paths)
    expected = sorted(
        f"{cid}-{i}.png" for cid, chat in content.chats.items() for i in range(1, len(chat.screens) + 1)
    )
    assert names == expected and {"3-03-1.png", "4-06-1.png", "4-12-1.png"} <= set(names)
    for p in paths:
        assert png_size(p) == (1080, 2340)


def test_answers_pdf(chromium, content, tmp_path):
    from engine.emergency import answers_pdf

    out = answers_pdf(content, tmp_path / "answers.pdf")
    data = out.read_bytes()
    assert data[:5] == b"%PDF-" and data.count(b"/Type /Page") - data.count(b"/Type /Pages") >= 8
