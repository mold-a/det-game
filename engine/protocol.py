"""Протокол (опроса, допроса): поля шапки «МЕТКА: значение» и реплики с фамилиями — общий конвейер
бумаги (``engine/paper.py``, бланк ``print/paper/protocol.html``) и развязки на сайте
(``engine/documents.py``, бланк ``blanks/protocol.html``): один разбор, одинаковый вид.

- ``interview`` — данные листа: строки полей (``interview_rows``), фамилии спрашивающего и отвечающего,
  преобразованный текст (``dialog_html``);
- ``surname_in`` — фамилия из «майор юстиции Беляев А. Н.» и «майор юстиции Авдеенко М.» (один инициал);
- у допроса (``by_label`` «Допросил…» или строка «Допрошен…») строка присутствовавших — «При допросе».
"""

from __future__ import annotations

import re
from typing import Any

from markupsafe import Markup

# Метка опрашиваемого — HTML-комментарий в тексте протокола.
PERSON_RE = re.compile(r"<!--\s*person:\s*([A-Za-z0-9_-]+)\s*-->")
_TAG_RE = re.compile(r"<[^>]+>")


def person_marks(text: str) -> list[str]:
    """ID персонажей из меток ``<!-- person: <id> -->`` по порядку."""
    return PERSON_RE.findall(text)


def strip_person_marks(text: str) -> str:
    """Текст без меток ``<!-- person -->`` (сайт: Markdown без сырого HTML показал бы их буквально)."""
    return PERSON_RE.sub("", text)


def _plain(html: str) -> str:
    from html import unescape

    return " ".join(unescape(_TAG_RE.sub(" ", html.replace("<br>", ", "))).split()).replace(" ,", ",")


# Поля протокола «МЕТКА: значение». Одиночный протокол — из front matter (meta.person, by, present, place,
# date/start/end); протоколы 1-08 — из HTML макроса head() в тексте (классы proto__fields, fld, fld__label,
# fld__value): блок вынимается из текста и печатается в шапке листа рядом с фото.
_FIELDS_RE = re.compile(r'<div class="proto__fields[^"]*">\s*((?:<div class="fld[^"]*">\s*<span class="fld__label">'
                        r'.*?</span>\s*<span class="fld__value">.*?</span>\s*</div>\s*)*)</div>\s*', re.S)
_FIELD_RE = re.compile(r'<div class="fld[^"]*">\s*<span class="fld__label">(.*?)</span>\s*'
                       r'<span class="fld__value">(.*?)</span>\s*</div>', re.S)
_WHO_RE = re.compile(r"^(.*?),\s*(\d{4})\s*г\.\s*р\.\s*(?:,\s*(.*))?$", re.S)
_SURNAME_RE = re.compile(r"([А-ЯЁ][а-яё\-]+)\s+[А-ЯЁ]\.\s?[А-ЯЁ]\.")
_SURNAME1_RE = re.compile(r"([А-ЯЁ][а-яё\-]+)\s+[А-ЯЁ]\.(?![а-яё])")  # один инициал: «Авдеенко М.»
_P_RE = re.compile(r"<p>(.*?)</p>", re.S)
_QA_LABEL_RE = re.compile(r"\s*<strong>(Вопрос|Ответ):</strong>\s*")
_NOTE_LABEL_RE = re.compile(r"((?:Служебная )?[Оо]тметка[^:<]{0,60}):\s*")
_EM_ONLY_RE = re.compile(r"<em>((?:(?!</?em>).)*)</em>", re.S)
PROTO_LABELS = {"year": "Год рождения", "info": "Сведения", "present": "При опросе", "by": "Опросил",
                "when": "Дата, время", "where": "Место", "note": "Примечание опросившего",
                "present_interrogation": "При допросе"}


def split_fields(html: str) -> tuple[list[tuple[str, str]], str]:
    """Блок ``.proto__fields`` из HTML раздела → ([(подпись, значение HTML)], HTML без блока)."""
    m = _FIELDS_RE.search(html)
    if not m:
        return [], html
    return [(_plain(a), b.strip()) for a, b in _FIELD_RE.findall(m[1])], html[:m.start()] + html[m.end():]


