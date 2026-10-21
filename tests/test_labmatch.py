"""Распознавание объекта лаборатории (docs/02, engine/labmatch.py): общие векторы + отдельные случаи.

Те же векторы читает tests/js/labmatch.test.mjs — паритет Python и JS.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.labmatch import (
    STEM_MIN,
    TITLE_STEM_MIN,
    alias_stems,
    best_match,
    lab_tokens,
    match_stems,
    norm,
    resolve_object,
    title_stems,
)
from engine.vectors import render_lab_match_vectors

VECTORS_PATH = Path(__file__).parent / "vectors" / "lab-match.json"
V = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def obj(id_: str, title: str, *aliases: str) -> dict:
    return {"id": id_, "title": title, "aliases": list(aliases)}


def test_vectors_file_is_up_to_date_and_deterministic():
    first = render_lab_match_vectors()
    assert first == render_lab_match_vectors()
    assert VECTORS_PATH.read_text(encoding="utf-8") == first, "перегенерируйте: python -m engine vectors"


def test_vectors_cover_all_statuses_and_enough_cases():
    statuses = {c["expected"]["status"] for c in V["resolve"]}
    assert statuses == {"ok", "ambiguous", "none"}
    assert len(V["resolve"]) >= 40 and len(V["tokens"]) >= 8
    assert {c["catalog"] for c in V["resolve"]} <= set(V["catalogs"])


@pytest.mark.parametrize("case", V["tokens"], ids=lambda c: repr(c["input"]))
def test_tokens_vectors(case):
    assert lab_tokens(case["input"]) == case["tokens"]


@pytest.mark.parametrize("case", V["resolve"], ids=lambda c: f"{c['catalog']}:{c['input']!r}")
def test_resolve_vectors(case):
    assert resolve_object(case["input"], V["catalogs"][case["catalog"]]) == case["expected"], case["note"]


# --- нормализация


def test_norm_reuses_text_normalization():
    from engine.normalize import normalize

    for s in ["Ёлка, ёж!", "  ", "", "Ключи — из кармана пальто", "за́мок"]:
        assert norm(s) == (normalize("text", s) or "")


def test_tokens_punctuation_yo_and_empty():
    assert lab_tokens("") == []
    assert lab_tokens("  ?!  ") == []
    assert lab_tokens("«Гримёрка» № 4, —  бутылка!") == ["гримерка", "4", "бутылка"]


# --- алгоритм


def test_stem_matches_prefix_of_token_only():
    assert match_stems(["ключ"], ["ключи"]) == (0, -4)
    assert match_stems(["ключи"], ["ключ"]) is None
    assert match_stems(["люч"], ["ключи"]) is None  # основа — начало токена, не подстрока


def test_each_token_is_used_once_repeated_stem_needs_two_tokens():
    assert match_stems(["бут", "бут"], ["бутылка"]) is None
    assert match_stems(["бут", "бут"], ["бутылка", "бутон"]) == (0, -6)
    assert match_stems(["бут", "бут"], ["чай", "бутылка", "бутон"]) == (1, -6)


def test_stem_takes_earliest_free_token_and_pos_is_minimum():
    # «камер» берёт токен 0, «вокзал» — токен 2
    assert match_stems(["камер", "вокзал"], ["камера", "и", "вокзала"]) == (0, -11)
    # порядок основ не важен: «вокзал» берёт токен 0, «камер» — токен 1; pos = 0
    assert match_stems(["камер", "вокзал"], ["вокзал", "камера"]) == (0, -11)
    # первая основа занимает токен, нужный второй: «а» и «аб» на «абв абг»
    assert match_stems(["а", "аб"], ["абв", "абг"]) == (0, -3)


def test_empty_alias_never_matches():
    assert match_stems([], ["любой"]) is None
    assert alias_stems("") == []
    assert alias_stems("  бутыл   вод ") == ["бутыл", "вод"]


def test_title_is_an_alias_of_tokens_not_shorter_than_min():
    assert TITLE_STEM_MIN == STEM_MIN == 3
    assert title_stems("Бутылка воды из гримёрки № 4") == ["бутылка", "воды", "гримерки"]
    assert title_stems("а б") == []
    assert best_match(obj("x", "а б"), ["а", "б"]) is None


def test_title_recognises_itself():
    objects = [obj("water", "Бутылка воды из гримёрки № 4"), obj("phone", "Телефон погибшего")]
    assert resolve_object("Бутылка воды из гримёрки № 4", objects) == {"status": "ok", "id": "water"}
    assert resolve_object("Телефон погибшего", objects) == {"status": "ok", "id": "phone"}


def test_key_pos_then_score():
    keys = obj("keys", "Связка ключей", "ключ")
    coat = obj("coat", "Пальто серое", "пальто")
    assert resolve_object("ключи из кармана пальто", [keys, coat]) == {"status": "ok", "id": "keys"}
    assert resolve_object("ключи из кармана пальто", [coat, keys]) == {"status": "ok", "id": "keys"}
    assert resolve_object("пальто, ключи", [keys, coat]) == {"status": "ok", "id": "coat"}


def test_score_breaks_ties_at_same_pos():
    a = obj("a", "Аа", "бутылк")
    b = obj("b", "Бб", "бутылк вод")
    assert resolve_object("бутылка воды", [a, b]) == {"status": "ok", "id": "b"}
    assert resolve_object("бутылка", [a, b]) == {"status": "ok", "id": "a"}


def test_ambiguous_ids_in_catalog_order():
    objs = [obj("z", "Зз", "кув"), obj("a", "Аа", "кув"), obj("m", "Мм", "кув")]
    assert resolve_object("кувшин", objs) == {"status": "ambiguous", "ids": ["z", "a", "m"]}


def test_empty_and_unknown():
    objs = [obj("keys", "Связка ключей", "ключ")]
    assert resolve_object("", objs) == {"status": "none"}
    assert resolve_object("   ", objs) == {"status": "none"}
    assert resolve_object("совсем другое", objs) == {"status": "none"}
    assert resolve_object("ключи", []) == {"status": "none"}


def test_objects_without_aliases_key_are_accepted():
    assert resolve_object("Телефон погибшего", [{"id": "phone", "title": "Телефон погибшего"}]) == {
        "status": "ok", "id": "phone"}


def test_multiword_alias_needs_all_stems():
    cam = obj("cam", "Камеры вокзала", "камер вокзал")
    assert resolve_object("камеры на вокзале", [cam]) == {"status": "ok", "id": "cam"}
    assert resolve_object("камеры", [cam]) == {"status": "none"}
    assert resolve_object("вокзал", [cam]) == {"status": "none"}


def test_cases_declension_and_yo():
    pill = obj("pill", "Таблетница погибшего", "таблетниц")
    for text in ["таблетница", "таблетницу", "таблетницы", "в таблетнице", "ТАБЛЕТНИЦЕЙ!"]:
        assert resolve_object(text, [pill]) == {"status": "ok", "id": "pill"}, text
    room = obj("room", "Гримёрка", "гример")
    assert resolve_object("ГРИМЁРКУ", [room]) == {"status": "ok", "id": "room"}
    assert resolve_object("гримерку", [room]) == {"status": "ok", "id": "room"}
