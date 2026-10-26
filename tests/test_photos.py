"""Фото в контенте: блок ``photo`` сайта организации, ``photos`` в lab.yaml, папка облака ``kind: photos``,
подпись к фото статьи (docs/03 §6б, §8; docs/04). Фикстуры — ``tests/pages_fixture.add_photo_fixtures``
(копия content/, в самом content/ тестовых фото нет)."""

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

from pages_fixture import (  # noqa: E402
    PHOTO_FILES,
    PHOTO_FOLDER_ID,
    add_fixture_pages,
    add_photo_fixtures,
    copy_content,
)

from engine import ROOT, crypto  # noqa: E402
from engine import salts as salts_mod  # noqa: E402
from engine.build import build  # noqa: E402
from engine.media import src_file  # noqa: E402
from engine.content import ContentError, load_content, media_refs  # noqa: E402
from engine.normalize import normalize  # noqa: E402
from engine.models import CloudFolder, CloudPhoto, LabSite, NewsArticle, SitePhoto  # noqa: E402


def fake_jpg(rel: str) -> bytes:
    """Разное содержимое у каждого файла (одинаковые сборщик склеивает в один) — это не настоящий JPEG."""
    return b"\xff\xd8\xff\xe0" + rel.encode() + bytes(range(60))


@pytest.fixture
def fx(tmp_path: Path) -> Path:
    c = copy_content(tmp_path)
    add_fixture_pages(c)
    add_photo_fixtures(c)
    return c


def errors_of(root: Path) -> list[str]:
    with pytest.raises(ContentError) as exc:
        load_content(root)
    return [str(e) for e in exc.value.errors]


def edit_yaml(path: Path, fn) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


# ---------------------------------------------------------------- модели


def test_site_photo_block_model():
    p = SitePhoto(kind="photo", file="theater/facade.jpg")
    assert p.caption is None and p.wide is False
    assert SitePhoto(kind="photo", file="a/b.WEBP", caption="Фасад", wide=True).wide is True
    for bad in ({"file": "a/b.mp3"}, {"file": "a/b.svg"}, {"file": "a/b.jpg", "alt": "x"}, {"file": "a/b.jpg", "wide": "yes"}):
        with pytest.raises(ValidationError):
            SitePhoto(kind="photo", **bad)


def test_lab_photos_model_limits_and_extensions():
    base = dict(name="n", full_name="f", tagline="t", about="a", accreditation="x",
                contacts={"address": "a", "phone": "p", "hours": "h"}, services_note="s")
    assert LabSite(**base).photos == []
    three = [{"file": f"lab/{i}.jpg", "caption": "c"} for i in range(3)]
    assert len(LabSite(**base, photos=three).photos) == 3
    with pytest.raises(ValidationError, match="at most 3"):
        LabSite(**base, photos=three + [{"file": "lab/4.jpg"}])
    with pytest.raises(ValidationError, match="допустимы файлы"):
        LabSite(**base, photos=[{"file": "lab/a.mp4"}])


def test_cloud_photos_folder_model_and_news_caption():
    f = CloudFolder(id="gallery", title="Фото", kind="photos", items=[{"file": "cloud/a.jpg", "caption": "c", "date": "2026-10-12"},
                                                                      {"file": "cloud/b.png"}])
    assert f.items[1] == CloudPhoto(file="cloud/b.png") and f.items[1].caption is None and f.items[1].date is None
    with pytest.raises(ValidationError):
        CloudFolder(id="g", title="Фото", kind="photos", items=[{"file": "cloud/a.txt"}])
    art = dict(datetime="2026-11-11T08:00", headline="h", body="b")
    assert NewsArticle(**art).photo_caption is None
    assert NewsArticle(**art, photo="news/x.jpg", photo_caption="Подпись").photo_caption == "Подпись"


# ---------------------------------------------------------------- проверки контента и media_refs


def test_photos_folder_requires_items_and_others_reject_them(fx):
    def drop(d):
        gal = next(f for f in d["folders"] if f["id"] == PHOTO_FOLDER_ID)
        del gal["items"]

    edit_yaml(fx / "pages/cloud/page.yaml", drop)
    errs = errors_of(fx)
    assert any("folders[" in e and "items" in e and "kind: photos" in e for e in errs), errs

    empty = copy_content(fx.parent / "again")
    add_fixture_pages(empty)
    add_photo_fixtures(empty)
    edit_yaml(empty / "pages/cloud/page.yaml",
              lambda d: next(f for f in d["folders"] if f["id"] == PHOTO_FOLDER_ID).update(items=[]))
    assert any("хотя бы одна фотография" in e for e in errors_of(empty))

    reg = copy_content(fx.parent / "third")
    add_fixture_pages(reg)
    edit_yaml(reg / "pages/cloud/page.yaml",
              lambda d: next(f for f in d["folders"] if f["kind"] == "table").update(items=[{"file": "cloud/a.jpg"}]))
    assert any("items" in e and "не применимо" in e for e in errors_of(reg))


