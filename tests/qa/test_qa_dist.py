"""QA: независимая проверка собранного dist/ (P02/P03) — без engine/leakscan.py и без engine.crypto.

Сборка — во временной папке из копии content/, site/, media/ и salts.lock.json, с уменьшенными
итерациями PBKDF2 (схема ключей от числа итераций не зависит). Проверяется:

- проход всех этапов независимой реализацией docs/02 §3 (Python, только ``cryptography``) и JS-кодом
  сайта (tests/qa/walk_dist.mjs); ключи этапов совпадают;
- finale.json — только K_4; закрытые страницы — только своим ключом; облако — паролем; AAD связан;
- независимый leak scan: фрагменты из 4 токенов ``base()`` всех расшифрованных текстов этапов 2–4,
  подсказок, экспертиз, развязки, закрытых страниц + ответы и варианты — в открытых файлах (сырой
  вид, ``\\uXXXX``, HTML-сущности, ключи JSON, имена файлов);
- pack-1 (ключ публичный): ни текстов этапов 2–4, ни персонажей вне пулов, ни лишних полей (PLAN B3);
- public.json — только поля docs/02 §3.5;
- детерминированность: пересборка — те же ключи, тот же порядок карточек, соли не меняются;
- мутации dist/: ``python -m engine check`` должен падать. Найденные пробелы check — ``xfail(strict)``.
"""

from __future__ import annotations

import base64
import html
import itertools
import json
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from engine import ROOT
from engine.build import build, prepare
from engine.check import check
from engine.content import units
from engine.dump import answers_data
from engine.normalize import normalize

NODE = shutil.which("node")
FAST_ITER = 1000
PUBLIC_FIELDS = {"v", "gameId", "title", "stages", "saltStart", "iter", "entriesPad", "points", "penalties", "hints",
                 "ranks", "defaultYear", "saltsId", "buildId"}


# ----------------------------------------------------------------------------- независимая криптография


def b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def pbkdf2(pw: bytes, salt: bytes, it: int) -> bytes:
    return PBKDF2HMAC(hashes.SHA256(), 32, salt, it).derive(pw)


def hkdf(ikm: bytes, info: bytes) -> bytes:
    return HKDF(hashes.SHA256(), 32, bytes(32), info).derive(ikm)


def open_box(key: bytes, box: dict, aad: str | None = None) -> bytes | None:
    """AAD берётся из аргумента (не из контейнера), если он передан: так проверяется связка AAD."""
    try:
        return AESGCM(key).decrypt(b64d(box["n"]), b64d(box["c"]), (aad if aad is not None else box["aad"]).encode())
    except InvalidTag:
        return None


def open_json(key: bytes, box: dict, aad: str | None = None):
    pt = open_box(key, box, aad)
    return None if pt is None else json.loads(pt.decode("utf-8"))


def try_entries(key: bytes, entries: list[dict], aad: str) -> bytes | None:
    for e in entries:
        if e.get("aad") != aad:
            continue
        pt = open_box(key, e, aad)
        if pt is not None:
            return pt
    return None


def answer_key(path: str, x: str, salt: bytes, it: int) -> bytes:
    return pbkdf2(f"detgame/answer/v1|{path}|{x}".encode(), salt, it)


def stage_secret(n: int, pairs) -> str:
    return f"detgame/stage/v1|{n}\x1f" + "\x1f".join(f"{p}={c}" for p, c in pairs)


def lab_info(obj: str, typ: str, basis: str, params) -> bytes:
    return f"detgame/lab/v1|{obj}|{typ}|{basis}|{'|'.join(params)}".encode()


def base(s: str) -> str:
    """Своя реализация base() (docs/02 §2) — для поиска утечек."""
    s = unicodedata.normalize("NFC", s).lower().replace("ё", "е")
    out = []
    for ch in s:
        cat = unicodedata.category(ch)[0]
        out.append(ch if cat in "LN" else ("" if cat == "M" else " "))
    return " ".join("".join(out).split())


# ----------------------------------------------------------------------------- сборка во временной папке


def _make_root(tmp: Path, *, fast: bool = True) -> Path:
    for d in ("content", "site", "media"):
        shutil.copytree(ROOT / d, tmp / d, ignore=shutil.ignore_patterns("__pycache__"))
    (tmp / "engine").mkdir()
    shutil.copy(ROOT / "engine" / "salts.lock.json", tmp / "engine" / "salts.lock.json")
    if fast:
        p = tmp / "content" / "settings.yaml"
        s = p.read_text(encoding="utf-8")
        s = re.sub(r"iter_answer:\s*\d+", f"iter_answer: {FAST_ITER}", s)
        s = re.sub(r"iter_stage:\s*\d+", f"iter_stage: {FAST_ITER}", s)
        p.write_text(s, encoding="utf-8")
    return tmp


