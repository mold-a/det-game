# Разработка: окружение и команды

Нужно: **Python 3.11+**, **Node.js 22 LTS** (с npm), **Git**. Все команды запускаются из корня репозитория.

## Установка с нуля

### Windows (PowerShell или cmd)

```
py -3 --version                     # 3.11 или новее; если нет — python.org, галочка «Add to PATH»
py -3 -m venv .venv
.venv\Scripts\activate              # PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m playwright install chromium
npm i
npx playwright install chromium
```

Если PowerShell не даёт запустить `Activate.ps1` («running scripts is disabled»), один раз выполните
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` или работайте из `cmd` (`.venv\Scripts\activate.bat`).

### macOS

```
python3 --version                   # 3.11+; иначе: brew install python@3.12
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
npm i                               # Node 22: brew install node@22 или nvm
npx playwright install chromium
```

### Linux

```
python3 --version                   # 3.11+; Debian/Ubuntu: sudo apt install python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install --with-deps chromium   # --with-deps ставит системные библиотеки
npm i
npx playwright install chromium
```

Кавычки в `".[dev]"` нужны для zsh (macOS) и ничему не мешают в cmd, PowerShell и bash.

### Про Playwright

Playwright стоит дважды: Python-версия (печать PDF/PNG в `qr`, `answers`, `chatshot`) и
`@playwright/test` для сквозных тестов. Их версии закреплены на одной минорной
(`playwright>=1.63,<1.64` в `pyproject.toml`, `"~1.63.0"` в `package.json`), поэтому обе
используют одну и ту же сборку Chromium, и вторая команда `playwright install` ничего не
скачивает заново. Меняя версию — меняйте в обоих файлах.

## Команды

После активации venv (`python` — это `.venv`):

| Команда | Что делает | Шаг |
|---|---|---|
| `python -m engine --help` | список команд | P01 |
| `python -m engine serve [--port 8000]` | раздаёт `dist/` на http://127.0.0.1:8000 без кеширования | P01 |
| `python -m engine build [--release]` | собирает `dist/` из `content/` и `site/` | P03 |
| `python -m engine check [--release]` | самопроверка: прохождение правильными ответами + leak scan | P03 |
| `python -m engine dump-answers` | ответы и варианты → `tests/.answers.json` (для JS/e2e) | P03 |
| `python -m engine names` | падежные формы всех персонажей | P03 |
| `python -m engine rotate-salts --yes` | пересоздать соли и ключи страниц (после — перепечатать QR) | P03 |
| `python -m engine vectors` | векторы криптографии → `tests/vectors/crypto.json` | P02 |
| `python -m engine qr` | QR-коды для печати → `print/qr/` | P07 |
| `python -m engine answers` | «Аварийный конверт» → `print/answers.pdf` | P07 |
| `python -m engine chatshot` | «скриншоты» переписок → `print/chats/` | P07 |
| `python -m engine paper [--only ID …] [--release]` | бумажные документы конвертов из `content/paper/` → `print/paper/` (PDF, сборники конвертов, превью PNG) | P07 |
| `python -m engine release` | build --release + check --release + архив dist | P08 |
| `python -m engine import-cast <xlsx> [--write] [--familiar ID=Имя]` | имена из таблицы персонажей → `content/characters.yaml` (без `--write` — только отчёт и diff) | P09 |

Все команды реализованы (заглушки «Будет реализовано в P0X», код 2, больше не осталось).

Тесты:

```
python -m pytest            # Python
npm run test:js             # JS: node --test "tests/js/*.test.mjs"
npm run test:e2e            # сквозные (Playwright): сначала build, в другом окне — serve
```

`serve` без собранного `dist/` пишет, что сначала нужен `python -m engine build`, и выходит с кодом 1.
Порт занят — `python -m engine serve --port 8001`.

`serve` поддерживает HTTP Range (`Accept-Ranges: bytes`, ответ `206 Partial Content`, один диапазон
`bytes=a-b`, `bytes=a-` или `bytes=-n`; невыполнимый — `416`). Без этого iOS Safari не проигрывает
аудио и видео: проверяя медиа с iPhone в локальной сети, используйте именно `serve`, а не другой
простой сервер. Помните, что по `http://` с другого устройства Web Crypto недоступна (PLAN R6) —
для полной проверки с телефона нужен HTTPS (выкладка или туннель).

## Кириллица в консоли Windows

`engine/__main__.py` первым делом переключает `stdout` и `stderr` на UTF-8
(`sys.stdout.reconfigure(encoding="utf-8")`), поэтому вывод на русском не падает
с `UnicodeEncodeError` в cmd и PowerShell — `chcp 65001` не нужен. Это проверяет тест
`tests/test_cli.py::test_cyrillic_output_survives_non_utf8_console` (имитирует консоль
с однобайтовой кодировкой).

