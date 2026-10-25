"""Каталог лаборатории и проверки сборки (docs/02 §2а, docs/03 §6, REDESIGN-2026-10 §2–3).

Испорченные копии ``content/`` во временной папке; целиком dist/ здесь не собирается (это tests/test_build.py).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable

import pytest
import yaml

from engine import ROOT, crypto
from engine.build import BuildError, build, prepare, site_base_ctx
from engine.content import ContentError, load_content
from engine.lab import lab_catalog, lab_objects, lab_problems, lab_site
from engine.labmatch import resolve_object
from engine.templating import make_context

CONTENT = ROOT / "content"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    dst = tmp_path / "content"
    shutil.copytree(CONTENT, dst)
    return dst


def edit_yaml(root: Path, rel: str, fn: Callable[[object], None]) -> None:
    p = root / rel
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    fn(data)
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def find(items: list[dict], id_: str) -> int:
    return next(i for i, x in enumerate(items) if x["id"] == id_)


def problems_of(root: Path):
    c = load_content(root)
    return lab_problems(c, make_context(c))


def text_of(errors) -> str:
    return "\n".join(str(e) for e in errors)


# ---------------------------------------------------------------- текущий контент


def test_current_content_has_no_lab_errors():
    errors, _ = problems_of(CONTENT)
    assert errors == [], text_of(errors)


def test_pillbox_in_inventory_from_stage_1_with_stage_3_bases():
    """Таблетница — в описи 1-09 (from_stage 1). Правило 2.1.4: результат этапа N > from_stage
    опирается только на документы этапа N. Заключение (с документом) — на основаниях этапа 3;
    ранние запросы (атмосферные записи этапов 1–2) отвечают нейтрально и без документа."""
    c = load_content(CONTENT)
    pill = next(o for o in c.expertise.objects if o.id == "pillbox")
    assert pill.from_stage == 1
    docs = c.documents_by_id
    results = [r for r in c.expertise.results if r.object == "pillbox"]
    assert results
    for r in results:
        if r.stage > pill.from_stage:
            assert all(docs[b].stage == r.stage for b in r.bases), r.id
    conclusions = [r for r in results if r.doc]
    assert conclusions and all(r.stage == 3 and all(docs[b].stage == 3 for b in r.bases) for r in conclusions)
    early = [r for r in results if r.stage < 3]
    assert early and all(not r.doc and r.text for r in early), "ранние записи — короткий атмосферный текст"


def test_every_title_is_recognised_on_every_available_stage():
    c = load_content(CONTENT)
    objs = lab_objects(c, make_context(c))
    for o in objs:
        for st in c.stages:
            if st.n >= o["from_stage"]:
                got = resolve_object(o["title"], [x for x in objs if x["from_stage"] <= st.n])
                assert got == {"status": "ok", "id": o["id"]}, (o["id"], st.n, got)


def test_lab_yaml_loads_and_site_ctx():
    c = load_content(CONTENT)
    ctx = make_context(c)
    site = lab_site(c, ctx)
    assert site["name"] == c.world["brands"]["lab"] and site["full_name"] == c.world["brands"]["lab_full"]
    assert {"tagline", "about", "about_html", "accreditation", "staff", "contacts", "services_note"} <= set(site)
    assert set(site["contacts"]) == {"address", "phone", "hours", "email"}
    assert "{{" not in json.dumps(site, ensure_ascii=False)
    base = site_base_ctx(c, {"title": "x"})
    assert base["lab_site"] == site and base["brands"]["lab"] == site["name"]


# ---------------------------------------------------------------- каталог в пакетах


def test_catalog_has_aliases_ref_description_and_objects_sit_in_their_from_stage(root):
    def fn(d):
        i = find(d["objects"], "pillbox")
        d["objects"][i]["aliases"] = ["Таблетниц", "пилюл"]
        d["types"][0]["description"] = "Описание {{ w.brands.lab }}"

    edit_yaml(root, "expertise.yaml", fn)
    c = load_content(root)
    ctx = make_context(c)
    first = c.stages[0].n
    cat1 = lab_catalog(c, ctx, first, [])
    pill = next(o for o in cat1["objects"] if o["id"] == "pillbox")
    assert pill["aliases"] == ["таблетниц", "пилюл"], "алиасы нормализованы"
    assert pill["ref"] == "1-09, поз. 17.3" and pill["title"] == next(
        o.title for o in c.expertise.objects if o.id == "pillbox")
    assert cat1["types"][0]["description"] == "Описание " + c.world["brands"]["lab"]
    # остальные виды — свои описания из контента (шаблоны раскрыты) или None, если описания нет
    assert all(t["description"] is None or "{{" not in t["description"] for t in cat1["types"][1:])
    assert [t["id"] for t in cat1["types"]] == [t.id for t in c.expertise.types]
    for st in c.stages:
        cat = lab_catalog(c, ctx, st.n, [])
        assert {o["id"] for o in cat["objects"]} == {o.id for o in c.expertise.objects if o.from_stage == st.n}
        assert (cat["types"] != []) == (st.n == first)
        assert all(set(o) == {"id", "title", "ord", "params", "aliases", "ref"} for o in cat["objects"])


def test_catalog_end_to_end_in_built_dist(tmp_path):
    dist = tmp_path / "dist"
    salts = tmp_path / "salts.lock.json"
    rep = build(dist=dist, salts_path=salts)
    k1 = crypto.b64u_decode(rep.stage_keys[1])
    box = json.loads((dist / "data/pack-1.json").read_text(encoding="utf-8"))
    pk = json.loads(crypto.open_(crypto.hkdf(k1, crypto.pack_info(1)), box, "pack/1"))
    assert {o["id"] for o in pk["lab"]["objects"]} >= {"pillbox", "water"}
    assert all("aliases" in o and "ref" in o for o in pk["lab"]["objects"])
    # алиасы и тексты лаборатории не раскрывают закрытое: страница лаборатории собрана, тексты открыты
    html = (dist / "lab" / "index.html").read_text(encoding="utf-8")
    assert "<html" in html


# ---------------------------------------------------------------- ошибки сборки


def test_short_stem_is_error(root):
    def fn(d):
        d["objects"][find(d["objects"], "water")]["aliases"] = ["вода бу"]

    edit_yaml(root, "expertise.yaml", fn)
    errors, _ = problems_of(root)
    t = text_of(errors)
    assert "content/expertise.yaml: objects[3].aliases[0]" in t and "основа «бу» короче 3 символов" in t


def test_alias_empty_after_normalization_is_error(root):
    def fn(d):
        d["objects"][find(d["objects"], "water")]["aliases"] = ["?!"]

    edit_yaml(root, "expertise.yaml", fn)
    errors, _ = problems_of(root)
    assert "пуст после нормализации" in text_of(errors)


def test_same_alias_on_different_objects_is_error(root):
    def fn(d):
        d["objects"][find(d["objects"], "water")]["aliases"] = ["Бутыл"]
        d["objects"][find(d["objects"], "costume")]["aliases"] = ["бутыл"]

    edit_yaml(root, "expertise.yaml", fn)
    errors, _ = problems_of(root)
    t = text_of(errors)
    assert "objects[4].aliases[0]" in t and "уже есть у объекта «water»" in t


def test_same_alias_same_stems_other_order_is_error(root):
    def fn(d):
        d["objects"][find(d["objects"], "water")]["aliases"] = ["бутыл вод"]
        d["objects"][find(d["objects"], "costume")]["aliases"] = ["вод бутыл"]

    edit_yaml(root, "expertise.yaml", fn)
    errors, _ = problems_of(root)
    assert "уже есть у объекта «water»" in text_of(errors)


def test_alias_that_steals_other_title_is_error(root):
    """Алиас чужого объекта, равный по весу названию телефона, делает это название неоднозначным."""
    def fn(d):
        d["objects"][find(d["objects"], "costume")]["aliases"] = ["телефон погибшего"]

    edit_yaml(root, "expertise.yaml", fn)
    errors, _ = problems_of(root)
    t = text_of(errors)
    assert "objects[5].title" in t and "Телефон погибшего" in t and "неоднозначно: costume, phone" in t


def test_title_that_does_not_recognise_itself_is_error(root):
    def fn(d):
        d["objects"][find(d["objects"], "phone")]["title"] = "Телефон"   # токен «телефон», а объект «tel» ниже
        d["objects"].append({"id": "tel", "title": "Телефонная книжка", "aliases": ["телефон"]})

    edit_yaml(root, "expertise.yaml", fn)
    errors, _ = problems_of(root)
    t = text_of(errors)
    assert "title" in t and "Телефон" in t and "неоднозначно" in t


def test_title_with_only_short_words_is_not_recognised(root):
    def fn(d):
        d["objects"][find(d["objects"], "costume")]["title"] = "А Б"

    edit_yaml(root, "expertise.yaml", fn)
    errors, _ = problems_of(root)
    assert "название «А Б»" in text_of(errors) and "не распознаётся" in text_of(errors)


def test_basis_rule_violation_is_error(root):
    def fn(d):
        d["results"][find(d["results"], "pillbox-content")]["bases"] = ["3-01", "1-09"]
        idx["pillbox"] = find(d["results"], "pillbox-content")

    idx: dict[str, int] = {}
    edit_yaml(root, "expertise.yaml", fn)
    errors, _ = problems_of(root)
    t = text_of(errors)
    assert f"results[{idx['pillbox']}].bases[1]" in t and "основание «1-09» (этап 1)" in t and "этапа 3" in t


def test_basis_rule_does_not_apply_when_object_appears_at_result_stage(root):
    # ингалятор виден с этапа 2 — результаты этапа 2 могут опираться на документы любых этапов ≤ 2
    errors, _ = problems_of(CONTENT)
    c = load_content(CONTENT)
    inh = next(r for r in c.expertise.results if r.id == "inhaler-chem")
    assert any(c.documents_by_id[b].stage < inh.stage for b in inh.bases)
    assert errors == []


def test_basis_rule_violation_stops_build_and_check_setup(root, tmp_path):
    def fn(d):
        d["results"][find(d["results"], "pillbox-prints")]["bases"] = ["2-02"]

    edit_yaml(root, "expertise.yaml", fn)
    with pytest.raises(BuildError) as exc:
        prepare(root, tmp_path / "salts.lock.json", create_salts=False)
    assert "pillbox-prints" in str(exc.value) and "bases[0]" in str(exc.value)


def test_shared_short_stem_is_warning_not_error(root):
    def fn(d):
        d["objects"][find(d["objects"], "water")]["aliases"] = ["фиал"]
        d["objects"][find(d["objects"], "costume")]["aliases"] = ["фиал"]

    edit_yaml(root, "expertise.yaml", fn)
    errors, warnings = problems_of(root)
    assert any("уже есть" in str(e) for e in errors), "одинаковые алиасы — ошибка"

    def fn2(d):
        d["objects"][find(d["objects"], "water")]["aliases"] = ["фиал"]
        d["objects"][find(d["objects"], "costume")]["aliases"] = ["фиал шар"]

    edit_yaml(root, "expertise.yaml", fn2)
    errors, warnings = problems_of(root)
    assert errors == [], text_of(errors)
    assert any("общая основа «фиал»" in str(w) and "water" in str(w) and "costume" in str(w) for w in warnings)


# ---------------------------------------------------------------- схема


def test_alias_must_be_list_of_strings(root):
    def fn(d):
        d["objects"][0]["aliases"] = "ингалятор"

    edit_yaml(root, "expertise.yaml", fn)
    with pytest.raises(ContentError) as exc:
        load_content(root)
    assert "objects[0].aliases" in str(exc.value)


def test_lab_yaml_is_required_and_validated(root):
    (root / "lab.yaml").unlink()
    with pytest.raises(ContentError) as exc:
        load_content(root)
    assert "content/lab.yaml" in str(exc.value) and "файл не найден" in str(exc.value)


def test_lab_yaml_missing_field(root):
    def fn(d):
        del d["contacts"]["phone"]

    edit_yaml(root, "lab.yaml", fn)
    with pytest.raises(ContentError) as exc:
        load_content(root)
    assert "content/lab.yaml: contacts.phone" in str(exc.value)


def test_lab_yaml_template_typo(root):
    p = root / "lab.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("w.brands.lab }}", "w.brands.nolab }}", 1), encoding="utf-8")
    with pytest.raises(ContentError) as exc:
        load_content(root)
    assert "content/lab.yaml: name" in str(exc.value)


def test_lab_yaml_todos_are_collected(root):
    """lab.yaml заполнен сценаристом: в боевом контенте TODO нет; поставленная в копии заглушка
    собирается как value-TODO с путём до поля."""
    from engine.content import collect_todos

    assert [t for t in collect_todos(load_content(CONTENT)) if t.file == "content/lab.yaml"] == []

    def fn(d):
        d["tagline"] = "TODO(content): слоган"

    edit_yaml(root, "lab.yaml", fn)
    todos = [t for t in collect_todos(load_content(root)) if t.file.endswith("lab.yaml")]
    assert [t.loc for t in todos] == ["tagline"] and all(t.kind == "value" for t in todos)


# ---------------------------------------------------------------- dump-answers и «Аварийный конверт»


def test_dump_answers_has_object_text_next_to_id():
    from engine.dump import answers_data

    prep = prepare(CONTENT, ROOT / "engine" / "salts.lock.json", create_salts=False)
    data = answers_data(prep)
    titles = {o["id"]: o["title"] for o in data["labObjects"]}
    assert data["lab"] and all(x["objectTitle"] == titles[x["object"]] for x in data["lab"])
    assert all(x["objectFromStage"] <= x["stage"] for x in data["lab"])
    assert {"id", "title", "fromStage", "aliases", "ref"} == set(data["labObjects"][0])
    # введённый как есть, объект распознаётся сам (так его вводят e2e-тесты)
    objs = lab_objects(prep.content, prep.ctx)
    for x in data["lab"]:
        avail = [o for o in objs if o["from_stage"] <= x["stage"]]
        assert resolve_object(x["objectTitle"], avail) == {"status": "ok", "id": x["object"]}


def test_emergency_envelope_lists_only_results_not_the_whole_inventory():
    from engine.emergency import emergency_data
    from engine.printing import print_env

    c = load_content(CONTENT)
    data = emergency_data(c)
    printed = {x["object"] for x in data["lab"]}
    with_results = {o.title for o in c.expertise.objects if o.id in {r.object for r in c.expertise.results}}
    ctx = make_context(c)
    from engine.templating import render
    assert printed == {render(t, ctx) for t in with_results}
    assert all({"object_from", "ref"} <= set(x) for x in data["lab"])
    html = print_env().get_template("print/answers.html").render(**data)
    assert "ничего не выявила" in html and "нельзя передать в лабораторию" in html
    assert "Недостаточно оснований" not in html
