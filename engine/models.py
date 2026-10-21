"""Pydantic-модели всех файлов ``content/`` (структура и типы).

Здесь только форма данных: строгие типы (``strict=True``) и запрет лишних полей
(``extra="forbid"``). Смысловые и перекрёстные проверки (ID существуют, подсказок
ровно три, ``order`` — перестановка карточек и т. п.) — в ``engine/content.py``:
там известны точные пути до полей.
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

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


# FORMATS §5: расширение медиа → MIME. Иное расширение — ошибка валидации.
MEDIA_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".mp4": "video/mp4",
}


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
    # Фразы, которые законно стоят и в открытом тексте, и в закрытом (leak scan не считает их шинглы иголками)
    leak_public_ok: list[str] = []

    @field_validator("domain", mode="after")
    @classmethod
    def _domain_root_only(cls, v: str) -> str:
        """FORMATS F18: сайт живёт только в корне домена — ``https://host[:port]`` без пути."""
        u = urlsplit(v)
        if u.scheme != "https" or not u.hostname:
            raise ValueError(f"domain {v!r}: нужен адрес вида https://host (схема https)")
        if u.path or u.query or u.fragment or "?" in v or "#" in v:
            raise ValueError(f"domain {v!r}: без пути, «/» в конце, параметров и фрагмента — "
                             "сайт размещается только в корне домена")
        if u.username or u.password:
            raise ValueError(f"domain {v!r}: без логина и пароля")
        return v


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
    # Фамилия и отчество выводятся от отца (engine.names.surname_for / patronymic_for);
    # сборка сверяет last/middle с выведенными, import-cast (P09) выводит их сам.
    father: Id | None = None
    # Дружеское/домашнее имя («Ваня»): {{ c.X.familiar }}, не склоняется.
    familiar: str | None = None
    # false — вымышленный персонаж: import-cast (P09) его не трогает.
    cast: bool = True

    @field_validator("middle", mode="after")
    @classmethod
    def _middle_none_to_empty(cls, v: str | None) -> str:
        return "" if v is None else v

    @field_validator("familiar", mode="after")
    @classmethod
    def _familiar_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("пустая строка: заполните familiar или удалите поле")
        return v


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
    # Основы для распознавания текста игрока (engine/labmatch.py): строка — одна или несколько основ
    # через пробел. Сборка нормализует их; название (title) — тоже алиас, отдельно его не указывают.
    aliases: list[str] = []
    ref: str | None = None  # где предмет упомянут: «1-09, поз. 17.3» (показывается в «Моих заявках»)


class ExpType(Strict):
    id: Id
    title: str
    description: str | None = None  # раздел «Услуги» сайта лаборатории


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


# ---------------------------------------------------------------- lab.yaml
# Тексты сайта лаборатории «Призма» (разделы «Услуги», «О центре», «Контакты»).


class LabStaff(Strict):
    name: str
    role: str


class LabContacts(Strict):
    address: str
    phone: str
    hours: str
    email: str | None = None


class LabSite(Strict):
    name: str
    full_name: str
    tagline: str
    about: str  # Markdown
    accreditation: str
    staff: list[LabStaff] = []
    contacts: LabContacts
    services_note: str


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
    """Общие поля ``page.yaml``. ``type`` по умолчанию равен ``slug`` (у каждой модели свой Literal).

    ``doc`` необязателен: страница, на которую попадают только по ссылкам, задаёт ``stage``
    (docs/REDESIGN-2026-10 §4.1). QR и ``qr_label`` — только у страниц с ``doc``.
    """

    slug: Id
    type: str
    doc: Id | None = None
    stage: PosInt | None = None
    locked: Literal[False, True, "password"]
    qr_label: str | None = None
    forbidden: list[str] = []

    @model_validator(mode="after")
    def _doc_or_stage(self) -> "PageBase":
        if self.doc is None and self.stage is None:
            raise ValueError("нужно одно из полей: doc (документ с QR) или stage (этап, если на страницу "
                             "попадают только по ссылкам)")
        if self.doc is None and self.qr_label:
            raise ValueError("qr_label бывает только у страницы с doc: QR печатается только для страниц с документом")
        if self.doc is not None and not (self.qr_label or "").strip():
            raise ValueError("у страницы с doc должно быть поле qr_label (подпись под QR-кодом)")
        return self


# --- call


class CallRecord(Strict):
    datetime: str
    number: str
    duration: str
    operator: str


class CallPage(PageBase):
    slug: Literal["call"]
    type: Literal["call"] = "call"
    title: str
    record: CallRecord
    audio: str
    note: str


# --- social (профиль в «Круге»), social_home, social_stub


class SocialPerson(Strict):
    """Человек в «Друзьях»: ``person`` (персонаж) или ``name`` (нефигурант); ``page`` — страница профиля."""

    person: Id | None = None
    name: str | None = None
    page: Id | None = None

    @model_validator(mode="after")
    def _one_of(self) -> "SocialPerson":
        if (self.person is None) == (self.name is None):
            raise ValueError("нужно ровно одно из полей: person (ID персонажа) или name (имя нефигуранта)")
        return self


