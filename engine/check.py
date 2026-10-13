"""Самопроверка собранного ``dist/`` — docs/06 §3, пункты 1–9.

Проверяется **записанный** ``dist/``: правильные ответы берутся из контента, ключи
выводятся по файлам ``dist/data/*.json`` так же, как это делает браузер.
"""

from __future__ import annotations

import html as html_mod
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from engine import ROOT, crypto
from engine import salts as salts_mod
from engine.answers import shift_time, wrong_inputs
from engine.build import BuildError, Prepared, prepare, release_problems
from engine.content import collect_todos, units
from engine.leakscan import NeedleSet, collect_needles, scan
from engine.media import MediaPlan, media_hash
from engine.normalize import base, normalize
from engine.pages import access_of, cloud_password_norm, locked_page_texts
from engine.templating import render

# Нейтральные примеры формата в интерфейсе (docs/02 §2): «например 08:15», placeholder и т. п.
_EXAMPLE_RES = [
    re.compile(r"например,?\s+([0-9][0-9.:\-]*[0-9])"),
    re.compile(r"placeholder=\"([^\"]+)\""),
    re.compile(r"\"(\d{1,2}[:.]\d{2}(?:\.\d{2,4})?)\""),
]
_TAG = re.compile(r"<[^>]+>")


@dataclass
class Row:
    name: str
    ok: bool
    detail: str


@dataclass
class CheckReport:
    rows: list[Row] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    stats: list[tuple[str, str]] = field(default_factory=list)
    todos: list = field(default_factory=list)
    short_needles: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.rows)

    def add(self, name: str, problems: list[str], detail: str) -> None:
        self.rows.append(Row(name, not problems, detail if not problems else f"{len(problems)} ошибок; {detail}"))
        self.problems += [f"[{name}] {p}" for p in problems]

    def table(self) -> str:
        w = max(len(r.name) for r in self.rows) if self.rows else 10
        lines = [f"{'Проверка'.ljust(w)}  Итог  Подробности", f"{'-' * w}  ----  -----------"]
        for r in self.rows:
            lines.append(f"{r.name.ljust(w)}  {'OK  ' if r.ok else 'FAIL'}  {r.detail}")
        if self.stats:
            lines.append("")
            sw = max(len(k) for k, _ in self.stats)
            lines += [f"{k.ljust(sw)}  {v}" for k, v in self.stats]
        if self.problems:
            lines.append("")
            lines.append(f"Ошибки ({len(self.problems)}):")
            lines += [f"  {p}" for p in self.problems[:200]]
        return "\n".join(lines)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _open_json(key: bytes, box: dict, aad: str) -> Any:
    return json.loads(crypto.open_(key, box, aad).decode("utf-8"))


def page_text(fragment_html: str) -> str:
    """Видимый текст фрагмента: без тегов, сущности раскрыты."""
    return html_mod.unescape(_TAG.sub(" ", fragment_html))


def secret_texts(prep: Prepared) -> list[tuple[str, str]]:
    """Отрендеренные закрытые тексты для leak scan: подсказки, письма 2…N, экспертизы, развязка."""
    content, ctx = prep.content, prep.ctx
    out: list[tuple[str, str]] = []
    for si, st in enumerate(content.stages):
        if si > 0:
            out.append((f"stages[{si}].intro", render(st.intro, ctx)))
        for qi, q in enumerate(st.questions):
            for hi, h in enumerate(q.hints):
                out.append((f"stages[{si}].questions[{qi}].hints[{hi}]", render(h, ctx)))
    for r in content.expertise.results:
        if r.text:
            out.append((f"expertise {r.id}.text", render(r.text, ctx)))
        if r.body and r.body in content.docs:
            out.append((f"content/{r.body}", render(content.docs[r.body].body, ctx)))
    for rel in (content.finale.confession, content.finale.letter):
        if rel in content.docs:
            out.append((f"content/{rel}", render(content.docs[rel].body, ctx)))
    for i, f in enumerate(content.finale.fates):
        out.append((f"finale.fates[{i}]", render(f.text, ctx)))
    return out


def leak_needles(prep: Prepared) -> NeedleSet:
    return collect_needles(prep, secret_texts(prep), locked_page_texts(prep.content, prep.ctx))


