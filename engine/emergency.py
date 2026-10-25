"""``python -m engine answers`` — «Аварийный конверт», ``print/answers.pdf`` (P07 п.3).

Титул «Вскрывать, только если сайт недоступен»; по этапам — вопросы, верные ответы и какой
конверт открыть дальше; экспертизы — какие запросы с какими основаниями дают результат и
сами тексты результатов; финал и развязка; баллы и ранги. A4, PT Serif.

Модуль назван не ``answers.py``, чтобы не путать с записями-проверками (PLAN §1).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from markupsafe import Markup

from engine import ROOT
from engine import salts as salts_mod
from engine.answers import display_answer, expand_all, iso_to_dmy
from engine.content import Content, load_content, units
from engine.lab import expand_params, lower_first
from engine.templating import make_context, make_link, render, render_markdown

PRINT_ANSWERS = ROOT / "print" / "answers.pdf"
KIND_LABEL = {"mandatory": "обязательный", "bonus": "бонус", "final": "финальный"}
FOOTER = ('<div style="font-size:8px;width:100%;text-align:center;color:#777;font-family:serif">'
          'Аварийный конверт · стр. <span class="pageNumber"></span> из <span class="totalPages"></span></div>')


def _tolerance_note(exp) -> str:
    return f"допуск ±{exp.tolerance} мин" if exp.tolerance else ""


def _accepted(exp, u_type: str) -> str:
    """Какие формы ответа принимает сайт (для ведущего при ручной проверке)."""
    if u_type == "text" and len(exp.raw) > 1:
        return "принимается также: " + "; ".join(exp.raw[1:])
    if u_type == "time":
        return _tolerance_note(exp)
    return ""


_ABS_LINK_RE = re.compile(r'(<a href="(https?://[^"]+)"[^>]*>.*?</a>)', re.S)


def _show_addresses(html: str) -> str:
    """В бумажном конверте ссылку не нажать: после текста ссылки печатаем её полный адрес."""
    return _ABS_LINK_RE.sub(lambda m: f"{m.group(1)} ({m.group(2)})", html)


def emergency_data(content: Content, salts: Any = None) -> dict:
    """``salts`` — соли и ключи страниц (по умолчанию ``engine/salts.lock.json``, только чтение): нужны,
    чтобы ``link('slug')`` в текстах результатов раскрывались в полный адрес с ключом, как в сборке."""
    if salts is None:
        salts = salts_mod.read()
        if salts is None:
            raise FileNotFoundError(f"нет файла солей {salts_mod.SALTS_LOCK} — сначала python -m engine build")
    ctx = make_context(content)
    domain = content.settings.domain.rstrip("/")
    site_link = make_link(content.pages or {}, salts)
    ctx["link"] = lambda slug: domain + site_link(slug)  # полный адрес: ведущему его можно набрать руками
    expanded = expand_all(content, ctx)
    params = expand_params(content, ctx)
    by_path = {u.path: u for u in units(content)}
    s = content.settings
    r = lambda t: render(t, ctx) if t else ""  # noqa: E731

    stages = []
    for st in content.stages:
        qs = []
        for q in st.questions:
            qpath = f"s{st.n}.{q.id}"
            rows = []
            if q.type == "form":
                for f in q.fields or []:
                    u = by_path[f"{qpath}.{f.id}"]
                    exp = expanded[u.path]
                    rows.append({"label": r(f.label), "answer": display_answer(u, exp, content, ctx),
                                 "note": _accepted(exp, u.type)})
            else:
                u = by_path[qpath]
                exp = expanded[u.path]
                rows.append({"label": None, "answer": display_answer(u, exp, content, ctx),
                             "note": _accepted(exp, u.type)})
            points = {"bonus": s.points.bonus, "final": s.points.final}.get(q.kind)
            qs.append({"path": qpath, "kind": KIND_LABEL[q.kind], "points": points, "prompt": r(q.prompt),
                       "rows": rows, "order": q.type == "order"})
        stages.append({"n": st.n, "envelope": st.envelope, "questions": qs, "next": r(st.on_complete) or None})

    docs = content.documents_by_id
    objects = {o.id: o for o in content.expertise.objects}
    types = {t.id: t for t in content.expertise.types}
    lab = []
    for res in sorted(content.expertise.results, key=lambda x: x.stage):
        obj = objects[res.object]
        prm = []
        for p in obj.params or []:
            exp = params[res.id][0][p.id]
            shown = exp.input if p.type != "date" else iso_to_dmy(exp.canon)
            prm.append({"label": r(p.label), "value": shown, "note": _tolerance_note(exp)})
        if res.doc:
            df = content.docs.get(res.body)
            body = Markup(_show_addresses(render_markdown(render(df.body, ctx)))) if df else Markup("<p>Текста документа пока нет.</p>")
            title = f"{res.doc} — {r(docs[res.doc].title)}"
        else:
            body = Markup(_show_addresses(render_markdown(r(res.text))))
            title = f"{r(obj.title)}: {lower_first(r(types[res.types[0]].title))} (без документа)"
        lab.append({
            "stage": res.stage, "object": r(obj.title), "object_from": obj.from_stage, "ref": r(obj.ref),
            "types": [r(types[t].title) for t in res.types],
            "bases": [f"{b} — {r(docs[b].title)}" for b in res.bases], "params": prm,
            "title": title, "body": body,
        })

    fin = content.finale
    def doc_html(rel: str) -> tuple[str, Markup]:
        df = content.docs.get(rel)
        if df is None:
            return "", Markup("<p>Текста пока нет.</p>")
        return render(df.meta.title, ctx), Markup(_show_addresses(render_markdown(render(df.body, ctx))))

    c = ctx["c"]
    confession = doc_html(fin.confession)
    letter = doc_html(fin.letter)
    return {
        "title": s.title,
        "stages": stages,
        "lab": lab,
        "lab_penalty": s.penalties.lab_no_basis,
        "confession": {"title": confession[0], "html": confession[1]},
        "letter": {"title": letter[0], "html": letter[1]},
        "fates": [{"name": getattr(c, f.who).full() if f.who else None, "text": r(f.text)} for f in fin.fates],
        "scoring": {
            "bonus": s.points.bonus, "final": s.points.final, "wrong": s.penalties.wrong_attempt,
            "lab": s.penalties.lab_no_basis, "hints": list(s.hints.cost), "auto": s.hints.auto_after_wrong,
            "ranks": [{"min": x.min, "max": x.max, "name": x.name} for x in s.ranks],
        },
    }


def answers_pdf(content: Content, out: Path = PRINT_ANSWERS) -> Path:
    from engine.printing import browser, html_to_pdf, print_env

    html = print_env().get_template("print/answers.html").render(**emergency_data(content))
    out = Path(out)
    with browser() as b:
        return html_to_pdf(b, html, out, footer=FOOTER)


def run(root: Path = ROOT, *, out: Path = PRINT_ANSWERS) -> Path:
    return answers_pdf(load_content(Path(root) / "content"), out)