class SocialProfile(Strict):
    person: Id | None = None
    name: str | None = None
    position: str | None = None
    city: str | None = None
    avatar: str | None = None
    cover: str | None = None
    about: str | None = None
    friends: list[SocialPerson] = []

    @model_validator(mode="after")
    def _one_of(self) -> "SocialProfile":
        if (self.person is None) == (self.name is None):
            raise ValueError("нужно ровно одно из полей: person (ID персонажа) или name (имя нефигуранта)")
        return self


class PostComment(Strict):
    author: str
    text: str
    page: Id | None = None  # страница автора; нет — ссылка на заглушку (krug-private)


class PostLink(Strict):
    page: Id
    text: str


VOICE_EXTENSIONS = (".mp3", ".m4a")


class PostAudio(Strict):
    """Голосовое сообщение в посте «Круга» (docs/03 §8)."""

    file: str  # путь в media/, как у фото: «<page>/voice-01.mp3»
    duration: str  # «М:СС» — показывается и при отсутствующем файле
    transcript: str | None = None  # «Расшифровка» в раскрывающемся блоке под плеером

    @field_validator("file")
    @classmethod
    def _audio_ext(cls, v: str) -> str:
        if not v.lower().endswith(VOICE_EXTENSIONS):
            raise ValueError(f"голосовое: допустимы файлы {', '.join(VOICE_EXTENSIONS)}")
        return v

    @field_validator("duration")
    @classmethod
    def _duration_fmt(cls, v: str) -> str:
        if not re.fullmatch(r"\d{1,3}:[0-5]\d", v):
            raise ValueError("длительность голосового — «М:СС», например «0:12»")
        return v


class SocialPost(Strict):
    datetime: str
    geo: str | None = None
    text: str = ""  # может быть пустым, если есть audio или photo
    photo: str | None = None
    audio: PostAudio | None = None
    likes: NonNegInt = 0
    link: PostLink | None = None
    comments: list[PostComment] = []

    @model_validator(mode="after")
    def _has_body(self) -> "SocialPost":
        if not (self.text.strip() or self.photo or self.audio):
            raise ValueError("у поста должен быть text, photo или audio")
        return self


class SocialPage(PageBase):
    type: Literal["social"] = "social"
    brand: str
    profile: SocialProfile
    posts: list[SocialPost] = []


class SocialPopular(Strict):
    page: Id
    text: str


class SocialHomePage(PageBase):
    type: Literal["social_home"] = "social_home"
    brand: str
    popular: list[SocialPopular] = []


class SocialStubPage(PageBase):
    type: Literal["social_stub"] = "social_stub"
    brand: str
    text: str


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
    type: Literal["inna"] = "inna"
    brand: str
    profile: InnaProfile
    posts: list[InnaPost]


# --- news


class NewsArticle(Strict):
    datetime: str
    headline: str
    photo: str | None = None
    body: str
    rubric: str = "Город"  # рубрика над заголовком
    urgent: bool = False  # плашка «Срочно»


class NewsSidebarItem(Strict):
    title: str
    datetime: str
    page: Id | None = None  # статья news-*; нет — окно «материал недоступен»


class NewsComment(Strict):
    author: str
    datetime: str
    text: str


class NewsAd(Strict):
    title: str
    text: str


class NewsPage(PageBase):
    type: Literal["news"] = "news"
    brand: str
    article: NewsArticle
    sidebar: list[NewsSidebarItem] = []
    comments: list[NewsComment] = []
    ads: list[NewsAd] = []

    @model_validator(mode="after")
    def _slug_news(self) -> "NewsPage":
        if self.slug != "news" and not self.slug.startswith("news-"):
            raise ValueError("slug страницы типа news: «news» или «news-…»")
        return self


# --- pharma


class Drug(Strict):
    name: str
    trade: list[str]
    group: str
    indications: str
    contraindications: str
    side_effects: str
    appearance: str | None = None  # «Внешний вид» — после «Действующего вещества»


class PharmaPage(PageBase):
    slug: Literal["pharma"]
    type: Literal["pharma"] = "pharma"
    brand: str
    disclaimer: str
    drugs: Annotated[list[Drug], Field(min_length=1)]


# --- cloud


class CloudBanner(Strict):
    scheduled: str
    last_confirmation: str


class ChatMessage(Strict):
    # В YAML ключ — «from» (зарезервированное слово Python); читается только по алиасу.
    model_config = ConfigDict(extra="forbid", strict=True, validate_by_alias=True, validate_by_name=False)

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
    type: Literal["cloud"] = "cloud"
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
    type: Literal["video"] = "video"
    title: str
    source: str
    file: VideoFile
    video: str


# --- site (сайт организации: театр, фонд, клуб)

SiteSkin = Literal["theater", "fund", "auction"]


class SiteCard(Strict):
    title: str
    subtitle: str | None = None
    text: str | None = None
    photo: str | None = None
    page: Id | None = None
    link_text: str | None = None  # подпись ссылки карточки (по умолчанию «Подробнее»)


