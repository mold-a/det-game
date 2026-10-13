"""Проверяемые единицы: рендер канона и вариантов → нормализация → допуски →
записи-проверки; ключи этапов (docs/02 §3.3–3.4, FORMATS §2).

Все ответы нормализуются здесь один раз (``expand_all``); дальше сборка, ``check`` и
``dump-answers`` работают с ``Expanded``.
"""

from __future__ import annotations

import calendar
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from engine import crypto
from engine.content import Content, ContentError, ContentIssue, Unit, units
from engine.models import Answer
from engine.normalize import normalize
from engine.templating import RenderError, make_context, render
from engine.util import b64u_encode, format_loc

FORBIDDEN_CHARS = ("|", crypto.UNIT_SEP)  # разделители строк ключей (labInfo, stageSecret)
WRONG_COUNT = 5  # docs/06 §3.3


@dataclass
class Expanded:
    """Нормализованный ответ единицы (или параметра экспертизы)."""

    path: str
    type: str
    input: str | list[str]  # отрендеренный канон до нормализации (что ввести в интерфейсе)
    canon: str  # нормализованный канон
    variants: list[str]  # все допустимые нормализованные варианты; канон первый
    raw: list[str] = field(default_factory=list)  # отрендеренные строки канона и вариантов (для leak scan)
    tolerance: int = 0


# ---------------------------------------------------------------- время и даты


def shift_time(hhmm: str, minutes: int) -> str:
    """``HH:MM`` ± минуты по модулю 24 ч (PLAN C10)."""
    h, m = int(hhmm[:2]), int(hhmm[3:5])
    t = (h * 60 + m + minutes) % (24 * 60)
    return f"{t // 60:02d}:{t % 60:02d}"


def iso_to_dmy(iso: str) -> str:
    return f"{iso[8:10]}.{iso[5:7]}.{iso[0:4]}"


def _add_months(d: date, k: int) -> date:
    y, m = divmod(d.month - 1 + k, 12)
    y += d.year
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


# ---------------------------------------------------------------- раскрытие ответа


def expand_answer(path: str, type_: str, answer: Answer, ctx: dict, default_year: int,
                  where: str) -> Expanded:
    """Рендер → нормализация → допуск. Ошибка → ``ValueError`` с понятным текстом."""

    def rnd(s: str, sub: str) -> str:
        try:
            return render(s, ctx, f"{where}.{sub}")
        except RenderError as e:
            raise ValueError(str(e)) from None

    if isinstance(answer.canon, list):
        inp: str | list[str] = [rnd(x, "canon") for x in answer.canon]
        raw: list[str] = []
    else:
        inp = rnd(answer.canon, "canon")
        raw = [inp]
    canon = normalize(type_, inp, default_year=default_year)
    if canon is None:
        raise ValueError(f"канон {inp!r} не проходит нормализацию type: {type_}")
    variants = [canon]
    for i, v in enumerate(answer.variants):
        rv = rnd(v, f"variants[{i}]")
        raw.append(rv)
        nv = normalize(type_, rv, default_year=default_year)
        if nv is None:
            raise ValueError(f"вариант {rv!r} не проходит нормализацию type: {type_}")
        variants.append(nv)
    tol = answer.tolerance_min or 0
    if type_ == "time" and tol:
        variants = [shift_time(v, d) for v in variants for d in range(-tol, tol + 1)]
    seen: dict[str, None] = {}
    for v in variants:
        seen.setdefault(v, None)
    out = list(seen)
    for v in out:
        if any(ch in v for ch in FORBIDDEN_CHARS):
            raise ValueError(f"значение {v!r} содержит запрещённый разделитель («|» или \\x1f)")
    return Expanded(path=path, type=type_, input=inp, canon=canon, variants=out, raw=raw, tolerance=tol)


def iter_units_with_loc(content: Content):
    """``(unit, loc)`` — loc ответа в stages.yaml (для сообщений об ошибках)."""
    by_path = {u.path: u for u in units(content)}
    for si, st in enumerate(content.stages):
        for qi, q in enumerate(st.questions):
            if q.type == "form":
                for fi, f in enumerate(q.fields or []):
                    yield by_path[f"s{st.n}.{q.id}.{f.id}"], ("stages", si, "questions", qi, "fields", fi, "answer")
            else:
                yield by_path[f"s{st.n}.{q.id}"], ("stages", si, "questions", qi, "answer")