def test_photo_paths_are_checked_like_other_media(fx):
    edit_yaml(fx / "lab.yaml", lambda d: d["photos"][0].update(file="../secret.jpg"))
    assert any("lab.yaml" in e and "относительным" in e for e in errors_of(fx))


def test_media_refs_cover_site_cloud_lab_and_news(fx):
    c = load_content(fx)
    uses = {(u.path, u.context): u.loc for u in media_refs(c.characters, c.pages, c.docs, lab=c.lab)}
    assert uses[("theater/wide.jpg", "open")].endswith("blocks[%d].file" % next(
        i for i, b in enumerate(next(s for s in c.pages["theater"].sections if s.id == "about").blocks)
        if getattr(b, "file", None) == "theater/wide.jpg"))
    assert ("theater/card.jpg", "open") in uses and ("theater/absent.jpg", "open") in uses
    assert re.fullmatch(r"folders\[\d+\]\.items\[0\]\.file", uses[("cloud/a.jpg", "locked")])  # облако закрыто паролем
    assert uses[("lab/t2.jpg", "open")] == "photos[1].file"  # сайт лаборатории открыт
    assert ("news/photo.jpg", "open") in uses
    assert not any(p == "lab/t1.jpg" for p in (u.path for u in media_refs(c.characters, c.pages, c.docs)))  # без lab= — не учитывается


# ---------------------------------------------------------------- сборка


def media_dir(tmp: Path, *, skip: tuple[str, ...] = ()) -> Path:
    m = tmp / "media"
    for rels in PHOTO_FILES.values():
        for rel in rels:
            if rel in skip:
                continue
            (m / rel).parent.mkdir(parents=True, exist_ok=True)
            (m / rel).write_bytes(fake_jpg(rel))
    return m


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("photos")
    c = copy_content(tmp)
    add_fixture_pages(c)
    add_photo_fixtures(c)
    media = media_dir(tmp, skip=("lab/t3.jpg",))  # третьего снимка лаборатории нет
    lock = tmp / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    dist = tmp / "dist"
    rep = build(content_dir=c, dist=dist, media_dir=media, salts_path=lock, log=lambda *_: None)
    return tmp, dist, lock, rep, media


def read(dist: Path, slug: str) -> str:
    return (dist / "p" / slug / "index.html").read_text(encoding="utf-8")


def test_site_photo_blocks_markup(built):
    _, dist, _, _, _ = built
    html = read(dist, "theater")
    figs = re.findall(r'<figure class="st-photo[^"]*">.*?</figure>', html, re.S)
    assert len(figs) == 3
    wide, inside, absent = figs
    assert 'class="st-photo st-photo--wide"' in wide and "st-photo--wide" not in inside
    for f in (wide, inside):
        assert re.search(r'<button class="st-photo__btn st-zoom" type="button" aria-haspopup="dialog" data-zoom', f)
        assert re.search(r'<img class="st-photo__img" src="/m/[0-9a-f]{32}\.jpg"', f)
        assert 'loading="lazy"' in f and 'decoding="async"' in f
    assert "<figcaption" in wide and "Тестовый фасад" in wide
    assert 'data-caption="Тестовый фасад"' in wide and 'alt="Тестовый фасад"' in wide
    # файла нет: аккуратная заглушка, ни сломанной картинки, ни кнопки «крупно»
    assert "<img" not in absent and "<button" not in absent and "src=" not in absent
    assert 'class="ph ph--img st-photo__img"' in absent and "Здесь будет фото" in absent
    assert "Тестовый снимок без файла" in absent  # подпись остаётся


def test_card_photos_open_large_and_missing_card_photo_is_plain_placeholder(built):
    _, dist, _, _, _ = built
    html = read(dist, "theater")
    cards = re.findall(r'<li class="st-card has-photo">.*?</li>', html, re.S)
    assert len(cards) == 2
    ok, missing = cards
    assert "<button" in ok and "data-zoom" in ok and re.search(r'<img class="st-img" src="/m/[0-9a-f]{32}\.jpg"', ok)
    assert 'loading="lazy"' in ok
    assert "<img" not in missing and "<button" not in missing and "ph--img" in missing


def test_site_photo_files_are_open_copies_in_dist(built):
    _, dist, _, rep, media = built
    open_html = read(dist, "theater")
    names = {Path(m).name for m in re.findall(r'src="(/m/[^"]+)"', open_html)}
    assert len(names) == 3  # wide, inside, card
    for n in names:
        assert (dist / "m" / n).read_bytes() in {(media / r).read_bytes() for r in PHOTO_FILES["theater"]}
    assert "theater/absent.jpg" in rep.missing_media and "theater/wide.jpg" not in rep.missing_media
    assert any("theater/absent.jpg" in w for w in rep.warnings)


def test_news_photo_caption(built):
    _, dist, _, _, _ = built
    html = read(dist, "news")
    fig = re.search(r'<figure class="nw-article__photo">.*?</figure>', html, re.S).group(0)
    assert '<figcaption class="nw-article__caption">Тестовая подпись к фото статьи</figcaption>' in fig
    assert re.search(r'<img class="nw-photo" src="/m/[0-9a-f]{32}\.jpg"', fig) and 'loading="lazy"' in fig