def _field_kind(label: str) -> str:
    low = label.lower()
    if low.startswith(("опрош", "объяснени", "допрош")):
        return "who"
    if low.startswith(("опросил", "составил", "допросил", "принял")):
        return "by"
    if low.startswith(("при опросе", "при допросе", "присутств")):
        return "present"
    if low.startswith("дата"):
        return "when"
    if low.startswith("место"):
        return "where"
    return "other"


def _lines_html(v: Any) -> str:
    from markupsafe import escape

    if isinstance(v, list):
        return ", ".join(str(escape(x)) for x in v if str(x).strip())
    return str(escape(v or ""))


def interview_rows(pairs: list[tuple[str, str]], present_label: str = PROTO_LABELS["present"]) -> list[dict[str, Any]]:
    """Поля протокола (подпись, значение HTML) → строки «МЕТКА: значение» в порядке бланка: кто (ФИО,
    год рождения, сведения), пробел, дата и время, место, кто опросил, кто присутствовал, прочее.
    Строка «Опрошен(а)» ``ФИО, 1981 г. р., должность`` делится на три поля; без года — как есть."""
    by_kind: dict[str, list[tuple[str, str]]] = {}
    for label, value in pairs:
        if value and value.strip():
            by_kind.setdefault(_field_kind(label), []).append((label, value))
    rows: list[dict[str, Any]] = []
    for label, value in by_kind.get("who", []):
        m = _WHO_RE.match(value.strip())
        if m:
            rows.append({"label": label, "value": Markup(m[1].strip())})
            rows.append({"label": PROTO_LABELS["year"], "value": Markup(m[2])})
            if m[3] and m[3].strip():
                rows.append({"label": PROTO_LABELS["info"], "value": Markup(m[3].strip())})
        else:
            rows.append({"label": label, "value": Markup(value)})
    if rows:
        rows.append({"gap": True})
    for kind in ("when", "where", "by", "present", "other"):
        for label, value in by_kind.get(kind, []):
            rows.append({"label": present_label if kind == "present" else label, "value": Markup(value)})
    return rows


def surname_in(text: str) -> str | None:
    """Фамилия из «сержант полиции Ковалёв Д. О.» (слово перед инициалами); с одним инициалом —
    «майор юстиции Авдеенко М.». Полные инициалы ищутся первыми."""
    plain = _plain(text)
    m = _SURNAME_RE.search(plain) or _SURNAME1_RE.search(plain)
    return m[1] if m else None


def is_interrogation(pairs: list[tuple[str, str]]) -> bool:
    """Допрос, а не опрос: «Допросил…» у проводившего или «Допрошен(а)…» у допрошенного."""
    return any(label.lower().startswith(("допросил", "допрош")) for label, _ in pairs)


