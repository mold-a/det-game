"""Бумажные документы ``content/paper/`` и ``python -m engine paper``: загрузка и валидация,
данные для бланков, ``--release``, PDF и сборники конвертов, защита от публикации в ``dist/``.

Тесты с браузером пропускаются с причиной, если Chromium для Playwright недоступен
(``PW_CHROMIUM_PATH`` или ``python -m playwright install chromium``, docs/DEV.md).
"""

from __future__ import annotations

import re
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


# Бумага в content/paper/ пишется сценаристами и меняется; тесты движка работают на копии контента,
# где в content/paper/ лежат только эти примеры (остальные документы — заглушки).
EXAMPLE_PAPERS = {
    "1-02": """---
id: "1-02"
form: report
signed:
  - { role: "{{ c.kovalev.role }}", name: "{{ c.kovalev.short() }}" }
---
TODO(content): текст рапорта (пример для тестов)
""",
    "1-07": """---
id: "1-07"
form: program
title: "{{ w.play.title }}"
date: "{{ w.dates.premiere }}"
meta:
  author: "{{ w.play.author }}"
---
| Роль | Исполнитель |
|---|---|
| {{ w.play.role_main }} | {{ c.voroncov.short() }} |
| — | {{ c.stas.short() }} |

Режиссёр-постановщик — {{ c.zavyalov.short() }}. Первое действие: {{ w.play.schedule.act1 }}.

TODO(content): пример незаполненного места
""",
}


@pytest.fixture(scope="module")
def examples(tmp_path_factory) -> Path:
    dst = tmp_path_factory.mktemp("examples") / "content"
    shutil.copytree(CONTENT, dst)
    shutil.rmtree(dst / "paper")
    (dst / "paper").mkdir()
    for doc_id, text in EXAMPLE_PAPERS.items():
        (dst / "paper" / f"{doc_id}.md").write_text(text, encoding="utf-8")
    return dst


@pytest.fixture(scope="module")
def content(examples):
    return load_content(examples)


@pytest.fixture(scope="module")
def salts(content, tmp_path_factory):
    return salts_mod.ensure_for_content(content, tmp_path_factory.mktemp("s") / "salts.lock.json")


@pytest.fixture
def root(examples, tmp_path: Path) -> Path:
    dst = tmp_path / "content"
    shutil.copytree(examples, dst)
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


def test_real_paper_renders():
    """Настоящая бумага content/paper/ загружается и даёт данные бланков (без проверок сюжета)."""
    c = load_content(CONTENT)
    ctx = make_context(c)
    for doc_id in paper_ids(c):
        d = doc_data(c, doc_id, ctx)
        assert d["stub"] == (doc_id not in c.paper) and "{{" not in d["body_html"], doc_id


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
    write_paper(root, "4-01", 'id: "4-01"\nform: protocol')
    assert_error(root, "content/paper/4-01.md: front matter.id", "kind: online")


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


def test_split_sections():
    from engine.paper import split_sections

    intro, secs = split_sections("Вступление\n\n## 1. А\nтекст\n```\n## не раздел\n```\n## 2. Б\nещё\n")
    assert intro == "Вступление\n\n"
    assert secs == ["## 1. А\nтекст\n```\n## не раздел\n```\n", "## 2. Б\nещё\n"]
    assert split_sections("Без разделов\n") == ("Без разделов\n", [])


def test_person_marks_and_portrait(content):
    from engine.paper import person_marks, portrait

    assert person_marks("x <!-- person: marina -->\n<!--person:kirill-->") == ["marina", "kirill"]
    ctx = make_context(content)
    p = portrait(content, ctx, "zavyalov", ROOT / "media")
    assert p["known"] and p["path"] == (content.characters_by_id["zavyalov"].photo or "portraits/zavyalov.jpg")
    assert p["name"] == ctx["c"].zavyalov.short()
    assert p["exists"] == (ROOT / "media" / p["path"]).is_file()
    assert not portrait(content, ctx, "nobody_x")["known"]


