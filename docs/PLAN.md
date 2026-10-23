# PLAN. План реализации онлайн-части «За кулисами правды»

Шаг P00, 2026-10-13. Источники: `CLAUDE.md`, `docs/01–06`, `content/**`, `prompts/P00–P09`. Сюжетные несостыковки здесь не разбираются: их ведёт `docs/STORY-ISSUES.md`.

Принципы плана:
- Python и JS зеркалят друг друга: `normalize` и `crypto` с одинаковыми именами функций, общие векторы в `tests/vectors/`.
- Сборщик сначала полностью собирает модель (контент → рендер → единицы → ключи), потом пишет `dist/`. `check` проверяет уже записанный `dist/`, а не внутренние структуры сборщика.
- Медиа планируются до шифрования (двухпроходная схема): в момент шифрования пакета уже известно, будет файл открытым или зашифрованным и какой у него ключ.

---

## 1. Модули `engine/` (Python)

**`engine/__main__.py`** — CLI на `argparse`. Первые строки: `sys.stdout.reconfigure(encoding="utf-8")` и то же для `stderr`. Подкоманды из `CLAUDE.md` → «Команды». `main(argv: list[str] | None = None) -> int`. Каждая подкоманда — тонкая обёртка над функцией модуля ниже. Зависит от всех модулей, но импортирует их лениво: `--help` не должен требовать `playwright`.

**`engine/paths.py`** — пути проекта. `project_root(start: Path | None = None) -> Path` ищет вверх по дереву `pyproject.toml` и `content/`. Константы `CONTENT`, `MEDIA`, `SITE`, `DIST`, `PRINT`, `TESTS`, `SALTS_LOCK`. Ни от чего не зависит.

**`engine/util.py`** — ввод-вывод и канонический JSON. `canonical_json(obj) -> bytes`: `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`, UTF-8, без завершающего `\n`. `sha256_hex(data: bytes) -> str`, `read_text(p: Path) -> str`, `write_text(p: Path, s: str) -> None` (всегда `encoding="utf-8"`, `newline="\n"`), `write_json(p, obj, *, pretty=False) -> None`. Зависит только от stdlib.

**`engine/normalize.py`** — нормализация по `docs/02` §2. `base(s: str) -> str`: посимвольно по `unicodedata.category`, не через `\w`. `normalize(type_: str, value: str | list[str]) -> str | None`. `TYPES = {"text", "password", "time", "date", "number", "choice", "person", "document", "multi", "persons", "order"}`. `default_year` передаётся параметром: `normalize(type_, value, *, default_year: int)`. Зависит только от stdlib.

**`engine/crypto.py`** — примитивы `docs/02` §3. Функции:
- `b64u_encode(b: bytes) -> str`, `b64u_decode(s: str) -> bytes`;
- `pbkdf2(password: bytes, salt: bytes, iterations: int) -> bytes` (32 байта);
- `hkdf(ikm: bytes, info: bytes) -> bytes` (соль — 32 нулевых байта, длина 32);
- `seal(key: bytes, plaintext: bytes, aad: str, *, _nonce: bytes | None = None) -> dict` и `open_(key: bytes, container: dict) -> bytes`. `_nonce` используется только генератором векторов;
- `seal_media(key, data, aad) -> bytes` и `open_media(key, blob, aad) -> bytes` (формат `nonce ‖ ct ‖ tag`);
- хелперы, которые строят строки ровно по §3.3–3.7: `answer_key(path, normalized, salt, iters) -> bytes`, `stage_secret(n: int, pairs: list[tuple[str, str]]) -> str`, `start_key(salt, iters) -> bytes`, `pack_info(n) -> bytes`, `lab_info(object_id, type_id, basis, params: list[str]) -> bytes`, `FINALE_INFO`, `cloud_key(password_norm, salt, iters) -> bytes`.

Зависит от `cryptography` (`PBKDF2HMAC`, `HKDF`, `AESGCM`).

**`engine/models.py`** — pydantic-модели всех файлов `content/`, везде `extra="forbid"`:
- `Settings`, `World` (свободное дерево; проверяются только типы листьев), `Character`, `Document`;
- `Stage`, `Question`, `Field` (общий базовый `UnitSpec`: `type`, `label|prompt`, `answer`, `options`, `pool`, `items`, `leak_scan`), `Answer` (`canon`, `variants`, `tolerance_min`);
- `ExpObject`, `ExpParam`, `ExpType`, `ExpResult` (ровно одно из `doc+body` или `text`), `Finale`, `Fate`;
- по модели на каждую страницу (`CallPage`, `GromovPage`, …; дискриминатор — `slug`) и `DocFrontMatter` (`id`, `form`, `title`, `media`).

Зависит от `pydantic`.

**`engine/content.py`** — загрузка и перекрёстная валидация. `load_content(root: Path) -> Content` — dataclass со всеми моделями и путями. `class ContentError(Exception)` с полями `file`, `loc`, `msg`; пример сообщения: `content/stages.yaml: stages[2].questions[0].answer.canon: …`. `validate(content) -> None` (поднимает `ContentErrors` со списком). `find_todos(content, rendered) -> list[Todo]`. Зависит от `models`, `PyYAML`, `python-frontmatter`.

**`engine/names.py`** — склонение и объект персонажа для шаблонов. `decline(part: Literal["last", "first", "middle"], value: str | None, gender: Literal["m", "f"], case: str) -> str`: `None` → `""`, пустая строка → `""`, ручные `forms` имеют приоритет. `class Person`: методы `full(case="nom")`, `short(case="nom")`, `io(case="nom")`, `first(case="nom")`, `last(case="nom")`, `middle(case="nom")`, `g(m: str, f: str) -> str`; поля `id`, `role`, `nick`, `age`, `gender`, `photo`. Пустые части имени пропускаются без двойных пробелов. `names_table(content) -> list[dict]` — для `python -m engine names` (части, выведенные от отца, помечены `↑`). Поля персонажа `father` (ID отца), `familiar` (дружеское имя, `c.X.familiar`, не склоняется), `cast` (по умолчанию `true`; `false` — import-cast не трогает). Чистые функции `surname_for(father_last, gender, source_gender="m") -> str` (м↔ж по окончаниям, незнакомое — без изменений) и `patronymic_for(father_first, gender) -> str` (неоднозначное имя → `DeclensionError`); `content` сверяет с ними `last`/`middle` персонажей с `father` (ручная `forms.<часть>.nom` важнее). Зависит от `pytrovich` (см. §7).

**`engine/templating.py`** — Jinja2 для контента. `make_content_env() -> SandboxedEnvironment` (`StrictUndefined`, без автоэкранирования: контент — это текст). `make_context(content) -> dict` с ключами `c` (неймспейс `Person` по ID) и `w`. `w` — **обёртка с доступом только к атрибутам**, а не `dict`: иначе `w.x.items` вернёт метод словаря. `render(tpl: str, ctx, where: str) -> str` — ошибка содержит `where`. `render_tree(obj, ctx, where) -> obj` — рекурсивно по строкам YAML. `render_markdown(md: str) -> str` (`markdown-it-py`, `html=False`). Отдельно `make_site_env(site_root) -> Environment` (автоэкранирование включено) для `site/templates/`. Зависит от `Jinja2`, `markdown-it-py`, `names`.

**`engine/salts.py`** — `engine/salts.lock.json`. `load_or_init(path, *, units: list[str], stages: list[int], pages: list[str]) -> Salts`: дописывает недостающее и ничего не удаляет; файл пишется только при изменениях, в каноническом виде с `\n`. `rotate(path, ...) -> Salts`. `salts_id(salts) -> str` — SHA-256 от `canonical_json`. Методы `Salts`: `unit(path)`, `stage(n)`, `start`, `cloud`, `page_key(slug)`. Зависит от `util`, `crypto`.

