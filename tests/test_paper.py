"""Бумажные документы ``content/paper/`` и ``python -m engine paper``: загрузка и валидация,
данные для бланков, ``--release``, PDF и сборники конвертов, защита от публикации в ``dist/``.

Тесты с браузером пропускаются с причиной, если Chromium для Playwright недоступен
(``PW_CHROMIUM_PATH`` или ``python -m playwright install chromium``, docs/DEV.md).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from engine import ROOT
from engine import salts as salts_mod
from engine.build import build
from engine.check import check, leak_needles
from engine.content import PAPER_TEMPLATES, ContentError, collect_todos, form_templates, load_content
from engine.leakscan import scan_text
from engine.paper import (
    PaperError,
    doc_data,
    paper_ids,
    paper_markdown,
    paper_texts,
    pdf_pages,
    qr_cards,
    render_paper,
)
from engine.templating import make_context

CONTENT = ROOT / "content"
FORMS = {"protocol", "report", "ambulance", "forensic", "plan", "program", "inventory", "phototable", "journal",
         "memo", "certificate", "ticket", "inspection", "estimate", "registry", "pharmacy", "chat", "letter",
         "note", "press"}


@pytest.fixture(scope="module")
def content():
    return load_content(CONTENT)


@pytest.fixture(scope="module")
def salts(content, tmp_path_factory):
    return salts_mod.ensure_for_content(content, tmp_path_factory.mktemp("s") / "salts.lock.json")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    dst = tmp_path / "content"
    shutil.copytree(CONTENT, dst)
    return dst


@pytest.fixture(scope="module")
def chromium():
    from engine.printing import PrintError, browser

    try:
        with browser():
            pass
    except PrintError as e:
        pytest.skip(f"Chromium для печати недоступен: {e}")
    return True


def write_paper(root: Path, doc_id: str, front: str, body: str = "Текст.\n", name: str | None = None) -> Path:
    p = root / "paper" / f"{name or doc_id}.md"
    p.parent.mkdir(exist_ok=True)
    p.write_text(f"---\n{front.strip()}\n---\n{body}", encoding="utf-8")
    return p


def errors_of(root: Path) -> list[str]:
    with pytest.raises(ContentError) as exc:
        load_content(root)
    return [str(e) for e in exc.value.errors]


def assert_error(root: Path, *parts: str) -> None:
    errs = errors_of(root)
    assert any(all(p in e for p in parts) for e in errs), "\n".join(["ожидалось: " + " … ".join(parts), *errs])


# ---------------------------------------------------------------- загрузка и заглушки


def test_all_forms_have_templates():
    assert FORMS <= set(form_templates(PAPER_TEMPLATES))
    assert not any(f.startswith("_") for f in form_templates(PAPER_TEMPLATES))


def test_examples_loaded(content):
    assert set(content.paper) >= {"1-02", "1-07"}
    assert content.paper["1-07"].meta.form == "program"
    assert content.paper["1-02"].meta.form == "report"
    missing = {t.loc for t in content.paper_missing}
    expected = [d for d in content.documents if d.kind == "paper" and d.id not in content.paper]
    assert len(content.paper_missing) == len(expected) and "documents[0]" in missing
    assert all(t.kind == "missing-paper" and "нет текста бумажного документа" in t.text for t in content.paper_missing)


def test_paper_todos_collected(content):
    todos = collect_todos(content)
    kinds = {t.kind for t in todos}
    assert "missing-paper" in kinds
    rep = [t for t in todos if t.file == "content/paper/1-02.md"]
    assert len(rep) == 1 and rep[0].kind == "text" and rep[0].loc == "строка 7"
    assert "текст рапорта" in rep[0].text


def test_front_matter_todo_is_value(root):
    write_paper(root, "1-03", 'id: "1-03"\nform: ambulance\nplace: "TODO(content): адрес"')
    c = load_content(root)
    t = [x for x in collect_todos(c) if x.file == "content/paper/1-03.md"]
    assert [(x.kind, x.loc) for x in t] == [("value", "front matter.place")]
    assert not any(x.kind == "missing-paper" and "1-03.md" in x.text for x in collect_todos(c))


# ---------------------------------------------------------------- валидация


def test_unknown_document(root):
    write_paper(root, "9-99", 'id: "9-99"\nform: protocol')
    assert_error(root, "content/paper/9-99.md: front matter.id", "документа «9-99» нет в documents.yaml")


def test_not_paper_kind(root):
    write_paper(root, "1-12", 'id: "1-12"\nform: protocol')
    assert_error(root, "content/paper/1-12.md: front matter.id", "kind: online")


def test_id_must_match_filename(root):
    write_paper(root, "1-03", 'id: "1-04"\nform: protocol', name="1-03")
    assert_error(root, "content/paper/1-03.md: front matter.id", "совпадать с именем файла")


def test_unknown_form(root):
    write_paper(root, "1-03", 'id: "1-03"\nform: telegram')
    assert_error(root, "content/paper/1-03.md: front matter.form", "нет бланка «telegram»",
                 "site/templates/print/paper/telegram.html")


def test_extra_field_and_unquoted_date(root):
    write_paper(root, "1-03", 'id: "1-03"\nform: ambulance\ndate: 2026-11-10\ncolor: red')
    errs = errors_of(root)
    assert any("1-03.md: front matter.date" in e and "в кавычки" in e for e in errs), errs
    assert any("1-03.md: front matter.color" in e and "лишнее поле" in e for e in errs), errs


def test_stage_mismatch(root):
    write_paper(root, "2-05", 'id: "2-05"\nform: journal\nstage: 3')
    assert_error(root, "content/paper/2-05.md: front matter.stage", "в конверте 2")


def test_qr_without_page(root):
    write_paper(root, "1-03", 'id: "1-03"\nform: ambulance\nqr: true')
    assert_error(root, "content/paper/1-03.md: front matter.qr", "нет page")


def test_chat_form_needs_chat_file(root):
    write_paper(root, "2-05", 'id: "2-05"\nform: chat', body="")
    assert_error(root, "content/paper/2-05.md: front matter.form", "content/chats/2-05.yaml")


def test_media_extensions(root):
    write_paper(root, "1-10", 'id: "1-10"\nform: phototable\nmedia: ["a/photo.gif", "a/sound.mp3", "../x.jpg"]')
    errs = errors_of(root)
    assert any("front matter.media[0]" in e and "не поддерживается" in e for e in errs), errs
    assert any("front matter.media[1]" in e and "только изображения" in e for e in errs), errs
    assert any("front matter.media[2]" in e and "относительным" in e for e in errs), errs


def test_template_typo_in_body_and_front_matter(root):
    write_paper(root, "1-03", 'id: "1-03"\nform: ambulance\nmeta:\n  org: "{{ w.ambulans }}"',
                body="Врач: {{ c.nobody.short() }}\n")
    errs = errors_of(root)
    assert any("content/paper/1-03.md: текст" in e and "нет персонажа «nobody»" in e for e in errs), errs
    assert any("content/paper/1-03.md: front matter.meta.org" in e and "w.ambulans" in e for e in errs), errs


def test_build_ignores_paper_dir(root, tmp_path):
    """build не публикует бумагу: в dist/ нет ни файлов, ни текста content/paper/."""
    marker = "Контрольная фраза бумажного документа для проверки публикации"
    write_paper(root, "1-03", 'id: "1-03"\nform: ambulance', body=f"{marker}.\n")
    dist = tmp_path / "dist"
    build(content_dir=root, dist=dist, salts_path=tmp_path / "salts.json", media_dir=tmp_path / "media")
    for p in dist.rglob("*"):
        assert "paper" not in p.relative_to(dist).as_posix()
        if p.is_file() and p.suffix in (".html", ".json", ".js", ".css", ".txt"):
            assert "Контрольная фраза" not in p.read_text(encoding="utf-8"), p


# ---------------------------------------------------------------- данные бланков (без браузера)


def test_markdown_tables_and_html():
    html = paper_markdown("| A | B |\n|---|---|\n| 1 | 2 |\n\n<div class=\"x\">сырой</div>\n")
    assert "<table>" in html and "<td>1</td>" in html and '<div class="x">сырой</div>' in html


def test_doc_data_examples(content, salts):
    ctx = make_context(content)
    w = content.world
    prog = doc_data(content, "1-07", ctx, cards=qr_cards(content, salts))
    assert prog["form"] == "program" and prog["title"] == w["play"]["title"] and not prog["stub"]
    assert prog["meta"]["author"] == w["play"]["author"] and prog["date"] == w["dates"]["premiere"]
    c = ctx["c"]
    for name in (c.voroncov.short(), c.stas.short(), c.zavyalov.short(), w["play"]["schedule"]["act1"],
                 w["play"]["role_main"]):
        assert name in prog["body_html"], name
    assert "<table>" in prog["body_html"] and "{{" not in prog["body_html"] and prog["qr"] is None
    rep = doc_data(content, "1-02", ctx)
    assert rep["title"] == f"Рапорт сержанта полиции {c.kovalev.short('gen')}"
    assert rep["signed"] == [{"role": c.kovalev.role, "name": c.kovalev.short()}]
    stub = doc_data(content, "2-05", ctx)
    assert stub["stub"] and stub["form"] == "stub" and stub["doc_title"] == "Журнал помощника режиссёра"


def test_doc_qr_same_link_as_qr_command(content, salts):
    ctx = make_context(content)
    cards = qr_cards(content, salts)
    call = doc_data(content, "1-05", ctx, cards=cards)
    assert call["qr"]["url"] == cards["call"].url and call["qr"]["label"] == cards["call"].label
    assert "<svg" in call["qr"]["svg"]
    cloud = doc_data(content, "4-13", ctx, cards=cards)
    assert cloud["qr"]["url"].endswith("/p/cloud/") and "#k=" not in cloud["qr"]["url"]
    inna = doc_data(content, "2-09", ctx, cards=cards)
    assert "#k=" in inna["qr"]["url"]


def test_qr_can_be_disabled(root, salts):
    write_paper(root, "1-05", 'id: "1-05"\nform: protocol\nqr: false')
    c = load_content(root)
    assert doc_data(c, "1-05", make_context(c), cards=qr_cards(c, salts))["qr"] is None


def test_paper_texts_rendered(content):
    texts = paper_texts(content)
    srcs = {s for s, _, _ in texts}
    assert {"content/paper/1-07.md", "content/paper/1-02.md"} <= srcs
    body = next(t for s, t, _ in texts if s == "content/paper/1-07.md")
    assert make_context(content)["c"].voroncov.short() in body and "{{" not in body
    assert {st for _, _, st in texts} == {1}


# ---------------------------------------------------------------- --release (без браузера)


def test_release_fails_on_missing_paper(content, salts, tmp_path):
    with pytest.raises(PaperError) as exc:
        render_paper(content, tmp_path / "out", salts=salts, release=True, media_dir=tmp_path / "media")
    text = str(exc.value)
    assert "2-05: нет текста бумажного документа content/paper/2-05.md" in text
    assert "TODO(content): content/paper/1-02.md: строка 7" in text
    assert "домен-заглушка" in text
    assert not list((tmp_path / "out").glob("*.pdf"))


def test_release_rendered_todo_and_missing_media(root, salts, tmp_path):
    write_paper(root, "1-10", 'id: "1-10"\nform: phototable\nmedia: ["lab/none.jpg"]',
                body="Исполнительница: {{ c.nina_actress.short() }}\n")
    c = load_content(root)
    with pytest.raises(PaperError) as exc:
        render_paper(c, tmp_path / "out", salts=salts, only=["1-10"], release=True, media_dir=tmp_path / "media")
    text = str(exc.value)
    assert "1-10: после подстановки" in text and "1-10: нет медиафайла media/lab/none.jpg" in text


def test_only_unknown_id(content, salts, tmp_path):
    with pytest.raises(PaperError) as exc:
        render_paper(content, tmp_path, salts=salts, only=["1-12"])
    assert "--only 1-12" in str(exc.value)


# ---------------------------------------------------------------- PDF (браузер)


def test_render_only_examples(chromium, content, salts, tmp_path):
    rep = render_paper(content, tmp_path, salts=salts, only=["1-07", "1-02"])
    assert [r.id for r in rep.rows] == ["1-02", "1-07"] and rep.envelopes == []
    for r in rep.rows:
        assert r.pdf.read_bytes()[:5] == b"%PDF-" and r.pages == 1
        assert r.preview.is_file() and r.preview.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert r.status == "TODO(content)"
    assert not list(tmp_path.glob(".chats-*"))


def test_render_envelopes_and_stubs(chromium, content, salts, tmp_path):
    rep = render_paper(content, tmp_path, salts=salts, preview=False)
    ids = paper_ids(content)
    assert [r.id for r in rep.rows] == ids
    assert [p.name for p in rep.envelopes] == [f"envelope-{n}.pdf" for n in (1, 2, 3, 4)]
    for n, env in enumerate(rep.envelopes, 1):
        expected = sum(r.pages for r in rep.rows if r.stage == n)
        assert pdf_pages(env) == expected, env
    stub = next(r for r in rep.rows if r.id == "2-05")
    assert stub.form == "stub" and stub.pages == 1 and "заглушка" in stub.status
    assert "2-05" in rep.table() and "бланк" in rep.table()


def test_render_chat_form(chromium, root, salts, tmp_path):
    write_paper(root, "3-03", 'id: "3-03"\nform: chat\npages_hint: 1', body="")
    c = load_content(root)
    rep = render_paper(c, tmp_path, salts=salts, only=["3-03"], preview=False)
    row = rep.rows[0]
    assert row.form == "chat" and row.pages == 2  # 4 снимка экрана по 2 на страницу
    assert "ожидалось 1 (pages_hint)" in row.status


# ---------------------------------------------------------------- check: бумага не попадает в dist


def test_check_catches_paper_in_dist(root, tmp_path):
    marker = "Фельдшер записал хрипы в лёгких и редкий пульс пострадавшего"
    write_paper(root, "1-03", 'id: "1-03"\nform: ambulance', body=f"{marker}.\n")
    write_paper(root, "3-07", 'id: "3-07"\nform: ticket', body="Поезд отправился с третьего пути без опоздания.\n")
    salts = tmp_path / "salts.json"
    dist = tmp_path / "dist"
    media = tmp_path / "media"
    build(content_dir=root, dist=dist, salts_path=salts, media_dir=media)
    assert check(content_dir=root, dist=dist, salts_path=salts, media_dir=media).ok
    (dist / "leak-paper.html").write_text(f"<p>{marker.upper()}!</p>", encoding="utf-8")
    rep = check(content_dir=root, dist=dist, salts_path=salts, media_dir=media)
    assert not rep.ok
    row = next(r for r in rep.rows if r.name.startswith("7."))
    assert not row.ok and "бумаги content/paper" in row.detail
    probs = [p for p in rep.problems if p.startswith("[7.")]
    assert any("leak-paper.html" in p and "(paper, shingle)" in p and "content/paper/1-03.md" in p for p in probs), probs


def test_pack1_may_quote_envelope1_paper_only(root, tmp_path):
    """В открытом тексте pack-1 (ключ публичный) бумага конверта 1 — не утечка, конверта 3 — утечка."""
    from engine.build import prepare
    from engine.check import pack1_problems

    write_paper(root, "3-07", 'id: "3-07"\nform: ticket', body="Поезд отправился с третьего пути без опоздания.\n")
    c = load_content(root)
    salts = tmp_path / "salts.json"
    salts_mod.ensure_for_content(c, salts)
    ns = leak_needles(prepare(root, salts, create_salts=False))
    texts: dict[str, str] = {}
    for src, t, _ in paper_texts(c):
        texts.setdefault(src, t)  # первым идёт тело документа
    assert {nd.stage for nd in ns.shingles.values() if nd.kind == "paper"} == {1, 3}
    assert pack1_problems({"questions": [{"prompt": texts["content/paper/1-07.md"]}]}, ns, 1) == []
    probs = pack1_problems({"questions": [{"prompt": texts["content/paper/3-07.md"]}]}, ns, 1)
    assert probs and all("content/paper/3-07.md" in p for p in probs)
    assert scan_text(texts["content/paper/1-07.md"], ns, "x")  # в файле dist/ — утечка и для конверта 1
