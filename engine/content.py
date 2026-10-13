"""Загрузка и перекрёстная валидация ``content/``.

``load_content(root)`` читает все YAML (UTF-8), проверяет их моделями
``engine/models.py``, затем — смысловые и перекрёстные правила docs/03 §5–6 и P03 п.1,
рендерит все строки шаблонов. Все ошибки собираются списком и поднимаются одним
``ContentError``; каждая — «файл: путь.до[поля]: что не так».

Отсутствующий файл текста (``body``, ``confession``, ``letter``) — не ошибка, а
заглушка (решение 4): попадает в ``Content.missing`` и в ``collect_todos``.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter
import yaml
from pydantic import BaseModel, ValidationError

from engine import ROOT
from engine.models import (
    CLOUD_FOLDER_FIELDS,
    ID_PATTERN,
    ID_TYPES,
    LIST_TYPES,
    MEDIA_MIME,
    PAGE_MODELS,
    Character,
    CharactersFile,
    CloudPage,
    DocFrontMatter,
    Document,
    DocumentsFile,
    ExpertiseFile,
    Finale,
    FormField,
    NewsPage,
    PageBase,
    Question,
    Settings,
    Stage,
    StagesFile,
    UnitSpec,
)
from engine.util import format_loc, iter_strings, read_text

CONTENT_DIR = ROOT / "content"
TODO_MARK = "TODO(content)"
_ID_RE = re.compile(ID_PATTERN)

YAML_FILES = (
    "settings.yaml",
    "world.yaml",
    "characters.yaml",
    "documents.yaml",
    "stages.yaml",
    "expertise.yaml",
    "finale.yaml",
)

# ---------------------------------------------------------------- ошибки и записи


@dataclass(frozen=True)
class ContentIssue:
    file: str
    loc: str
    msg: str

    def __str__(self) -> str:
        return f"{self.file}: {self.loc}: {self.msg}" if self.loc else f"{self.file}: {self.msg}"


class ContentError(Exception):
    """Ошибки контента. ``errors`` — список ``ContentIssue``."""

    def __init__(self, errors: list[ContentIssue]) -> None:
        self.errors = list(errors)
        super().__init__(self.report())

    def report(self) -> str:
        n = len(self.errors)
        head = f"Ошибки в контенте ({n}):"
        return "\n".join([head, *(f"  {e}" for e in self.errors)])


@dataclass(frozen=True)
class Todo:
    """Заглушка ``TODO(content)``. ``kind``: value — в значении, comment — в комментарии YAML,
    text — в тексте Markdown, missing-file — нет файла текста (будет заглушка)."""

    file: str
    loc: str
    text: str
    kind: str = "value"

    def __str__(self) -> str:
        return f"{self.file}: {self.loc}: {self.text}"


@dataclass
class DocFile:
    """Документ ``content/documents/*.md`` (или другой Markdown с front matter)."""

    path: str  # относительно content/
    meta_raw: dict
    meta: DocFrontMatter | None
    body: str


@dataclass(frozen=True)
class Unit:
    """Проверяемая единица: вопрос или поле формы. ``path`` — ``s<n>.<q>[.<field>]``."""

    path: str
    type: str
    kind: str
    stage: int
    question: Question
    field: FormField | None = None

    @property
    def spec(self) -> UnitSpec:
        return self.field if self.field is not None else self.question

    @property
    def leak_scan(self) -> bool:
        """Поле переопределяет вопрос; по умолчанию — искать."""
        for v in (self.field.leak_scan if self.field else None, self.question.leak_scan):
            if v is not None:
                return v
        return True


@dataclass
class Content:
    root: Path
    settings: Settings
    world: dict
    characters: list[Character]
    documents: list[Document]
    stages: list[Stage]
    expertise: ExpertiseFile
    finale: Finale
    pages: dict[str, PageBase]
    docs: dict[str, DocFile] = field(default_factory=dict)  # путь .md → документ с front matter
    texts: dict[str, str] = field(default_factory=dict)  # путь .md → текст (тела страниц)
    raw: dict[str, Any] = field(default_factory=dict)  # «content/…yaml» → разобранный YAML
    missing: list[Todo] = field(default_factory=list)
    warnings: list[ContentIssue] = field(default_factory=list)

    @property
    def characters_by_id(self) -> dict[str, Character]:
        return {c.id: c for c in self.characters}

    @property
    def documents_by_id(self) -> dict[str, Document]:
        return {d.id: d for d in self.documents}

    @property
    def last_stage(self) -> int:
        return max(s.n for s in self.stages)

    def stage(self, n: int) -> Stage:
        for s in self.stages:
            if s.n == n:
                return s
        raise KeyError(n)

    def pool(self, spec: UnitSpec) -> list[str]:
        """ID персонажей пула: ``default`` → все с ``in_pool: true`` в порядке characters.yaml."""
        return _resolve_pool(spec.pool, self.characters)

    def doc_for(self, rel: str) -> DocFile | None:
        return self.docs.get(rel)


def _resolve_pool(pool: Any, characters: list[Character]) -> list[str]:
    if pool == "default":
        return [c.id for c in characters if c.in_pool]
    return list(pool or [])


# ---------------------------------------------------------------- YAML


class _Loader(yaml.SafeLoader):
    """SafeLoader, который не прощает повторяющихся ключей."""


def _construct_mapping(loader: _Loader, node: yaml.MappingNode, deep: bool = False) -> dict:
    seen: set = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            dup = key in seen
        except TypeError:
            dup = False
        if dup:
            raise yaml.constructor.ConstructorError(
                None, None, f"повторяющийся ключ «{key}»", key_node.start_mark
            )
        try:
            seen.add(key)
        except TypeError:
            pass
    return loader.construct_mapping(node, deep)


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _yaml_error_text(e: yaml.YAMLError) -> str:
    mark = getattr(e, "problem_mark", None)
    problem = getattr(e, "problem", None) or str(e)
    if mark is not None:
        return f"ошибка YAML: {problem} (строка {mark.line + 1}, столбец {mark.column + 1})"
    return f"ошибка YAML: {problem}"


# ---------------------------------------------------------------- перевод ошибок pydantic

_TYPE_RU = {
    "str": "строка", "int": "целое число", "float": "дробное число", "bool": "true/false",
    "list": "список", "dict": "словарь", "NoneType": "пусто (null)", "date": "дата", "datetime": "дата-время",
}


def _got(value: Any) -> str:
    t = type(value).__name__
    shown = repr(value)
    if len(shown) > 60:
        shown = shown[:57] + "…"
    return f"получено: {_TYPE_RU.get(t, t)} {shown}"


def _pyd_msg(err: dict) -> str:
    t = err["type"]
    ctx = err.get("ctx") or {}
    inp = err.get("input")
    if t == "missing":
        return "обязательное поле отсутствует"
    if t == "extra_forbidden":
        return "лишнее поле (нет в схеме)"
    if t == "string_type":
        hint = " (даты и время в YAML берите в кавычки)" if type(inp).__name__ in ("date", "datetime") else ""
        return f"ожидается строка, {_got(inp)}{hint}"
    if t in ("int_type", "int_parsing", "int_from_float"):
        return f"ожидается целое число, {_got(inp)}"
    if t == "bool_type":
        return f"ожидается true или false, {_got(inp)}"
    if t == "list_type":
        return f"ожидается список, {_got(inp)}"
    if t in ("dict_type", "model_type", "model_attributes_type"):
        return f"ожидается словарь (набор полей), {_got(inp)}"
    if t == "literal_error":
        return f"недопустимое значение {inp!r}; допустимы: {ctx.get('expected')}"
    if t == "string_pattern_mismatch":
        if ctx.get("pattern") == ID_PATTERN:
            return f"ID {inp!r}: допустимы только строчные латинские буквы, цифры, «_» и «-»"
        return f"значение {inp!r} не соответствует шаблону {ctx.get('pattern')}"
    if t == "greater_than":
        return f"должно быть больше {ctx.get('gt')}, {_got(inp)}"
    if t == "greater_than_equal":
        return f"должно быть не меньше {ctx.get('ge')}, {_got(inp)}"
    if t == "too_short":
        return "список не должен быть пустым"
    if t == "value_error":
        return str(err.get("msg", "")).removeprefix("Value error, ")
    return str(err.get("msg", t))


def _pyd_issues(file: str, exc: ValidationError, prefix: tuple = ()) -> list[ContentIssue]:
    return [
        ContentIssue(file, format_loc((*prefix, *e["loc"])), _pyd_msg(e))
        for e in exc.errors(include_url=False)
    ]


# ---------------------------------------------------------------- загрузка


class _Loading:
    """Состояние одной загрузки: корень, ошибки, предупреждения, заглушки."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.errors: list[ContentIssue] = []
        self.warnings: list[ContentIssue] = []
        self.missing: list[Todo] = []
        self.raw: dict[str, Any] = {}
        self.page_slugs: set[str] = set()  # папки pages/ с page.yaml (даже если схема не прошла)

    # имя файла в сообщениях: «content/stages.yaml»
    def name(self, rel: str) -> str:
        return f"{self.root.name}/{rel}"

    def err(self, rel: str, loc: tuple | str, msg: str) -> None:
        loc_s = loc if isinstance(loc, str) else format_loc(loc)
        self.errors.append(ContentIssue(self.name(rel), loc_s, msg))

    def warn(self, rel: str, loc: tuple | str, msg: str) -> None:
        loc_s = loc if isinstance(loc, str) else format_loc(loc)
        self.warnings.append(ContentIssue(self.name(rel), loc_s, msg))

    def read_yaml(self, rel: str) -> Any:
        path = self.root / rel
        if not path.is_file():
            self.err(rel, "", "файл не найден")
            return None
        try:
            data = yaml.load(read_text(path), Loader=_Loader)  # noqa: S506 — SafeLoader-наследник
        except yaml.YAMLError as e:
            self.err(rel, "", _yaml_error_text(e))
            return None
        self.raw[self.name(rel)] = data
        return data

    def model(self, rel: str, cls: type[BaseModel], data: Any, prefix: tuple = ()) -> Any:
        if data is None:
            if (self.root / rel).is_file() and self.name(rel) in self.raw:
                self.err(rel, "", "файл пуст")
            return None
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            for issue in _pyd_issues(self.name(rel), e, prefix):
                self.errors.append(issue)
            return None

    def text_path(self, ref_rel: str, loc: tuple, value: str) -> Path | None:
        """Путь к тексту относительно content/; вне content/ — ошибка; отсутствует — заглушка."""
        p = (self.root / value).resolve()
        try:
            p.relative_to(self.root.resolve())
        except ValueError:
            self.err(ref_rel, loc, f"путь «{value}» выходит за пределы content/")
            return None
        if not p.is_file():
            self.missing.append(
                Todo(self.name(ref_rel), format_loc(loc), f"нет файла {self.root.name}/{value} — будет заглушка",
                     "missing-file")
            )
            return None
        return p


def _dupes(ids: list[str]) -> set[str]:
    return {k for k, n in Counter(ids).items() if n > 1}


def _check_unique(ld: _Loading, rel: str, items: list, base: tuple, what: str = "ID",
                  key: str = "id") -> None:
    seen: dict[str, int] = {}
    for i, it in enumerate(items):
        v = getattr(it, key)
        if v in seen:
            ld.err(rel, (*base, i, key), f"дубликат {what} «{v}» (уже есть в {format_loc((*base, seen[v]))})")
        else:
            seen[v] = i


def load_content(root: Path | str = CONTENT_DIR) -> Content:
    """Прочитать и проверить ``content/``. Ошибки → ``ContentError`` со списком."""
    ld = _Loading(Path(root))

    settings = ld.model("settings.yaml", Settings, ld.read_yaml("settings.yaml"))

    world_raw = ld.read_yaml("world.yaml")
    world: dict | None = None
    if world_raw is not None:
        if isinstance(world_raw, dict):
            world = world_raw
            _check_world(ld, world)
        else:
            ld.err("world.yaml", "", "ожидается словарь (ключ: значение) на верхнем уровне")

    ch_file = ld.model("characters.yaml", CharactersFile, ld.read_yaml("characters.yaml"))
    characters = ch_file.characters if ch_file else None
    docs_file = ld.model("documents.yaml", DocumentsFile, ld.read_yaml("documents.yaml"))
    documents = docs_file.documents if docs_file else None
    st_file = ld.model("stages.yaml", StagesFile, ld.read_yaml("stages.yaml"))
    stages = st_file.stages if st_file else None
    expertise = ld.model("expertise.yaml", ExpertiseFile, ld.read_yaml("expertise.yaml"))
    finale = ld.model("finale.yaml", Finale, ld.read_yaml("finale.yaml"))
    pages = _load_pages(ld)

    if characters is not None:
        _check_characters(ld, characters)
    if documents is not None:
        _check_documents(ld, documents, stages, pages)
    if stages is not None:
        _check_stages(ld, stages, settings, characters, documents)

    docs: dict[str, DocFile] = {}
    texts: dict[str, str] = {}
    if expertise is not None:
        _check_expertise(ld, expertise, stages, documents, docs)
    if finale is not None:
        _check_finale(ld, finale, characters, docs)
    _check_doc_ids(ld, docs)
    if pages is not None:
        _check_pages(ld, pages, characters, documents, texts)

    for use in media_refs(characters or [], pages or {}, docs, name=ld.name):
        _check_media(ld, use)

    if characters is not None and world is not None:
        _check_templates(ld, characters, world, docs, texts)

    if ld.errors:
        raise ContentError(ld.errors)

    return Content(
        root=ld.root,
        settings=settings,
        world=world,
        characters=characters,
        documents=documents,
        stages=stages,
        expertise=expertise,
        finale=finale,
        pages=pages,
        docs=docs,
        texts=texts,
        raw=ld.raw,
        missing=ld.missing,
        warnings=ld.warnings,
    )


# ---------------------------------------------------------------- проверки по файлам


def _check_world(ld: _Loading, world: dict) -> None:
    def walk(obj: Any, loc: tuple) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if not isinstance(k, str) or not k.isidentifier() or k.startswith("_"):
                    ld.err("world.yaml", loc, f"ключ «{k}» недоступен в шаблонах: нужна латиница, цифры, «_», "
                                              "не с цифры и не с «_»")
                walk(v, (*loc, str(k)))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, (*loc, i))
        elif obj is None or not isinstance(obj, (str, int, float, bool)):
            hint = " (даты и время берите в кавычки)" if type(obj).__name__ in ("date", "datetime") else ""
            ld.err("world.yaml", loc, f"значение должно быть строкой или числом, {_got(obj)}{hint}")

    walk(world, ())


def _check_characters(ld: _Loading, characters: list[Character]) -> None:
    rel = "characters.yaml"
    _check_unique(ld, rel, characters, ("characters",))
    for i, ch in enumerate(characters):
        if not ch.last.strip() and not ch.first.strip():
            ld.err(rel, ("characters", i), "у персонажа пустые и фамилия, и имя")
        if ch.in_pool and ch.importance in ("service", "background"):
            ld.warn(rel, ("characters", i, "in_pool"),
                    f"in_pool: true у персонажа с importance: {ch.importance}")


def _check_documents(ld: _Loading, documents: list[Document], stages: list[Stage] | None,
                     pages: dict[str, PageBase] | None) -> None:
    rel = "documents.yaml"
    _check_unique(ld, rel, documents, ("documents",))
    stage_ns = {s.n for s in stages} if stages else None
    for i, d in enumerate(documents):
        loc = ("documents", i)
        if stage_ns is not None and d.stage not in stage_ns:
            ld.err(rel, (*loc, "stage"), f"этапа {d.stage} нет в stages.yaml")
        if d.kind == "online" and d.page is None:
            ld.err(rel, (*loc, "page"), "у документа kind: online должно быть поле page")
        if d.kind == "lab" and d.page is not None:
            ld.err(rel, (*loc, "page"), "у документа kind: lab не бывает page")
        if d.page is not None and pages is not None and d.page not in ld.page_slugs:
            ld.err(rel, (*loc, "page"), f"страницы «{d.page}» нет в content/pages/")


def _check_stages(ld: _Loading, stages: list[Stage], settings: Settings | None,
                  characters: list[Character] | None, documents: list[Document] | None) -> None:
    rel = "stages.yaml"
    last = max(s.n for s in stages)
    n_hints = len(settings.hints.cost) if settings else None
    char_ids = {c.id for c in characters} if characters is not None else None
    doc_ids = {d.id for d in documents} if documents is not None else None
    for si, st in enumerate(stages):
        sloc = ("stages", si)
        if st.n != si + 1:
            ld.err(rel, (*sloc, "n"), f"этапы должны идти по порядку 1, 2, …; здесь ожидался n: {si + 1}")
        if st.n < last and not st.on_complete:
            ld.err(rel, (*sloc, "on_complete"), "у этапа, кроме последнего, должно быть on_complete")
        if st.n == last and st.on_complete is not None:
            ld.err(rel, (*sloc, "on_complete"), "у последнего этапа не бывает on_complete")
        _check_unique(ld, rel, st.questions, (*sloc, "questions"))
        for qi, q in enumerate(st.questions):
            qloc = (*sloc, "questions", qi)
            if q.kind == "final" and st.n != last:
                ld.err(rel, (*qloc, "kind"), f"kind: final допустим только в последнем этапе ({last})")
            if q.kind == "mandatory" and st.n == last:
                ld.err(rel, (*qloc, "kind"), "в последнем этапе нет обязательных вопросов (только final и bonus)")
            if q.kind == "mandatory":
                if n_hints is not None and len(q.hints) != n_hints:
                    ld.err(rel, (*qloc, "hints"),
                           f"у обязательного вопроса должно быть ровно {n_hints} подсказки "
                           f"(по числу уровней settings.hints.cost), сейчас {len(q.hints)}")
            elif q.hints:
                ld.err(rel, (*qloc, "hints"), f"у вопроса kind: {q.kind} подсказок быть не должно "
                                              f"(сейчас {len(q.hints)})")
            if q.type == "form":
                if not q.fields:
                    ld.err(rel, (*qloc, "fields"), "у вопроса type: form должны быть поля fields")
                for name in ("answer", "options", "pool", "items"):
                    if getattr(q, name) is not None:
                        ld.err(rel, (*qloc, name), f"у вопроса type: form поле {name} задаётся в fields, "
                                                   "а не на вопросе")
                for fi, f in enumerate(q.fields or []):
                    _check_unit(ld, rel, f, (*qloc, "fields", fi), characters, char_ids, doc_ids)
                _check_unique(ld, rel, q.fields or [], (*qloc, "fields"))
            else:
                if q.fields is not None:
                    ld.err(rel, (*qloc, "fields"), f"fields допустимы только у type: form, а здесь type: {q.type}")
                _check_unit(ld, rel, q, qloc, characters, char_ids, doc_ids)


def _check_unit(ld: _Loading, rel: str, spec: UnitSpec, loc: tuple, characters: list[Character] | None,
                char_ids: set[str] | None, doc_ids: set[str] | None) -> None:
    """Проверки одной единицы (вопрос не-form или поле формы)."""
    t = spec.type
    # Поля, применимые только к некоторым типам.
    allowed = {"options": ("choice", "multi"), "pool": ("person", "persons"), "items": ("order",)}
    for name, types in allowed.items():
        val = getattr(spec, name)
        if t in types:
            if not val:
                ld.err(rel, (*loc, name), f"у type: {t} должно быть непустое поле {name}")
        elif val is not None:
            ld.err(rel, (*loc, name), f"поле {name} не применимо к type: {t} (только {', '.join(types)})")
    if spec.options:
        _check_unique(ld, rel, spec.options, (*loc, "options"))
    if spec.items:
        _check_unique(ld, rel, spec.items, (*loc, "items"))
    pool_ids: list[str] | None = None
    if isinstance(spec.pool, list):
        for i, cid in enumerate(spec.pool):
            if char_ids is not None and cid not in char_ids:
                ld.err(rel, (*loc, "pool", i), f"персонажа «{cid}» нет в characters.yaml")
        for d in sorted(_dupes(spec.pool)):
            ld.err(rel, (*loc, "pool"), f"персонаж «{d}» указан в pool несколько раз")
    if spec.pool is not None and characters is not None:
        pool_ids = _resolve_pool(spec.pool, characters)

    ans = spec.answer
    if ans is None:
        ld.err(rel, (*loc, "answer"), "нет ответа (answer)")
        return
    aloc = (*loc, "answer")
    if ans.tolerance_min is not None and t != "time":
        ld.err(rel, (*aloc, "tolerance_min"), f"tolerance_min применим только к type: time, а здесь type: {t}")
    canon = ans.canon
    if t in LIST_TYPES:
        if not isinstance(canon, list):
            ld.err(rel, (*aloc, "canon"), f"для type: {t} ответ — список ID")
            return
        if not canon:
            ld.err(rel, (*aloc, "canon"), "ответ не должен быть пустым списком")
            return
    elif not isinstance(canon, str):
        ld.err(rel, (*aloc, "canon"), f"для type: {t} ответ — строка, а не список")
        return
    elif not canon.strip():
        ld.err(rel, (*aloc, "canon"), "пустой ответ")
        return

    if t not in ID_TYPES:
        for i, v in enumerate(ans.variants):
            if not v.strip():
                ld.err(rel, (*aloc, "variants", i), "пустой вариант ответа")
        return

    # --- ответы-ID
    if ans.variants:
        ld.err(rel, (*aloc, "variants"), f"у type: {t} ответ — ID, вариантов (variants) не бывает")
    ids = canon if isinstance(canon, list) else [canon]
    cloc = (*aloc, "canon")

    def at(i: int) -> tuple:
        return (*cloc, i) if isinstance(canon, list) else cloc

    ok_ids: list[tuple[int, str]] = []
    for i, v in enumerate(ids):
        if not _ID_RE.match(v):
            ld.err(rel, at(i), f"ID ответа «{v}»: только строчные латинские буквы, цифры, «_» и «-»")
        else:
            ok_ids.append((i, v))
    if t != "order":
        for d in sorted(_dupes(ids)):
            ld.err(rel, cloc, f"ID «{d}» указан в ответе несколько раз")

    if t in ("choice", "multi") and spec.options:
        opt = [o.id for o in spec.options]
        for i, v in ok_ids:
            if v not in opt:
                ld.err(rel, at(i), f"варианта «{v}» нет среди options ({', '.join(opt)})")
    elif t in ("person", "persons"):
        for i, v in ok_ids:
            if char_ids is not None and v not in char_ids:
                ld.err(rel, at(i), f"персонажа «{v}» нет в characters.yaml")
            elif pool_ids is not None and v not in pool_ids:
                ld.err(rel, at(i), f"персонаж «{v}» не входит в pool вопроса")
    elif t == "document":
        for i, v in ok_ids:
            if doc_ids is not None and v not in doc_ids:
                ld.err(rel, at(i), f"документа «{v}» нет в documents.yaml")
    elif t == "order" and spec.items:
        item_ids = [it.id for it in spec.items]
        for i, v in ok_ids:
            if v not in item_ids:
                ld.err(rel, at(i), f"карточки «{v}» нет в items")
        counts = Counter(ids)
        for v, n in counts.items():
            if n > 1:
                ld.err(rel, cloc, f"карточка «{v}» указана в ответе {n} раз(а), нужно ровно один")
        absent = [x for x in item_ids if x not in counts]
        if absent:
            ld.err(rel, cloc, f"в ответе нет карточек: {', '.join(absent)} — каждая карточка должна быть ровно один раз")


def _load_doc(ld: _Loading, ref_rel: str, loc: tuple, value: str, docs: dict[str, DocFile]) -> DocFile | None:
    """Прочитать Markdown с front matter (если есть); результат кешируется в ``docs``."""
    if value in docs:
        return docs[value]
    p = ld.text_path(ref_rel, loc, value)
    if p is None:
        return None
    try:
        post = frontmatter.loads(read_text(p))
    except yaml.YAMLError as e:
        ld.err(value, "front matter", _yaml_error_text(e))
        return None
    meta_raw = dict(post.metadata)
    meta: DocFrontMatter | None = None
    try:
        meta = DocFrontMatter.model_validate(meta_raw)
    except ValidationError as e:
        for issue in _pyd_issues(ld.name(value), e, ("front matter",)):
            ld.errors.append(issue)
    doc = DocFile(path=value, meta_raw=meta_raw, meta=meta, body=post.content)
    docs[value] = doc
    return doc


def _check_expertise(ld: _Loading, exp: ExpertiseFile, stages: list[Stage] | None,
                     documents: list[Document] | None, docs: dict[str, DocFile]) -> None:
    rel = "expertise.yaml"
    _check_unique(ld, rel, exp.objects, ("objects",))
    _check_unique(ld, rel, exp.types, ("types",))
    _check_unique(ld, rel, exp.results, ("results",))
    stage_ns = {s.n for s in stages} if stages else None
    docs_by_id = {d.id: d for d in documents} if documents is not None else None
    objects = {o.id: o for o in exp.objects}
    type_ids = {t.id for t in exp.types}

    for oi, o in enumerate(exp.objects):
        if stage_ns is not None and o.from_stage not in stage_ns:
            ld.err(rel, ("objects", oi, "from_stage"), f"этапа {o.from_stage} нет в stages.yaml")
        if o.params is not None:
            if not o.params:
                ld.err(rel, ("objects", oi, "params"), "пустой список params — уберите поле")
            _check_unique(ld, rel, o.params, ("objects", oi, "params"))

    combos: dict[tuple, int] = {}
    for ri, r in enumerate(exp.results):
        loc = ("results", ri)
        obj = objects.get(r.object)
        if obj is None:
            ld.err(rel, (*loc, "object"), f"объекта «{r.object}» нет в objects")
        for ti, t in enumerate(r.types):
            if t not in type_ids:
                ld.err(rel, (*loc, "types", ti), f"вида исследования «{t}» нет в types")
        for d in sorted(_dupes(r.types)):
            ld.err(rel, (*loc, "types"), f"вид «{d}» указан несколько раз")
        if stage_ns is not None and r.stage not in stage_ns:
            ld.err(rel, (*loc, "stage"), f"этапа {r.stage} нет в stages.yaml")
        if obj is not None and obj.from_stage > r.stage:
            ld.err(rel, (*loc, "stage"), f"объект «{obj.id}» появляется с этапа {obj.from_stage}, "
                                         f"а результат открывается на этапе {r.stage}")
        for bi, b in enumerate(r.bases):
            if docs_by_id is None:
                break
            bd = docs_by_id.get(b)
            if bd is None:
                ld.err(rel, (*loc, "bases", bi), f"документа «{b}» нет в documents.yaml")
            elif bd.stage > r.stage:
                ld.err(rel, (*loc, "bases", bi), f"основание «{b}» появляется на этапе {bd.stage}, "
                                                 f"а результат открывается на этапе {r.stage}")
        for d in sorted(_dupes(r.bases)):
            ld.err(rel, (*loc, "bases"), f"основание «{d}» указано несколько раз")

        # doc + body (документ) или text (атмосферный результат)
        if r.doc is not None or r.body is not None:
            if r.doc is None:
                ld.err(rel, (*loc, "doc"), "у результата с body должно быть doc")
            if r.body is None:
                ld.err(rel, (*loc, "body"), "у результата с doc должно быть body")
            if r.text is not None:
                ld.err(rel, (*loc, "text"), "у результата-документа (doc + body) не бывает text")
        elif r.text is None:
            ld.err(rel, loc, "нужен либо doc + body (документ), либо text (атмосферный результат)")
        if r.doc is not None and docs_by_id is not None:
            dd = docs_by_id.get(r.doc)
            if dd is None:
                ld.err(rel, (*loc, "doc"), f"документа «{r.doc}» нет в documents.yaml")
            elif dd.kind != "lab":
                ld.err(rel, (*loc, "doc"), f"документ «{r.doc}» должен быть kind: lab, а он kind: {dd.kind}")
            elif dd.stage != r.stage:
                ld.warn(rel, (*loc, "doc"), f"документ «{r.doc}» числится на этапе {dd.stage}, "
                                            f"результат — на этапе {r.stage}")
        if r.body is not None:
            df = _load_doc(ld, rel, (*loc, "body"), r.body, docs)
            if df is not None and df.meta is not None and r.doc is not None:
                if df.meta.id != r.doc:
                    ld.err(r.body, "front matter.id", f"id «{df.meta.id}» не совпадает с doc результата «{r.doc}» "
                                                      f"({ld.name(rel)}: {format_loc(loc)})")
                dd = docs_by_id.get(r.doc) if docs_by_id else None
                if dd is not None and df.meta.title != dd.title:
                    ld.err(r.body, "front matter.title",
                           f"заголовок не совпадает с documents.yaml («{dd.title}»)")

        # параметры запроса
        params = (obj.params or []) if obj is not None else None
        if params is not None:
            pids = [p.id for p in params]
            if params:
                if r.params_answer is None:
                    ld.err(rel, (*loc, "params_answer"),
                           f"у объекта «{obj.id}» есть params — нужен params_answer со всеми параметрами "
                           f"({', '.join(pids)})")
                else:
                    for pid in pids:
                        if pid not in r.params_answer:
                            ld.err(rel, (*loc, "params_answer"), f"нет параметра «{pid}»")
                    ptypes = {p.id: p.type for p in params}
                    for pid, ans in r.params_answer.items():
                        aloc = (*loc, "params_answer", pid)
                        if pid not in ptypes:
                            ld.err(rel, aloc, f"у объекта «{obj.id}» нет параметра «{pid}»")
                            continue
                        if not isinstance(ans.canon, str) or not ans.canon.strip():
                            ld.err(rel, (*aloc, "canon"), "ответ параметра — непустая строка")
                        if ans.tolerance_min is not None and ptypes[pid] != "time":
                            ld.err(rel, (*aloc, "tolerance_min"),
                                   f"tolerance_min применим только к time, а параметр — {ptypes[pid]}")
            elif r.params_answer is not None:
                ld.err(rel, (*loc, "params_answer"), f"у объекта «{obj.id}» нет params — params_answer не нужен")

            if not params:
                for t in r.types:
                    for b in r.bases:
                        key = (r.object, t, b, r.stage)
                        if key in combos:
                            ld.err(rel, loc, f"запрос «{r.object} / {t} / {b}» на этапе {r.stage} уже даёт "
                                             f"results[{combos[key]}]")
                        else:
                            combos[key] = ri

    if docs_by_id is not None:
        produced = {r.doc for r in exp.results if r.doc}
        for di, d in enumerate(documents or []):
            if d.kind == "lab" and d.id not in produced:
                ld.err("documents.yaml", ("documents", di),
                       f"документ kind: lab «{d.id}» не выдаёт ни один результат expertise.yaml")


def _check_finale(ld: _Loading, fin: Finale, characters: list[Character] | None,
                  docs: dict[str, DocFile]) -> None:
    rel = "finale.yaml"
    char_ids = {c.id for c in characters} if characters is not None else None
    for fi, f in enumerate(fin.fates):
        if f.who is not None and char_ids is not None and f.who not in char_ids:
            ld.err(rel, ("fates", fi, "who"), f"персонажа «{f.who}» нет в characters.yaml")
    whos = [f.who for f in fin.fates if f.who is not None]
    for d in sorted(_dupes(whos)):
        ld.warn(rel, "fates", f"судьба персонажа «{d}» указана несколько раз")
    for name in ("confession", "letter"):
        _load_doc(ld, rel, (name,), getattr(fin, name), docs)


def _check_doc_ids(ld: _Loading, docs: dict[str, DocFile]) -> None:
    seen: dict[str, str] = {}
    for path, df in docs.items():
        if df.meta is None:
            continue
        if df.meta.id in seen and seen[df.meta.id] != path:
            ld.err(path, "front matter.id", f"дубликат id «{df.meta.id}» (уже в {ld.name(seen[df.meta.id])})")
        else:
            seen[df.meta.id] = path


def _load_pages(ld: _Loading) -> dict[str, PageBase] | None:
    pages_dir = ld.root / "pages"
    if not pages_dir.is_dir():
        ld.err("pages", "", "папка не найдена")
        return None
    pages: dict[str, PageBase] = {}
    for d in sorted(p for p in pages_dir.iterdir() if p.is_dir()):
        slug = d.name
        rel = f"pages/{slug}/page.yaml"
        if not (d / "page.yaml").is_file():
            ld.err(f"pages/{slug}", "", "нет файла page.yaml")
            continue
        ld.page_slugs.add(slug)
        data = ld.read_yaml(rel)
        if data is None:
            continue
        cls = PAGE_MODELS.get(slug)
        if cls is None:
            ld.err(rel, "", f"нет схемы для страницы «{slug}» (известны: {', '.join(PAGE_MODELS)})")
            continue
        if isinstance(data, dict) and data.get("slug") != slug:
            ld.err(rel, "slug", f"slug должен совпадать с именем папки «{slug}»")
            continue
        page = ld.model(rel, cls, data)
        if page is not None:
            pages[slug] = page
    return pages


def _check_pages(ld: _Loading, pages: dict[str, PageBase], characters: list[Character] | None,
                 documents: list[Document] | None, texts: dict[str, str]) -> None:
    char_ids = {c.id for c in characters} if characters is not None else None
    docs_by_id = {d.id: d for d in documents} if documents is not None else None

    def body(rel: str, loc: tuple, value: str) -> None:
        p = ld.text_path(rel, loc, value)
        if p is not None:
            texts[value] = read_text(p)

    for slug, page in pages.items():
        rel = f"pages/{slug}/page.yaml"
        if docs_by_id is not None:
            d = docs_by_id.get(page.doc)
            if d is None:
                ld.err(rel, "doc", f"документа «{page.doc}» нет в documents.yaml")
            elif d.page != slug:
                ld.err(rel, "doc", f"документ «{page.doc}» в documents.yaml ссылается на страницу "
                                   f"«{d.page}», а не на «{slug}»")
        if page.locked == "password" and not isinstance(page, CloudPage):
            ld.err(rel, "locked", "locked: password поддерживается только страницей с паролем (cloud)")
        if isinstance(page, CloudPage):
            if page.locked != "password":
                ld.err(rel, "locked", "у страницы с password должно быть locked: password")
            if not page.password.strip():
                ld.err(rel, "password", "пустой пароль")
            _check_unique(ld, rel, page.folders, ("folders",))
            for fi, f in enumerate(page.folders):
                floc = ("folders", fi)
                need = CLOUD_FOLDER_FIELDS[f.kind]
                for name in ("columns", "rows", "participants", "messages", "body"):
                    present = getattr(f, name) is not None
                    if name in need and not present:
                        ld.err(rel, (*floc, name), f"у папки kind: {f.kind} должно быть поле {name}")
                    elif name not in need and present:
                        ld.err(rel, (*floc, name), f"поле {name} не применимо к папке kind: {f.kind}")
                if f.columns is not None and f.rows is not None:
                    for ri, row in enumerate(f.rows):
                        if len(row) != len(f.columns):
                            ld.err(rel, (*floc, "rows", ri),
                                   f"в строке {len(row)} ячеек, а колонок {len(f.columns)}")
                if char_ids is not None:
                    for pi, cid in enumerate(f.participants or []):
                        if cid not in char_ids:
                            ld.err(rel, (*floc, "participants", pi), f"персонажа «{cid}» нет в characters.yaml")
                    for mi, m in enumerate(f.messages or []):
                        if m.from_ not in (f.participants or []):
                            ld.err(rel, (*floc, "messages", mi, "from"),
                                   f"«{m.from_}» не входит в participants папки")
                if f.body is not None:
                    body(rel, (*floc, "body"), f.body)
        profile = getattr(page, "profile", None)
        if profile is not None and char_ids is not None and profile.person not in char_ids:
            ld.err(rel, "profile.person", f"персонажа «{profile.person}» нет в characters.yaml")
        if isinstance(page, NewsPage):
            body(rel, ("article", "body"), page.article.body)


@dataclass(frozen=True)
class MediaUse:
    """Ссылка на файл из ``media/``: где упомянут (файл, путь до поля) и в каком контексте.

    ``context``: ``portrait`` — портрет персонажа (всегда открытый, решение 5);
    ``open`` — открытая страница; ``locked`` — закрытая страница или документ (шифруется).
    """

    file: str
    loc: str
    path: str
    context: str


def media_refs(characters: list[Character], pages: dict[str, PageBase], docs: dict[str, DocFile],
               *, name=lambda rel: f"content/{rel}") -> list[MediaUse]:
    """Все ссылки на медиа в контенте (пути относительно ``media/``)."""
    out: list[MediaUse] = []
    for i, ch in enumerate(characters):
        if ch.photo:
            out.append(MediaUse(name("characters.yaml"), format_loc(("characters", i, "photo")), ch.photo,
                                "portrait"))
    for slug, page in pages.items():
        f = name(f"pages/{slug}/page.yaml")
        ctx = "open" if page.locked is False else "locked"
        refs: list[tuple[tuple, str | None]] = []
        for attr in ("audio", "video"):
            refs.append(((attr,), getattr(page, attr, None)))
        profile = getattr(page, "profile", None)
        if profile is not None:
            for attr in ("avatar", "cover"):
                refs.append((("profile", attr), getattr(profile, attr, None)))
        for pi, post in enumerate(getattr(page, "posts", None) or []):
            refs.append((("posts", pi, "photo"), getattr(post, "photo", None)))
        article = getattr(page, "article", None)
        if article is not None:
            refs.append((("article", "photo"), article.photo))
        for loc, value in refs:
            if value:
                out.append(MediaUse(f, format_loc(loc), value, ctx))
    for path, df in docs.items():
        if df.meta is not None:
            for mi, value in enumerate(df.meta.media):
                out.append(MediaUse(name(path), format_loc(("front matter", "media", mi)), value, "locked"))
    return out


def _check_media(ld: _Loading, use: MediaUse) -> None:
    """Путь медиа: относительный внутри media/, расширение из FORMATS §5. Отсутствие файла — не ошибка."""
    v = use.path
    parts = v.replace("\\", "/").split("/")
    if v.startswith("/") or "\\" in v or ".." in parts or ":" in v:
        ld.errors.append(ContentIssue(use.file, use.loc, f"путь медиа «{v}» должен быть относительным "
                                                         "внутри media/ (через «/», без «..»)"))
        return
    ext = Path(v).suffix.lower()
    if ext not in MEDIA_MIME:
        ld.errors.append(ContentIssue(use.file, use.loc, f"расширение «{ext or '(нет)'}» у «{v}» не поддерживается; "
                                                         f"допустимы: {', '.join(MEDIA_MIME)}"))


def _check_templates(ld: _Loading, characters: list[Character], world: dict,
                     docs: dict[str, DocFile], texts: dict[str, str]) -> None:
    """Отрендерить все строки контента: опечатка в шаблоне — ошибка с путём до поля."""
    from engine.templating import check_tree, make_context

    ctx = make_context(characters=characters, world=world)
    world_name = ld.name("world.yaml")
    for fname, data in ld.raw.items():
        if fname == world_name:  # мир — источник данных для шаблонов, а не шаблон
            continue
        for f, loc, msg in check_tree(data, ctx, fname):
            ld.errors.append(ContentIssue(f, loc, msg))
    for path, df in docs.items():
        for f, loc, msg in check_tree(df.meta_raw, ctx, ld.name(path), ("front matter",)):
            ld.errors.append(ContentIssue(f, loc, msg))
        for f, loc, msg in check_tree(df.body, ctx, ld.name(path), ("текст",)):
            ld.errors.append(ContentIssue(f, loc, msg))
    for path, text in texts.items():
        for f, loc, msg in check_tree(text, ctx, ld.name(path), ("текст",)):
            ld.errors.append(ContentIssue(f, loc, msg))


# ---------------------------------------------------------------- единицы


def units(content: Content) -> list[Unit]:
    """Все проверяемые единицы по порядку: этапы → вопросы → поля формы."""
    out: list[Unit] = []
    for st in content.stages:
        for q in st.questions:
            if q.type == "form":
                for f in q.fields or []:
                    out.append(Unit(f"s{st.n}.{q.id}.{f.id}", f.type, q.kind, st.n, q, f))
            else:
                out.append(Unit(f"s{st.n}.{q.id}", q.type, q.kind, st.n, q, None))
    return out


# ---------------------------------------------------------------- заглушки


def _comment_start(line: str) -> int:
    """Индекс «#», с которого начинается комментарий YAML, или -1 (кавычки учитываются)."""
    quote: str | None = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\" and quote == '"':
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return i
        i += 1
    return -1


def _todo_line(s: str) -> str:
    for line in s.splitlines():
        if TODO_MARK in line:
            return line.strip()
    return s.strip()


def collect_todos(content: Content) -> list[Todo]:
    """Все ``TODO(content)``: в значениях YAML (с путём до поля), в комментариях YAML
    (с номером строки), в текстах Markdown и отсутствующие файлы текстов."""
    todos: list[Todo] = []
    root = content.root
    prefix = f"{root.name}/"
    for fname, data in content.raw.items():
        for loc, s in iter_strings(data):
            if TODO_MARK in s:
                todos.append(Todo(fname, format_loc(loc), _todo_line(s), "value"))
        path = root / fname.removeprefix(prefix)
        for ln, line in enumerate(read_text(path).splitlines(), 1):
            c = _comment_start(line)
            if c >= 0 and TODO_MARK in line[c:]:
                todos.append(Todo(fname, f"строка {ln} (комментарий)", line[c:].lstrip("# ").strip(), "comment"))
    for rel in sorted({*content.docs, *content.texts}):
        for ln, line in enumerate(read_text(root / rel).splitlines(), 1):
            if TODO_MARK in line:
                todos.append(Todo(prefix + rel, f"строка {ln}", line.strip(), "text"))
    todos.extend(content.missing)
    return todos
