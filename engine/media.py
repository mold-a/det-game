"""Медиа по docs/02 §4а и FORMATS §5.

Сначала план (``MediaPlan``): все ссылки на медиа из контента (``content.media_refs``)
с контекстом, и для каждого файла решение — открытый или зашифрованный:

- портреты (``characters[].photo``) — всегда открытые (решение 5);
- иначе открытый, если на файл ссылается хоть одна открытая страница;
- иначе зашифрованный: ``/m/<hash>.bin`` = ``nonce ‖ ct ‖ tag``, ``aad = "media/<hash>"``,
  случайный ключ на сборку (решение 6), ключ — внутри ссылающегося зашифрованного объекта.

Отсутствующий файл — ``{"src": null, "missing": true, …}`` и предупреждение (F11);
файлов-плейсхолдеров в ``dist/`` нет. В ``--release`` это ошибка (решает build).
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from markupsafe import Markup, escape

from engine import ROOT, crypto
from engine.content import Content, MediaUse, media_refs
from engine.models import MEDIA_MIME

MEDIA_DIR = ROOT / "media"
HASH_HEX = 32  # первые 32 hex-символа sha256 исходного файла (FORMATS §5)

# Видео: технический предел для телефона, не сюжетный параметр. Зашифрованное видео браузер скачивает целиком
# и расшифровывает в памяти (файл + расшифрованная копия + Blob), поэтому на закрытых страницах оно ограничено;
# открытое играет потоком (HTTP Range) и такого предела не имеет, но вес всё равно стоит держать в рамках.
MAX_SEALED_VIDEO_BYTES = 25 * 1024 * 1024
WARN_VIDEO_BYTES = 15 * 1024 * 1024

_PLACEHOLDER_ALT = {"image": "Здесь будет фото", "audio": "Здесь будет аудиозапись", "video": "Здесь будет видео"}


def media_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:HASH_HEX]


@dataclass
class MediaFile:
    rel: str
    mime: str
    uses: list[MediaUse] = field(default_factory=list)
    exists: bool = False
    hash: str | None = None
    encrypted: bool = False
    key: bytes | None = None
    size: int | None = None  # размер в dist/

    @property
    def open_context(self) -> bool:
        return any(u.context in ("portrait", "open") for u in self.uses)

    @property
    def out_name(self) -> str | None:
        if not self.exists:
            return None
        return f"{self.hash}.bin" if self.encrypted else f"{self.hash}{Path(self.rel).suffix.lower()}"


class MediaPlan:
    def __init__(self, content: Content, media_dir: Path = MEDIA_DIR) -> None:
        self.media_dir = Path(media_dir)
        self.files: dict[str, MediaFile] = {}
        for use in media_refs(content.characters, content.pages, content.docs):
            mf = self.files.get(use.path)
            if mf is None:
                mf = MediaFile(use.path, MEDIA_MIME[Path(use.path).suffix.lower()])
                self.files[use.path] = mf
            mf.uses.append(use)
        data_by_hash: dict[str, bytes] = {}
        for mf in self.files.values():
            src = self.media_dir / mf.rel
            mf.exists = src.is_file()
            if not mf.exists:
                continue
            data = src.read_bytes()
            mf.hash = media_hash(data)
            data_by_hash[mf.hash] = data
        # Одинаковое содержимое под разными путями — один файл в dist/m/: открытый, если открыт хоть один из
        # путей, иначе зашифрованный с одним общим ключом (иначе второй файл затёр бы первый вместе с его ключом).
        keys: dict[str, bytes] = {}
        open_hashes = {mf.hash for mf in self.files.values() if mf.exists and mf.open_context}
        for mf in self.files.values():
            if not mf.exists:
                continue
            mf.encrypted = mf.hash not in open_hashes
            if mf.encrypted:
                mf.key = keys.setdefault(mf.hash, secrets.token_bytes(crypto.KEY_LEN))
                mf.size = crypto.NONCE_LEN + len(data_by_hash[mf.hash]) + crypto.TAG_LEN
            else:
                mf.size = len(data_by_hash[mf.hash])

    def size_problems(self) -> tuple[list[str], list[str]]:
        """(ошибки, предупреждения) по размеру видео: зашифрованное > MAX_SEALED_VIDEO_BYTES — ошибка."""
        errors: list[str] = []
        warns: list[str] = []
        for mf in self.files.values():
            if not mf.exists or mf.mime != "video/mp4":
                continue
            raw = (self.media_dir / mf.rel).stat().st_size
            mb = raw / 1024 / 1024
            where = ", ".join(f"{u.file} → {u.loc}" for u in mf.uses[:2])
            if mf.encrypted and raw > MAX_SEALED_VIDEO_BYTES:
                errors.append(
                    f"видео media/{mf.rel} — {mb:.1f} МБ, а на закрытых страницах видео не больше "
                    f"{MAX_SEALED_VIDEO_BYTES // 1024 // 1024} МБ (браузер расшифровывает его целиком в памяти): "
                    f"пережмите (H.264, 720p, ~1,5 Мбит/с) или сделайте страницу открытой ({where})")
            elif raw > WARN_VIDEO_BYTES:
                warns.append(f"видео media/{mf.rel} — {mb:.1f} МБ: для телефона лучше до "
                             f"{WARN_VIDEO_BYTES // 1024 // 1024} МБ (H.264 + AAC, ~1,5 Мбит/с)")
        return errors, warns

    @property
    def missing(self) -> list[MediaFile]:
        return [mf for mf in self.files.values() if not mf.exists]

    def ref(self, rel: str, alt: str = "") -> dict[str, Any]:
        """``MediaRef`` (FORMATS §5) для файла из плана."""
        mf = self.files.get(rel)
        if mf is None:
            raise KeyError(f"медиа «{rel}» нет в плане (content.media_refs его не нашёл)")
        if not mf.exists:
            kind = mf.mime.split("/")[0]
            return {"src": None, "missing": True, "mime": mf.mime, "alt": alt or _PLACEHOLDER_ALT.get(kind, "")}
        ref: dict[str, Any] = {"src": f"/m/{mf.out_name}", "mime": mf.mime, "size": mf.size}
        if mf.encrypted:
            ref["key"] = crypto.b64u_encode(mf.key)
            ref["aad"] = f"media/{mf.hash}"
        ref["alt"] = alt
        return ref

    def emit(self, dist: Path) -> list[Path]:
        """Записать файлы в ``dist/m/``: открытые — копией, остальные — зашифрованными."""
        out: list[Path] = []
        mdir = Path(dist) / "m"
        done: set[str] = set()
        for mf in self.files.values():
            if not mf.exists or mf.out_name in done:
                continue
            done.add(mf.out_name)
            mdir.mkdir(parents=True, exist_ok=True)
            data = (self.media_dir / mf.rel).read_bytes()
            if mf.encrypted:
                data = crypto.seal_media(mf.key, data, f"media/{mf.hash}")
            p = mdir / mf.out_name
            p.write_bytes(data)
            out.append(p)
        return out


class MediaCollector:
    """Хелпер ``media(rel, alt)`` для шаблонов фрагментов и бланков (FORMATS §6.1).

    ``mode="open"`` — прямой ``src`` (открытая страница); ``mode="sealed"`` — ``data-media="<i>"``
    с индексом в ``refs`` (зашифрованные объекты). Отсутствующий файл — ``data-missing="1"``.
    """

    def __init__(self, plan: MediaPlan, mode: str) -> None:
        if mode not in ("open", "sealed"):
            raise ValueError(mode)
        self.plan = plan
        self.mode = mode
        self.refs: list[dict] = []
        self._index: dict[str, int] = {}

    def __call__(self, rel: str | None, alt: str = "") -> Markup:
        if not rel:
            return Markup('data-missing="1" data-alt=""')
        ref = self.plan.ref(rel, alt)
        if ref["src"] is None:
            return Markup(f'data-missing="1" data-mime="{escape(ref["mime"])}" data-alt="{escape(ref["alt"])}"')
        if self.mode == "open":
            if "key" in ref:
                raise ValueError(f"зашифрованное медиа «{rel}» на открытой странице")
            return Markup(f'src="{escape(ref["src"])}" data-mime="{escape(ref["mime"])}"')
        if rel not in self._index:
            self._index[rel] = len(self.refs)
            self.refs.append(ref)
        return Markup(f'data-media="{self._index[rel]}" data-mime="{escape(ref["mime"])}"')