**`engine/answers.py`** — проверяемые единицы и ключи этапов. `iter_units(content) -> list[Unit]`; `Unit` — dataclass с полями `path`, `stage`, `kind`, `type`, `spec`, `leak_scan`. `expand(unit, ctx, settings) -> Expanded(canon: str, variants: list[str], raw: list[str])` — рендер, нормализация, раскрытие `tolerance_min` по модулю 24 ч. `check_entries(unit, expanded, salt, iters, pad) -> list[dict]` — записи плюс паддинг, перемешаны через `secrets`. `mandatory_pairs(content, canons, n) -> list[tuple[path, canon]]` — порядок из `content`, поля формы по порядку. `stage_keys(content, salts, canons, settings) -> dict[int, bytes]` (1…4). `order_shuffle(unit, salt) -> list[str]` — детерминированная перестановка карточек `order`; гарантированно не совпадает с ответом. Зависит от `normalize`, `crypto`, `templating`.

**`engine/media.py`** — медиа по `docs/02` §4а. Сначала `plan_media(content) -> MediaPlan`: собирает все ссылки на медиа с пометкой «открытый / зашифрованный контекст» и решает судьбу каждого файла. Правило: есть хоть одна открытая ссылка → файл открытый; портреты — см. вопрос 5. Затем `MediaPlan.ref(rel) -> MediaRef` (формат — `docs/FORMATS.md` §5) и `MediaPlan.emit(dist: Path) -> list[EmittedFile]`. Отсутствующий файл → `src: null, missing: true` (файлов-плейсхолдеров в `dist/` нет; заглушку рисует шаблон или клиент) и предупреждение; в `--release` → ошибка. Зависит от `crypto`, `util`.

**`engine/documents.py`** — документы из `content/documents/*.md`. `render_document(path: Path, ctx, media: MediaPlan, site_env) -> RenderedDoc(id, form, title, html, media: list[MediaRef], plain_text)`. Front matter и тело — шаблоны Jinja2; затем Markdown → HTML; затем обёртка бланка `site/templates/blanks/<form>.html`. Отсутствующий `body` → заглушка (см. несостыковку A1). Зависит от `python-frontmatter`, `templating`, `media`.

**`engine/lab.py`** — экспертизы по §3.6. `expand_params(result, obj, settings) -> list[list[str]]` — декартово произведение нормализованных параметров и предупреждение при > 200. `lab_entries(content, stage_keys, rendered_docs, pad) -> dict[int, list[dict]]` — для каждого этапа: контейнеры `aad="lab"`, паддинг, перемешивание. `lab_catalog(content, n) -> dict` — объекты и виды, которые попадают в пакет `n` (по `from_stage`). Зависит от `crypto`, `normalize`, `answers`.

**`engine/pages.py`** — вымышленные страницы. `build_pages(content, ctx, salts, media, site_env, dist) -> list[PageResult]`. Открытая страница → `dist/p/<slug>/index.html`. `locked: true` → оболочка `page_shell.html` + `payload.json`. Внутри payload — отрендеренный HTML-фрагмент страницы и карта медиа, зашифрованные `K_p` с `aad="page/<slug>"`. `locked: password` → `{"salt", "iter", "box"}`. Также `forbidden_hits(page_text, forbidden) -> list[str]` (подстрока в `base()`). Зависит от `templating`, `crypto`, `media`, `normalize`.

**`engine/packs.py`** — `build_public(content, salts, build_id) -> dict`, `build_pack(n, ...) -> dict` (содержимое по §3.5 плюс `on_complete` этапа `n`), `build_finale(content, ctx, keys, rendered) -> dict` (признание, письмо, судьбы, `answers` для разбора). Зависит от `answers`, `lab`, `documents`, `crypto`.

**`engine/build.py`** — оркестратор. `build(root: Path, *, release: bool = False) -> BuildReport`. Порядок:
1. загрузка и валидация;
2. контекст шаблонов;
3. соли;
4. единицы и каноны;
5. ключи этапов;
6. план медиа;
7. документы;
8. пакеты, лаборатория, развязка;
9. страницы;
10. HTML системы расследования из `site/templates/`;
11. копирование `site/assets/`, `robots.txt`;
12. вывод медиа;
13. список заглушек.

`dist/` пересоздаётся целиком во временной папке и атомарно подменяется. Зависит от всех модулей выше.

**`engine/leakscan.py`** — `tokens(s: str) -> list[str]` (через `base()`), `needles(content, rendered, settings) -> list[Needle(text, kind, source)]`, `scan(dist: Path, needles) -> list[Finding(file, needle, source, form)]`. Сканирует html, js, css, json, svg, txt, xml. Перед поиском раскрывает `\uXXXX`. Пропускает поля `n` и `c` контейнеров и файлы `*.bin`. Ищет сырой вид (целые слова) и последовательности токенов после `base()`. Зависит от `normalize`.

**`engine/check.py`** — `check(root: Path, *, release: bool = False) -> CheckReport`, пункты 1–9 из `docs/06` §3. Читает **записанный** `dist/`: правильные ответы берёт из контента, а ключи и расшифровку проверяет по файлам `dist/data/*.json`. Итоговая таблица — в stdout. Зависит от `build` (только загрузка и рендер контента), `crypto`, `leakscan`.

**`engine/serve.py`** — `serve(dist: Path, port: int = 8000, host: str = "127.0.0.1") -> None`. Это `http.server` с картой MIME (`.json`, `.mp4`, `.mp3`, `.webp`, `.woff2`, `.bin`, `.svg`) и `Cache-Control: no-store`. Зависит только от stdlib.

**`engine/vectors.py`** — `make_crypto_vectors(out: Path) -> None`: детерминированные nonce через `_nonce`, результат — `tests/vectors/crypto.json`. Зависит от `crypto`.

**`engine/dump.py`** — `dump_answers(root, out=tests/.answers.json) -> None`. Пишет для каждой единицы отрендеренный канон и все варианты, для экспертиз — объект, вид, основания и параметры, а также пароль облака, `points`, `penalties`, `hints` и ожидаемый максимум. Зависит от `content`, `answers`.

**`engine/printing.py`** (P07) — `html_to_pdf(html: str, out: Path, *, base_url: Path) -> None` и `html_to_png(html, out, width, height) -> None` через `playwright.sync_api`. Шрифты подключаются из `site/assets/fonts/` через `file://`.

**`engine/qr.py`** (P07) — `make_qr_set(content, salts, out=print/qr) -> list[Path]`: `segno`, коррекция H, PNG 1200 px и SVG; `qr_sheet(...) -> Path` (`sheet.pdf`); `verify_qr(png, url) -> bool | None` (опционально `zxing-cpp`).

**`engine/chatshot.py`** (P07) — `load_chats(content) -> list[Chat]` (схема `content/chats/*.yaml`), `render_chats(out=print/chats) -> list[Path]`.

**`engine/emergency.py`** (P07) — `answers_pdf(out=print/answers.pdf) -> Path`. Это «Аварийный конверт». Модуль назван не `answers.py`, чтобы не путать с проверочными записями.

**`engine/importcast.py`** (P09) — `read_cast(xlsx: Path) -> CastTable` (`openpyxl`, колонки ищутся по названию), `plan_import(content, cast) -> CastDiff`, `apply_import(diff) -> None` (только после «ок»). Персонажи с `cast: false` пропускаются; у персонажей с `father` из таблицы берётся только имя, фамилия и отчество — `names.surname_for`/`patronymic_for` от отца; `familiar` при смене имени — вопрос автору.

**`engine/release.py`** (P08) — `release(root) -> Path`: `build --release` → `check --release` → `print/dist-<buildId>.zip`.

## 2. Модули `site/` (JS, CSS, шаблоны)

**`site/assets/js/boot.js`** — **классический** (не модульный) скрипт, подключается первым на каждой странице. Если `location.protocol === "file:"`, или `!isSecureContext`, или нет `crypto.subtle`, или нет поддержки ES-модулей, показывает понятное сообщение про HTTPS и localhost. Нужен потому, что на `file://` модули и `fetch()` блокируются до запуска модульного кода (см. риск R6). Ни от чего не зависит.

**`core/normalize.js`** — `export function base(s)`, `export function normalize(type, value, { defaultYear })`. Посимвольно по `\p{L}`, `\p{N}`, `\p{M}` (флаг `u`). Ни от чего не зависит.

