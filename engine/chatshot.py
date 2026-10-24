"""``python -m engine chatshot`` — «скриншоты» телефона для бумажных документов (P07 п.2).

Вход — ``content/chats/<id>.yaml`` (схема ``engine.models.ChatFile``): экраны ``notification``
(экран блокировки), ``chat`` (вымышленный мессенджер ``w.brands.messenger``), ``calls``
(журнал вызовов). Выход — ``print/chats/<id>-<n>.png``, 1080 × 2340.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from engine import ROOT
from engine.content import Content, load_content
from engine.media import MEDIA_DIR
from engine.models import CallsScreen, ChatScreen, NotificationScreen
from engine.templating import make_context, render

PRINT_CHATS = ROOT / "print" / "chats"
WIDTH, HEIGHT = 1080, 2340
# Цвета аватарок-инициалов (без портрета): приглушённые, в палитре мессенджера.
AVATAR_COLORS = ("#8E5B9E", "#C0793A", "#4F7C82", "#A2525C", "#6F7A3A", "#5A6A9C", "#9C6B4F")


def plural(n: int, forms: tuple[str, str, str]) -> str:
    """1 участник, 2 участника, 5 участников."""
    a, b = abs(n) % 100, abs(n) % 10
    if 10 < a < 20:
        return forms[2]
    return forms[0] if b == 1 else forms[1] if 2 <= b <= 4 else forms[2]


def _initials(text: str) -> str:
    parts = [p for p in text.replace("TODO(content)", "?").split() if p]
    return "".join(p[0].upper() for p in parts[:2]) or "?"


def _color(key: str) -> str:
    return AVATAR_COLORS[hashlib.sha256(key.encode("utf-8")).digest()[0] % len(AVATAR_COLORS)]


class _People:
    def __init__(self, content: Content, ctx: dict, media_dir: Path) -> None:
        self.content = content
        self.c = ctx["c"]
        self.media_dir = media_dir

    def contact(self, pid: str | None, name: str | None = None) -> dict[str, Any]:
        """Как контакт записан в телефоне: «Имя Фамилия», портрет или инициалы."""
        if pid is None:
            label = name or "?"
            return {"name": label, "photo": None, "initials": _initials(label), "color": _color(label), "g": None}
        p = getattr(self.c, pid)
        label = name or " ".join(x for x in (p.first(), p.last()) if x)
        photo = self.content.characters_by_id[pid].photo
        src = (self.media_dir / photo) if photo else None
        return {
            "name": label,
            "photo": src.as_uri() if src is not None and src.is_file() else None,
            "initials": _initials(label),
            "color": _color(pid),
            "g": p.g,
        }


def screens_data(content: Content, chat_id: str, media_dir: Path = MEDIA_DIR) -> list[dict]:
    ctx = make_context(content)
    chat = content.chats[chat_id]
    people = _People(content, ctx, media_dir)
    where = f"content/chats/{chat_id}.yaml"

    def r(s: str | None, loc: str) -> str | None:
        return None if s is None else render(s, ctx, f"{where}: {loc}")

    out: list[dict] = []
    for i, sc in enumerate(chat.screens):
        loc = f"screens[{i}]"
        if isinstance(sc, NotificationScreen):
            out.append({
                "kind": "notification", "time": r(sc.time, f"{loc}.time"), "date": r(sc.date, f"{loc}.date"),
                "items": [{"app": r(it.app, f"{loc}.items[{j}].app"), "title": r(it.title, f"{loc}.items[{j}].title"),
                           "text": r(it.text, f"{loc}.items[{j}].text"), "time": r(it.time, f"{loc}.items[{j}].time"),
                           "color": _color(it.app)} for j, it in enumerate(sc.items)],
            })
        elif isinstance(sc, ChatScreen):
            msgs = []
            for j, m in enumerate(sc.messages):
                who = people.contact(m.from_, r(m.name, f"{loc}.messages[{j}].name"))
                msgs.append({
                    "mine": sc.owner is not None and m.from_ == sc.owner,
                    "author": who, "time": r(m.time, f"{loc}.messages[{j}].time"),
                    "text": r(m.text, f"{loc}.messages[{j}].text"), "status": m.status,
                })
            if sc.with_ is not None:
                peer = people.contact(sc.with_)
                header = {"name": peer["name"], "sub": peer["g"]("был в сети недавно", "была в сети недавно"),
                          "avatar": peer, "group": False}
            else:
                title = r(sc.title, f"{loc}.title") or ""
                senders = {(m["author"]["name"]) for m in msgs}
                k = len(senders) + (1 if sc.owner else 0)
                header = {"name": title, "sub": f"{k} {plural(k, ('участник', 'участника', 'участников'))}",
                          "avatar": {"name": title, "photo": None, "initials": _initials(title), "color": _color(title)},
                          "group": True}
            out.append({
                "kind": "chat", "time": r(sc.time, f"{loc}.time") or (msgs[-1]["time"] if msgs else ""),
                "date": r(sc.date, f"{loc}.date"), "header": header, "messages": msgs,
            })
        elif isinstance(sc, CallsScreen):
            out.append({
                "kind": "calls", "time": r(sc.time, f"{loc}.time"),
                "items": [{"who": people.contact(it.who, r(it.name, f"{loc}.items[{j}].name")),
                           "number": r(it.number, f"{loc}.items[{j}].number"),
                           "time": r(it.time, f"{loc}.items[{j}].time"), "direction": it.direction}
                          for j, it in enumerate(sc.items)],
            })
    return out


def render_chats(content: Content, out: Path = PRINT_CHATS, *, media_dir: Path = MEDIA_DIR,
                 only: list[str] | None = None, paper: bool = False) -> list[Path]:
    """``paper`` — вариант для бумаги конвертов (``engine paper``): светлый фон экранов и без чёрной рамки
    корпуса (рамку рисует бланк), чтобы лист не «съедал» краску (docs/05 §4)."""
    from engine.printing import browser, html_to_png, print_env

    env = print_env()
    tpl = env.get_template("print/chat.html")
    brand = content.world["brands"]["messenger"]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with browser() as b:
        for chat_id in content.chats:
            if only and chat_id not in only:
                continue
            for n, sc in enumerate(screens_data(content, chat_id, media_dir), 1):
                html = tpl.render(title=f"{chat_id} — {n}", screen=sc, brand=brand, width=WIDTH, height=HEIGHT,
                                  paper=paper)
                written.append(html_to_png(b, html, out / f"{chat_id}-{n}.png", width=WIDTH, height=HEIGHT))
    return written


def run(root: Path = ROOT, *, out: Path = PRINT_CHATS) -> list[Path]:
    content = load_content(Path(root) / "content")
    if not content.chats:
        from engine.build import BuildError

        raise BuildError(["нет файлов content/chats/*.yaml"])
    return render_chats(content, out, media_dir=Path(root) / "media")
