# Шрифты

PT Sans и PT Serif — шрифты ParaType, лицензия SIL Open Font License 1.1
(тексты лицензий: `OFL-PT-Sans.txt`, `OFL-PT-Serif.txt`). Подключаются в
`site/assets/css/fonts.css`, сайт не обращается ни к каким CDN.

## Откуда взяты

Из npm-пакетов Fontsource (упакованные шрифты Google Fonts), скачаны `npm pack`,
в `package.json` проекта не добавлены:

| Пакет | Версия | Лицензия |
|---|---|---|
| `@fontsource/pt-sans` | 5.3.0 | OFL-1.1 |
| `@fontsource/pt-serif` | 5.3.0 | OFL-1.1 |

Взяты файлы `files/pt-<sans|serif>-<subset>-<начертание>.woff2`:

- подмножества `cyrillic` и `latin` (разбиты по `unicode-range`, браузер грузит только нужное);
- начертания `400-normal`, `400-italic`, `700-normal` (жирный курсив синтезирует браузер).

Лицензии — файл `LICENSE` из каждого пакета без изменений.

## Как обновить или добавить начертание

```
mkdir tmp-fonts && cd tmp-fonts
npm pack @fontsource/pt-sans @fontsource/pt-serif
tar xzf fontsource-pt-sans-*.tgz        # распакуется в package/
# скопировать нужные package/files/*.woff2 в site/assets/fonts/
# и добавить @font-face в site/assets/css/fonts.css;
# диапазоны unicode-range — в package/unicode.json
```

Альтернатива — https://fonts.google.com/specimen/PT+Sans и
https://fonts.google.com/specimen/PT+Serif (TTF, перевести в woff2 любым конвертером)
или https://www.paratype.ru/ (оригинал от ParaType).

Если файлов нет, CSS откатывается на системные шрифты из `--font-sans` и
`--font-serif` (Segoe UI / Roboto / Arial и Georgia / Times New Roman).

## Шрифты бумаги конвертов

Только для печати (`python -m engine paper`, `site/templates/print/paper/paper.css`), сайт их не
подключает. Все — SIL Open Font License 1.1, из npm-пакетов Fontsource:

| Шрифт | Пакет | Файлы | Лицензия | Где |
|---|---|---|---|---|
| Caveat | `@fontsource/caveat` 5.3.0 | `caveat-<subset>-400/600-normal.woff2` | `OFL-Caveat.txt` | «ручка»: графы, подписи, записки |
| PT Mono | `@fontsource/pt-mono` 5.3.0 | `pt-mono-<subset>-400-normal.woff2` | `OFL-PT-Mono.txt` | рапорт «на машинке» |
| Oswald | `@fontsource/oswald` 5.1.0 | `oswald-<subset>-500/600/700-normal.woff2` | `OFL-Oswald.txt` | шапки организаций и заголовки документов |
