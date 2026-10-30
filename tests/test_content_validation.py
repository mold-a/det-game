"""Загрузка и валидация content/: текущий контент и испорченные копии во временной папке."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Callable

import pytest
import yaml

from engine import ROOT
from engine.content import ContentError, collect_todos, load_content, units
from engine.templating import make_context, make_link, render, render_tree

CONTENT = ROOT / "content"


# ---------------------------------------------------------------- помощники


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


def edit_text(root: Path, rel: str, old: str, new: str) -> None:
    p = root / rel
    s = p.read_text(encoding="utf-8")
    assert old in s, f"в {rel} нет {old!r}"
    p.write_text(s.replace(old, new, 1), encoding="utf-8")


def errors_of(root: Path) -> list[str]:
    with pytest.raises(ContentError) as exc:
        load_content(root)
    errs = [str(e) for e in exc.value.errors]
    assert errs, "ContentError без ошибок"
    return errs


def assert_error(root: Path, *parts: str) -> list[str]:
    errs = errors_of(root)
    assert any(all(p in e for p in parts) for e in errs), "\n".join(["ожидалось: " + " … ".join(parts), *errs])
    return errs


def q_index(data: dict, n: int, qid: str) -> tuple[int, int]:
    for si, st in enumerate(data["stages"]):
        if st["n"] == n:
            for qi, q in enumerate(st["questions"]):
                if q["id"] == qid:
                    return si, qi
    raise KeyError((n, qid))


def find(items: list[dict], id_: str) -> int:
    return next(i for i, x in enumerate(items) if x["id"] == id_)


def q_loc(root: Path, n: int, qid: str) -> str:
    """«stages[si].questions[qi]» вопроса ``s<n>.<qid>`` по данным content (номера не зашиваем: вопросы добавляются)."""
    d = yaml.safe_load((root / "stages.yaml").read_text(encoding="utf-8"))
    si, qi = q_index(d, n, qid)
    return f"stages[{si}].questions[{qi}]"


# ---------------------------------------------------------------- текущий контент


def test_current_content_loads():
    c = load_content(CONTENT)
    assert c.settings.game_id
    assert {s.n for s in c.stages} == {1, 2, 3, 4}
    # базовые страницы + «Круг» (главная и заглушка); страницы сценариста (REDESIGN §4.3) добавляются сверх
    # 28.10: «Кадр» (inna, kadr-*) убран, фото Рябовой — в «Круге» (krug-ryabova, документ 2-09)
    assert {"call", "cloud", "gromov", "krug-ryabova", "news", "pharma", "video", "krug", "krug-private"} <= set(c.pages)
    assert c.documents_by_id["2-09"].page == "krug-ryabova"
    assert c.pages["gromov"].type == "social" and c.pages["call"].type == "call"
    # middle: None/отсутствует → ""
    assert all(isinstance(ch.middle, str) for ch in c.characters)
    assert c.warnings == []


def test_units_order_and_kinds():
    c = load_content(CONTENT)
    us = units(c)
    paths = [u.path for u in us]
    # число единиц — из content: поля формы и вопросы без полей (28.10: контрольные вопросы, 43 единицы)
    n_units = sum(len(q.fields) if q.fields else 1 for st in c.stages for q in st.questions)
    assert len(us) == n_units
    assert len(set(paths)) == len(paths)
    # PLAN C7: поля формы — по порядку, вопросы — по порядку
    assert paths[:5] == ["s1.q1.time", "s1.q1.conflict", "s1.q1.disease", "s1.q1.delivered", "s1.q2"]
    by = {u.path: u for u in us}
    assert by["s1.q1.time"].type == "time" and by["s1.q1.time"].kind == "mandatory"
    assert by["s1.q1.time"].field is not None and by["s1.q1.time"].question.id == "q1"
    assert by["s1.q2"].field is None and by["s1.q2"].type == "order"
    assert by["s1.b1"].leak_scan is False  # leak_scan: false на вопросе
    assert by["s3.b1"].leak_scan is True and by["s3.b1"].field is None
    assert {u.stage for u in us if u.kind == "final"} == {4}
    # у каждого этапа, кроме последнего, есть обязательные; у последнего (30.10: контрольные s4.q1, s4.q2 сняты) — сразу финал
    assert {u.stage for u in us if u.kind == "mandatory"} == {st.n for st in c.stages if st.n != c.last_stage}


def test_render_all_content_strings():
    """Все строки контента рендерятся без ошибок StrictUndefined."""
    c = load_content(CONTENT)
    ctx = make_context(c)
    ctx["link"] = make_link(set(c.pages))  # link('slug'): существование страницы; ключей закрытых здесь нет
    n = 0
    for fname, data in c.raw.items():
        if fname.endswith("world.yaml"):
            continue
        out = render_tree(data, ctx, fname)
        assert "{{" not in str(out)
        n += 1
    for path, doc in c.docs.items():
        render_tree(doc.meta_raw, ctx, path)
        assert "{{" not in render(doc.body, ctx, path)
    for path, text in c.texts.items():
        render(text, ctx, path)
    brands = 1 if (CONTENT / "pages" / "_brands.yaml").is_file() else 0  # тексты подвала сервисов
    assert n == 7 + len(c.pages) + len(c.chats) + brands  # файлы YAML без world.yaml (с lab.yaml) + страницы + переписки
    # пример: шаблон с персонажем и миром
    z = next(ch for ch in c.characters if ch.id == "zavyalov")
    assert render("{{ c.zavyalov.short() }}, {{ w.theater.short }}", ctx) == f"{z.last}\xa0{z.first[0]}.\xa0{z.middle[0]}., ВОДТ"


def test_missing_body_is_todo_not_error(root):
    # тексты заполнены 20.10.2026 — удаляем их в копии content
    (root / "pages" / "news" / "article.md").unlink()
    (root / "pages" / "cloud" / "if_you_read_this.md").unlink()
    c = load_content(root)
    missing = {(t.file, t.loc) for t in c.missing}
    assert ("content/pages/news/page.yaml", "article.body") in missing
    assert ("content/pages/cloud/page.yaml", "folders[2].body") in missing


def test_collect_todos(root):
    # заглушки-значения в боевом content закрываются — подкладываем их в копию
    edit_text(root, "pages/video/page.yaml", 'size: "1,4 МБ"', 'size: "TODO(content): размер"')
    with (root / "pages" / "video" / "page.yaml").open("a", encoding="utf-8") as f:
        f.write("\n# TODO(content): комментарий-заглушка\n")
    c = load_content(root)
    todos = collect_todos(c)
    kinds = {t.kind for t in todos}
    assert {"value", "comment"} <= kinds  # «text» и «missing-file» — в test_missing_body_is_todo_not_error
    assert any(t.file == "content/pages/video/page.yaml" and t.loc == "file.size" and t.kind == "value" for t in todos)
    assert not any(t.file == "content/settings.yaml" and "домен" in t.text for t in todos)  # домен задан 20.10
    for t in todos:
        assert t.file.startswith("content/") and t.loc


# ---------------------------------------------------------------- испорченные копии


def test_missing_hint(root):
    def fn(d):
        si, qi = q_index(d, 1, "q1")
        d["stages"][si]["questions"][qi]["hints"].pop()

    edit_yaml(root, "stages.yaml", fn)
    assert_error(root, "content/stages.yaml: stages[0].questions[0].hints:", "ровно 3 подсказки", "сейчас 2")


def test_bonus_with_hints(root):
    def fn(d):
        si, qi = q_index(d, 2, "b1")
        d["stages"][si]["questions"][qi]["hints"] = ["лишняя"]

    loc = q_loc(root, 2, "b1")
    edit_yaml(root, "stages.yaml", fn)
    assert_error(root, f"{loc}.hints", "kind: bonus подсказок быть не должно")


def test_wrong_answer_option_id(root):
    def fn(d):
        si, qi = q_index(d, 2, "b1")
        d["stages"][si]["questions"][qi]["answer"]["canon"] = "o9"

    loc = q_loc(root, 2, "b1")
    edit_yaml(root, "stages.yaml", fn)
    assert_error(root, f"content/stages.yaml: {loc}.answer.canon:", "варианта «o9» нет среди options")


def test_answer_id_not_lowercase(root):
    def fn(d):
        si, qi = q_index(d, 4, "f1")
        d["stages"][si]["questions"][qi]["answer"]["canon"] = "Volkov"

    loc = q_loc(root, 4, "f1")
    edit_yaml(root, "stages.yaml", fn)
    assert_error(root, f"{loc}.answer.canon", "ID ответа «Volkov»", "строчные")


def test_answer_person_unknown_and_document_unknown(root):
    def fn(d):
        si, qi = q_index(d, 4, "f2")
        d["stages"][si]["questions"][qi]["answer"]["canon"] = ["zavyalov", "nobody"]
        si, qi = q_index(d, 3, "q3")
        d["stages"][si]["questions"][qi]["fields"][1]["answer"]["canon"] = "9-99"

    f2, q3 = q_loc(root, 4, "f2"), q_loc(root, 3, "q3")
    edit_yaml(root, "stages.yaml", fn)
    errs = assert_error(root, f"{f2}.answer.canon[1]", "персонажа «nobody» нет")
    assert any(f"{q3}.fields[1].answer.canon" in e and "документа «9-99» нет" in e for e in errs)


def test_answer_person_not_in_pool(root):
    def fn(d):
        si, qi = q_index(d, 2, "q2")
        d["stages"][si]["questions"][qi]["answer"]["canon"].append("voroncov")

    edit_yaml(root, "stages.yaml", fn)
    assert_error(root, "stages[1].questions[1].answer.canon", "«voroncov» не входит в pool")


def test_duplicate_character_id(root):
    def fn(d):
        d["characters"][1]["id"] = d["characters"][0]["id"]

    edit_yaml(root, "characters.yaml", fn)
    assert_error(root, "content/characters.yaml: characters[1].id:", "дубликат ID «voroncov»", "characters[0]")


def test_duplicate_question_id(root):
    def fn(d):
        si, qi = q_index(d, 1, "b1")
        d["stages"][si]["questions"][qi]["id"] = "q2"

    loc = q_loc(root, 1, "b1")
    edit_yaml(root, "stages.yaml", fn)
    assert_error(root, f"{loc}.id", "дубликат ID «q2»")


def test_template_typo_character(root):
    edit_text(root, "stages.yaml", "{{ c.zavyalov.short() }}; астма", "{{ c.zavyalv.short() }}; астма")
    assert_error(root, "content/stages.yaml: stages[0].questions[0].hints[2]:", "ошибка шаблона",
                 "нет персонажа «zavyalv»")


def test_template_typo_world_and_syntax(root):
    # первый предмет описи, в названии которого есть ссылка на мир (ищем в данных, а не по номеру)
    objs = yaml.safe_load((root / "expertise.yaml").read_text(encoding="utf-8"))["objects"]
    idx, ref = next((i, o["title"]) for i, o in enumerate(objs) if "{{ w." in o["title"])
    key = ref[ref.index("{{ w.") + 5:ref.index(" }}", ref.index("{{ w."))]
    edit_text(root, "expertise.yaml", "{{ w." + key + " }}", "{{ w.typo_" + key.replace(".", "_") + " }}")
    edit_text(root, "finale.yaml", "{{ c.marina.g('Уехал', 'Уехала') }}", "{{ c.marina.g('Уехал', 'Уехала' }}")
    errs = assert_error(root, f"content/expertise.yaml: objects[{idx}].title", "нет ключа «w.typo_")
    assert any("content/finale.yaml: fates[2].text" in e and "синтаксис" in e for e in errs)


def test_template_bad_case_and_markdown(root):
    edit_text(root, "documents/4-10.md", "{{ w.places.bridge }}", "{{ c.voroncov.full('gn') }}")
    assert_error(root, "content/documents/4-10.md: текст", "неизвестный падеж 'gn'")


def test_order_missing_card(root):
    def fn(d):
        si, qi = q_index(d, 1, "q2")
        d["stages"][si]["questions"][qi]["answer"]["canon"].remove("r4")

    edit_yaml(root, "stages.yaml", fn)
    assert_error(root, "stages[0].questions[1].answer.canon", "в ответе нет карточек: r4")


def test_order_duplicate_card(root):
    def fn(d):
        si, qi = q_index(d, 1, "q2")
        canon = d["stages"][si]["questions"][qi]["answer"]["canon"]
        canon[-1] = canon[0]

    edit_yaml(root, "stages.yaml", fn)
    errs = assert_error(root, "stages[0].questions[1].answer.canon", "карточка «k3» указана в ответе 2 раз")
    assert any("нет карточек: r4" in e for e in errs)


def test_final_outside_last_stage(root):
    def fn(d):
        si, qi = q_index(d, 2, "b1")
        d["stages"][si]["questions"][qi]["kind"] = "final"

    loc = q_loc(root, 2, "b1")
    edit_yaml(root, "stages.yaml", fn)
    assert_error(root, f"{loc}.kind", "kind: final допустим только в последнем этапе (4)")


def test_mandatory_in_last_stage_allowed_with_hints(root):
    """28.10: обязательные вопросы бывают и в последнем этапе (финал открывается после них), правила те же:
    ровно 3 подсказки. С 30.10 в контенте их нет, поэтому вопрос добавляется копией обязательного s3.q1."""
    import copy

    def add(d):
        si, qi = q_index(d, 3, "q1")
        q = copy.deepcopy(d["stages"][si]["questions"][qi])
        q["id"] = "qx"
        last = next(i for i, st in enumerate(d["stages"]) if st["n"] == 4)
        d["stages"][last]["questions"].insert(0, q)

    edit_yaml(root, "stages.yaml", add)
    c = load_content(root)
    assert any(q.kind == "mandatory" for q in c.stage(c.last_stage).questions)

    def fn(d):
        si, qi = q_index(d, 4, "qx")
        d["stages"][si]["questions"][qi]["hints"].pop()

    loc = q_loc(root, 4, "qx")
    edit_yaml(root, "stages.yaml", fn)
    assert_error(root, f"{loc}.hints", "ровно 3 подсказки")


def test_form_without_fields(root):
    def fn(d):
        si, qi = q_index(d, 2, "q1")
        del d["stages"][si]["questions"][qi]["fields"]

    edit_yaml(root, "stages.yaml", fn)
    assert_error(root, "stages[1].questions[0].fields", "у вопроса type: form должны быть поля fields")


def station_video_index() -> int:
    """Позиция результата station-video в expertise.yaml (не зашиваем номер: список результатов растёт)."""
    d = yaml.safe_load((ROOT / "content" / "expertise.yaml").read_text(encoding="utf-8"))
    return find(d["results"], "station-video")


def test_params_answer_missing_param(root):
    def fn(d):
        ri = find(d["results"], "station-video")
        del d["results"][ri]["params_answer"]["window"]

    edit_yaml(root, "expertise.yaml", fn)
    assert_error(root, f"content/expertise.yaml: results[{station_video_index()}].params_answer:", "нет параметра «window»")


def test_params_answer_absent(root):
    def fn(d):
        ri = find(d["results"], "station-video")
        del d["results"][ri]["params_answer"]

    edit_yaml(root, "expertise.yaml", fn)
    assert_error(root, f"results[{station_video_index()}].params_answer", "нужен params_answer со всеми параметрами", "date, time, window")


def test_expertise_unknown_refs(root):
    pos: dict[str, int] = {}  # индексы новых элементов — сразу после существующих (длины списков растут вместе с контентом)

    def fn(d):
        d["results"][0]["object"] = "ghost"
        pos["basis"] = len(d["results"][1]["bases"])
        d["results"][1]["bases"].append("8-88")
        pos["type"] = len(d["results"][2]["types"])
        d["results"][2]["types"].append("xray")

    edit_yaml(root, "expertise.yaml", fn)
    errs = assert_error(root, "results[0].object", "объекта «ghost» нет")
    assert any(f"results[1].bases[{pos['basis']}]" in e and "«8-88» нет" in e for e in errs)
    assert any(f"results[2].types[{pos['type']}]" in e and "«xray» нет" in e for e in errs)


def test_page_unknown_document(root):
    edit_text(root, "pages/call/page.yaml", 'doc: "1-05"', 'doc: "9-99"')
    assert_error(root, "content/pages/call/page.yaml: doc:", "документа «9-99» нет в documents.yaml")


def test_document_unknown_page(root):
    def fn(d):
        d["documents"][find(d["documents"], "1-05")]["page"] = "nopage"

    edit_yaml(root, "documents.yaml", fn)
    idx = find(yaml.safe_load((root / "documents.yaml").read_text(encoding="utf-8"))["documents"], "1-05")
    errs = assert_error(root, f"content/documents.yaml: documents[{idx}].page", "страницы «nopage» нет")
    assert any("pages/call/page.yaml: doc" in e and "ссылается на страницу «nopage»" in e for e in errs)


def test_extra_field(root):
    edit_text(root, "pages/video/page.yaml", 'resolution: "1920×1080"', 'resolution: "1920×1080"\n  fps: 30')
    assert_error(root, "content/pages/video/page.yaml: file.fps:", "лишнее поле")


def test_extra_field_question(root):
    def fn(d):
        si, qi = q_index(d, 3, "q1")
        d["stages"][si]["questions"][qi]["hint"] = "опечатка в имени поля"

    edit_yaml(root, "stages.yaml", fn)
    assert_error(root, "stages[2].questions[0].hint", "лишнее поле")


def test_wrong_type(root):
    edit_text(root, "pages/gromov/page.yaml", "likes: 47", 'likes: "много"')
    edit_text(root, "characters.yaml", "age: 61", 'age: "61"')
    errs = assert_error(root, "content/pages/gromov/page.yaml: posts[0].likes:", "ожидается целое число")
    assert any("content/characters.yaml: characters[1].age" in e and "ожидается целое число" in e for e in errs)


def test_wrong_literal_and_unquoted_date(root):
    edit_text(root, "characters.yaml", "gender: m", "gender: x")
    world = (root / "world.yaml").read_text(encoding="utf-8")
    premiere = re.search(r'premiere: "(\d{4}-\d{2}-\d{2})"', world).group(1)  # дата из контента, не литерал
    edit_text(root, "world.yaml", f'premiere: "{premiere}"', f"premiere: {premiere}")
    errs = assert_error(root, "content/characters.yaml: characters[0].gender", "допустимы")
    assert any("content/world.yaml: dates.premiere" in e and "в кавычки" in e for e in errs)


def test_duplicate_yaml_key(root):
    edit_text(root, "settings.yaml", "default_year: 2026", "default_year: 2026\ndefault_year: 2027")
    assert_error(root, "content/settings.yaml", "повторяющийся ключ «default_year»", "строка")


def test_front_matter_mismatch(root):
    edit_text(root, "documents/3-06.md", 'id: "3-06"', 'id: "3-07"')
    assert_error(root, "content/documents/3-06.md: front matter.id", "не совпадает с doc результата «3-06»")


def test_fate_unknown_character(root):
    edit_text(root, "finale.yaml", "who: oleg,", "who: olga,")
    assert_error(root, "content/finale.yaml: fates[7].who", "персонажа «olga» нет")


def test_errors_are_collected_together(root):
    def st(d):
        si, qi = q_index(d, 1, "q1")
        d["stages"][si]["questions"][qi]["hints"] = []

    edit_yaml(root, "stages.yaml", st)
    edit_text(root, "pages/call/page.yaml", 'doc: "1-05"', 'doc: "9-99"')
    errs = errors_of(root)
    assert any("stages.yaml" in e for e in errs) and any("call/page.yaml" in e for e in errs)


def test_content_error_message_format(root):
    edit_text(root, "pages/call/page.yaml", 'doc: "1-05"', 'doc: "9-99"')
    with pytest.raises(ContentError) as exc:
        load_content(root)
    text = str(exc.value)
    assert text.startswith("Ошибки в контенте (1):")
    assert "content/pages/call/page.yaml: doc: документа «9-99» нет в documents.yaml" in text


@pytest.mark.parametrize("domain", ["https://example.ru/", "https://example.ru/game", "http://example.ru",
                                    "example.ru", "https://example.ru?x=1"])
def test_domain_root_only(root, domain):
    edit_text(root, "settings.yaml", 'domain: "https://mydetgame.ru"', f'domain: "{domain}"')
    assert_error(root, "content/settings.yaml: domain:", f"domain {domain!r}")


def test_domain_with_port_ok(root):
    edit_text(root, "settings.yaml", 'domain: "https://mydetgame.ru"', 'domain: "https://example.ru:8443"')
    assert load_content(root).settings.domain == "https://example.ru:8443"


def test_cloud_chat_message_from_alias(root):
    """Ключ «from» в YAML читается через алиас поля from_ и проверяется по participants."""
    c = load_content(root)
    chat = next(f for f in c.pages["cloud"].folders if f.kind == "chat")
    senders = [m.from_ for m in chat.messages]
    assert senders[0] == "voroncov" and set(senders) == {"voroncov", "zavyalov"}


def test_cloud_chat_message_errors(root):
    edit_text(root, "pages/cloud/page.yaml", "    messages:\n",
              '    messages:\n'
              '      - { from: gromov, datetime: "2026-09-01T10:00", text: "Чужой" }\n'
              '      - { from_: zavyalov, datetime: "2026-09-01T10:00", text: "Имя поля Python" }\n')
    errs = assert_error(root, "content/pages/cloud/page.yaml: folders[1].messages[1].from:",
                        "обязательное поле отсутствует")
    assert any("folders[1].messages[1].from_" in e and "лишнее поле" in e for e in errs)


def test_cloud_chat_message_sender_not_participant(root):
    edit_text(root, "pages/cloud/page.yaml", "    messages:\n",
              '    messages:\n      - { from: gromov, datetime: "2026-09-01T10:00", text: "Чужой" }\n')
    assert_error(root, "folders[1].messages[0].from", "«gromov» не входит в participants")


def test_media_extension_and_path(root):
    edit_text(root, "pages/call/page.yaml", '"audio/anonymous_call.mp3"', '"audio/anonymous_call.wav"')
    edit_text(root, "characters.yaml", '"portraits/zavyalov.jpg"', '"../portraits/zavyalov.jpg"')
    errs = assert_error(root, "content/pages/call/page.yaml: audio:", "расширение «.wav»")
    assert any("characters[1].photo" in e and "без «..»" in e for e in errs)


def test_missing_media_is_not_error():
    # media/ в репозитории нет совсем (PLAN A2) — загрузка всё равно проходит
    c = load_content(CONTENT)
    from engine.content import media_refs

    refs = media_refs(c.characters, c.pages, c.docs)
    assert {r.context for r in refs} == {"portrait", "open", "locked"}
    assert any(r.path == "lab/station_cam.jpg" and r.context == "locked" for r in refs)


# ---------------------------------------------------------------- father: фамилия и отчество от отца


def test_father_current_content_consistent():
    c = load_content(CONTENT)
    by_id = c.characters_by_id
    kids = [ch for ch in c.characters if ch.father]
    assert kids, "в characters.yaml нет персонажей с father"
    for ch in kids:
        assert by_id[ch.father].gender == "m"


def test_father_wrong_patronymic_and_surname(root):
    # ожидаемые формы берём из текущего content (имена меняет import-cast)
    marina = next(c for c in load_content(root).characters if c.id == "marina")
    exp_mid, exp_last = marina.middle, marina.last

    def fn(d):
        i = find(d["characters"], "marina")
        d["characters"][i]["middle"] = "Петровна"
        d["characters"][i]["last"] = "Иванов"
    edit_yaml(root, "characters.yaml", fn)
    errs = assert_error(root, "content/characters.yaml: characters[", "].middle:", "указано «Петровна»",
                        f"ожидается «{exp_mid}»", "forms.middle.nom")
    assert any("].last:" in e and f"ожидается «{exp_last}»" in e for e in errs)


def test_father_follows_renamed_father(root):
    # отца переименовали — у дочерей отчество и фамилия устарели
    def fn(d):
        i = find(d["characters"], "kirill")
        d["characters"][i]["first"] = "Пётр"
        d["characters"][i]["last"] = "Достоевский"
    edit_yaml(root, "characters.yaml", fn)
    errs = assert_error(root, "].middle:", "ожидается «Петровна»", "«kirill»")
    assert any("].last:" in e and "ожидается «Достоевская»" in e for e in errs)


def test_father_manual_nom_form_wins(root):
    def fn(d):
        i = find(d["characters"], "kirill")
        d["characters"][i]["first"] = "Шота"
        for kid in ("marina", "marina_sister"):
            k = find(d["characters"], kid)
            d["characters"][k]["middle"] = "Шотаевна"
            d["characters"][k]["forms"] = {"middle": {"nom": "Шотаевна"}}
    edit_yaml(root, "characters.yaml", fn)
    load_content(root)


def test_father_underivable_name(root):
    edit_yaml(root, "characters.yaml",
              lambda d: d["characters"][find(d["characters"], "kirill")].update(first="Шота"))
    assert_error(root, "].middle:", "не удалось вывести отчество от имени «Шота»", "укажите отчество вручную в forms")


def test_father_todo_is_skipped(root):
    edit_yaml(root, "characters.yaml",
              lambda d: d["characters"][find(d["characters"], "kirill")].update(first="TODO(content)",
                                                                               last="TODO(content)"))
    load_content(root)


@pytest.mark.parametrize(("father", "msg"), [
    ("nobody", "нет персонажа «nobody»"),
    ("marina", "указан отцом самого себя"),
    ("volskaya", "должен быть мужского пола"),
])
def test_father_bad_reference(root, father, msg):
    edit_yaml(root, "characters.yaml",
              lambda d: d["characters"][find(d["characters"], "marina")].update(father=father))
    assert_error(root, "content/characters.yaml: characters[", "].father:", msg)


def test_familiar_and_cast_schema(root):
    def fn(d):
        d["characters"][find(d["characters"], "voroncov")]["familiar"] = ""
        d["characters"][find(d["characters"], "kovalev")]["cast"] = "нет"
    edit_yaml(root, "characters.yaml", fn)
    errs = assert_error(root, "].familiar:", "пустая строка")
    assert any("].cast:" in e and "ожидается true или false" in e for e in errs)
