"""Криптография (docs/02 §3): векторы tests/vectors/crypto.json, ошибки, независимые проверки."""

import hashlib
import hmac
import json
from pathlib import Path

import pytest

from engine import crypto as c
from engine.normalize import normalize
from engine.vectors import render_crypto_vectors

VECTORS_PATH = Path(__file__).parent / "vectors" / "crypto.json"
V = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
D = c.b64u_decode


# --- генератор ------------------------------------------------------------------


def test_vectors_file_is_up_to_date_and_deterministic():
    first = render_crypto_vectors()
    assert first == render_crypto_vectors()
    assert VECTORS_PATH.read_text(encoding="utf-8") == first, "перегенерируйте: python -m engine vectors"


def test_cli_vectors_writes_same_file(tmp_path, monkeypatch):
    import engine.vectors as vectors
    from engine.__main__ import main

    out = tmp_path / "crypto.json"
    monkeypatch.setattr(vectors, "DEFAULT_OUT", out)
    monkeypatch.setattr(vectors.make_crypto_vectors, "__defaults__", (out,))
    assert main(["vectors"]) == 0
    assert out.read_bytes() == VECTORS_PATH.read_bytes()


# --- base64url ------------------------------------------------------------------


@pytest.mark.parametrize("case", V["b64u"]["valid"], ids=lambda x: x["b64u"][:12] or "empty")
def test_b64u_valid(case):
    raw = bytes.fromhex(case["hex"])
    assert c.b64u_encode(raw) == case["b64u"]
    assert c.b64u_decode(case["b64u"]) == raw


@pytest.mark.parametrize("s", V["b64u"]["invalid"])
def test_b64u_invalid(s):
    with pytest.raises(c.CryptoError):
        c.b64u_decode(s)


def test_b64u_rejects_non_string():
    with pytest.raises(c.CryptoError):
        c.b64u_decode(None)  # type: ignore[arg-type]


# --- KDF ------------------------------------------------------------------------


@pytest.mark.parametrize("case", V["pbkdf2"], ids=lambda x: str(x["iterations"]))
def test_pbkdf2(case):
    pw = c.utf8(case["password"])
    assert pw.hex() == case["password_hex"]
    key = c.pbkdf2(pw, D(case["salt"]), case["iterations"])
    assert key == D(case["key"])
    # независимо: hashlib (та же функция по RFC 8018)
    assert key == hashlib.pbkdf2_hmac("sha256", pw, D(case["salt"]), case["iterations"], 32)


def _hkdf_rfc5869(ikm: bytes, info: bytes, salt: bytes = b"") -> bytes:
    prk = hmac.new(salt or bytes(32), ikm, hashlib.sha256).digest()
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()


@pytest.mark.parametrize("case", V["hkdf"], ids=lambda x: x["info"][:20])
def test_hkdf(case):
    ikm, info = D(case["ikm"]), c.utf8(case["info"])
    okm = c.hkdf(ikm, info)
    assert okm == D(case["okm"])
    # независимо: RFC 5869 вручную; пустая соль ≡ 32 нулевых байта
    assert okm == _hkdf_rfc5869(ikm, info, bytes(32)) == _hkdf_rfc5869(ikm, info, b"")


# --- AES-GCM --------------------------------------------------------------------


@pytest.mark.parametrize("case", V["aesgcm"], ids=lambda x: x["aad"])
def test_aesgcm_vector_opens(case):
    key = D(case["key"])
    box = case["container"]
    assert box["v"] == 1 and box["alg"] == "A256GCM" and box["aad"] == case["aad"]
    assert c.open_(key, box) == c.utf8(case["plaintext"])
    assert c.open_(key, box, case["aad"]) == c.utf8(case["plaintext"])
    # детерминированный nonce воспроизводит тот же контейнер
    assert c.seal(key, c.utf8(case["plaintext"]), case["aad"], _nonce=D(box["n"])) == box


@pytest.mark.parametrize("case", V["aesgcm"], ids=lambda x: x["aad"])
def test_aesgcm_wrong_key_and_aad(case):
    key = D(case["key"])
    box = case["container"]
    wrong_key = bytes([key[0] ^ 1]) + key[1:]
    with pytest.raises(c.CryptoError):
        c.open_(wrong_key, box)
    with pytest.raises(c.CryptoError):
        c.open_(key, {**box, "aad": box["aad"] + "x"})  # подменённый AAD → тег не сходится
    with pytest.raises(c.CryptoError):
        c.open_(key, box, "pack/9")  # ожидали другой AAD
    tampered = bytearray(D(box["c"]))
    tampered[-1] ^= 1
    with pytest.raises(c.CryptoError):
        c.open_(key, {**box, "c": c.b64u_encode(bytes(tampered))})


