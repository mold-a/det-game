"""Нормализация ответов — docs/02-architecture.md §2.

Зеркало ``site/assets/js/core/normalize.js``: обе реализации обязаны давать
побайтно одинаковый результат. Общие векторы — ``tests/vectors/normalize.json``.

``normalize(type_, value, *, default_year=None) -> str | None``; ``None`` —
невалидный ввод (не попытка: интерфейс показывает подсказку формата).
"""

from __future__ import annotations

import calendar
import re
import unicodedata

TYPES = frozenset(
    {"text", "password", "time", "date", "number", "choice", "person", "document", "multi", "persons", "order"}
)
ID_TYPES = frozenset({"choice", "person", "document"})
LIST_TYPES = frozenset({"multi", "persons", "order"})

# Только ASCII-цифры: в Python ``\d`` ловит любые Unicode-цифры, в JS — только 0–9.
_DIGIT_GROUP = re.compile(r"[0-9]+")
_ID = re.compile(r"[a-z0-9_-]+")


def base(s: str) -> str:
    """NFC → lower → «ё»→«е» → M* удалить, не L*/N* → пробел → схлопнуть пробелы.

    Посимвольно по ``unicodedata.category``, а не через ``\\w``.
    """
    s = unicodedata.normalize("NFC", s).lower().replace("ё", "е")
    out: list[str] = []
    for ch in s:
        major = unicodedata.category(ch)[0]
        if major in ("L", "N"):
            out.append(ch)
        elif major == "M":
            continue
        else:
            out.append(" ")
    return " ".join(part for part in "".join(out).split(" ") if part)


def _norm_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.lower()
    return v if _ID.fullmatch(v) else None


def _norm_ids(value: object) -> list[str] | None:
    if not isinstance(value, (list, tuple)) or not value:
        return None
    ids: list[str] = []
    for item in value:
        v = _norm_id(item)
        if v is None:
            return None
        ids.append(v)
    return ids


def _int(group: str) -> int:
    """Группа цифр → число. Длинные группы заведомо вне диапазона: без ``int()``
    на тысячах цифр (лимит Python 4300 знаков)."""
    stripped = group.lstrip("0")
    return int(stripped or "0") if len(stripped) <= 6 else 10**7


def _time(s: str) -> str | None:
    groups = _DIGIT_GROUP.findall(s)
    if len(groups) == 1:
        g = groups[0]
        if len(g) not in (3, 4):
            return None
        h, m = _int(g[:-2]), _int(g[-2:])
    elif len(groups) == 2:
        h, m = _int(groups[0]), _int(groups[1])
    else:
        return None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return f"{h:02d}:{m:02d}"


def _date(s: str, default_year: int | None) -> str | None:
    groups = _DIGIT_GROUP.findall(s)
    if len(groups) == 2:
        if default_year is None:
            raise ValueError("normalize('date', …): не передан default_year")
        d, m, y = _int(groups[0]), _int(groups[1]), int(default_year)
    elif len(groups) == 3:
        yg = groups[2]
        if len(yg) == 2:
            y = 2000 + _int(yg)
        elif len(yg) == 4:
            y = _int(yg)
        else:
            return None
        d, m = _int(groups[0]), _int(groups[1])
    else:
        return None
    if not (1 <= y <= 9999 and 1 <= m <= 12):
        return None
    if not (1 <= d <= calendar.monthrange(y, m)[1]):
        return None
    return f"{y:04d}-{m:02d}-{d:02d}"


def _number(s: str) -> str | None:
    digits = "".join(_DIGIT_GROUP.findall(s))
    if not digits:
        return None
    return digits.lstrip("0") or "0"


def normalize(type_: str, value: object, *, default_year: int | None = None) -> str | None:
    """Нормализовать ввод по типу единицы. ``None`` — невалидный ввод.

    Для ``multi``/``persons``/``order`` ``value`` — список ID, для остальных — строка.
    ``default_year`` нужен только для ``date`` из двух групп цифр.
    """
    if type_ not in TYPES:
        raise ValueError(f"неизвестный тип единицы: {type_!r}")

    if type_ in ID_TYPES:
        return _norm_id(value)

    if type_ in LIST_TYPES:
        ids = _norm_ids(value)
        if ids is None:
            return None
        if type_ == "order":
            if len(set(ids)) != len(ids):
                return None
            return ",".join(ids)
        return ",".join(sorted(set(ids)))

    if not isinstance(value, str):
        return None

    if type_ == "text":
        result = base(value)
    elif type_ == "password":
        result = base(value).replace(" ", "")
    elif type_ == "time":
        result = _time(value)
    elif type_ == "date":
        result = _date(value, default_year)
    else:  # number
        result = _number(value)
    return result or None