**`core/crypto.js`** — `b64uEncode(u8)`, `b64uDecode(s)` (собственная реализация: `Uint8Array.fromBase64` в Node 22 нет), `utf8(s)`, `pbkdf2(pw, salt, iters) → Promise<Uint8Array>`, `hkdf(ikm, info)`, `seal(key, pt, aad)` (для тестов и `make_vectors.mjs`), `open(key, container)`, `openMedia(key, bytes, aad)`, `answerKey`, `stageSecret`, `labInfo`, `packInfo`, `FINALE_INFO`, `cloudKey`, `isCryptoAvailable()`. PBKDF2 и HKDF — через `deriveBits`, ключи AES неэкспортируемые. Зависит от Web Crypto.

**`core/state.js`** — чистая логика прогресса без DOM, тестируется в Node. `createStore({ storage, gameId, now })` → `{ get, update(fn), exportJson, importJson, reset, onExternalChange }`. В `update` — перечитать, применить, слить (несколько вкладок). Редьюсеры: `score(s)`, `recordWrong(s, path, hash, penalty)`, `buyHint(s, path, level, cost)`, `maybeAutoHint(s, path, threshold)`, `solve(s, path, canon)`, `advanceStage(s, n, keyB64)`, `labDone(s, fp, docId | null)`, `labRejected(s, fp, penalty)`, `finalSubmit(s, path, value)`, `finalFinish(s, results, points)`, `isCompatible(s, pub)`. Ни от чего не зависит; `storage` внедряется извне.

**`core/game.js`** — проверка ответов и этапы. `loadPublic()`, `openPack(n, key)`, `startKey(pub)`, `checkUnit(unit, rawInput) → { valid, correct, canon }` (один PBKDF2 и перебор записей), `checkQuestion(q, inputs)` (поля формы — `Promise.all`), `nextStageKey(n, pairs, salt, iters)`, `wrongHash(q, normalizedInputs)`. Зависит от `normalize`, `crypto`.

**`core/lab.js`** — `labFingerprint(req) → string`, `labRequest(req, { stage, keys, packs }) → { stage, entry } | null`: перебор всех открытых этапов, берётся самый поздний. Зависит от `crypto`, `normalize`.

**`core/media.js`** — `mediaUrl(ref) → Promise<string>`: открытый URL или `fetch(.bin)` → `openMedia` → Blob URL с MIME из ссылки; прогресс загрузки для видео. `hydrateMedia(root, media[])` проставляет `src` всем `[data-media]` во вставленном HTML-фрагменте (`docs/FORMATS.md` §0, §5). Зависит от `crypto`.

**`app/`** — DOM системы расследования:
- точки входа: `main.js` (`/`), `lab.js` (`/lab/`), `final.js` (`/final/`);
- компоненты: `dom.js` (хелперы), `texts.js` (все строки интерфейса — в одном месте), `questions.js` (`renderQuestion(q, ctx)` по типам), `order.js` (перетаскивание мышью и касанием, кнопки ↑/↓), `hints.js`, `docs-panel.js`, `modal.js`, `scorelog.js`, `menu.js` (сохранить, загрузить, начать заново), `stamp.js`.

Все зависят от `core/*`.

**`pages/`** — вымышленные страницы:
- `shell.js`: `openLockedPage(slug)` — `#k=` → `sessionStorage` → `replaceState` → расшифровка → вставка фрагмента → медиа; `openPasswordPage(slug)` — для облака;
- интерактив: `audio-player.js` (call), `gallery.js` (inna), `pharma.js` (поиск через `base()`), `cloud.js` (сортировка, папки), `video.js` (плеер, «Свойства файла»).

Зависят от `core/crypto.js`, `core/normalize.js`, `core/media.js`.

**`site/templates/`** — шаблоны Jinja2 (рендерит `engine`):
- `base.html` (noindex, шрифты, `boot.js`), `index.html`, `lab.html`, `final.html`;
- `page_open.html`, `page_shell.html`;
- `pages/<slug>.html` ×7 — одни и те же фрагменты для открытой страницы и для payload;
- `blanks/{expert,operator,video,protocol,letter}.html`;
- `print/{qr_sheet,answers,chat}.html`.

**`site/assets/css/`** — `base.css` (токены, `@font-face`, сброс, тёмная тема, reduced motion), `app.css`, `blank.css`, `print.css`, `pages/{call,gromov,news,inna,pharma,cloud}.css` (`video` использует `app.css`).

## 3. Полный список файлов

```
.claude/agents/*.md                     (есть)
.gitignore                              (есть; P01 сверяет)
CLAUDE.md, README.md                    (есть)
pyproject.toml                          P01
package.json, package-lock.json         P01
playwright.config.ts                    P04 (webServer: python -m engine serve)
docs/
  01..06-*.md                           (есть)
  PLAN.md                               P00
  STORY-ISSUES.md                       P00 (story-auditor)
  DEV.md                                P01
  FORMATS.md                            P03 (контракт данных engine ↔ site)
  DEPLOY.md, CHECKLIST.md               P08
content/                                (есть; меняет только автор)
  settings.yaml world.yaml characters.yaml documents.yaml stages.yaml expertise.yaml finale.yaml
  documents/{2-01,3-05,3-06,4-08,4-10,R-01-confession,R-01-letter}.md
  pages/{call,cloud,gromov,inna,news,pharma,video}/page.yaml
  pages/news/article.md, pages/cloud/if_you_read_this.md      (нет — ждут контента)
  chats/{3-03,4-06,4-12}.yaml           P07 (схема и примеры с TODO)
media/                                  (нет; автор: portraits/, gromov/, news/, inna/, lab/, audio/, video/)
engine/
  __init__.py __main__.py paths.py util.py                       P01
  serve.py                                                       P01
  normalize.py crypto.py vectors.py                              P02
  models.py content.py names.py templating.py salts.py answers.py
  media.py documents.py lab.py pages.py packs.py build.py
  leakscan.py check.py dump.py                                   P03
  salts.lock.json                       P03 (создаётся первой сборкой, коммитится)
  printing.py qr.py chatshot.py emergency.py                     P07
  release.py                                                     P08
  importcast.py                                                  P09
site/
  templates/base.html index.html lab.html final.html page_open.html page_shell.html   P03 (минимальные) → P04–P06
  templates/pages/{call,gromov,news,inna,pharma,cloud,video}.html                    P03 (минимальные) → P06
  templates/blanks/{expert,operator,video,protocol,letter}.html                       P03 (простой) → P05
  templates/print/{qr_sheet,answers,chat}.html                                         P07
  assets/fonts/PTSans-{Regular,Italic,Bold,BoldItalic}.woff2
  assets/fonts/PTSerif-{Regular,Italic,Bold,BoldItalic}.woff2, OFL.txt                P01
  assets/css/base.css app.css blank.css print.css                                      P04–P05
  assets/css/pages/{call,gromov,news,inna,pharma,cloud}.css                            P06
  assets/js/boot.js                                                                    P03
  assets/js/core/normalize.js crypto.js                                                P01 (пусто) → P02
  assets/js/core/state.js game.js                                                      P04
  assets/js/core/lab.js media.js                                                       P05 / P03–P06
  assets/js/app/main.js lab.js final.js dom.js texts.js questions.js order.js hints.js
                docs-panel.js modal.js scorelog.js menu.js stamp.js                    P04–P05
  assets/js/pages/shell.js audio-player.js gallery.js pharma.js cloud.js video.js      P06
tests/
  conftest.py test_smoke.py                                                            P01
  test_normalize.py test_crypto.py test_crypto_js_compat.py                            P02
  test_content_validation.py test_names.py test_salts.py test_build.py
  test_leakscan.py test_check.py                                                       P03
  test_print.py                                                                        P07
  test_importcast.py                                                                   P09
  vectors/normalize.json (руками) vectors/crypto.json (engine vectors)                 P02
  js/smoke.test.mjs                                                                    P01
  js/normalize.test.mjs crypto.test.mjs make_vectors.mjs bench_pbkdf2.mjs              P02
  js/state.test.mjs storage.test.mjs                                                   P04
  js/lab.test.mjs                                                                      P05
  e2e/helpers.ts stage1.spec.ts                                                        P04
  e2e/full.spec.ts lab.spec.ts final.spec.ts                                           P05
  e2e/pages.spec.ts                                                                    P06
  e2e/hints.spec.ts reload.spec.ts layout.spec.ts network.spec.ts perf.spec.ts        P08
  .answers.json                         (генерируется, в .gitignore)
dist/ print/ node_modules/ .venv/ test-results/ playwright-report/   (в .gitignore)
```