@pytest.mark.parametrize(
    "box",
    [
        None,
        {},
        {"v": 2, "alg": "A256GCM", "aad": "x", "n": "AAAAAAAAAAAAAAAA", "c": "AAAAAAAAAAAAAAAAAAAAAA"},
        {"v": 1, "alg": "A128GCM", "aad": "x", "n": "AAAAAAAAAAAAAAAA", "c": "AAAAAAAAAAAAAAAAAAAAAA"},
        {"v": 1, "alg": "A256GCM", "aad": "", "n": "AAAAAAAAAAAAAAAA", "c": "AAAAAAAAAAAAAAAAAAAAAA"},
        {"v": 1, "alg": "A256GCM", "aad": "x", "n": "AAAA", "c": "AAAAAAAAAAAAAAAAAAAAAA"},
        {"v": 1, "alg": "A256GCM", "aad": "x", "n": "AAAAAAAAAAAAAAAA", "c": "AAAA"},
        {"v": 1, "alg": "A256GCM", "aad": "x", "n": "AAAAAAAAAAAAAAAA=", "c": "AAAAAAAAAAAAAAAAAAAAAA"},
    ],
)
def test_open_malformed_container(box):
    with pytest.raises(c.CryptoError):
        c.open_(bytes(32), box)


def test_seal_roundtrip_random_nonce():
    key = bytes(range(32))
    a = c.seal(key, "секрет".encode("utf-8"), "pack/1")
    b = c.seal(key, "секрет".encode("utf-8"), "pack/1")
    assert a["n"] != b["n"]
    assert c.open_(key, a) == c.open_(key, b) == "секрет".encode("utf-8")


def test_seal_requires_aad_and_key_len():
    with pytest.raises(c.CryptoError):
        c.seal(bytes(32), b"x", "")
    with pytest.raises(c.CryptoError):
        c.seal(bytes(16), b"x", "lab")


def test_media_vector():
    m = V["media"]
    key, blob = D(m["key"]), D(m["blob"])
    assert c.open_media(key, blob, m["aad"]) == D(m["data"])
    assert c.seal_media(key, D(m["data"]), m["aad"], _nonce=blob[:12]) == blob
    with pytest.raises(c.CryptoError):
        c.open_media(key, blob, m["aad"] + "x")
    with pytest.raises(c.CryptoError):
        c.open_media(key, blob[:20], m["aad"])


# --- хелперы строк (docs/02 §3.3–3.9) -------------------------------------------


def test_answer_key():
    for case in V["helpers"]["answer_key"]:
        assert c.answer_secret(case["path"], case["normalized"]) == case["secret"]
        assert case["secret"] == "detgame/answer/v1|" + case["path"] + "|" + case["normalized"]
        key = c.answer_key(case["path"], case["normalized"], D(case["salt"]), case["iterations"])
        assert key == D(case["key"])


def test_start_and_stage_keys():
    h = V["helpers"]
    assert c.start_key(D(h["start_key"]["salt"]), h["start_key"]["iterations"]) == D(h["start_key"]["key"])
    for case in h["stage_secret"]:
        assert c.stage_secret(case["n"], [tuple(p) for p in case["pairs"]]) == case["secret"]
    assert h["stage_secret"][0]["secret"] == (
        "detgame/stage/v1|1\x1fs1.q1.time=08:15\x1fs1.q2=zavyalov\x1fs1.q3.who=gromov,oleg"
    )
    sk = h["stage_key"]
    key = c.stage_key(sk["n"], [tuple(p) for p in sk["pairs"]], D(sk["salt"]), sk["iterations"])
    assert key == D(sk["key"])


def test_info_strings_and_derived_keys():
    h = V["helpers"]
    for case in h["pack_info"]:
        assert c.pack_info(case["n"]) == c.utf8(case["info"]) == c.utf8(f"detgame/pack/v1|{case['n']}")
    assert c.hkdf(D(h["pack_key"]["stage_key"]), c.pack_info(h["pack_key"]["n"])) == D(h["pack_key"]["key"])
    assert c.FINALE_INFO == b"detgame/finale/v1" == c.utf8(h["finale_info"])
    assert c.hkdf(D(h["finale_key"]["stage_key"]), c.FINALE_INFO) == D(h["finale_key"]["key"])
    for case in h["lab_info"]:
        assert c.lab_info(case["object"], case["type"], case["basis"], case["params"]) == c.utf8(case["info"])


def test_lab_info_always_has_trailing_separator():
    # Решение автора 1: без параметров — завершающий «|» (ровно четыре «|» после префикса)
    assert c.lab_info("o", "t", "b", []) == b"detgame/lab/v1|o|t|b|"
    assert c.lab_info("o", "t", "b", ["p1", "p2"]) == b"detgame/lab/v1|o|t|b|p1|p2"