def check(
    root: Path = ROOT,
    *,
    content_dir: Path | None = None,
    media_dir: Path | None = None,
    dist: Path | None = None,
    salts_path: Path | None = None,
    release: bool = False,
    log: Callable[[str], None] | None = None,
) -> CheckReport:
    root = Path(root)
    dist = Path(dist or root / "dist")
    media_dir = Path(media_dir or root / "media")
    rep = CheckReport()
    prep = prepare(Path(content_dir or root / "content"), Path(salts_path or salts_mod.SALTS_LOCK),
                   create_salts=False)
    content = prep.content
    s = content.settings
    data = dist / "data"
    if not (data / "public.json").is_file():
        raise BuildError([f"нет {data / 'public.json'} — сначала python -m engine build"])
    pub = _load(data / "public.json")
    all_units = units(content)
    key_cache: dict[tuple[str, str], bytes] = {}

    def akey(path: str, value: str, salt: bytes) -> bytes:
        k = (path, value)
        if k not in key_cache:
            key_cache[k] = crypto.answer_key(path, value, salt, pub["iter"]["answer"])
        return key_cache[k]

    # 1. Прохождение
    problems: list[str] = []
    packs: dict[int, dict] = {}
    keys: dict[int, bytes] = {}
    if pub.get("saltsId") != prep.salts.id:
        problems.append("saltsId в public.json не совпадает с salts.lock.json")
    keys[1] = crypto.start_key(crypto.b64u_decode(pub["saltStart"]), pub["iter"]["stage"])
    for st in content.stages:
        n = st.n
        try:
            box = _load(data / f"pack-{n}.json")
            packs[n] = _open_json(crypto.hkdf(keys[n], crypto.pack_info(n)), box, f"pack/{n}")
        except (OSError, crypto.CryptoError, KeyError) as e:
            problems.append(f"pack-{n}: не открылся ({e})")
            break
        pack = packs[n]
        if pack.get("n") != n:
            problems.append(f"pack-{n}: поле n = {pack.get('n')}")
        if n < content.last_stage:
            pairs = [(u.path, prep.expanded[u.path].canon) for u in all_units if u.stage == n and u.kind == "mandatory"]
            keys[n + 1] = crypto.stage_key(n, pairs, crypto.b64u_decode(pack["saltStage"]), pub["iter"]["stage"])
    for n, k in keys.items():
        if prep.keys.get(n) != k:
            problems.append(f"K_{n}: ключ из dist не совпадает с ключом из контента")
    rep.add("1. Прохождение", problems, f"этапов открыто: {len(packs)} из {len(content.stages)}")

    # единицы пакетов по путям
    pack_units: dict[str, dict] = {}
    for pack in packs.values():
        for q in pack["questions"]:
            for obj in q.get("fields", [q]):
                if "unit" in obj:
                    pack_units[obj["unit"]["path"]] = obj["unit"]

    # 2. Все варианты
    problems = []
    n_variants = 0
    for u in all_units:
        pu = pack_units.get(u.path)
        if pu is None:
            problems.append(f"{u.path}: единицы нет в пакете")
            continue
        exp = prep.expanded[u.path]
        salt = crypto.b64u_decode(pu["salt"])
        if len(pu["entries"]) < s.crypto.entries_pad:
            problems.append(f"{u.path}: записей {len(pu['entries'])} < entries_pad")
        lens = {len(e["c"]) for e in pu["entries"]}
        if len(lens) != 1:
            problems.append(f"{u.path}: записи разной длины")
        for v in exp.variants:
            n_variants += 1
            got = crypto.check_answer(akey(u.path, v, salt), u.path, pu["entries"])
            if got != exp.canon:
                problems.append(f"{u.path}: вариант {v!r} → {got!r}, ожидался канон {exp.canon!r}")
    rep.add("2. Все варианты", problems, f"единиц: {len(all_units)}, вариантов: {n_variants}")

    # 3. Неверные ответы
    problems = []
    n_wrong = 0
    for u in all_units:
        pu = pack_units.get(u.path)
        if pu is None:
            continue
        exp = prep.expanded[u.path]
        salt = crypto.b64u_decode(pu["salt"])
        wrong = wrong_inputs(u, exp, content, prep.expanded)
        if len(wrong) < 5:
            problems.append(f"{u.path}: удалось подобрать только {len(wrong)} неверных ответов")
        if u.type not in ("multi", "persons", "order") and normalize(u.type, "", default_year=s.default_year) is not None:
            problems.append(f"{u.path}: пустая строка проходит нормализацию")
        for w in wrong:
            n_wrong += 1
            nv = normalize(u.type, w, default_year=s.default_year)
            if crypto.check_answer(akey(u.path, nv, salt), u.path, pu["entries"]) is not None:
                problems.append(f"{u.path}: неверный ответ {w!r} принят")
    rep.add("3. Неверные ответы", problems, f"проверено: {n_wrong} + пустой ввод")

    # 4. Экспертизы
    problems = []
    n_lab = 0
    objects = {o.id: o for o in content.expertise.objects}
    for r in content.expertise.results:
        params, combos = prep.params[r.id]
        n = r.stage
        if n not in packs:
            problems.append(f"{r.id}: пакет этапа {n} не открыт")
            continue
        entries = packs[n]["lab"]["entries"]
        for t in r.types:
            for b in r.bases:
                for p in combos:
                    n_lab += 1
                    pt = crypto.try_entries(crypto.hkdf(keys[n], crypto.lab_info(r.object, t, b, list(p))), entries, "lab")
                    if pt is None:
                        problems.append(f"{r.id}: не открылась ({t}, {b}, {'|'.join(p)})")
                        continue
                    rec = json.loads(pt)
                    if rec.get("doc") != r.doc:
                        problems.append(f"{r.id}: doc {rec.get('doc')!r} вместо {r.doc!r}")
        t, b, p = r.types[0], r.bases[0], list(combos[0]) if combos else []
        # до своего этапа
        for m in range(1, n):
            if m in packs and crypto.try_entries(crypto.hkdf(keys[m], crypto.lab_info(r.object, t, b, p)),
                                                 packs[m]["lab"]["entries"], "lab"):
                problems.append(f"{r.id}: открылась на этапе {m} — раньше своего этапа {n}")
        # чужое основание
        other = next((d.id for d in content.documents if d.stage <= n and d.id not in r.bases
                      and not any(x.object == r.object and t in x.types and d.id in x.bases
                                  for x in content.expertise.results)), None)
        if other is not None:
            for m in range(1, n + 1):
                if m in packs and crypto.try_entries(crypto.hkdf(keys[m], crypto.lab_info(r.object, t, other, p)),
                                                     packs[m]["lab"]["entries"], "lab"):
                    problems.append(f"{r.id}: открылась с чужим основанием {other}")
        # неверный параметр
        for i, prm in enumerate(objects[r.object].params or []):
            exp = params[prm.id]
            bad = {"time": lambda v: shift_time(v, exp.tolerance + 1),
                   "number": lambda v: str(int(v) + 1),
                   "date": lambda v: v[:8] + ("02" if v[8:] == "01" else "01"),
                   "text": lambda v: v + "х"}[prm.type](exp.canon)
            if bad in exp.variants:
                continue
            q = list(p)
            q[i] = bad
            if crypto.try_entries(crypto.hkdf(keys[n], crypto.lab_info(r.object, t, b, q)), entries, "lab"):
                problems.append(f"{r.id}: открылась с неверным параметром {prm.id}={bad}")
    rep.add("4. Экспертизы", problems, f"результатов: {len(content.expertise.results)}, запросов: {n_lab}")

    # 5. Страницы (+ forbidden)
    problems = []
    fragments: dict[str, str] = {}
    for slug, page in content.pages.items():
        pdir = dist / "p" / slug
        access = access_of(page)
        if not (pdir / "index.html").is_file():
            problems.append(f"{slug}: нет index.html")
            continue
        try:
            if access == "open":
                if (pdir / "payload.json").exists():
                    problems.append(f"{slug}: у открытой страницы есть payload.json")
                fragments[slug] = (pdir / "index.html").read_text(encoding="utf-8")
                continue
            box = _load(pdir / "payload.json")
            if access == "key":
                inner = _open_json(prep.salts.page_key(slug), box, f"page/{slug}")
            else:
                key = crypto.cloud_key(cloud_password_norm(page), crypto.b64u_decode(box["salt"]), box["iter"])
                inner = _open_json(key, box["box"], f"page/{slug}")
            if inner.get("slug") != slug or not inner.get("html"):
                problems.append(f"{slug}: неверное содержимое payload")
            fragments[slug] = inner.get("html", "")
        except (OSError, crypto.CryptoError, KeyError, ValueError) as e:
            problems.append(f"{slug}: не открылась ({e})")
    for slug, page in content.pages.items():
        text = " " + base(page_text(fragments.get(slug, ""))) + " "
        for word in page.forbidden:
            if base(word) and base(word) in text:
                problems.append(f"{slug}: на странице есть запрещённое «{word}» (forbidden)")
    rep.add("5. Страницы", problems,
            f"страниц: {len(content.pages)} (" + ", ".join(f"{k}: {access_of(v)}" for k, v in content.pages.items()) + ")")

    # 6. Развязка
    problems = []
    try:
        fin = _open_json(crypto.hkdf(keys[content.last_stage], crypto.FINALE_INFO), _load(data / "finale.json"),
                         "finale")
        missing = [u.path for u in all_units if u.path not in fin.get("answers", {})]
        if missing:
            problems.append(f"в answers нет единиц: {', '.join(missing)}")
        if len(fin.get("fates", [])) != len(content.finale.fates):
            problems.append("число судеб не совпадает с finale.yaml")
    except (OSError, crypto.CryptoError, KeyError) as e:
        problems.append(f"finale.json не открылся ({e})")
    rep.add("6. Развязка", problems, f"открыта ключом этапа {content.last_stage}")

    # 7. Leak scan + медиа + нейтральные примеры
    ns = leak_needles(prep)
    rep.short_needles = ns.short
    findings = scan(dist, ns.needles)
    problems = [str(f) for f in findings]
    plan = MediaPlan(content, media_dir)
    mdir = dist / "m"
    open_hashes = set()
    if mdir.is_dir():
        for p in mdir.iterdir():
            if p.suffix != ".bin":
                open_hashes.add(media_hash(p.read_bytes()))
    for mf in plan.files.values():
        if not mf.exists:
            continue
        if mf.encrypted and mf.hash in open_hashes:
            problems.append(f"медиа {mf.rel} используется только зашифрованным контентом, но лежит открытым")
        expected = mdir / mf.out_name
        if not expected.is_file():
            problems.append(f"медиа {mf.rel}: нет файла {expected.relative_to(dist).as_posix()}")
    examples = neutral_examples(dist)
    for ex in sorted(examples):
        for u in all_units:
            if u.type in ("time", "date", "number", "text"):
                nv = normalize(u.type, ex, default_year=s.default_year)
                if nv is not None and nv in prep.expanded[u.path].variants:
                    problems.append(f"нейтральный пример «{ex}» совпадает с ответом {u.path}")
    short = ", ".join(sorted({v for v, _ in ns.short})) or "—"
    rep.add("7. Leak scan", problems,
            f"иголок: {len(ns.needles)}, примеров интерфейса: {len(examples)}; короче 4 символов (не ищутся): {short}")

    # 8. Заглушки
    todos = collect_todos(content)
    rep.todos = todos
    problems = release_problems(content, todos, sorted(mf.rel for mf in plan.missing)) if release else []
    by_kind: dict[str, int] = {}
    for t in todos:
        by_kind[t.kind] = by_kind.get(t.kind, 0) + 1
    rep.add("8. Заглушки", problems,
            f"TODO(content): {len(todos)} (" + ", ".join(f"{k}: {v}" for k, v in sorted(by_kind.items()))
            + f"); нет медиа: {len(plan.missing)}" + ("" if release else "; без --release — не ошибка"))

    # 9. Отчёт
    files = [p for p in dist.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    biggest = max(files, key=lambda p: p.stat().st_size)
    lab_total = sum(len(pk["lab"]["entries"]) for pk in packs.values())
    rep.stats = [
        ("Этапов", str(len(content.stages))),
        ("Единиц", f"{len(all_units)} (обязательных {sum(u.kind == 'mandatory' for u in all_units)})"),
        ("Вариантов", str(n_variants)),
        ("Экспертиз", f"{len(content.expertise.results)} результатов, {n_lab} запросов, {lab_total} записей с паддингом"),
        ("Страниц", str(len(content.pages))),
        ("Размер dist/", f"{size / 1024:.1f} КБ, файлов {len(files)}"),
        ("Самый большой файл", f"{biggest.relative_to(dist).as_posix()} ({biggest.stat().st_size / 1024:.1f} КБ)"),
    ]
    rep.add("9. Отчёт", [], f"dist/: {size / 1024:.1f} КБ")
    if log:
        log(rep.table())
    return rep


def neutral_examples(dist: Path) -> set[str]:
    """Примеры формата из интерфейса: «например …», placeholder, строки вида «08:15» в JS."""
    out: set[str] = set()
    for p in dist.rglob("*"):
        if p.is_file() and p.suffix in (".html", ".js", ".mjs") and "/p/" not in "/" + p.relative_to(dist).as_posix():
            text = p.read_text(encoding="utf-8", errors="replace")
            for rx in _EXAMPLE_RES:
                out.update(m.strip() for m in rx.findall(text) if any(ch.isdigit() for ch in m))
    return out