## 4. Порядок реализации и проверка после каждого шага

Зависимости: P01 → P02 → P03 → (P04 → P05) ∥ P06 → P07 → P08 → P09. P06 можно начинать сразу после P03.

| Шаг | Что появляется | Проверка (команды) |
|---|---|---|
| P01 | Каркас, `pyproject.toml`, `package.json`, CLI-заглушки, `serve`, шрифты, `docs/DEV.md` | `pip install -e .[dev]`; `python -m engine --help` (все 12 подкоманд); `python -m engine build` → «Будет реализовано в P03», код 2; `python -m pytest`; `npm run test:js`; `python -m engine serve` + `curl -sI http://127.0.0.1:8000/` → 200 и `Cache-Control: no-store`; `python -c "print('Проверка кириллицы')"` в cmd и PowerShell |
| P02 | `normalize` и `crypto` на Python и JS, векторы, кросс-тесты, замер | `python -m pytest tests/test_normalize.py tests/test_crypto.py tests/test_crypto_js_compat.py`; `npm run test:js`; `python -m engine vectors && git diff --exit-code tests/vectors/crypto.json` (повторная генерация не меняет файл); `python -c "import json;print(len(json.load(open('tests/vectors/normalize.json',encoding='utf-8'))))"` ≥ 60; `node tests/js/bench_pbkdf2.mjs` |
| P03 | Валидация, шаблоны и склонение, соли, пакеты, лаборатория, развязка, страницы, `check`, `dump-answers` | `python -m engine build && python -m engine check` (зелёный, таблица, список TODO); `python -m engine names`; второй `build` → `git diff --exit-code engine/salts.lock.json`; `python -m engine dump-answers`; `python -m pytest` (≥ 8 испорченных копий контента, тест «подложенная утечка → check падает»); `python -m engine build --release` → ожидаемо падает со списком `TODO(content)` |
| P04 | `/`: этапы, вопросы всех типов, подсказки, журнал, конверты, меню | `npm run test:js` (`state.test.mjs`); `python -m engine build && npx playwright test tests/e2e/stage1.spec.ts`; руками: `python -m engine serve`, этапы 1 → 3, перезагрузка; скриншоты 360, 768, 1280 и тёмная тема |
| P05 | `/lab/`, бланки, `/final/`, итоги, развязка | `npm run test:js` (`lab.test.mjs`); `npx playwright test tests/e2e/full.spec.ts tests/e2e/lab.spec.ts tests/e2e/final.spec.ts`; печать бланка в PDF — одна страница A4 |
| P06 | 7 вымышленных страниц, оболочка закрытых страниц | `npx playwright test tests/e2e/pages.spec.ts` (с ключом, без ключа, с испорченным ключом, облако по паролю, [Улика] видимы на 360 px); `python -m engine check` (`forbidden` у `news`) |
| P07 | QR, «скриншоты» переписок, аварийный конверт | `python -m engine qr` → `print/qr/*.png`, `*.svg`, `sheet.pdf` (самопроверка декодированием); `python -m engine chatshot` → `print/chats/*.png` 1080×2340; `python -m engine answers` → `print/answers.pdf`; `python -m pytest tests/test_print.py` |
| P08 | Полный e2e, производительность, аудит, `release`, DEPLOY, CHECKLIST | `npx playwright test` (все); отчёт `perf.spec.ts` (CPU ×4); `network.spec.ts` (ноль внешних запросов); `python -m engine release` → падает, пока есть TODO и `example.ru` (ожидаемо) |
| P09 | `import-cast`, настоящие имена, финальные тексты | `python -m engine import-cast <xlsx>` (diff, затем «ок»); `python -m engine names`; `python -m engine build && python -m engine check`; ключи страниц до и после совпадают: `python -c "import json;print(json.load(open('engine/salts.lock.json',encoding='utf-8'))['pages'])"`; `npx playwright test tests/e2e/full.spec.ts`; `python -m engine release` |

## 5. Версии библиотек

Проверено 2026-10-13 через `pypi.org/pypi/<pkg>/json` и `npm view`. Окружение: Python 3.13 (в sandbox 3.13.16), Node 22.22.0.

| Пакет | Последняя | Диапазон в `pyproject.toml` / `package.json` | Обоснование |
|---|---|---|---|
| PyYAML | 6.0.3 (2025-09) | `>=6.0.3,<7` | `safe_load`; колёса для 3.13 есть |
| Jinja2 | 3.1.6 (2025-03) | `>=3.1.6,<4` | 3.1.6 закрывает уязвимости песочницы (`SandboxedEnvironment` критичен) |
| pydantic | 2.14.1 (2026-10-11, два дня) | `>=2.13,<3` | Нужен только API v2; нижняя граница 2.13 позволяет откатиться с совсем свежей 2.14.x без правки диапазона; Python ≥ 3.10 |
| cryptography | 50.0.2 (2026-09-30) | `>=50.0.2,<51` | PBKDF2HMAC, HKDF, AESGCM стабильны много лет; мажоры у пакета частые, поэтому верхняя граница обязательна |
| segno | 1.6.6 (2025-03) | `>=1.6.6,<2` | QR без зависимостей, PNG и SVG |
| pytrovich | 0.2.0 (2026-06-13) | `>=0.2.0,<0.3` | 0.x: минорная версия ломает API (в 0.2 появился `known_gender`); проверен фактически (§7); без зависимостей |
| playwright (py) | 1.63.0 (2026-09-15) | `>=1.63.0,<1.64` | Та же минорная, что у `@playwright/test`: общая сборка Chromium r1243 (153.0.8010.12) |
| markdown-it-py | 4.2.0 (2026-05) | `>=4.2.0,<5` | CommonMark; Python ≥ 3.10 |
| python-frontmatter | 1.3.0 (2026-05) | `>=1.3.0,<2` | Front matter документов |
| openpyxl | 3.1.5 (2024-06) | `>=3.1.5,<4` | Чтение xlsx для `import-cast` |
| pypdf | 6.21.0 (2026-10-16, проверено в тот же день) | `>=6.20,<7` | `paper`: сборник `envelope-<N>.pdf` — склейка готовых `<id>.pdf`, чтобы у каждого документа была своя нумерация «Лист 1…» (в одном HTML Chromium ведёт сквозной `counter(page)` и не сбрасывает его между документами); число страниц PDF — по дереву страниц, а не поиском `/Type /Page` в байтах. Чистый Python, без зависимостей, BSD-3-Clause; нижняя граница 6.20 — откат со свежей 6.21.x без правки диапазона, мажоры ломают API |
| pytest (dev) | 9.1.1 (2026-06) | `>=9.1.1,<10` | — |
| zxing-cpp (extra `qrcheck`, необязательно) | 3.1.1 (2026-07) | `>=3.1.1,<4` | Самопроверка QR в P07 без системных библиотек (в отличие от `pyzbar`, последняя версия 2022 года) |
| pillow (extra `qrcheck`) | 12.3.0 (2026-07) | `>=12.3,<13` | Нужен `zxing-cpp` для чтения PNG |
| @playwright/test (npm, dev) | 1.64.0 | `~1.63.0` | Держим 1.63.x ради общей сборки Chromium с Python-пакетом. **Поправка к вводным:** по `npm view @playwright/test time` версия 1.64.0 опубликована 2026-10-07, а не сегодня; сегодня вышла только `1.65.0-alpha-2026-10-13` |

