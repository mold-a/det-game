"""Блок «Спасибо за игру» (finale.thanks): сборка финала с полем и без него, шифрование, leak scan, валидация."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from engine import ROOT, crypto
from engine.build import build, prepare
from engine.check import check
from engine.content import ContentError, load_content

CONTENT = ROOT / "content"
THANKS = {
    "title": "Спасибо за игру, {{ w.play.title }}",
    "text": "Первый абзац благодарности.\n\nВторой абзац, совсем другой.",
    "signature": "Автор игры, уникальная подпись-проверка",
}


def make_content(tmp_path: Path, thanks: dict | None) -> Path:
    root = tmp_path / "content"
    shutil.copytree(CONTENT, root)
    p = root / "finale.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    data.pop("thanks", None)
    if thanks is not None:
        data["thanks"] = thanks
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10_000), encoding="utf-8")
    return root


def build_and_open(tmp_path: Path, thanks: dict | None):
    content = make_content(tmp_path, thanks)
    salts = tmp_path / "salts.lock.json"
    shutil.copyfile(ROOT / "engine" / "salts.lock.json", salts)
    dist = tmp_path / "dist"
    build(content_dir=content, dist=dist, salts_path=salts, media_dir=ROOT / "media", log=lambda *_: None)
    prep = prepare(content, salts, create_salts=False)
    box = json.loads((dist / "data" / "finale.json").read_text(encoding="utf-8"))
    key = crypto.hkdf(prep.keys[prep.content.last_stage], crypto.FINALE_INFO)
    fin = json.loads(crypto.open_(key, box, "finale").decode("utf-8"))
    return content, dist, salts, fin


def test_finale_with_thanks(tmp_path):
    content, dist, salts, fin = build_and_open(tmp_path, THANKS)
    assert set(fin["thanks"]) == {"title", "text", "signature"}
    assert fin["thanks"]["title"].startswith("Спасибо за игру, ") and "{{" not in fin["thanks"]["title"]  # шаблон отрендерен
    assert fin["thanks"]["text"] == THANKS["text"] and fin["thanks"]["signature"] == THANKS["signature"]
    rep = check(content_dir=content, dist=dist, salts_path=salts, media_dir=ROOT / "media")
    assert rep.ok, rep.problems
    # блок только в зашифрованном виде: открытого текста нигде в dist/ нет
    for p in dist.rglob("*"):
        if p.is_file() and p.suffix in {".json", ".html", ".js", ".css"}:
            assert THANKS["signature"] not in p.read_text(encoding="utf-8", errors="ignore"), p


def test_finale_without_thanks(tmp_path):
    content, dist, salts, fin = build_and_open(tmp_path, None)
    assert "thanks" not in fin and fin["fates"]
    rep = check(content_dir=content, dist=dist, salts_path=salts, media_dir=ROOT / "media")
    assert rep.ok, rep.problems


def test_thanks_text_is_leak_scanned(tmp_path):
    """Текст thanks — часть закрытой развязки: leak scan ловит его на открытой странице."""
    from tests.test_leak_open_pages import ANCHOR, PAGE  # noqa: PLC0415

    sentence = "Эта благодарность не должна встретиться ни на одной открытой странице сайта."
    content = make_content(tmp_path, {**THANKS, "text": sentence})
    page = content / PAGE
    text = page.read_text(encoding="utf-8")
    page.write_text(text.replace(ANCHOR, f'text: "{sentence}\\n' + ANCHOR[len('text: "'):], 1), encoding="utf-8")
    salts = tmp_path / "salts.lock.json"
    shutil.copyfile(ROOT / "engine" / "salts.lock.json", salts)
    dist = tmp_path / "dist"
    build(content_dir=content, dist=dist, salts_path=salts, media_dir=ROOT / "media", log=lambda *_: None)
    rep = check(content_dir=content, dist=dist, salts_path=salts, media_dir=ROOT / "media")
    assert not rep.ok and any("thanks.text" in p for p in rep.problems), rep.problems


@pytest.mark.parametrize("missing", ["title", "text", "signature"])
def test_thanks_requires_all_fields(tmp_path, missing):
    bad = {k: v for k, v in THANKS.items() if k != missing}
    root = make_content(tmp_path, bad)
    with pytest.raises(ContentError) as exc:
        load_content(root)
    assert any("finale.yaml" in str(e) and f"thanks.{missing}" in str(e) for e in exc.value.errors), exc.value.errors


def test_thanks_template_error_is_reported(tmp_path):
    root = make_content(tmp_path, {**THANKS, "title": "{{ c.marina.g('Уехал', 'Уехала' }}"})
    with pytest.raises(ContentError) as exc:
        load_content(root)
    assert any("finale.yaml" in str(e) and "thanks" in str(e) for e in exc.value.errors), exc.value.errors


def test_thanks_unknown_field_is_rejected(tmp_path):
    root = make_content(tmp_path, {**THANKS, "footer": "лишнее"})
    with pytest.raises(ContentError):
        load_content(root)
