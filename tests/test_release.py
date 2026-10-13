"""``python -m engine release``: падает на текущем контенте; на «полной» копии — проходит и
создаёт zip только с содержимым dist/ и без открытых ответов."""

from __future__ import annotations

import itertools
import re
import shutil
import zipfile
from pathlib import Path

import pytest

from engine import ROOT
from engine.build import prepare
from engine.check import leak_needles
from engine.content import collect_todos, load_content, media_refs
from engine.leakscan import scan
from engine.release import ReleaseError, release

CONTENT = ROOT / "content"
TODO = "TODO(content)"


def complete_copy(tmp_path: Path) -> tuple[Path, Path]:
    """Копия контента без заглушек: TODO(content) → уникальные нейтральные строки, пароль облака,
    свой домен, недостающие тексты страниц; медиа — крошечные сгенерированные файлы."""
    cdir = tmp_path / "content"
    shutil.copytree(CONTENT, cdir)
    cloud = cdir / "pages" / "cloud" / "page.yaml"
    cloud.write_text(re.sub(r'password: "TODO\(content\)"', 'password: "Арбенин-1835-тест"',
                            cloud.read_text(encoding="utf-8")), encoding="utf-8")
    settings = cdir / "settings.yaml"
    settings.write_text(settings.read_text(encoding="utf-8").replace("https://example.ru", "https://zakulisami.test"),
                        encoding="utf-8")
    counter = itertools.count(1)
    for p in sorted(cdir.rglob("*")):
        if p.suffix in (".yaml", ".md"):
            s = p.read_text(encoding="utf-8")
            if TODO in s:
                s = re.sub(re.escape(TODO), lambda _m: f"Заполнено {next(counter)}", s)
                p.write_text(s, encoding="utf-8")
    c = load_content(cdir)
    for m in c.missing:  # тексты страниц, которых нет (news/article.md, cloud/if_you_read_this.md)
        rel = m.text.split("нет файла ", 1)[1].split(" —", 1)[0].removeprefix("content/")
        (cdir / rel).parent.mkdir(parents=True, exist_ok=True)
        (cdir / rel).write_text(f"Текст страницы {next(counter)}.\n", encoding="utf-8")
    for d in c.documents:  # тексты бумажных документов, которых нет (content/paper/<id>.md)
        if d.kind == "paper" and d.id not in c.paper:
            form = "chat" if d.id in c.chats else "protocol"
            (cdir / "paper").mkdir(exist_ok=True)
            (cdir / "paper" / f"{d.id}.md").write_text(
                f'---\nid: "{d.id}"\nform: {form}\n---\nТекст бумажного документа {next(counter)}.\n', encoding="utf-8")
    media = tmp_path / "media"
    c = load_content(cdir)
    for use in media_refs(c.characters, c.pages, c.docs):
        f = media / use.path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(f"media:{use.path}".encode("utf-8"))
    assert collect_todos(c) == []
    return cdir, media


def test_release_fails_on_current_content(tmp_path):
    with pytest.raises(ReleaseError) as exc:
        release(dist=tmp_path / "dist", salts_path=tmp_path / "salts.json", out_dir=tmp_path / "print")
    e = exc.value
    assert e.stage == "build --release"
    text = str(e)
    assert "TODO(content)" in text and "нет медиафайла" in text
    assert "домен-заглушка" in text  # пароль облака задан в content с 14.10.2026
    assert not (tmp_path / "print").exists() and not (tmp_path / "dist").exists()


def test_release_passes_on_complete_copy(tmp_path):
    cdir, media = complete_copy(tmp_path)
    salts = tmp_path / "salts.json"
    dist = tmp_path / "dist"
    rep = release(content_dir=cdir, media_dir=media, dist=dist, salts_path=salts, out_dir=tmp_path / "print")
    assert rep.check.ok, rep.check.table()
    assert rep.archive.name == f"dist-{rep.build_id}.zip" and rep.archive.parent == tmp_path / "print"
    with zipfile.ZipFile(rep.archive) as zf:
        names = sorted(zf.namelist())
        assert names == sorted(p.relative_to(dist).as_posix() for p in dist.rglob("*") if p.is_file())
        assert "data/public.json" in names and "index.html" in names
        assert not any(n.startswith(("content/", "engine/", "print/", "tests/")) for n in names)
        out = tmp_path / "unzipped"
        zf.extractall(out)
    # в архиве нет открытых ответов: leak scan по распакованному архиву
    prep = prepare(cdir, salts, create_salts=False)
    assert scan(out, leak_needles(prep)) == []
    # медиа на месте: открытые — копии, закрытые — .bin
    assert any(n.startswith("m/") and n.endswith(".bin") for n in names)
    assert any(n.startswith("m/") and n.endswith(".jpg") for n in names)
