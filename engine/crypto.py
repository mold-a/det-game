"""Криптография — docs/02-architecture.md §3.

Зеркало ``site/assets/js/core/crypto.js``. Векторы — ``tests/vectors/crypto.json``
(``python -m engine vectors``); кросс-тест JS → Python — ``tests/test_crypto_js_compat.py``.

Примитивы: PBKDF2-HMAC-SHA256 (32 байта), HKDF-SHA256 (соль — 32 нулевых байта,
32 байта), AES-256-GCM (nonce 12 байт, тег 128 бит, AAD обязателен), base64url без «=».
"""

from __future__ import annotations

import base64
import json
import os
import re
from collections.abc import Iterable, Sequence

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from engine.util import canonical_json

KEY_LEN = 32
NONCE_LEN = 12
TAG_LEN = 16
HKDF_SALT = bytes(32)  # явно с обеих сторон (R1)
CONTAINER_VERSION = 1
CONTAINER_ALG = "A256GCM"

ANSWER_PREFIX = "detgame/answer/v1|"
STAGE_PREFIX = "detgame/stage/v1|"
START_SECRET = "detgame/stage/v1|start"
PACK_PREFIX = "detgame/pack/v1|"
LAB_PREFIX = "detgame/lab/v1|"
CLOUD_PREFIX = "detgame/cloud/v1|"
FINALE_INFO = b"detgame/finale/v1"
UNIT_SEP = "\x1f"

_B64U = re.compile(r"[A-Za-z0-9_-]*")


class CryptoError(ValueError):
    """Неверный ключ, AAD, повреждённый контейнер или кодировка (не голый ``InvalidTag``)."""


# --- кодирование -----------------------------------------------------------------


def utf8(s: str) -> bytes:
    return s.encode("utf-8")


def b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def b64u_decode(s: str) -> bytes:
    """Строгий base64url без «=»: только алфавит, допустимая длина, каноническая форма."""
    if not isinstance(s, str) or not _B64U.fullmatch(s) or len(s) % 4 == 1:
        raise CryptoError("неверная строка base64url")
    data = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    if b64u_encode(data) != s:  # ненулевые «хвостовые» биты
        raise CryptoError("неканоническая строка base64url")
    return data


def _check_key(key: bytes) -> None:
    if not isinstance(key, (bytes, bytearray)) or len(key) != KEY_LEN:
        raise CryptoError(f"ключ должен быть {KEY_LEN} байта")


# --- выработка ключей ------------------------------------------------------------


def pbkdf2(password: bytes, salt: bytes, iterations: int) -> bytes:
    """PBKDF2-HMAC-SHA256 → 32 байта."""
    if iterations < 1:
        raise ValueError("iterations должно быть ≥ 1")
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=KEY_LEN, salt=bytes(salt), iterations=iterations)
    return kdf.derive(bytes(password))


def hkdf(ikm: bytes, info: bytes) -> bytes:
    """HKDF-SHA256, соль — 32 нулевых байта, длина 32."""
    kdf = HKDF(algorithm=hashes.SHA256(), length=KEY_LEN, salt=HKDF_SALT, info=bytes(info))
    return kdf.derive(bytes(ikm))


# --- AES-256-GCM -----------------------------------------------------------------


def seal(key: bytes, plaintext: bytes, aad: str, *, _nonce: bytes | None = None) -> dict:
    """Зашифровать в контейнер ``{"v", "alg", "aad", "n", "c"}`` (docs/02 §3.1).

    ``_nonce`` — только для генератора векторов (engine/vectors.py); в сборке не передаётся.
    """
    _check_key(key)
    if not isinstance(aad, str) or not aad:
        raise CryptoError("AAD обязателен")
    nonce = os.urandom(NONCE_LEN) if _nonce is None else bytes(_nonce)
    if len(nonce) != NONCE_LEN:
        raise CryptoError(f"nonce должен быть {NONCE_LEN} байт")
    ct = AESGCM(bytes(key)).encrypt(nonce, bytes(plaintext), utf8(aad))
    return {"v": CONTAINER_VERSION, "alg": CONTAINER_ALG, "aad": aad, "n": b64u_encode(nonce), "c": b64u_encode(ct)}


def _parse_container(container: object) -> tuple[str, bytes, bytes]:
    if not isinstance(container, dict):
        raise CryptoError("контейнер должен быть объектом")
    if container.get("v") != CONTAINER_VERSION or container.get("alg") != CONTAINER_ALG:
        raise CryptoError("неизвестная версия или алгоритм контейнера")
    aad = container.get("aad")
    if not isinstance(aad, str) or not aad:
        raise CryptoError("в контейнере нет AAD")
    nonce = b64u_decode(container.get("n"))
    ct = b64u_decode(container.get("c"))
    if len(nonce) != NONCE_LEN or len(ct) < TAG_LEN:
        raise CryptoError("повреждённый контейнер")
    return aad, nonce, ct


def open_(key: bytes, container: dict, aad: str | None = None) -> bytes:
    """Расшифровать контейнер. ``aad`` — ожидаемый AAD: если передан и не совпадает
    с записанным в контейнере, это ошибка (защита от подмены контейнера).

    Неверный ключ, AAD или повреждение → :class:`CryptoError`.
    """
    _check_key(key)
    stored, nonce, ct = _parse_container(container)
    if aad is not None and aad != stored:
        raise CryptoError("AAD контейнера не совпадает с ожидаемым")
    try:
        return AESGCM(bytes(key)).decrypt(nonce, ct, utf8(stored))
    except InvalidTag:
        raise CryptoError("неверный ключ или AAD") from None