def test_cloud_key():
    ck = V["helpers"]["cloud_key"]
    assert normalize("password", ck["input"]) == ck["normalized"]
    assert c.cloud_key(ck["normalized"], D(ck["salt"]), ck["iterations"]) == D(ck["key"])


# --- записи-проверки и экспертизы -----------------------------------------------


def test_answer_unit_entries():
    u = V["answer_unit"]
    salt = D(u["salt"])
    assert len(u["entries"]) == u["entries_pad"] == 8
    assert {e["aad"] for e in u["entries"]} == {"ans/" + u["path"]}
    assert len({len(e["c"]) for e in u["entries"]}) == 1, "паддинг той же длины, что и записи"
    assert len(D(u["entries"][0]["c"])) == c.answer_ct_len(u["canonical"]) == 128 + 16
    for variant in u["variants"]:
        key = c.answer_key(u["path"], variant, salt, u["iterations"])
        assert c.check_answer(key, u["path"], u["entries"]) == u["canonical"]
    for case in u["accept"]:
        norm = normalize(u["type"], case["input"])
        assert norm == case["normalized"]
        key = c.answer_key(u["path"], norm, salt, u["iterations"])
        assert c.check_answer(key, u["path"], u["entries"]) == u["canonical"]
    for case in u["reject"]:
        norm = normalize(u["type"], case["input"])
        assert norm == case["normalized"]
        key = c.answer_key(u["path"], norm, salt, u["iterations"])
        assert c.check_answer(key, u["path"], u["entries"]) is None
    # верный ключ, но чужой путь (AAD) — не открывается
    key = c.answer_key(u["path"], u["canonical"], salt, u["iterations"])
    assert c.try_entries(key, u["entries"], "ans/s1.q2") is None


def test_lab_entry():
    lab = V["lab_entry"]
    k = D(lab["stage_key"])

    def key_for(r):
        return c.hkdf(k, c.lab_info(r["object"], r["type"], r["basis"], r["params"]))

    assert c.try_entries(key_for(lab["request"]), lab["entries"], "lab") == c.utf8(lab["plaintext"])
    assert c.try_entries(key_for(lab["request"]), lab["entries"], "pack/1") is None
    for r in lab["wrong_requests"]:
        assert c.try_entries(key_for(r), lab["entries"], "lab") is None


def test_try_entries_skips_garbage():
    key = bytes(32)
    good = c.seal(key, b"ok", "lab")
    entries = [{"v": 1}, "мусор", c.fake_container("lab", 20), good]
    assert c.try_entries(key, entries, "lab") == b"ok"
    assert c.try_entries(key, [], "lab") is None


def test_answer_plaintext_padding_vectors():
    for case in V["helpers"]["answer_plaintext"]:
        pt = c.answer_plaintext(case["canonical"])
        assert pt == c.utf8(case["plaintext"])
        assert len(pt) == case["length"] == c.answer_plaintext_len(case["canonical"])
        assert len(pt) >= 128 and len(pt) % 64 == 0
        obj = json.loads(pt)
        assert set(obj) == {"c", "p"} and obj["c"] == case["canonical"] and obj["p"].strip(" ") == ""


def test_answer_plaintext_is_padded_canonical_json():
    assert c.answer_plaintext("08:15") == b'{"c":"08:15","p":"' + b" " * (128 - 20) + b'"}'
    assert len(c.answer_plaintext("ёж")) == 128
    # граница: 113 + 15 = 128 байт без пробелов, 114 → 192
    assert c.answer_plaintext("a" * 113) == b'{"c":"' + b"a" * 113 + b'","p":""}'
    assert len(c.answer_plaintext("a" * 114)) == 192


def test_answer_entries_hide_canon_length():
    # ID разной длины → записи одной длины (QA: длина записи выдавала ответ choice)
    key = bytes(32)
    lens = {len(c.b64u_decode(c.seal_answer(key, "s1.q1", cid)["c"])) for cid in ["a", "fund", "train", "early", "x" * 60]}
    assert lens == {128 + 16}
    assert c.answer_ct_len("fund") == 144


def test_check_answer_ignores_padding_field():
    key = bytes(32)
    assert c.check_answer(key, "s1.q1", [c.seal_answer(key, "s1.q1", "fund")]) == "fund"
    # старый формат без "p" тоже читается: клиент смотрит только на "c"
    assert c.check_answer(key, "s1.q1", [c.seal(key, b'{"c":"fund"}', "ans/s1.q1")]) == "fund"
    assert c.check_answer(key, "s1.q1", [c.seal(key, b'{"p":"  "}', "ans/s1.q1")]) is None
