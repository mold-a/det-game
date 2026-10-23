> Актуальная версия — docs/PRODUCTION.md (статусы, свежие промпты, план). Этот документ остаётся для истории и справки.

# Желательные фото для новых страниц (черновик сценариста)

В черновиках страниц все фото — существующие файлы из `media/` (`portraits/*.jpg`, `news/voroncov_arbenin.jpg`) или `null`. Ниже — что стоит сгенерировать дальше; после утверждения файла режиссёр подставляет путь в поле `photo` / `cover`. Запросы — в стиле `docs/PROMPTS.md` (на английском, с хвостом-запретом). Сюжетных улик в этих кадрах нет; главное — **никаких надписей, логотипов, гербов, флагов и читаемых вывесок**, а люди — только по утверждённым портретам или без различимых лиц.

Общий хвост уже вписан в каждый запрос.

## F01. `theater/facade.jpg` — фасад театра (сайт `theater`, обложка)

- **Сохранить как:** `detgame-media/theater/facade.jpg`
- **Формат:** JPEG, широкая горизонталь 21:9 (обрежу сам), ≤ 1 МБ
- **Приложить:** ничего

```text
Wide photograph of the main facade of a provincial Russian-like drama theatre built in the 1950s: a light ochre neoclassical building with six white columns, a triangular pediment WITHOUT any sculpture group or emblem, wide stone steps, tall windows, a small square in front with bare November trees and a few street lamps. Early evening in November: overcast sky, wet pavement, warm light in the windows. A few tiny distant passers-by with umbrellas, faces not distinguishable. NO posters with text, NO signboards, NO letters on the building, NO flags, NO coats of arms, no vehicles with readable number plates. Very wide horizontal composition. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: на фронтоне и над входом нет надписей и гербов; ноябрь (голые деревья, мокрый асфальт); людей не узнать.

## F02. `theater/hall.jpg` — зрительный зал (сайт `theater`, «О театре»)

- **Сохранить как:** `detgame-media/theater/hall.jpg`
- **Формат:** JPEG, горизонталь 3:2, ≤ 800 КБ
- **Приложить:** ничего

```text
Photograph of an empty auditorium of a provincial drama theatre seen from the back of the stalls: rows of red velvet seats, a horseshoe-shaped dress circle with two boxes near the stage, a balcony above, a heavy dark-red stage curtain, closed, warm dim work light, a small chandelier. No people. No text on the curtain, no emblem above the stage, no signs, no exit signs with letters. Horizontal 3:2. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: ложи у сцены есть (две, рядом), надписей нет, зал пустой.

## F03. `krug/kirill_cat.jpg` — кот Кирилла (пост 07.11 «Кот работает из дома»)

- **Сохранить как:** `detgame-media/krug/kirill_cat.jpg`
- **Формат:** JPEG, квадрат 1:1, ≤ 500 КБ
- **Приложить:** фото настоящего кота дяди, если есть (тогда первой строкой: `Use image 1 as the strict reference for the cat's colour and markings.`)

```text
Casual smartphone photo of a large fluffy domestic cat lying across a laptop keyboard on a home desk, looking straight at the camera with a bored, superior expression. Next to the laptop: a mug of tea and a pair of reading glasses. Warm evening lamp light, slightly grainy home photo. The laptop screen is dark or shows only a blurred abstract wallpaper, NO readable text, no app windows, no brand logo on the laptop. No people. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: экран ноутбука без текста и логотипа; кот главный.

## F04. `krug/voroncov_rehearsal.jpg` — репетиция (пост 05.11 «прогон второго акта»)

- **Сохранить как:** `detgame-media/krug/voroncov_rehearsal.jpg`
- **Формат:** JPEG, горизонталь 4:3, ≤ 800 КБ
- **Приложить:** 1 — `portraits/voroncov.jpg` (правленый, прозрачные очки)

```text
Use image 1 as the strict identity reference. Casual backstage smartphone photo during a rehearsal on the stage of a provincial theatre: this same man, about 56 years old, with thick dark eyebrows and grey hair, wearing a plain white shirt with rolled sleeves and dark trousers (rehearsal clothes, not a full costume), glasses with transparent frames pushed up on his forehead, holding a few sheets of a script, laughing. Bare stage with work lights, a wooden rehearsal table, a couple of chairs; out of focus in the background two other actors, faces not distinguishable. Warm work lighting, slightly grainy. No readable text on the script pages (only blurred lines), no posters, no signs. Horizontal 4:3. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: лицо узнаваемо, оправа прозрачная, листы без читаемого текста. **Не** снимать в гримёрке и **не** показывать сумку, бутылку, столик с вещами — это кадры улик 1-10.