def expand_all(content: Content, ctx: dict | None = None) -> dict[str, Expanded]:
    """Все единицы → ``{path: Expanded}`` в порядке ``units()``. Ошибки — ``ContentError``."""
    ctx = ctx or make_context(content)
    year = content.settings.default_year
    out: dict[str, Expanded] = {}
    errors: list[ContentIssue] = []
    file = f"{content.root.name}/stages.yaml"
    for u, loc in iter_units_with_loc(content):
        try:
            out[u.path] = expand_answer(u.path, u.type, u.spec.answer, ctx, year, f"{file}: {format_loc(loc)}")
        except ValueError as e:
            errors.append(ContentIssue(file, format_loc(loc), str(e)))
    if errors:
        raise ContentError(errors)
    return out


# ---------------------------------------------------------------- записи-проверки


def check_entries(path: str, exp: Expanded, salt: bytes, iters: int, pad: int,
                  *, key_cache: dict | None = None) -> list[dict]:
    """Записи для каждого варианта + паддинг до ``pad``; перемешаны (docs/02 §3.3)."""
    entries = []
    for v in exp.variants:
        ck = (path, v)
        if key_cache is not None and ck in key_cache:
            key = key_cache[ck]
        else:
            key = crypto.answer_key(path, v, salt, iters)
            if key_cache is not None:
                key_cache[ck] = key
        entries.append(crypto.seal_answer(key, path, exp.canon))
    # все записи единицы одной длины: открытый текст выровнен (crypto.answer_plaintext)
    ct_len = crypto.answer_ct_len(exp.canon)
    while len(entries) < pad:
        entries.append(crypto.fake_container(crypto.answer_aad(path), ct_len))
    secrets.SystemRandom().shuffle(entries)
    return entries


def pad_and_shuffle(entries: list[dict], aad: str, pad: int, default_len: int = 256) -> list[dict]:
    """Дополнить записи случайными (длина — как у случайной настоящей) и перемешать."""
    rnd = secrets.SystemRandom()
    out = list(entries)
    lens = [len(crypto.b64u_decode(e["c"])) for e in entries] or [default_len]
    while len(out) < pad:
        out.append(crypto.fake_container(aad, rnd.choice(lens)))
    rnd.shuffle(out)
    return out


# ---------------------------------------------------------------- ключи этапов


def mandatory_pairs(content: Content, expanded: dict[str, Expanded], n: int) -> list[tuple[str, str]]:
    """Обязательные единицы этапа ``n`` в порядке content (поля формы — по порядку)."""
    return [(u.path, expanded[u.path].canon) for u in units(content) if u.stage == n and u.kind == "mandatory"]


def stage_keys(content: Content, salts: Any, expanded: dict[str, Expanded]) -> dict[int, bytes]:
    """``{n: K_n}`` для всех этапов (docs/02 §3.4)."""
    iters = content.settings.crypto.iter_stage
    keys = {1: crypto.start_key(salts.start, iters)}
    for st in content.stages[:-1]:
        pairs = mandatory_pairs(content, expanded, st.n)
        keys[st.n + 1] = crypto.stage_key(st.n, pairs, salts.stage(st.n), iters)
    return keys


# ---------------------------------------------------------------- order


def order_shuffle(item_ids: list[str], answer: list[str], salt: bytes) -> list[str]:
    """Детерминированная перестановка карточек (затравка — соль единицы); ≠ ответу (PLAN C3)."""
    ids = list(item_ids)
    for i in range(len(ids) - 1, 0, -1):
        h = hashlib.sha256(salt + b"order" + i.to_bytes(4, "big")).digest()
        j = int.from_bytes(h[:8], "big") % (i + 1)
        ids[i], ids[j] = ids[j], ids[i]
    if ids == list(answer) and len(ids) > 1:
        ids = ids[1:] + ids[:1]
    return ids


# ---------------------------------------------------------------- неверные ответы (check, dump)