Если кириллица всё же ломается (старая консоль показывает «кракозябры», или падает
посторонний скрипт без такой настройки), запасной вариант — включить UTF-8-режим Python:

```
set PYTHONUTF8=1              # cmd
$env:PYTHONUTF8 = "1"         # PowerShell
```

или навсегда — в переменных среды пользователя. Для «кракозябр» в старом `conhost`
помогает шрифт консоли с кириллицей (Consolas, Cascadia) или Windows Terminal.

Файлы проекта всегда читаются и пишутся в UTF-8 (`encoding="utf-8"`), независимо от
кодировки системы.

## Шрифты

PT Sans и PT Serif (OFL) лежат в `site/assets/fonts/`, подключаются в
`site/assets/css/fonts.css`. Откуда взяты и как обновить — `site/assets/fonts/README.md`.

## Свой Chromium вместо `playwright install`

Если браузер Playwright скачать нельзя, а Chromium уже установлен (например, в облачном окружении),
укажите путь к нему в переменной `PW_CHROMIUM_PATH` — её учитывают и `npx playwright test`,
и команды печати (`qr`, `answers`, `chatshot`, `paper`):

```
PW_CHROMIUM_PATH=/opt/pw-browsers/chromium npx playwright test
```

## Печать (`qr`, `chatshot`, `answers`, `paper`)

Результаты — в `print/` (в `.gitignore`: там ответы и ключи страниц, не публиковать).
Нужен Chromium для Python-пакета `playwright` (см. выше; `PW_CHROMIUM_PATH` тоже работает):

```
PW_CHROMIUM_PATH=/opt/pw-browsers/chromium python -m engine qr
```

Самопроверка QR декодированием — необязательная зависимость `qrcheck` (`zxing-cpp`, `pillow`):
`pip install -e ".[qrcheck]"`. Без неё `qr` создаёт коды и предупреждает, что проверка пропущена.
Тесты печати (`tests/test_print.py`, `tests/test_paper.py`) без браузера пропускаются с причиной
в отчёте pytest (`-rs`).

### Бумажные документы (`paper`)

Тексты конвертов 1–4 — `content/paper/<id>.md` (формат — docs/03 «paper/»), бланки —
`site/templates/print/paper/<form>.html` (контекст шаблона и классы описаны в `_base.html`).

```
PW_CHROMIUM_PATH=/opt/pw-browsers/chromium python -m engine paper              # все документы + сборники
python -m engine paper --only 1-07 1-02                                       # только эти, без сборников
python -m engine paper --release                                              # для печати к игре
```

Результат в `print/paper/`: `<id>.pdf` (A4), `envelope-<N>.pdf` — все бумажные документы конверта
по порядку `documents.yaml` (заглушки тоже); `preview/<id>.png` — первая страница для просмотра.
Сборник — склейка готовых `<id>.pdf` пакетом `pypdf` (зависимость проекта; нет его — ошибка
с подсказкой `pip install -e ".[dev]"`), поэтому у каждого документа в сборнике своя нумерация
«Лист 1…», как в отдельном PDF. С `--only` сборники не собираются. В консоли — таблица
`id | бланк | страниц | статус` (страницы — по факту из PDF через `pypdf`; `pages_hint` не совпал —
пометка в статусе) и число страниц каждого сборника.

- Нет `content/paper/<id>.md` — печатается страница-заглушка «Документ 2-05: текст не готов»;
  `build` и `check` пишут это в отчёт заглушек (`missing-paper`), `paper --release`, `build --release`
  и `release` падают.
- QR-код страницы (та же ссылка, что у `qr`; у облака — без ключа) печатается в правом верхнем углу
  с подписью `qr_label`; нужен `engine/salts.lock.json` (сначала `build`).
- `form: chat` — «скриншоты» телефона генерируются на лету из `content/chats/<id>.yaml`.
- `--release` дополнительно запрещает TODO(content) (и в файле, и после подстановки имён), отсутствующие
  файлы `media:` и домен-заглушку в QR.
- Бумага не публикуется: `build` не кладёт её в `dist/`, а `check` (пункт 7, leak scan) ищет шинглы
  текстов бумаги во всех файлах `dist/`. Цитаты открытых материалов (открытые страницы `call`, `gromov`,
  `news`, интерфейс, `public.json`) утечкой не считаются: шинглы бумаги, которые есть в публичном выводе
  сборки, из иголок вычитаются.

## Импорт имён из таблицы (`import-cast`)

