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
    if args.command == "vectors":
        from engine.vectors import make_crypto_vectors  # лениво: --help без cryptography

        print(f"Векторы криптографии записаны: {make_crypto_vectors()}")
        return 0
    if args.command == "names":
        return cmd_names()
    if args.command == "rotate-salts":
        return cmd_rotate_salts(args.yes)
    if args.command == "build":
        return cmd_build(args.release)
    if args.command == "check":
        return cmd_check(args.release)
    if args.command == "dump-answers":
        return cmd_dump_answers()
    if args.command == "qr":
        return cmd_qr()
    if args.command == "chatshot":
        return cmd_chatshot()
    if args.command == "answers":
        return cmd_answers()
    if args.command == "release":
        return cmd_release()
    return not_implemented(args.command)


EXIT_CONTENT_ERROR = 1
EXIT_REFUSED = 2


def _load_content_or_report():
    """Загрузить content/; при ошибках — напечатать их в stderr и вернуть None."""
    from engine.content import ContentError, load_content

    try:
        return load_content()
    except ContentError as e:
        print(e.report(), file=sys.stderr)
        return None


def cmd_names() -> int:
    from engine.names import format_names_table

    content = _load_content_or_report()
    if content is None:
        return EXIT_CONTENT_ERROR
    print(format_names_table(content.characters))
    return 0


def cmd_rotate_salts(yes: bool) -> int:
    from engine import salts

    if not yes:
        print(
            "Отказ: rotate-salts пересоздаёт ВСЕ соли и ключи закрытых страниц.\n"
            "Старые QR-коды перестанут открывать страницы, сохранённый прогресс игроков станет несовместим.\n"
            "Если это действительно нужно: python -m engine rotate-salts --yes",
            file=sys.stderr,
        )
        return EXIT_REFUSED
    content = _load_content_or_report()
    if content is None:
        return EXIT_CONTENT_ERROR
    new = salts.rotate_for_content(content, salts.SALTS_LOCK, confirm=True)
    pages = ", ".join(sorted(new.data["pages"])) or "—"
    print(f"Соли и ключи страниц пересозданы: {new.path} (saltsId {new.id[:12]}…).")
    print(
        f"ВНИМАНИЕ: перепечатайте QR-коды закрытых страниц ({pages}) — python -m engine qr; "
        "старые коды больше не работают. Пересоберите сайт: python -m engine build."
    )
    return 0



def _guarded(fn):
    """Ошибки контента и сборки — понятный текст в stderr и код 1, без трассировки."""
    from engine.build import BuildError
    from engine.content import ContentError
    from engine.salts import SaltsError

    try:
        return fn()
    except ContentError as e:
        print(e.report(), file=sys.stderr)
    except (BuildError, SaltsError) as e:
        print(str(e), file=sys.stderr)
    return EXIT_CONTENT_ERROR


def cmd_build(release: bool) -> int:
    from engine.build import build, format_report

    def run() -> int:
        print(format_report(build(release=release)))
        return 0

    return _guarded(run)


def cmd_check(release: bool) -> int:
    from engine.check import check

    def run() -> int:
        rep = check(release=release, log=print)
        print("check: OK" if rep.ok else "check: FAIL", file=sys.stdout if rep.ok else sys.stderr)
        return 0 if rep.ok else 1

    return _guarded(run)


def cmd_dump_answers() -> int:
    from engine.dump import dump_answers

    def run() -> int:
        print(f"Ответы для тестов записаны: {dump_answers()} (файл в .gitignore, не коммитить)")
        return 0

    return _guarded(run)



def _guarded_print(fn):
    """Как _guarded, плюс «нет браузера» → понятный текст и код 1."""
    from engine.printing import PrintError

    def run() -> int:
        try:
            return fn()
        except PrintError as e:
            print(f"Печать невозможна: {e}", file=sys.stderr)
            return EXIT_CONTENT_ERROR

    return _guarded(run)


def cmd_qr() -> int:
    from engine.qr import run as qr_run

    def run() -> int:
        rep = qr_run()
        for c in rep.cards:
            mark = {True: "проверен", False: "НЕ СОВПАЛ", None: "не проверен"}[c.verified]
            print(f"  {c.slug:<8} {c.access:<8} {mark:<11} {c.url}")
        print(f"QR-коды: {rep.cards[0].png.parent if rep.cards else ''}; лист: {rep.sheet}")
        for w in rep.warnings:
            print(f"ВНИМАНИЕ: {w}", file=sys.stderr)
        return 1 if any(c.verified is False for c in rep.cards) else 0

    return _guarded_print(run)


def cmd_chatshot() -> int:
    from engine.chatshot import run as chat_run

    def run() -> int:
        paths = chat_run()
        for p in paths:
            print(f"  {p}")
        print(f"Скриншоты переписок: {len(paths)} PNG 1080×2340")
        return 0

    return _guarded_print(run)


def cmd_answers() -> int:
    from engine.emergency import run as answers_run

    def run() -> int:
        print(f"Аварийный конверт: {answers_run()} (содержит ответы — не публиковать)")
        return 0

    return _guarded_print(run)



def cmd_release() -> int:
    from engine.release import ReleaseError, release

    def run() -> int:
        try:
            rep = release()
        except ReleaseError as e:
            print(str(e), file=sys.stderr)
            return EXIT_CONTENT_ERROR
        print(rep.check.table())
        size = rep.archive.stat().st_size / 1024 / 1024
        print(f"Релиз готов: {rep.archive} ({size:.1f} МБ), buildId {rep.build_id}.")
        print("Выкладка — docs/DEPLOY.md; перед игрой — docs/CHECKLIST.md.")
        return 0

    return _guarded(run)


if __name__ == "__main__":
    sys.exit(main())
