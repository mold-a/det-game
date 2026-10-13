"""Leak scan (docs/06 §3.7, PLAN §9 вопрос 9 — пересмотрен: шинглы, F4–F6).

Два вида «иголок»:

- **значения** — ищутся целиком (целые токены ``base()`` и сырой вид с границами слов):
  нормализованные каноны и варианты единиц ``text``/``time``/``date``/``number`` (кроме
  ``leak_scan: false``), параметры экспертиз, ``settings.leak_watchlist``, пароль облака,
  названия документов этапов 2…N; значения короче 4 символов не ищутся (F5);
- **шинглы** — все последовательности из 4 токенов ``base()`` по всему тексту подсказок,
  писем и текстов пакетов этапов 2…N, экспертиз, развязки и закрытых страниц (отрендеренных,
  как их видит игрок). Не считаются иголками шинглы только из служебных слов и шинглы
  «обвязки» (статический текст шаблонов ``site/templates``, строки интерфейса ``texts.js``,
  то, что оболочка закрытой страницы показывает по замыслу: бренд, логин облака).

У каждой иголки есть этап (0 — общая). Открытый текст pack-1 (его ключ публичный) сканируется
иголками всех этапов, кроме 1.

Сканируются все текстовые файлы ``dist/`` (кроме ``*.bin`` и шрифтов) и имена всех файлов;
перед поиском раскрываются ``\\uXXXX`` и HTML-сущности; в JSON пропускаются поля ``n``/``c``
контейнеров, соли и ключи (случайный base64url даёт ложные совпадения).
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from engine.normalize import base

BINARY_EXT = {".bin", ".woff", ".woff2", ".ttf", ".otf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico",
              ".mp3", ".m4a", ".mp4", ".webm", ".pdf", ".zip"}
MARKUP_EXT = {".html", ".htm", ".svg", ".xml"}
MIN_LEN = 4
SHINGLE = 4
TODO_MARK = "TODO(content)"
FILENAMES = "<имена файлов>"
# Значения JSON, которые — случайные байты в base64url (ложные совпадения): поля контейнера и соли/ключи.
B64_KEYS = {"n", "c", "salt", "saltStart", "saltStage", "key", "saltsId", "buildId"}
_U_ESC = re.compile(r"\\u([0-9a-fA-F]{4})")
_TAG = re.compile(r"<[^>]+>")
_WORD = r"[0-9A-Za-zА-Яа-яЁё]"

# Служебные и самые частые слова: шингл только из них — не утечка («так же как в»).
STOPWORDS = frozenset("""
а без бы был была были было в вам вас ваш весь во вот все всё вы где да даже для до его ее её если есть же за
здесь и из или им их к как ко когда кто ли мы на над не него нее неё нет ни но о об один она они оно от по под
после при про с со так также там те то того той только тот ту тут у уже чем что чтобы эта эти это этот я
ещё еще ведь вам себя себе свой своя свои своё свое том тем то-то нам нас ну ох ах чтоб
""".split())


@dataclass(frozen=True)
class Needle:
    text: str  # форма base()
    raw: str | None  # сырой вид (ищется с границами слов), если отличается
    kind: str  # answer | param | watchlist | password | title | text
    source: str
    stage: int = 0  # этап, к которому относится секрет; 0 — общий


@dataclass(frozen=True)
class Finding:
    file: str
    needle: str
    kind: str
    source: str
    form: str  # base | raw | shingle

    def __str__(self) -> str:
        return f"{self.file}: «{self.needle}» ({self.kind}, {self.form}) — из {self.source}"


def tokens(text: str) -> list[str]:
    return [t for t in base(text).split(" ") if t]


def shingles(toks: list[str], k: int = SHINGLE) -> set[str]:
    return {" ".join(toks[i:i + k]) for i in range(len(toks) - k + 1)}


def text_shingles(text: str) -> set[str]:
    """Шинглы текста; маркер TODO(content) разрывает текст (шинглы не идут через него)."""
    out: set[str] = set()
    for part in text.split(TODO_MARK):
        out |= shingles(tokens(part))
    return out


# Заглушки отсутствующих данных «Здесь будет …» (F11) шаблоны собирают из частей — это обвязка.
PLACEHOLDER = "здесь будет"


def is_stop_shingle(sh: str) -> bool:
    return all(t in STOPWORDS for t in sh.split(" ")) or PLACEHOLDER in sh


@dataclass
class NeedleSet:
    needles: list[Needle] = field(default_factory=list)
    shingles: dict[str, Needle] = field(default_factory=dict)
    short: list[tuple[str, str]] = field(default_factory=list)  # (значение, источник) — короче MIN_LEN
    exclude: set[str] = field(default_factory=set)  # шинглы «обвязки»
    _seen: set[tuple[str, str | None]] = field(default_factory=set)

    def add(self, value: str, kind: str, source: str, *, raw: str | None = None, is_base: bool = False,
            stage: int = 0) -> None:
        b = value if is_base else base(value.replace(TODO_MARK, " "))
        if not b:
            return
        if len(b) < MIN_LEN:
            self.short.append((value, source))
            return
        r = raw.strip() if raw else None
        if r and (TODO_MARK in r or base(r) == r):  # сырой вид ничего не добавляет к base()
            r = None
        key = (b, r)
        if key in self._seen:
            return
        self._seen.add(key)
        self.needles.append(Needle(b, r, kind, source, stage))

    def add_text(self, text: str, kind: str, source: str, *, stage: int = 0) -> None:
        """Шинглы всего текста (без служебных и «обвязки»)."""
        for sh in text_shingles(text):
            if sh in self.exclude or is_stop_shingle(sh) or sh in self.shingles:
                continue
            self.shingles[sh] = Needle(sh, None, kind, source, stage)

    @property
    def count(self) -> int:
        return len(self.needles) + len(self.shingles)


# ---------------------------------------------------------------- «обвязка»


def boilerplate_shingles(site_dir: Path, visible: Iterable[str] = ()) -> set[str]:
    """Шинглы статического текста шаблонов сайта, строк интерфейса и того, что видно по замыслу."""
    parts: list[str] = []
    tdir = Path(site_dir) / "templates"
    for p in sorted(tdir.rglob("*.html")) if tdir.is_dir() else []:
        # Jinja не вырезается: строки-литералы в выражениях («Здесь будет фото …») — тоже обвязка
        parts.append(_TAG.sub(" ", p.read_text(encoding="utf-8")))
    for rel in ("assets/js/app/texts.js", "assets/js/boot.js"):
        p = Path(site_dir) / rel
        if p.is_file():
            parts.append(p.read_text(encoding="utf-8"))
    parts += list(visible)
    out: set[str] = set()
    for t in parts:
        out |= text_shingles(html.unescape(t))
    return out


# ---------------------------------------------------------------- сканирование


def _json_strings(obj: Any, out: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in B64_KEYS and isinstance(v, str):
                continue
            out.append(str(k))
            _json_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _json_strings(v, out)
    elif isinstance(obj, str):
        out.append(obj)
    elif obj is not None:
        out.append(str(obj))


def json_text(obj: Any) -> str:
    parts: list[str] = []
    _json_strings(obj, parts)
    return "\n".join(parts)


def unescape(text: str) -> str:
    return html.unescape(_U_ESC.sub(lambda m: chr(int(m.group(1), 16)), text))


def file_text(path: Path) -> str | None:
    """Текст файла для поиска или ``None`` (двоичный). JSON — только строки (без n/c/солей)."""
    if path.suffix.lower() in BINARY_EXT:
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    if path.suffix.lower() == ".json":
        try:
            raw = json_text(json.loads(raw))
        except json.JSONDecodeError:
            pass
    raw = unescape(raw)
    if path.suffix.lower() in MARKUP_EXT:  # и с тегами (атрибуты), и без (видимый текст подряд)
        raw = raw + "\n" + _TAG.sub(" ", raw)
    return raw


def scan_text(text: str, ns: NeedleSet | list[Needle], where: str, *, skip_stage: int | None = None) -> list[Finding]:
    """Найти иголки в тексте. ``skip_stage`` — не искать иголки этого этапа (pack-1)."""
    needles = ns.needles if isinstance(ns, NeedleSet) else ns
    found: list[Finding] = []
    b = " " + base(text) + " "
    for nd in needles:
        if skip_stage is not None and nd.stage == skip_stage:
            continue
        if " " + nd.text + " " in b:
            found.append(Finding(where, nd.text, nd.kind, nd.source, "base"))
        elif nd.raw and re.search(rf"(?<!{_WORD}){re.escape(nd.raw)}(?!{_WORD})", text, re.IGNORECASE):
            found.append(Finding(where, nd.raw, nd.kind, nd.source, "raw"))
    if isinstance(ns, NeedleSet) and ns.shingles:
        for sh in sorted(text_shingles(text) & ns.shingles.keys()):
            nd = ns.shingles[sh]
            if skip_stage is not None and nd.stage == skip_stage:
                continue
            found.append(Finding(where, sh, nd.kind, nd.source, "shingle"))
    return found


def scan(dist: Path, ns: NeedleSet | list[Needle]) -> list[Finding]:
    """Все текстовые файлы ``dist/`` и имена всех файлов."""
    dist = Path(dist)
    found: list[Finding] = []
    names: list[str] = []
    for p in sorted(dist.rglob("*")):
        rel = p.relative_to(dist).as_posix()
        names.append(rel)
        if not p.is_file():
            continue
        text = file_text(p)
        if text is not None:
            found += scan_text(text, ns, rel)
    found += scan_text("\n".join(names), ns, FILENAMES)
    return found
