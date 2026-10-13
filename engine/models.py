"""Pydantic-модели всех файлов ``content/`` (структура и типы).

Здесь только форма данных: строгие типы (``strict=True``) и запрет лишних полей
(``extra="forbid"``). Смысловые и перекрёстные проверки (ID существуют, подсказок
ровно три, ``order`` — перестановка карточек и т. п.) — в ``engine/content.py``:
там известны точные пути до полей.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

# ---------------------------------------------------------------- общие типы

ID_PATTERN = r"^[a-z0-9_-]+$"
Id = Annotated[str, StringConstraints(pattern=ID_PATTERN)]
# ID документов развязки (R-01-…) — не участвуют в ответах, регистр допустим.
DocId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]+$")]
PosInt = Annotated[int, Field(gt=0)]
NonNegInt = Annotated[int, Field(ge=0)]

CASES: tuple[str, ...] = ("nom", "gen", "dat", "acc", "ins", "pre")
Case = Literal["nom", "gen", "dat", "acc", "ins", "pre"]
NamePartName = Literal["last", "first", "middle"]

# Типы проверяемых единиц (docs/01 §3). form — только у вопроса.
UNIT_TYPES: tuple[str, ...] = (
    "text", "time", "date", "number", "choice", "multi", "person", "persons", "order", "document",
)
UnitType = Literal["text", "time", "date", "number", "choice", "multi", "person", "persons", "order", "document"]
QuestionType = Literal[
    "text", "time", "date", "number", "choice", "multi", "person", "persons", "order", "document", "form",
]
# Типы, ответ которых — список ID.
LIST_TYPES = frozenset({"multi", "persons", "order"})
# Типы, ответ которых — ID (один или список).
ID_TYPES = frozenset({"choice", "multi", "person", "persons", "order", "document"})
QuestionKind = Literal["mandatory", "bonus", "final"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=False)


# ---------------------------------------------------------------- settings.yaml


class CryptoSettings(Strict):
    iter_answer: PosInt
    iter_stage: PosInt
    entries_pad: PosInt


class PointsSettings(Strict):
    bonus: int
    final: int


class PenaltiesSettings(Strict):
    wrong_attempt: int
    lab_no_basis: int


class HintsSettings(Strict):
    cost: Annotated[list[NonNegInt], Field(min_length=1)]
    auto_after_wrong: PosInt


class Rank(Strict):
    min: int | None
    max: int | None
    name: str


class Settings(Strict):
    game_id: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]+$")]
    title: str
    domain: str
    default_year: int
    crypto: CryptoSettings
    points: PointsSettings
    penalties: PenaltiesSettings
    hints: HintsSettings
    ranks: Annotated[list[Rank], Field(min_length=1)]
    leak_watchlist: list[str] = []


# ---------------------------------------------------------------- characters.yaml


class Character(Strict):
    id: Id
    working: str
    role: str
    importance: Literal["key", "secondary", "service", "background"]
    last: str
    first: str
    middle: str | None = None
    nick: str | None = None
    gender: Literal["m", "f"]
    age: NonNegInt | None = None
    photo: str | None = None
    in_pool: bool = False
    forms: dict[NamePartName, dict[Case, str]] | None = None

    @field_validator("middle", mode="after")
    @classmethod
    def _middle_none_to_empty(cls, v: str | None) -> str:
        return "" if v is None else v


class CharactersFile(Strict):
    characters: Annotated[list[Character], Field(min_length=1)]


# ---------------------------------------------------------------- documents.yaml


class Document(Strict):
    id: Id
    stage: PosInt
    kind: Literal["paper", "online", "lab"]
    title: str
    page: Id | None = None


class DocumentsFile(Strict):
    documents: list[Document]


class DocFrontMatter(Strict):
    """Front matter документов ``content/documents/*.md``."""

    id: DocId
    form: Literal["expert", "operator", "video", "protocol", "letter"]
    title: str
    media: list[str] = []


# ---------------------------------------------------------------- stages.yaml


def _canon_shape(v: Any) -> Any:
    if isinstance(v, str):
        return v
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return v
    raise ValueError("ожидается строка или список строк")


class Answer(Strict):
    canon: str | list[str]
    variants: list[str] = []
    tolerance_min: NonNegInt | None = None

    @field_validator("canon", mode="before")
    @classmethod
    def _check_canon(cls, v: Any) -> Any:
        return _canon_shape(v)


class Option(Strict):
    id: Id
    text: str


class Item(Strict):
    id: Id
    text: str


def _pool_shape(v: Any) -> Any:
    if v is None or v == "default":
        return v
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return v
    raise ValueError("ожидается «default» или список ID персонажей")


class UnitSpec(Strict):
    """Общее у вопроса и поля формы: всё, что нужно для проверки единицы."""

    type: QuestionType
    help: str | None = None
    answer: Answer | None = None
    options: list[Option] | None = None
    pool: Literal["default"] | list[str] | None = None
    items: list[Item] | None = None
    leak_scan: bool | None = None

    @field_validator("pool", mode="before")
    @classmethod
    def _check_pool(cls, v: Any) -> Any:
        return _pool_shape(v)


class FormField(UnitSpec):
    id: Id
    type: UnitType
    label: str


class Question(UnitSpec):
    id: Id
    kind: QuestionKind
    prompt: str
    fields: list[FormField] | None = None
    hints: list[str] = []


class Stage(Strict):
    n: PosInt
    envelope: PosInt
    intro: str
    on_complete: str | None = None
    questions: Annotated[list[Question], Field(min_length=1)]


class StagesFile(Strict):
    stages: Annotated[list[Stage], Field(min_length=1)]


# ---------------------------------------------------------------- expertise.yaml


class ExpParam(Strict):
    id: Id
    type: Literal["text", "time", "date", "number"]
    label: str


class ExpObject(Strict):
    id: Id
    title: str
    from_stage: PosInt = 1
    params: list[ExpParam] | None = None


class ExpType(Strict):
    id: Id
    title: str


class ExpResult(Strict):
    id: Id
    object: Id
    types: Annotated[list[Id], Field(min_length=1)]
    stage: PosInt
    bases: Annotated[list[Id], Field(min_length=1)]
    params_answer: dict[str, Answer] | None = None
    doc: Id | None = None
    body: str | None = None
    text: str | None = None


class ExpertiseFile(Strict):
    objects: Annotated[list[ExpObject], Field(min_length=1)]
    types: Annotated[list[ExpType], Field(min_length=1)]
    results: Annotated[list[ExpResult], Field(min_length=1)]


# ---------------------------------------------------------------- finale.yaml


class Fate(Strict):
    who: Id | None
    text: str


class Finale(Strict):
    confession: str
    letter: str
    fates: list[Fate]


# ---------------------------------------------------------------- pages/<slug>/page.yaml
# Решение 8 (PLAN §9): модель на каждый slug по текущим файлам, лишние поля запрещены.


class PageBase(Strict):
    slug: Id
    doc: Id
    locked: Literal[False, True, "password"]
    qr_label: str
    forbidden: list[str] = []


# --- call


class CallRecord(Strict):
    datetime: str
    number: str
    duration: str
    operator: str


class CallPage(PageBase):
    slug: Literal["call"]
    title: str
    record: CallRecord
    audio: str
    note: str


# --- gromov


class GromovProfile(Strict):
    person: Id
    position: str
    city: str
    avatar: str | None = None
    cover: str | None = None


class PostComment(Strict):
    author: str
    text: str


class GromovPost(Strict):
    datetime: str
    geo: str | None = None
    text: str
    photo: str | None = None
    likes: NonNegInt = 0
    comments: list[PostComment] = []


class GromovPage(PageBase):
    slug: Literal["gromov"]
    brand: str
    profile: GromovProfile
    posts: list[GromovPost]


# --- inna


class InnaProfile(Strict):
    person: Id
    avatar: str | None = None
    bio: str


class InnaPost(Strict):
    datetime: str
    photo: str
    caption: str | None = None
    likes: NonNegInt = 0


class InnaPage(PageBase):
    slug: Literal["inna"]
    brand: str
    profile: InnaProfile
    posts: list[InnaPost]


# --- news


class NewsArticle(Strict):
    datetime: str
    headline: str
    photo: str | None = None
    body: str


class NewsSidebarItem(Strict):
    title: str
    datetime: str


class NewsComment(Strict):
    author: str
    datetime: str
    text: str


class NewsAd(Strict):
    title: str
    text: str


class NewsPage(PageBase):
    slug: Literal["news"]
    brand: str
    article: NewsArticle
    sidebar: list[NewsSidebarItem] = []
    comments: list[NewsComment] = []
    ads: list[NewsAd] = []


# --- pharma


class Drug(Strict):
    name: str
    trade: list[str]
    group: str
    indications: str
    contraindications: str
    side_effects: str


class PharmaPage(PageBase):
    slug: Literal["pharma"]
    brand: str
    disclaimer: str
    drugs: Annotated[list[Drug], Field(min_length=1)]


# --- cloud


class CloudBanner(Strict):
    scheduled: str
    last_confirmation: str


class ChatMessage(Strict):
    from_: Id = Field(alias="from")
    datetime: str
    text: str


class CloudFolder(Strict):
    """Папка облака. Набор полей зависит от ``kind`` — проверяется в content.py."""

    id: Id
    title: str
    kind: Literal["table", "chat", "letter", "locked"]
    columns: list[str] | None = None
    rows: list[list[str]] | None = None
    participants: list[Id] | None = None
    messages: list[ChatMessage] | None = None
    body: str | None = None


# Какие поля обязательны для каждого вида папки (остальные необязательные запрещены).
CLOUD_FOLDER_FIELDS: dict[str, tuple[str, ...]] = {
    "table": ("columns", "rows"),
    "chat": ("participants", "messages"),
    "letter": ("body",),
    "locked": (),
}


class CloudPage(PageBase):
    slug: Literal["cloud"]
    password: str
    brand: str
    account: str
    banner: CloudBanner
    folders: Annotated[list[CloudFolder], Field(min_length=1)]


# --- video


class VideoFile(Strict):
    name: str
    size: str
    created: str
    device: str
    duration: str
    resolution: str


class VideoPage(PageBase):
    slug: Literal["video"]
    title: str
    source: str
    file: VideoFile
    video: str


PAGE_MODELS: dict[str, type[PageBase]] = {
    "call": CallPage,
    "gromov": GromovPage,
    "inna": InnaPage,
    "news": NewsPage,
    "pharma": PharmaPage,
    "cloud": CloudPage,
    "video": VideoPage,
}