```
python -m engine import-cast Персонажи.xlsx                          # dry-run: проблемы + diff, файл не меняется
python -m engine import-cast Персонажи.xlsx --write                  # записать characters.yaml
python -m engine import-cast Персонажи.xlsx --write --familiar voroncov=Петя
```

Формат таблицы (версия от 11.10.2026):

- лист «Персонажи»: заголовки во 2-й строке, 3-я — пример (пропускается), данные с 4-й; колонки
  «Роль (рабочее имя)», «ФИО в документах», «Возраст в игре»;
- лист «Фоновые имена»: заголовки в 1-й строке, данные со 2-й, строки-примера нет (так в
  `sources/cast-2026-10-14.xlsx`); колонки «Кто» и «Имя (заполни)».

Листы и колонки ищутся по названию (без учёта регистра, ё/е, пунктуации и лишних пробелов), не по
букве; другие колонки игнорируются. Строка ↔ персонаж — по `working` в `characters.yaml` (то же
сравнение). Персонаж с `importance: background` ищется сначала на листе «Фоновые имена», остальные —
на «Персонажи»; если там нет — на другом листе.

Правила:

- «ФИО в документах» — «Фамилия Имя Отчество» (ровно 3 части), иначе проблема (пустая ячейка — тоже).
  «Имя (заполни)» — «Имя Фамилия» (пол — из `content`) или ФИО; пустая ячейка — проблема, если в
  `content` у персонажа `TODO(content)`, иначе имя остаётся (предупреждение). Возраст — целое число;
  пустой — не меняется, текст («в жизни 32») — проблема.
- Пол — по отчеству: `-вич` (и Ильич, Никитич, Фомич, Кузьмич, Лукич) → `m`; `-вна`/`-чна`/`-ична` → `f`;
  иное — проблема (пол не угадывается). Смена пола — предупреждение в отчёте.
- `father: <id>`: из таблицы берётся только имя (и возраст); фамилия и отчество выводятся
  `surname_for`/`patronymic_for` от отца из новой версии данных. В ячейке может быть только имя или
  ФИО — тогда фамилия и отчество сверяются с выведенными, расхождение — проблема. Ручная
  `forms.<last|middle>.nom` ребёнка важнее правила; если имя отца не даёт отчества (`DeclensionError`) —
  проблема: впишите отчество в `middle` и `forms.middle.nom` вручную и повторите импорт.
- `cast: false` — пропускается, строка в таблице не ищется (и не считается лишней).
- `familiar`: если у персонажа меняется имя — проблема «уточните дружеское имя…»; новое дружеское
  имя задаёт автор флагом `--familiar ID=Имя` (сама команда `familiar` не придумывает).
- ID, порядок, комментарии и прочие поля не меняются: правятся только значения `last`, `first`,
  `middle`, `age`, `gender` (и `familiar` по флагу) — точечно, в блочных и в однострочных
  `{ id: …, … }` записях; недостающее поле (например, `age`) вставляется рядом.
- Строка таблицы с именем, не сопоставленная ни с одним персонажем, ручные `forms` у меняющегося
  имени, удаление отчества, смена пола — предупреждения (не мешают записи). Строки без имени
  (итоги «Ролей заполнено: …») не сопоставляются молча.

Любая проблема — код 1, файл не пишется. Перед записью новая версия проверяется `load_content` на копии
`content/`; после записи — ещё раз на настоящем `content/` (ошибка → прежний файл возвращается).
После импорта: `python -m engine names` (вычитать падежи), `python -m engine build && python -m engine check`.

### Имена буквами (`check`, пункт 10)

Импорт меняет только `characters.yaml`; имя, вписанное в текст буквами («Иван Сергеевич»
вместо `{{ c.voroncov.io() }}`), останется рабочим. Поэтому `check` ищет в сырых текстах
`content/` (список файлов и правила — docs/06 §3 п.10, код — `engine/hardnames.py`) все
падежные формы фамилии, имени, отчества и `familiar` персонажей с `cast: true` и печатает:

```
Предупреждения (7):
  [10. Имена буквами] content/paper/1-08.md:83: найдено «Иван Сергеевич» → {{ c.voroncov.io() }}
```

Без `--release` это предупреждение, с `check --release` и в `release` — ошибка. Ложное
срабатывание на обычное слово («Вера в победу») — добавьте имя в `COMMON_WORD_NAMES`
в `engine/hardnames.py` с комментарием; фамилию — в `SURNAME_EXCEPTIONS` (только если
она и правда встречается с заглавной буквы не как имя). Слова из строк `world.yaml`
(роль «Нина») исключаются для одиночных имён автоматически. Отдельной команды нет.
