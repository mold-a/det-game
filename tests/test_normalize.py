"""Нормализация (docs/02 §2): общие векторы tests/vectors/normalize.json + граничные случаи."""

import json
import unicodedata
from pathlib import Path

import pytest

from engine.normalize import TYPES, base, normalize

VECTORS_PATH = Path(__file__).parent / "vectors" / "normalize.json"
VECTORS = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def _id(case: dict) -> str:
    return f"{case['type']}:{case['input']!r}"


def test_vectors_count_and_shape():
    assert isinstance(VECTORS, list)
    assert len(VECTORS) >= 60
    keys = set()
    for case in VECTORS:
        assert set(case) <= {"type", "input", "expected", "default_year", "note"}, case
        assert case["type"] in TYPES, case
        key = (case["type"], json.dumps(case["input"], ensure_ascii=False), case.get("default_year"))
        assert key not in keys, f"дубликат вектора: {case}"
        keys.add(key)


def test_vectors_cover_all_types():
    assert {case["type"] for case in VECTORS} == set(TYPES)


@pytest.mark.parametrize("case", VECTORS, ids=[_id(c) for c in VECTORS])
def test_vector(case):
    got = normalize(case["type"], case["input"], default_year=case.get("default_year"))
    assert got == case["expected"]


def _codepoints(value) -> str:
    return "".join(value) if isinstance(value, list) else value


def test_vectors_use_only_stable_codepoints():
    # Python 3.13 — Unicode 15.1, Node 22 — 16.0. Неназначенный в 15.1 символ (Cn)
    # может классифицироваться в JS иначе, поэтому таких в векторах быть не должно.
    for case in VECTORS:
        for ch in _codepoints(case["input"]):
            cat = unicodedata.category(ch)
            assert cat != "Cn", f"{case}: U+{ord(ch):04X} не назначен в Unicode {unicodedata.unidata_version}"


def test_base_examples():
    assert base(" Бронхиальная  астма! ") == "бронхиальная астма"
    assert base("") == ""
    assert base("Ё-моё") == "е мое"


def test_unknown_type_raises():
    with pytest.raises(ValueError):
        normalize("color", "red")


def test_date_without_default_year_raises_only_when_needed():
    with pytest.raises(ValueError):
        normalize("date", "05.03")
    assert normalize("date", "05.03.2026") == "2026-03-05"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("00:00", "00:00"),
        ("23:59", "23:59"),
        ("0:59", "00:59"),
        ("23:0", "23:00"),
        ("100", "01:00"),
        ("2359", "23:59"),
        ("0000", "00:00"),
        ("23:60", None),
        ("-1:30", "01:30"),
        ("1:2:3", None),
        ("99999999999999999999:15", None),
        ("1" * 5000 + ":15", None),
    ],
)
def test_time_boundaries(raw, expected):
    assert normalize("time", raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("31.01.2026", "2026-01-31"),
        ("28.02.2026", "2026-02-28"),
        ("30.04.2026", "2026-04-30"),
        ("31.12.2026", "2026-12-31"),
        ("01.01.9999", "9999-01-01"),
        ("31.06.2026", None),
        ("29.02.1900", None),
        ("29.02.1600", "1600-02-29"),
        ("1" * 5000 + ".01.2026", None),
    ],
)
def test_date_boundaries(raw, expected):
    assert normalize("date", raw, default_year=2026) == expected


def test_list_types_accept_tuples_and_reject_non_strings():
    assert normalize("multi", ("b", "a")) == "a,b"
    assert normalize("multi", ["a", 1]) is None
    assert normalize("choice", ["a"]) is None
    assert normalize("text", None) is None
