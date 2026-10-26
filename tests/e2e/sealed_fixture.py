"""Фикстура для tests/e2e/sealed-media.spec.ts: боевой content/ и media/ (копии), сервер с кешированием как на хостинге.

Регресс 25.10: на mydetgame.ru закрытые медиа (фото «Кадра», видео 4-07, фото облака, витрина клуба) не
открывались у тех, кто заходил на сайт до последней выкладки. Файл `/m/<hash>.bin` называется по хешу исходника
и отдаётся с `Cache-Control: immutable`, а ключ и nonce у него новые в каждой сборке: браузер брал старую копию из
кеша, и она новым ключом не расшифровывалась. `python -m engine serve` отдаёт всё с `no-store` и этого не ловит,
поэтому здесь сервер берёт заголовки из `dist/_headers` — те же, что сборка пишет для хостингов.

    python tests/e2e/sealed_fixture.py <out>              # собрать (каждый вызов — новая сборка: новые ключи медиа)
    python tests/e2e/sealed_fixture.py <out> --serve PORT # раздавать <out>/dist (файлы читаются на каждый запрос)

Видео 4-07 подменяется коротким VP9 + Opus (ffmpeg): Chromium от Playwright не играет боевой H.264 + AAC.
"""

from __future__ import annotations

import fnmatch
import functools
import hashlib
import json
import shutil
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from pages_fixture import copy_content  # noqa: E402

from engine import salts as salts_mod  # noqa: E402
from engine.build import build  # noqa: E402
from engine.serve import DistRequestHandler  # noqa: E402
from engine.util import b64u_encode  # noqa: E402


def make(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    content = out / "content"
    if not content.is_dir():
        copy_content(out)
    media = out / "media"
    video_rel = yaml.safe_load((content / "pages/video/page.yaml").read_text(encoding="utf-8"))["video"]
    if not media.is_dir():
        shutil.copytree(ROOT / "media", media)
        dst = media / video_rel
        dst.unlink()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=2",
                        "-f", "lavfi", "-i", "sine=frequency=330:duration=2", "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p",
                        "-b:v", "150k", "-c:a", "libopus", "-b:a", "32k", "-movflags", "+faststart", "-shortest", str(dst)],
                       check=True)
    lock = out / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    build(content_dir=content, dist=out / "dist", media_dir=media, salts_path=lock, log=lambda *_: None)
    salts = salts_mod.read(lock)
    cloud = yaml.safe_load((content / "pages/cloud/page.yaml").read_text(encoding="utf-8"))
    photos = next(f for f in cloud["folders"] if f["kind"] == "photos")
    info = {
        "inna": f"/p/inna/#k={b64u_encode(salts.page_key('inna'))}",
        "video": f"/p/video/#k={b64u_encode(salts.page_key('video'))}",
        "video_sha256": hashlib.sha256((media / video_rel).read_bytes()).hexdigest(),
        # облако с двумя замками (locked: true): адрес с ключом страницы, как в QR записки
        "cloud": "/p/cloud/" + (f"#k={b64u_encode(salts.page_key('cloud'))}" if cloud.get("locked") is True else ""),
        "cloud_password": cloud["password"],
        "cloud_folder": photos["id"],
        "cloud_photos": len(photos["items"]),
    }
    (out / "info.json").write_text(json.dumps(info), encoding="utf-8")
    return info


def parse_headers(text: str) -> list[tuple[str, dict[str, str]]]:
    """Правила `_headers` (Netlify/Cloudflare): строка-путь, под ней «  Имя: значение»."""
    rules: list[tuple[str, dict[str, str]]] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            rules.append((line.strip(), {}))
        elif rules:
            name, _, value = line.strip().partition(":")
            rules[-1][1][name.strip()] = value.strip()
    return rules


class ProdLikeHandler(DistRequestHandler):
    """Как engine.serve (MIME, Range), но Cache-Control — по `dist/_headers`, как на хостинге."""

    def end_headers(self) -> None:
        path = self.path.split("?", 1)[0]
        rules = parse_headers((Path(self.directory) / "_headers").read_text(encoding="utf-8"))
        cache = "no-cache"
        for pattern, hdrs in rules:
            if "Cache-Control" in hdrs and (fnmatch.fnmatchcase(path, pattern) or path == pattern):
                cache = hdrs["Cache-Control"]
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", cache)
        SimpleHTTPRequestHandler.end_headers(self)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass


if __name__ == "__main__":
    out = Path(sys.argv[1])
    if "--serve" in sys.argv:
        port = int(sys.argv[sys.argv.index("--serve") + 1])
        handler = functools.partial(ProdLikeHandler, directory=str(out / "dist"))
        ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
    else:
        make(out)
