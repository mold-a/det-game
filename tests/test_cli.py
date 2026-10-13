import os
import subprocess
import sys

import pytest

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


@pytest.mark.parametrize(
    "args",
    # vectors реализована в P02 (tests/test_crypto.py)
    # names и rotate-salts реализованы в P03 (tests/test_names.py, tests/test_salts.py)
    [[c] for c in sorted(PLANNED_STEP) if c not in {"import-cast", "rotate-salts", "vectors", "names"}]
    + [["build", "--release"], ["check", "--release"], ["import-cast", "cast.xlsx"]],
)
def test_stub_returns_2(args):
    res = run_engine(*args)
    assert res.returncode == 2
    out = res.stdout.decode("utf-8")
    assert f"Будет реализовано в {PLANNED_STEP[args[0]]}" in out


def test_cyrillic_output_survives_non_utf8_console():
    # Имитация консоли Windows с однобайтовой кодировкой: reconfigure в __main__
    # должен переключить вывод на UTF-8, а не упасть с UnicodeEncodeError.
    res = run_engine("build", env_extra={"PYTHONIOENCODING": "ascii", "PYTHONUTF8": "0"})
    assert res.returncode == 2, res.stderr.decode("utf-8", "replace")
    assert "Будет реализовано" in res.stdout.decode("utf-8")
    assert b"UnicodeEncodeError" not in res.stderr
