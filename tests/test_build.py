"""Сборка dist/, check, leak scan, медиа, --release, dump-answers. Всё — во временных папках."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from engine import ROOT, crypto
from engine.answers import expand_all, order_shuffle
from engine.build import BuildError, build, prepare
from engine.check import check, leak_needles
from engine.content import ContentError, load_content
from engine.dump import answers_data, dump_answers
from engine.build import strip_css_comments
from engine.leakscan import is_stop_shingle, scan, scan_text, text_shingles
from engine.media import media_hash
from engine import util

CONTENT = ROOT / "content"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("b")
    salts = tmp / "salts.lock.json"
    dist = tmp / "dist"
    rep = build(dist=dist, salts_path=salts)
    return tmp, dist, salts, rep


def test_dist_layout(built):
    _, dist, _, rep = built
    for rel in ["data/public.json", "data/pack-1.json", "data/pack-4.json", "data/finale.json", "index.html",
                "lab/index.html", "final/index.html", "robots.txt", "assets/js/boot.js", "assets/css/fonts.css",
                "p/call/index.html", "p/inna/payload.json", "p/cloud/payload.json"]:
        assert (dist / rel).is_file(), rel
    assert not (dist / "p" / "news" / "payload.json").exists()
    assert (dist / "robots.txt").read_text(encoding="utf-8") == "User-agent: *\nDisallow: /\n"
    headers = (dist / "_headers").read_text(encoding="utf-8")
    blocks = {b.splitlines()[0]: b for b in headers.split("\n\n") if b.strip() and not b.startswith("#")}
    assert "no-cache" in blocks["/data/*"] and "immutable" in blocks["/m/*"] and "immutable" in blocks["/assets/fonts/*"]
    assert "Cache-Control" not in blocks["/*"] and "noindex" in blocks["/*"]
    # Apache (REG.RU): корневой .htaccess — no-cache и noindex, в папках неизменяемых файлов — immutable
    root_ht = (dist / ".htaccess").read_text(encoding="utf-8")
    assert 'Cache-Control "no-cache"' in root_ht and "noindex, nofollow" in root_ht and "Options -Indexes" in root_ht
    assert "AddType font/woff2 .woff2" in root_ht and "AddType application/json .json" in root_ht
    for d in ("assets/fonts", "m"):
        if (dist / d).is_dir():
            assert "immutable" in (dist / d / ".htaccess").read_text(encoding="utf-8"), d
    for p in dist.rglob("*.html"):
        assert '<meta name="robots" content="noindex, nofollow">' in p.read_text(encoding="utf-8"), p
    pub = json.loads((dist / "data/public.json").read_text(encoding="utf-8"))
    assert list(pub)[:3] == ["v", "gameId", "title"] and pub["stages"] == 4
    assert pub["buildId"].endswith(pub["buildId"][-8:]) and len(pub["buildId"].split("-")[1]) == 8
    pack = json.loads((dist / "data/pack-2.json").read_text(encoding="utf-8"))
    assert set(pack) == {"v", "alg", "aad", "n", "c"} and pack["aad"] == "pack/2"
    shell = (dist / "p/inna/index.html").read_text(encoding="utf-8")
    assert 'data-slug="inna"' in shell and 'data-access="key"' in shell
    assert set(rep.page_keys) == {"inna", "pharma", "video"}


def test_check_passes_on_current_content(built):
    _, dist, salts, _ = built
    rep = check(dist=dist, salts_path=salts)
    assert rep.ok, rep.table()
    assert [r.name.split(".")[0] for r in rep.rows] == [str(i) for i in range(1, 11)]
    # имена буквами в тексте без --release — предупреждение, не ошибка
    # предупреждения — только «Имена буквами» (тексты и похожие дружеские имена, S-62)
    assert all(w.startswith("[10. Имена буквами]") for w in rep.warnings)
    assert len(rep.warnings) >= len(rep.name_hits)
    assert "Размер dist/" in rep.table()


def test_rebuild_keeps_keys(built, tmp_path):
    _, _, salts, rep1 = built
    before = salts.read_bytes()
    rep2 = build(dist=tmp_path / "dist2", salts_path=salts)
    assert rep2.stage_keys == rep1.stage_keys
    assert rep2.page_keys == rep1.page_keys
    assert salts.read_bytes() == before


def test_pack_contents(built):
    tmp, dist, salts, rep = built
    prep = prepare(CONTENT, salts, create_salts=False)
    k1 = crypto.b64u_decode(rep.stage_keys[1])
    pk = json.loads(crypto.open_(crypto.hkdf(k1, crypto.pack_info(1)),
                                 json.loads((dist / "data/pack-1.json").read_text(encoding="utf-8")), "pack/1"))
    assert pk["n"] == 1 and pk["onComplete"] and pk["saltStage"]
    q1 = pk["questions"][0]
    assert q1["type"] == "form" and [f["id"] for f in q1["fields"]] == ["time", "conflict", "disease", "delivered"]
    assert all(len(f["unit"]["entries"]) >= 8 for f in q1["fields"])
    assert "lab" not in {d["kind"] for d in pk["documents"]}
    online = [d for d in pk["documents"] if d["kind"] == "online"]
    assert online and all(d["link"] == f"/p/{d['link'].split('/')[2]}/" for d in online)
    assert all(d["link"] is None for d in pk["documents"] if d["kind"] == "paper")
    assert pk["lab"]["types"] and "role" not in next(iter(pk["characters"].values()))
    order = pk["questions"][1]
    answer = prep.expanded["s1.q2"].canon.split(",")
    assert [i["id"] for i in order["items"]] != answer and sorted(i["id"] for i in order["items"]) == sorted(answer)


def test_order_shuffle_deterministic():
    ids = ["a", "b", "c", "d"]
    salt = b"\x01" * 16
    assert order_shuffle(ids, ids, salt) == order_shuffle(ids, ids, salt) != ids
    assert order_shuffle(["a", "b"], ["a", "b"], b"\x00" * 16) == ["b", "a"]


def test_time_tolerance_expansion(built):
    _, _, salts, _ = built
    prep = prepare(CONTENT, salts, create_salts=False)
    assert prep.expanded["s2.q1.left"].variants == ["19:33", "19:34", "19:35", "19:36", "19:37"]
    params, combos = prep.params["station-video"]
    assert params["date"].variants == ["2026-10-30"] and len(combos) == 15


def test_util_b64u_is_crypto():
    assert util.b64u_encode(b"\xff\xfe") == crypto.b64u_encode(b"\xff\xfe") == "__4"
    with pytest.raises(ValueError):
        util.b64u_decode("a=")


# ---------------------------------------------------------------- leak scan


def test_shingle_rules():
    sh = text_shingles("TODO(content): полный текст документа. Обязательно: что-то ещё")
    assert "полный текст документа обязательно" in sh
    assert not any("todo" in x for x in sh)  # маркер разрывает текст
    assert text_shingles("Короткий текст") == set()
    assert is_stop_shingle("так же как в") and not is_stop_shingle("так же как пропранолол")
    assert is_stop_shingle("здесь будет фото профиля")


def test_strip_css_comments():
    css = '/* макет: Пропранолол */a{b:url(data:x/*y*/z)}/*! OFL */c{content:"/* keep */";d:url(\'a/*b\')}'
    out = strip_css_comments(css)
    assert "Пропранолол" not in out and "/*! OFL */" in out
    assert 'url(data:x/*y*/z)' in out and '"/* keep */"' in out and "url('a/*b')" in out


def test_leak_scan_catches_planted(built, tmp_path):
    _, dist, salts, _ = built
    leaky = tmp_path / "dist"
    shutil.copytree(dist, leaky)
    (leaky / "leak-raw.html").write_text("<p>Вещество: Пропранолол.</p>", encoding="utf-8")
    (leaky / "leak-u.json").write_text('{"x": "\\u0430\\u0441\\u0442\\u043c\\u0430"}', encoding="utf-8")
    (leaky / "leak-base.js").write_text('const t = "БРОНХИАЛЬНАЯ — астма!";', encoding="utf-8")
    (leaky / "leak-time.txt").write_text("ушёл в 19.35", encoding="utf-8")
    # поля n/c контейнеров и *.bin — не ищутся
    (leaky / "ok.json").write_text('{"v":1,"alg":"A256GCM","aad":"x","n":"астма","c":"астма"}', encoding="utf-8")
    (leaky / "m").mkdir(exist_ok=True)
    (leaky / "m" / "x.bin").write_text("астма", encoding="utf-8")
    rep = check(dist=leaky, salts_path=salts)
    assert not rep.ok
    row = next(r for r in rep.rows if r.name.startswith("7."))
    assert not row.ok
    files = {p.split(":")[0].split("] ")[1] for p in rep.problems if p.startswith("[7.")}
    assert {"leak-raw.html", "leak-u.json", "leak-base.js", "leak-time.txt"} <= files
    assert "ok.json" not in files and "m/x.bin" not in files


def test_leak_scan_whole_words_only(built):
    _, _, salts, _ = built
    prep = prepare(CONTENT, salts, create_salts=False)
    ns = leak_needles(prep)
    assert scan_text("астматический", ns, "f") == []  # не целое слово
    assert scan_text("Астма", ns, "f")
    assert any(n.kind == "watchlist" for n in ns.needles) and ns.shingles


def test_leak_scan_watchlist_and_hint(built, tmp_path):
    _, _, salts, _ = built
    prep = prepare(CONTENT, salts, create_salts=False)
    ns = leak_needles(prep)
    (tmp_path / "a.html").write_text("ООО «Сценическая  мастерская»", encoding="utf-8")
    (tmp_path / "b.html").write_text("Все четыре ответа есть в документах папки, начните с карты", encoding="utf-8")
    # середина подсказки этапа 3 (не начало) — шинглы по всему тексту
    (tmp_path / "c.md").write_text("Ингалятор и успокоительное у погибшего были свои", encoding="utf-8")
    (tmp_path / "пропранолол.txt").write_text("x", encoding="utf-8")  # имя файла
    (tmp_path / "ok.html").write_text("Так же как в прошлый раз", encoding="utf-8")
    found = {f.file for f in scan(tmp_path, ns)}
    assert found == {"a.html", "b.html", "c.md", "<имена файлов>"}


# ---------------------------------------------------------------- страницы, медиа, release


def _content_copy(tmp_path: Path) -> Path:
    dst = tmp_path / "content"
    shutil.copytree(CONTENT, dst)
    return dst


def test_forbidden_word_on_page(tmp_path):
    cdir = _content_copy(tmp_path)
    p = cdir / "pages/news/page.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace('"21:18"]', '"21:18", "скончался"]'), encoding="utf-8")
    salts = tmp_path / "salts.json"
    build(content_dir=cdir, dist=tmp_path / "dist", salts_path=salts)
    rep = check(content_dir=cdir, dist=tmp_path / "dist", salts_path=salts)
    assert any("news" in p and "скончался" in p and "forbidden" in p for p in rep.problems)
    assert not next(r for r in rep.rows if r.name.startswith("5.")).ok


def test_media_open_and_encrypted(tmp_path):
    media = tmp_path / "media"
    for rel, data in [("lab/station_cam.jpg", b"STATION"), ("gromov/meeting.jpg", b"MEETING"),
                      ("portraits/kirill.jpg", b"KIRILL"), ("video/rehearsal.mp4", b"VIDEO")]:
        (media / rel).parent.mkdir(parents=True, exist_ok=True)
        (media / rel).write_bytes(data)
    salts = tmp_path / "salts.json"
    dist = tmp_path / "dist"
    rep = build(media_dir=media, dist=dist, salts_path=salts)
    assert "lab/station_cam.jpg" not in rep.missing_media
    names = {p.name for p in (dist / "m").iterdir()}
    assert f"{media_hash(b'MEETING')}.jpg" in names  # открытая страница
    assert f"{media_hash(b'KIRILL')}.jpg" in names  # портрет — открытый
    assert f"{media_hash(b'STATION')}.bin" in names  # только экспертиза — зашифрован
    assert f"{media_hash(b'VIDEO')}.bin" in names  # закрытая страница
    gromov = (dist / "p/gromov/index.html").read_text(encoding="utf-8")
    assert f'src="/m/{media_hash(b"MEETING")}.jpg"' in gromov
    # зашифрованное видео: ключ в payload, файл открывается
    inner = json.loads(crypto.open_(crypto.b64u_decode(rep.page_keys["video"]),
                                    json.loads((dist / "p/video/payload.json").read_text(encoding="utf-8")),
                                    "page/video"))
    ref = inner["media"][0]
    assert 'data-media="0"' in inner["html"] and ref["mime"] == "video/mp4"
    blob = (dist / ref["src"].lstrip("/")).read_bytes()
    assert crypto.open_media(crypto.b64u_decode(ref["key"]), blob, ref["aad"]) == b"VIDEO"
    assert check(media_dir=media, dist=dist, salts_path=salts).ok
    # подложить открытую копию зашифрованного файла → check падает
    (dist / "m" / f"{media_hash(b'STATION')}.jpg").write_bytes(b"STATION")
    rep2 = check(media_dir=media, dist=dist, salts_path=salts)
    assert any("лежит открытым" in p for p in rep2.problems)


def test_release_fails_with_todos(built, tmp_path):
    _, dist, salts, _ = built
    with pytest.raises(BuildError) as exc:
        build(dist=tmp_path / "dist", salts_path=salts, release=True)
    text = str(exc.value)
    assert "TODO(content)" in text and "комментарий" in text
    # пароль облака задан в content (14.10.2026) — проверка «пароль облака не задан» здесь больше не срабатывает
    # домен задан в content (20.10.2026: mydetgame.ru) — «домен-заглушка» здесь больше не срабатывает
    assert "нет медиафайла" in text and "домен-заглушка" not in text
    assert not (tmp_path / "dist").exists()
    rep = check(dist=dist, salts_path=salts, release=True)
    assert not next(r for r in rep.rows if r.name.startswith("8.")).ok


def test_check_without_salts_file(built, tmp_path):
    _, dist, _, _ = built
    with pytest.raises(BuildError, match="нет файла солей"):
        check(dist=dist, salts_path=tmp_path / "none.json")
    assert not (tmp_path / "none.json").exists()


# ---------------------------------------------------------------- валидация для сборки


def test_stage_without_mandatory(tmp_path):
    cdir = _content_copy(tmp_path)
    p = cdir / "stages.yaml"
    s = p.read_text(encoding="utf-8")
    s = s.replace("      - id: q2\n        kind: mandatory\n        type: persons",
                  "      - id: q2\n        kind: bonus\n        type: persons")
    s = s.replace("""      - id: q1
        kind: mandatory
        type: form
        prompt: "Восстановите""", """      - id: q1
        kind: bonus
        type: form
        prompt: "Восстановите""")
    p.write_text(s, encoding="utf-8")
    with pytest.raises(ContentError) as exc:
        load_content(cdir)
    assert any("stages[1].questions" in str(e) and "хотя бы один обязательный" in str(e) for e in exc.value.errors)


