"""Сборка ``dist/`` из ``content/`` и ``site/`` (P03, FORMATS).

Порядок: загрузка и валидация → контекст шаблонов → соли → единицы и каноны →
ключи этапов → план медиа → документы → экспертизы, пакеты, развязка → страницы →
HTML системы → ассеты и robots.txt → медиа. ``dist/`` собирается во временной папке
и подменяется целиком.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from engine import ROOT
from engine import salts as salts_mod
from engine.answers import expand_all, stage_keys
from engine.content import Content, Todo, collect_todos, load_content
from engine.documents import RenderedDoc, render_document
from engine.lab import dumps, expand_params, lab_entries, result_payload
from engine.media import MediaPlan
from engine.packs import PackBuilder, build_finale, build_public, chrome_of, seal_finale, seal_pack
from engine.pages import build_page
from engine.templating import make_context, make_site_env, render
from engine.util import b64u_encode, write_text

SITE = ROOT / "site"
ROBOTS = "noindex, nofollow"
ROBOTS_TXT = "User-agent: *\nDisallow: /\n"
# Заголовки для хостингов с файлом `_headers` (Netlify, Cloudflare Pages) — FORMATS §9.1, docs/DEPLOY.md.
# Правило на каждый путь отдельно и без общего `/*` для Cache-Control: оба хостинга склеивают значения
# совпавших правил, и «no-cache» смешался бы с «immutable».
NO_CACHE_PATHS = ("/", "/index.html", "/lab/*", "/final/*", "/p/*", "/data/*", "/assets/js/*", "/assets/css/*",
                  "/robots.txt")
IMMUTABLE_PATHS = ("/assets/fonts/*", "/m/*")


def headers_file() -> str:
    lines = ["# Создано python -m engine build. Кеширование — docs/DEPLOY.md, FORMATS §9.1.", "", "/*",
             "  X-Robots-Tag: noindex, nofollow", "  X-Content-Type-Options: nosniff", ""]
    for p in NO_CACHE_PATHS:
        lines += [p, "  Cache-Control: no-cache", ""]
    for p in IMMUTABLE_PATHS:
        lines += [p, "  Cache-Control: public, max-age=31536000, immutable", ""]
    return "\n".join(lines)
APP_ENTRIES = {
    "index.html": ("index.html", "/assets/js/app/main.js"),
    "lab/index.html": ("lab.html", "/assets/js/app/lab.js"),
    "final/index.html": ("final.html", "/assets/js/app/final.js"),
}
PLACEHOLDER_DOMAINS = ("example.ru", "example.com", "example.org", "example.net")


class BuildError(Exception):
    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("Сборка остановлена:\n" + "\n".join(f"  {p}" for p in problems))


@dataclass
class BuildReport:
    dist: Path
    stage_keys: dict[int, str]  # b64u K_n — для тестов стабильности
    page_keys: dict[str, str]
    todos: list[Todo]
    warnings: list[str] = field(default_factory=list)
    missing_media: list[str] = field(default_factory=list)
    files: int = 0
    size: int = 0
    seconds: float = 0.0


@dataclass
class Prepared:
    """Всё, что вычисляется из контента до записи dist/ (переиспользуется check и dump)."""

    content: Content
    ctx: dict
    salts: Any
    expanded: dict
    keys: dict[int, bytes]
    params: dict


def prepare(content_dir: Path, salts_path: Path, *, create_salts: bool = True) -> Prepared:
    """``create_salts=False`` (check, dump): файл солей только читается; его нет — ``BuildError``."""
    content = load_content(content_dir)
    ctx = make_context(content)
    if create_salts:
        salts = salts_mod.ensure_for_content(content, salts_path)
    else:
        salts = salts_mod.read(salts_path)
        if salts is None:
            raise BuildError([f"нет файла солей {salts_path} — сначала python -m engine build"])
    expanded = expand_all(content, ctx)
    params = expand_params(content, ctx)
    keys = stage_keys(content, salts, expanded)
    return Prepared(content, ctx, salts, expanded, keys, params)


def release_problems(content: Content, todos: list[Todo], missing_media: list[str]) -> list[str]:
    """Что запрещено в ``--release`` (P03 п.11, FORMATS F11, F18)."""
    problems = [f"TODO(content): {t}" for t in todos]
    problems += [f"нет медиафайла media/{m}" for m in missing_media]
    cloud = content.pages.get("cloud")
    pw = getattr(cloud, "password", None)
    if cloud is not None and (not pw or not pw.strip() or "TODO(content)" in pw):
        problems.append("content/pages/cloud/page.yaml: password: пароль облака не задан")
    host = (urlsplit(content.settings.domain).hostname or "").lower()
    if any(host == d or host.endswith("." + d) for d in PLACEHOLDER_DOMAINS):
        problems.append(f"content/settings.yaml: domain: {content.settings.domain} — домен-заглушка")
    return problems


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dumps(obj))


def _swap_dir(tmp: Path, dist: Path) -> None:
    old = dist.with_name(dist.name + ".__old__")
    if old.exists():
        shutil.rmtree(old)
    if dist.exists():
        dist.rename(old)
    tmp.rename(dist)
    if old.exists():
        shutil.rmtree(old)


def build(
    root: Path = ROOT,
    *,
    content_dir: Path | None = None,
    site_dir: Path | None = None,
    media_dir: Path | None = None,
    dist: Path | None = None,
    salts_path: Path | None = None,
    release: bool = False,
    log=print,
) -> BuildReport:
    t0 = time.monotonic()
    root = Path(root)
    content_dir = Path(content_dir or root / "content")
    site_dir = Path(site_dir or root / "site")
    media_dir = Path(media_dir or root / "media")
    dist = Path(dist or root / "dist")
    salts_path = Path(salts_path or salts_mod.SALTS_LOCK)

    prep = prepare(content_dir, salts_path)
    content, ctx, salts, expanded, keys = prep.content, prep.ctx, prep.salts, prep.expanded, prep.keys
    warnings = [str(w) for w in content.warnings]

    plan = MediaPlan(content, media_dir)
    missing_media = sorted(mf.rel for mf in plan.missing)
    todos = collect_todos(content)
    if release:
        problems = release_problems(content, todos, missing_media)
        if problems:
            raise BuildError(problems)

    site_env = make_site_env(site_dir / "templates")

    # документы экспертиз и развязки
    docs_by_id = content.documents_by_id
    rendered: dict[str, RenderedDoc] = {}
    for r in content.expertise.results:
        if r.doc is not None:
            title = render(docs_by_id[r.doc].title, ctx)
            rendered[r.id] = render_document(content.docs.get(r.body), ctx, plan, site_env, doc_id=r.doc,
                                             fallback_title=title)
    fin = content.finale
    confession = render_document(content.docs.get(fin.confession), ctx, plan, site_env)
    letter = render_document(content.docs.get(fin.letter), ctx, plan, site_env)

    payloads = {r.id: result_payload(content, r, ctx, rendered) for r in content.expertise.results}
    lab_by_stage = lab_entries(content, keys, payloads, prep.params, warnings)

    pub = build_public(content, salts)
    chrome = chrome_of(content)
    base_ctx = {"pub": pub, "chrome": chrome, "robots": ROBOTS}

    tmp = dist.with_name(dist.name + ".__tmp__")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        data = tmp / "data"
        _write_json(data / "public.json", pub)
        pb = PackBuilder(content, ctx, salts, expanded, plan)
        for st in content.stages:
            _write_json(data / f"pack-{st.n}.json", seal_pack(keys[st.n], st.n, pb.pack(st.n, lab_by_stage[st.n])))
        finale = build_finale(content, ctx, expanded, confession, letter)
        _write_json(data / "finale.json", seal_finale(keys[content.last_stage], finale))

        page_keys: dict[str, str] = {}
        for slug, page in content.pages.items():
            out = build_page(content, page, ctx, salts, plan, site_env, base_ctx)
            write_text(tmp / "p" / slug / "index.html", out.index_html)
            if out.payload is not None:
                _write_json(tmp / "p" / slug / "payload.json", out.payload)
            if out.access == "key":
                page_keys[slug] = b64u_encode(salts.page_key(slug))

        for out_rel, (tpl, entry) in APP_ENTRIES.items():
            ctx_html = dict(base_ctx, title=pub["title"], entry=entry, css=[], body_class="app")
            write_text(tmp / out_rel, site_env.get_template(tpl).render(**ctx_html))

        assets = site_dir / "assets"
        if assets.is_dir():
            shutil.copytree(assets, tmp / "assets", ignore=shutil.ignore_patterns(".gitkeep", "*.md"))
        write_text(tmp / "robots.txt", ROBOTS_TXT)
        write_text(tmp / "_headers", headers_file())
        plan.emit(tmp)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    _swap_dir(tmp, dist)

    files = [p for p in dist.rglob("*") if p.is_file()]
    for m in missing_media:
        warnings.append(f"нет медиафайла media/{m} — в dist ссылка src: null")
    report = BuildReport(
        dist=dist,
        stage_keys={n: b64u_encode(k) for n, k in keys.items()},
        page_keys=page_keys,
        todos=todos,
        warnings=warnings,
        missing_media=missing_media,
        files=len(files),
        size=sum(p.stat().st_size for p in files),
        seconds=time.monotonic() - t0,
    )
    return report


def format_report(rep: BuildReport) -> str:
    lines = [f"Сборка готова: {rep.dist} — {rep.files} файлов, {rep.size / 1024:.1f} КБ, {rep.seconds:.1f} с."]
    if rep.warnings:
        lines.append(f"Предупреждения ({len(rep.warnings)}):")
        lines += [f"  {w}" for w in rep.warnings]
    if rep.todos:
        by_kind: dict[str, int] = {}
        for t in rep.todos:
            by_kind[t.kind] = by_kind.get(t.kind, 0) + 1
        kinds = ", ".join(f"{k}: {v}" for k, v in sorted(by_kind.items()))
        lines.append(f"Заглушки TODO(content): {len(rep.todos)} ({kinds}); с --release это ошибка.")
        lines += [f"  {t}" for t in rep.todos]
    return "\n".join(lines)


