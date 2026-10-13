"""Leak scan (docs/06 §3.7, PLAN §9 вопрос 9, F4–F6).

«Иголки» — то, чего не должно быть в ``dist/`` в открытом виде:
- нормализованные каноны и варианты единиц ``text``/``time``/``date``/``number`` (кроме ``leak_scan: false``);
- начала текстов (целые токены ``base()`` до 40 символов, минимум 3 токена; короткий текст — целиком):
  подсказки, вводные письма этапов 2…N, результаты экспертиз, развязка, тексты закрытых страниц;
- ``settings.leak_watchlist``; значения ``params_answer``; пароль облака.

Значения короче 4 символов после нормализации не ищутся (F5) и перечисляются в отчёте.
Поиск — по целым токенам в форме ``base()`` и в сыром виде с границами слов; перед поиском
раскрываются ``\\uXXXX`` и HTML-сущности; поля ``n``/``c`` контейнеров, соли и ключи
в JSON и файлы ``*.bin`` пропускаются.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.normalize import base

TEXT_EXT = {".html", ".js", ".mjs", ".css", ".json", ".svg", ".txt", ".xml"}
MIN_LEN = 4
SNIPPET_MAX = 40
SNIPPET_MIN_TOKENS = 3
TODO_MARK = "TODO(content)"
# Значения JSON, которые — случайные байты в base64url (ложные совпадения): поля контейнера и соли/ключи.
B64_KEYS = {"n", "c", "salt", "saltStart", "saltStage", "key", "saltsId", "buildId"}
_U_ESC = re.compile(r"\\u([0-9a-fA-F]{4})")
_WORD = r"[0-9A-Za-zА-Яа-яЁё]"


@dataclass(frozen=True)
class Needle:
    text: str  # форма base()
    raw: str | None  # сырой вид (ищется с границами слов), если отличается
    kind: str  # answer | snippet | watchlist | param | password
    source: str


@dataclass(frozen=True)
class Finding:
    file: str
    needle: str
    kind: str
    source: str
    form: str  # base | raw

    def __str__(self) -> str:
        return f"{self.file}: «{self.needle}» ({self.kind}, {self.form}) — из {self.source}"


def snippet(text: str) -> str:
    """Начало текста для поиска: целые токены base(), пока длина ≤ 40 (минимум 3 токена)."""
    toks = base(text.replace(TODO_MARK, " ")).split(" ")
    toks = [t for t in toks if t]
    out: list[str] = []
    for t in toks:
        cand = " ".join([*out, t])
        if len(out) >= SNIPPET_MIN_TOKENS and len(cand) > SNIPPET_MAX:
            break
        out.append(t)
    return " ".join(out)


class NeedleSet:
    def __init__(self) -> None:
        self.needles: list[Needle] = []
        self.short: list[tuple[str, str]] = []  # (значение, источник) — короче MIN_LEN, не ищутся
        self._seen: set[tuple[str, str | None]] = set()

    def add(self, value: str, kind: str, source: str, *, raw: str | None = None, is_base: bool = False) -> None:
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
        self.needles.append(Needle(b, r, kind, source))

    def add_snippet(self, text: str, kind: str, source: str) -> None:
        s = snippet(text)
        if s:
            self.add(s, kind, source, is_base=True)


def collect_needles(prep: Any, rendered_texts: list[tuple[str, str]], locked_texts: list[tuple[str, str]]) -> NeedleSet:
    """Иголки из подготовленного контента (``build.Prepared``).

    ``rendered_texts`` — уже отрендеренные тексты (подсказки, письма, документы, судьбы) с источниками;
    ``locked_texts`` — строки закрытых страниц: берутся только тексты из ≥ 3 токенов.
    """
    from engine.answers import iso_to_dmy
    from engine.content import units

    content = prep.content
    ns = NeedleSet()
    for u in units(content):
        if u.type not in ("text", "time", "date", "number") or not u.leak_scan:
            continue
        exp = prep.expanded[u.path]
        for v in exp.variants:
            ns.add(v, "answer", u.path)
            if u.type == "date":
                ns.add(iso_to_dmy(v), "answer", u.path)
        for r in exp.raw:
            ns.add(r, "answer", u.path, raw=r)
    for rid, (params, _) in prep.params.items():
        for pid, exp in params.items():
            for v in exp.variants:
                ns.add(v, "param", f"{rid}.{pid}")
                if exp.type == "date":
                    ns.add(iso_to_dmy(v), "param", f"{rid}.{pid}")
            for r in exp.raw:
                ns.add(r, "param", f"{rid}.{pid}", raw=r)
    for w in content.settings.leak_watchlist:
        ns.add(w, "watchlist", "settings.leak_watchlist", raw=w)
    for source, text in rendered_texts:
        ns.add_snippet(text, "snippet", source)
    for source, text in locked_texts:
        if len(snippet(text).split(" ")) >= SNIPPET_MIN_TOKENS:
            ns.add_snippet(text, "page", source)
    cloud = content.pages.get("cloud")
    pw = getattr(cloud, "password", None)
    if pw and TODO_MARK not in pw:
        from engine.normalize import normalize

        npw = normalize("password", pw)
        if npw:
            ns.add(npw, "password", "content/pages/cloud/page.yaml: password", is_base=True)
            ns.add(pw, "password", "content/pages/cloud/page.yaml: password", raw=pw)
    return ns


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


def file_text(path: Path) -> str:
    """Текст файла для поиска: JSON — только строки (без n/c/солей), ``\\uXXXX`` и сущности раскрыты."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".json":
        try:
            parts: list[str] = []
            _json_strings(json.loads(raw), parts)
            raw = "\n".join(parts)
        except json.JSONDecodeError:
            pass
    raw = _U_ESC.sub(lambda m: chr(int(m.group(1), 16)), raw)
    return html.unescape(raw)


def scan_text(text: str, needles: list[Needle], where: str) -> list[Finding]:
    found: list[Finding] = []
    b = " " + base(text) + " "
    for nd in needles:
        if " " + nd.text + " " in b:
            found.append(Finding(where, nd.text, nd.kind, nd.source, "base"))
        elif nd.raw and re.search(rf"(?<!{_WORD}){re.escape(nd.raw)}(?!{_WORD})", text, re.IGNORECASE):
            found.append(Finding(where, nd.raw, nd.kind, nd.source, "raw"))
    return found


def scan(dist: Path, needles: list[Needle]) -> list[Finding]:
    dist = Path(dist)
    found: list[Finding] = []
    for p in sorted(dist.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT:
            continue
        found += scan_text(file_text(p), needles, p.relative_to(dist).as_posix())
    return found
