"""Имена персонажей, вписанные в тексты буквами, а не шаблоном (docs/06 §3 п.10).

Защита от поломки при подстановке настоящих имён (``import-cast``, P09): если в тексте
написано «Иван Сергеевич», а не ``{{ c.voroncov.io() }}``, после импорта в игре останется
рабочее имя. Сканируются **сырые** (нерендеренные) тексты ``content/``: значения строк YAML
(ключи и комментарии пропускаются) и тела Markdown с front matter (значения front matter
тоже, ключи — нет), вне конструкций ``{{ … }}``, ``{% … %}``, ``{# … #}``.

Совпадение — целые слова (токены из букв), сравнение через ``normalize.base`` (регистр, ё/е),
каждое слово найденного — с заглавной буквы (обычные слова в середине фразы — строчные:
«стая волков» — не «Волков»). Ищутся все падежные формы (``engine.names.Person``) фамилии,
имени, отчества и ``familiar`` персонажей с ``cast: true``; сочетания «Фамилия Имя Отчество»,
«Имя Отчество», «Имя Фамилия», «Фамилия Имя» — целиком (самое длинное совпадение).

Строгость: сочетания и фамилии находятся всегда (фамилии — кроме ``SURNAME_EXCEPTIONS``);
одиночные имя, отчество и ``familiar`` пропускаются, если совпадают с обычным словом
(``COMMON_WORD_NAMES``) или со словом из названий мира (строки ``world.yaml``: роль «Нина»
в пьесе и т. п.). Персонажи с ``cast: false`` (вымышленные) не ищутся; их ФИО целиком
поглощается и не даёт ложных срабатываний по чужим частям. Части имени с ``TODO(content)``
и строки текста с ``TODO(content)`` не учитываются (заглушки и так запрещены в ``--release``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

import yaml

from engine.content import TODO_MARK, _body_start
from engine.models import CASES, Character
from engine.names import DeclensionError, Person, decline
from engine.normalize import base
from engine.util import iter_strings, read_text

# Что сканируется: файлы и маски относительно content/ (docs/06 §3 п.10).
SCAN_FILES: tuple[str, ...] = ("stages.yaml", "documents.yaml", "expertise.yaml", "finale.yaml")
SCAN_GLOBS: tuple[tuple[str, str], ...] = (
    ("documents", "*.md"),
    ("pages", "**/*.yaml"),
    ("pages", "**/*.md"),
    ("chats", "*.yaml"),
    ("paper", "*.md"),
)

# Одиночные имена, которые одновременно обычные слова русского языка: «Вера в …» в начале
# фразы — не персонаж. Сравнение через base() (регистр, ё/е); исключение действует на все
# падежные формы имени (Веры, Вере, Веру…), но не на сочетания («Вера Ивановна» найдётся).
COMMON_WORD_NAMES: frozenset[str] = frozenset({
    "вера",      # вера
    "надежда",   # надежда
    "любовь",    # любовь
    "лев",       # лев (зверь)
    "роман",     # роман (книга)
    "слава",     # слава
    "роза",      # роза (цветок)
    "лилия",     # лилия (цветок)
    "мир",       # мир
    "заря",      # заря
    "ангел",     # ангел
})

# Фамилии — обычные слова. Проверяются строже имён: исключение только явное, здесь.
# Пусто: ни одна фамилия текущего контента не встречается с заглавной буквы как обычное слово.
SURNAME_EXCEPTIONS: frozenset[str] = frozenset()

_JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.S)
_WORD = re.compile(r"[^\W\d_]+")
_GAP = re.compile(r"\s*")  # между словами сочетания — только пробельные символы
_SINGLE_SOFT = ("first", "middle", "familiar")  # одиночные — мягкая проверка


@dataclass(frozen=True)
class NameHit:
    file: str          # «content/paper/1-07.md»
    line: int
    found: str         # как написано в тексте
    suggestions: tuple[str, ...]
    replacement: str   # шаблон первого предложения — для автозамены в тестах

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: найдено «{self.found}» → {' или '.join(self.suggestions)}"


@dataclass(frozen=True)
class _Pattern:
    keys: tuple[str, ...]
    char_id: str
    kind: str          # full | io | first_last | last_first | last | first | middle | familiar
    case: str
    cast: bool
    lemma: str         # base() именительного падежа части имени — для исключений


def _keys(text: str) -> tuple[str, ...]:
    return tuple(base(w) for w in _WORD.findall(text))


def _usable(value: str | None) -> bool:
    return bool(value) and TODO_MARK not in value


def _patterns(characters: Iterable[Character]) -> dict[str, list[_Pattern]]:
    """Индекс: ключ первого слова → шаблоны имён (все падежи, все сочетания)."""
    index: dict[str, list[_Pattern]] = {}

    def add(text: str, ch: Character, kind: str, case: str, lemma: str = "") -> None:
        keys = _keys(text)
        if keys:
            index.setdefault(keys[0], []).append(_Pattern(keys, ch.id, kind, case, ch.cast, base(lemma)))

    for ch in characters:
        p = Person(ch)
        ok = {part: _usable(getattr(ch, part)) for part in ("last", "first", "middle")}
        for case in CASES:
            last = p.last(case) if ok["last"] else ""
            first = p.first(case) if ok["first"] else ""
            middle = p.middle(case) if ok["middle"] else ""
            if last and first and middle:
                add(f"{last} {first} {middle}", ch, "full", case)
            if first and middle:
                add(f"{first} {middle}", ch, "io", case)
            if first and last:
                add(f"{first} {last}", ch, "first_last", case)
                add(f"{last} {first}", ch, "last_first", case)
            for kind, value in (("last", last), ("first", first), ("middle", middle)):
                if value:
                    add(value, ch, kind, case, p._part(kind, "nom"))
            if _usable(ch.familiar):
                try:  # familiar в шаблоне не склоняется, но в тексте может стоять в падеже
                    fam = ch.familiar if case == "nom" else decline("first", ch.familiar, ch.gender, case)
                except DeclensionError:
                    fam = ch.familiar if case == "nom" else ""
                if fam:
                    add(fam, ch, "familiar", case, ch.familiar)
    for pats in index.values():
        pats.sort(key=lambda x: -len(x.keys))
    return index


def world_words(world: Any) -> frozenset[str]:
    """Слова из строк ``world.yaml`` (названия мира: роли пьесы, бренды, улицы) — ключи base()."""
    return frozenset(k for _, s in iter_strings(world) if TODO_MARK not in s for k in _keys(s))


def _arg(case: str) -> str:
    return "()" if case == "nom" else f"('{case}')"


def _suggest(pats: list[_Pattern]) -> tuple[tuple[str, ...], str]:
    """Предложения ``{{ c.<id>.… }}`` (по одному на персонажа и вид, прочие падежи — в скобках)
    и чистый шаблон первого из них."""
    by: dict[tuple[str, str], list[str]] = {}
    for p in pats:
        cases = by.setdefault((p.char_id, p.kind), [])
        if p.case not in cases:
            cases.append(p.case)
    out: list[str] = []
    first = ""
    for (cid, kind), cases in by.items():
        case = cases[0]
        if kind == "familiar":
            s = f"{{{{ c.{cid}.familiar }}}}" + ("" if case == "nom" else " (не склоняется)")
        elif kind == "first_last":
            s = f"{{{{ c.{cid}.first{_arg(case)} }}}} {{{{ c.{cid}.last{_arg(case)} }}}}"
        elif kind == "last_first":
            s = f"{{{{ c.{cid}.last{_arg(case)} }}}} {{{{ c.{cid}.first{_arg(case)} }}}}"
        else:
            s = f"{{{{ c.{cid}.{kind}{_arg(case)} }}}}"
        first = first or s.removesuffix(" (не склоняется)")
        others = [c for c in cases[1:] if kind != "familiar"]
        if others:
            s += " (или " + ", ".join(f"'{c}'" for c in others) + ")"
        out.append(s)
    return tuple(out), first


_MASK_CHAR = "\x00"  # не буква и не пробел: сочетание «Иван {{ … }} Сергеевич» не склеивается


def _mask(text: str) -> str:
    """Конструкции Jinja → ``_MASK_CHAR`` (переводы строк сохраняются: номера строк не сдвигаются)."""
    return _JINJA.sub(lambda m: re.sub(r"[^\n]", _MASK_CHAR, m.group(0)), text)


class _Scanner:
    def __init__(self, characters: Iterable[Character], world: Any) -> None:
        self.index = _patterns(characters)
        self.soft = COMMON_WORD_NAMES | world_words(world)

    def _skip_single(self, key: str, pats: list[_Pattern]) -> bool:
        """Одиночное слово-исключение: сама форма или именительный падеж каждого кандидата
        («Нины» — форма «Нина») есть в списке; фамилии — только ``SURNAME_EXCEPTIONS``."""
        if all(p.kind in _SINGLE_SOFT for p in pats):
            return key in self.soft or all(p.lemma in self.soft for p in pats)
        return key in SURNAME_EXCEPTIONS or all(p.lemma in SURNAME_EXCEPTIONS for p in pats)

    def scan_text(self, text: str, file: str, first_line: int = 1) -> Iterator[NameHit]:
        """Имена в куске текста; ``first_line`` — номер строки файла, с которой он начинается."""
        masked = _mask(text)
        lines = text.split("\n")
        words = list(_WORD.finditer(masked))
        keys = [base(m.group(0)) for m in words]
        i = 0
        while i < len(words):
            best: list[_Pattern] = []
            for pat in self.index.get(keys[i], ()):
                n = len(pat.keys)
                if best and n < len(best[0].keys):
                    break
                if i + n > len(words) or tuple(keys[i:i + n]) != pat.keys:
                    continue
                if not all(words[j].group(0)[0].isupper() for j in range(i, i + n)):
                    continue
                if not all(_GAP.fullmatch(masked[words[j].end():words[j + 1].start()])
                           for j in range(i, i + n - 1)):
                    continue
                best.append(pat)
            if not best:
                i += 1
                continue
            n = len(best[0].keys)
            start, end = words[i].start(), words[i + n - 1].end()
            i += n
            cast = [p for p in best if p.cast]
            if not cast or (n > 1 and len(cast) < len(best)):
                continue  # вымышленный персонаж (cast: false) — целиком
            if n == 1 and self._skip_single(keys[i - 1], cast):
                continue
            ln = masked.count("\n", 0, start)
            if TODO_MARK in lines[ln]:
                continue
            found = " ".join(masked[start:end].split())
            yield NameHit(file, first_line + ln, found, *_suggest(cast))

    def scan_yaml(self, src: str, file: str, line_offset: int = 0) -> Iterator[NameHit]:
        """Значения строк YAML (не ключи, не комментарии) с номерами строк файла."""
        root = yaml.compose(src, Loader=yaml.SafeLoader)
        stack = [root] if root is not None else []
        while stack:
            node = stack.pop()
            if isinstance(node, yaml.MappingNode):
                stack.extend(v for _, v in reversed(node.value))
            elif isinstance(node, yaml.SequenceNode):
                stack.extend(reversed(node.value))
            elif isinstance(node, yaml.ScalarNode) and node.tag == "tag:yaml.org,2002:str":
                s, e = node.start_mark, node.end_mark
                seg = src[s.index:e.index]
                line = s.line
                if node.style in ("|", ">"):  # заголовок блока («|» и комментарий после него)
                    cut = seg.find("\n")
                    seg = "" if cut < 0 else seg[cut + 1:]
                    line += 1
                yield from self.scan_text(seg, file, line_offset + line + 1)


def scan_files(content_dir: Path) -> list[Path]:
    root = Path(content_dir)
    found = [root / f for f in SCAN_FILES if (root / f).is_file()]
    for sub, pattern in SCAN_GLOBS:
        found += sorted(p for p in (root / sub).glob(pattern) if p.is_file())
    return found


def _front_matter(text: str) -> tuple[str, int] | None:
    """Текст front matter и номер строки (с 0), с которой он начинается, или ``None``."""
    body = _body_start(text)
    if body == 1:
        return None
    lines = text.split("\n")
    return "\n".join(lines[1:body - 2]), 1


def hardcoded_names(content_dir: Path, characters: Iterable[Character], world: Any) -> list[NameHit]:
    """Все имена персонажей с ``cast: true``, вписанные в тексты ``content/`` буквами."""
    root = Path(content_dir)
    scanner = _Scanner(characters, world)
    hits: list[NameHit] = []
    for path in scan_files(root):
        rel = f"{root.name}/{path.relative_to(root).as_posix()}"
        text = read_text(path)
        if path.suffix == ".md":
            fm = _front_matter(text)
            if fm is not None:
                hits += scanner.scan_yaml(fm[0], rel, fm[1])
            start = _body_start(text)
            body = "\n".join(text.split("\n")[start - 1:])
            hits += scanner.scan_text(body, rel, start)
        else:
            hits += scanner.scan_yaml(text, rel)
    return hits