Дополнительно:
- `requires-python = ">=3.11"` (по `CLAUDE.md`); фактически минимум у зависимостей — 3.10. Проверяем на 3.13.
- `"engines": {"node": ">=22"}`. В Node 22 есть `globalThis.crypto.subtle` и шаблоны в `node --test "…/*.test.mjs"`.
- В sandbox `/opt/pw-browsers` есть только `chromium-1194` (Playwright 1.56). Для 1.63 нужна ревизия 1243: в P01 выполнить `python -m playwright install chromium`. Если загрузка закрыта — обход уже сделан в P01: переменная `PW_CHROMIUM_PATH` (см. `docs/DEV.md`), её учитывают `playwright.config.js` и команды печати.
- Шрифты PT Sans и PT Serif (OFL 1.1): источник `woff2` — npm-пакеты `@fontsource/pt-sans@5.3.0` и `@fontsource/pt-serif@5.3.0` (лицензия OFL-1.1, файлы `cyrillic` и `latin`), разово через `npm pack`. Пакеты в зависимости не добавлять; файлы и `OFL.txt` положить в `site/assets/fonts/`.

## 6. Риски

**R1. Web Crypto ↔ `cryptography`.**
- *PBKDF2:* в обоих — HMAC-SHA256 и 32 байта. В JS — `importKey("raw", pw, "PBKDF2")` + `deriveBits(256)`. Пустой пароль невозможен: всегда есть префикс `detgame/…`.
- *HKDF:* соль из 32 нулевых байт передаётся явно с обеих сторон. По RFC 5869 это то же, что пустая соль, но явность снимает разночтения. В JS `salt` обязателен. Длина — 256 бит.
- *AES-GCM:* `AESGCM.encrypt` в Python и `encrypt` в Web Crypto возвращают одинаковый формат `ciphertext ‖ tag(16)`, так что поле `c` совпадает без перекладки. Тег по умолчанию 128 бит, AAD обязателен — строка UTF-8.
- *base64url:* в Node 22 нет `Uint8Array.fromBase64` (проверено), а на старых телефонах его тоже нет. Пишем свою реализацию через `atob`/`btoa` и проверяем по векторам.
- *Unicode:* Python 3.13 использует Unicode 15.1, Node 22 — Unicode 16.0 (проверено); у браузеров версия своя. Символы, добавленные в 16.0, могут классифицироваться по-разному. Поэтому `base()` проверяется на стабильных символах, а в векторах нет недавно добавленных code points. `lower()` и `toLowerCase()` совпадают на кириллице, `İ` и final sigma — это есть в векторах.
- *Риск «тихой» ошибки:* строка `labInfo` без параметров (вопрос 1). Защита — векторы для всех хелперов строк, а не только для примитивов.

**R2. Склонение ФИО.** `pytrovich` 0.2.0 на всём текущем составе склоняет без ошибок (§7). Риски:
- `None` вместо строки → `AttributeError`; обёртка приводит к `""`;
- несклоняемые и редкие фамилии в настоящем составе (P09) → ручные `forms`;
- `TODO(content)` возвращается как есть;
- пол берётся только из `gender` контента (`known_gender=True`), а не из детектора.

**R3. Размер видео.** Видео `video` лежит на закрытой странице, поэтому шифруется целиком. Потоковой загрузки и Range-запросов нет: телефон скачивает весь `.bin`, держит в памяти шифротекст и Blob (≈ 2× размера) и только потом играет. Рекомендации:
- 720p H.264 + AAC, 5–6 с (решение автора 23.10; раньше 40–60 с), ≤ 15 МБ (жёсткий потолок 25 МБ из контента);
- индикатор загрузки по `ReadableStream`; `playsinline`;
- лимит хостинга на один файл (у некоторых бесплатных ≈ 25 МиБ) сверить в P08;
- аудио `call` на открытой странице не шифруется и играет потоком.

**R4. PBKDF2 на телефоне.** Замер на сервере sandbox: Node Web Crypto — 150k за 24 мс, 300k за 47 мс; Python hashlib — 46 и 80 мс. Телефон среднего уровня медленнее в 5–15 раз, оценка — 0,15–0,7 с на 150k. Узкие места:
- форма `s1.q1` из 4 полей = 4 × PBKDF2 → проверять поля параллельно (`Promise.all`; в Chrome `deriveBits` выполняется вне главного потока);
- переход этапа добавляет ещё 300k;
- старт: K1 — тоже 300k.

Сборка: ≈ 52 варианта × 150k плюс `check` (все варианты + 5 неверных на каждую из 23 единиц) ≈ 170 PBKDF2, около 10 с здесь и до минуты на слабом ноутбуке — приемлемо. Нужен кеш `K(path, value)` внутри `check`. Итерации снижаются только через `settings.yaml` по замеру P08.

**R5. Хостинг из России.** Доступность зарубежных статических хостингов из российских сетей нестабильна (блокировки и замедления по провайдерам). В P08 предложить:
- основной вариант: российское объектное хранилище со статическим сайтом и сертификатом на свой домен (Yandex Object Storage + Certificate Manager; аналоги — Selectel, Timeweb Cloud, VK Cloud);
- запасной: GitHub Pages, Netlify или Cloudflare Pages с обязательной проверкой с мобильного интернета нескольких операторов.

Ещё два момента. Внешних запросов во время игры нет, поэтому CDN не нужен. После печати QR домен менять нельзя: QR привязаны к `settings.domain`.

**R6. Защищённый контекст.**
- `http://192.168.x.x` — не защищённый контекст, `crypto.subtle === undefined`.
- `file://` в Chrome формально считается защищённым, но ES-модули и `fetch()` к `data/*.json` блокируются (origin `null`). Итог тот же — не работает, но причина другая.

Поэтому проверка — в классическом `boot.js` до загрузки модулей: `protocol === "file:"`, `isSecureContext`, `crypto?.subtle`. Сообщение: «Откройте сайт по адресу https://… или http://localhost:8000 (`python -m engine serve`)». Для проверки с телефона в P08 — выкладка или HTTPS-туннель.

**R7. Модель угроз: ответы финала из консоли** (подробно — несостыковка F1). Принять и описать честно.

**R8. Стабильность ключей и прогресса.** `secret_N` зависит от порядка обязательных единиц и полей формы в `content/`. Перестановка, переименование `id` или новая единица (меняет `saltsId`) делают сохранённый прогресс несовместимым. QR не страдают: ключи страниц постоянные. Правило: после начала игры не пересобирать (уже есть в README).

**R9. Медиа в Git.** `media/` не игнорируется. Видео до 25 МБ в приватном репозитории допустимо, но каждая перезаливка раздувает историю. Предложение: класть финальное видео один раз или использовать Git LFS — решение автора, не блокирует.

## 7. Склонение: проверка pytrovich

Запуск: `.venv/bin/python -I`, `pytrovich 0.2.0`.

API:
- `from pytrovich.enums import Case, Gender, NamePart`, `from pytrovich.maker import PetrovichDeclinationMaker`, `from pytrovich.detector import PetrovichGenderDetector`.
- `PetrovichDeclinationMaker().make(name_part: NamePart, gender: Gender, case_to_use: Case, original_name: str, known_gender: bool = True) -> str`.
- `Case`: `GENITIVE`, `DATIVE`, `ACCUSATIVE`, `INSTRUMENTAL`, `PREPOSITIONAL`, `NOMINATIVE` — на входе всегда именительный.
- `Gender`: `MALE`, `FEMALE`, `ANDROGYNOUS`.
- `PetrovichGenderDetector().detect(firstname=, lastname=, middlename=) -> Gender`.
- Сетевых обращений нет, правила — в пакете (`petrovich-rules/rules.json`). 10 000 вызовов — 0,03 с.

| ФИО (пол) | gen | dat | acc | ins | pre |
|---|---|---|---|---|---|
| Завьялов Юрий Викторович (m) | Завьялова Юрия Викторовича | Завьялову Юрию Викторовичу | Завьялова Юрия Викторовича | Завьяловым Юрием Викторовичем | Завьялове Юрии Викторовиче |
| Тарасова Марина Олеговна (f) | Тарасовой Марины Олеговны | Тарасовой Марине Олеговне | Тарасову Марину Олеговну | Тарасовой Мариной Олеговной | Тарасовой Марине Олеговне |
| Лёвин Станислав Игоревич (m) | Лёвина Станислава Игоревича | Лёвину Станиславу Игоревичу | Лёвина Станислава Игоревича | Лёвиным Станиславом Игоревичем | Лёвине Станиславе Игоревиче |
| Гнедич Елена Михайловна (f) | Гнедич Елены Михайловны | Гнедич Елене Михайловне | Гнедич Елену Михайловну | Гнедич Еленой Михайловной | Гнедич Елене Михайловне |
| Ковалёв Денис Олегович (m) | Ковалёва Дениса Олеговича | Ковалёву Денису Олеговичу | Ковалёва Дениса Олеговича | Ковалёвым Денисом Олеговичем | Ковалёве Денисе Олеговиче |
| Кузнецов Виктор Ильич (m) | Кузнецова Виктора Ильича | Кузнецову Виктору Ильичу | Кузнецова Виктора Ильича | Кузнецовым Виктором Ильичом | Кузнецове Викторе Ильиче |