## F05. `fund/costumes.jpg` — проект «Вторая жизнь костюма» (сайт `fund`)

- **Сохранить как:** `detgame-media/fund/costumes.jpg`
- **Формат:** JPEG, горизонталь 3:2, ≤ 800 КБ
- **Приложить:** ничего

```text
Photograph in a theatre costume workshop: close-up of two pairs of hands (faces out of frame) restoring an old 19th-century dark green velvet dress on a wooden table — one hand holds a needle with gold thread, the other smooths lace on the sleeve. Around: spools of thread, a tape measure, pins in a cushion, a tailor's dummy in the background with a half-finished frock coat. Soft daylight from a window. No faces, no jewellery or brooches on the table, no readable labels or tags. Horizontal 3:2. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: **на столе нет брошей, шалей и перчаток** (это пропажи 2-08 — не дразним ложный след раньше этапа 2).

## F06. `news/yama.jpg` — яма на Садовой (статья `news-yama`)

- **Сохранить как:** `detgame-media/news/yama.jpg`
- **Формат:** JPEG, горизонталь 3:2, ≤ 600 КБ
- **Приложить:** ничего

```text
Local news photograph of a provincial city street in November: a fresh dark asphalt patch on a worn road and, three metres further, a new deep pothole filled with muddy water reflecting the grey sky. A minibus passes in the background, slightly motion-blurred, no readable route number. Five-storey residential buildings, bare trees, wet pavement. No people in focus. No readable street signs, no shop signs, no number plates. Horizontal 3:2. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

## F07. `news/hockey.jpg` — матч «Медведей» (статья `news-hockey`)

- **Сохранить как:** `detgame-media/news/hockey.jpg`
- **Формат:** JPEG, горизонталь 3:2, ≤ 800 КБ
- **Приложить:** ничего

```text
Sports photograph from the stands of a small provincial ice arena: a hockey goalie in plain dark-brown gear without any logos crouching in the goal, a puck in the air, two blurred players in plain white jerseys without numbers or logos. Bright arena light, a few rows of spectators in the foreground from behind, faces not visible. NO team logos, NO sponsor boards with text, NO numbers on jerseys, no scoreboard text. Horizontal 3:2. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

## F08. `auction/snuffbox_lot.jpg` — лот клуба (сайт `auction`, этап 4, закрытая) — по желанию

Описание — строго по 4-11: прямоугольная, серебро, позолота внутри, крышка с гильошированной эмалью, клеймо на дне (клеймо не показываем). Кадр «витринный», как его снял клуб.

- **Сохранить как:** `detgame-media/auction/snuffbox_lot.jpg`
- **Формат:** JPEG, горизонталь 4:3, ≤ 600 КБ
- **Приложить:** ничего

```text
Elegant catalogue-style photograph of an antique-looking rectangular silver snuff box standing on dark blue velvet, lid slightly open: the lid is covered with translucent deep-blue guilloché enamel over an engine-turned pattern, silver borders with fine chased leaves, the inside is gilded. Soft candle-like warm side light, dark background, shallow depth of field, a single burning candle out of focus in the background. The bottom of the box and any hallmarks are NOT visible. No hands, no people, no price tags, no labels. Horizontal 4:3. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: прямоугольная, эмаль на крышке, позолота внутри; клейма не видны; ни одного узнаваемого «фирменного» стиля известного ювелирного дома.
