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
    persons = {c.id: Person(c) for c in load_content().characters}
    for cid in ("zavyalov", "paramedic"):
        assert persons[cid].last("gen") in out


# ---------------------------------------------------------------- фамилия и отчество от отца

from engine.names import DERIVED_MARK, patronymic_for, surname_for  # noqa: E402

PATRONYMICS = [
    # имя отца, мужское, женское
    ("Иван", "Иванович", "Ивановна"),
    ("Олег", "Олегович", "Олеговна"),
    ("Константин", "Константинович", "Константиновна"),
    ("Виктор", "Викторович", "Викторовна"),
    ("Артём", "Артёмович", "Артёмовна"),
    ("Даниил", "Даниилович", "Данииловна"),
    ("Сергей", "Сергеевич", "Сергеевна"),
    ("Андрей", "Андреевич", "Андреевна"),
    ("Алексей", "Алексеевич", "Алексеевна"),
    ("Матвей", "Матвеевич", "Матвеевна"),
    ("Тимофей", "Тимофеевич", "Тимофеевна"),
    ("Николай", "Николаевич", "Николаевна"),
    ("Евгений", "Евгеньевич", "Евгеньевна"),
    ("Аркадий", "Аркадьевич", "Аркадьевна"),
    ("Анатолий", "Анатольевич", "Анатольевна"),
    ("Юрий", "Юрьевич", "Юрьевна"),
    ("Виталий", "Витальевич", "Витальевна"),
    ("Геннадий", "Геннадьевич", "Геннадьевна"),
    ("Валерий", "Валерьевич", "Валерьевна"),
    ("Василий", "Васильевич", "Васильевна"),
    ("Григорий", "Григорьевич", "Григорьевна"),
    ("Арсений", "Арсеньевич", "Арсеньевна"),
    ("Дмитрий", "Дмитриевич", "Дмитриевна"),
    ("Георгий", "Георгиевич", "Георгиевна"),
    ("Игорь", "Игоревич", "Игоревна"),
    ("Илья", "Ильич", "Ильинична"),
    ("Никита", "Никитич", "Никитична"),
    ("Фома", "Фомич", "Фоминична"),
    ("Кузьма", "Кузьмич", "Кузьминична"),
    ("Лука", "Лукич", "Лукинична"),
    ("Савва", "Саввич", "Саввична"),
    ("Павел", "Павлович", "Павловна"),
    ("Лев", "Львович", "Львовна"),
    ("Пётр", "Петрович", "Петровна"),
    ("Петр", "Петрович", "Петровна"),
    ("Яков", "Яковлевич", "Яковлевна"),
    ("Михаил", "Михайлович", "Михайловна"),
]


@pytest.mark.parametrize(("name", "m", "f"), PATRONYMICS)
def test_patronymic_for(name, m, f):
    assert patronymic_for(name, "m") == m
    assert patronymic_for(name, "f") == f


def test_patronymic_for_count():
    assert len(PATRONYMICS) >= 30


@pytest.mark.parametrize("name", ["Шота", "Миша", "Марко", "Ли", "Анна-Мария", "иван", "Ivan", "",
                                  "TODO(content)", "Иван Петрович"])
def test_patronymic_for_unknown_raises(name):
    with pytest.raises(DeclensionError, match="укажите отчество вручную в forms"):
        patronymic_for(name, "m")


SURNAMES = [
    # мужская, женская
    ("Воронцов", "Воронцова"),
    ("Беляев", "Беляева"),
    ("Королёв", "Королёва"),
    ("Пушкин", "Пушкина"),
    ("Лёвин", "Лёвина"),
    ("Солженицын", "Солженицына"),
    ("Достоевский", "Достоевская"),
    ("Вольский", "Вольская"),
    ("Высоцкий", "Высоцкая"),
    ("Римский-Корсаков", "Римская-Корсакова"),
    ("ИВАНОВ", "ИВАНОВА"),
]
SURNAMES_FIXED = ["Гнедич", "Шевченко", "Черных", "Долгих", "Гоголь", "Дюма", "Цой", "Толстой", "Ов", "Мельник"]


@pytest.mark.parametrize(("m", "f"), SURNAMES)
def test_surname_for(m, f):
    assert surname_for(m, "f") == f
    assert surname_for(m, "m") == m
    assert surname_for(f, "m", source_gender="f") == m
    assert surname_for(f, "f", source_gender="f") == f


@pytest.mark.parametrize("last", SURNAMES_FIXED)
def test_surname_for_unchanged(last):
    assert surname_for(last, "f") == last
    assert surname_for(last, "m", source_gender="f") == last


def test_surname_for_skoy_and_bad_gender():
    assert surname_for("Трубецкой", "f") == "Трубецкая"
    assert surname_for("Луговской", "f") == "Луговская"
    assert surname_for("", "f") == ""
    with pytest.raises(DeclensionError):
        surname_for("Иванов", "x")
    with pytest.raises(DeclensionError):
        patronymic_for("Иван", "x")


def test_names_table_marks_derived():
    father = ch(id="dad", last="Воронцов", first="Иван", middle="Сергеевич", familiar="Ваня")
    kid = ch(id="kid", last="Воронцова", first="Марина", middle="Ивановна", gender="f", father="dad")
    rows = {(r["id"], r["part"]): r for r in names_table([father, kid])}
    assert rows[("kid", "last")]["derived"] and rows[("kid", "middle")]["derived"]
    assert not rows[("kid", "first")]["derived"] and not rows[("dad", "last")]["derived"]
    text = format_names_table([father, kid])
    assert f"last {DERIVED_MARK}" in text and f"middle {DERIVED_MARK}" in text
    assert "familiar: Ваня" in text and f"{DERIVED_MARK} father: dad" in text


def test_new_character_fields_schema():
    c = ch()
    assert c.father is None and c.familiar is None and c.cast is True
    assert ch(cast=False).cast is False
    with pytest.raises(Exception):
        ch(familiar="  ")
    with pytest.raises(Exception):
        ch(father="Bad Id")
    with pytest.raises(Exception):
        ch(cast="нет")


def test_template_familiar():
    ctx = make_context(characters=[ch(id="dad", familiar="Ваня"), ch(id="kid")], world={})
    assert render("{{ c.dad.familiar }}, привет", ctx) == "Ваня, привет"
    with pytest.raises(RenderError, match="у персонажа «kid» нет familiar"):
        render("{{ c.kid.familiar }}", ctx, "x.yaml: a")