Все 30 форм верны: «ё» сохраняется, «Ильичом» — правильная ударная форма, женская «Гнедич» не склоняется. Остальные 13 названных персонажей (Воронцов, Волков, Сомов, Резникова, Рябова, Вольская, Лисицына, Беляев, Зуев, Горохов, Громов, Родионов Г. П.) тоже склоняются без ошибок.

Граничные случаи:

| Вход | Результат | Вывод для `engine/names.py` |
|---|---|---|
| `"TODO(content)"` (фамилия и имя, m/f) | Возвращается без изменений во всех падежах, исключений нет | Сборка не падает. `short()` даёт «TODO(content) T.»; заглушку ловит поиск `TODO(content)` (в `--release` — ошибка) |
| `middle = ""` | `""` без ошибки | `full()`/`io()` склеивают только непустые части, иначе остаётся хвостовой пробел («…TODO(content) ») |
| `middle = None` | **`AttributeError: 'NoneType' object has no attribute 'split'`** | Обёртка приводит `None` к `""` — обязательно (YAML `middle: null` или отсутствие ключа) |
| `"ИЛЬИЧ"` (капслок) | `ИЛЬИЧа` | Регистр окончания не подстраивается; в контенте капслока нет, в `names` можно предупреждать |
| `name_part="lastname"` (строка) | `TypeError` | Передавать только enum |
| `gender="m"` (строка) | `AttributeError` | Маппинг `m → Gender.MALE`, `f → Gender.FEMALE` и `known_gender=True` |
| `Гнедич` с `Gender.MALE` или `ANDROGYNOUS` | Гнедича, Гнедичу… | Пол обязательно брать из контента, не из детектора: `detect(lastname="Гнедич")` → `ANDROGYNOUS` |
| Пётр / Лев / Илья / Салтыков-Щедрин / Шевченко / Белых | Петра / Льва / Ильёй / Салтыкова-Щедрина / несклоняемо / несклоняемо | Беглые гласные, ё → е, двойные фамилии и несклоняемые обрабатываются корректно |

**Вывод:** `pytrovich 0.2.0` подходит, альтернатива не нужна. Ручные исправления — через `characters.yaml → forms`, а `python -m engine names` выводит таблицу для вычитки. Запасной вариант, если в настоящем составе найдутся массовые ошибки: `pymorphy3` 2.0.6 (словарный, тяжелее, ФИО склоняет хуже на редких фамилиях), но только как источник подсказок для `forms`, а не как замена.

## 8. Найденные несостыковки (технические)

Формат: что → где → предложение (вариант по умолчанию). Пункты с пометкой «вопрос N» вынесены в §9. Сюжетные расхождения — в `docs/STORY-ISSUES.md`; отсюда туда отнесены неполный список судеб в `finale.yaml` (строки для `stas`, `reznikova`, `gnedich`, `viktor`, `dmitriy` добавлены — S-11; у погибшего `voroncov` строки нет намеренно) и прочие вопросы сюжета.

Перекрёстная проверка скриптом подтвердила следующее:
- все `c.<id>`, `w.<путь>` и ID документов в ответах, основаниях, `doc` и `page` существуют;
- у каждого `kind: lab` документа ровно один результат, тело есть;
- у оснований `stage ≤ stage` результата, `from_stage` объекта ≤ этапа результата;
- комбинации (объект, вид, основание) уникальны: правило «самый поздний этап» текущим контентом не задействуется;
- у всех обязательных вопросов по 3 подсказки, у бонусных и финальных — 0;
- ответы `person`/`persons` входят в пул, ответы `choice` — среди вариантов;
- единиц 23, обязательных 12 (s1: 5, s2: 3, s3: 4), бонусов 5, финальных 5. Максимум 225 совпадает с docs/01 §6.

### A. Файлы и пути

- **A1.** Нет файлов `body`: `content/pages/news/article.md` (`news.article.body`) и `content/pages/cloud/if_you_read_this.md` (`cloud.folders[letter].body`). Предложение: отсутствующий `body` — такая же заглушка, как отсутствующее медиа: «Здесь будет …» в HTML, запись в списке `TODO(content)`, ошибка только в `--release` (вопрос 4).
- **A2.** Папки `media/` нет совсем: нет ни портретов, ни фото, ни аудио, ни видео. Сборка обязана работать без неё — плейсхолдеры и предупреждение.
- **A3.** Папки `content/chats/` (docs/03) нет. Её создаёт P07 — это ожидаемо.
- **A4.** `documents/4-08.md`: в front matter `media: ["lab/station_cam.jpg"]`, а в тексте «media/station_cam.jpg». Источником считаем front matter, текст — заглушка.
- **A5.** Front matter документов (`id`, `form`, `title`, `media`) в docs/03 не описан, есть только в P03 и P05. Предложение: модель `DocFrontMatter`. Для результатов экспертиз `id` из front matter должен совпадать с `doc` результата, `title` — с `documents.yaml` (сейчас совпадают все 5). `R-01-*` в реестр не входят — это документы развязки, их ID проверяются только на уникальность. `form` ∈ {`expert`, `operator`, `video`, `protocol`, `letter`} — используются ровно эти пять.

### B. `characters.yaml`

- **B1.** У 10 фоновых персонажей `last` и `first` = `"TODO(content)"`, `middle: ""`. Проверено: склонение не падает (§7). `names` и сборка проходят, в `--release` — ошибка.
- **B2.** У 3 служебных и 12 фоновых нет `age` и `photo`. В схеме оба поля необязательны (`int | None`, `str | None`), хотя пример docs/03 их показывает. `middle` тоже необязательно, `None` → `""`.
- **B3.** `role` используется как атрибут (`{{ c.gromov.role }}` в `pages/gromov`), а в таблице docs/03 §1 он не описан, хотя есть в P03. У `rodionov_director` `role` содержит «Сценическая мастерская» из `leak_watchlist`. Правило: персонажи не выгружаются целиком ни в открытые файлы, ни в `pack-1` (его ключ публичный). В пакеты идут только персонажи из пулов: ID, ФИО и портрет.
- **B4.** Пул `default`: docs/01 §3 — «все лица дела, кроме служебных», docs/03 — флаг `in_pool`. Сейчас это одно и то же множество (14 человек, включая погибшего `voroncov`). Предложение: источник — `in_pool: true`, порядок как в `characters.yaml`. Предупреждение, если у `service` или `background` стоит `in_pool: true`.
- **B5.** `nick` есть только у `viktor`, в шаблонах не используется. Атрибут `c.X.nick` → `str | None`.
- **B6.** Формат `short()`: в docs/03 §1 «Завьялов Ю. В.», в примере docs/03 §4 «М. А. Громова» (вопрос 7).
- **B7.** Значения в примерах docs/03 расходятся с контентом (например, возраст Завьялова 58 против 61, названия объектов экспертизы). Источник — `content/`, примеры не нормативны.
- **B8.** Имя вписано текстом, а не шаблоном: `documents/R-01-confession.md` — «Иван просто уснёт…». При замене имён в P09 не поменяется; предложить `{{ c.voroncov.first() }}` (это и так делает P09 п.3). **Исправлено** вместе с S-12.

### C. `stages.yaml`

