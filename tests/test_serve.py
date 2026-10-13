import threading
import urllib.error
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


# ---------------------------------------------------------------- HTTP Range (iOS Safari: аудио и видео)


def _get(url: str, rng: str | None = None):
    req = urllib.request.Request(url, headers={"Range": rng} if rng else {})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


BIN = bytes(range(32))


def test_full_response_advertises_ranges(server):
    status, headers, body = _get(f"{server}/m/abc.bin")
    assert status == 200 and body == BIN
    assert headers["Accept-Ranges"] == "bytes"
    assert headers["Content-Length"] == "32"


@pytest.mark.parametrize("rng, start, end", [
    ("bytes=0-0", 0, 0),
    ("bytes=2-9", 2, 9),
    ("bytes=30-", 30, 31),
    ("bytes=10-1000", 10, 31),  # конец за пределами файла — обрезается
    ("bytes=-5", 27, 31),  # суффикс
    ("bytes=-100", 0, 31),  # суффикс длиннее файла — весь файл
])
def test_range_partial_content(server, rng, start, end):
    status, headers, body = _get(f"{server}/m/abc.bin", rng)
    assert status == 206
    assert body == BIN[start:end + 1]
    assert headers["Content-Range"] == f"bytes {start}-{end}/32"
    assert headers["Content-Length"] == str(end - start + 1)
    assert headers.get_content_type() == "application/octet-stream"
    assert headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("rng", ["bytes=32-", "bytes=100-200", "bytes=9-2", "bytes=-0"])
def test_range_not_satisfiable(server, rng):
    status, headers, body = _get(f"{server}/m/abc.bin", rng)
    assert status == 416
    assert headers["Content-Range"] == "bytes */32"
    assert body == b""


@pytest.mark.parametrize("rng", ["bytes=0-1,4-5", "items=0-1", "bytes=-", "garbage"])
def test_unsupported_range_ignored(server, rng):
    status, _, body = _get(f"{server}/m/abc.bin", rng)
    assert status == 200 and body == BIN


def test_range_on_media_type_and_missing_file(server):
    status, headers, body = _get(f"{server}/m/a.mp4", "bytes=0-")
    assert status == 206 and headers.get_content_type() == "video/mp4" and body == b"\x00"
    status, _, _ = _get(f"{server}/m/nope.mp4", "bytes=0-1")
    assert status == 404
