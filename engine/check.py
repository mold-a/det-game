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
from engine.answers import iso_to_dmy, shift_time, wrong_inputs
from engine.build import BuildError, Prepared, prepare, release_problems
from engine.content import Content, collect_todos, units
from engine.leakscan import (
    NeedleSet,
    boilerplate_shingles,
    json_text,
    markup_text,
    scan,
    scan_text,
    text_shingles,
    unescape,
)
from engine.media import MEDIA_DIR, MediaPlan, media_hash
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


SITE = ROOT / "site"
# Поля пакета, которые не текст для игрока (структура, ID, служебное) — не источник шинглов.
_PACK_SKIP = {"v", "n", "id", "path", "kind", "type", "link", "envelope", "stage", "saltStage", "unit", "pool",
              "ord", "characters", "entries", "lab"}
# Поля персонажа в пакете (PLAN B3, FORMATS §2.2).
CHARACTER_FIELDS = {"id", "full", "short", "photo"}


@dataclass
class Decrypted:
    """То, что check расшифровал из dist/ (как браузер)."""

    packs: dict[int, dict] = field(default_factory=dict)
    lab: dict[str, dict] = field(default_factory=dict)  # result id → запись
    finale: dict | None = None
    pages: dict[str, str] = field(default_factory=dict)  # slug закрытой страницы → HTML фрагмента


