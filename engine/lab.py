"""Экспертизы: docs/02 §3.6, FORMATS §2.3 и §3.

Для результата этапа N и каждого (вид, основание, вариант параметров):
``key = HKDF(K_N, labInfo(object, type, basis, p))``, запись — ``Box`` с ``aad = "lab"``.
Атмосферные результаты (без ``doc``) — ``{doc: null, form: null, html: "<p>…</p>"}`` (D1, F8).
"""

from __future__ import annotations

import itertools
import json
from typing import Any

from markupsafe import escape

from engine import crypto
from engine.answers import Expanded, expand_answer, pad_and_shuffle
from engine.content import Content, ContentError, ContentIssue
from engine.documents import RenderedDoc
from engine.labmatch import SHARED_STEM_WARN, STEM_MIN, alias_stems, norm, resolve_object, title_stems
from engine.models import ExpObject, ExpResult
from engine.templating import render, render_markdown
from engine.util import format_loc

LAB_AAD = "lab"
COMBO_WARN = 200  # docs/03 §6: предупреждение при > 200 комбинаций на результат


def dumps(obj: Any) -> bytes:
    """JSON для dist/: UTF-8, без пробелов, порядок ключей — как задан (FORMATS §0)."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def lower_first(s: str) -> str:
    return s[:1].lower() + s[1:]


def expand_params(content: Content, ctx: dict) -> dict[str, tuple[dict[str, Expanded], list[tuple[str, ...]]]]:
    """``{result_id: (params, combos)}``; ошибки нормализации — ``ContentError``."""
    objects = {o.id: o for o in content.expertise.objects}
    year = content.settings.default_year
    file = f"{content.root.name}/expertise.yaml"
    out: dict[str, tuple[dict[str, Expanded], list[tuple[str, ...]]]] = {}
    errors: list[ContentIssue] = []
    for ri, r in enumerate(content.expertise.results):
        obj = objects[r.object]
        params: dict[str, Expanded] = {}
        for p in obj.params or []:
            loc = f"results[{ri}].params_answer.{p.id}"
            try:
                params[p.id] = expand_answer(f"{r.id}.{p.id}", p.type, r.params_answer[p.id], ctx, year,
                                             f"{file}: {loc}")
            except ValueError as e:
                errors.append(ContentIssue(file, loc, str(e)))
        ok = all(p.id in params for p in obj.params or [])
        combos = list(itertools.product(*(params[p.id].variants for p in obj.params or []))) if ok else []
        out[r.id] = (params, combos)
    if errors:
        raise ContentError(errors)
    return out


def result_payload(content: Content, r: ExpResult, ctx: dict, docs: dict[str, RenderedDoc]) -> dict:
    """Внутренний JSON записи (FORMATS §3.2)."""
    if r.doc is not None:
        rd = docs[r.id]
        return {"v": 1, "doc": r.doc, **rd.record()}
    objects = {o.id: o for o in content.expertise.objects}
    types = {t.id: t for t in content.expertise.types}
    obj_title = render(objects[r.object].title, ctx)
    type_title = render(types[r.types[0]].title, ctx)
    text = render(r.text, ctx)
    return {
        "v": 1,
        "doc": None,
        "title": f"{obj_title}: {lower_first(type_title)}",
        "form": None,
        "html": f"<p>{escape(text)}</p>",
        "media": [],
    }


def lab_entries(content: Content, keys: dict[int, bytes], payloads: dict[str, dict],
                params: dict[str, tuple[dict, list]], warnings: list[str]) -> dict[int, list[dict]]:
    """Записи экспертиз по этапам, с паддингом до ``entries_pad`` и перемешанные."""
    pad = content.settings.crypto.entries_pad
    by_stage: dict[int, list[dict]] = {st.n: [] for st in content.stages}
    for r in content.expertise.results:
        _, combos = params[r.id]
        if len(combos) > COMBO_WARN:
            warnings.append(f"экспертиза «{r.id}»: {len(combos)} комбинаций параметров (> {COMBO_WARN})")
        pt = dumps(payloads[r.id])
        k_n = keys[r.stage]
        for t, b, p in itertools.product(r.types, r.bases, combos):
            key = crypto.hkdf(k_n, crypto.lab_info(r.object, t, b, list(p)))
            by_stage[r.stage].append(crypto.seal(key, pt, LAB_AAD))
    return {n: pad_and_shuffle(entries, LAB_AAD, pad) for n, entries in by_stage.items()}


def norm_aliases(o: ExpObject, ctx: dict) -> list[str]:
    """Алиасы объекта после шаблонов и ``norm`` (в порядке файла; пустые не отбрасываются)."""
    return [norm(render(a, ctx)) for a in o.aliases]


def lab_objects(content: Content, ctx: dict) -> list[dict]:
    """Объекты для распознавания в порядке expertise.yaml: ``{id, title, from_stage, aliases, ref}``.

    ``title`` отрендерен, ``aliases`` нормализованы (пустые отброшены) — ровно то, что получает браузер."""
    return [
        {
            "id": o.id,
            "title": render(o.title, ctx),
            "from_stage": o.from_stage,
            "aliases": [a for a in norm_aliases(o, ctx) if a],
            "ref": render(o.ref, ctx) if o.ref else None,
        }
        for o in content.expertise.objects
    ]


def lab_catalog(content: Content, ctx: dict, n: int, entries: list[dict]) -> dict:
    """``LabCatalog`` пакета ``n`` (FORMATS §2.3): виды — в пакете первого этапа, объекты — в пакете
    своего ``from_stage`` (с ``aliases`` для распознавания и ``ref``)."""
    first = content.stages[0].n
    types = (
        [
            {"id": t.id, "title": render(t.title, ctx), "ord": i,
             "description": render(t.description, ctx) if t.description else None}
            for i, t in enumerate(content.expertise.types)
        ]
        if n == first
        else []
    )
    by_id = {o["id"]: o for o in lab_objects(content, ctx)}
    objects = [
        {
            "id": o.id,
            "title": by_id[o.id]["title"],
            "ord": i,
            "params": [{"id": p.id, "type": p.type, "label": render(p.label, ctx)} for p in o.params or []],
            "aliases": by_id[o.id]["aliases"],
            "ref": by_id[o.id]["ref"],
        }
        for i, o in enumerate(content.expertise.objects)
        if o.from_stage == n
    ]
    return {"types": types, "objects": objects, "entries": entries}


def lab_site(content: Content, ctx: dict) -> dict:
    """Тексты сайта лаборатории (``content/lab.yaml``) для шаблона ``lab.html``, уже отрендеренные.

    ``about`` — Markdown с подставленными шаблонами, ``about_html`` — он же в HTML. Пусто, если файла нет."""
    lab = content.lab
    if lab is None:
        return {}
    r = lambda t: render(t, ctx) if t else t  # noqa: E731
    about = r(lab.about)
    return {
        "name": r(lab.name),
        "full_name": r(lab.full_name),
        "tagline": r(lab.tagline),
        "about": about,
        "about_html": render_markdown(about),
        "accreditation": r(lab.accreditation),
        "staff": [{"name": r(p.name), "role": r(p.role)} for p in lab.staff],
        "contacts": {"address": r(lab.contacts.address), "phone": r(lab.contacts.phone),
                     "hours": r(lab.contacts.hours), "email": r(lab.contacts.email)},
        "services_note": r(lab.services_note),
    }


def lab_problems(content: Content, ctx: dict) -> tuple[list[ContentIssue], list[ContentIssue]]:
    """Проверки распознавания объекта и правило оснований: ``(ошибки, предупреждения)``.

    Ошибки (``build`` и ``check`` падают):
      * основа алиаса короче ``STEM_MIN`` символов (после ``norm``), алиас пуст после ``norm``;
      * одинаковые алиасы у разных объектов;
      * ``title`` не распознаётся сам в себя на этапе, где объект доступен;
      * правило 2.1.4: объект доступен раньше этапа результата (``from_stage < stage``), а основание —
        не документ этапа результата (иначе тот же запрос на раннем этапе ответил бы «ничего не выявила»,
        а на позднем — заключением).
    Предупреждение: общая у двух объектов основа длиной ≤ ``SHARED_STEM_WARN``.
    """
    file = f"{content.root.name}/expertise.yaml"
    errors: list[ContentIssue] = []
    warnings: list[ContentIssue] = []
    exp = content.expertise
    stages = sorted(st.n for st in content.stages)

    # основы и дубликаты алиасов
    seen: dict[tuple[str, ...], tuple[int, int]] = {}
    for oi, o in enumerate(exp.objects):
        for ai, alias in enumerate(norm_aliases(o, ctx)):
            loc = format_loc(("objects", oi, "aliases", ai))
            stems = alias_stems(alias)
            if not stems:
                errors.append(ContentIssue(file, loc, f"алиас «{o.aliases[ai]}» пуст после нормализации"))
                continue
            for stem in stems:
                if len(stem) < STEM_MIN:
                    errors.append(ContentIssue(
                        file, loc, f"основа «{stem}» короче {STEM_MIN} символов (алиас «{o.aliases[ai]}»)"))
            key = tuple(sorted(stems))
            if key in seen and seen[key][0] != oi:
                po, pa = seen[key]
                errors.append(ContentIssue(
                    file, loc, f"алиас «{alias}» уже есть у объекта «{exp.objects[po].id}» "
                               f"({format_loc(('objects', po, 'aliases', pa))}): алиасы разных объектов не повторяются"))
            else:
                seen.setdefault(key, (oi, ai))

    # название распознаётся само в себя на каждом этапе доступности
    objs = lab_objects(content, ctx)
    for oi, o in enumerate(objs):
        for n in stages:
            if n < o["from_stage"]:
                continue
            res = resolve_object(o["title"], [x for x in objs if x["from_stage"] <= n])
            if res != {"status": "ok", "id": o["id"]}:
                what = ("распознаётся как «" + res["id"] + "»" if res["status"] == "ok"
                        else "неоднозначно: " + ", ".join(res["ids"]) if res["status"] == "ambiguous"
                        else "не распознаётся")
                errors.append(ContentIssue(
                    file, format_loc(("objects", oi, "title")),
                    f"название «{o['title']}» на этапе {n} {what}; добавьте объекту aliases или "
                    "уберите пересечение с другими предметами"))
                break

    # предупреждение: общая короткая основа у разных объектов
    owners: dict[str, list[str]] = {}
    for o in objs:
        stems = {s for a in o["aliases"] for s in alias_stems(a)} | set(title_stems(o["title"]))
        for stem in stems:
            if len(stem) <= SHARED_STEM_WARN:
                owners.setdefault(stem, []).append(o["id"])
    for stem, ids in sorted(owners.items()):
        if len(ids) > 1:
            warnings.append(ContentIssue(file, "objects",
                                         f"общая основа «{stem}» (≤ {SHARED_STEM_WARN} символов) у объектов "
                                         f"{', '.join(ids)}: возможна неоднозначность ввода"))

    # правило 2.1.4
    objects = {o.id: o for o in exp.objects}
    docs = content.documents_by_id
    for ri, r in enumerate(exp.results):
        o = objects.get(r.object)
        if o is None or o.from_stage >= r.stage:
            continue
        for bi, b in enumerate(r.bases):
            d = docs.get(b)
            if d is not None and d.stage != r.stage:
                early = max(o.from_stage, d.stage)
                errors.append(ContentIssue(
                    file, format_loc(("results", ri, "bases", bi)),
                    f"основание «{b}» (этап {d.stage}): объект «{o.id}» доступен с этапа {o.from_stage}, а результат "
                    f"«{r.id}» открывается на этапе {r.stage}; у таких результатов основания — только документы "
                    f"этапа {r.stage}, иначе тот же запрос на этапе {early} ответит «ничего не выявила», а на этапе "
                    f"{r.stage} — заключением"))
    return errors, warnings


def fingerprint(object_id: str, type_id: str, basis: str, params: list[str]) -> str:
    """``fp`` (FORMATS F7) — для тестов и dump."""
    import hashlib

    s = object_id + "|" + type_id + "|" + basis + "|" + "|".join(params)
    return crypto.b64u_encode(hashlib.sha256(s.encode("utf-8")).digest())