def _build(root: Path, dist: Path | None = None):
    return build(root, dist=dist or root / "dist", salts_path=root / "engine" / "salts.lock.json", log=lambda *a: None)


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    root = _make_root(tmp_path_factory.mktemp("qa"))
    rep = _build(root)
    prep = prepare(root / "content", root / "engine" / "salts.lock.json", create_salts=False)
    answers = answers_data(prep)
    (root / "answers.json").write_text(json.dumps(answers, ensure_ascii=False), encoding="utf-8")
    walk = _walk(root / "dist", answers)
    return {"root": root, "dist": root / "dist", "rep": rep, "prep": prep, "A": answers, "walk": walk}


def _load(dist: Path, rel: str):
    return json.loads((dist / rel).read_text(encoding="utf-8"))


def _units_by_path(A: dict) -> dict:
    out = {}
    for st in A["stages"]:
        for q in st["questions"]:
            for u in q.get("fields", [q]):
                out[u["path"]] = dict(u, type=u.get("type", q["type"]), kind=q["kind"])
    return out


def _walk(dist: Path, A: dict) -> dict:
    """Проход как в браузере (FORMATS §2.4): пары — по порядку вопросов пакета, тип — из пакета."""
    pub = _load(dist, "data/public.json")
    ia, is_ = pub["iter"]["answer"], pub["iter"]["stage"]
    ub = _units_by_path(A)
    fails: list[str] = []
    keys = {1: pbkdf2(b"detgame/stage/v1|start", b64d(pub["saltStart"]), is_)}
    packs: dict[int, dict] = {}
    for n in range(1, pub["stages"] + 1):
        box = _load(dist, f"data/pack-{n}.json")
        for m, km in keys.items():
            if m != n and open_box(hkdf(km, f"detgame/pack/v1|{n}".encode()), box, f"pack/{n}") is not None:
                fails.append(f"pack-{n} открылся ключом K_{m}")
        pack = open_json(hkdf(keys[n], f"detgame/pack/v1|{n}".encode()), box, f"pack/{n}")
        if pack is None:
            fails.append(f"pack-{n} не открылся")
            break
        packs[n] = pack
        pairs = []
        for q in pack["questions"]:
            for f in q.get("fields", [q]):
                unit = f["unit"]
                path = unit["path"]
                a = ub[path]
                salt = b64d(unit["salt"])
                x = normalize(unit["type"], a["input"], default_year=pub["defaultYear"])
                pt = try_entries(answer_key(path, x, salt, ia), unit["entries"], "ans/" + path) if x else None
                got = json.loads(pt)["c"] if pt else None
                if got != a["canon"]:
                    fails.append(f"{path}: ввод {a['input']!r} → {got!r}")
                for v in a["variants"]:
                    pt = try_entries(answer_key(path, v, salt, ia), unit["entries"], "ans/" + path)
                    if pt is None or json.loads(pt)["c"] != a["canon"]:
                        fails.append(f"{path}: вариант {v!r} не принят")
                for w in a["wrong"]:
                    wv = normalize(unit["type"], w, default_year=pub["defaultYear"])
                    if wv and try_entries(answer_key(path, wv, salt, ia), unit["entries"], "ans/" + path):
                        fails.append(f"{path}: неверный {w!r} принят")
                if q["kind"] == "mandatory":
                    pairs.append((path, got))
        if n < pub["stages"]:
            keys[n + 1] = pbkdf2(stage_secret(n, pairs).encode(), b64d(pack["saltStage"]), is_)
    return {"keys": keys, "packs": packs, "fails": fails, "pub": pub}


# ----------------------------------------------------------------------------- проход и криптография


def test_independent_walk_opens_all_stages(env):
    w = env["walk"]
    assert not w["fails"], "\n".join(w["fails"])
    assert len(w["packs"]) == w["pub"]["stages"]
    assert {n: b64e(k) for n, k in w["keys"].items()} == env["rep"].stage_keys


def test_wrong_mandatory_answer_does_not_open_next_pack(env):
    w, dist, A = env["walk"], env["dist"], env["A"]
    ub = _units_by_path(A)
    pub = w["pub"]
    for n, pack in w["packs"].items():
        if n == pub["stages"]:
            continue
        pairs = [(f["unit"]["path"], ub[f["unit"]["path"]]["canon"]) for q in pack["questions"]
                 for f in q.get("fields", [q]) if q["kind"] == "mandatory"]
        nxt = _load(dist, f"data/pack-{n + 1}.json")
        for i, (path, _) in enumerate(pairs):
            wv = normalize(ub[path]["type"], ub[path]["wrong"][0], default_year=pub["defaultYear"])
            bad = list(pairs)
            bad[i] = (path, wv)
            kb = pbkdf2(stage_secret(n, bad).encode(), b64d(pack["saltStage"]), pub["iter"]["stage"])
            assert open_box(hkdf(kb, f"detgame/pack/v1|{n + 1}".encode()), nxt) is None, path
        # бонусы на ключ не влияют: с бонусами в секрете пакет не открывается
        extra = pairs + [(f["unit"]["path"], ub[f["unit"]["path"]]["canon"]) for q in pack["questions"]
                         for f in q.get("fields", [q]) if q["kind"] != "mandatory"]
        if len(extra) > len(pairs):
            kb = pbkdf2(stage_secret(n, extra).encode(), b64d(pack["saltStage"]), pub["iter"]["stage"])
            assert open_box(hkdf(kb, f"detgame/pack/v1|{n + 1}".encode()), nxt) is None


