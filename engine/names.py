"""Склонение ФИО (pytrovich 0.2) и объект персонажа для шаблонов.

Пол берётся только из ``characters.yaml → gender`` (детектор не используется).
Ручные исправления — ``characters[].forms: {last|first|middle: {падеж: форма}}``,
они важнее библиотеки. ``None`` и пустая строка → ``""``; пустые части имени
при склейке пропускаются.

Персонаж с ``father: <id>`` получает фамилию и отчество от отца:
``surname_for(father_last, gender)`` и ``patronymic_for(father_first, gender)`` —
чистые функции (без pytrovich), их используют валидация ``content`` и import-cast (P09).
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Mapping

from pytrovich.enums import Case, Gender, NamePart
from pytrovich.maker import PetrovichDeclinationMaker

from engine.models import CASES, Character

PARTS: tuple[str, ...] = ("last", "first", "middle")
DERIVED_PARTS: tuple[str, ...] = ("last", "middle")  # что выводится от отца (father)
DERIVED_MARK = "↑"
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


class DeclensionError(ValueError):
    """Неверный падеж, часть имени или пол; имя, от которого не выводится отчество."""


# ---------------------------------------------------------------- фамилия и отчество от отца

# Пары окончаний фамилии «мужская → женская». Порядок важен: длинные окончания раньше.
_SURNAME_M2F: tuple[tuple[str, str], ...] = (
    ("ский", "ская"),
    ("цкий", "цкая"),
    ("ской", "ская"),
    ("цкой", "цкая"),
    ("ов", "ова"),
    ("ев", "ева"),
    ("ёв", "ёва"),
    ("ин", "ина"),
    ("ын", "ына"),
)
# «Женская → мужская»: -ская однозначно не восстанавливается (-ский/-ской), берём -ский.
_SURNAME_F2M: tuple[tuple[str, str], ...] = (
    ("ская", "ский"),
    ("цкая", "цкий"),
    ("ова", "ов"),
    ("ева", "ев"),
    ("ёва", "ёв"),
    ("ина", "ин"),
    ("ына", "ын"),
)
_MIN_STEM = 1  # перед окончанием должна остаться хотя бы одна буква («Ов» — не фамилия на -ов)


def _check_gender(gender: str) -> str:
    if gender not in _GENDER:
        raise DeclensionError(f"неизвестный пол {gender!r}; допустимы: m, f")
    return gender


def _swap_ending(word: str, pairs: tuple[tuple[str, str], ...]) -> str:
    low = word.lower()
    for src, dst in pairs:
        if low.endswith(src) and len(low) - len(src) >= _MIN_STEM:
            stem = word[: len(word) - len(src)]
            tail = dst.upper() if word[-len(src):].isupper() else dst
            return stem + tail
    return word


def surname_for(father_last: str, gender: str, source_gender: str = "m") -> str:
    """Фамилия ребёнка пола ``gender`` по фамилии отца (``source_gender`` — пол формы на входе).

    м→ж: -ов/-ев/-ёв/-ин/-ын → +а; -ский/-цкий/-ской/-цкой → -ская/-цкая.
    ж→м — обратная замена. Несклоняемые и незнакомые окончания (-ич, -ко, -ых, -их,
    гласная, мягкий знак, -ой и т. п.) остаются как есть. Двойная фамилия через дефис —
    по частям. Если правило не подходит, правильную форму задают в ``forms.last.nom``.
    """
    _check_gender(gender)
    _check_gender(source_gender)
    value = (father_last or "").strip()
    if not value or gender == source_gender:
        return value
    pairs = _SURNAME_M2F if gender == "f" else _SURNAME_F2M
    return "-".join(_swap_ending(part, pairs) for part in value.split("-"))


# Имена с особым отчеством: имя (строчными, ё → е) → (мужское, женское).
_PATRONYMIC_SPECIAL: dict[str, tuple[str, str]] = {
    "илья": ("Ильич", "Ильинична"),
    "никита": ("Никитич", "Никитична"),
    "фома": ("Фомич", "Фоминична"),
    "кузьма": ("Кузьмич", "Кузьминична"),
    "лука": ("Лукич", "Лукинична"),
    "савва": ("Саввич", "Саввична"),
    "данила": ("Данилович", "Даниловна"),
    "гаврила": ("Гаврилович", "Гавриловна"),
    "павел": ("Павлович", "Павловна"),
    "лев": ("Львович", "Львовна"),
    "петр": ("Петрович", "Петровна"),
    "яков": ("Яковлевич", "Яковлевна"),
    "михаил": ("Михайлович", "Михайловна"),
    "дмитрий": ("Дмитриевич", "Дмитриевна"),
    "георгий": ("Георгиевич", "Георгиевна"),
}
_CYR_NAME = re.compile(r"^[А-ЯЁ][а-яё]+$")
_HUSHING = "жшчщц"  # после них -евич, а не -ович
_VOWELS = "аеёиоуыэюя"


def _patronymic_error(name: str, why: str) -> DeclensionError:
    return DeclensionError(
        f"не удалось вывести отчество от имени «{name}»: {why}; "
        "укажите отчество вручную в forms (forms: {middle: {nom: …}}) и в middle"
    )


def patronymic_for(father_first: str, gender: str) -> str:
    """Отчество по имени отца по русским правилам.

    Иван → Иванович/Ивановна; -й (Сергей, Николай) → -евич/-евна; -ий → -ьевич/-ьевна
    (Юрий → Юрьевич), но Дмитрий/Георгий → -иевич; -ь (Игорь) → -евич; особые случаи —
    Илья, Никита, Фома, Кузьма, Лука, Павел, Лев, Пётр, Яков, Михаил и др. Имя, для
    которого правило неоднозначно (прочие на -а/-я, на -о, на гласную) или не
    записано одним словом кириллицей, — ``DeclensionError``.
    """
    _check_gender(gender)
    name = (father_first or "").strip()
    if not _CYR_NAME.match(name):
        raise _patronymic_error(name, "ожидается одно слово кириллицей с заглавной буквы")
    key = name.lower().replace("ё", "е")
    if key in _PATRONYMIC_SPECIAL:
        m, f = _PATRONYMIC_SPECIAL[key]
        return m if gender == "m" else f
    last = key[-1]
    if key.endswith("ий") and len(key) > 2:
        stem, suffix = name[:-2] + "ь", "ев"
    elif last == "й" and key[-2] in _VOWELS:
        stem, suffix = name[:-1], "ев"
    elif last == "ь":
        stem, suffix = name[:-1], "ев"
    elif last in _VOWELS:
        raise _patronymic_error(name, "имя оканчивается на гласную, правило неоднозначно")
    elif last in _HUSHING:
        stem, suffix = name, "ев"
    elif last == "й":
        raise _patronymic_error(name, "непривычное окончание")
    else:
        stem, suffix = name, "ов"
    return stem + suffix + ("ич" if gender == "m" else "на")


@lru_cache(maxsize=1)
def _maker() -> PetrovichDeclinationMaker:
    return PetrovichDeclinationMaker()


def check_case(case: str) -> str:
    if case not in _CASE:
        raise DeclensionError(f"неизвестный падеж {case!r}; допустимы: {', '.join(CASES)}")
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
        raise DeclensionError(f"неизвестная часть имени {part!r}; допустимы: {', '.join(PARTS)}")
    if gender not in _GENDER:
        raise DeclensionError(f"неизвестный пол {gender!r}; допустимы: m, f")
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
        self.father = ch.father

    @property
    def familiar(self) -> str | None:
        """Дружеское имя («Ваня») как есть, без склонения; ``None``, если не задано."""
        return self._ch.familiar

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

    ``manual`` — падежи, взятые из ручных ``forms``; ``derived`` — часть выведена
    от отца (``father``): фамилия и отчество.
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
                    "derived": bool(ch.father) and part in DERIVED_PARTS,
                }
            )
    return rows


def format_names_table(characters: list[Character]) -> str:
    """Текстовая таблица для ``python -m engine names``: по блоку на персонажа."""
    rows = names_table(characters)
    headers = ["персонаж", "часть", *CASES]
    table: list[list[str]] = []
    for r in rows:
        cells = [f"{r['id']} ({r['gender']})" if r["part"] == "last" else "",
                 r["part"] + (f" {DERIVED_MARK}" if r["derived"] else "")]
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
        extra = []
        if p.father:
            extra.append(f"{DERIVED_MARK} father: {p.father}")
        if p.familiar:
            extra.append(f"familiar: {p.familiar}")
        tail = f"  ({'; '.join(extra)})" if extra else ""
        out.append(f"  {p.id.ljust(sw)}  {forms}{tail}")
    out.append("")
    out.append("* — ручная форма из characters.yaml → forms; short() показан в nom | gen | ins.")
    out.append(f"{DERIVED_MARK} — фамилия и отчество выведены от отца (characters.yaml → father), "
               "сборка сверяет их с last/middle.")
    return "\n".join(out)
