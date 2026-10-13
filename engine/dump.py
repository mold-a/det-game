"""``python -m engine dump-answers`` → ``tests/.answers.json`` (FORMATS §8).

Только для тестов: файл в ``.gitignore`` — в нём ответы, ключи страниц и пароль облака.
"""

from __future__ import annotations

import json
from pathlib import Path

from engine import ROOT
from engine import salts as salts_mod
from engine.answers import wrong_inputs
from engine.build import Prepared, prepare
from engine.content import units
from engine.pages import access_of
from engine.templating import render
from engine.util import b64u_encode, write_text

ANSWERS_JSON = ROOT / "tests" / ".answers.json"


def _unit_entry(prep: Prepared, u) -> dict:
    exp = prep.expanded[u.path]
    return {
        "type": u.type,
        "input": exp.input,
        "canon": exp.canon,
        "variants": exp.variants,
        "wrong": wrong_inputs(u, exp, prep.content, prep.expanded),
    }


def answers_data(prep: Prepared) -> dict:
    content = prep.content
    s = content.settings
    by_path = {u.path: u for u in units(content)}
    stages = []
    for st in content.stages:
        qs = []
        for q in st.questions:
            qpath = f"s{st.n}.{q.id}"
            item = {"path": qpath, "kind": q.kind, "type": q.type}
            if q.type == "form":
                item["fields"] = [
                    {"path": f"{qpath}.{f.id}", "id": f.id, **_unit_entry(prep, by_path[f"{qpath}.{f.id}"])}
                    for f in q.fields or []
                ]
            else:
                e = _unit_entry(prep, by_path[qpath])
                e.pop("type")
                item.update(e)
            qs.append(item)
        stages.append({"n": st.n, "envelope": st.envelope, "questions": qs})

    last = content.stage(content.last_stage)
    final_order = [f"s{last.n}.{q.id}" for q in last.questions if q.kind == "final"]
    final_order += [f"s{last.n}.{q.id}" for q in last.questions if q.kind == "bonus"]

    objects = {o.id: o for o in content.expertise.objects}
    lab = []
    for r in content.expertise.results:
        params, _ = prep.params[r.id]
        wrong_basis = next(
            (d.id for d in content.documents
             if d.stage <= r.stage and d.kind != "lab" and d.id not in r.bases
             and not any(x.object == r.object and set(x.types) & set(r.types) and d.id in x.bases
                         for x in content.expertise.results)),
            None,
        )
        if r.doc:
            title = render(content.documents_by_id[r.doc].title, prep.ctx)
        else:
            types = {t.id: t for t in content.expertise.types}
            t = render(types[r.types[0]].title, prep.ctx)
            title = f"{render(objects[r.object].title, prep.ctx)}: {t[:1].lower() + t[1:]}"
        lab.append({
            "result": r.id, "object": r.object, "types": list(r.types), "stage": r.stage, "bases": list(r.bases),
            "params": {pid: {"input": e.input, "variants": e.variants} for pid, e in params.items()},
            "doc": r.doc, "title": title, "wrongBasis": wrong_basis,
        })

    pages = []
    for slug, page in content.pages.items():
        access = access_of(page)
        entry = {"slug": slug, "access": access, "url": f"/p/{slug}/"}
        if access == "key":
            key = b64u_encode(prep.salts.page_key(slug))
            entry["url"] += f"#k={key}"
            entry["key"] = key
        elif access == "password":
            entry["password"] = page.password
        pages.append(entry)

    # по вопросам, а не по единицам: бонус-форма даёт баллы один раз
    q_bonus = sum(q.kind == "bonus" for st in content.stages for q in st.questions)
    q_final = sum(q.kind == "final" for st in content.stages for q in st.questions)
    max_score = q_bonus * s.points.bonus + q_final * s.points.final
    return {
        "v": 1,
        "gameId": s.game_id,
        "settings": {
            "points": {"bonus": s.points.bonus, "final": s.points.final},
            "penalties": {"wrongAttempt": s.penalties.wrong_attempt, "labNoBasis": s.penalties.lab_no_basis},
            "hints": {"cost": list(s.hints.cost), "autoAfterWrong": s.hints.auto_after_wrong},
            "iter": {"answer": s.crypto.iter_answer, "stage": s.crypto.iter_stage},
            "defaultYear": s.default_year,
        },
        "stages": stages,
        "finalOrder": final_order,
        "lab": lab,
        "pages": pages,
        "expected": {"maxScore": max_score, "perfectRunScore": max_score},
    }


def dump_answers(root: Path = ROOT, *, content_dir: Path | None = None, salts_path: Path | None = None,
                 out: Path | None = None) -> Path:
    prep = prepare(Path(content_dir or Path(root) / "content"), Path(salts_path or salts_mod.SALTS_LOCK))
    out = Path(out or ANSWERS_JSON)
    write_text(out, json.dumps(answers_data(prep), ensure_ascii=False, separators=(",", ":")))
    return out