def dialog_html(html: str, asker: str | None, answerer: str | None) -> str:
    """Реплики протокола: «**Вопрос:**» / «**Ответ:**» → фамилия опросившего / опрашиваемого
    (``.who--q`` / ``.who--a``); абзац без метки после реплики — её продолжение (``.qa-cont``, без
    повторной фамилии); курсивные абзацы после последней реплики (пояснение присутствовавшего, запись
    опросившего) — блоком под одной меткой «Примечание опросившего:» обычным текстом; курсивные абзацы
    между репликами — ``.rem`` без курсива. Без реплик (объяснение от первого лица) текст не меняется."""
    from markupsafe import escape

    paras = list(_P_RE.finditer(html))
    kinds: list[tuple[str, re.Match | None]] = []
    for m in paras:
        q = _QA_LABEL_RE.match(m[1])
        kinds.append(("qa", q) if q else ("em", None) if _EM_ONLY_RE.fullmatch(m[1].strip()) else ("p", None))
    qa = [i for i, (k, _) in enumerate(kinds) if k == "qa"]
    if not qa:
        return html
    last = qa[-1]
    note = [i for i in range(last + 1, len(paras)) if kinds[i][0] == "em"]
    # примечание — подряд идущие курсивные абзацы (между ними только пробелы)
    run: list[int] = []
    for i in note:
        if run and (i != run[-1] + 1 or html[paras[run[-1]].end():paras[i].start()].strip()):
            break
        run.append(i)
    # абзацы без метки — продолжение реплики, если стоят между репликами или перед примечанием; после
    # последней реплики без примечания («С моих слов записано верно», объяснение от первого лица) — текст
    cont_end = run[0] if run else last
    out: list[str] = []
    pos = 0
    in_note = False
    for i, m in enumerate(paras):
        out.append(html[pos:m.start()])
        pos = m.end()
        kind, q = kinds[i]
        if kind == "qa":
            k = "q" if q[1] == "Вопрос" else "a"
            name = (asker if k == "q" else answerer) or q[1]
            out.append(f'<p class="qa qa--{k}"><span class="who who--{k}">{escape(name)}:</span> {m[1][q.end():]}</p>')
        elif i in run:
            inner = _EM_ONLY_RE.fullmatch(m[1].strip())[1]
            own = _NOTE_LABEL_RE.match(inner)
            if own or not in_note:
                if in_note:
                    out.append("</div>")
                label = own[1] if own else PROTO_LABELS["note"]
                out.append(f'<div class="proto__note"><div class="proto__note-label">{label}:</div>')
                in_note = True
                if own:
                    inner = inner[own.end():]
                    inner = inner[:1].upper() + inner[1:]
            out.append(f"<p>{inner}</p>")
            if i == run[-1]:
                out.append("</div>")
                in_note = False
        elif kind == "em":
            out.append(f'<p class="rem">{_EM_ONLY_RE.fullmatch(m[1].strip())[1]}</p>')
        elif qa[0] < i < cont_end:
            out.append(f'<p class="qa-cont">{m[1]}</p>')
        else:
            out.append(m[0])
    out.append(html[pos:])
    return "".join(out)


def _ddmmyyyy(s: str | None) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    return f"{m[3]}.{m[2]}.{m[1]}" if m else (s or "")


def interview(d: dict[str, Any], body_html: str, person: dict | None, ctx: dict,
              pairs: list[tuple[str, str]] | None = None) -> dict[str, Any]:
    """Данные листа протокола: поля, фамилии для реплик, преобразованный текст. ``pairs`` — поля из
    макроса head() (раздел 1-08); без них — из front matter одиночного протокола."""
    meta = d.get("meta") or {}
    if pairs is None:
        pairs = []
        who = meta.get("person")
        if who:
            pairs.append((meta.get("person_label") or "Опрошен(а)", _lines_html(who)))
        iso = d.get("date") or ""
        start = meta.get("start") or (iso[11:16] if len(iso) >= 16 and iso[10] == "T" else "")
        end = meta.get("end") or ""
        when = ", ".join(x for x in (_ddmmyyyy(iso), "–".join(x for x in (start, end) if x)) if x)
        if when:
            pairs.append((PROTO_LABELS["when"], when))
        if d.get("place"):
            pairs.append((PROTO_LABELS["where"], _lines_html(d["place"])))
        if meta.get("by"):
            pairs.append((meta.get("by_label") or PROTO_LABELS["by"], _lines_html(meta["by"])))
        if meta.get("present"):
            pairs.append((PROTO_LABELS["present"], _lines_html(meta["present"])))
    by = next((v for k, v in pairs if _field_kind(k) == "by"), "")
    who = next((v for k, v in pairs if _field_kind(k) == "who"), "")
    when = next((_plain(v) for k, v in pairs if _field_kind(k) == "when"), "")
    answerer = None
    if person and person.get("known"):
        answerer = ctx["c"][person["id"]].last()
    if not answerer and who:
        answerer = (_plain(who).split() or [None])[0]
        answerer = answerer.rstrip(",") if answerer else None
    asker = surname_in(by) if by else None
    present_label = PROTO_LABELS["present_interrogation" if is_interrogation(pairs) else "present"]
    return {"rows": interview_rows(pairs, present_label), "asker": asker, "answerer": answerer,
            "who": _WHO_RE.sub(r"\1", _plain(who)) if who else "", "when": when,
            "where": next((_plain(v) for k, v in pairs if _field_kind(k) == "where"), ""),
            "date": when[:10] if re.match(r"\d\d\.\d\d\.\d{4}", when) else "",
            "body": Markup(dialog_html(body_html, asker, answerer))}
