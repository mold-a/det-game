"""QA: случайный фаззинг нормализации Python ↔ JS (docs/02 §2, CLAUDE.md «побайтно одинаково»).

≥ 20 000 строк для типов text, password, time, date, number: кириллица, латиница, цифры
(ASCII и не-ASCII), пунктуация, пробелы разных видов, комбинируемые знаки, особые случаи
регистра (İ, ß, Σ/ς, ǅ), эмодзи, астральные буквы. Затравка фиксирована — падение воспроизводимо.

Отдельно: случайные кодовые точки всего Unicode. Расхождения в символах, которые Python
(unicodedata) считает неназначенными (Cn), а ICU в Node — назначенными, относятся к разнице
версий Unicode, а не к логике; они проверяются в ``test_random_codepoints_only_version_skew``.
"""

from __future__ import annotations

import json
import random
import shutil
import subprocess
import unicodedata
from pathlib import Path

import pytest

from engine.normalize import normalize

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "tests" / "qa" / "normalize_cli.mjs"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js не найден")

YEAR = 2026
TYPES = ("text", "password", "time", "date", "number")
SEED = 20261013

CYR = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
LAT = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIG = "0123456789"
DIG_OTHER = "٠١٢٣٤٥٦٧٨٩۰۳०१२০੩０１２９²³¹⅕Ⅻⅻ①᠑"
PUNCT = ".,:;-–—‑!?()«»\"'/\\_@#№%&*+=[]{}|~`^…·•‐"
SPACES = [" ", "\t", "\n", "\r", " ", " ", " ", "　", "​", "﻿", " ",
          "\u0085", "᠎", " ", " ", "­", "‍", "‌"]
COMBINING = ["́", "̀", "̈", "̆", "̧", "̨", "̌", "⃝", "҉",
             "ः", "ָ", "ั", "़", "️", "̲", "\U0001d167"]
SPECIAL = ["İ", "ı", "ß", "ẞ", "Σ", "ς", "σ", "ﬁ", "ﬀ", "Ǆ", "ǅ", "ǆ", "Ω", "Ω", "K", "Å", "Å", "ŉ",
           "😀", "👍🏽", "👨‍👩‍👧", "🇷🇺", "𝐀", "𝟗", "𐐀", "𐐨", "Ა", "Ꭰ", "ꭰ", "Ḁ", "ǰ", "ΐ", "ΰ",
           "가", "가", "ﾊﾟ", "ㄱ", "ä", "ä", "ё", "Ё", "й", "й", "Ӂ",
           "Ꙁ", "ꙁ", "Ꚁ", "ᲀ", "ꞵ", "Ʞ", "ǈ", "ǋ", "ǲ", "ᾈ", "ᾼ", "ῼ", "ﬓ", "ẞ", "ǅ"]
TIME_SEPS = [":", ".", " ", "-", "ч", " ч ", "h", ",", "/", " ", "：", "꞉", ""]


def _pick(rng: random.Random, pool) -> str:
    return pool[rng.randrange(len(pool))]


def _free(rng: random.Random) -> str:
    """Произвольная смесь символов из всех групп."""
    groups = [CYR, LAT, DIG, DIG_OTHER, PUNCT, SPACES, COMBINING, SPECIAL]
    weights = [30, 15, 20, 4, 10, 10, 6, 5]
    n = rng.randrange(0, 24)
    return "".join(_pick(rng, rng.choices(groups, weights)[0]) for _ in range(n))


def _digits(rng: random.Random, k: int) -> str:
    return "".join(_pick(rng, DIG if rng.random() < 0.93 else DIG_OTHER) for _ in range(k))


def _timeish(rng: random.Random) -> str:
    parts = [_digits(rng, rng.choice([1, 1, 2, 2, 2, 3, 4, 5])) for _ in range(rng.choice([1, 2, 2, 2, 3]))]
    out = _pick(rng, ["", "", " ", "в ", "~", "около "])
    for i, p in enumerate(parts):
        if i:
            out += _pick(rng, TIME_SEPS)
        out += p
        if rng.random() < 0.1:
            out += _pick(rng, COMBINING)
    return out + _pick(rng, ["", "", " ", " мин", "!", " ч", " "])


