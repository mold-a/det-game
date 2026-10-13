"""Локальный статический сервер для dist/ (только для разработки и e2e-тестов)."""

from __future__ import annotations

import functools
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# Явная таблица: на Windows mimetypes берёт типы из реестра и бывает неправ
# (например, .js → text/plain), а Web Crypto/ES-модули к этому чувствительны.
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".mp4": "video/mp4",
    ".mp3": "audio/mpeg",
    ".woff2": "font/woff2",
    ".bin": "application/octet-stream",
}


# Один диапазон: bytes=a-b, bytes=a-, bytes=-n (RFC 9110 §14). Несколько диапазонов и другие
# единицы не поддерживаются — такой заголовок игнорируется, отдаётся весь файл (это разрешено RFC).
_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


class _Limited:
    """Файл, из которого читается не больше ``left`` байт (тело ответа 206)."""

    def __init__(self, f, left: int) -> None:
        self.f = f
        self.left = left

    def read(self, n: int = -1) -> bytes:
        if self.left <= 0:
            return b""
        n = self.left if n is None or n < 0 else min(n, self.left)
        data = self.f.read(n)
        self.left -= len(data)
        return data

    def close(self) -> None:
        self.f.close()


class DistRequestHandler(SimpleHTTPRequestHandler):
    """Раздаёт файлы с правильными MIME-типами, без кеширования и с HTTP Range
    (206 Partial Content): без него iOS Safari не проигрывает аудио и видео."""

    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, **MIME_TYPES}

    def guess_type(self, path):  # type: ignore[override]
        suffix = Path(str(path)).suffix.lower()
        if suffix in MIME_TYPES:
            return MIME_TYPES[suffix]
        return super().guess_type(path)

    def send_head(self):  # type: ignore[override]
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        m = _RANGE.match(rng.strip()) if rng else None
        if m is None or os.path.isdir(path) or self.path.split("?", 1)[0].endswith("/") or m.group(1) == m.group(2) == "":
            return super().send_head()
        try:
            f = open(path, "rb")  # noqa: SIM115 — закрывает copyfile/do_HEAD
        except OSError:
            self.send_error(404, "File not found")
            return None
        size = os.fstat(f.fileno()).st_size
        first, last = m.group(1), m.group(2)
        if first == "":  # суффикс: последние n байт
            n = int(last)
            start, end = max(0, size - n), size - 1
            bad = n == 0
        else:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
            bad = bool(last) and int(last) < start
        if bad or start >= size or size == 0:
            f.close()
            self.send_response(416, "Range Not Satisfiable")
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        length = end - start + 1
        self.send_response(206, "Partial Content")
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(length))
        self.send_header("Last-Modified", self.date_time_string(int(os.fstat(f.fileno()).st_mtime)))
        self.end_headers()
        f.seek(start)
        return _Limited(f, length)

    def end_headers(self) -> None:
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        sys.stderr.write(f"{self.address_string()} {format % args}\n")


def make_server(directory: Path, port: int = DEFAULT_PORT, host: str = DEFAULT_HOST) -> ThreadingHTTPServer:
    """Создаёт (но не запускает) сервер для ``directory``. ``port=0`` — любой свободный."""
    handler = functools.partial(DistRequestHandler, directory=str(Path(directory)))
    return ThreadingHTTPServer((host, port), handler)


def serve(directory: Path, port: int = DEFAULT_PORT, host: str = DEFAULT_HOST) -> int:
    """Запускает сервер до Ctrl+C. Возвращает код выхода."""
    directory = Path(directory)
    if not directory.is_dir():
        problem = f"папка {directory} не найдена"
    elif not (directory / "index.html").is_file():
        problem = f"в {directory} нет index.html"
    else:
        problem = None
    if problem:
        print(
            f"Нечего раздавать: {problem}.\n"
            "Сначала соберите сайт: python -m engine build",
            file=sys.stderr,
        )
        return 1
    try:
        httpd = make_server(directory, port, host)
    except OSError as exc:
        print(f"Не удалось занять порт {port} на {host}: {exc}.\n"
              "Укажите другой: python -m engine serve --port 8001", file=sys.stderr)
        return 1
    real_port = httpd.server_address[1]
    print(f"Раздаю {directory} на http://{host}:{real_port}/ (остановить — Ctrl+C)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
    finally:
        httpd.server_close()
    return 0