def test_barcode_code39():
    from engine.paper import _CODE39, barcode_svg

    assert all(len(v) == 9 and v.count("1") == 3 for v in _CODE39.values())
    svg = str(barcode_svg("47/2026"))
    assert svg.count("<rect") == 5 * (len("47/2026") + 2)  # 5 полос на знак, со стоп-знаками *…*
    assert str(barcode_svg("47/2026 ДЕЛО")).count("<rect") == 5 * (len("47/2026 ") + 2)  # кириллица — мимо


def test_autographs():
    from engine.paper import add_autographs, autograph

    sign = ('<div class="paper__sign"><span class="role">Опросил</span><span class="line"><span class="hint">(подпись)'
            '</span></span><span class="name">Ковалёв Д. О.</span></div>')
    out = add_autographs(sign + sign)
    assert out.count('class="autograph"') == 2 and out.count("Ковалёв Д. О.") == 2
    assert '<span class="autograph__text">Кова</span>' in out  # первые 55 % букв фамилии, не меньше трёх
    assert autograph("Ковалёв Д. О.") == autograph("Ковалёв Д. О.")  # детерминированно
    assert autograph("") == ""


def test_fit_scales_and_fit_pdf(tmp_path):
    """Подгонка: ступени допустимы, только если «втягивается» не больше last_page_min страницы;
    выбирается самый крупный масштаб, при котором страниц становится меньше."""
    from pypdf import PdfWriter

    from engine.models import PrintFitSettings
    from engine.paper import fit_pdf, fit_scales

    fit = PrintFitSettings(last_page_min=0.15, scales=[0.97, 0.94, 0.91, 0.88])
    assert fit_scales(1, fit) == []
    assert fit_scales(2, fit) == [0.97, 0.94, 0.91, 0.88]
    assert fit_scales(3, fit) == [0.97, 0.94]          # 2·(1/0,91 − 1) ≈ 0,198 > 0,15
    assert fit_scales(9, fit) == []

    calls: list[float] = []

    def fake(pages_at):
        def to_pdf(_b, _html, out, scale=1):
            calls.append(scale)
            w = PdfWriter()
            for _ in range(pages_at(scale)):
                w.add_blank_page(595, 842)
            with open(out, "wb") as fh:
                w.write(fh)
            return out
        return to_pdf

    out = tmp_path / "doc.pdf"
    assert fit_pdf(None, "", out, fit, fake(lambda s: 1 if s <= 0.94 else 2))[1:] == (1, 0.94)
    assert calls == [1, 0.88, 0.97, 0.94] and not list(tmp_path.glob(".doc.*"))
    calls.clear()
    assert fit_pdf(None, "", out, fit, fake(lambda s: 2))[1:] == (2, 1.0)
    assert calls == [1, 0.88]  # мельчайшая ступень не помогла — дальше не пробуем
    calls.clear()
    assert fit_pdf(None, "", out, fit, fake(lambda s: 1))[1:] == (1, 1.0) and calls == [1]


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
    assert {st for s, _, st in texts if s in ("content/paper/1-07.md", "content/paper/1-02.md")} == {1}


# ---------------------------------------------------------------- --release (без браузера)


def test_release_fails_on_missing_paper(content, salts, tmp_path):
    with pytest.raises(PaperError) as exc:
        render_paper(content, tmp_path / "out", salts=salts, release=True, media_dir=tmp_path / "media")
    text = str(exc.value)
    assert "2-05: нет текста бумажного документа content/paper/2-05.md" in text
    assert "TODO(content): content/paper/1-02.md: строка 7" in text
    assert "домен-заглушка" not in text  # домен задан 20.10.2026
    assert not list((tmp_path / "out").glob("*.pdf"))


def test_release_rendered_todo_and_missing_media(root, salts, tmp_path):
    write_paper(root, "1-10", 'id: "1-10"\nform: phototable\nmedia: ["lab/none.jpg"]',
                body="Подстановка: {{ 'TODO' ~ '(content)' }}\n")
    c = load_content(root)
    with pytest.raises(PaperError) as exc:
        render_paper(c, tmp_path / "out", salts=salts, only=["1-10"], release=True, media_dir=tmp_path / "media")
    text = str(exc.value)
    assert "1-10: после подстановки" in text and "1-10: нет медиафайла media/lab/none.jpg" in text


