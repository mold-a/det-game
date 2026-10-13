"""Ввод-вывод и канонический JSON. Только stdlib.

Все файлы читаются и пишутся в UTF-8 с переводами строк ``\\n`` (Windows, Git).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json(obj: Any) -> bytes:
    """Каноническая форма для хешей: сортировка ключей, без пробелов, UTF-8, без ``\\n`` в конце."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def pretty_json(obj: Any) -> str:
    """Читаемая каноническая форма для файлов в репозитории: сортировка ключей, отступ 2, ``\\n`` в конце."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def write_json(path: Path, obj: Any, *, pretty: bool = False) -> None:
    if pretty:
        write_text(path, pretty_json(obj))
    else:
        write_text(path, canonical_json(obj).decode("utf-8"))


# base64url без «=»: единственная реализация — engine/crypto.py. Здесь — тонкие обёртки
# с отложенным импортом (crypto.py сам импортирует util.canonical_json).
def b64u_encode(data: bytes) -> str:
    from engine.crypto import b64u_encode as _enc

    return _enc(data)


def b64u_decode(text: str) -> bytes:
    """Строгий декодер; ошибка — ``engine.crypto.CryptoError`` (подкласс ``ValueError``)."""
    from engine.crypto import b64u_decode as _dec

    return _dec(text)


def format_loc(parts: tuple | list) -> str:
    """``("stages", 2, "questions", 0, "answer")`` → ``stages[2].questions[0].answer``."""
    out = ""
    for p in parts:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            out += ("." if out else "") + str(p)
    return out


def iter_strings(obj: Any, loc: tuple = ()):
    """Все строки дерева YAML/JSON с путями: ``(loc_tuple, str)``. Ключи словарей не обходятся."""
    if isinstance(obj, str):
        yield loc, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, (*loc, k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from iter_strings(v, (*loc, i))
