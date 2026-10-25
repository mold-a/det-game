"""Тип ``video`` с любым slug: закрытая ``video`` (4-07) и открытая ``archive`` (1-15).

Всё — во временной копии ``content/`` с копией ``engine/salts.lock.json``; соли и ключи существующих страниц
не меняются, у открытой страницы ключа нет.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pages_fixture import copy_content  # noqa: E402

from engine import ROOT, crypto  # noqa: E402
from engine import salts as salts_mod  # noqa: E402
from engine.build import build  # noqa: E402
from engine.check import check  # noqa: E402
from engine.content import load_content  # noqa: E402
from engine.leakscan import is_stop_shingle  # noqa: E402
from engine.models import VideoPage  # noqa: E402

FAKE_MP4 = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 8
FAKE_JPG = b"\xff\xd8\xff\xe0" + bytes(range(100)) * 3
SECRET = ("Таблетка из отделения ЧТ отличается от таблеток из отделений СР, ПТ, СБ, ВС "
          "формой, наличием риски, отсутствием гравировки")  # documents/3-06.md, результат экспертизы этапа 3
PAGE = "pages/archive/page.yaml"


def _edit(path: Path, fn) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _setup(tmp_path: Path, *, with_media: bool, edit=None) -> tuple[Path, Path, Path, Path]:
    content = copy_content(tmp_path)
    if edit:
        edit(content)
    media = tmp_path / "media"
    media.mkdir()
    if with_media:
        (media / "video").mkdir()
        (media / "video" / "archive-cam.mp4").write_bytes(FAKE_MP4)
        (media / "video" / "archive-cam.jpg").write_bytes(FAKE_JPG)
    lock = tmp_path / "salts.lock.json"
    shutil.copyfile(ROOT / "engine" / "salts.lock.json", lock)
    return content, media, lock, tmp_path / "dist"


def _build(content, media, lock, dist):
    return build(content_dir=content, dist=dist, media_dir=media, salts_path=lock, log=lambda *_: None)


def test_model_accepts_any_slug_and_validates_poster():
    base = {"doc": "1-15", "qr_label": "q", "title": "t", "source": "s", "video": "video/a.mp4",
            "file": {"name": "a.mp4", "size": "1", "created": "2026-11-10T21:02:12", "device": "d",
                     "duration": "0:08", "resolution": "1280×720"}}
    page = VideoPage(slug="archive", locked=False, **base)
    assert page.type == "video" and page.poster is None and page.clues == ["filename", "created"]
    assert VideoPage(slug="archive", locked=False, poster="video/a.jpg", clues=[], **base).clues == []
    with pytest.raises(ValidationError, match="постер"):
        VideoPage(slug="archive", locked=False, poster="video/a.gif", **base)
    with pytest.raises(ValidationError, match="mp4"):
        VideoPage(slug="archive", locked=False, **{**base, "video": "video/a.avi"})


def test_archive_is_open_video_page_of_1_15():
    c = load_content(ROOT / "content")
    page = c.pages["archive"]
    assert page.type == "video" and page.locked is False and page.doc == "1-15" and page.clues == []
    assert {d.id: d.page for d in c.documents}["1-15"] == "archive"
    assert c.pages["video"].type == "video" and c.pages["video"].locked is True
    assert "archive" not in salts_mod.read(ROOT / "engine" / "salts.lock.json").data["pages"]  # открытая: ключа нет


def test_open_archive_markup_with_media(tmp_path):
    content, media, lock, dist = _setup(tmp_path, with_media=True)
    _build(content, media, lock, dist)
    html = (dist / "p" / "archive" / "index.html").read_text(encoding="utf-8")
    video = re.search(r"<video[^>]*>", html).group(0)
    assert re.search(r'src="/m/[0-9a-f]{32}\.mp4"', video) and re.search(r'poster="/m/[0-9a-f]{32}\.jpg"', video)
    assert "controls" in video and "data-media" not in video
    assert 'data-type="video"' in html and "page--archive" in html and "/assets/css/pages/video.css" in html
    assert 'class="ev-bar"' in html and "Видеофайл, " in html
    assert "clue" not in html  # у archive меток улик нет
    assert not (dist / "p" / "archive" / "payload.json").exists()
    assert "Здесь будет видео" not in html
    assert "·" not in html.split("<body", 1)[1]
    assert re.search(r"<title>Фрагмент архивной записи", html)  # заголовок открытой video — title страницы
    assert salts_mod.read(lock).data["pages"] == salts_mod.read(ROOT / "engine" / "salts.lock.json").data["pages"]


def test_missing_media_is_warning_not_failure(tmp_path):
    content, media, lock, dist = _setup(tmp_path, with_media=False)
    rep = _build(content, media, lock, dist)
    html = (dist / "p" / "archive" / "index.html").read_text(encoding="utf-8")
    assert "<video" not in html and "Здесь будет видео" in html
    assert {"video/archive-cam.mp4", "video/archive-cam.jpg"} <= set(rep.missing_media)
    assert any("archive-cam.mp4" in w for w in rep.warnings)
    rep = check(content_dir=content, dist=dist, salts_path=lock, media_dir=media)
    assert rep.ok, rep.problems


def test_closed_video_keeps_clues_and_sealed_poster(tmp_path):
    def edit(c: Path) -> None:  # закрытая video с постером; archive становится закрытой — shell_brand по type
        _edit(c / "pages" / "video" / "page.yaml", lambda d: d.update(poster="video/archive-cam.jpg"))
        _edit(c / PAGE, lambda d: d.update(locked=True))

    content, media, lock, dist = _setup(tmp_path, with_media=True, edit=edit)
    (media / "video" / "rehearsal.mp4").write_bytes(FAKE_MP4 + b"rehearsal")
    _build(content, media, lock, dist)
    salts = salts_mod.read(lock)
    box = json.loads((dist / "p" / "video" / "payload.json").read_text(encoding="utf-8"))
    inner = json.loads(crypto.open_(salts.page_key("video"), box, "page/video"))
    assert 'data-clue="filename"' in inner["html"] and 'data-clue="created"' in inner["html"]
    assert re.search(r'<video[^>]*data-media="\d+"[^>]*data-poster-media="\d+"', inner["html"])
    assert "src=" not in re.search(r"<video[^>]*>", inner["html"]).group(0)
    assert len(inner["media"]) == 2 and all("key" in m for m in inner["media"])
    shell = (dist / "p" / "archive" / "index.html").read_text(encoding="utf-8")  # закрытая archive: оболочка
    assert (dist / "p" / "archive" / "payload.json").exists() and "Электронное дело" in shell
    assert "Фрагмент архивной записи" not in shell  # заголовок страницы в оболочке не виден
    a_box = json.loads((dist / "p" / "archive" / "payload.json").read_text(encoding="utf-8"))
    a_inner = json.loads(crypto.open_(salts.page_key("archive"), a_box, "page/archive"))
    assert a_inner["title"].startswith("Фрагмент архивной записи") and "clue" not in a_inner["html"]


def test_template_words_are_not_secret_on_open_video():
    assert is_stop_shingle("видео свойства файла свойства")
    assert not is_stop_shingle("таблетка из отделения чт")


def test_secret_in_open_archive_fails_leak_scan(tmp_path):
    """Обвязка шаблона video — не утечка, а закрытый текст в подписи открытой archive — утечка."""
    content, media, lock, dist = _setup(tmp_path, with_media=False,
                                        edit=lambda c: _edit(c / PAGE, lambda d: d.update(source=SECRET)))
    _build(content, media, lock, dist)
    rep = check(content_dir=content, dist=dist, salts_path=lock, media_dir=media)
    assert not rep.ok and any(p.startswith("[7.") and "archive" in p for p in rep.problems), rep.problems