def test_only_unknown_id(content, salts, tmp_path):
    with pytest.raises(PaperError) as exc:
        render_paper(content, tmp_path, salts=salts, only=["4-01"])
    assert "--only 4-01" in str(exc.value)


# ---------------------------------------------------------------- PDF (браузер)


def test_render_only_examples(chromium, content, salts, tmp_path):
    rep = render_paper(content, tmp_path, salts=salts, only=["1-07", "1-02"])
    assert [r.id for r in rep.rows] == ["1-02", "1-07"] and rep.envelopes == []
    for r in rep.rows:
        assert r.pdf.read_bytes()[:5] == b"%PDF-" and r.pages == 1
        assert r.preview.is_file() and r.preview.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert r.status == "TODO(content)"
    assert not list(tmp_path.glob(".chats-*"))


def _page_texts(path: Path) -> list[str]:
    from pypdf import PdfReader

    # extract_text расставляет пробелы между словами по-своему — сжимаем пробельные символы
    return [" ".join((pg.extract_text() or "").split()) for pg in PdfReader(path).pages]


def _has_sheet(text: str, n: int) -> bool:
    return re.search(rf"Лист {n}(?!\d)", text) is not None


def _two_protocols(root: Path) -> None:
    write_paper(root, "2-02", 'id: "2-02"\nform: protocol', body='Первый лист.\n\n<div class="page-break"></div>\n\nВторой лист.\n')
    write_paper(root, "2-04", 'id: "2-04"\nform: protocol', body="Единственный лист.\n")


def _set_duplex(c, duplex: bool) -> None:
    c.settings.print.duplex = duplex


def test_render_envelopes_and_stubs(chromium, root, salts, tmp_path):
    """Односторонняя печать: сборник конверта = склейка отдельных PDF по порядку documents.yaml
    (заглушки тоже): страниц — сумма, у каждого документа своя нумерация «Лист 1…» (протокол 2-04
    после двухлистового 2-02)."""
    _two_protocols(root)
    c = load_content(root)
    _set_duplex(c, False)
    out = tmp_path / "out"
    rep = render_paper(c, out, salts=salts, preview=False)
    ids = paper_ids(c)
    assert [r.id for r in rep.rows] == ids
    assert [p.name for p in rep.envelopes] == [f"envelope-{n}.pdf" for n in (1, 2, 3, 4)]
    for n, env in enumerate(rep.envelopes, 1):
        rows = [r for r in rep.rows if r.stage == n]
        assert pdf_pages(env) == sum(r.pages for r in rows), env
        # страницы сборника — это страницы отдельных PDF подряд, в порядке documents.yaml
        assert _page_texts(env) == [t for r in rows for t in _page_texts(r.pdf)], env
    by_id = {r.id: r for r in rep.rows}
    assert by_id["2-02"].pages == 2 and by_id["2-04"].pages == 1
    env2 = _page_texts(out / "envelope-2.pdf")
    offset = sum(r.pages for r in rep.rows if r.stage == 2 and ids.index(r.id) < ids.index("2-04"))
    assert offset >= 3  # 2-02 (2 листа) и заглушка 2-03 — до 2-04
    first_204 = env2[offset]
    assert "Единственный лист" in first_204 and _has_sheet(first_204, 1), first_204
    assert not _has_sheet(first_204, offset + 1)  # не сквозная нумерация по конверту
    assert [r.id for r in rep.rows if r.stage == 2][0] == "2-02"
    assert _has_sheet(env2[0], 1) and _has_sheet(env2[1], 2) and "Второй лист" in env2[1], env2[:2]
    stub = next(r for r in rep.rows if r.id == "2-05")
    assert stub.form == "stub" and stub.pages == 1 and "заглушка" in stub.status
    assert "2-05" in rep.table() and "бланк" in rep.table()


def _sheet_no(path: Path, page: int) -> str | None:
    """Номер листа дела «от руки» (поле @top-right) на странице PDF: отдельная строка из цифр."""
    from pypdf import PdfReader

    text = PdfReader(path).pages[page].extract_text() or ""
    # pypdf ставит его в строку метки дела «Дело № … · документ 1-02» (то же поле листа) или отдельно
    m = re.search(r"документ\s+\d+-\d+\s+(\d+)\s*$", text.splitlines()[0]) if text else None
    if m:
        return m[1]
    return next((x.strip() for x in text.splitlines() if x.strip().isdigit()), None)


