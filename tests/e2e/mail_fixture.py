"""Фикстурная сборка для tests/e2e/mail.spec.ts: копия content/ + почтовый ящик ``mail-sample``
(tests/pages_fixture.add_mail_fixture: три цепочки, вложения) и настоящий jpeg вложения (ffmpeg); остальных
медиа в сборке нет (заглушки). Результат —
<out>/dist, адрес ящика с ключом — <out>/info.json.

    python tests/e2e/mail_fixture.py <out>               # собрать
    python tests/e2e/mail_fixture.py <out> --serve PORT  # собрать (если нет) и раздавать dist/ (до остановки)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from pages_fixture import MAIL_FILES, MAIL_SLUG, add_mail_fixture, copy_content  # noqa: E402

from engine import salts as salts_mod  # noqa: E402
from engine.build import build  # noqa: E402
from engine.util import b64u_encode  # noqa: E402


def make(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    src = os.environ.get("MAIL_CONTENT_SRC")  # необязательно: другая копия content/
    content = copy_content(out, Path(src) if src else None)
    add_mail_fixture(content)
    media = out / "media"
    for rel in MAIL_FILES:
        dst = media / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=1200x800:rate=1",
                        "-frames:v", "1", "-q:v", "6", str(dst)], check=True)
    lock = out / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    build(content_dir=content, dist=out / "dist", media_dir=media, salts_path=lock, log=lambda *_: None)
    key = b64u_encode(salts_mod.read(lock).page_key(MAIL_SLUG))
    info = {"mail": f"/p/{MAIL_SLUG}/#k={key}"}
    (out / "info.json").write_text(json.dumps(info), encoding="utf-8")
    return info


if __name__ == "__main__":
    out = Path(sys.argv[1])
    if "--serve" not in sys.argv or not (out / "info.json").is_file():
        make(out)
    if "--serve" in sys.argv:
        from engine.serve import serve

        sys.exit(serve(out / "dist", port=int(sys.argv[sys.argv.index("--serve") + 1])))
