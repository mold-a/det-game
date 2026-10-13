"""Точка входа: ``python -m engine <команда>``."""

import sys

# Консоль Windows (cp866/cp1251) не должна падать на кириллице — до любого вывода.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

import argparse  # noqa: E402
from pathlib import Path  # noqa: E402

from engine import DIST  # noqa: E402
from engine.serve import DEFAULT_PORT, serve  # noqa: E402

EXIT_NOT_IMPLEMENTED = 2

# Команда → шаг, в котором она появится (prompts/P0X-*.md).
PLANNED_STEP = {
    "build": "P03",
    "check": "P03",
    "dump-answers": "P03",
    "rotate-salts": "P03",
    "names": "P03",
    "vectors": "P02",
    "qr": "P07",
    "answers": "P07",
    "chatshot": "P07",
    "release": "P08",
    "import-cast": "P09",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m engine",
        description="Сборщик онлайн-части игры «За кулисами правды».",
    )
    sub = parser.add_subparsers(dest="command", metavar="<команда>", required=True)

    p = sub.add_parser("build", help="собрать dist/ из content/ и site/")
    p.add_argument("--release", action="store_true", help="сборка для выкладки")

    p = sub.add_parser("check", help="самопроверка: прохождение правильными ответами и leak scan")
    p.add_argument("--release", action="store_true", help="проверка сборки для выкладки")

    p = sub.add_parser("serve", help="локальный сервер dist/ на http://127.0.0.1:8000")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"порт (по умолчанию {DEFAULT_PORT})")

    sub.add_parser("qr", help="QR-коды для печати → print/qr/")
    sub.add_parser("answers", help="«Аварийный конверт» с ответами → print/answers.pdf")
    sub.add_parser("chatshot", help="«скриншоты» переписок для печати → print/chats/")
    sub.add_parser("names", help="таблица падежных форм всех персонажей")

    p = sub.add_parser("import-cast", help="имена из таблицы персонажей → content/characters.yaml")
    p.add_argument("xlsx", type=Path, help="путь к таблице .xlsx")

    sub.add_parser("release", help="build --release + check --release + архив dist")
    sub.add_parser("vectors", help="тестовые векторы криптографии → tests/vectors/crypto.json")
    sub.add_parser("dump-answers", help="ответы и варианты → tests/.answers.json для JS/e2e-тестов")

    p = sub.add_parser("rotate-salts", help="пересоздать соли и ключи страниц (после — перепечатать QR)")
    p.add_argument("--yes", action="store_true", help="подтверждение: старые QR-коды перестанут работать")

    return parser


def not_implemented(command: str) -> int:
    print(f"Будет реализовано в {PLANNED_STEP[command]} (команда «{command}»).")
    return EXIT_NOT_IMPLEMENTED


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        return serve(DIST, port=args.port)
    return not_implemented(args.command)


if __name__ == "__main__":
    sys.exit(main())