def test_pack_does_not_contain_next_stage_secret(env):
    """В pack-N нет K_{N+1}, соли следующего этапа и полей с канонами (кроме текстов подсказок)."""
    w = env["walk"]
    for n, pack in w["packs"].items():
        blob = json.dumps(pack, ensure_ascii=False)
        for m, k in w["keys"].items():
            if m > n:
                assert b64e(k) not in blob, f"K_{m} лежит в pack-{n}"
                assert k.hex() not in blob
        assert '"canon"' not in blob and '"answer"' not in blob and '"variants"' not in blob, f"pack-{n}"


def test_finale_only_with_k4(env):
    w, dist = env["walk"], env["dist"]
    box = _load(dist, "data/finale.json")
    last = w["pub"]["stages"]
    for m, k in w["keys"].items():
        assert (open_box(hkdf(k, b"detgame/finale/v1"), box, "finale") is not None) == (m == last), m
        for x in range(1, last + 1):
            assert open_box(hkdf(k, f"detgame/pack/v1|{x}".encode()), box, "finale") is None
    fin = open_json(hkdf(w["keys"][last], b"detgame/finale/v1"), box, "finale")
    assert set(fin["answers"]) == set(_units_by_path(env["A"]))


def test_locked_pages_only_own_key_cloud_by_password(env):
    dist, A, w = env["dist"], env["A"], env["walk"]
    keyed = [p for p in A["pages"] if p["access"] == "key"]
    for pg in A["pages"]:
        pdir = dist / "p" / pg["slug"]
        if pg["access"] == "open":
            assert not (pdir / "payload.json").exists()
            continue
        payload = _load(dist, f"p/{pg['slug']}/payload.json")
        if pg["access"] == "key":
            inner = open_json(b64d(pg["key"]), payload, f"page/{pg['slug']}")
            assert inner and inner["slug"] == pg["slug"]
            for o in keyed:
                if o["slug"] != pg["slug"]:
                    assert open_box(b64d(o["key"]), payload) is None
            for k in w["keys"].values():
                assert open_box(k, payload) is None
            assert open_box(b64d(pg["key"]), payload, "page/x") is None  # AAD связан
        else:
            pw = normalize("password", pg["password"])
            key = pbkdf2(f"detgame/cloud/v1|{pw}".encode(), b64d(payload["salt"]), payload["iter"])
            assert open_json(key, payload["box"], "page/cloud")["slug"] == "cloud"
            for bad in ("", pw + "1", pw[:-1], "password"):
                kb = pbkdf2(f"detgame/cloud/v1|{bad}".encode(), b64d(payload["salt"]), payload["iter"])
                assert open_box(kb, payload["box"]) is None
            assert payload["iter"] == w["pub"]["iter"]["stage"]


def test_aad_is_bound_for_swapped_containers(env):
    w, dist = env["walk"], env["dist"]
    k1 = hkdf(w["keys"][1], b"detgame/pack/v1|1")
    box1 = _load(dist, "data/pack-1.json")
    assert open_box(k1, {**box1, "aad": "pack/2"}) is None  # переписанное поле aad → тег не сходится
    assert open_box(k1, box1, "pack/2") is None
    # контейнер пакета 2 под именем пакета 1
    assert open_box(k1, _load(dist, "data/pack-2.json"), "pack/1") is None


def test_lab_entries(env):
    w, A = env["walk"], env["A"]
    for L in A["lab"]:
        pv = [p["variants"] for p in L["params"].values()]
        for t, b, p in itertools.product(L["types"], L["bases"], itertools.product(*pv)):
            info = lab_info(L["object"], t, b, p)
            pt = try_entries(hkdf(w["keys"][L["stage"]], info), w["packs"][L["stage"]]["lab"]["entries"], "lab")
            assert pt is not None, (L["result"], t, b, p)
            assert json.loads(pt)["doc"] == L["doc"]
            for m in range(1, L["stage"]):
                assert try_entries(hkdf(w["keys"][m], info), w["packs"][m]["lab"]["entries"], "lab") is None


