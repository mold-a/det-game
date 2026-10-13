"""engine/salts.lock.json: создание, дописывание, неизменность, rotate. Только во временной папке."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

import engine.salts as salts_mod
from engine import ROOT
from engine.__main__ import main
from engine.content import load_content
from engine.salts import (
    PAGE_KEY_BYTES,
    SALT_BYTES,
    SaltsError,
    ensure_for_content,
    load_or_init,
    read,
    rotate,
    salts_id,
)
from engine.util import b64u_decode, canonical_json, sha256_hex

REQ = dict(units=["s1.q1.time", "s1.q2"], stages=[1, 2], pages=["inna"])


def test_created_with_sizes(tmp_path):
    path = tmp_path / "salts.lock.json"
    s = load_or_init(path, **REQ)
    assert path.is_file()
    assert len(s.unit("s1.q1.time")) == SALT_BYTES == 16
    assert len(s.stage(2)) == 16 and len(s.start) == 16 and len(s.cloud) == 16
    assert len(s.page_key("inna")) == PAGE_KEY_BYTES == 32
    for v in [*s.data["units"].values(), s.data["start"]]:
        assert "=" not in v
    with pytest.raises(KeyError):
        s.unit("s9.q9")


def test_file_format_and_salts_id(tmp_path):
    path = tmp_path / "salts.lock.json"
    s = load_or_init(path, **REQ)
    text = path.read_text(encoding="utf-8")
    assert text.endswith("}\n") and "\r" not in text
    assert text == json.dumps(json.loads(text), sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    assert s.id == salts_id(s.data) == sha256_hex(canonical_json(json.loads(text)))


def test_second_call_changes_nothing(tmp_path):
    path = tmp_path / "salts.lock.json"
    a = load_or_init(path, **REQ)
    before = path.read_bytes()
    mtime = path.stat().st_mtime_ns
    b = load_or_init(path, **REQ)
    assert path.read_bytes() == before
    assert path.stat().st_mtime_ns == mtime  # файл не переписывался
    assert a.data == b.data and a.id == b.id


def test_new_unit_appends_keeps_old(tmp_path):
    path = tmp_path / "salts.lock.json"
    a = load_or_init(path, **REQ)
    b = load_or_init(path, units=[*REQ["units"], "s1.b1"], stages=[1, 2, 3], pages=["inna", "video"])
    for k, v in a.data["units"].items():
        assert b.data["units"][k] == v
    assert b.data["pages"]["inna"] == a.data["pages"]["inna"]
    assert b.data["start"] == a.data["start"] and b.data["cloud"] == a.data["cloud"]
    assert "s1.b1" in b.data["units"] and "3" in b.data["stages"] and "video" in b.data["pages"]
    assert a.id != b.id
    # удалённая единица остаётся
    c = load_or_init(path, units=["s1.q2"], stages=[1], pages=[])
    assert "s1.q1.time" in c.data["units"] and c.data == b.data


def test_rotate_changes_everything(tmp_path):
    path = tmp_path / "salts.lock.json"
    a = load_or_init(path, **REQ)
    with pytest.raises(SaltsError):
        rotate(path, **REQ)
    assert read(path).data == a.data  # без подтверждения файл не тронут
    b = rotate(path, **REQ, confirm=True)
    assert read(path).data == b.data
    for section in ("units", "stages", "pages"):
        assert set(a.data[section]) == set(b.data[section])
        for k in a.data[section]:
            assert a.data[section][k] != b.data[section][k]
    assert a.data["start"] != b.data["start"] and a.data["cloud"] != b.data["cloud"]


def test_corrupted_file_is_not_recreated(tmp_path):
    path = tmp_path / "salts.lock.json"
    load_or_init(path, **REQ)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["pages"]["inna"] = data["units"]["s1.q2"]  # 16 байт вместо 32
    bad = json.dumps(data)
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(SaltsError, match="32 байт"):
        load_or_init(path, **REQ)
    assert path.read_text(encoding="utf-8") == bad
    path.write_text("{oops", encoding="utf-8")
    with pytest.raises(SaltsError, match="неверный JSON"):
        load_or_init(path, **REQ)


def test_for_current_content(tmp_path):
    c = load_content()
    path = tmp_path / "salts.lock.json"
    s = ensure_for_content(c, path)
    assert len(s.data["units"]) == 23
    assert set(s.data["stages"]) == {"1", "2", "3", "4"}
    assert set(s.data["pages"]) == {"inna", "pharma", "video"}  # locked: true; cloud — по паролю
    assert len(b64u_decode(s.data["pages"]["video"])) == 32
    assert ensure_for_content(c, path).data == s.data


def test_cli_rotate_requires_yes():
    lock = ROOT / "engine" / "salts.lock.json"
    existed = lock.exists()
    res = subprocess.run([sys.executable, "-m", "engine", "rotate-salts"], cwd=ROOT, capture_output=True, timeout=60)
    assert res.returncode == 2
    assert "--yes" in res.stderr.decode("utf-8")
    assert lock.exists() == existed


def test_cli_rotate_yes(tmp_path, monkeypatch, capsys):
    path = tmp_path / "salts.lock.json"
    monkeypatch.setattr(salts_mod, "SALTS_LOCK", path)
    assert main(["rotate-salts", "--yes"]) == 0
    out = capsys.readouterr().out
    assert "QR" in out and "перепечатайте" in out
    first = read(path).data
    assert main(["rotate-salts", "--yes"]) == 0
    assert read(path).data["start"] != first["start"]
