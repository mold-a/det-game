import threading
import urllib.request
from pathlib import Path

import pytest

from engine.serve import make_server, serve

FILES = {
    "index.html": ("<!doctype html><title>Тест</title>".encode("utf-8"), "text/html"),
    "data/public.json": (b'{"ok": true}', "application/json"),
    "m/abc.bin": (bytes(range(32)), "application/octet-stream"),
    "assets/fonts/x.woff2": (b"wOF2fake", "font/woff2"),
    "m/a.mp4": (b"\x00", "video/mp4"),
    "m/a.mp3": (b"\x00", "audio/mpeg"),
    "m/a.webp": (b"\x00", "image/webp"),
    "assets/i.svg": (b"<svg xmlns='http://www.w3.org/2000/svg'/>", "image/svg+xml"),
    "assets/js/a.js": (b"export {};", "text/javascript"),
}


@pytest.fixture()
def server(tmp_path: Path):
    for rel, (body, _) in FILES.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    httpd = make_server(tmp_path, port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    yield f"http://{host}:{port}"
    httpd.shutdown()
    httpd.server_close()


@pytest.mark.parametrize("rel", sorted(FILES))
def test_mime_and_no_store(server, rel):
    body, mime = FILES[rel]
    with urllib.request.urlopen(f"{server}/{rel}") as resp:
        assert resp.status == 200
        assert resp.headers.get_content_type() == mime
        assert resp.headers["Cache-Control"] == "no-store"
        assert resp.read() == body


def test_root_serves_index(server):
    with urllib.request.urlopen(f"{server}/") as resp:
        assert resp.headers.get_content_type() == "text/html"
        assert resp.headers.get_content_charset() == "utf-8"
        assert "Тест" in resp.read().decode("utf-8")


def test_serve_without_dist(tmp_path, capsys):
    assert serve(tmp_path / "dist", port=0) == 1
    assert "python -m engine build" in capsys.readouterr().err