def test_render_envelopes_duplex(chromium, root, salts, tmp_path):
    """Двусторонняя печать: каждый документ сборника — с нечётной страницы (после документа
    с нечётным числом страниц — пустой оборот с пометкой blank_back), номер листа дела — на лицевых
    страницах, сквозной по конверту; отдельные PDF без оборотов в конце."""
    _two_protocols(root)
    c = load_content(root)
    _set_duplex(c, True)
    note = c.settings.print.blank_back
    assert note, "settings.print.blank_back"
    out = tmp_path / "out"
    rep = render_paper(c, out, salts=salts, preview=False)
    for n, env in enumerate(rep.envelopes, 1):
        rows = [r for r in rep.rows if r.stage == n]
        expected: list[str] = []
        starts = []
        for k, r in enumerate(rows):
            starts.append(len(expected))
            expected += _page_texts(r.pdf)
            if k < len(rows) - 1 and r.pages % 2:
                expected.append(note)
        got = _page_texts(env)
        assert got == expected, env
        assert all(x % 2 == 0 for x in starts)  # документ — с лицевой стороны листа
        # лист дела: k-й документ начинается с листа starts/2 + 1
        for k, r in enumerate(rows):
            assert _sheet_no(env, starts[k]) == str(starts[k] // 2 + 1), (env, r.id)
    by_id = {r.id: r for r in rep.rows}
    assert by_id["2-02"].pages == 2 and by_id["2-04"].pages == 1 and by_id["2-04"].blanks == 0


def test_render_protocol_sections_duplex(chromium, root, salts, tmp_path):
    """Протокол с разделами «## …»: каждый раздел — отдельная часть со своей «Лист 1» и с лицевой
    страницы (duplex); метка <!-- person: id --> даёт фото из media/portraits, если файл есть."""
    from engine.paper import doc_data

    body = ("Вступление.\n\n## 1. Первый\n<!-- person: zavyalov -->\n\nТекст первого.\n\n"
            "<div class=\"page-break\"></div>\n\nПродолжение первого.\n\n"
            "## 2. Второй\n<!-- person: nobody_x -->\n\nТекст второго.\n\n"
            "## 3. Третий\n\nТекст третьего.\n")
    write_paper(root, "2-02", 'id: "2-02"\nform: protocol', body=body)
    c = load_content(root)
    _set_duplex(c, True)
    d = doc_data(c, "2-02", make_context(c), media_dir=ROOT / "media")
    assert [s["n"] for s in d["sections"]] == [1, 2, 3]
    assert d["sections"][0]["person"]["id"] == "zavyalov" and d["sections"][2]["person"] is None
    assert d["persons_unknown"] == ["nobody_x"] and "Вступление" in d["intro_html"]
    rep = render_paper(c, tmp_path, salts=salts, only=["2-02"], preview=False, media_dir=ROOT / "media")
    row = rep.rows[0]
    texts = _page_texts(row.pdf)
    # 1-й протокол — 2 страницы, 2-й — 1 + оборот, 3-й — 1 (в конце оборот не нужен)
    assert row.pages == 5 and row.blanks == 1, texts
    assert "Вступление" in texts[0] and "Продолжение первого" in texts[1] and "Текст второго" in texts[2]
    assert texts[3] == c.settings.print.blank_back and "Текст третьего" in texts[4]
    assert _has_sheet(texts[2], 1) and _has_sheet(texts[4], 1)  # у каждого протокола свой «Лист 1»
    assert "Вступление" not in texts[2]
    assert "нет персонажа: person: nobody_x" in row.status
    with pytest.raises(PaperError) as exc:
        render_paper(c, tmp_path, salts=salts, only=["2-02"], release=True, media_dir=ROOT / "media")
    assert any("person: nobody_x" in p for p in exc.value.problems)
    if (ROOT / "media" / "portraits" / "zavyalov.jpg").is_file():
        html = (ROOT / "media" / "portraits" / "zavyalov.jpg").as_uri()
        assert d["sections"][0]["person"]["src"] == html


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


def test_release_command_fails_on_missing_paper(root, tmp_path):
    """``python -m engine release``: бумажный документ без текста — ошибка (как TODO(content))."""
    from engine.release import ReleaseError, release

    with pytest.raises(ReleaseError) as exc:
        release(content_dir=root, media_dir=tmp_path / "media", dist=tmp_path / "dist",
                salts_path=tmp_path / "salts.json", out_dir=tmp_path / "print")
    assert "нет текста бумажного документа content/paper/2-05.md" in str(exc.value)


def test_no_pypdf_clear_error(content, salts, tmp_path, monkeypatch):
    """Нет pypdf — понятная ошибка с подсказкой до запуска браузера, ничего не напечатано."""
    import sys

    from engine.printing import PrintError

    monkeypatch.setitem(sys.modules, "pypdf", None)  # import pypdf → ImportError
    with pytest.raises(PrintError) as exc:
        render_paper(content, tmp_path / "out", salts=salts, preview=False)
    assert "pypdf" in str(exc.value) and 'pip install -e ".[dev]"' in str(exc.value)
    assert not list((tmp_path / "out").glob("*.pdf"))


def test_paper_may_quote_open_page(root, tmp_path):
    """Бумага конверта 1 цитирует строку открытой страницы (как отрендерил build) — не утечка; уникальная
    фраза бумаги конверта 3, подложенная в dist/, — утечка. Бумагу конверта 3 открытая страница не отбеливает:
    та же цитата в ней — иголка (docs/02 §5а)."""
    from engine.build import prepare
    from engine.check import page_text
    from engine.leakscan import is_stop_shingle, text_shingles

    salts = tmp_path / "salts.json"
    dist = tmp_path / "dist"
    media = tmp_path / "media"
    build(content_dir=root, dist=dist, salts_path=salts, media_dir=media)
    ns0 = leak_needles(prepare(root, salts, create_salts=False), media_dir=media)
    page = page_text((dist / "p" / "gromov" / "index.html").read_text(encoding="utf-8"))
    quotes = sorted(sh for sh in text_shingles(page) - ns0.exclude if not is_stop_shingle(sh))
    assert quotes, "на открытой странице gromov нет текста сверх «обвязки»"
    quote = quotes[0]  # шингл только из открытой отрендеренной страницы (не из public_texts контента)
    unique = "Поезд отправился с третьего пути без опоздания"
    write_paper(root, "1-03", 'id: "1-03"\nform: ambulance', body=f"{quote}.\n")
    write_paper(root, "3-07", 'id: "3-07"\nform: ticket', body=f"{unique}.\n")
    build(content_dir=root, dist=dist, salts_path=salts, media_dir=media)
    ns = leak_needles(prepare(root, salts, create_salts=False), media_dir=media)
    assert quote not in ns.shingles
    assert any(nd.kind == "paper" and nd.source == "content/paper/3-07.md" for nd in ns.shingles.values())
    # та же цитата в бумаге конверта 3: открытая страница её не отбеливает
    write_paper(root, "3-07", 'id: "3-07"\nform: ticket', body=f"{quote}.\n\n{unique}.\n")
    nd3 = leak_needles(prepare(root, salts, create_salts=False), media_dir=media).shingles.get(quote)
    assert nd3 is not None and nd3.kind == "paper" and nd3.source == "content/paper/3-07.md"
    write_paper(root, "3-07", 'id: "3-07"\nform: ticket', body=f"{unique}.\n")
    rep = check(content_dir=root, dist=dist, salts_path=salts, media_dir=media)
    assert rep.ok, rep.problems
    (dist / "quote.html").write_text(f"<p>{quote}</p>", encoding="utf-8")
    assert check(content_dir=root, dist=dist, salts_path=salts, media_dir=media).ok
    (dist / "leak-paper.html").write_text(f"<p>{unique}</p>", encoding="utf-8")
    rep = check(content_dir=root, dist=dist, salts_path=salts, media_dir=media)
    assert not rep.ok
    probs = [p for p in rep.problems if p.startswith("[7.")]
    assert probs and all("leak-paper.html" in p and "content/paper/3-07.md" in p for p in probs), probs