class SiteText(Strict):
    kind: Literal["text"]
    md: str


class SiteCards(Strict):
    kind: Literal["cards"]
    title: str | None = None
    items: Annotated[list[SiteCard], Field(min_length=1)]


class SiteTable(Strict):
    kind: Literal["table"]
    title: str | None = None
    columns: Annotated[list[str], Field(min_length=1)]
    rows: list[list[str]]


class SiteNotice(Strict):
    kind: Literal["notice"]
    text: str


SiteBlock = Annotated[SiteText | SiteCards | SiteTable | SiteNotice, Field(discriminator="kind")]


class SiteSection(Strict):
    id: Id
    title: str
    blocks: Annotated[list[SiteBlock], Field(min_length=1)]


class SitePage(PageBase):
    type: Literal["site"] = "site"
    brand: str
    skin: SiteSkin
    tagline: str | None = None
    sections: Annotated[list[SiteSection], Field(min_length=1)]
    footer: str | None = None


# --- тексты подвала сервисов (content/pages/_brands.yaml)


class ServiceTexts(Strict):
    """Короткие тексты подвала сервиса: «О сервисе», «Правила», «Помощь» (абзацы — через пустую строку)."""

    about: str
    rules: str
    help: str


class ServicesFile(Strict):
    """``_brands.yaml``: ключ — бренд из ``world.yaml → brands`` (social, photo, news, pharma, cloud)."""

    services: dict[Id, ServiceTexts]


# Ключ — type страницы (по умолчанию = slug). Шаблон — site/templates/pages/<type>.html.
PAGE_MODELS: dict[str, type[PageBase]] = {
    "call": CallPage,
    "inna": InnaPage,
    "news": NewsPage,
    "pharma": PharmaPage,
    "cloud": CloudPage,
    "video": VideoPage,
    "social": SocialPage,
    "social_home": SocialHomePage,
    "social_stub": SocialStubPage,
    "site": SitePage,
}


# ---------------------------------------------------------------- chats/<id>.yaml (P07, печать)
# «Скриншоты» телефона для бумажных документов: экран блокировки с уведомлениями,
# переписка в вымышленном мессенджере, список вызовов. Только для печати (print/chats/).


class NotificationItem(Strict):
    app: str
    title: str
    text: str
    time: str


class NotificationScreen(Strict):
    kind: Literal["notification"]
    time: str  # время в строке состояния и на экране блокировки
    date: str  # «вторник, 10 ноября»
    items: Annotated[list[NotificationItem], Field(min_length=1)]


class ChatLine(Strict):
    """Сообщение. ``from`` — ID персонажа; ``name`` — подпись вместо имени персонажа
    (например, для участника рабочего чата без ID)."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_by_alias=True, validate_by_name=False)

    from_: Id | None = Field(default=None, alias="from")
    name: str | None = None
    time: str
    text: str
    status: Literal["sent", "delivered", "read"] | None = None


class ChatScreen(Strict):
    model_config = ConfigDict(extra="forbid", strict=True, validate_by_alias=True, validate_by_name=False)

    kind: Literal["chat"]
    owner: Id | None = None  # чей телефон: его сообщения справа
    with_: Id | None = Field(default=None, alias="with")  # личная переписка
    title: str | None = None  # название группового чата
    time: str | None = None  # время в строке состояния (по умолчанию — время последнего сообщения)
    date: str | None = None  # разделитель дня над сообщениями
    messages: Annotated[list[ChatLine], Field(min_length=1)]


class CallItem(Strict):
    who: Id | None = None
    name: str | None = None  # подпись, если это не персонаж или номер не сохранён
    number: str
    time: str
    direction: Literal["in", "out", "missed"]


class CallsScreen(Strict):
    kind: Literal["calls"]
    owner: Id | None = None
    time: str
    items: Annotated[list[CallItem], Field(min_length=1)]


ChatScreenAny = Annotated[NotificationScreen | ChatScreen | CallsScreen, Field(discriminator="kind")]


class ChatFile(Strict):
    id: Id
    screens: Annotated[list[ChatScreenAny], Field(min_length=1)]


# ---------------------------------------------------------------- paper/<id>.md (печать, бумажные документы)
# Тексты документов конвертов 1–4: front matter + Markdown. Только для печати (print/paper/),
# в dist/ не попадают. Бланк ``form`` — имя шаблона site/templates/print/paper/<form>.html
# (список расширяемый: проверяется наличие шаблона, а не перечисление здесь).


class PaperSignature(Strict):
    role: str
    name: str


class PaperFrontMatter(Strict):
    id: Id
    form: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]*$")]
    title: str | None = None  # по умолчанию — из documents.yaml
    stage: PosInt | None = None  # необязательно; если указан — сверяется с documents.yaml
    date: str | None = None
    place: str | None = None
    signed: list[PaperSignature] = []
    media: list[str] = []
    qr: bool | None = None  # по умолчанию — true, если у документа в documents.yaml есть page
    pages_hint: PosInt | None = None
    meta: dict[str, Any] = {}
