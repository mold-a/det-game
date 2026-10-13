"""Генератор тестовых векторов криптографии → ``tests/vectors/crypto.json``.

``python -m engine vectors``. Файл детерминирован: все «случайные» байты (ключи, соли,
nonce, паддинг) выводятся из фиксированных меток через SHA-256, а nonce передаются в
:func:`engine.crypto.seal` флагом ``_nonce`` — только здесь, не в сборке.
Повторный запуск даёт побайтно тот же файл.

Проверяют: ``tests/test_crypto.py`` (Python) и ``tests/js/crypto.test.mjs`` (JS).
"""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

from engine import ROOT
from engine import crypto as c
from engine.normalize import normalize

DEFAULT_OUT = ROOT / "tests" / "vectors" / "crypto.json"

# Итерации в векторах заведомо меньше игровых (кроме одного случая PBKDF2): тесты быстрые,
# а совпадение реализаций от числа итераций не зависит.
ANSWER_ITERS = 1000
STAGE_ITERS = 1000
ENTRIES_PAD = 8


def det_bytes(label: str, n: int) -> bytes:
    """Детерминированные «случайные» байты: SHA-256(метка ‖ счётчик)."""
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(f"detgame/vectors|{label}|{counter}".encode("utf-8")).digest()
        counter += 1
    return out[:n]


def _det_rand(label: str):
    """Замена ``os.urandom`` для паддинга: каждый вызов — новые детерминированные байты."""
    counter = itertools.count()
    return lambda n: det_bytes(f"{label}/{next(counter)}", n)


def _hex(b: bytes) -> str:
    return b.hex()


def _b64u_cases() -> dict:
    samples = [b"", b"f", b"fo", b"foo", b"foob", b"fooba", b"foobar", bytes([0xFB, 0xFF, 0xBF]), bytes(range(256))]
    return {
        "valid": [{"hex": _hex(s), "b64u": c.b64u_encode(s)} for s in samples],
        # «=», «+», «/», пробел, длина ≡ 1 (mod 4), ненулевые «хвостовые» биты («AB», «AAB»)
        "invalid": ["AA==", "a+b/", "ab c", "A", "AAAAA", "AB", "AAB", "Zm9vYg=", "Zm9v\n"],
    }


def _pbkdf2_cases() -> list[dict]:
    cases = [
        ("password", det_bytes("pbkdf2/salt/1", 16), 1),
        ("detgame/answer/v1|s1.q1.time|08:15", det_bytes("pbkdf2/salt/2", 16), 1000),
        ("detgame/cloud/v1|пароль ёлка", det_bytes("pbkdf2/salt/3", 16), 150_000),
    ]
    return [
        {
            "password": pw,
            "password_hex": _hex(c.utf8(pw)),
            "salt": c.b64u_encode(salt),
            "iterations": it,
            "key": c.b64u_encode(c.pbkdf2(c.utf8(pw), salt, it)),
        }
        for pw, salt, it in cases
    ]


def _hkdf_cases() -> list[dict]:
    ikm1 = det_bytes("hkdf/ikm/1", 32)
    ikm2 = det_bytes("hkdf/ikm/2", 32)
    cases = [
        (ikm1, c.pack_info(2)),
        (ikm2, c.lab_info("obj-1", "type_a", "doc-1", ["08:15", "ёж"])),
    ]
    return [
        {"ikm": c.b64u_encode(ikm), "info": info.decode("utf-8"), "okm": c.b64u_encode(c.hkdf(ikm, info))}
        for ikm, info in cases
    ]


def _aesgcm_cases() -> list[dict]:
    cases = [
        ("pack/2", '{"intro":"Тестовое письмо этапа","n":2}'),
        ("lab", '{"doc":"x-01","html":"<p>Результат — «тест» ✓</p>"}'),
        ("page/cloud", ""),
    ]
    out = []
    for i, (aad, text) in enumerate(cases, start=1):
        key = det_bytes(f"aes/key/{i}", 32)
        nonce = det_bytes(f"aes/nonce/{i}", c.NONCE_LEN)
        out.append(
            {
                "key": c.b64u_encode(key),
                "aad": aad,
                "plaintext": text,
                "container": c.seal(key, c.utf8(text), aad, _nonce=nonce),
            }
        )
    return out


