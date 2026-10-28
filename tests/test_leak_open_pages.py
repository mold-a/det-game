"""Leak scan и открытые страницы (docs/02 §5а): проза открытой страницы не отбеливает секретные шинглы.

Фраза из закрытого текста (заключение эксперта этапа 3, развязка), вставленная в пост открытой страницы
(``locked: false``), обязана ронять check. Бренды, подвалы сервисов и фразы ``settings.leak_public_ok`` — нет.
Всё — во временной копии ``content/`` с копией ``engine/salts.lock.json``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from engine import ROOT
from engine.build import build
from engine.check import check
from engine.leakscan import is_stop_shingle, text_shingles

CONTENT = ROOT / "content"
# Предложения закрытых текстов: без иголок-значений (ответов, watchlist), только шинглы.
SECRET_EXPERT = ("Таблетка из отделения ЧТ отличается от таблеток из отделений СР, ПТ, СБ, ВС "
                 "формой, наличием риски, отсутствием гравировки")  # documents/3-06.md, результат экспертизы
SECRET_FATE = "Журнал светового пульта приобщён к делу. По-прежнему ведёт свет на всех премьерах театра."  # finale.yaml
PAGE = "pages/krug-kirill/page.yaml"
ANCHOR = 'text: "Кот сегодня работает из дома.'  # начало текста поста на открытой странице Кирилла


def _run(tmp_path: Path, insert: str, *, settings_extra: str = "") -> tuple[object, Path]:  # settings_extra: пункты в конец leak_public_ok (последний ключ settings.yaml)
    """Копия контента, ``insert`` — отдельной строкой в начале поста открытой страницы; build + check."""
    content = tmp_path / "content"
    shutil.copytree(CONTENT, content)
    salts = tmp_path / "salts.lock.json"
    shutil.copyfile(ROOT / "engine" / "salts.lock.json", salts)
    page = content / PAGE
    text = page.read_text(encoding="utf-8")
    assert ANCHOR in text, "якорь поста изменился — обновите ANCHOR в тесте"
    page.write_text(text.replace(ANCHOR, f'text: "{insert}\\n' + ANCHOR[len('text: "'):], 1), encoding="utf-8")
    if settings_extra:
        sp = content / "settings.yaml"
        sp.write_text(sp.read_text(encoding="utf-8").rstrip("\n") + "\n" + settings_extra, encoding="utf-8")
    dist = tmp_path / "dist"
    build(content_dir=content, dist=dist, salts_path=salts, media_dir=ROOT / "media")
    rep = check(content_dir=content, dist=dist, salts_path=salts, media_dir=ROOT / "media")
    return rep, dist


def _leak_problems(rep) -> list[str]:
    return [p for p in rep.problems if p.startswith("[7.")]


def test_baseline_is_clean(tmp_path):
    rep, _ = _run(tmp_path, "Всем хорошего дня")
    assert rep.ok, rep.problems


@pytest.mark.parametrize("secret", [SECRET_EXPERT, SECRET_FATE], ids=["expertise-3-06", "finale"])
def test_secret_sentence_on_open_page_is_caught(tmp_path, secret):
    rep, _ = _run(tmp_path, secret)
    assert not rep.ok
    row = next(r for r in rep.rows if r.name.startswith("7."))
    assert not row.ok
    probs = _leak_problems(rep)
    assert any("p/krug-kirill/index.html" in p and "shingle" in p for p in probs), probs
    assert all("p/krug-kirill/index.html" in p for p in probs), probs  # ничего лишнего


def test_brands_and_service_footer_are_not_leaks(tmp_path):
    # бренд мира, название театра и подвал сервиса стоят на странице по замыслу
    insert = ("{{ w.brands.social }} — городская сеть для общения: страницы горожан, организаций и сообществ. "
              "{{ w.theater.full }}, {{ w.city }}, {{ w.theater.address }}. О сервисе, Правила, Помощь")
    rep, _ = _run(tmp_path, insert)
    assert rep.ok, rep.problems


def test_leak_public_ok_allows_listed_phrase_only(tmp_path):
    rep, _ = _run(tmp_path, SECRET_EXPERT, settings_extra=f'  - "{SECRET_EXPERT}"')
    assert rep.ok, rep.problems  # явный allowlist: автор осознанно разрешил повтор
    # соседняя фраза того же закрытого документа в allowlist не входит
    rep, _ = _run(tmp_path / "second", SECRET_FATE, settings_extra=f'  - "{SECRET_EXPERT}"')
    assert not rep.ok and _leak_problems(rep)


def test_ui_label_shingles_are_stop():
    assert text_shingles("О сервисе Правила Помощь")
    assert all(is_stop_shingle(sh) for sh in text_shingles("О сервисе Правила Помощь"))
    assert not is_stop_shingle("правила помощь экспертиза пропранолол")
