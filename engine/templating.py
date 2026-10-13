"""Шаблоны контента: Jinja2 в песочнице, ``StrictUndefined``.

В шаблонах доступны ``c`` (персонажи: ``c.zavyalov.full('gen')``) и ``w`` (мир:
``w.theater.short``). ``w`` — обёртка только с доступом через точку, а не ``dict``:
иначе ``w.money.items`` вернул бы метод словаря. Опечатка в имени персонажа или
ключа мира — ошибка с понятным текстом.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable

from jinja2 import StrictUndefined, TemplateError, TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment

from engine.models import Character
from engine.names import DeclensionError, Person
from engine.util import format_loc, iter_strings


class TemplateRefError(Exception):
    """Обращение к несуществующему персонажу, ключу мира или атрибуту."""


class RenderError(Exception):
    """Ошибка рендера строки контента: ``where`` — файл и путь до поля."""

    def __init__(self, where: str, msg: str, text: str = "") -> None:
        self.where = where
        self.msg = msg
        self.text = text
        snippet = " ".join(text.split())
        if len(snippet) > 80:
            snippet = snippet[:77] + "…"
        full = f"{where}: ошибка шаблона: {msg}" if where else f"ошибка шаблона: {msg}"
        if snippet:
            full += f" — в «{snippet}»"
        super().__init__(full)


class _PersonView(Person):
    """Person с понятной ошибкой на опечатку в имени метода (``c.x.fulll()``)."""

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        raise TemplateRefError(
            f"у персонажа «{self.id}» нет атрибута «{name}» "
            "(есть: full, short, io, first, last, middle, g, role, nick, age, id)"
        )


class CharactersNS:
    """``c`` в шаблонах: ``c.<id>`` → персонаж."""

    def __init__(self, characters: Iterable[Character]) -> None:
        self._by_id = {ch.id: _PersonView(ch) for ch in characters}

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._by_id[name]
        except KeyError:
            raise TemplateRefError(f"нет персонажа «{name}» (c.{name}) в characters.yaml") from None

    def __getitem__(self, name: str) -> Any:
        return self.__getattr__(name)

    def __str__(self) -> str:
        raise TemplateRefError("«c» — список персонажей; нужно c.<id>.<метод>()")


class WorldNS:
    """``w`` в шаблонах: раздел ``world.yaml`` с доступом через точку."""

    def __init__(self, data: dict, path: str = "w") -> None:
        self._data = data
        self._path = path

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._data:
            raise TemplateRefError(f"нет ключа «{self._path}.{name}» в world.yaml")
        return _wrap(self._data[name], f"{self._path}.{name}")

    def __getitem__(self, name: str) -> Any:
        return self.__getattr__(name)

    def __str__(self) -> str:
        raise TemplateRefError(f"«{self._path}» — раздел world.yaml, а не значение; укажите ключ внутри")


def _wrap(value: Any, path: str) -> Any:
    if isinstance(value, dict):
        return WorldNS(value, path)
    if isinstance(value, list):
        return [_wrap(v, f"{path}[{i}]") for i, v in enumerate(value)]
    return value


def make_content_env() -> SandboxedEnvironment:
    return SandboxedEnvironment(
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


_ENV = make_content_env()


@lru_cache(maxsize=8192)
def _compile(text: str):
    return _ENV.from_string(text)


def make_context(content: Any = None, *, characters: Iterable[Character] | None = None,
                 world: dict | None = None) -> dict[str, Any]:
    """Контекст шаблонов ``{"c": …, "w": …}`` из объекта Content или из частей."""
    if content is not None:
        characters = content.characters
        world = content.world
    return {"c": CharactersNS(characters or []), "w": WorldNS(world or {})}


def render(text: str, ctx: dict[str, Any], where: str = "") -> str:
    """Отрендерить строку контента. Ошибка → ``RenderError`` с ``where`` и текстом ошибки."""
    if "{" not in text:  # быстрый путь: ни выражений, ни тегов, ни комментариев
        return text
    try:
        return _compile(text).render(ctx)
    except TemplateSyntaxError as e:
        raise RenderError(where, f"синтаксис (строка {e.lineno} шаблона): {e.message}", text) from None
    except TemplateError as e:
        raise RenderError(where, str(e), text) from None
    except (TemplateRefError, DeclensionError) as e:
        raise RenderError(where, str(e), text) from None
    except TypeError as e:  # неверное число аргументов метода и т. п.
        raise RenderError(where, f"неверный вызов: {e}", text) from None


def render_tree(obj: Any, ctx: dict[str, Any], where: str = "", loc: tuple = ()) -> Any:
    """Рекурсивно отрендерить все строки дерева (ключи не трогаются)."""
    if isinstance(obj, str):
        sep = ": " if where else ""
        return render(obj, ctx, f"{where}{sep}{format_loc(loc)}" if loc else where)
    if isinstance(obj, dict):
        return {k: render_tree(v, ctx, where, (*loc, k)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [render_tree(v, ctx, where, (*loc, i)) for i, v in enumerate(obj)]
    return obj


def check_tree(obj: Any, ctx: dict[str, Any], file: str, loc: tuple = ()) -> list[tuple[str, str, str]]:
    """Отрендерить все строки дерева и собрать ошибки: ``[(file, loc, msg)]``."""
    errors: list[tuple[str, str, str]] = []
    for sub, s in iter_strings(obj, loc):
        try:
            render(s, ctx)
        except RenderError as e:
            errors.append((file, format_loc(sub), f"ошибка шаблона: {e.msg}"))
    return errors


# ---------------------------------------------------------------- Markdown и шаблоны сайта

_ISO_RE = __import__("re").compile(r"^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?$")


@lru_cache(maxsize=1)
def _md():
    from markdown_it import MarkdownIt

    return MarkdownIt("commonmark", {"html": False, "typographer": False})


def render_markdown(md: str) -> str:
    """Markdown → HTML (``html=False``: сырой HTML из контента экранируется)."""
    return _md().render(md)


def dt(value: Any, fmt: str = "datetime") -> str:
    """Даты мира игры (PLAN E8): ``2026-11-10T19:30`` → ``10.11.2026, 19:30``.

    ``fmt``: ``datetime`` (по умолчанию), ``date``, ``time``. Не-ISO строка (например,
    ``TODO(content)``) возвращается как есть.
    """
    if not isinstance(value, str):
        return "" if value is None else str(value)
    m = _ISO_RE.match(value.strip())
    if not m:
        return value
    y, mo, d, hh, mi, ss = m.groups()
    day = f"{d}.{mo}.{y}"
    tm = None if hh is None else (f"{hh}:{mi}:{ss}" if ss else f"{hh}:{mi}")
    if fmt == "date" or tm is None:
        return day
    if fmt == "time":
        return tm
    return f"{day}, {tm}"


def make_site_env(templates_dir: Any):
    """Jinja2 для ``site/templates/`` — автоэкранирование включено, ``StrictUndefined``."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(default=True, default_for_string=True),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["dt"] = dt
    return env
