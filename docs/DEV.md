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
| `python -m engine release` | build --release + check --release + архив dist | P08 |
| `python -m engine import-cast <xlsx>` | имена из таблицы персонажей → `content/characters.yaml` | P09 |

Пока шаг не сделан, команда печатает «Будет реализовано в P0X» и завершается с кодом 2.

Тесты:

```
python -m pytest            # Python
npm run test:js             # JS: node --test "tests/js/*.test.mjs"
npm run test:e2e            # сквозные (Playwright): сначала build, в другом окне — serve
```

`serve` без собранного `dist/` пишет, что сначала нужен `python -m engine build`, и выходит с кодом 1.
Порт занят — `python -m engine serve --port 8001`.

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
и команды печати (`qr`, `answers`, `chatshot`):

```
PW_CHROMIUM_PATH=/opt/pw-browsers/chromium npx playwright test
```
