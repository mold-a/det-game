"""Кросс-тест JS → Python: tests/js/make_vectors.mjs шифрует на Web Crypto, Python расшифровывает.

Обратное направление (Python → JS) — tests/js/crypto.test.mjs по tests/vectors/crypto.json.
Без Node тест пропускается.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from engine import crypto as c
from engine.normalize import normalize

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tests" / "js" / "make_vectors.mjs"
D = c.b64u_decode

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js не найден")


@pytest.fixture(scope="module")
def js() -> dict:
    res = subprocess.run([NODE, str(SCRIPT)], cwd=ROOT, capture_output=True, timeout=120)
    assert res.returncode == 0, res.stderr.decode("utf-8", "replace")
    return json.loads(res.stdout.decode("utf-8"))


def test_b64u(js):
    for case in js["b64u"]:
        raw = bytes.fromhex(case["hex"])
        assert c.b64u_decode(case["b64u"]) == raw
        assert c.b64u_encode(raw) == case["b64u"]


def test_pbkdf2(js):
    for case in js["pbkdf2"]:
        assert c.pbkdf2(c.utf8(case["password"]), D(case["salt"]), case["iterations"]) == D(case["key"])


def test_hkdf(js):
    for case in js["hkdf"]:
        assert c.hkdf(D(case["ikm"]), c.utf8(case["info"])) == D(case["okm"])


def test_containers_open_in_python(js):
    for case in js["aesgcm"]:
        key, box = D(case["key"]), case["container"]
        assert set(box) == {"v", "alg", "aad", "n", "c"}
        assert c.open_(key, box, case["aad"]) == c.utf8(case["plaintext"])
        with pytest.raises(c.CryptoError):
            c.open_(bytes(32), box)
        with pytest.raises(c.CryptoError):
            c.open_(key, {**box, "aad": "other"})


def test_media(js):
    m = js["media"]
    assert c.open_media(D(m["key"]), D(m["blob"]), m["aad"]) == D(m["data"])


def test_answer_entries(js):
    u = js["answer_unit"]
    salt = D(u["salt"])
    assert u["variants"] == [normalize("persons", ["Gromov", "Oleg"]), normalize("persons", ["oleg", "GROMOV", "gromov"])]
    for variant in u["variants"]:
        key = c.answer_key(u["path"], variant, salt, u["iterations"])
        assert c.check_answer(key, u["path"], u["entries"]) == u["canonical"]
    for e in u["entries"]:
        assert len(D(e["c"])) == c.answer_ct_len(u["canonical"]), "JS выравнивает так же, как Python"
    wrong = c.answer_key(u["path"], "gromov", salt, u["iterations"])
    assert c.check_answer(wrong, u["path"], u["entries"]) is None


def test_helpers(js):
    h = js["helpers"]
    st = h["stage"]
    pairs = [tuple(p) for p in st["pairs"]]
    assert c.stage_secret(st["n"], pairs) == st["secret"]
    stage_key = c.stage_key(st["n"], pairs, D(st["salt"]), st["iterations"])
    assert stage_key == D(st["key"])
    assert c.start_key(D(h["start"]["salt"]), h["start"]["iterations"]) == D(h["start"]["key"])
    cl = h["cloud"]
    assert normalize("password", " Пароль-Ёлка ") == cl["normalized"]
    assert c.cloud_key(cl["normalized"], D(cl["salt"]), cl["iterations"]) == D(cl["key"])
    assert c.pack_info(h["pack"]["n"]) == c.utf8(h["pack"]["info"])
    assert c.hkdf(stage_key, c.pack_info(h["pack"]["n"])) == D(h["pack"]["key"])
    assert c.hkdf(stage_key, c.FINALE_INFO) == D(h["finale"]["key"])
    r = h["lab"]["request"]
    info = c.lab_info(r["object"], r["type"], r["basis"], r["params"])
    assert info == c.utf8(h["lab"]["info"])
    assert c.try_entries(c.hkdf(stage_key, info), [h["lab"]["container"]], "lab") == b'{"doc":"x-02"}'