def test_bad_canon_normalization(tmp_path):
    cdir = _content_copy(tmp_path)
    p = cdir / "stages.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace('canon: "21:18"', 'canon: "25:99"'), encoding="utf-8")
    c = load_content(cdir)
    with pytest.raises(ContentError) as exc:
        expand_all(c)
    assert "content/stages.yaml: stages[0].questions[0].fields[0].answer: канон '25:99' не проходит" in str(exc.value)


# ---------------------------------------------------------------- dump-answers


def test_dump_answers_structure(built, tmp_path):
    _, _, salts, rep = built
    out = dump_answers(salts_path=salts, out=tmp_path / ".answers.json")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["v"] == 1 and data["gameId"] == "zakulisami"
    assert [s["n"] for s in data["stages"]] == [1, 2, 3, 4]
    q1 = data["stages"][0]["questions"][0]
    assert q1["type"] == "form" and q1["fields"][0] == {
        **q1["fields"][0], "path": "s1.q1.time", "id": "time", "type": "time", "input": "21:18", "canon": "21:18"}
    for st in data["stages"]:
        for q in st["questions"]:
            for u in q.get("fields", [q]):
                assert len(u["wrong"]) == 5 and u["canon"] in u["variants"]
    assert data["stages"][0]["questions"][1]["input"] == ["k3", "p8", "d1", "x5", "m2", "t7", "b9", "r4"]
    assert data["finalOrder"] == ["s4.f1", "s4.f2", "s4.f3", "s4.f4", "s4.f5", "s4.fb", "s4.fb2"]
    sv = next(x for x in data["lab"] if x["result"] == "station-video")
    assert sv["params"]["time"]["input"] == "14:37" and len(sv["params"]["time"]["variants"]) == 15
    assert sv["wrongBasis"] and sv["wrongBasis"] not in sv["bases"]
    pages = {p["slug"]: p for p in data["pages"]}
    assert pages["inna"]["key"] == rep.page_keys["inna"] and pages["inna"]["url"].endswith("#k=" + rep.page_keys["inna"])
    assert pages["cloud"]["access"] == "password" and "password" in pages["cloud"]
    assert pages["call"] == {"slug": "call", "access": "open", "url": "/p/call/"}
    assert data["expected"] == {"maxScore": 255, "perfectRunScore": 255}


def test_answers_data_matches_settings(built):
    _, _, salts, _ = built
    data = answers_data(prepare(CONTENT, salts, create_salts=False))
    assert data["settings"]["hints"] == {"cost": [10, 20, 40], "autoAfterWrong": 3}
