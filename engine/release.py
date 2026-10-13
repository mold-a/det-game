"""``python -m engine release`` — сборка для выкладки (P08 п.4).

``build --release`` → ``check --release`` → архив ``print/dist-<buildId>.zip`` (только
содержимое ``dist/``). Любая причина (TODO(content), нет медиа, пароль облака, домен-заглушка,
провал check) — ``ReleaseError`` с полным списком.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from engine import ROOT
from engine import salts as salts_mod
from engine.build import BuildError, BuildReport, build
from engine.check import CheckReport, check

PRINT = ROOT / "print"


class ReleaseError(Exception):
    def __init__(self, stage: str, problems: list[str]) -> None:
        self.stage = stage
        self.problems = problems
        head = f"Релиз остановлен на шаге «{stage}» — причин: {len(problems)}"
        super().__init__("\n".join([head, *(f"  {p}" for p in problems)]))


@dataclass
class ReleaseReport:
    build: BuildReport
    check: CheckReport
    archive: Path
    build_id: str


def make_zip(dist: Path, out: Path) -> Path:
    """Архив только с содержимым dist/ (пути от корня сайта), в стабильном порядке."""
    dist = Path(dist)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".zip.part")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(x for x in dist.rglob("*") if x.is_file()):
            zf.write(p, p.relative_to(dist).as_posix())
    tmp.replace(out)
    return out


def release(
    root: Path = ROOT,
    *,
    content_dir: Path | None = None,
    media_dir: Path | None = None,
    dist: Path | None = None,
    salts_path: Path | None = None,
    out_dir: Path | None = None,
) -> ReleaseReport:
    root = Path(root)
    dist = Path(dist or root / "dist")
    salts_path = Path(salts_path or salts_mod.SALTS_LOCK)
    kw = dict(content_dir=content_dir, media_dir=media_dir, dist=dist, salts_path=salts_path)
    try:
        brep = build(root, release=True, **kw)
    except BuildError as e:
        raise ReleaseError("build --release", e.problems) from None
    crep = check(root, release=True, **kw)
    if not crep.ok:
        raise ReleaseError("check --release", crep.problems or [r.name for r in crep.rows if not r.ok])
    build_id = json.loads((dist / "data" / "public.json").read_text(encoding="utf-8"))["buildId"]
    archive = make_zip(dist, Path(out_dir or root / "print") / f"dist-{build_id}.zip")
    return ReleaseReport(brep, crep, archive, build_id)
