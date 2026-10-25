"""``public.json``, ``pack-N.json`` и ``finale.json`` (FORMATS §1, §2, §4)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from engine import crypto
from engine.answers import Expanded, check_entries, display_answer, order_shuffle
from engine.content import Content, Unit, units
from engine.documents import RenderedDoc
from engine.lab import dumps, lab_catalog
from engine.media import MediaPlan
from engine.models import FormField, Question, UnitSpec
from engine.pages import stage_page_index
from engine.templating import render, render_markdown
from engine.util import b64u_encode, canonical_json


def build_public(content: Content, salts: Any, *, now: datetime | None = None) -> dict:
    s = content.settings
    pub = {
        "v": 1,
        "gameId": s.game_id,
        "title": s.title,
        "stages": len(content.stages),
        "saltStart": b64u_encode(salts.start),
        "iter": {"answer": s.crypto.iter_answer, "stage": s.crypto.iter_stage},
        "entriesPad": s.crypto.entries_pad,
        "points": {"bonus": s.points.bonus, "final": s.points.final},
        "penalties": {"wrongAttempt": s.penalties.wrong_attempt, "labNoBasis": s.penalties.lab_no_basis},
        "hints": {"cost": list(s.hints.cost), "autoAfterWrong": s.hints.auto_after_wrong},
        "ranks": [{"min": r.min, "max": r.max, "name": r.name} for r in s.ranks],
        "defaultYear": s.default_year,
        "saltsId": salts.id,
    }
    now = now or datetime.now(timezone.utc)
    digest = hashlib.sha256(canonical_json(pub)).hexdigest()[:8]
    pub["buildId"] = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{digest}"
    return pub


def chrome_of(content: Content) -> dict:
    """Оформление интерфейса (FORMATS F19) — рендерится в HTML, не в public.json."""
    w = content.world
    return {"system": w["brands"]["system"], "department": w["police"]["department"], "caseNo": w["police"]["case_no"]}


class PackBuilder:
    def __init__(self, content: Content, ctx: dict, salts: Any, expanded: dict[str, Expanded], plan: MediaPlan,
                 key_cache: dict | None = None) -> None:
        self.content = content
        self.ctx = ctx
        self.salts = salts
        self.expanded = expanded
        self.plan = plan
        self.key_cache = key_cache if key_cache is not None else {}
        self.units = {u.path: u for u in units(content)}

    # --- единицы и вопросы

    def unit_obj(self, u: Unit) -> dict:
        s = self.content.settings.crypto
        salt = self.salts.unit(u.path)
        entries = check_entries(u.path, self.expanded[u.path], salt, s.iter_answer, s.entries_pad,
                                key_cache=self.key_cache)
        return {"path": u.path, "type": u.type, "salt": b64u_encode(salt), "entries": entries}

    def _inputs(self, spec: UnitSpec, path: str, out: dict) -> None:
        r = lambda s: render(s, self.ctx)  # noqa: E731
        if spec.type in ("choice", "multi"):
            out["options"] = [{"id": o.id, "text": r(o.text)} for o in spec.options or []]
        if spec.type in ("person", "persons"):
            out["pool"] = self.content.pool(spec)
        if spec.type == "order":
            items = {it.id: r(it.text) for it in spec.items or []}
            order = order_shuffle(list(items), self.expanded[path].canon.split(","), self.salts.unit(path))
            out["items"] = [{"id": i, "text": items[i]} for i in order]

    def field_obj(self, n: int, q: Question, f: FormField) -> dict:
        path = f"s{n}.{q.id}.{f.id}"
        out: dict[str, Any] = {"id": f.id, "path": path, "type": f.type, "label": render(f.label, self.ctx),
                               "help": render(f.help, self.ctx) if f.help else None}
        self._inputs(f, path, out)
        out["unit"] = self.unit_obj(self.units[path])
        return out

    def question_obj(self, n: int, q: Question) -> dict:
        path = f"s{n}.{q.id}"
        out: dict[str, Any] = {
            "id": q.id, "path": path, "kind": q.kind, "type": q.type,
            "prompt": render(q.prompt, self.ctx),
            "help": render(q.help, self.ctx) if q.help else None,
            "hints": [render(h, self.ctx) for h in q.hints],
        }
        if q.type == "form":
            out["fields"] = [self.field_obj(n, q, f) for f in q.fields or []]
        else:
            self._inputs(q, path, out)
            out["unit"] = self.unit_obj(self.units[path])
        return out

    # --- пакет

    def characters(self, n: int) -> dict:
        ids: list[str] = []
        for q in self.content.stage(n).questions:
            for spec in ([*q.fields] if q.fields else [q]):
                if spec.type in ("person", "persons"):
                    ids.extend(self.content.pool(spec))
        c = self.ctx["c"]
        out = {}
        by_id = self.content.characters_by_id
        for pid in dict.fromkeys(ids):
            p = getattr(c, pid)
            photo = by_id[pid].photo
            out[pid] = {"full": p.full(), "short": p.short(),
                        "photo": self.plan.ref(photo, p.full()) if photo else None}
        return out

    def documents(self, n: int) -> list[dict]:
        return [
            {"id": d.id, "stage": d.stage, "kind": d.kind, "title": render(d.title, self.ctx),
             "link": f"/p/{d.page}/" if d.kind == "online" else None}
            for d in self.content.documents
            if d.stage == n and d.kind in ("paper", "online")
        ]

    def pack(self, n: int, lab_entries: list[dict]) -> dict:
        st = self.content.stage(n)
        last = st.n == self.content.last_stage
        return {
            "v": 1,
            "n": n,
            "envelope": st.envelope,
            "introHtml": render_markdown(render(st.intro, self.ctx)),
            "onComplete": render(st.on_complete, self.ctx) if st.on_complete else None,
            "saltStage": None if last else b64u_encode(self.salts.stage(n)),
            "questions": [self.question_obj(n, q) for q in st.questions],
            "characters": self.characters(n),
            "documents": self.documents(n),
            "lab": lab_catalog(self.content, self.ctx, n, lab_entries),
            # профили закрытых этапов этого этапа: ключи и строки поиска (docs/02 §3.10)
            "pages": stage_page_index(self.content, self.ctx, self.salts, n),
        }


def seal_pack(key_n: bytes, n: int, pack: dict) -> dict:
    return crypto.seal(crypto.hkdf(key_n, crypto.pack_info(n)), dumps(pack), f"pack/{n}")


def build_finale(content: Content, ctx: dict, expanded: dict[str, Expanded], confession: RenderedDoc,
                 letter: RenderedDoc) -> dict:
    c = ctx["c"]
    fates = [
        {"who": f.who, "name": getattr(c, f.who).full() if f.who else None, "text": render(f.text, ctx)}
        for f in content.finale.fates
    ]
    answers = {u.path: display_answer(u, expanded[u.path], content, ctx) for u in units(content)}
    out = {"v": 1, "confession": confession.record(), "letter": letter.record(), "fates": fates, "answers": answers}
    thanks = content.finale.thanks
    if thanks is not None:  # необязательный блок: ключа нет, пока поля нет в finale.yaml
        out["thanks"] = {k: render(getattr(thanks, k), ctx) for k in ("title", "text", "signature")}
    return out


def seal_finale(key_last: bytes, finale: dict) -> dict:
    return crypto.seal(crypto.hkdf(key_last, crypto.FINALE_INFO), dumps(finale), "finale")
