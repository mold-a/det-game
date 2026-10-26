"""Фикстурная сборка для tests/e2e/photos.spec.ts: копия content/ + тестовые страницы + фото-фикстуры
(tests/pages_fixture.add_photo_fixtures: блоки photo на сайте театра, папка облака kind: photos, photos в lab.yaml,
подпись к фото статьи) и настоящие jpeg (ffmpeg, тестовые картинки 1200x800). Результат — <out>/dist,
адреса и пароль облака — <out>/info.json.

    python tests/e2e/photos_fixture.py <out>               # собрать
    python tests/e2e/photos_fixture.py <out> --serve PORT  # собрать (если нет) и раздавать dist/ (до остановки)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from pages_fixture import PHOTO_FILES, add_fixture_pages, add_photo_fixtures, copy_content  # noqa: E402

from engine.build import build  # noqa: E402

PATTERNS = ["testsrc", "testsrc2", "smptebars", "rgbtestsrc", "yuvtestsrc", "pal75bars", "testsrc", "testsrc2"]


def make(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    src = os.environ.get("PHOTOS_CONTENT_SRC")  # необязательно: другая копия content/
    content = copy_content(out, Path(src) if src else None)
    add_fixture_pages(content)
    add_photo_fixtures(content)
    media = out / "media"
    files = [rel for rels in PHOTO_FILES.values() for rel in rels]
    for i, rel in enumerate(files):
        dst = media / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        pattern = PATTERNS[i % len(PATTERNS)]
        # Разные картинки: одинаковое содержимое сборщик склеил бы в один файл (открытый, если открыт хоть один путь).
        size = "1200x800" if i % 2 == 0 else "900x1200"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"{pattern}=size={size}:rate=1",
                        "-vf", f"hue=h={i * 31}", "-frames:v", "1", "-q:v", "6", str(dst)], check=True)
    lock = out / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    build(content_dir=content, dist=out / "dist", media_dir=media, salts_path=lock, log=lambda *_: None)
    cloud = yaml.safe_load((content / "pages/cloud/page.yaml").read_text(encoding="utf-8"))
    # облако с двумя замками (locked: true): адрес с ключом страницы, как в QR записки
    cloud_url = "/p/cloud/"
    if cloud.get("locked") is True:
        from engine import salts as salts_mod
        from engine.util import b64u_encode

        cloud_url += "#k=" + b64u_encode(salts_mod.read(lock).page_key("cloud"))
    info = {"site": "/p/theater/", "lab": "/lab/", "cloud": cloud_url, "cloud_password": cloud["password"],
            "news": "/p/news/", "folder": "gallery"}
    (out / "info.json").write_text(json.dumps(info), encoding="utf-8")
    return info


if __name__ == "__main__":
    out = Path(sys.argv[1])
    if "--serve" not in sys.argv or not (out / "info.json").is_file():
        make(out)
    if "--serve" in sys.argv:
        from engine.serve import serve

        sys.exit(serve(out / "dist", port=int(sys.argv[sys.argv.index("--serve") + 1])))
