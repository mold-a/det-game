"""Локальный статический сервер для dist/ (только для разработки и e2e-тестов)."""

from __future__ import annotations

import functools
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


class DistRequestHandler(SimpleHTTPRequestHandler):
    """Раздаёт файлы с правильными MIME-типами и без кеширования."""

    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, **MIME_TYPES}

    def guess_type(self, path):  # type: ignore[override]
        suffix = Path(str(path)).suffix.lower()
        if suffix in MIME_TYPES:
            return MIME_TYPES[suffix]
        return super().guess_type(path)

    def end_headers(self) -> None:
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
