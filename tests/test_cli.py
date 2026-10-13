import os
import subprocess
import sys


from engine import ROOT
from engine.__main__ import PLANNED_STEP

ALL_COMMANDS = sorted([*PLANNED_STEP, "serve"])


def run_engine(*args: str, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [sys.executable, "-m", "engine", *args],
        cwd=ROOT,
        capture_output=True,
        env=env,
        timeout=60,
    )


def test_help_lists_all_commands():
    res = run_engine("--help")
    assert res.returncode == 0
    out = res.stdout.decode("utf-8")
    for command in ALL_COMMANDS:
        assert command in out, command


def test_expected_command_set():
    assert set(ALL_COMMANDS) == {
        "build", "check", "serve", "qr", "answers", "names", "vectors",
        "rotate-salts", "chatshot", "import-cast", "release", "dump-answers",
    }


def test_all_commands_implemented():
    # import-cast реализована в P09 (tests/test_importcast.py) — заглушек не осталось.
    res = run_engine("import-cast", "--help")
    assert res.returncode == 0
    assert "--write" in res.stdout.decode("utf-8")


def test_cyrillic_output_survives_non_utf8_console():
    # Имитация консоли Windows с однобайтовой кодировкой: reconfigure в __main__
    # должен переключить вывод на UTF-8, а не упасть с UnicodeEncodeError.
    res = run_engine("import-cast", "нет-такого.xlsx",
                     env_extra={"PYTHONIOENCODING": "ascii", "PYTHONUTF8": "0"})
    assert res.returncode == 1, res.stderr.decode("utf-8", "replace")
    assert "Таблица: нет-такого.xlsx" in res.stdout.decode("utf-8")
    assert "файл не найден" in res.stderr.decode("utf-8")
    assert b"UnicodeEncodeError" not in res.stderr