def _media_case() -> dict:
    key = det_bytes("media/key", 32)
    data = det_bytes("media/data", 100)
    aad = "media/" + hashlib.sha256(data).hexdigest()[:16]
    blob = c.seal_media(key, data, aad, _nonce=det_bytes("media/nonce", c.NONCE_LEN))
    return {"key": c.b64u_encode(key), "aad": aad, "data": c.b64u_encode(data), "blob": c.b64u_encode(blob)}


def _helpers() -> dict:
    salt_start = det_bytes("helpers/salt/start", 16)
    salt_stage1 = det_bytes("helpers/salt/stage/1", 16)
    salt_cloud = det_bytes("helpers/salt/cloud", 16)
    salt_unit = det_bytes("helpers/salt/unit", 16)

    k1 = c.start_key(salt_start, STAGE_ITERS)
    pairs = [("s1.q1.time", "08:15"), ("s1.q2", "zavyalov"), ("s1.q3.who", "gromov,oleg")]
    k2 = c.stage_key(1, pairs, salt_stage1, STAGE_ITERS)

    lab_cases = [
        ("obj-1", "type_a", "doc-1", []),
        ("obj-1", "type_a", "", []),
        ("obj-2", "type_b", "doc-2", ["08:15"]),
        ("obj-2", "type_b", "doc-2", ["08:15", "2026-03-05", "ёж"]),
    ]
    return {
        "answer_key": [
            {
                "path": path,
                "normalized": norm,
                "salt": c.b64u_encode(salt_unit),
                "iterations": ANSWER_ITERS,
                "secret": c.answer_secret(path, norm),
                "key": c.b64u_encode(c.answer_key(path, norm, salt_unit, ANSWER_ITERS)),
            }
            for path, norm in [("s1.q1.time", "08:15"), ("s2.q4", "еж в тумане")]
        ],
        "start_key": {"salt": c.b64u_encode(salt_start), "iterations": STAGE_ITERS, "key": c.b64u_encode(k1)},
        "stage_secret": [
            {"n": 1, "pairs": [list(p) for p in pairs], "secret": c.stage_secret(1, pairs)},
            {"n": 3, "pairs": [["s3.q1", "ёж"]], "secret": c.stage_secret(3, [("s3.q1", "ёж")])},
            {"n": 2, "pairs": [], "secret": c.stage_secret(2, [])},
        ],
        "stage_key": {
            "n": 1,
            "pairs": [list(p) for p in pairs],
            "salt": c.b64u_encode(salt_stage1),
            "iterations": STAGE_ITERS,
            "key": c.b64u_encode(k2),
        },
        "pack_info": [{"n": n, "info": c.pack_info(n).decode("utf-8")} for n in (1, 4)],
        "pack_key": {"stage_key": c.b64u_encode(k2), "n": 2, "key": c.b64u_encode(c.hkdf(k2, c.pack_info(2)))},
        "lab_info": [
            {"object": o, "type": t, "basis": b, "params": p, "info": c.lab_info(o, t, b, p).decode("utf-8")}
            for o, t, b, p in lab_cases
        ],
        "finale_info": c.FINALE_INFO.decode("utf-8"),
        "finale_key": {"stage_key": c.b64u_encode(k2), "key": c.b64u_encode(c.hkdf(k2, c.FINALE_INFO))},
        "cloud_key": {
            "input": " Пароль-Ёлка 2026 ",
            "normalized": normalize("password", " Пароль-Ёлка 2026 "),
            "salt": c.b64u_encode(salt_cloud),
            "iterations": STAGE_ITERS,
            "key": c.b64u_encode(c.cloud_key(normalize("password", " Пароль-Ёлка 2026 "), salt_cloud, STAGE_ITERS)),
        },
    }


def _deterministic_shuffle(items: list[dict], label: str) -> list[dict]:
    keyed = [(det_bytes(f"{label}/{i}", 8), item) for i, item in enumerate(items)]
    return [item for _, item in sorted(keyed, key=lambda kv: kv[0])]