def test_lab_no_foreign_basis_or_type_opens(env):
    """Исчерпывающе: любой документ, не входящий в основания, и любой вид вне types — не открывают запись."""
    w, A, prep = env["walk"], env["A"], env["prep"]
    doc_ids = [d.id for d in prep.content.documents]
    type_ids = [t.id for t in prep.content.expertise.types]
    by_obj: dict[str, list] = {}
    for L in A["lab"]:
        by_obj.setdefault(L["object"], []).append(L)
    for obj, results in by_obj.items():
        allowed = {(t, b) for L in results for t in L["types"] for b in L["bases"]}
        p0 = [p["variants"][0] for p in results[0]["params"].values()]
        for t, b in itertools.product(type_ids, doc_ids):
            if (t, b) in allowed:
                continue
            for n, pack in w["packs"].items():
                pt = try_entries(hkdf(w["keys"][n], lab_info(obj, t, b, p0)), pack["lab"]["entries"], "lab")
                assert pt is None, f"{obj}: открылось ({t}, {b}) на этапе {n}"


def _media_refs(o, out):
    if isinstance(o, dict):
        if "src" in o and "mime" in o:
            out.append(o)
        for v in o.values():
            _media_refs(v, out)
    elif isinstance(o, list):
        for v in o:
            _media_refs(v, out)
    return out


def test_media_refs_decrypt(env):
    """Каждый зашифрованный MediaRef (пакеты, экспертизы, развязка, страницы) открывается своим ключом,
    aad = media/<hash>; открытые ссылки указывают на существующие файлы с хешем в имени."""
    dist, w, A = env["dist"], env["walk"], env["A"]
    objs = list(w["packs"].values())
    for L in A["lab"]:
        p0 = [p["variants"][0] for p in L["params"].values()]
        pt = try_entries(hkdf(w["keys"][L["stage"]], lab_info(L["object"], L["types"][0], L["bases"][0], p0)),
                         w["packs"][L["stage"]]["lab"]["entries"], "lab")
        objs.append(json.loads(pt))
    objs.append(open_json(hkdf(w["keys"][w["pub"]["stages"]], b"detgame/finale/v1"), _load(dist, "data/finale.json")))
    for pg in A["pages"]:
        if pg["access"] == "key":
            objs.append(open_json(b64d(pg["key"]), _load(dist, f"p/{pg['slug']}/payload.json")))
    for ref in _media_refs(objs, []):
        if ref["src"] is None:
            assert ref.get("missing") is True
            continue
        blob = (dist / ref["src"].lstrip("/")).read_bytes()
        if "key" in ref:
            assert ref["src"].endswith(".bin") and ref["aad"] == "media/" + Path(ref["src"]).stem
            AESGCM(b64d(ref["key"])).decrypt(blob[:12], blob[12:], ref["aad"].encode())
        else:
            assert not ref["src"].endswith(".bin")


@pytest.mark.skipif(NODE is None, reason="Node.js не найден")
def test_js_walk_matches_python(env):
    res = subprocess.run([NODE, str(ROOT / "tests" / "qa" / "walk_dist.mjs"), str(env["dist"]), str(env["root"] / "answers.json")],
                         capture_output=True, timeout=600)
    assert res.returncode == 0, res.stderr.decode("utf-8", "replace")
    out = json.loads(res.stdout)
    assert out["ok"], "\n".join(out["fails"])
    assert out["keys"] == {str(n): b64e(k) for n, k in env["walk"]["keys"].items()}


# ----------------------------------------------------------------------------- public.json и pack-1


def test_public_json_only_open_fields(env):
    pub = env["walk"]["pub"]
    assert set(pub) == PUBLIC_FIELDS
    assert re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", pub["buildId"])


def test_pack1_has_only_pool_characters_with_open_fields(env):
    p1 = env["walk"]["packs"][1]
    pool: set[str] = set()
    for q in p1["questions"]:
        for f in q.get("fields", [q]):
            pool |= set(f.get("pool", []))
    assert set(p1["characters"]) == pool
    for c in p1["characters"].values():
        assert set(c) == {"full", "short", "photo"}
    for d in p1["documents"]:
        assert d["stage"] == 1 and d["kind"] in ("paper", "online")
    for p in env["walk"]["packs"].values():  # F4: документы kind: lab не перечисляются
        assert all(d["kind"] != "lab" for d in p["documents"])


def test_pool_characters_present_in_pack(env):
    """s4.fb2 — явный пул с voroncov (in_pool: false): персонаж должен быть в pack-4.characters."""
    for n, p in env["walk"]["packs"].items():
        for q in p["questions"]:
            for f in q.get("fields", [q]):
                for pid in f.get("pool", []):
                    assert pid in p["characters"], f"{f['path']}: {pid} нет в pack-{n}.characters"


