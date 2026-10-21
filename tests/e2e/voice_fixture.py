"""Фикстурная сборка для tests/e2e/voice.spec.ts: копия content/ + тестовые страницы (krug-actor, krug-closed)
с голосовыми сообщениями и настоящими mp3 (ffmpeg, 2 с тона). Результат — <out>/dist, ключи — <out>/info.json.

    python tests/e2e/voice_fixture.py <out>          # собрать
    python tests/e2e/voice_fixture.py <out> --serve PORT  # собрать (если нет) и раздавать dist/ (до остановки)
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

from pages_fixture import add_fixture_pages, copy_content  # noqa: E402

from engine import salts as salts_mod  # noqa: E402
from engine.build import build  # noqa: E402
from engine.util import b64u_encode  # noqa: E402


def make(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    src = os.environ.get("VOICE_CONTENT_SRC")  # необязательно: другая копия content/ (например, из git archive)
    content = copy_content(out, Path(src) if src else None)
    add_fixture_pages(content)
    media = out / "media"
    for rel in ("krug-actor/voice-01.mp3", "krug-closed/voice-01.mp3"):
        dst = media / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                        "-ac", "1", "-b:a", "32k", str(dst)], check=True)
    lock = out / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    build(content_dir=content, dist=out / "dist", media_dir=media, salts_path=lock, log=lambda *_: None)
    key = b64u_encode(salts_mod.read(lock).page_key("krug-closed"))
    info = {"open": "/p/krug-actor/", "closed": f"/p/krug-closed/#k={key}"}
    (out / "info.json").write_text(json.dumps(info), encoding="utf-8")
    return info


if __name__ == "__main__":
    out = Path(sys.argv[1])
    if "--serve" not in sys.argv or not (out / "info.json").is_file():
        make(out)
    if "--serve" in sys.argv:
        from engine.serve import serve

        sys.exit(serve(out / "dist", port=int(sys.argv[sys.argv.index("--serve") + 1])))