def _answer_unit() -> dict:
    """Единица ``time`` с допуском ±1 мин: 3 варианта, паддинг до 8, перемешано."""
    path = "s1.q1.time"
    canonical = "08:15"
    variants = ["08:14", "08:15", "08:16"]
    salt = det_bytes("unit/salt", 16)
    aad = c.answer_aad(path)
    real = []
    for v in variants:
        key = c.answer_key(path, v, salt, ANSWER_ITERS)
        real.append(c.seal_answer(key, path, canonical, _nonce=det_bytes(f"unit/nonce/{v}", c.NONCE_LEN)))
    ct_len = len(c.b64u_decode(real[0]["c"]))
    pad = [
        c.fake_container(aad, ct_len, _rand=_det_rand(f"unit/pad/{i}"))
        for i in range(ENTRIES_PAD - len(real))
    ]
    entries = _deterministic_shuffle(real + pad, "unit/shuffle")
    return {
        "path": path,
        "type": "time",
        "salt": c.b64u_encode(salt),
        "iterations": ANSWER_ITERS,
        "canonical": canonical,
        "variants": variants,
        "entries_pad": ENTRIES_PAD,
        "entries": entries,
        # ввод → нормализация (normalize.json) → ключ → запись
        "accept": [
            {"input": "8.15", "normalized": "08:15"},
            {"input": "814", "normalized": "08:14"},
            {"input": "8 ч 16 мин", "normalized": "08:16"},
        ],
        "reject": [
            {"input": "08:17", "normalized": "08:17"},
            {"input": "08:13", "normalized": "08:13"},
            {"input": "20:15", "normalized": "20:15"},
        ],
    }


def _lab_entry() -> dict:
    """Запись экспертизы: ключ из ``K_N`` и ``lab_info``, ``aad = "lab"``; паддинг до 8."""
    stage_key = det_bytes("lab/stage_key", 32)
    request = {"object": "obj-1", "type": "type_a", "basis": "doc-1", "params": []}
    key = c.hkdf(stage_key, c.lab_info(request["object"], request["type"], request["basis"], request["params"]))
    content = '{"doc":"x-02","html":"<p>Заключение</p>","media":[],"title":"Тест"}'
    real = c.seal(key, c.utf8(content), "lab", _nonce=det_bytes("lab/nonce", c.NONCE_LEN))
    ct_len = len(c.b64u_decode(real["c"]))
    pad = [
        c.fake_container("lab", ct_len, _rand=_det_rand(f"lab/pad/{i}"))
        for i in range(ENTRIES_PAD - 1)
    ]
    return {
        "stage_key": c.b64u_encode(stage_key),
        "request": request,
        "plaintext": content,
        "wrong_requests": [
            {"object": "obj-1", "type": "type_a", "basis": "doc-2", "params": []},
            {"object": "obj-1", "type": "type_a", "basis": "", "params": []},
            {"object": "obj-1", "type": "type_a", "basis": "doc-1", "params": ["08:15"]},
            {"object": "obj-2", "type": "type_a", "basis": "doc-1", "params": []},
        ],
        "entries": _deterministic_shuffle([real, *pad], "lab/shuffle"),
    }


def build_crypto_vectors() -> dict:
    return {
        "_comment": "Сгенерировано `python -m engine vectors` (engine/vectors.py). Не редактировать руками. "
        "Байты — base64url без «=», если не сказано иное.",
        "version": 1,
        "b64u": _b64u_cases(),
        "pbkdf2": _pbkdf2_cases(),
        "hkdf": _hkdf_cases(),
        "aesgcm": _aesgcm_cases(),
        "media": _media_case(),
        "helpers": _helpers(),
        "answer_unit": _answer_unit(),
        "lab_entry": _lab_entry(),
    }


def render_crypto_vectors() -> str:
    return json.dumps(build_crypto_vectors(), ensure_ascii=False, indent=2) + "\n"


def make_crypto_vectors(out: Path = DEFAULT_OUT) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_crypto_vectors(), encoding="utf-8", newline="\n")
    return out
