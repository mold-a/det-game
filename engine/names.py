"""Склонение ФИО (pytrovich 0.2) и объект персонажа для шаблонов.

Пол берётся только из ``characters.yaml → gender`` (детектор не используется).
Ручные исправления — ``characters[].forms: {last|first|middle: {падеж: форма}}``,
они важнее библиотеки. ``None`` и пустая строка → ``""``; пустые части имени
при склейке пропускаются.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping

from pytrovich.enums import Case, Gender, NamePart
from pytrovich.maker import PetrovichDeclinationMaker

from engine.models import CASES, Character

PARTS: tuple[str, ...] = ("last", "first", "middle")
NBSP = " "

_CASE = {
    "nom": Case.NOMINATIVE,
    "gen": Case.GENITIVE,
    "dat": Case.DATIVE,
    "acc": Case.ACCUSATIVE,
    "ins": Case.INSTRUMENTAL,
    "pre": Case.PREPOSITIONAL,
}
_PART = {"last": NamePart.LASTNAME, "first": NamePart.FIRSTNAME, "middle": NamePart.MIDDLENAME}
_GENDER = {"m": Gender.MALE, "f": Gender.FEMALE}


class NameError_(ValueError):
    """Неверный падеж, часть имени или пол."""


@lru_cache(maxsize=1)
def _maker() -> PetrovichDeclinationMaker:
    return PetrovichDeclinationMaker()


def check_case(case: str) -> str:
    if case not in _CASE:
        raise NameError_(f"неизвестный падеж {case!r}; допустимы: {', '.join(CASES)}")
    return case


@lru_cache(maxsize=4096)
def _decline_lib(part: str, value: str, gender: str, case: str) -> str:
    return _maker().make(_PART[part], _GENDER[gender], _CASE[case], value, known_gender=True)


def decline(
    part: str,
    value: str | None,
    gender: str,
    case: str = "nom",
    forms: Mapping[str, Mapping[str, str]] | None = None,
) -> str:
    """Форма части имени в падеже. Ручная форма из ``forms`` важнее библиотеки."""
    check_case(case)
    if part not in _PART:
        raise NameError_(f"неизвестная часть имени {part!r}; допустимы: {', '.join(PARTS)}")
    if gender not in _GENDER:
        raise NameError_(f"неизвестный пол {gender!r}; допустимы: m, f")
    manual = (forms or {}).get(part, {}) or {}
    if case in manual:
        return manual[case]
    if not value:
        return ""
    if case == "nom":
        return value
    return _decline_lib(part, value, gender, case)


def _initials(name: str) -> str:
    """«Юрий» → «Ю.»; «Анна-Мария» → «А.-М.»."""
    return "-".join(p[0].upper() + "." for p in name.split("-") if p)


class Person:
    """Персонаж в шаблонах: ``c.<id>.full('gen')``, ``c.<id>.g('ушёл', 'ушла')``, ``c.<id>.role``."""

    def __init__(self, ch: Character) -> None:
        self._ch = ch
        self.id = ch.id
        self.role = ch.role
        self.nick = ch.nick
        self.age = ch.age
        self.gender = ch.gender
        self.photo = ch.photo

    def _part(self, part: str, case: str) -> str:
        ch = self._ch
        forms: Any = ch.forms or {}
        return decline(part, getattr(ch, part), ch.gender, case, forms)

    def last(self, case: str = "nom") -> str:
        return self._part("last", case)

    def first(self, case: str = "nom") -> str:
        return self._part("first", case)

    def middle(self, case: str = "nom") -> str:
        return self._part("middle", case)

    def full(self, case: str = "nom") -> str:
        """Фамилия Имя Отчество."""
        return " ".join(p for p in (self.last(case), self.first(case), self.middle(case)) if p)

    def io(self, case: str = "nom") -> str:
        """Имя Отчество."""
        return " ".join(p for p in (self.first(case), self.middle(case)) if p)

    def short(self, case: str = "nom") -> str:
        """«Фамилия И. О.» с неразрывными пробелами (решение 7)."""
        check_case(case)
        initials = [_initials(x) for x in (self._ch.first, self._ch.middle) if x]
        return NBSP.join(p for p in (self.last(case), *initials) if p)

    def g(self, m: str, f: str) -> str:
        return m if self._ch.gender == "m" else f

    def __str__(self) -> str:
        return self.full()

    def __repr__(self) -> str:
        return f"Person({self.id!r})"


def names_table(characters: list[Character]) -> list[dict[str, Any]]:
    """Строки таблицы: персонаж × часть имени, формы по всем падежам.

    ``manual`` — падежи, взятые из ручных ``forms``.
    """
    rows: list[dict[str, Any]] = []
    for ch in characters:
        p = Person(ch)
        forms = ch.forms or {}
        for part in PARTS:
            rows.append(
                {
                    "id": ch.id,
                    "gender": ch.gender,
                    "part": part,
                    "forms": {case: p._part(part, case) for case in CASES},
                    "manual": sorted((forms.get(part) or {}).keys()),
                }
            )
    return rows


def format_names_table(characters: list[Character]) -> str:
    """Текстовая таблица для ``python -m engine names``: по блоку на персонажа."""
    rows = names_table(characters)
    headers = ["персонаж", "часть", *CASES]
    table: list[list[str]] = []
    for r in rows:
        cells = [f"{r['id']} ({r['gender']})" if r["part"] == "last" else "", r["part"]]
        for case in CASES:
            v = r["forms"][case] or "—"
            cells.append(v + ("*" if case in r["manual"] else ""))
        table.append(cells)
    widths = [max(len(h), *(len(row[i]) for row in table)) for i, h in enumerate(headers)]

    def line(cells: list[str]) -> str:
        return "  ".join(c.ljust(w) for c, w in zip(cells, widths)).rstrip()

    out = [line(headers), line(["-" * w for w in widths])]
    for i, row in enumerate(table):
        if i and rows[i]["part"] == "last":
            out.append("")
        out.append(line(row))
    out.append("")
    out.append("short():")
    persons = [Person(ch) for ch in characters]
    sw = max(len(p.id) for p in persons)
    for p in persons:
        forms = "  |  ".join(p.short(c).replace(NBSP, " ") for c in ("nom", "gen", "ins"))
        out.append(f"  {p.id.ljust(sw)}  {forms}")
    out.append("")
    out.append("* — ручная форма из characters.yaml → forms; short() показан в nom | gen | ins.")
    return "\n".join(out)
