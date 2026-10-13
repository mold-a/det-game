"""Соли и постоянные ключи — ``engine/salts.lock.json`` (docs/02 §3.2).

Файл создаётся при первом обращении, при новых единицах, этапах и закрытых
страницах дописывается и **никогда** не пересоздаётся автоматически: ключи
страниц напечатаны в QR-кодах. Удалённая единица оставляет свою соль. Пересоздать
всё — только ``rotate(..., confirm=True)`` (``python -m engine rotate-salts --yes``).

Формат (значения — base64url без «=»):

    {"version": 1,
     "units":  {"s1.q1.time": <16 байт>, …},
     "stages": {"1": <16 байт>, …},
     "start":  <16 байт>,
     "cloud":  <16 байт>,
     "pages":  {"inna": <32 байта>, …}}

Файл пишется в каноническом виде (сортировка ключей, отступ 2, ``\\n``) и только
при изменениях. ``saltsId`` — SHA-256 от канонического JSON без пробелов.
"""

from __future__ import annotations

import copy
import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from engine import ROOT
from engine.util import b64u_decode, b64u_encode, canonical_json, pretty_json, read_text, sha256_hex, write_text

SALTS_LOCK = ROOT / "engine" / "salts.lock.json"
FORMAT_VERSION = 1
SALT_BYTES = 16  # соли единиц, этапов, старта и облака (docs/02 §3.2)
PAGE_KEY_BYTES = 32  # ключи закрытых страниц (AES-256)

_MAPS = ("units", "stages", "pages")
_SINGLES = ("start", "cloud")


class SaltsError(Exception):
    """Файл солей повреждён или операция не подтверждена. Файл при этом не трогается."""


def _new(n: int) -> str:
    return b64u_encode(secrets.token_bytes(n))


def salts_id(data: dict) -> str:
    """SHA-256 канонического JSON (сортировка ключей, без пробелов, UTF-8) — ``saltsId`` в public.json."""
    return sha256_hex(canonical_json(data))


@dataclass(frozen=True)
class Salts:
    data: dict
    path: Path | None = None

    def _get(self, section: str, key: str) -> bytes:
        try:
            return b64u_decode(self.data[section][key])
        except KeyError:
            raise KeyError(f"нет записи {section}[{key!r}] в {self.path or 'salts.lock.json'}") from None

    def unit(self, path: str) -> bytes:
        return self._get("units", path)

    def stage(self, n: int) -> bytes:
        return self._get("stages", str(n))

    def page_key(self, slug: str) -> bytes:
        return self._get("pages", slug)

    @property
    def start(self) -> bytes:
        return b64u_decode(self.data["start"])

    @property
    def cloud(self) -> bytes:
        return b64u_decode(self.data["cloud"])

    @property
    def id(self) -> str:
        return salts_id(self.data)


def requirements(content: Any) -> tuple[list[str], list[int], list[str]]:
    """Что должно быть в файле солей для данного контента: единицы, этапы, закрытые страницы."""
    from engine.content import units as content_units

    unit_paths = [u.path for u in content_units(content)]
    stage_ns = [s.n for s in content.stages]
    locked_pages = [slug for slug, p in content.pages.items() if p.locked is True]
    return unit_paths, stage_ns, locked_pages


def _validate(data: Any, path: Path) -> dict:
    where = str(path)
    if not isinstance(data, dict):
        raise SaltsError(f"{where}: ожидается объект JSON")
    if data.get("version") != FORMAT_VERSION:
        raise SaltsError(f"{where}: version должен быть {FORMAT_VERSION}, а не {data.get('version')!r}")
    extra = set(data) - {"version", *_MAPS, *_SINGLES}
    if extra:
        raise SaltsError(f"{where}: неизвестные ключи {sorted(extra)}")

    def check(value: Any, size: int, loc: str) -> None:
        try:
            raw = b64u_decode(value)
        except (ValueError, TypeError):
            raise SaltsError(f"{where}: {loc}: не base64url без «=»") from None
        if len(raw) != size:
            raise SaltsError(f"{where}: {loc}: ожидается {size} байт, а не {len(raw)}")

    for section in _MAPS:
        sec = data.get(section, {})
        if not isinstance(sec, dict):
            raise SaltsError(f"{where}: {section}: ожидается объект")
        size = PAGE_KEY_BYTES if section == "pages" else SALT_BYTES
        for k, v in sec.items():
            check(v, size, f"{section}[{k!r}]")
    for single in _SINGLES:
        if single in data:
            check(data[single], SALT_BYTES, single)
    return data


def read(path: Path = SALTS_LOCK) -> Salts | None:
    """Прочитать файл солей без изменений; ``None``, если файла нет."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as e:
        raise SaltsError(f"{path}: неверный JSON: {e}") from None
    return Salts(_validate(data, path), path)


def _write(path: Path, data: dict) -> None:
    write_text(path, pretty_json(data))


def _fill(data: dict, units: Iterable[str], stages: Iterable[int], pages: Iterable[str]) -> dict:
    """Дописать недостающее; существующие значения не трогаются."""
    out = copy.deepcopy(data)
    out["version"] = FORMAT_VERSION
    for section in _MAPS:
        out.setdefault(section, {})
    for u in units:
        out["units"].setdefault(u, _new(SALT_BYTES))
    for n in stages:
        out["stages"].setdefault(str(n), _new(SALT_BYTES))
    for slug in pages:
        out["pages"].setdefault(slug, _new(PAGE_KEY_BYTES))
    for single in _SINGLES:
        out.setdefault(single, _new(SALT_BYTES))
    return out


def load_or_init(path: Path = SALTS_LOCK, *, units: Iterable[str], stages: Iterable[int],
                 pages: Iterable[str]) -> Salts:
    """Прочитать (или создать) файл солей и дописать недостающее. Ничего не удаляет и не меняет."""
    path = Path(path)
    current = read(path)
    before = current.data if current else {}
    after = _fill(before, units, stages, pages)
    if after != before:
        _write(path, after)
    return Salts(after, path)


def ensure_for_content(content: Any, path: Path = SALTS_LOCK) -> Salts:
    u, s, p = requirements(content)
    return load_or_init(path, units=u, stages=s, pages=p)


def rotate(path: Path = SALTS_LOCK, *, units: Iterable[str], stages: Iterable[int], pages: Iterable[str],
           confirm: bool = False) -> Salts:
    """Пересоздать ВСЕ соли и ключи страниц. Старые QR-коды перестанут работать."""
    if not confirm:
        raise SaltsError("пересоздание солей не подтверждено (нужно confirm=True / --yes)")
    data = _fill({}, units, stages, pages)
    _write(Path(path), data)
    return Salts(data, Path(path))


def rotate_for_content(content: Any, path: Path = SALTS_LOCK, *, confirm: bool = False) -> Salts:
    u, s, p = requirements(content)
    return rotate(path, units=u, stages=s, pages=p, confirm=confirm)