def test_order_cards_shuffled_not_answer(env):
    ub = _units_by_path(env["A"])
    for p in env["walk"]["packs"].values():
        for q in p["questions"]:
            for f in q.get("fields", [q]):
                if f["type"] == "order":
                    shown = [i["id"] for i in f["items"]]
                    assert shown != ub[f["path"]]["input"]
                    assert sorted(shown) == sorted(ub[f["path"]]["input"])


# ----------------------------------------------------------------------------- независимый leak scan

_SKIP_JSON = {"n", "c", "salt", "saltStart", "saltStage", "key", "saltsId", "buildId"}
_STRUCT = re.compile(r"\.(id|kind|type|path|link|mime|src|aad|alg|who|form|doc|slug|v)$|pool\[\d+\]$|\.(full|short|alt)$")
SHINGLE = 4


def _strings(o, out, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in _SKIP_JSON and isinstance(v, str):
                continue
            _strings(v, out, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            _strings(v, out, f"{path}[{i}]")
    elif isinstance(o, str):
        out.append((path, o))


def _visible(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def _secret_texts(env) -> list[tuple[str, str]]:
    w, A, dist = env["walk"], env["A"], env["dist"]
    out: list[tuple[str, str]] = []
    for n, p in w["packs"].items():
        items: list = []
        if n == 1:
            _strings([q.get("hints", []) for q in p["questions"]], items, ".hints")
        else:
            _strings({k: v for k, v in p.items() if k not in ("lab", "characters")}, items)
            _strings({"types": p["lab"]["types"], "objects": p["lab"]["objects"]}, items, ".lab")
        out += [(f"pack-{n}{a}", _visible(s)) for a, s in items if not _STRUCT.search(a)]
    for L in A["lab"]:
        p0 = [p["variants"][0] for p in L["params"].values()]
        pt = try_entries(hkdf(w["keys"][L["stage"]], lab_info(L["object"], L["types"][0], L["bases"][0], p0)),
                         w["packs"][L["stage"]]["lab"]["entries"], "lab")
        rec = json.loads(pt)
        out += [(f"lab:{L['result']}.title", rec["title"]), (f"lab:{L['result']}.html", _visible(rec["html"]))]
    fin = open_json(hkdf(w["keys"][w["pub"]["stages"]], b"detgame/finale/v1"), _load(dist, "data/finale.json"), "finale")
    items = []
    _strings({k: v for k, v in fin.items() if k != "answers"}, items)
    out += [(f"finale{a}", _visible(s)) for a, s in items if not re.search(r"\.(who|name|form)$", a)]
    for pg in A["pages"]:
        if pg["access"] == "key":
            inner = open_json(b64d(pg["key"]), _load(dist, f"p/{pg['slug']}/payload.json"))
        elif pg["access"] == "password":
            pl = _load(dist, "p/cloud/payload.json")
            pw = normalize("password", pg["password"])
            inner = open_json(pbkdf2(f"detgame/cloud/v1|{pw}".encode(), b64d(pl["salt"]), pl["iter"]), pl["box"])
        else:
            continue
        out.append((f"page:{pg['slug']}", _visible(inner["html"])))
    return out


def _open_corpus(dist: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for f in sorted(dist.rglob("*")):
        if not f.is_file() or f.suffix == ".bin":
            continue
        try:
            raw = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # шрифты
        if f.suffix == ".json":
            obj = json.loads(raw)
            items: list = []
            _strings(obj, items)
            keys: list[str] = []

            def _keys(o):
                if isinstance(o, dict):
                    for k, v in o.items():
                        keys.append(k)
                        _keys(v)
                elif isinstance(o, list):
                    for v in o:
                        _keys(v)

            _keys(obj)
            raw = "\n".join(s for _, s in items) + "\n" + "\n".join(keys)
        raw = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), raw)
        files[f.relative_to(dist).as_posix()] = html.unescape(raw)
    files["<имена файлов>"] = "\n".join(p.relative_to(dist).as_posix() for p in dist.rglob("*"))
    return files


def _shell_visible(text: str) -> str:
    """Что закрытая страница показывает до ключа по замыслу (PLAN E7, FORMATS §9.3): title, бренд, логин."""
    parts = re.findall(r"<title>(.*?)</title>", text, re.S)
    parts += re.findall(r'class="shell__brand">(.*?)<', text, re.S)
    parts += re.findall(r'value="([^"]*)"', text)
    return " | ".join(parts)


def _shingles(tokens: list[str], k: int) -> set[str]:
    return {" ".join(tokens[i:i + k]) for i in range(len(tokens) - k + 1)}


# Совпадения, которые не утечка: общий текст интерфейса совпал с черновым TODO вводного письма 4.
# Общие фразы-заглушки и обороты: «Здесь будет фото профиля» (F11), «так же как в».
ALLOWED_SHINGLES = {"ответы финала нельзя изменить", "здесь будет фото профиля", "так же как в",
                    # вводное письмо 4 пересказывает правило интерфейса (texts.js) — это не секрет
                    "бонусные вопросы прошлых этапов",
                    }


def _public_ok_shingles() -> set[str]:
    """Законные повторы открытого и закрытого текста — ``settings.leak_public_ok`` (название учреждения «Бюро
    судебно-медицинской экспертизы», служебный оборот «с 18:00 до» и т. п.; см. docs/02 §5а)."""
    from engine.build import prepare
    from engine.check import public_ok_texts

    prep = prepare(ROOT / "content", ROOT / "engine" / "salts.lock.json", create_salts=False)
    out: set[str] = set()
    for t in public_ok_texts(prep.content, prep.ctx):
        out |= _shingles(base(t).split(), SHINGLE)
    return out


def _public_brand_shingles() -> set[str]:
    """Названия вымышленных организаций из world.yaml стоят в шапках открытых страниц — это не утечка,
    даже если те же слова есть в закрытых документах (протоколы, бланки)."""
    import yaml
    world = yaml.safe_load((ROOT / "content" / "world.yaml").read_text(encoding="utf-8"))
    names = [world["police"]["department"]]
    out: set[str] = set()
    for n in names:
        out |= _shingles(base(n).split(), SHINGLE)
    return out


def test_independent_leak_scan_secret_fragments(env):
    dist = env["dist"]
    files = _open_corpus(dist)
    brand_sh = _public_brand_shingles() | _public_ok_shingles()
    open_sh: dict[str, set[str]] = {}
    for rel, text in files.items():
        allowed = set(ALLOWED_SHINGLES) | brand_sh
        if rel.startswith("p/") and rel.endswith("/index.html"):
            allowed |= _shingles(base(_shell_visible(text)).split(), SHINGLE)
            allowed.add(base(_shell_visible(text)))
        for sh in _shingles(base(text).split(), SHINGLE):
            if sh not in allowed:
                open_sh.setdefault(sh, set()).add(rel)
    hits = []
    for label, text in _secret_texts(env):
        for sh in _shingles(base(text).split(), SHINGLE):
            for rel in open_sh.get(sh, ()):
                hits.append(f"{rel}: «{sh}» ← {label}")
    assert not hits, "\n".join(sorted(set(hits))[:50])


def test_independent_leak_scan_answers(env):
    """Ответы и варианты text/time/date/number (кроме leak_scan: false) и параметры экспертиз — в сыром и base() виде."""
    prep, A = env["prep"], env["A"]
    files = _open_corpus(env["dist"])
    bases = {rel: f" {base(t)} " for rel, t in files.items()}
    no_scan = {u.path for u in units(prep.content) if not u.leak_scan}
    needles: list[tuple[str, str]] = []
    for path, u in _units_by_path(A).items():
        if u["type"] in ("text", "time", "date", "number") and path not in no_scan:
            needles += [(path, v) for v in [u["input"], *u["variants"]]]
            if u["type"] == "date":
                needles += [(path, f"{v[8:10]}.{v[5:7]}.{v[:4]}") for v in u["variants"]]
    for L in A["lab"]:
        for pid, p in L["params"].items():
            needles += [(f"{L['result']}.{pid}", v) for v in [p["input"], *p["variants"]]]
    hits = []
    for src, v in needles:
        b = base(v)
        if len(b) < 4:  # F5: короткие значения не ищутся
            continue
        for rel, text in bases.items():
            if f" {b} " in text:
                hits.append(f"{rel}: «{v}» ({src})")
    assert not hits, "\n".join(hits)


def test_stage_2_4_document_titles_not_in_open_files(env):
    """docs/03 §4: названия документов stage > 1 — только в зашифрованных пакетах."""
    prep = env["prep"]
    from engine.templating import render

    files = _open_corpus(env["dist"])
    bases = {rel: f" {base(t)} " for rel, t in files.items()}
    hits = []
    for d in prep.content.documents:
        if d.stage > 1:
            t = base(render(d.title, prep.ctx))
            hits += [f"{rel}: {d.id} «{t}»" for rel, b in bases.items() if f" {t} " in b]
    assert not hits, "\n".join(hits)


def test_media_file_names_are_hashes(env):
    for p in (env["dist"] / "m").glob("*") if (env["dist"] / "m").is_dir() else []:
        if p.name == ".htaccess":  # настройки Apache (DEPLOY §2.4), не медиа
            continue
        assert re.fullmatch(r"[0-9a-f]{32}\.(bin|jpg|jpeg|png|webp|svg|mp3|m4a|mp4)", p.name), p.name


def test_answer_entry_length_does_not_identify_choice(env):
    """Записи-проверки шифруют {"c": canon} без выравнивания: по длине `c` видно длину ID ответа.
    Ожидание: для choice ни один вариант не вычисляется однозначно по длине записи."""
    unique = []
    for p in env["walk"]["packs"].values():
        for q in p["questions"]:
            for f in q.get("fields", [q]):
                if f["type"] != "choice":
                    continue
                ln = len(b64d(f["unit"]["entries"][0]["c"])) - 16 - len('{"c":""}')
                cands = [o["id"] for o in f["options"] if len(o["id"].encode()) == ln]
                if len(cands) == 1:
                    unique.append(f"{f['path']} → {cands[0]}")
    assert not unique, "ответ однозначно виден по длине записи: " + ", ".join(unique)


# ----------------------------------------------------------------------------- детерминированность


def test_rebuild_is_stable(env, tmp_path):
    root = env["root"]
    salts = (root / "engine" / "salts.lock.json").read_bytes()
    dist2 = tmp_path / "dist2"
    rep2 = _build(root, dist2)
    assert (root / "engine" / "salts.lock.json").read_bytes() == salts
    assert rep2.stage_keys == env["rep"].stage_keys
    assert rep2.page_keys == env["rep"].page_keys
    w2 = _walk(dist2, env["A"])
    for n, p in w2["packs"].items():
        for q, q1 in zip(p["questions"], env["walk"]["packs"][n]["questions"]):
            assert q.get("items") == q1.get("items")
    pub1, pub2 = env["walk"]["pub"], w2["pub"]
    assert {k: v for k, v in pub1.items() if k != "buildId"} == {k: v for k, v in pub2.items() if k != "buildId"}


# ----------------------------------------------------------------------------- мутации: check должен падать


def _seal(key: bytes, obj, aad: str) -> dict:
    n = os.urandom(12)
    ct = AESGCM(key).encrypt(n, json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode(), aad.encode())
    return {"v": 1, "alg": "A256GCM", "aad": aad, "n": b64e(n), "c": b64e(ct)}


def _mutated(env, tmp_path, fn) -> Path:
    d = tmp_path / "dist"
    shutil.copytree(env["dist"], d)
    fn(d)
    return d


def _repack(env, d: Path, n: int, fn) -> None:
    k = hkdf(env["walk"]["keys"][n], f"detgame/pack/v1|{n}".encode())
    pack = open_json(k, _load(d, f"data/pack-{n}.json"))
    fn(pack)
    (d / f"data/pack-{n}.json").write_text(json.dumps(_seal(k, pack, f"pack/{n}")), encoding="utf-8")


def _check_problems(env, d: Path) -> list[str]:
    root = env["root"]
    return check(root, dist=d, salts_path=root / "engine" / "salts.lock.json").problems


def _new_problems(env, d: Path) -> list[str]:
    """Ошибки check на мутированном dist/, которых нет на исходном (исходный может быть уже красным)."""
    if "baseline" not in env:
        env["baseline"] = set(_check_problems(env, env["dist"]))
    return [p for p in _check_problems(env, d) if p not in env["baseline"]]


def _append(d: Path, rel: str, text: str) -> None:
    p = d / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(text)


def test_check_baseline_ok(env):
    problems = _check_problems(env, env["dist"])
    assert not problems, "\n".join(problems)


DETECTED = {
    "raw answer": ("7", lambda env, d: _append(d, "index.html", "<p>Пропранолол</p>")),
    "html entities": ("7", lambda env, d: _append(d, "index.html", "".join(f"&#{ord(c)};" for c in "пропранолол"))),
    "\\u in js": ("7", lambda env, d: _append(d, "assets/js/core/game.js", "//" + "".join(f"\\u{ord(c):04x}" for c in "анаприлин"))),
    "tolerance variant": ("7", lambda env, d: _append(d, "index.html", "<b>19:37</b>")),
    "date param": ("7", lambda env, d: _append(d, "lab/index.html", "<b>30.10.2026</b>")),
    "watchlist": ("7", lambda env, d: _append(d, "index.html", "СЦЕНИЧЕСКАЯ МАСТЕРСКАЯ")),
    "neutral example": ("7", lambda env, d: _append(d, "lab/index.html", '<input placeholder="21:18">')),
    "page payload swapped": ("5", lambda env, d: (d / "p/inna/payload.json").write_bytes((d / "p/pharma/payload.json").read_bytes())),
    "finale = pack-4": ("6", lambda env, d: (d / "data/finale.json").write_bytes((d / "data/pack-4.json").read_bytes())),
    "saltStage corrupted": ("1", lambda env, d: _repack(env, d, 1, lambda p: p.__setitem__("saltStage", b64e(os.urandom(16))))),
    "lab early stage": ("4", lambda env, d: _repack(env, d, 1, lambda p: p["lab"]["entries"].append(
        _seal(hkdf(env["walk"]["keys"][1], lab_info("blood", "chem", "3-01", [])), {"v": 1, "doc": "3-05"}, "lab")))),
}


@pytest.mark.parametrize("name", list(DETECTED))
def test_check_detects(env, tmp_path, name):
    row, fn = DETECTED[name]
    new = _new_problems(env, _mutated(env, tmp_path, lambda d: fn(env, d)))
    assert any(p.startswith(f"[{row}.") for p in new), new


def _cloud_display_date(env) -> str:
    pg = next(p for p in env["A"]["pages"] if p["access"] == "password")
    pl = _load(env["dist"], "p/cloud/payload.json")
    pw = normalize("password", pg["password"])
    inner = open_json(pbkdf2(f"detgame/cloud/v1|{pw}".encode(), b64d(pl["salt"]), pl["iter"]), pl["box"])
    m = re.search(r"\d\d\.\d\d\.\d{4},? \d\d:\d\d", _visible(inner["html"]))
    assert m, "в облаке нет даты в формате показа"
    return m.group(0)


def _reorder_questions(p):
    p["questions"] = [p["questions"][1], p["questions"][0], *p["questions"][2:]]


GAPS = {
    # docs/02 §3.4 / FORMATS §2.4: клиент берёт порядок и kind из пакета; check — из content
    "pack questions reordered": lambda env, d: _repack(env, d, 1, _reorder_questions),
    "bonus marked mandatory in pack": lambda env, d: _repack(env, d, 1, lambda p: p["questions"][2].__setitem__("kind", "mandatory")),
    "unit.type changed in pack": lambda env, d: _repack(env, d, 3, lambda p: p["questions"][0]["unit"].__setitem__("type", "password")),
    # docs/06 §3.4: «не открывается чужим основанием» — проверяется одно основание и только первый вид
    "lab foreign basis 1-05": lambda env, d: _repack(env, d, 3, lambda p: p["lab"]["entries"].append(
        _seal(hkdf(env["walk"]["keys"][3], lab_info("blood", "chem", "1-05", [])), {"v": 1, "doc": "3-05"}, "lab"))),
    "lab foreign type": lambda env, d: _repack(env, d, 3, lambda p: p["lab"]["entries"].append(
        _seal(hkdf(env["walk"]["keys"][3], lab_info("blood", "prints", "3-01", [])), {"v": 1, "doc": "3-05"}, "lab"))),
    # PLAN B3 / docs/02 §3.4: pack-1 открывается публичным ключом, но leak scan его не читает
    "stage-3 answer and watchlist inside pack-1": lambda env, d: _repack(env, d, 1, lambda p: p["questions"][0].__setitem__(
        "help", "пропранолол; Сценическая мастерская")),
    "non-pool character with role in pack-1": lambda env, d: _repack(env, d, 1, lambda p: p["characters"].__setitem__(
        "rodionov_director", {"full": "Родионов Геннадий Павлович", "short": "Родионов Г. П.", "photo": None,
                              "role": "Директор ООО «Сценическая мастерская»"})),
    # docs/03 §4: названия документов этапов 2–4 — не иголки leak scan
    "stage-2 document title in open html": lambda env, d: _append(d, "index.html", "<p>{}</p>".format(
        env["walk"]["packs"][2]["documents"][0]["title"])),
    # PLAN §9 в.9: ищется только начало текста (≤ 40 символов); середина подсказки не находится
    "middle of a stage-3 hint": lambda env, d: _append(d, "final/index.html", "Ингалятор и успокоительное у погибшего были свои"),
    # PLAN C3: перемешивание карточек order не проверяется
    "order cards in answer order": lambda env, d: _repack(env, d, 1, lambda p: p["questions"][1].__setitem__(
        "items", sorted(p["questions"][1]["items"], key=lambda i: ["k3", "p8", "d1", "x5", "m2", "t7", "b9", "r4"].index(i["id"])))),
    # docs/06 §3.7: тексты закрытых страниц берутся из строк content, а не из отрендеренного фрагмента:
    # дата в формате показа (фильтр dt) и текст из шаблона страницы не ищутся
    "locked cloud date as displayed": lambda env, d: _append(d, "index.html", "<p>{}</p>".format(_cloud_display_date(env))),
    # имена файлов не сканируются; расширения вне списка (.md, .vtt) не сканируются
    "answer in a file name": lambda env, d: _append(d, "assets/propranolol-пропранолол.txt", "x"),
    "answer in .vtt": lambda env, d: _append(d, "m/sub.vtt", "WEBVTT\n\n00:00.000 --> 00:01.000\nпропранолол"),
}


@pytest.mark.parametrize("name", list(GAPS))
def test_check_gap(env, tmp_path, name):
    new = _new_problems(env, _mutated(env, tmp_path, lambda d: GAPS[name](env, d)))
    assert new, f"check не заметил: {name}"