- **C1.** У полей формы есть `pool: default` (`s1.q1.conflict`, `s1.q1.delivered`) и `options` (`s3.q3.how`, `s3.b1.plan`), а docs/03 описывает `options` и `pool` только для вопросов. Предложение: поле формы — та же модель единицы, что и вопрос, без `kind`, `hints` и `fields`. Вложенных форм нет.
- **C2.** `leak_scan: false` стоит на вопросе (`s1.b1`), а docs/03 говорит «у единицы». Разрешаем на вопросе (действует на все его единицы) и на поле (переопределяет).
- **C3.** `help` и `items` описаны только в §6а, не в примере §5 — допустимо. **Карточки `order` в `content` перечислены ровно в порядке ответа** (k3…r4 = `answer.canon`). Сборщик обязан перемешать их детерминированно (затравка — соль единицы), убедиться, что перестановка ≠ ответу, и класть в пакет только перемешанный порядок. JS ничего не перемешивает, поэтому паритет генераторов случайных чисел не нужен.
- **C4.** `kind: bonus` в этапе 4 (`s4.fb`) согласован с docs/01 §2, §8 и docs/03 §5. Правила схемы:
  - в этапе 4 нет `mandatory`, а `final` есть только в этапе 4;
  - бонус этапа 4 показывается последним, интерфейс сортирует сам, независимо от позиции в файле;
  - у бонусных и финальных вопросов `hints` пусты или отсутствуют.
- **C5.** У этапа 4 нет `on_complete`. Схема: `on_complete` обязателен для `n < max(n)` и отсутствует у последнего. Текст в контенте «Ответ принят. Вскройте конверт № 2.», в docs/01 §11 и docs/04 — «Откройте конверт №2». Интерфейс показывает текст из контента. `on_complete` этапа N кладём в пакет N.
- **C6.** Типы вопросов:
  - используются: `form`, `order`, `text`, `persons`, `choice`, `person`, `document`, `time` (в полях);
  - не используются в вопросах: `date`, `number`, `multi` (`date`, `time`, `number` есть в параметрах экспертиз);
  - `password` есть в нормализации docs/02 §2, но не в типах вопросов docs/01 §3 — он нужен только облаку.

  Реализуем и тестируем все типы.
- **C7.** `secret_N` строится **только из обязательных единиц** (docs/02 §3.4): бонусы на ключи не влияют, это правильно. Поля формы раскрываются в порядке `fields`, вопросы — в порядке `questions`. Для `s1` это `s1.q1.time`, `s1.q1.conflict`, `s1.q1.disease`, `s1.q1.delivered`, `s1.q2`. Канон `order` и `persons` содержит запятые; на однозначность это не влияет, потому что пути фиксированы. Следствие — R8.
- **C8.** Список документов для типа `document` (docs/01 §3) — «бумажные … плюс результаты экспертиз». Онлайн-документы (`1-12`, `1-13`, `4-01`) не упомянуты, хотя тоже «получены». Предложение: включать документы всех видов из открытых этапов плюс выполненные экспертизы; тот же список — для «Основания» в лаборатории.
- **C9.** Прогресс `units[path].canon` (docs/02 §4) показан только для формы (`{"time": …}`). Предложение: для простого вопроса `canon` — строка, для формы — объект «поле → канон». `wrong[path]` — `wrongHash` по `docs/FORMATS.md` §7.1 (решение F17).
- **C10.** Допуск времени через полночь (например, 23:58 ± 5) docs не описывают. Предложение: по модулю 24 ч. Текущий контент не затрагивает (23:40 ± 0).

### D. `expertise.yaml`

- **D1.** Атмосферные результаты (`theater-cam`, `inhaler-prints`, `pillbox-prints`, `water-chem`) хранят текст в `text`, а содержимое записи в docs/02 §3.6 описано только для документов (`doc`, `title`, `html`, `media`). Предложение: `{"v": 1, "doc": null, "title": "<объект>: <вид>", "form": null, "html": "<p>текст</p>", "media": []}` (`docs/FORMATS.md` §3.2, F8). В документы не добавляется, штрафа нет, `lab.done[fp] = null`.
- **D2.** `water-chem` с `stage: 1` стоял под комментарием «этап 3». **Исправлено** (S-04): запись перенесена в блок этапа 1.
- **D3.** Строка `labInfo` при пустых параметрах — с хвостовым `|` или без (вопрос 1).
- **D4.** `fp` в `lab.done` и `lab.rejected` не определён. Предложение: `b64u(sha256(UTF8(object|type|basis|p)))`, где `p` — нормализованные параметры.
- **D5.** Где лежат каталоги: виды исследований и объекты с `from_stage: 1` — в `pack-1`, объекты этапа N — в пакете N; в `public.json` ничего. `station-video` даёт 1 × 15 × 1 × 1 × 1 = 15 записей (порог 200 не достигнут).

### E. `pages/`

- **E1.** Формальной схемы `page.yaml` нет: docs/03 §8 ссылается на docs/04, но docs/04 описывает интерфейс, а не поля. Фактические поля:
  - общие: `slug`, `doc`, `locked`, `qr_label`, `brand` (5 страниц; в docs/03 не описан), `title` (`call`, `video`), `forbidden` (`news`);
  - `call`: `record{datetime, number, duration, operator}`, `audio`, `note`;
  - `gromov`, `inna`: `profile{person, position, city, avatar, cover, bio}`, `posts[{datetime, geo, text, photo, likes, comments, caption}]`;
  - `news`: `article{datetime, headline, photo, body}`, `sidebar`, `comments`, `ads`;
  - `pharma`: `disclaimer`, `drugs[{name, trade, group, indications, contraindications, side_effects}]`;
  - `cloud`: `password`, `account`, `banner{scheduled, last_confirmation}`, `folders[{id, title, kind: table|chat|letter|locked, columns, rows, participants, messages, body}]`;
  - `video`: `source`, `file{name, size, created, device, duration, resolution}`, `video`.

  Пустые списки `sidebar`, `comments`, `ads`, `messages`, `posts[].comments` не задают структуру элементов. Вопрос 8.
- **E2.** Поля медиа: docs/03 §2 перечисляет `photo`, `avatar`, `audio`, `video`, а в контенте есть ещё `cover`. Медиа определяются по полям схемы, а не по списку имён.
- **E3.** `forbidden` в `news` — основы слов («таблетк», «отравлен»), поэтому ищем **подстроку** в `base()` отрендеренного текста всей страницы (статья, колонка, комментарии, баннеры). Целые слова, как в leak scan, здесь не подходят.
- **E4.** `locked` — `false | true | "password"`; YAML даёт `bool` и `str`, модель — `Literal[False, True, "password"]`.
- **E5.** Пароль облака (`cloud.password`, сейчас `TODO(content)`) не входит в leak scan по docs/06 §3, хотя напечатан только в записке 4-13. Предложение: добавить его в «иголки» и в `--release` требовать не-TODO.
- **E6.** Документ `4-13` (`paper`, `page: cloud`) и `4-01` (`online`, `page: cloud`) ссылаются на одну страницу, а `cloud.doc = 4-01`. Валидатор: у `page.doc` должно быть `page == slug`; несколько документов на одну страницу допустимы; QR — один на страницу.
- **E7.** Оболочка закрытой страницы не должна раскрывать названия документов этапов 2–4 (docs/03 §4). Предложение: `<title>` оболочки — бренд из `world.yaml` (для `video` — `brands.system`).
- **E8.** Даты в контенте в ISO (`2026-11-10T19:30`). Форматирование для показа — фильтр шаблонов сайта (`|dt`), не контент.
- **E9.** `video.source` использует `full('gen')` («Волкова Артёма Андреевича»), а docs/04 — «Волкова А. А.». Источник — контент.

### F. Криптосхема, leak scan, модель угроз

- **F1.** **Ответы финала доступны из консоли с начала этапа 4.** `finale.json` с полем `answers` шифруется `HKDF(K_4)`, а `K_4` есть у команды с момента входа в финал. При статическом сайте это неустранимо:
  - развязка «одна для всех» и должна открываться при *любых* ответах. Значит, её ключ не может зависеть от правильности ответов — только от того, что у команды уже есть (`K_4` и публичные данные). Отдельный ключ для `answers` ничего не даёт по той же причине: его тоже пришлось бы выводить из `K_4`, иначе клиент не покажет разбор после проваленного вопроса;
  - даже без `finale.json` в `pack-4` лежат записи-проверки финальных вопросов. Из консоли можно перебрать 5–6 вариантов каждого `choice`, не «отправляя» ответ. Это тот же класс атаки, что уже признан в docs/02 §6 («скрипт перебора»).

  Дёшево и полезно: (а) клиент не скачивает и не расшифровывает `finale.json` до последнего ответа и не кладёт его содержимое в `localStorage` — тогда «Сеть», «Исходный код» и «Хранилище» ничего не показывают; (б) дописать в модель угроз docs/02 §6 строку «ответы финала и бонусов достижимы из консоли разработчика после входа в этап 4». Предложение — принять (вопрос 10).
