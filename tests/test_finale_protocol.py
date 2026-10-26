"""Финальный заход 26.10: развязка-протокол (R-01, R-02) на сайте через общий конвейер протокола
(engine/protocol.py), конверт «после финала» (stage: последний этап + 1, только печать), подсказка
владельца к паролю облака (password_hint) и пароль облака в аварийном конверте."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from engine import ROOT, crypto
from engine.build import build, prepare
from engine.content import ContentError, load_content
from engine.models import DocFrontMatter
from engine.normalize import normalize
from engine.protocol import interview, strip_person_marks, surname_in
from engine.templating import make_context

CONTENT = ROOT / "content"


# ---------------------------------------------------------------- протокол: фамилии и «При допросе»


def test_surname_in_one_initial():
    assert surname_in("руководитель следственной группы майор юстиции Иванов М.") == "Иванов"
    assert surname_in("сержант полиции Ковалёв Д. О.") == "Ковалёв"
    assert surname_in("Майор юстиции, руководитель следственной группы Беляев А. Н.") == "Беляев"
    # полные инициалы важнее одного: «Петров А. Б.» не превращается в «А.»
    assert surname_in("майор Петров А. Б., при участии Сидорова В.") == "Петров"
    assert surname_in("без фамилии") is None


def _rows(meta: dict) -> dict[str, str]:
    d = {"date": "2026-11-15T15:20", "place": "кабинет", "meta": meta}
    p = interview(d, "<p><strong>Вопрос:</strong> Да?</p>\n<p><strong>Ответ:</strong> Да.</p>", None, {"c": None})
    return {r["label"]: str(r["value"]) for r in p["rows"] if not r.get("gap")}, p


def test_present_label_interrogation_vs_interview():
    rows, p = _rows({"person_label": "Допрошен в качестве подозреваемого", "person": ["Иванов Иван Иванович, 1990 г. р."],
                     "by_label": "Допросил", "by": "майор юстиции Петров П.", "present": "защитник"})
    assert rows["При допросе"] == "защитник" and "При опросе" not in rows
    assert p["asker"] == "Петров" and p["answerer"] == "Иванов"
    assert '<span class="who who--q">Петров:</span>' in str(p["body"])
    rows, _ = _rows({"person": ["Иванов Иван Иванович, 1990 г. р."], "by": "сержант Ковалёв Д. О.", "present": "мать"})
    assert rows["При опросе"] == "мать" and "При допросе" not in rows


def test_strip_person_marks():
    assert strip_person_marks("<!-- person: volkov -->\n\nТекст") == "\n\nТекст"


def test_doc_front_matter_protocol_fields_only_for_protocol():
    DocFrontMatter.model_validate({"id": "R-09", "form": "protocol", "title": "т", "date": "2026-11-15",
                                   "meta": {"by": "x"}, "signed": [{"role": "a", "name": "b"}]})
    with pytest.raises(ValidationError, match="только у протокола"):
        DocFrontMatter.model_validate({"id": "R-09", "form": "letter", "title": "т", "date": "2026-11-15"})


# ---------------------------------------------------------------- сборка: развязка, облако, пакеты


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("fin")
    salts = tmp / "salts.lock.json"
    shutil.copyfile(ROOT / "engine" / "salts.lock.json", salts)
    dist = tmp / "dist"
    build(content_dir=CONTENT, dist=dist, salts_path=salts, media_dir=ROOT / "media", log=lambda *_: None)
    prep = prepare(CONTENT, salts, create_salts=False)
    box = json.loads((dist / "data" / "finale.json").read_text(encoding="utf-8"))
    fin = json.loads(crypto.open_(crypto.hkdf(prep.keys[prep.content.last_stage], crypto.FINALE_INFO), box,
                                  "finale").decode("utf-8"))
    return prep, dist, fin


def test_finale_protocols_in_paper_layout(built):
    prep, _, fin = built
    content, ctx = prep.content, prep.ctx
    c = ctx["c"]
    keys = ["confession", "letter"] + (["confession2"] if content.finale.confession2 else [])
    assert all(k in fin for k in keys)
    for k in ("confession", "confession2"):
        if k not in fin:
            continue
        html = fin[k]["html"]
        assert 'class="blank blank--protocol"' in html and 'class="blank__fields proto-fields"' in html
        assert "<dt>При допросе</dt>" in html and "При опросе" not in html
        assert f'<span class="who who--q">{c.belyaev.last()}:</span>' in html  # следователь с одним инициалом
        assert 'class="who who--a"' in html and 'class="blank__sign"' in html
        assert "person:" not in html and "&lt;!--" not in html


def test_finale_confession2_matches_yaml(built):
    prep, _, fin = built
    assert ("confession2" in fin) == (prep.content.finale.confession2 is not None)


def test_after_final_documents_not_in_packs(built):
    prep, dist, _ = built
    content = prep.content
    after = [d.id for d in content.documents if d.stage == content.after_final_stage]
    assert after, "в documents.yaml есть конверт «после финала»"
    assert all(content.documents_by_id[i].kind == "paper" and not content.documents_by_id[i].page_slugs for i in after)
    for st in content.stages:
        box = json.loads((dist / "data" / f"pack-{st.n}.json").read_text(encoding="utf-8"))
        pack = json.loads(crypto.open_(crypto.hkdf(prep.keys[st.n], crypto.pack_info(st.n)), box,
                                       f"pack/{st.n}").decode("utf-8"))
        ids = {d["id"] for d in pack["documents"]}
        assert ids and not ids & set(after), st.n


def test_cloud_two_locks_hint_behind_key(built):
    """Облако с двумя замками (аудит S-134): без ключа QR в оболочке нет ни формы с логином, ни подсказки;
    ключ страницы открывает форму входа (логин, подсказка владельца), пароль — содержимое."""
    from engine.check import leak_needles
    from engine.leakscan import scan_text
    from engine.pages import open_password_payload

    prep, dist, _ = built
    cloud = prep.content.pages["cloud"]
    assert cloud.locked is True and cloud.password_hint
    html = (dist / "p" / "cloud" / "index.html").read_text(encoding="utf-8")
    assert 'data-access="key"' in html and cloud.password_hint not in html and cloud.account not in html
    assert cloud.password not in html
    payload = json.loads((dist / "p" / "cloud" / "payload.json").read_text(encoding="utf-8"))
    assert cloud.password_hint not in json.dumps(payload, ensure_ascii=False)
    inner, outer = open_password_payload(cloud, payload, prep.salts.page_key("cloud"))
    assert outer["login"] == {"account": cloud.account, "hint": cloud.password_hint} and outer["html"] == ""
    assert inner["slug"] == "cloud" and inner["html"]
    assert normalize("password", cloud.password) not in normalize("password", cloud.password_hint)
    # подсказка — секрет этапа облака: фраза из неё на открытой странице — утечка
    ns = leak_needles(prep)
    assert scan_text(f"<p>{cloud.password_hint}</p>", ns, "x")


# ---------------------------------------------------------------- загрузчик: конверт «после финала»


def _content_with(tmp_path: Path, line: str) -> Path:
    root = tmp_path / "content"
    shutil.copytree(CONTENT, root)
    p = root / "documents.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    data["documents"].append(yaml.safe_load(line))
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10_000), encoding="utf-8")
    return root


def test_after_final_stage_only_paper_without_page(tmp_path):
    last = load_content(CONTENT).last_stage
    root = _content_with(tmp_path, f'{{id: "9-01", stage: {last + 1}, kind: lab, title: "т"}}')
    with pytest.raises(ContentError, match="после финала"):
        load_content(root)


def test_stage_beyond_after_final_is_error(tmp_path):
    last = load_content(CONTENT).last_stage
    root = _content_with(tmp_path, f'{{id: "9-01", stage: {last + 2}, kind: paper, title: "т"}}')
    with pytest.raises(ContentError, match=f"этапа {last + 2} нет"):
        load_content(root)


# ---------------------------------------------------------------- аварийный конверт и бумага


def test_emergency_has_cloud_password_and_second_protocol():
    from engine.emergency import emergency_data

    content = load_content(CONTENT)
    data = emergency_data(content)
    cloud = content.pages["cloud"]
    st = content.documents_by_id[cloud.doc].stage
    pw = [p for s in data["stages"] if s["n"] == st for p in s["passwords"]]
    assert pw and pw[0]["password"] == cloud.password and pw[0]["hint"]
    if cloud.locked is True:  # два замка: адрес с ключом страницы (как QR записки) + пароль
        assert "/p/cloud/#k=" in pw[0]["url"] and pw[0]["doc"] == cloud.doc
    assert (data["confession2"] is not None) == (content.finale.confession2 is not None)
    assert "person:" not in str(data["confession"]["html"])


def test_paper_after_final_protocol_and_cover():
    from engine.paper import COVER_TEMPLATE, _common, doc_data, paper_ids
    from engine.printing import print_env

    content = load_content(CONTENT)
    ctx = make_context(content)
    after = content.after_final_stage
    ids = [i for i in paper_ids(content) if content.documents_by_id[i].stage == after]
    assert ids
    protos = [doc_data(content, i, ctx) for i in ids if content.paper[i].meta.form == "protocol"]
    assert protos
    for d in protos:
        labels = [r["label"] for r in d["proto"]["rows"] if not r.get("gap")]
        assert "При допросе" in labels and d["proto"]["asker"] == ctx["c"].belyaev.last()
    html = print_env().get_template(COVER_TEMPLATE).render(
        n=after, rows=[{"id": i, "title": "т", "pages": 1} for i in ids], **_common(content, ctx))
    assert f"Конверт {after}" in html and "Вскрыть после финала" in html and all(i in html for i in ids)
