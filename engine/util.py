"""Ввод-вывод и канонический JSON. Только stdlib.

Все файлы читаются и пишутся в UTF-8 с переводами строк ``\\n`` (Windows, Git).
"""

from __future__ import annotations

import base64
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


# base64url без «=». Временная копия: в engine/crypto.py есть свой хелпер — объединить.
def b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64u_decode(text: str) -> bytes:
    if not isinstance(text, str) or "=" in text:
        raise ValueError("ожидается base64url без «=»")
    pad = "=" * (-len(text) % 4)
    raw = base64.urlsafe_b64decode(text + pad)
    if b64u_encode(raw) != text:  # отсекает лишние символы и неканоничные хвосты
        raise ValueError("неканоничная строка base64url")
    return raw
