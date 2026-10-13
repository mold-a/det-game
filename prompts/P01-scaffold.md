# P01. Каркас репозитория

---

Работаем по `CLAUDE.md` и `docs/PLAN.md`. Цель шага — пустой, но рабочий каркас: всё устанавливается, команды запускаются, тесты зелёные.

**Сделай:**

1. Структуру папок из `CLAUDE.md` → «Структура».
2. `pyproject.toml`: Python ≥ 3.11, зависимости из `CLAUDE.md` → «Стек» с диапазонами версий, `pytest` в dev-зависимостях. Пакет `engine` устанавливается через `pip install -e .`; явно `packages = ["engine"]` (в корне есть папки `site`, `content`, `media`, `print` — автопоиск пакетов setuptools на них споткнётся).
3. `package.json` только для тестов: `"engines": {"node": ">=22"}`, `@playwright/test` в devDependencies, скрипты `test:js` (`node --test "tests/js/*.test.mjs"` — кавычки обязательны, шаблон раскрывает сам Node, так работает и в cmd, и в PowerShell) и `test:e2e`.
4. `.gitignore`: `dist/`, `print/`, `node_modules/`, `.venv/`, `__pycache__/`, `test-results/`, `tests/.answers.json`. **Не** игнорировать `engine/salts.lock.json` и `content/`.
5. `engine/__main__.py` на `argparse` с подкомандами: `build [--release]`, `check [--release]`, `serve [--port 8000]`, `qr`, `answers`, `names`, `vectors`, `rotate-salts --yes`, `chatshot`, `import-cast <xlsx>`, `release`, `dump-answers`. Пока всё, кроме `serve`, печатает «Будет реализовано в P0X» с номером шага и возвращает код 2.
6. `serve`: раздаёт `dist/` на `127.0.0.1`, с правильными MIME-типами для `.json`, `.mp4`, `.mp3`, `.webp`, `.woff2`, `.bin`, `.svg`; без кеширования (`Cache-Control: no-store`). Если `dist/` нет — понятное сообщение.
7. Шрифты PT Sans, PT Serif (OFL): положи `woff2` в `site/assets/fonts/` и файл лицензии рядом. Если скачать нельзя — создай `site/assets/fonts/README.md` с инструкцией, откуда взять файлы, и задай в CSS запасные системные шрифты.
8. Тесты-заглушки: `tests/test_smoke.py` (импорт `engine`), `tests/js/smoke.test.mjs` (импорт пустого `site/assets/js/core/normalize.js`).
9. `docs/DEV.md`: как поставить окружение с нуля на Windows, macOS и Linux (venv, `pip install -e .[dev]`, `python -m playwright install chromium`, `npm i`, `npx playwright install chromium`) и как запустить каждую команду. Проверь, что вывод кириллицы в консоль Windows не падает.

**Не делай:** логику сборки, нормализации, криптографии и интерфейса — это следующие шаги.

**Готово, когда:**
- `python -m engine --help` показывает все подкоманды;
- `python -m pytest` и `npm run test:js` проходят;
- `python -m engine serve` отвечает на `http://127.0.0.1:8000` (с временным `dist/index.html`).

**Отчёт:** что создано, точные команды проверки, что не удалось (например, шрифты).
