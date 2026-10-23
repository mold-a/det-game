"""Имена персонажей буквами в текстах content/ (docs/06 §3 п.10, engine/hardnames.py)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from engine import ROOT
from engine.build import build
from engine.check import check
from engine.content import load_content
from engine.hardnames import COMMON_WORD_NAMES, familiar_collisions, hardcoded_names
from engine.models import Character

CONTENT = ROOT / "content"


def ch(cid: str, last: str, first: str, middle: str, gender: str = "m", **kw) -> Character:
    return Character(id=cid, working=f"{first} {last}", role="роль", importance="key",
                     last=last, first=first, middle=middle, gender=gender, **kw)


CAST = [
    ch("voroncov", "Воронцов", "Иван", "Сергеевич", familiar="Ваня"),
    ch("zavyalov", "Завьялов", "Юрий", "Викторович"),
    ch("stas", "Лёвин", "Станислав", "Игоревич"),
    ch("volkov", "Волков", "Артём", "Андреевич"),
    ch("sister", "Воронцова", "Вера", "Ивановна", "f"),
    ch("witness", "Гусева", "Нина", "Алексеевна", "f"),
    ch("kovalev", "Ковалёв", "Денис", "Олегович", cast=False),
    ch("fake", "Сабиров", "Юрий", "Альбертович", cast=False),
    ch("todo", "TODO(content)", "Пантелеймон", ""),
]
WORLD = {"play": {"role_nina": "Нина", "role_main": "Арбенин"}}


def scan(tmp_path: Path, files: dict[str, str], characters=CAST, world=WORLD):
    root = tmp_path / "content"
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return hardcoded_names(root, characters, world)


def found(hits) -> list[tuple[str, int, str]]:
    return [(h.file, h.line, h.found) for h in hits]


def test_finds_names_in_paper_body(tmp_path):
    hits = scan(tmp_path, {"paper/1-08.md": (
        "---\nid: \"1-08\"\nform: protocol\n---\n"
        "**Ответ:** Иван Сергеевич меня избегал.\n"
        "Встречался с Завьяловым, потом позвонил Ване.\n"
        "Все звали его Ваня.\n"
    )})
    assert found(hits) == [
        ("content/paper/1-08.md", 5, "Иван Сергеевич"),
        ("content/paper/1-08.md", 6, "Завьяловым"),
        ("content/paper/1-08.md", 6, "Ване"),
        ("content/paper/1-08.md", 7, "Ваня"),
    ]
    assert hits[0].suggestions == ("{{ c.voroncov.io() }}",)
    assert hits[1].suggestions == ("{{ c.zavyalov.last('ins') }}",)
    assert hits[3].suggestions == ("{{ c.voroncov.familiar }}",)
    assert str(hits[0]) == "content/paper/1-08.md:5: найдено «Иван Сергеевич» → {{ c.voroncov.io() }}"


def test_longest_match_and_ambiguity(tmp_path):
    hits = scan(tmp_path, {"documents/2-01.md": (
        "Воронцов Иван Сергеевич умер. Звонил Ивану Воронцову.\n"
        "Дочь — Воронцова.\n"
    )})
    assert [h.found for h in hits] == ["Воронцов Иван Сергеевич", "Ивану Воронцову", "Воронцова"]
    assert hits[0].suggestions == ("{{ c.voroncov.full() }}",)
    assert hits[1].replacement == "{{ c.voroncov.first('dat') }} {{ c.voroncov.last('dat') }}"
    # «Воронцова» — и родительный/винительный Воронцова, и именительный его дочери
    assert hits[2].suggestions == ("{{ c.voroncov.last('gen') }} (или 'acc')", "{{ c.sister.last() }}")


def test_yo_and_e_are_equal(tmp_path):
    hits = scan(tmp_path, {"stages.yaml": 'a: "Левин и Артем Волков"\n'})
    assert [h.found for h in hits] == ["Левин", "Артем Волков"]
    assert hits[0].suggestions == ("{{ c.stas.last() }}",)


def test_jinja_breaks_combination(tmp_path):
    hits = scan(tmp_path, {"paper/1-03.md": "Юрий {{ c.zavyalov.middle() }} Завьялов\n"})
    assert [h.found for h in hits] == ["Юрий", "Завьялов"]


def test_not_found_inside_jinja(tmp_path):
    hits = scan(tmp_path, {
        "paper/1-01.md": (
            "{{ c.voroncov.io() }} и {{ c.x.g('Иван Сергеевич', 'Завьялов') }}\n"
            "{% set who = 'Завьялов' %}{# Ваня — в комментарии шаблона #}\n"
            "{{ c.zavyalov.first()\n  }} без имён\n"
        ),
        "finale.yaml": "text: \"{{ c.voroncov.last('gen') }} — {{ 'Воронцов' }}\"\n",
    })
    assert hits == []


def test_yaml_comments_and_keys_skipped(tmp_path):
    hits = scan(tmp_path, {
        "stages.yaml": (
            "# Иван Сергеевич — в комментарии\n"
            "Завьялов: значение без имён   # Ваня\n"
            "list:\n"
            "  - \"строка # Волков\"   # Завьялов\n"
            "  - text: |   # Ваня в заголовке блока\n"
            "      Первая строка.\n"
            "      # не комментарий: Ваня\n"
        ),
        "paper/1-02.md": "---\nid: \"1-02\"\nЗавьялов: x\ntitle: \"Протокол Завьялова\"\n---\nТело.\n",
    })
    assert sorted(found(hits)) == [
        ("content/paper/1-02.md", 4, "Завьялова"),   # значение front matter — сканируется, ключ — нет
        ("content/stages.yaml", 4, "Волков"),        # «#» внутри кавычек — не комментарий
        ("content/stages.yaml", 7, "Ваня"),          # в блочном скаляре «#» — текст
    ]


def test_exceptions(tmp_path):
    assert "вера" in COMMON_WORD_NAMES
    hits = scan(tmp_path, {"paper/2-08.md": (
        "Вера в победу. Нина, Баронесса. Роль Нины.\n"   # обычное слово и роль из world.yaml
        "Стая волков у дороги.\n"                        # строчная — обычное слово, не фамилия
        "Вера Ивановна и Нина Алексеевна пришли.\n"      # сочетания проверяются строже
        "Пантелеймон пришёл.\n"                          # фамилия — заглушка, имя проверяется
        "TODO(content): Иван Сергеевич?\n"               # строка с заглушкой не считается
    )})
    assert found(hits) == [
        ("content/paper/2-08.md", 3, "Вера Ивановна"),
        ("content/paper/2-08.md", 3, "Нина Алексеевна"),
        ("content/paper/2-08.md", 4, "Пантелеймон"),
    ]


def test_cast_false_skipped(tmp_path):
    hits = scan(tmp_path, {"chats/3-03.yaml": (
        "messages:\n"
        "  - text: \"Ковалёв Денис Олегович, сержант. Позвоните Ковалёву.\"\n"
        "  - text: \"Сабиров Юрий Альбертович, понятой\"\n"   # ФИО вымышленного — целиком, «Юрий» не ловится
        "  - text: \"Юрий пришёл\"\n"                         # одиночное имя есть и у cast: true
    )})
    assert found(hits) == [("content/chats/3-03.yaml", 4, "Юрий")]
    assert hits[0].suggestions == ("{{ c.zavyalov.first() }}",)


def test_scanned_files_only(tmp_path):
    hits = scan(tmp_path, {
        "characters.yaml": "x: Завьялов\n",
        "world.yaml": "x: Завьялов\n",
        "settings.yaml": "x: Завьялов\n",
        "pages/inna/page.yaml": "body: Завьялов\n",
        "pages/news/article.md": "Завьялов\n",
        "documents.yaml": "documents:\n  - title: Справка о Завьялове\n",
    })
    assert sorted(found(hits)) == [
        ("content/documents.yaml", 2, "Завьялове"),
        ("content/pages/inna/page.yaml", 1, "Завьялов"),
        ("content/pages/news/article.md", 1, "Завьялов"),
    ]


def test_check_warns_and_release_fails(tmp_path):
    cdir = tmp_path / "content"
    shutil.copytree(CONTENT, cdir)
    paper = sorted((cdir / "paper").glob("*.md"))[0]
    zav = next(c for c in load_content(CONTENT).characters if c.id == "zavyalov")
    full = f"{zav.last} {zav.first} {zav.middle}"
    paper.write_text(paper.read_text(encoding="utf-8") + f"\n{full}\n", encoding="utf-8")
    kw = dict(content_dir=cdir, dist=tmp_path / "dist", salts_path=tmp_path / "salts.json")
    build(**kw)
    rep = check(**kw)
    row = next(r for r in rep.rows if r.name.startswith("10."))
    assert row.ok and rep.ok
    assert any(f"«{full}» → {{{{ c.zavyalov.full() }}}}" in w for w in rep.warnings)
    assert "Предупреждения" in rep.table()
    rep = check(**kw, release=True)
    row = next(r for r in rep.rows if r.name.startswith("10."))
    assert not row.ok
    assert any(p.startswith("[10. Имена буквами] content/paper/") and full in p
               for p in rep.problems)


@pytest.mark.parametrize("cid", [c.id for c in CAST if c.cast and c.id != "todo"])
def test_every_case_form_found(tmp_path, cid):
    from engine.models import CASES
    from engine.names import Person

    p = Person(next(c for c in CAST if c.id == cid))
    text = "\n".join(f"Текст: {p.full(case)}." for case in CASES) + "\n"
    hits = scan(tmp_path, {"finale.yaml": f"t: |\n" + "".join(f"  {ln}\n" for ln in text.splitlines())})
    assert [h.line for h in hits] == list(range(2, 2 + len(CASES)))
    assert all(h.replacement.startswith(f"{{{{ c.{cid}.full(") for h in hits)


def test_familiar_collision_with_other_first_name():
    # S-62: «Тёма» у погибшего при дублёре-«Артёме» — ложная улика
    cast = [ch("voroncov", "Воронцов", "Иван", "Сергеевич", familiar="Тёма"),
            ch("volkov", "Волков", "Артём", "Андреевич")]
    clash = familiar_collisions(cast)
    assert len(clash) == 1 and "voroncov.familiar «Тёма»" in clash[0] and "volkov «Артём»" in clash[0]
    # своё имя не в счёт; «Ваня» ни на кого из CAST не похоже
    assert familiar_collisions([ch("voroncov", "Молдованов", "Артём", "Сергеевич", familiar="Тёма"),
                                ch("volkov", "Блинов", "Вячеслав", "Иванович")]) == []
    assert familiar_collisions(CAST) == []