def _dateish(rng: random.Random) -> str:
    seps = [".", "/", "-", " ", ",", ". ", " ", "—"]
    n = rng.choice([2, 3, 3, 3, 1, 4])
    parts = [_digits(rng, rng.choice([1, 2, 2, 2, 3, 4])) for _ in range(n)]
    out = parts[0]
    for p in parts[1:]:
        out += _pick(rng, seps) + p
    if rng.random() < 0.2:
        out = _pick(rng, ["", " ", "дата ", "г."]) + out + _pick(rng, ["", " г", "г.", " года"])
    return out


def _wordy(rng: random.Random) -> str:
    words = []
    for _ in range(rng.randrange(1, 5)):
        w = "".join(_pick(rng, CYR if rng.random() < 0.7 else LAT) for _ in range(rng.randrange(1, 10)))
        if rng.random() < 0.2:
            pos = rng.randrange(len(w) + 1)
            w = w[:pos] + _pick(rng, COMBINING + SPECIAL) + w[pos:]
        words.append(w)
    out = ""
    for w in words:
        out += w + "".join(_pick(rng, SPACES + list(PUNCT)) for _ in range(rng.randrange(0, 3)))
    return out


def make_cases(n: int, seed: int = SEED) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    gens = [_free, _timeish, _dateish, _wordy]
    cases = []
    for i in range(n):
        s = gens[i % len(gens)](rng)
        for t in TYPES:
            cases.append((t, s))
    return cases


def run_js(cases: list[tuple[str, str]]) -> list:
    payload = json.dumps({"defaultYear": YEAR, "cases": cases}, ensure_ascii=True)
    res = subprocess.run([NODE, str(CLI)], input=payload.encode("ascii"), capture_output=True, timeout=300)
    assert res.returncode == 0, res.stderr.decode("utf-8", "replace")
    return json.loads(res.stdout.decode("utf-8"))


def py(t: str, s: str):
    try:
        return normalize(t, s, default_year=YEAR)
    except Exception as e:  # noqa: BLE001 — сравниваем и исключения
        return {"error": type(e).__name__}


def _diff(cases, js_out):
    bad = []
    for (t, s), j in zip(cases, js_out):
        p = py(t, s)
        if isinstance(p, dict) and isinstance(j, dict):
            continue  # обе стороны бросили исключение
        if p != j:
            bad.append((t, s, p, j))
    return bad


def test_fuzz_python_equals_js():
    strings = 6000  # × 5 типов = 30 000 вызовов
    cases = make_cases(strings)
    # плюс ещё 20 000 строк только для text/password (самая сложная часть — base())
    rng = random.Random(SEED + 1)
    extra = []
    for i in range(20000):
        s = (_free, _wordy)[i % 2](rng)
        extra.append(("text", s))
        extra.append(("password", s))
    cases += extra
    assert len({s for _, s in cases}) >= 20000
    js_out = run_js(cases)
    assert len(js_out) == len(cases)
    bad = _diff(cases, js_out)
    report = "\n".join(f"{t} {s!r} [{' '.join(f'U+{ord(c):04X}' for c in s)}]: py={p!r} js={j!r}" for t, s, p, j in bad[:30])
    assert not bad, f"{len(bad)} расхождений Python ↔ JS:\n{report}"


def _random_cp(rng: random.Random) -> str:
    while True:
        r = rng.random()
        cp = rng.randrange(0x20, 0x3000) if r < 0.6 else rng.randrange(0x3000, 0x30000)
        if 0xD800 <= cp <= 0xDFFF:
            continue
        return chr(cp)


def test_random_codepoints_only_version_skew():
    """Случайные кодовые точки: допустимы только расхождения из-за символов, неизвестных Python (Cn)."""
    rng = random.Random(SEED + 2)
    cases = []
    for _ in range(20000):
        s = "".join(_random_cp(rng) for _ in range(rng.randrange(1, 6)))
        cases.append(("text", s))
    js_out = run_js(cases)
    real = []
    skew = set()
    for t, s, p, j in _diff(cases, js_out):
        unknown = [c for c in s if unicodedata.category(c) == "Cn"]
        if unknown:
            skew.update(unknown)
            continue
        real.append((t, s, p, j))
    report = "\n".join(f"{s!r} [{' '.join(f'U+{ord(c):04X}' for c in s)}]: py={p!r} js={j!r}" for _, s, p, j in real[:30])
    assert not real, f"{len(real)} расхождений не из-за версии Unicode:\n{report}"