def wrong_inputs(unit: Unit, exp: Expanded, content: Content, expanded: dict[str, Expanded]) -> list:
    """5 правдоподобных неверных вводов (docs/06 §3.3). Каждый нормализуется и не входит в варианты."""
    year = content.settings.default_year
    spec = unit.spec
    t = unit.type
    cands: list[Any] = []
    if t == "time":
        d = exp.tolerance + 1
        cands = [shift_time(exp.canon, -d), shift_time(exp.canon, d), shift_time(exp.canon, 60),
                 shift_time(exp.canon, -60), shift_time(exp.canon, 12 * 60), shift_time(exp.canon, d + 10)]
    elif t == "date":
        dd = date.fromisoformat(exp.canon)
        ds = [dd - timedelta(days=1), dd + timedelta(days=1), _add_months(dd, 1), _add_months(dd, -1),
              dd.replace(year=dd.year + 1) if not (dd.month == 2 and dd.day == 29) else dd + timedelta(days=366)]
        cands = [x.strftime("%d.%m.%Y") for x in ds]
    elif t == "number":
        n = int(exp.canon)
        cands = [str(n + 1), str(max(n - 1, 0)), str(n + 10), str(n * 10 + 1), "0", str(n + 100)]
    elif t == "text":
        others = [e.input for p, e in expanded.items() if e.type == "text" and p != unit.path]
        s = exp.input if isinstance(exp.input, str) else ""
        cands = [*others, s[: max(1, len(s) // 2)], "нет", "не знаю", "другое", "1"]
    elif t in ("choice", "person", "document"):
        if t == "choice":
            pool = [o.id for o in spec.options or []]
        elif t == "person":
            pool = content.pool(spec) + [c.id for c in content.characters]
        else:
            pool = [d.id for d in content.documents if d.stage <= unit.stage]
            pool += [d.id for d in content.documents]
        if exp.canon in pool:  # соседние варианты списка — первыми
            i = pool.index(exp.canon)
            pool = sorted(pool, key=lambda x: abs(pool.index(x) - i))
        cands = pool + [c.id for c in content.characters] + [d.id for d in content.documents]
    elif t in ("persons", "multi"):
        canon = exp.canon.split(",")
        pool = content.pool(spec) if t == "persons" else [o.id for o in spec.options or []]
        extra = [x for x in pool if x not in canon]
        cands = [canon[:-1], canon[1:]]
        if extra:
            cands += [canon + extra[:1], [extra[0]]]
        cands += [pool, [canon[0]], canon + extra[1:2], extra[:2], *([x] for x in extra[1:])]
    elif t == "order":
        a = list(exp.input)
        sw = lambda i, j: [*a[:i], a[j], *a[i + 1:j], a[i], *a[j + 1:]]  # noqa: E731
        k = len(a)
        cands = [sw(0, 1), sw(k - 2, k - 1), sw(k // 2 - 1, k // 2), list(reversed(a)), a[1:] + a[:1], sw(0, k - 1)]
    out: list = []
    seen: set[str] = set()
    for c in cands:
        if isinstance(c, list) and not c:
            continue
        nv = normalize(t, c, default_year=year)
        if nv is None or nv in exp.variants or nv in seen:
            continue
        seen.add(nv)
        out.append(c)
        if len(out) == WRONG_COUNT:
            break
    return out


# ---------------------------------------------------------------- текст верного ответа (FORMATS F10)


def display_answer(unit: Unit, exp: Expanded, content: Content, ctx: dict) -> str:
    c = ctx["c"]
    spec = unit.spec
    t = unit.type
    if t in ("text", "time", "number"):
        return exp.input if isinstance(exp.input, str) else exp.canon
    if t == "date":
        return iso_to_dmy(exp.canon)
    if t in ("choice", "multi"):
        texts = {o.id: render(o.text, ctx) for o in spec.options or []}
        if t == "choice":
            return texts[exp.canon]
        chosen = set(exp.canon.split(","))
        return "; ".join(texts[o.id] for o in spec.options if o.id in chosen)
    if t == "person":
        return getattr(c, exp.canon).full()
    if t == "persons":
        chosen = set(exp.canon.split(","))
        return ", ".join(getattr(c, pid).full() for pid in content.pool(spec) if pid in chosen)
    if t == "document":
        d = content.documents_by_id[exp.canon]
        return f"{d.id} — {render(d.title, ctx)}"
    if t == "order":
        texts = {it.id: render(it.text, ctx) for it in spec.items or []}
        return " → ".join(texts[i] for i in exp.canon.split(","))
    raise ValueError(t)


def unit_salt_b64(salts: Any, path: str) -> str:
    return b64u_encode(salts.unit(path))