def _pack_strings(obj: Any, out: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _PACK_SKIP:
                continue
            _pack_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _pack_strings(v, out)
    elif isinstance(obj, str):
        out.append(page_text(obj) if "<" in obj else obj)


def secret_texts(prep: Prepared, dec: Decrypted | None = None) -> list[tuple[str, str, int]]:
    """Закрытые тексты для шинглов: ``(источник, текст, этап)``.

    С ``dec`` — расшифрованное из dist/ (то, что видит игрок: шаблоны, даты в формате показа);
    без него — отрендеренные строки контента.
    """
    content, ctx = prep.content, prep.ctx
    last = content.last_stage
    out: list[tuple[str, str, int]] = []
    if dec is not None:
        for n, pack in dec.packs.items():
            if n == content.stages[0].n:
                for q in pack["questions"]:
                    out += [(f"pack-{n} {q['path']}.hints", h, n) for h in q.get("hints", [])]
                continue
            parts: list[str] = []
            _pack_strings(pack, parts)
            parts += [o["title"] for o in pack.get("lab", {}).get("objects", [])]
            out += [(f"pack-{n}", t, n) for t in parts]
        stage_of = {r.id: r.stage for r in content.expertise.results}
        for rid, rec in dec.lab.items():
            out.append((f"экспертиза {rid}", rec.get("title", "") + "\n" + page_text(rec.get("html", "")), stage_of[rid]))
        if dec.finale:
            for k in ("confession", "letter"):
                d = dec.finale.get(k) or {}
                out.append((f"развязка {k}", d.get("title", "") + "\n" + page_text(d.get("html", "")), last))
            out += [(f"развязка fates[{i}]", f.get("text", ""), last) for i, f in enumerate(dec.finale.get("fates", []))]
        docs = content.documents_by_id
        for slug, frag in dec.pages.items():
            out.append((f"страница {slug}", page_text(frag), docs[content.pages[slug].doc].stage))
        return out
    for si, st in enumerate(content.stages):
        if si > 0:
            out.append((f"stages[{si}].intro", render(st.intro, ctx), st.n))
        for qi, q in enumerate(st.questions):
            for hi, h in enumerate(q.hints):
                out.append((f"stages[{si}].questions[{qi}].hints[{hi}]", render(h, ctx), st.n))
    for r in content.expertise.results:
        if r.text:
            out.append((f"expertise {r.id}.text", render(r.text, ctx), r.stage))
        if r.body and r.body in content.docs:
            out.append((f"content/{r.body}", render(content.docs[r.body].body, ctx), r.stage))
    for rel in (content.finale.confession, content.finale.letter):
        if rel in content.docs:
            out.append((f"content/{rel}", render(content.docs[rel].body, ctx), last))
    for i, f in enumerate(content.finale.fates):
        out.append((f"finale.fates[{i}]", render(f.text, ctx), last))
    docs = content.documents_by_id
    for source, text in locked_page_texts(content, ctx):
        slug = source.split("/")[2] if source.startswith("content/pages/") else ""
        stage = docs[content.pages[slug].doc].stage if slug in content.pages else 0
        out.append((source, text, stage))
    return out


def public_texts(content: Content, ctx: dict) -> list[str]:
    """Тексты, открытые по замыслу: их шинглы — не утечка, даже если повторяются в закрытых текстах.

    Бренды, шапка, логин облака (оболочка закрытой страницы, PLAN E7), заглушки сборщика,
    тексты этапа 1 кроме подсказок (pack-1 открывается публичным ключом) и строки открытых страниц.
    """
    from engine.documents import STUB_HTML
    from engine.media import _PLACEHOLDER_ALT
    from engine.pages import STUB_BODY_HTML
    from engine.util import iter_strings

    w = content.world
    out = [content.settings.title, w["brands"]["system"], w["police"]["department"], w["police"]["case_no"],
           page_text(STUB_HTML), page_text(STUB_BODY_HTML), *_PLACEHOLDER_ALT.values()]
    out += [str(v) for v in w["brands"].values()]
    r = lambda t: render(t, ctx) if t else ""  # noqa: E731
    for page in content.pages.values():
        for attr in ("brand", "account"):
            out.append(r(getattr(page, attr, None)))
        if page.locked is False:
            out += [r(x) for _, x in iter_strings(page.model_dump(by_alias=True))]
    first = content.stages[0]
    out += [r(first.intro), r(first.on_complete)]
    for q in first.questions:
        for spec in [q, *(q.fields or [])]:
            out += [r(getattr(spec, "prompt", None)), r(getattr(spec, "label", None)), r(spec.help)]
            out += [r(o.text) for o in spec.options or []] + [r(i.text) for i in spec.items or []]
    out += [r(d.title) for d in content.documents if d.stage == first.n]
    out += [r(t.title) for t in content.expertise.types]
    out += [r(o.title) for o in content.expertise.objects if o.from_stage == first.n]
    return out


def published_texts(prep: Prepared, *, site_dir: Path = SITE, media_dir: Path = MEDIA_DIR) -> list[str]:
    """Публичный вывод сборки, отрендеренный заново из контента так же, как это делает ``build``:
    открытые страницы целиком (``p/<slug>/index.html``), страницы системы расследования и
    ``public.json``. Берётся не из ``dist/``: утечка в записанный файл не должна делать себя «публичной»."""
    from engine.build import APP_ENTRIES, app_html, site_base_ctx
    from engine.packs import build_public
    from engine.pages import build_page
    from engine.templating import make_site_env

    content = prep.content
    site_env = make_site_env(Path(site_dir) / "templates")
    plan = MediaPlan(content, Path(media_dir))
    pub = build_public(content, prep.salts)
    base_ctx = site_base_ctx(content, pub)
    out = [json_text(pub)]
    for page in content.pages.values():
        if access_of(page) == "open":
            html = build_page(content, page, prep.ctx, prep.salts, plan, site_env, base_ctx).index_html
            out.append(markup_text(unescape(html)))
    out += [markup_text(unescape(app_html(site_env, base_ctx, rel))) for rel in APP_ENTRIES]
    return out


def leak_needles(prep: Prepared, dec: Decrypted | None = None, *, site_dir: Path = SITE,
                 media_dir: Path = MEDIA_DIR) -> NeedleSet:
    """Иголки leak scan (значения и шинглы), см. engine/leakscan.py."""
    content, ctx = prep.content, prep.ctx
    ns = NeedleSet()
    ns.exclude = boilerplate_shingles(site_dir, public_texts(content, ctx))
    for u in units(content):
        if u.type not in ("text", "time", "date", "number") or not u.leak_scan:
            continue
        exp = prep.expanded[u.path]
        for v in exp.variants:
            ns.add(v, "answer", u.path, stage=u.stage)
            if u.type == "date":
                ns.add(iso_to_dmy(v), "answer", u.path, stage=u.stage)
        for r in exp.raw:
            ns.add(r, "answer", u.path, raw=r, stage=u.stage)
    stage_of = {r.id: r.stage for r in content.expertise.results}
    for rid, (params, _) in prep.params.items():
        for pid, exp in params.items():
            for v in exp.variants:
                ns.add(v, "param", f"{rid}.{pid}", stage=stage_of[rid])
                if exp.type == "date":
                    ns.add(iso_to_dmy(v), "param", f"{rid}.{pid}", stage=stage_of[rid])
            for r in exp.raw:
                ns.add(r, "param", f"{rid}.{pid}", raw=r, stage=stage_of[rid])
    for w in content.settings.leak_watchlist:
        ns.add(w, "watchlist", "settings.leak_watchlist", raw=w)
    first = content.stages[0].n
    for d in content.documents:  # docs/03 §4: названия документов этапов 2…N — только в пакетах
        if d.stage > first:
            t = render(d.title, ctx)
            ns.add(t, "title", f"documents.yaml {d.id}", raw=t, stage=d.stage)
    cloud = content.pages.get("cloud")
    pw = getattr(cloud, "password", None)
    if pw and "TODO(content)" not in pw:
        npw = normalize("password", pw)
        if npw:
            st = content.documents_by_id[cloud.doc].stage
            ns.add(npw, "password", "content/pages/cloud/page.yaml: password", is_base=True, stage=st)
            ns.add(pw, "password", "content/pages/cloud/page.yaml: password", raw=pw, stage=st)
    for source, text, stage in secret_texts(prep, dec):
        ns.add_text(text, "text", source, stage=stage)
    # Бумага конвертов (content/paper/) не публикуется: её шинглы в dist/ — утечка; в открытом
    # тексте pack-1 допустима только бумага конверта 1 (иголки этапа 1 там не ищутся). Бумага вправе
    # цитировать открытое (страницы call, gromov, news; интерфейс; public.json): такие шинглы — не иголки.
    from engine.paper import paper_texts

    published: set[str] = set()
    for t in published_texts(prep, site_dir=site_dir, media_dir=media_dir):
        published |= text_shingles(t)
    for source, text, stage in paper_texts(content, ctx):
        ns.add_text(text, "paper", source, stage=stage, also_exclude=published)
    return ns


def check(
    root: Path = ROOT,
    *,
    content_dir: Path | None = None,
    media_dir: Path | None = None,
    dist: Path | None = None,
    salts_path: Path | None = None,
    site_dir: Path | None = None,
    release: bool = False,
    log: Callable[[str], None] | None = None,
) -> CheckReport:
    root = Path(root)
    site_dir = Path(site_dir or root / "site")
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

    # 1. Прохождение — как браузер (FORMATS §2.4): порядок вопросов, kind и unit.type — из пакета
    problems: list[str] = []
    dec = Decrypted()
    packs = dec.packs
    keys: dict[int, bytes] = {}
    if pub.get("saltsId") != prep.salts.id:
        problems.append("saltsId в public.json не совпадает с salts.lock.json")
    keys[1] = crypto.start_key(crypto.b64u_decode(pub["saltStart"]), pub["iter"]["stage"])
    for st in content.stages:
        n = st.n
        try:
            box = _load(data / f"pack-{n}.json")
            packs[n] = _open_json(crypto.hkdf(keys[n], crypto.pack_info(n)), box, f"pack/{n}")
        except (OSError, crypto.CryptoError, KeyError, ValueError) as e:
            problems.append(f"pack-{n}: не открылся ({e})")
            break
        pack = packs[n]
        if pack.get("n") != n:
            problems.append(f"pack-{n}: поле n = {pack.get('n')}")
        problems += pack_structure_problems(prep, pack, n)
        if n < content.last_stage:
            pairs = []
            for q in pack["questions"]:
                if q.get("kind") != "mandatory":
                    continue
                for f in q.get("fields", [q]):
                    pu = f["unit"]
                    path = pu["path"]
                    exp = prep.expanded.get(path)
                    x = normalize(pu["type"], exp.input, default_year=s.default_year) if exp else None
                    got = crypto.check_answer(akey(path, x, crypto.b64u_decode(pu["salt"])), path, pu["entries"]) if x else None
                    if got is None:
                        problems.append(f"{path}: верный ответ не принят записями пакета")
                    pairs.append((path, got or ""))
            keys[n + 1] = crypto.stage_key(n, pairs, crypto.b64u_decode(pack["saltStage"]), pub["iter"]["stage"])
    for n, k in keys.items():
        if prep.keys.get(n) != k:
            problems.append(f"K_{n}: ключ, выведенный по пакету, не совпадает с ключом из контента")
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
                    dec.lab.setdefault(r.id, rec)
                    if rec.get("doc") != r.doc:
                        problems.append(f"{r.id}: doc {rec.get('doc')!r} вместо {r.doc!r}")
        t, b, p = r.types[0], r.bases[0], list(combos[0]) if combos else []
        # до своего этапа
        for m in range(1, n):
            if m in packs and crypto.try_entries(crypto.hkdf(keys[m], crypto.lab_info(r.object, t, b, p)),
                                                 packs[m]["lab"]["entries"], "lab"):
                problems.append(f"{r.id}: открылась на этапе {m} — раньше своего этапа {n}")
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
    # исчерпывающе: объект × любой вид × любой документ вне допустимых → ни на одном этапе не открывается
    doc_ids = [d.id for d in content.documents]
    type_ids = [t.id for t in content.expertise.types]
    n_foreign = 0
    for obj_id in {r.object for r in content.expertise.results}:
        res = [r for r in content.expertise.results if r.object == obj_id]
        allowed: dict[tuple[str, str], set[int]] = {}
        for r in res:
            for t in r.types:
                for b in r.bases:
                    allowed.setdefault((t, b), set()).add(r.stage)
        _, combos0 = prep.params[res[0].id]
        p0 = list(combos0[0]) if combos0 else []
        for t in type_ids:
            for b in doc_ids:
                ok_stages = allowed.get((t, b), set())
                for m, pk in packs.items():
                    if m in ok_stages:
                        continue
                    n_foreign += 1
                    if crypto.try_entries(crypto.hkdf(keys[m], crypto.lab_info(obj_id, t, b, p0)),
                                          pk["lab"]["entries"], "lab"):
                        problems.append(f"{obj_id}: открылась запись с ({t}, {b}) на этапе {m} — "
                                        "это не основание/вид результата или не его этап")
    rep.add("4. Экспертизы", problems, f"результатов: {len(content.expertise.results)}, запросов: {n_lab}, "
                                       f"чужих комбинаций проверено: {n_foreign}")

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
            dec.pages[slug] = fragments[slug]
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
        dec.finale = fin
        missing = [u.path for u in all_units if u.path not in fin.get("answers", {})]
        if missing:
            problems.append(f"в answers нет единиц: {', '.join(missing)}")
        if len(fin.get("fates", [])) != len(content.finale.fates):
            problems.append("число судеб не совпадает с finale.yaml")
    except (OSError, crypto.CryptoError, KeyError) as e:
        problems.append(f"finale.json не открылся ({e})")
    rep.add("6. Развязка", problems, f"открыта ключом этапа {content.last_stage}")

    # 7. Leak scan + pack-1 + медиа + нейтральные примеры
    plan = MediaPlan(content, media_dir)
    ns = leak_needles(prep, dec, site_dir=site_dir, media_dir=media_dir)
    rep.short_needles = ns.short
    problems = [str(f) for f in scan(dist, ns)]
    first = content.stages[0].n
    if first in packs:  # ключ pack-1 публичный: его открытый текст — как открытый файл
        problems += pack1_problems(packs[first], ns, first)
    open_hashes: dict[str, str] = {}
    for p in dist.rglob("*"):
        if p.is_file() and p.suffix != ".bin":
            open_hashes.setdefault(media_hash(p.read_bytes()), p.relative_to(dist).as_posix())
    mdir = dist / "m"
    for mf in plan.files.values():
        if not mf.exists:
            continue
        if mf.encrypted and mf.hash in open_hashes:
            problems.append(f"медиа {mf.rel} используется только зашифрованным контентом, но лежит открытым: "
                            f"{open_hashes[mf.hash]}")
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
    n_paper = sum(1 for nd in ns.shingles.values() if nd.kind == "paper")
    rep.add("7. Leak scan", problems,
            f"иголок: {len(ns.needles)} значений + {len(ns.shingles)} шинглов (из них бумаги content/paper: "
            f"{n_paper}), примеров интерфейса: {len(examples)}; "
            f"не ищутся (короче 4 символов): «{short}»")

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


def pack_structure_problems(prep: Prepared, pack: dict, n: int) -> list[str]:
    """Пакет совпадает с контентом там, где от него зависит ключ или проверка: порядок вопросов и полей,
    kind, тип единицы; карточки order перемешаны и ≠ ответу (PLAN C3)."""
    content = prep.content
    out: list[str] = []
    st = content.stage(n)
    want = [(f"s{n}.{q.id}", q.kind, q.type, [(f"s{n}.{q.id}.{f.id}", f.type) for f in q.fields or []])
            for q in st.questions]
    got = [(q.get("path"), q.get("kind"), q.get("type"),
            [(f.get("path"), f.get("type")) for f in q.get("fields", [])]) for q in pack.get("questions", [])]
    if [w[0] for w in want] != [g[0] for g in got]:
        out.append(f"pack-{n}: порядок вопросов {[g[0] for g in got]} ≠ контенту {[w[0] for w in want]}")
    by_path = {g[0]: g for g in got}
    for path, kind, typ, fields in want:
        g = by_path.get(path)
        if g is None:
            continue
        if g[1] != kind:
            out.append(f"{path}: в пакете kind {g[1]!r}, в контенте {kind!r}")
        if g[2] != typ:
            out.append(f"{path}: в пакете type {g[2]!r}, в контенте {typ!r}")
        if g[3] != fields:
            out.append(f"{path}: поля формы в пакете {g[3]} ≠ контенту {fields}")
    for q in pack.get("questions", []):
        for f in q.get("fields", [q]):
            unit = f.get("unit") or {}
            path = unit.get("path")
            exp = prep.expanded.get(path)
            if exp is None:
                out.append(f"pack-{n}: единица {path!r} не из контента")
                continue
            if unit.get("type") != exp.type:
                out.append(f"{path}: в пакете unit.type {unit.get('type')!r}, в контенте {exp.type!r}")
            if exp.type == "order":
                shown = [i.get("id") for i in f.get("items", [])]
                answer = exp.canon.split(",")
                if shown == answer:
                    out.append(f"{path}: карточки order в пакете стоят в порядке ответа")
                if sorted(shown) != sorted(answer):
                    out.append(f"{path}: карточки order в пакете ≠ карточкам ответа")
    return out


def pack1_problems(pack: dict, ns: NeedleSet, first: int) -> list[str]:
    """pack-1 открывается публичным ключом: ни секретов этапов 2…N, ни лишних персонажей и полей (PLAN B3)."""
    out = [f"{f} (открытый текст pack-{first})" for f in
           (str(x) for x in scan_text(json_text(pack), ns, f"data/pack-{first}.json", skip_stage=first))]
    pools: set[str] = set()
    for q in pack.get("questions", []):
        for f in q.get("fields", [q]):
            pools |= set(f.get("pool", []))
    for cid, ch in pack.get("characters", {}).items():
        if cid not in pools:
            out.append(f"pack-{first}: персонаж «{cid}» не из пулов вопросов этапа")
        extra = set(ch) - CHARACTER_FIELDS
        if extra:
            out.append(f"pack-{first}: у персонажа «{cid}» лишние поля {sorted(extra)}")
    return out