def try_entries(key: bytes, entries: Iterable[dict], aad: str) -> bytes | None:
    """Попробовать расшифровать записи ключом; первая удачная → открытый текст, иначе ``None``.

    Записи с другим AAD или повреждённые пропускаются (паддинг выглядит как настоящие записи).
    """
    _check_key(key)
    for entry in entries:
        try:
            return open_(key, entry, aad)
        except CryptoError:
            continue
    return None


def fake_container(aad: str, ct_len: int, *, _rand=os.urandom) -> dict:
    """Запись-паддинг: случайные nonce и шифротекст длиной ``ct_len`` (как у настоящих)."""
    if ct_len < TAG_LEN:
        raise ValueError("шифротекст короче тега")
    return {
        "v": CONTAINER_VERSION,
        "alg": CONTAINER_ALG,
        "aad": aad,
        "n": b64u_encode(_rand(NONCE_LEN)),
        "c": b64u_encode(_rand(ct_len)),
    }


def seal_media(key: bytes, data: bytes, aad: str, *, _nonce: bytes | None = None) -> bytes:
    """Медиафайл: ``nonce (12) ‖ ciphertext ‖ tag (16)`` (docs/02 §4а)."""
    _check_key(key)
    if not aad:
        raise CryptoError("AAD обязателен")
    nonce = os.urandom(NONCE_LEN) if _nonce is None else bytes(_nonce)
    if len(nonce) != NONCE_LEN:
        raise CryptoError(f"nonce должен быть {NONCE_LEN} байт")
    return nonce + AESGCM(bytes(key)).encrypt(nonce, bytes(data), utf8(aad))


def open_media(key: bytes, blob: bytes, aad: str) -> bytes:
    _check_key(key)
    if len(blob) < NONCE_LEN + TAG_LEN:
        raise CryptoError("повреждённый медиафайл")
    try:
        return AESGCM(bytes(key)).decrypt(bytes(blob[:NONCE_LEN]), bytes(blob[NONCE_LEN:]), utf8(aad))
    except InvalidTag:
        raise CryptoError("неверный ключ или AAD") from None


# --- строки и ключи схемы (docs/02 §3.3–3.9) -------------------------------------


def answer_secret(path: str, normalized: str) -> str:
    return ANSWER_PREFIX + path + "|" + normalized


def answer_key(path: str, normalized: str, salt: bytes, iters: int) -> bytes:
    """``K(x) = PBKDF2(UTF8("detgame/answer/v1|" + path + "|" + x), salt_u, ITER_ANSWER)``."""
    return pbkdf2(utf8(answer_secret(path, normalized)), salt, iters)


def answer_aad(path: str) -> str:
    return "ans/" + path


def answer_plaintext(canonical: str) -> bytes:
    """``UTF8(JSON {"c": canonical})`` — содержимое записи-проверки."""
    return canonical_json({"c": canonical})


def seal_answer(key: bytes, path: str, canonical: str, *, _nonce: bytes | None = None) -> dict:
    return seal(key, answer_plaintext(canonical), answer_aad(path), _nonce=_nonce)


def check_answer(key: bytes, path: str, entries: Iterable[dict]) -> str | None:
    """Ключ из нормализованного ввода → канонический ответ или ``None`` (неверно)."""
    pt = try_entries(key, entries, answer_aad(path))
    if pt is None:
        return None
    return json.loads(pt.decode("utf-8"))["c"]


def start_key(salt: bytes, iters: int) -> bytes:
    """``K1 = PBKDF2(UTF8("detgame/stage/v1|start"), salt_start, ITER_STAGE)``."""
    return pbkdf2(utf8(START_SECRET), salt, iters)


def stage_secret(n: int, pairs: Sequence[tuple[str, str]]) -> str:
    """``"detgame/stage/v1|" + N + "\\x1f" + "\\x1f".join(path + "=" + canon)``."""
    return STAGE_PREFIX + str(int(n)) + UNIT_SEP + UNIT_SEP.join(p + "=" + c for p, c in pairs)


def stage_key(n: int, pairs: Sequence[tuple[str, str]], salt: bytes, iters: int) -> bytes:
    """``K_{N+1} = PBKDF2(UTF8(secret_N), salt_stage_N, ITER_STAGE)``."""
    return pbkdf2(utf8(stage_secret(n, pairs)), salt, iters)


def pack_info(n: int) -> bytes:
    return utf8(PACK_PREFIX + str(int(n)))


def lab_info(object_id: str, type_id: str, basis: str, params: Sequence[str]) -> bytes:
    """``"detgame/lab/v1|" + object + "|" + type + "|" + b + "|" + p``; ``p`` — параметры
    через ``|``, пусто без параметров (завершающий ``|`` есть всегда — решение автора 1)."""
    return utf8(LAB_PREFIX + object_id + "|" + type_id + "|" + basis + "|" + "|".join(params))


def cloud_key(password_norm: str, salt: bytes, iters: int) -> bytes:
    """``PBKDF2(UTF8("detgame/cloud/v1|" + password(ввод)), salt_cloud, ITER_STAGE)``."""
    return pbkdf2(utf8(CLOUD_PREFIX + password_norm), salt, iters)
