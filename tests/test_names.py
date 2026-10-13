"""Склонение ФИО и объект персонажа в шаблонах."""

from __future__ import annotations

import subprocess
import sys

import pytest

from engine import ROOT
from engine.content import load_content
from engine.models import CASES, Character
from engine.names import NBSP, DeclensionError, Person, decline, format_names_table, names_table
from engine.templating import RenderError, make_context, render


def ch(**kw) -> Character:
    base = dict(id="x", working="x", role="роль", importance="key", last="Завьялов", first="Юрий",
                middle="Викторович", gender="m")
    base.update(kw)
    return Character.model_validate(base)


def test_names_table_all_characters():
    c = load_content()
    rows = names_table(c.characters)
    assert len(rows) == 3 * len(c.characters)
    for r in rows:
        assert set(r["forms"]) == set(CASES)
        assert all(isinstance(v, str) for v in r["forms"].values())
    text = format_names_table(c.characters)
    for character in c.characters:
        assert character.id in text


def test_known_forms():
    p = Person(ch())
    assert p.full("gen") == "Завьялова Юрия Викторовича"
    assert p.full("ins") == "Завьяловым Юрием Викторовичем"
    assert p.io() == "Юрий Викторович"
    assert p.first("dat") == "Юрию"
    assert p.last("ins") == "Завьяловым"
    assert p.middle("pre") == "Викторовиче"
    f = Person(ch(last="Гнедич", first="Елена", middle="Михайловна", gender="f"))
    assert f.full("dat") == "Гнедич Елене Михайловне"  # женская «Гнедич» не склоняется
    v = Person(ch(last="Кузнецов", first="Виктор", middle="Ильич"))
    assert v.middle("ins") == "Ильичом"


def test_short_nbsp():
    p = Person(ch())
    assert p.short() == f"Завьялов{NBSP}Ю.{NBSP}В."
    assert p.short("gen") == f"Завьялова{NBSP}Ю.{NBSP}В."
    assert Person(ch(middle=None)).short() == f"Завьялов{NBSP}Ю."
    assert Person(ch(first="Анна-Мария", gender="f", last="Петрова", middle="")).short() == f"Петрова{NBSP}А.-М."


def test_empty_parts_are_skipped():
    p = Person(ch(middle=None))
    assert p.full() == "Завьялов Юрий"
    assert p.full("gen") == "Завьялова Юрия"
    assert p.io() == "Юрий"
    assert p.middle("gen") == ""
    assert "  " not in Person(ch(middle="")).full("dat")


def test_todo_names_do_not_fail():
    p = Person(ch(last="TODO(content)", first="TODO(content)", middle="", gender="f"))
    for case in CASES:
        assert p.full(case) == "TODO(content) TODO(content)"


def test_manual_forms_override():
    p = Person(ch(forms={"last": {"gen": "Завьялова-ручная"}, "first": {"nom": "Юра"}}))
    assert p.last("gen") == "Завьялова-ручная"
    assert p.last("dat") == "Завьялову"
    assert p.first() == "Юра"
    rows = names_table([ch(forms={"last": {"gen": "Ручная"}})])
    assert rows[0]["manual"] == ["gen"]
    assert "Ручная*" in format_names_table([ch(forms={"last": {"gen": "Ручная"}})])


def test_forms_schema_rejects_bad_case():
    with pytest.raises(Exception):
        ch(forms={"last": {"genitive": "x"}})


def test_gender_helper_and_fields():
    m, f = Person(ch()), Person(ch(gender="f", last="Тарасова", first="Марина", middle="Олеговна", age=52))
    assert m.g("ушёл", "ушла") == "ушёл"
    assert f.g("ушёл", "ушла") == "ушла"
    assert f.age == 52 and f.role == "роль" and f.id == "x" and m.nick is None


def test_decline_validation():
    assert decline("middle", None, "m", "gen") == ""
    with pytest.raises(DeclensionError):
        decline("last", "Иванов", "m", "abl")
    with pytest.raises(DeclensionError):
        decline("last", "Иванов", "x", "gen")


def test_template_person_errors():
    ctx = make_context(characters=[ch(id="zavyalov")], world={"city": "Город", "theater": {"short": "ВОДТ"}})
    assert render("{{ c.zavyalov.full('acc') }} — {{ w.city }}", ctx) == "Завьялова Юрия Викторовича — Город"
    with pytest.raises(RenderError, match="нет атрибута «fulll»"):
        render("{{ c.zavyalov.fulll() }}", ctx, "f.yaml: x")
    with pytest.raises(RenderError, match="нет ключа «w.theater.items»"):
        render("{{ w.theater.items }}", ctx)
    with pytest.raises(RenderError, match="раздел world.yaml"):
        render("{{ w.theater }}", ctx)
    with pytest.raises(RenderError, match="is undefined"):
        render("{{ x }}", ctx)
    with pytest.raises(RenderError, match="^f.yaml: hints\\[0\\]: ошибка шаблона"):
        render("{{ c.nobody.short() }}", ctx, "f.yaml: hints[0]")


def test_sandbox_blocks_internals():
    ctx = make_context(characters=[ch(id="zavyalov")], world={})
    with pytest.raises(RenderError):
        render("{{ c.zavyalov.__class__.__mro__ }}", ctx)


def test_cli_names():
    res = subprocess.run([sys.executable, "-m", "engine", "names"], cwd=ROOT, capture_output=True, timeout=60)
    assert res.returncode == 0, res.stderr.decode("utf-8", "replace")
    out = res.stdout.decode("utf-8")
    assert "Завьялова" in out and "Гнедич" in out and "TODO(content)" in out