- **F2.** Ключ медиа закрытых страниц: в docs/02 §3.8 — «шифруются тем же ключом» (`K_p`), в §3.6 и §4а — «у каждого файла свой случайный ключ, он хранится в ссылающемся зашифрованном объекте». Противоречие проявится, если один файл используется и закрытой страницей, и экспертизой или пакетом (например, портрет). Вопрос 6.
- **F3.** Портреты: §4а называет их открытыми медиа, но правило «только зашифрованный контент → шифровать» делает их зашифрованными: портреты нужны только в пулах внутри пакетов. Исключение — `gromov.jpg`, он же аватар открытой страницы. Вопрос 5.
- **F4.** Leak scan: «первые 40 символов» (docs/06 §3.7) плюс поиск «по целым словам». Обрезанное на 40-м символе слово не совпадёт ни с одним целым токеном, и проверка молча пропустит утечку. Вопрос 9.
- **F5.** Короткие значения: `number` и короткий `text` (например, «2») дадут ложные срабатывания, а порог «от 4 символов» есть только у `params_answer`. Предложение: единый порог — значения короче 4 символов после нормализации не ищутся, но перечисляются в отчёте `check`. Сейчас под порог попадает только параметр кассы «2». Время ищем во всех раскрытых вариантах допуска (`19:33…19:37`, `19:48…19:52`, `14:30…14:44`), даты — и в исходном («30.10.2026»), и в нормализованном («2026-10-30») виде.
- **F6.** Leak scan вводных писем и подсказок с заглушками: у трёх вводных одинаковое начало «TODO(content): вводное письмо к конверту», у пяти документов — «TODO(content): полный текст документа.». Пока это не открытый текст, проблем нет. Но вставлять в открытые плейсхолдеры исходный текст `TODO(content): …` из закрытых источников нельзя — только нейтральное «Здесь будет …».
- **F7.** `file://` (docs/02 §1): формулировка «Web Crypto не работает» неточна, см. R6. Сообщение и проверка — в классическом `boot.js`.
- **F8.** `buildId` не определён. Предложение: `YYYYMMDDTHHMMSSZ-<первые 8 hex sha256(canonical public.json без поля buildId)>` (`docs/FORMATS.md` §1, F2). Используется только для показа и имени архива; совместимость прогресса определяют `saltsId` и расшифровка пакета. Пакеты при каждой сборке получают новые nonce и паддинг, но ключи те же, поэтому прогресс переживает пересборку без изменений контента.
- **F9.** `saltsId` меняется при дописывании соли новой единицы. Это делает прогресс «несовместимым», даже если старые ключи валидны. Принимаем, интерфейс честно предлагает начать заново.
- **F10.** Нормализация ID и неоднозначные форматы времени и дат (вопросы 2–3).
- **F11.** Пути в `dist/` абсолютные от корня домена (`/assets/…`, `/data/…`, `/m/…`), поэтому сайт размещается только в корне домена. Валидатор P03: в `settings.domain` нет пути (ошибка в `--release`). Подробно и вместе с остальными форматами данных engine ↔ site — `docs/FORMATS.md` (решения F1–F19).

## 9. Вопросы к автору

> **Решение автора (2026-10-13): все 10 вопросов — по умолчанию.** Варианты «По умолчанию» ниже — принятые решения; они обязательны для P02–P03 и последующих шагов. Пункты раздела 8, где предложен вариант, тоже считаются принятыми, если автор не сказал иное.

Только то, без чего нельзя начать P01–P03. У каждого вопроса есть вариант по умолчанию: если ответа нет, делаем так.

**Нормализация и криптоформаты (P02)**

1. Строка ключа экспертизы без параметров: `detgame/lab/v1|<объект>|<вид>|<основание>|` с завершающим `|` или без него?
   *По умолчанию:* всегда с завершающим `|` (ровно четыре `|` после префикса), чтобы формат не зависел от наличия параметров; фиксируется векторами.
2. ID (`choice`, `person`, `document`, `multi`, `persons`, `order`): по docs/02 — «как есть», но P02 просит вектор «перепутанный регистр ID». Приводить к нижнему регистру?
   *По умолчанию:* да — `lower()`/`toLowerCase()`, затем проверка `^[a-z0-9_-]+$`, иначе невалидно; валидатор контента требует ID в нижнем регистре (сейчас так и есть).
3. Неоднозначный ввод времени и даты: «21:18:00» (три группы), «8» (одна группа из 1–2 цифр), ISO «2026-10-30».
   *По умолчанию:* всё невалидно (не попытка, подсказка формата), строго по таблице docs/02 §2.

**Сборка: файлы, медиа, схемы (P03)**

4. Отсутствующий файл `body` (`pages/news/article.md`, `pages/cloud/if_you_read_this.md`) — ошибка сборки или заглушка?
   *По умолчанию:* заглушка, как у отсутствующего медиа: «Здесь будет …», запись в списке `TODO(content)`, ошибка только в `--release`.
5. Портреты персонажей: открытые файлы (docs/02 §4а) или зашифрованные (на них ссылаются только пакеты)?
   *По умолчанию:* открытые — явное исключение из правила §4а: имена и лица участников есть в бумажной папке, а один открытый файл проще и легче, чем копии в каждом пакете.
6. Медиа закрытых страниц: шифровать ключом страницы `K_p` (docs/02 §3.8) или случайным ключом файла, который хранится в ссылающемся зашифрованном объекте (§3.6, §4а)?
   *По умолчанию:* единое правило §4а для всех зашифрованных медиа (страницы, экспертизы, развязка); §3.8 считать неточностью.
7. Формат `short()`: «Завьялов Ю. В.» (docs/03 §1) или «М. А. Громова» (пример docs/03 §4)?
   *По умолчанию:* «Фамилия И. О.» с неразрывными пробелами после фамилии и между инициалами; второй формат не делаем, пока он не понадобится в контенте.
8. Схемы `page.yaml` не описаны в docs/04. Строить модели по текущим файлам со строгим запретом лишних полей?
    *По умолчанию:* да, модель на каждый `slug` с `extra="forbid"`. Для пустых списков структура такая:
    - `sidebar`: `[{title, datetime}]`;
    - `comments`: `[{author, datetime, text}]`;
    - `ads`: `[{title, text}]`;
    - `cloud.chat.messages`: `[{from, datetime, text}]`;
    - `posts[].comments`: `[{author, text}]`.

**Leak scan и модель угроз (P03)**

9. «Первые 40 символов» плюс поиск «по целым словам» несовместимы: слово, обрезанное на 40-м символе, ни с чем не совпадёт. Как брать фрагмент?
   *По умолчанию:* берём `base()` текста и набираем целые токены, пока длина ≤ 40 символов (минимум 3 токена; короткий текст — целиком); значения ответов короче 4 символов не ищутся и перечисляются в отчёте `check`.
   *Пересмотрено (QA P08, 2026-10-13):* вместо начала текста — шинглы из 4 токенов `base()` по всему тексту; исключаются шинглы только из служебных слов, заглушки «Здесь будет …», статический текст шаблонов и строк интерфейса, открытые по замыслу тексты. Подробно — docs/06 §3.7, `engine/leakscan.py`.
10. Ответы финала и бонусов достижимы из консоли разработчика с начала этапа 4 (`finale.json` на ключе `K_4`, плюс записи-проверки в `pack-4`); при статическом сайте это неустранимо. Принимаем?
   *По умолчанию:* принимаем. `finale.json` скачивается и расшифровывается только после последнего ответа финала и не сохраняется в `localStorage`; в модель угроз добавляется честная строка об этом.
