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
from engine.models import ExpResult
from engine.templating import render

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


def lab_catalog(content: Content, ctx: dict, n: int, entries: list[dict]) -> dict:
    """``LabCatalog`` пакета ``n`` (FORMATS §2.3)."""
    first = content.stages[0].n
    types = (
        [{"id": t.id, "title": render(t.title, ctx), "ord": i} for i, t in enumerate(content.expertise.types)]
        if n == first
        else []
    )
    objects = [
        {
            "id": o.id,
            "title": render(o.title, ctx),
            "ord": i,
            "params": [{"id": p.id, "type": p.type, "label": render(p.label, ctx)} for p in o.params or []],
        }
        for i, o in enumerate(content.expertise.objects)
        if o.from_stage == n
    ]
    return {"types": types, "objects": objects, "entries": entries}


def fingerprint(object_id: str, type_id: str, basis: str, params: list[str]) -> str:
    """``fp`` (FORMATS F7) — для тестов и dump."""
    import hashlib

    s = object_id + "|" + type_id + "|" + basis + "|" + "|".join(params)
    return crypto.b64u_encode(hashlib.sha256(s.encode("utf-8")).digest())