def test_news_without_caption_has_no_figcaption(built):
    _, dist, _, _, _ = built
    html = read(dist, "news-most")
    assert "nw-article__caption" not in html


def sealed_inner(built, slug: str) -> dict:
    from engine.models import CloudPage
    from engine.pages import open_password_payload

    tmp, dist, lock, _, _ = built
    page = CloudPage.model_validate(yaml.safe_load((tmp / "content/pages" / slug / "page.yaml").read_text(encoding="utf-8")))
    box = json.loads((dist / "p" / slug / "payload.json").read_text(encoding="utf-8"))
    assert page.locked in (True, "password")
    page_key = salts_mod.read(lock).page_key(slug) if page.locked is True else None
    return open_password_payload(page, box, page_key)[0]


def test_cloud_photos_folder_is_sealed_with_encrypted_media(built):
    _, dist, _, _, media = built
    raw_page = (dist / "p/cloud/index.html").read_text(encoding="utf-8") + (dist / "p/cloud/payload.json").read_text(encoding="utf-8")
    assert "Тестовая репетиция" not in raw_page and "tc-photos" not in raw_page
    inner = sealed_inner(built, "cloud")
    html = inner["html"]
    panel = re.search(r'<section class="tc-panel tc-panel--photos" id="tc-gallery".*?</section>', html, re.S).group(0)
    items = re.findall(r'<li class="tc-photo">.*?</li>', panel, re.S)
    assert len(items) == 4
    a, b, c, absent = items
    assert "data-media=" in a and "src=" not in a and 'loading="lazy"' in a and "data-zoom" in a
    assert 'data-caption="Тестовая репетиция · 12.10.2026"' in a
    assert '<time class="tc-photo__date" datetime="2026-10-12">12.10.2026</time>' in a
    assert 'data-caption="Только подпись"' in b and "tc-photo__date" not in b
    assert "tc-photo__cap" not in c  # ни подписи, ни даты
    assert "<img" not in absent and "<button" not in absent and "ph--img" in absent and "Нет файла" in absent
    refs = [r for r in inner["media"] if r["mime"] == "image/jpeg"]
    assert len(refs) == 3
    plain = {(media / r).read_bytes() for r in PHOTO_FILES["cloud"]}
    for ref in refs:
        assert src_file(ref["src"]).endswith(".bin") and ref["key"] and ref["aad"].startswith("media/")
        blob = (dist / "m" / src_file(ref["src"]).rsplit("/", 1)[1]).read_bytes()
        assert crypto.open_media(crypto.b64u_decode(ref["key"]), blob, ref["aad"]) in plain
        assert blob not in plain
    assert not any(p.read_bytes() in plain for p in (dist / "m").iterdir())  # открытых копий нет
    assert "Нажмите на снимок" in html


def test_lab_photos_are_open_and_missing_ones_are_skipped(built):
    _, dist, _, rep, media = built
    html = (dist / "lab/index.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r'<script type="application/json" id="lab-site">(.*?)</script>', html, re.S).group(1))
    assert [p["caption"] for p in data["photos"]] == ["Тестовый вход со двора", "Тестовый хроматограф"]
    for p, rel in zip(data["photos"], ("lab/t1.jpg", "lab/t2.jpg")):
        assert re.fullmatch(r"/m/[0-9a-f]{32}\.jpg", p["src"])  # сайт лаборатории открыт: файл открытый
        assert (dist / p["src"][1:]).read_bytes() == (media / rel).read_bytes()
        assert p["alt"] == p["caption"]
    assert "lab/t3.jpg" in rep.missing_media and any("lab/t3.jpg" in w for w in rep.warnings)
    assert "/assets/css/pages/_ui.css" in html  # окно «крупно» берёт стили общего файла


def test_lab_without_photos_has_empty_list(tmp_path):
    c = copy_content(tmp_path)
    lock = tmp_path / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    build(content_dir=c, dist=tmp_path / "dist", media_dir=tmp_path / "nomedia", salts_path=lock, log=lambda *_: None)
    html = (tmp_path / "dist/lab/index.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r'<script type="application/json" id="lab-site">(.*?)</script>', html, re.S).group(1))
    assert data["photos"] == []


def test_release_build_fails_on_missing_photo_files(fx, tmp_path):
    from engine.build import BuildError

    lock = tmp_path / "salts.lock.json"
    shutil.copy(ROOT / "engine" / "salts.lock.json", lock)
    with pytest.raises(BuildError) as e:
        build(content_dir=fx, dist=tmp_path / "dist", media_dir=media_dir(tmp_path), salts_path=lock, release=True,
              log=lambda *_: None)
    msgs = "\n".join(e.value.problems)
    assert "нет медиафайла media/theater/absent.jpg" in msgs and "media/cloud/absent.jpg" in msgs
