> Актуальная версия — docs/PRODUCTION.md (статусы, свежие промпты, план). Этот документ остаётся для истории и справки.

# Запросы для генерации медиа (Gemini и Kling): копируй и вставляй

Готовые к вставке запросы для всех файлов набора «А» (`docs/MEDIA-PLAN-A.md`). **Этот файл главнее разделов 4-5 плана**: там запросы с «подстановками» и «+NEG», здесь они раскрыты. Сюжетные детали сверены с `content/` (1-09, 1-10, 2-03, 2-06, 2-08, 3-06, 4-08, `pages/gromov`, `pages/inna`, `pages/video`), `docs/SCENARIO.md` и `content/characters.yaml`. Если что-то расходится - прав сценарий.

Запросы написаны **на английском**: генератор точнее понимает ракурс, свет, оптику. Пояснения - на русском. Все запросы полностью заполнены: ничего подставлять не нужно, только приложить файлы, указанные в строке «Приложить».

Решения автора от 21.10, на которых построен файл: портрет «как на документ», чисто белый фон, анфас, взгляд в камеру, голова и плечи до середины груди, мягкий ровный свет, формат **4:5** (квадрат автор вырезает сам); стандарт задан готовым `portraits/voroncov.jpg`; Марина - 24 года; возраст в запросах работает в обе стороны (состарить или омолодить). Цель - правильный портрет **с одного запроса**.

## Оглавление

1. [Порядок работы](#порядок-работы)
2. [Универсальный запрос для портрета](#универсальный-запрос-для-портрета) (шаблон, как прикладывать, как править)
3. [Портреты: 14 готовых запросов](#портреты-14-готовых-запросов) (R01 правка Воронцова, P01-P14)
4. [Сцены и улики](#сцены-и-улики) (S01-S07: новость, совещание, обложка, брошь, вокзал, таблетница)
5. [Бумажные фото](#бумажные-фото) (S08-S18: гримёрка 1-10, камера 2-03, кабинет 2-06)
6. [Видео Волкова](#видео-волкова) (S19 кадр-основа, K01 шаги Kling)
7. [Что прислать оркестратору](#что-прислать-оркестратору)

Счёт запросов: 1 правка + 14 портретов + 19 запросов к картинкам (S01-S19; в S07 есть запасной вариант) + 1 сценарий для Kling = **35 запросов**.

## Порядок работы

1. **Подготовка.** Образцы лиц — по 1–2 фото на человека. Для портретов — полные промпты ниже: сначала фото человека, последним — `voroncov.jpg` как образец стиля.
2. **R01 - правка `voroncov.jpg`** (чёрная оправа -> прозрачная). Сделайте первой: правленый портрет нужен как образец в новости, на вокзале и как стиль для остальных.
3. **P02-P14 - портреты.** Каждый портрет - в **новом чате** (иначе генератор тянет лицо из предыдущего). Утвердили - сохранили - можно переходить к следующему.
4. **Сцены.** Сначала хрупкие улики (S07 таблетница, S04-S05 брошь, S06 вокзал), потом остальное. Люди в сценах - по **утверждённым портретам** (они уже нужного возраста), сырой образец - только если остался слот.
5. **Бумажные фото.** Гримёрка (S08-S10), камера у служебного входа (S11-S16) и кабинет (S17-S18) - каждая серия в **одном чате**, кадры подряд.
6. **Видео.** S19 кадр-основа -> утверждение -> K01 (Kling) после того, как я пришлю аудио монолога.
7. Неудачные и запасные варианты - в `detgame-media/_attempts/`, не удалять до проверки.

Лимиты и график по вечерам - `MEDIA-PLAN-A` §3; как работать в интерфейсе Gemini - §3.1.

---

## Портреты: как пользоваться (21.10)

Полные промпты — ниже (по просьбе автора: с ними генерация лучше). В них **нет реквизита** (наушников, сантиметров, фартуков, значков, формы) — только одежда, очки, украшения; возраст задан диапазоном и запретом «не старше».
- Вышло старше: в том же чате — `Same image, but make the person look 10 years younger. Keep the face and everything else.`
- Вышло младше: `Same image, but make the person look 5 years older.`
- Готовы: voroncov (ждёт R01 — прозрачная оправа), kirill, marina, volkov.

## Универсальный запрос для портрета

Один шаблон для всех 14 ролей. Ниже (раздел «Портреты») он уже заполнен для каждого персонажа; здесь - как он устроен и что менять, если нужна 15-я роль или перегенерация.

### Как прикладывать файлы (порядок важен)

| Слот | Что | Пояснение |
|---|---|---|
| 1 | фото человека №1 | анфас, дневной свет, без тёмных очков и фильтров |
| 2 | фото человека №2 (необязательно) | другое выражение или освещение; если фото одно - слот пропустите |
| последний | `portraits/voroncov.jpg` (после правки R01) — **прикладывать всегда последним** | образец стиля: белый фон, рамка, свет. В запросе прямо сказано не брать с него лицо, возраст и седину |

В запросе стиль всегда называется «LAST attached image», остальное - «OTHER attached images», поэтому запрос одинаково работает при 1 или 2 фото человека. Вставьте текст запроса **после** загрузки файлов, в новом чате, с включённым созданием изображений.

### Шаблон (для справки: `<<...>>` - то, что уже подставлено в готовых запросах)

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly <<AGE>> years old (<<AGE HINT>>) - age them up or down from the reference as needed. Do NOT make the person look older than <<AGE>>. Change only the apparent age, never the identity.

SUBJECT: <<SUBJECT>>.
EXPRESSION: <<EXPR>>
CLOTHES AND DETAILS: <<CLOTHES>>

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```
Откуда берутся значения: возраст - `age` из `content/characters.yaml`; пол - `gender` оттуда же (**dmitriy и gromov - женщины**); одежда и выражение - `docs/MEDIA-SHOTLIST.md` §1, `docs/VOICES.md` и таблица `MEDIA-PLAN-A` §1.1/§4.2. Возраст формулируется одной и той же фразой для всех: «Make the person look exactly N years old - age them up or down from the reference as needed». Возраст Инны и Олега в жизни неизвестен, поэтому направление (старше или моложе образца) генератор выбирает сам.

### Если портрет не получился: одна фраза-правка в том же чате

Не переписывайте запрос с нуля - напишите правку в том же чате (она экономит лимит и держит удачные части):

- **Не похоже на человека (главная правка):**
  ```text
  Same image, but make the face match the reference photos exactly (same eyes, nose, mouth, face shape and hairline); keep the white background, framing, light, age and clothes unchanged.
  ```
- Возраст: `Same image, but make the person look exactly N years old; keep the identity, background, framing and clothes unchanged.`
- Фон не белый или есть тень: `Same image, but make the background pure white (#FFFFFF), seamless, with no shadow or gradient; change nothing else.`
- Кадр другой, чем у образца: `Same image, but reframe exactly like the style reference: frontal, head and shoulders down to mid-chest, face centred; change nothing else.`
- Улыбка шире нужной или кожа «пластиковая»: `Same image, but make the expression exactly as described, and keep natural skin texture with no smoothing.`

Типичные ошибки: «синдром одного лица» (разные люди похожи друг на друга), слишком гладкая кожа, при сильном старении лицо уходит к «другому человеку», чёрная оправа вместо прозрачной у Воронцова, лишний реквизит (наушники, значки, форма).

---

## Портреты: 14 готовых запросов

Для каждого: путь сохранения, формат, что приложить, запрос и чек-лист. Формат везде: **JPEG, вертикаль 4:5, не меньше 800 px по короткой стороне**, полный размер (кнопка скачивания, не скриншот). Если Gemini выдал не 4:5 - не страшно, обрежу я или вы.

### R01. Правка готового `portraits/voroncov.jpg`: заменить чёрную оправу на прозрачную

- **Сохранить как:** `detgame-media/portraits/voroncov.jpg` (старую версию - в `_attempts/voroncov_black_frame.jpg`).
- **Формат:** тот же, что у исходного файла (сейчас квадрат 800 x 800); обрезку и пропорции не менять.
- **Приложить:** 1 - `portraits/voroncov.jpg` (текущий). Больше ничего.

```text
Edit this photo. Change ONLY the glasses: replace the thick black frames with thin glasses that have a TRANSPARENT frame (the frame is clear, see-through plastic, almost invisible, with a thin outline), keep the lenses clear and without glare so both eyes stay fully visible and undistorted. Keep EVERYTHING else exactly identical: the face and its age, the thick dark eyebrows, the grey hair, the grey beard, the expression, the dark T-shirt, the thin neck chain, the pure white background, the lighting, the framing and the crop. Do not retouch the skin, do not change the aspect ratio. No text, no watermark, no logos, no shadows on the background.
```
Проверь перед сохранением:

- [ ] оправа тонкая и прозрачная, не чёрная и не коричневая (она читается как контур вокруг стёкол)
- [ ] глаза за стёклами на месте, без бликов, брови густые и тёмные
- [ ] всё остальное как было: борода, волосы, футболка, цепочка, белый фон
- [ ] нет артефактов правки (ореол вокруг очков, «поплывшее» лицо); если есть - правка: `Same image, but keep the face exactly as in the input photo; only the glasses frame is transparent.`

Если после 3 правок лицо ушло - запустите полный запрос P01 ниже (с образцами автора).

### P01. `portraits/voroncov.jpg` - Воронцов (автор)

- **Сохранить как:** `detgame-media/portraits/voroncov.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 56 (`content/characters.yaml`)
- **Приложить:** 1-2 фото автора (в очках, если есть), затем voroncov.jpg. Внимание: voroncov.jpg - и образец стиля, и сам результат; если нужна только правка очков - используйте запрос R01 ниже, а не этот. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 56 years old (mid-fifties: some grey at the temples and in the beard, moderate lines) - age them up or down from the reference as needed. Do NOT make the person look older than 56. Change only the apparent age, never the identity.

SUBJECT: a man.
EXPRESSION: Charismatic but slightly tired look, mouth closed with a barely visible half-smile (not a broad smile). Thick, dark, bushy eyebrows - keep them thick and dark.
CLOTHES AND DETAILS: Thin glasses with a TRANSPARENT frame (the frame itself is clear, see-through plastic - not black, not tortoiseshell, not metal), clear lenses without glare so the eyes stay fully visible. Dark charcoal crew-neck T-shirt (as in the existing portrait). Greying hair and beard as in the existing portrait and the reference photos.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] очки в тонкой ПРОЗРАЧНОЙ оправе (не чёрной), глаза за стёклами видны без бликов
- [ ] густые тёмные брови
- [ ] на вид около 56 лет, лицо узнаваемо как автор
- [ ] фон чисто белый, рамка и свет как у текущего voroncov.jpg

### P02. `portraits/zavyalov.jpg` - Завьялов, худрук (дедушка)

- **Сохранить как:** `detgame-media/portraits/zavyalov.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 61 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Завьялова-дедушки, затем voroncov.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 61 years old (early sixties, a bit YOUNGER than in the reference: fewer wrinkles) - age them up or down from the reference as needed. Do NOT make the person look older than 61. Change only the apparent age, never the identity.

SUBJECT: a man.
EXPRESSION: Authoritative, commanding, serious look; mouth closed, no smile.
CLOTHES AND DETAILS: Dark formal suit, white shirt, dark tie.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] взгляд в камеру поверх оправы, очки на кончике носа
- [ ] властное выражение, рот закрыт
- [ ] костюм, рубашка, галстук; на вид около 61 года
- [ ] лицо узнаваемо; фон белый

### P03. `portraits/volkov.jpg` - Волков, дублёр (Слава)

- **Сохранить как:** `detgame-media/portraits/volkov.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 31 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Славы, затем voroncov.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 31 years old (early thirties: fresh face, NO wrinkles, NO grey hair) - age them up or down from the reference as needed. Do NOT make the person look older than 31. Change only the apparent age, never the identity.

SUBJECT: a man.
EXPRESSION: Charming, friendly, gentle open smile (lips slightly parted at most), warm friendly eyes.
CLOTHES AND DETAILS: Casual knit crew-neck sweater in a muted dark blue-grey, plain, no pattern, no logo.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] обаятельная улыбка, не широкая
- [ ] свитер без логотипов и рисунка
- [ ] на вид около 31 года, лицо узнаваемо
- [ ] фон белый, взгляд в камеру

### P04. `portraits/marina.jpg` - Марина, крестница Воронцова и дочь Кирилла (Алина)

- **Сохранить как:** `detgame-media/portraits/marina.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 24 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Алины, затем voroncov.jpg. Решено автором 21.10: возраст в игре 24, согласие родителей получено. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 24 years old (mid-twenties: smooth youthful skin, NO wrinkles, NO grey hair) - age them up or down from the reference as needed. Do NOT make the person look older than 24. Change only the apparent age, never the identity.

SUBJECT: a young woman, an adult.
EXPRESSION: Closed, guarded expression: lips closed, NO smile at all, direct steady gaze into the camera.
CLOTHES AND DETAILS: Simple plain casual crew-neck top in a muted beige or grey, no print, no logo. Hair styled as in the reference photos.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] выглядит взрослой женщиной около 24 лет
- [ ] без улыбки, закрытый взгляд
- [ ] причёска как на образцах; лицо узнаваемо
- [ ] фон белый, никаких украшений

### P05. `portraits/kirill.jpg` - Кирилл, программист (дядя Саша)

- **Сохранить как:** `detgame-media/portraits/kirill.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 56 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Кирилла, затем voroncov.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 56 years old (mid-fifties: some grey, light lines at the eyes) - age them up or down from the reference as needed. Do NOT make the person look older than 56. Change only the apparent age, never the identity.

SUBJECT: a man.
EXPRESSION: Cheerful, laughing eyes with crow's feet and a hint of a smirk; lips closed or only barely smiling.
CLOTHES AND DETAILS: Checked flannel shirt (muted red and navy), open collar, no logo.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] весёлые глаза, лёгкая ухмылка, рот почти закрыт
- [ ] клетчатая рубашка без логотипов
- [ ] на вид около 56 лет, лицо узнаваемо
- [ ] фон белый, голова прямо

### P06. `portraits/stas.jpg` - Лёвин, актёр (Стас)

- **Сохранить как:** `detgame-media/portraits/stas.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 44 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Стаса, затем voroncov.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 44 years old (mid-forties: a few faint lines at the eyes, almost NO grey) - age them up or down from the reference as needed. Do NOT make the person look older than 44. Change only the apparent age, never the identity.

SUBJECT: a man.
EXPRESSION: Artistic, expressive face: one eyebrow very slightly raised, a thoughtful ironic look; mouth closed, at most a faint smile.
CLOTHES AND DETAILS: Dark turtleneck sweater, plain, black or deep charcoal.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] лёгкий подъём одной брови, артистичная мимика
- [ ] тёмная водолазка
- [ ] на вид около 44 лет, лицо узнаваемо
- [ ] голова не наклонена, фон белый

### P07. `portraits/reznikova.jpg` - Резникова, помреж (мама)

- **Сохранить как:** `detgame-media/portraits/reznikova.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 47 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Резниковой (мамы), затем voroncov.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 47 years old (late forties, well-kept: light lines at the eyes, no grey hair) - age them up or down from the reference as needed. Do NOT make the person look older than 47. Change only the apparent age, never the identity.

SUBJECT: a woman.
EXPRESSION: Composed, organised, attentive look; lips closed, no smile or a very faint one.
CLOTHES AND DETAILS: Hair tied back neatly. Simple dark blouse or cardigan.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] волосы собраны, собранное внимательное выражение
- [ ] на вид около 47 лет, лицо узнаваемо
- [ ] фон белый, взгляд в камеру

### P08. `portraits/gnedich.jpg` - Гнедич, костюмер (бабушка)

- **Сохранить как:** `detgame-media/portraits/gnedich.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 63 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Гнедич (бабушки), затем voroncov.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 63 years old (early sixties, a bit YOUNGER than in the reference) - age them up or down from the reference as needed. Do NOT make the person look older than 63. Change only the apparent age, never the identity.

SUBJECT: a woman.
EXPRESSION: Strict, no-nonsense expression; lips closed, no smile.
CLOTHES AND DETAILS: Dark blouse with a plain cardigan.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] строгое выражение
- [ ] на вид около 63 лет, лицо узнаваемо

### P09. `portraits/viktor.jpg` - Виктор «Мастер», свет (двоюродный брат)

- **Сохранить как:** `detgame-media/portraits/viktor.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 50 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Виктора, затем voroncov.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 50 years old (about fifty: a little grey at the temples, light lines — moderate, not old) - age them up or down from the reference as needed. Do NOT make the person look older than 50. Change only the apparent age, never the identity.

SUBJECT: a man.
EXPRESSION: Taciturn, calm, reserved look; mouth closed, no smile.
CLOTHES AND DETAILS: Plain black crew-neck T-shirt, no print, no logo. Short hair, hairstyle and facial hair as in the reference photos.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] немногословное спокойное выражение
- [ ] чёрная футболка без принтов
- [ ] на вид около 50 лет, лицо узнаваемо (не двойник автора!)
- [ ] фон белый, голова прямо

### P10. `portraits/oleg.jpg` - Охранник Олег

- **Сохранить как:** `detgame-media/portraits/oleg.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 64 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Олега, затем voroncov.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 64 years old (early-to-mid sixties) - age them up or down from the reference as needed. Do NOT make the person look older than 64. Change only the apparent age, never the identity.

SUBJECT: a man.
EXPRESSION: Good-natured, kind, gentle face with a very small closed-mouth smile.
CLOTHES AND DETAILS: Plain dark navy jacket with a collar over a light shirt, no patches, no badges, no logos.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] добродушное выражение
- [ ] на вид около 64 лет, лицо узнаваемо
- [ ] фон белый, взгляд в камеру

### P11. `portraits/inna.jpg` - Инна, буфетчица (мама мужа сестры)

- **Сохранить как:** `detgame-media/portraits/inna.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 29 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Инны, затем voroncov.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 29 years old (late twenties: smooth skin, NO wrinkles, NO grey hair) - age them up or down from the reference as needed. Do NOT make the person look older than 29. Change only the apparent age, never the identity.

SUBJECT: a woman.
EXPRESSION: Lively, slightly fussy look: eyebrows slightly raised, attentive eyes, a small closed-mouth smile. Bright red lipstick - clearly visible and neat.
CLOTHES AND DETAILS: Light cream blouse. Hair as in the reference photos.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] яркая красная помада
- [ ] на вид около 29 лет, лицо узнаваемо
- [ ] фон белый, улыбка не широкая

### P12. `portraits/dmitriy.jpg` - Водитель Дарья (роль «Дмитрий»)

- **Сохранить как:** `detgame-media/portraits/dmitriy.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 40 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Дарьи (жены брата тёти), затем voroncov.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 40 years old (around forty: very few faint lines, no grey hair) - age them up or down from the reference as needed. Do NOT make the person look older than 40. Change only the apparent age, never the identity.

SUBJECT: a woman (the character is a female driver).
EXPRESSION: Plain, reliable, calm look; lips closed, no smile or a very faint one.
CLOTHES AND DETAILS: Practical dark zip-up jacket over a plain T-shirt, no logos. Hair as in the reference photos.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] это женщина
- [ ] простая куртка без логотипов
- [ ] на вид около 40 лет, лицо узнаваемо
- [ ] фон белый, взгляд в камеру

### P13. `portraits/volskaya.jpg` - Вольская, меценат (тётя Света)

- **Сохранить как:** `detgame-media/portraits/volskaya.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 54 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Вольской (тёти Светы), затем voroncov.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 54 years old (mid-fifties, well-groomed: light lines, hair may be coloured) - age them up or down from the reference as needed. Do NOT make the person look older than 54. Change only the apparent age, never the identity.

SUBJECT: a woman.
EXPRESSION: Society-lady look: poised, elegant, self-assured; lips closed with a faint polite smile.
CLOTHES AND DETAILS: A single-strand pearl necklace, neat styled hair, a tasteful ivory blouse under a dark tailored jacket.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] жемчужное ожерелье, аккуратная причёска
- [ ] светская, собранная, улыбка еле заметна
- [ ] на вид около 54 лет, лицо узнаваемо
- [ ] фон белый, взгляд в камеру

### P14. `portraits/gromov.jpg` - Громова, чиновник (сестра Юля)

- **Сохранить как:** `detgame-media/portraits/gromov.jpg`
- **Формат:** JPEG, 4:5 вертикаль, белый фон; возраст в игре - 57 (`content/characters.yaml`)
- **Приложить:** 1-2 фото Громовой (сестры), затем voroncov.jpg. Портрет потом используется как образец в gromov/meeting.jpg. Порядок: сначала фото человека, **последним - `portraits/voroncov.jpg` (образец стиля)**.

```text
Create a photorealistic ID-style portrait photograph of a real person.

ATTACHED IMAGES: The LAST attached image is a STYLE reference only. Match its pure white seamless background, its framing (frontal view, head and shoulders, cropped at mid-chest, head centred with a small margin of white space above the hair), its soft even daylight-like lighting and its natural, neutral colours of a document photo. Do NOT copy the person from that image: not the face, hair, beard, glasses, clothes or neck chain, and do NOT take the AGE, grey hair or wrinkles from it. All the OTHER attached images are photos of the real person: use them as the strict identity reference.

IDENTITY: Keep the exact identity of the person in the reference photos: same face shape, eyes, eyebrows, nose, mouth, ears, jawline, skin tone and hairline, and the same hairstyle and facial hair as in the reference photos (apart from natural changes caused by age). The result must be instantly recognisable as this same real person, not a lookalike and not a generic face.

AGE: Make the person look exactly 57 years old (mid-to-late fifties, well-groomed: light lines, neat coloured hair) - age them up or down from the reference as needed. Do NOT make the person look older than 57. Change only the apparent age, never the identity.

SUBJECT: a woman (the character is a female official).
EXPRESSION: Official, composed, slightly stern look; lips closed, no smile.
CLOTHES AND DETAILS: Formal grey blazer over a white blouse. Hair as in the reference photos.

COMPOSITION: Strictly frontal, facing straight into the camera, eyes looking directly into the lens, head upright and level (not tilted, not turned), shoulders square to the camera, head and shoulders down to mid-chest, face centred. Both hands out of frame. Vertical 4:5 format.
LIGHT AND BACKGROUND: Soft, even, diffuse frontal daylight, no harsh shadows. Background is a plain pure white seamless backdrop (#FFFFFF), perfectly uniform, with no shadow, no gradient and no vignette.
REALISM: Photorealistic, natural age-appropriate skin texture (no extra wrinkles), natural colours, sharp focus on the eyes. Plain document-photo look.

AVOID: no props or accessories of any profession (no headphones, headsets, measuring tapes, aprons, badges, pins, uniforms), no text, no watermark, no logos, no props in hands, no tilted head, no smile wider than described, no glamour retouching or skin smoothing, no beauty filter, no grey or coloured background, no shadows on the background, no hat, no sunglasses, no necklaces, pendants, crosses or other symbolic jewellery (unless described above), no illustration or cartoon look.
```

Проверь перед сохранением:

- [ ] это женщина; на вид около 57 лет (старше образца), лицо узнаваемо
- [ ] официальное сдержанное выражение
- [ ] фон белый, голова прямо

---

## Сцены и улики

Хвост запроса (запрет текста, логотипов и т. п.) уже вписан в каждый запрос. Таблички, таймкоды, этикетки, номерки и линейку генератор **не рисует** - я накладываю их сам, поэтому в кадре оставлены пустые места. Нижний правый угол кадра я могу обрезать (возможный знак Gemini): важного там нет.

### S01. `news/voroncov_arbenin.jpg` - новость 1-13 и программка 1-07

- **Сохранить как:** `detgame-media/news/voroncov_arbenin.jpg`
- **Формат:** JPEG, горизонталь 3:2, целиться в ≤ 300 КБ после моего сжатия
- **Приложить:** 1 - `portraits/voroncov.jpg` (правленый, прозрачные очки); 2 - одно сырое фото автора (необязательно).

```text
Use image 1 (and image 2 if attached) as the strict identity reference. Create a photorealistic theatre press photograph of this same man, who looks about 56 years old, playing Arbenin in Lermontov's play "Masquerade" on the stage of a provincial theatre. Keep exactly his face, his thick dark eyebrows, his grey hair and his beard as in image 1. He wears a black 19th-century tailcoat, a white shirt with a high stiff collar and a dark cravat. NO glasses (he takes them off for the stage). Serious dramatic expression, half-length shot, body slightly turned, face toward the camera. Warm side stage spotlight, dark background with a hint of heavy theatre curtain, shallow depth of field. No posters, no signs, no other actors, no props with writing. Horizontal 3:2. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением:

- [ ] лицо и борода узнаваемы как на портрете, густые тёмные брови
- [ ] фрак XIX века, белая сорочка, шейный платок; очков нет
- [ ] сцена и сценический свет, нет афиш и надписей
- [ ] нет других людей и логотипов

### S02. `gromov/meeting.jpg` - пост 1-12, УЛИКА

Улика: старое фото с совещания, **за окном густая летняя зелень** (совещание 10.11 прошло в ноябре, пресс-служба выложила старый снимок - так в `pages/gromov`, 3-10).

- **Сохранить как:** `detgame-media/gromov/meeting.jpg`
- **Формат:** JPEG, горизонталь 4:3 (рамка поста 4:3), ≤ 1 МБ
- **Приложить:** 1 - `portraits/gromov.jpg` (утверждённый, ей 57); 2 - одно сырое фото Громовой (необязательно).

```text
Use image 1 (and image 2 if attached) as the strict identity reference. Create an official press-service style photograph of this same woman, who looks about 57 years old, sitting at a long conference table in a municipal administration meeting room. She wears a formal grey blazer over a white blouse, her hands rest on papers. On the table in front of her: a neat stack of papers, a laptop, two glass bottles of water with glasses, and a blank white landscape A4 name sign in a clear plastic holder standing square-on facing the camera - leave the sign COMPLETELY BLANK, no letters at all (the text is added later). Two or three other participants sit further down the table, out of focus, faces not distinguishable. Behind her, a large window: outside are LUSH GREEN TREES IN FULL SUMMER FOLIAGE in bright summer daylight, no autumn colours, no bare branches, no snow. Plain neutral office walls, no flag, no emblem, no portraits on the wall. Straight-on, slightly flat press-office photography, even light, aspect ratio 4:3. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением:

- [ ] **за окном густая зелёная летняя листва** (не жёлтая, не голые ветки, не снег)
- [ ] табличка на столе есть, но **пустая** (текст «Рабочее совещание по развитию культурной инфраструктуры» накладываю я)
- [ ] нет флагов, гербов, портретов на стене; лицо узнаваемо, женщина около 57 лет
- [ ] на столе бумаги и вода; остальные участники без различимых лиц

### S03. `gromov/cover.jpg` - обложка профиля 1-12

- **Сохранить как:** `detgame-media/gromov/cover.jpg`
- **Формат:** JPEG, очень широкая панорама (цель около 8:3; если Gemini выдал 16:9 или 3:2 - обрежу я), ≤ 1 МБ
- **Приложить:** ничего (людей нет).

```text
Wide panoramic photograph of the main building of a city administration in a provincial Russian-like town: a five-storey light-coloured building with a columned central entrance, a small square in front with trees and a lawn, a few distant pedestrians as tiny figures, overcast daylight. NO flags, NO coat of arms, NO signboards, NO nameplates, no readable text, no vehicles with readable number plates. Very wide horizontal aspect ratio, about 8:3. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением:

- [ ] на здании и перед ним нет флагов, гербов, вывесок и надписей
- [ ] здание администрации провинциального города, колонны, площадь с деревьями
- [ ] кадр очень широкий (можно обрезать до 8:3 без потери здания)
- [ ] нет читаемых номеров машин

### S04. `work/brooch_ref.jpg` - рабочий эталон броши (в игру не идёт)

Брошь должна совпасть с описью 2-08, поз. 7: «овальная, металл под старое серебро, в центре - крупный зелёный камень (стекло), по краю - **два ряда** мелких прозрачных страз, внизу - подвеска-капля; 6 x 4,5 см».

- **Сохранить как:** `detgame-media/work/brooch_ref.jpg`
- **Формат:** JPEG, квадрат 1:1, полный размер
- **Приложить:** ничего (людей нет).

```text
Macro product photograph of a handmade theatrical costume brooch lying on dark red velvet, front view, sharp focus on the whole brooch, even soft light, no harsh reflections. The brooch is oval, about 6 x 4.5 cm. Its frame is metal that looks like antique tarnished silver. ONE large green faceted stone (green glass) sits in the centre of the oval. Along the edge of the oval run exactly TWO concentric rows of tiny clear rhinestones (an inner row and an outer row). Below the oval, ONE single teardrop-shaped pendant hangs from the bottom. Showy, vintage look. Nothing else in the frame. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением (на 100% увеличении, считайте):

- [ ] форма - овал, металл «под старое серебро»
- [ ] **один** крупный зелёный камень строго по центру
- [ ] по краю ровно **два** ряда мелких прозрачных страз (пересчитайте ряды)
- [ ] **одна** подвеска-капля внизу, других подвесок нет
- [ ] правка при ошибке: `Same image, but exactly two rows of small clear stones around the edge, one large green stone in the centre, one teardrop pendant at the bottom.`

### S05. `inna/brooch.jpg` - фотосеть 2-09, УЛИКА

- **Сохранить как:** `detgame-media/inna/brooch.jpg`
- **Формат:** JPEG, квадрат 1:1 (плитки сетки квадратные), ≤ 1 МБ
- **Приложить:** 1 - `portraits/inna.jpg` (утверждённый портрет); 2 - `work/brooch_ref.jpg` (эталон из S04). Третий слот свободен: если лицо не похоже - добавьте сырое фото Инны **перед** эталоном (тогда эталон окажется «LAST», так и сказано в запросе).

```text
Use the FIRST attached image(s) as the strict identity reference for the woman (about 29 years old, bright red lipstick). Use the LAST attached image as the exact reference for the brooch. Create a photorealistic mirror selfie in a cosy home hallway in the evening, warm indoor light: the woman holds a smartphone with a plain case (no logo, no brand mark) in front of her chest and takes the photo in the mirror, her face is mostly visible and recognisable. She wears a plain light cream blouse, and the brooch is pinned prominently at the collar / upper chest: LARGE, SHARP and clearly visible, identical to the brooch reference - oval shape, antique-silver look, ONE large green stone in the centre, exactly TWO rows of small clear rhinestones along the edge, ONE teardrop pendant at the bottom. No other brooches or jewellery. Proud, happy, pleased pose. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением (брошь - на 100% увеличении):

- [ ] брошь крупная и резкая, те же 5 признаков, что у эталона: овал, один зелёный камень, два ряда страз, одна капля, металл «под старое серебро»
- [ ] второй броши и другой бижутерии нет
- [ ] на телефоне нет логотипа; лицо узнаваемо как Инна, около 29 лет
- [ ] если Gemini «упрощает» брошь - пришлите мне лучший кадр: я вклею эталон (Pillow)

### S06. `lab/station_cam.jpg` - экспертиза 4-08, УЛИКА

По `content/documents/4-08.md`: камера под потолком кассового зала смотрит сверху вниз на окна касс № 1, 2, 3 и пространство перед ними; ч/б; напротив окна кассы № 2 стоит колонна зала, до неё около 6 м; мужчина № 1 - высокий, в длинном тёмном пальто, без головного убора, в очках, стоит у окна кассы № 2 и передаёт кассиру деньги; второй (Волков, мужчина) - в короткой тёмной куртке, без головного убора, стоит **у колонны напротив окна кассы № 2, лицом к окнам касс**, голова повёрнута в сторону окна № 2. (В `MEDIA-PLAN-A` §4.5 колонна стояла «справа от Воронцова» - это неточно; по 4-08 колонна напротив окна, в 5-7 м.) Камера: сверху, время «30.10.2026 14:37:22 КАССА-2» - **днём**, таймкод накладываю я, угол справа сверху оставлен пустым.

- **Сохранить как:** `detgame-media/lab/station_cam.jpg`
- **Формат:** JPEG, 3:2 (допустимо 16:9), чёрно-белый, ≤ 1 МБ
- **Приложить:** 1 - `portraits/voroncov.jpg` (правленый); 2 - `portraits/volkov.jpg`.

```text
Use image 1 as the identity reference for the first man (about 56 years old, grey hair, grey beard, thin transparent-frame glasses) and image 2 as the identity reference for the second man (about 31 years old). Create a still frame from a ceiling-mounted CCTV camera that looks steeply down (about 40-50 degrees) from a high point onto the ticket windows and the floor space in front of them, inside the ticket hall of a provincial railway station, in the daytime. Pure black-and-white, grainy low-resolution surveillance image, slight wide-angle barrel distortion, slight motion blur, flat lighting. Along one wall there are three ticket windows with big plain digits 1, 2, 3 above them, left to right. The first man - tall, wearing a long dark overcoat and glasses, NO hat - stands at the middle window, number 2, leaning toward it and handing banknotes to the cashier behind the glass. About 6 metres away from window 2, out in the hall FACING the windows, stands a thick square concrete hall column. The second man stands next to that column: short dark jacket, NO hat, hands in his pockets, facing the ticket windows, his head turned toward the first man at window 2 and looking at him. The two men are clearly separated by open floor, about 6 metres apart. One or two other passengers at windows 1 and 3 and far in the background, small, not looking at anyone. Tiled floor, a few benches, no brand names, no text except the three digits. Faces visible at least in profile. 3:2. Photorealistic CCTV frame, not an illustration. No captions, no timestamps, no camera name, no watermarks, no logos, no brand names, no readable signs. The ONLY text allowed is the three big digits 1, 2, 3 above the ticket windows. The picture fills the whole frame edge to edge as ONE seamless image: no black boxes, no blank or cut-out areas, no panorama stitching. In the top-right and bottom-right parts of the picture show only plain dark wall or asphalt, with no important objects. Highest available resolution.
```

Проверь перед сохранением:

- [ ] цифры 1, 2, 3 над окнами видны, мужчина № 1 - у окна **№ 2**: длинное тёмное пальто, очки, без шапки
- [ ] колонна напротив окна № 2; мужчина № 2 у колонны в 5-7 м (не рядом с первым!), в короткой тёмной куртке, без шапки, смотрит на первого
- [ ] ч/б, вид сверху, зерно, день; на кадре нет никаких надписей, кроме трёх цифр (таймкод и «КАССА-2» накладываю я)
- [ ] правый верхний угол пуст; лица различимы хотя бы в профиль

### S07. `lab/pillbox.jpg` - экспертиза 3-06, УЛИКА (самая хрупкая)

По `content/documents/3-06.md`: чёрная пластиковая недельная таблетница, 18 x 3 x 2 см, **7 отделений в один ряд**, откидные крышки с выпуклыми буквами «ПН», «ВТ», «СР», «ЧТ», «ПТ», «СБ», «ВС»; на фото крышки открыты (снимок до отбора проб). Содержимое: ПН и ВТ - **пусто**; СР, ПТ, СБ, ВС - по 1 белой круглой двояковыпуклой таблетке в оболочке с гравировкой «S» (диаметр 8 мм, риски нет); ЧТ - 1 белая круглая **плоская** таблетка с фаской и риской, **9 мм (чуть крупнее)**, без гравировки. (Строка шот-листа в `SCENARIO.md` про «СБ с S, ВС с риской» устарела - прав `3-06`.)

- **Сохранить как:** `detgame-media/lab/pillbox.jpg`
- **Формат:** JPEG, 3:2, вид строго сверху, ≤ 1 МБ
- **Приложить:** ничего (людей нет).

```text
Top-down macro photograph, camera directly above, of a black plastic weekly pill organiser with exactly 7 separate rectangular compartments in ONE straight row. It is long and slim (about 18 x 3 cm). Every lid is open, folded back flat above its compartment, and on the outside of each lid there are raised (embossed) Russian two-letter day abbreviations, upright and readable from the viewer's side, from left to right: ПН, ВТ, СР, ЧТ, ПТ, СБ, ВС. Contents: compartments ПН and ВТ are completely EMPTY. Compartments СР, ПТ, СБ and ВС each contain exactly ONE white round tablet: slightly domed and coated, about 8 mm, with a single capital letter S engraved in the centre and no score line. Compartment ЧТ contains exactly ONE white round tablet that is FLAT with a bevelled edge, slightly LARGER (about 9 mm), with a straight score line across its middle and NO letter. One tablet per compartment, no loose tablets elsewhere. The organiser fills most of the frame and lies on a plain light wooden table, soft window daylight from the left, slightly worn plastic, sharp focus across the whole organiser. No other objects. Horizontal 3:2. Photorealistic photograph with a natural, slightly imperfect look; not an illustration, not 3D. No watermarks, no logos, no brand names, no captions. The ONLY text allowed is the seven embossed day abbreviations on the lids. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Запасной вариант (если Gemini упорно ломает кириллицу на крышках; подписи дней я тогда нарисую сам) - отправьте вместо основного запроса:

```text
Top-down macro photograph, camera directly above, of a black plastic weekly pill organiser with exactly 7 separate rectangular compartments in ONE straight row, long and slim (about 18 x 3 cm). Every lid is open and folded back flat above its compartment, with a blank raised rectangular patch on each lid where a label would be (leave the patches blank, no letters). Contents from left to right: compartments 1 and 2 are completely EMPTY; compartments 3, 5, 6 and 7 each contain exactly ONE white round tablet, slightly domed and coated, about 8 mm, with a single capital letter S engraved in the centre and no score line; compartment 4 contains exactly ONE white round tablet that is FLAT with a bevelled edge, slightly larger (about 9 mm), with a straight score line across the middle and no letter. The organiser fills most of the frame on a plain light wooden table, soft window daylight from the left, slightly worn plastic, sharp focus. No other objects. Horizontal 3:2. Photorealistic, natural look, no watermarks, no logos, no text anywhere. Highest available resolution.
```

Проверь перед сохранением (на 100% увеличении, по одному отделению):

- [ ] ровно **7** отделений в один ряд, чёрный пластик, крышки открыты
- [ ] ПН - пусто, ВТ - пусто
- [ ] СР, ПТ, СБ, ВС - по одной белой круглой таблетке с «S», без риски
- [ ] ЧТ - одна белая круглая **плоская** таблетка с риской, чуть крупнее, без «S»
- [ ] правка при ошибке: `Same image, but Wednesday, Friday, Saturday and Sunday each have one S tablet, Thursday has one larger flat tablet with a score line and no S, Monday and Tuesday are empty.` Подписи дней и «S» при необходимости перерисую я.

---

## Бумажные фото

Идут в бумажные документы конвертов (`content/paper/*.md`), печать, ≤ 1 МБ каждый. Номерки-указатели, линейка, таймкоды, этикетки - накладываю я, поэтому в запросах написано «no numbers, no markers».

### Гримёрка № 4: три кадра (S08-S10), один чат

Источник - `content/paper/1-09.md` (опись, расположение) и `content/paper/1-10.md` (подписи): комната около 3 x 4 м, **окон нет**, свет - верхний и лампы вокруг зеркала. Справа от входа - вешалка-стойка и диван; прямо - гримировальный столик с зеркалом в лампах, перед ним кресло; слева от столика - стул; у стены - раковина; розетка на стене слева от столика. **Телефона в комнате нет нигде** (улика).

### S08. `paper/1-10-general.jpg` - кадр 1, общий вид от входной двери

- **Сохранить как:** `detgame-media/paper/1-10-general.jpg`
- **Формат:** JPEG, горизонталь 4:3
- **Приложить:** ничего. Этот кадр потом прикладывается как образец комнаты к S09 и S10.

```text
Photorealistic forensic documentation photograph, shot with a compact camera from the entrance doorway of a small WINDOWLESS theatre dressing room, about 3 by 4 metres, lit by a ceiling light plus bulbs around the mirror (all on), a mild on-camera-flash feel, neutral colours, slightly lived-in, nobody in the room. Straight ahead: a make-up table with a large mirror framed by round bulbs, a leather armchair in front of it with a dark-blue men's jacket over its back. To the left of the table: a wooden chair with an open brown leather men's bag on it. A washbasin against the wall at the left. To the right of the entrance: a clothes rack with a black wool coat, a grey scarf and a stage costume (tailcoat, waistcoat, shirt), black shoes on the floor under it, and next to it a sofa with a plaid wool blanket and an opened box of chocolates. A plastic bucket with a bouquet of red roses stands on the floor near the mirror. A wall socket on the wall to the left of the table. No windows anywhere. Horizontal 4:3. No numbers, no ruler, no markers (they are added later). Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением:

- [ ] окон нет
- [ ] видны: кресло с тёмно-синим пиджаком (6), стул с коричневой сумкой (17), вешалка с костюмом (4), диван (19)
- [ ] зеркало в лампах, раковина, букет красных роз в ведре
- [ ] людей, номерков, линейки и надписей нет

### S09. `paper/1-10-table.jpg` - кадр 2, гримировальный столик (таблетница на втором плане)

- **Сохранить как:** `detgame-media/paper/1-10-table.jpg`
- **Формат:** JPEG, горизонталь 4:3
- **Приложить:** 1 - готовый `paper/1-10-general.jpg` (образец комнаты). Запрос отправлять **в том же чате**.

```text
Same dressing room as in the attached reference image (same mirror, bulbs, table, walls, chair). New view: a closer, slightly angled shot of the make-up table. On the table: a men's wristwatch with a leather strap, an open metal make-up case with brushes and sponges, a comb, a plastic half-litre water bottle that is already opened and about one third full, a thick typewritten script with pencil notes (no readable text), white wireless earbuds in a white charging case, a half-used pack of paper napkins, and near the mirror a small wooden-framed photo of a man and two girls on an embankment (tiny, faces not distinguishable). A phone charger is plugged into the wall socket to the left of the table; its cable dangles loose over the table edge and is connected to NOTHING; there is NO phone anywhere in the frame. In the SECOND PLANE on the left, slightly out of focus but recognisable: the open brown leather men's bag on the chair, with a black plastic weekly pill organiser sticking out of it, and the corner of a book. Horizontal 4:3. No numbers, no ruler, no markers. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением:

- [ ] **зарядка в розетке, кабель свисает ни к чему не подключённый, телефона нет нигде**
- [ ] часы (8), кейс с гримом (9), бутылка на треть полная (11), машинописный текст (12), наушники в белом футляре (14)
- [ ] сумка (17) на втором плане не в фокусе, из неё торчит чёрная таблетница
- [ ] комната та же, что в кадре 1; номерков и надписей нет

### S10. `paper/1-10-rack.jpg` - кадр 3, вешалка-стойка (справа от входа, у дивана)

- **Сохранить как:** `detgame-media/paper/1-10-rack.jpg`
- **Формат:** JPEG, горизонталь 4:3
- **Приложить:** 1 - готовый `paper/1-10-general.jpg` (общий план). Лучше **новый чат** — в старом генератор тянется повторить общий план.
- Почему старый запрос не работал: «by the door» — на общем плане вешалка не у двери, а у **правой стены**, между ведром с розами и диваном (так и в протоколе 1-09: «справа от входа — вешалка-стойка и диван»).

```text
The attached photo is the general view of a theatre dressing room. Create a NEW photograph of the SAME room, taken by a police forensic photographer as a close-up of ONE object: the chrome clothes rack that stands against the RIGHT-hand wall in the attached photo (between the red roses in the white bucket and the beige sofa).

CAMERA: The photographer stands in the middle of the room and points the camera straight at the right-hand wall, so we see the clothes rack from the front, square-on, at chest height, with a slight downward tilt so the floor under the rack is visible. The rack fills about 80% of the frame.

THE RACK (copy it exactly from the attached photo): a simple chrome clothes rail on two legs with small wheels. Hanging on it, from left to right, on wooden hangers:
1) a long black wool men's overcoat;
2) a long grey knitted wool scarf with fringe, hanging over the rail;
3) a 19th-century stage costume: a black tailcoat with long tails, a dark grey waistcoat and a white shirt with a wing collar, on one hanger.
On the floor directly under the rack: ONE pair of black leather men's casual shoes, side by side.

SURROUNDINGS (same as in the attached photo, only at the edges of the frame): the same plain cream-coloured wall, the same beige speckled carpet, the same cold overhead ceiling light; at the left edge a few red roses in the white plastic bucket; at the right edge the arm of the beige sofa with the checked plaid. Nothing else.

LOOK: the same colours, light and photo quality as the attached photo — a plain, documentary, slightly flat forensic photo, sharp, with natural texture of the wool. Photorealistic photograph, not an illustration, not 3D.

AVOID: no people, no mirror in this shot, no extra clothes on the rack, no more than one pair of shoes, no numbers, no markers, no ruler, no text, no labels, no captions, no timestamps, no watermarks, no logos, no brand names. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Horizontal 4:3, highest available resolution.
```

Если вешалка получается не той или комната другая — правка в том же чате:
`Same image, but make the rack, the clothes and the room look exactly like in the attached general photo. Keep the close-up framing.`

Если 3 попытки не вышли — пришлите как есть: вырежу вешалку из общего плана сам (качество будет ниже, но для печати в фототаблице хватит).

Проверь перед сохранением:

- [ ] пальто (1), шарф (2), костюм — фрак, жилет, белая сорочка (4), **одна** пара туфель под вешалкой (5)
- [ ] вешалка та же хромированная, что на общем плане; стена, ковёр и свет те же
- [ ] людей, зеркала и надписей нет

### Камера у служебного входа 2-03: шесть кадров (S11-S16), один чат

Источник - `content/paper/2-03.md`: камера **над служебной дверью театра, направлена вниз**: в кадре крыльцо, дверь и часть двора; внутрь здания не видно. 10.11.2026, 19:30-20:00 - **ночь**, ч/б. Охранник Олег (мужчина, форменная куртка) выходит курить, подходит к машине, разговаривает с водителем Дарьей через опущенное стекло, прикуривает вторую, входит; машина и водитель в салоне всё время на месте. Номер машины не нужен. Кадры 7 и 8 (пустое крыльцо) генерировать **не нужно**: сделаю из `2-03-01.jpg`. Таймкоды 19:30:06 ... 20:00:00 накладываю я: **правый верхний угол и правый нижний угол оставляйте пустыми**.

Работайте строго по порядку 01 -> 06 в одном чате; каждый следующий запрос - правка предыдущей картинки. Если нужно переделать кадр - прикрепите заново `2-03-01.jpg` и напишите тот же запрос. Сохраняйте файлы с именами из заголовков.

### S11. `paper/2-03-01.jpg` - дверь закрыта, машина, человек в салоне (основа для кадров 7 и 8)

- **Сохранить как:** `detgame-media/paper/2-03-01.jpg`
- **Формат:** JPEG, 16:9, ч/б, вид сверху, зерно
- **Приложить:** ничего.

```text
Still frame from a fixed outdoor CCTV camera mounted high above the service entrance door of a theatre and pointing steeply down: we see the porch with three concrete steps, a closed grey metal service door with a small lamp above it, and part of the asphalt yard. Night, a November evening, the lamp over the door is lit; black-and-white, grainy, low-resolution infrared-like surveillance look, wide-angle barrel distortion, vignetting. Parked right by the porch: a dark passenger sedan (generic shape, no badges, number plate blank and unreadable), seen from above and a little from the side; a WOMAN of about 40 sits in the driver's seat behind the windshield (left-hand-drive car), her face in shadow and NOT recognisable in this frame. The car has NO brand emblem on the grille and a completely blank licence plate with no characters. Nobody else in the frame. Horizontal 16:9. Photorealistic CCTV frame, not an illustration. No captions, no timestamps, no watermarks, no logos, no brand names, no readable signs, no readable number plate. The picture fills the whole frame edge to edge as ONE seamless image: no black boxes, no blank or cut-out areas, no panorama stitching. In the top-right and bottom-right parts of the picture show only plain dark wall or asphalt, with no important objects. Highest available resolution.
```

Проверь перед сохранением:

- [ ] дверь закрыта, крыльцо со ступенями, фонарь над дверью, ночь, ч/б, вид сверху
- [ ] тёмная машина у крыльца, за рулём **женщина** (роль «Дмитрий» — водитель Ксения), лицо в тени — различимо оно только в кадре 4 (S14), больше никого
- [ ] кадр цельный, без чёрных прямоугольников и склеек
- [ ] номер машины пустой или нечитаем; логотипов нет
- [ ] углы справа пусты (под таймкод)

### S12. `paper/2-03-02.jpg` - охранник выходит с сигаретой

- **Сохранить как:** `detgame-media/paper/2-03-02.jpg`
- **Формат:** JPEG, 16:9, ч/б, зерно
- **Приложить:** портрет Олега: 1 - `portraits/oleg.jpg`. Запрос - правка предыдущей картинки в том же чате.

```text
Edit the previous image. Keep the camera angle, porch, door, yard, lamp, black-and-white CCTV look and the car with its driver IDENTICAL. Now the service door is open a little and a man aged about 64 in a dark security-guard-style uniform jacket (no logos, no patches) steps out onto the porch with a cigarette in his hand. His face and build match the attached photo (image 1). Nobody else appears. Horizontal 16:9, black-and-white, grainy. No text, no timestamps, no logos.
```

Проверь перед сохранением:

- [ ] машина, водитель, крыльцо, ракурс те же, что в кадре 1
- [ ] лицо Олега в зерне допустимо неузнаваемо, но возраст около 64 лет, телосложение похоже

### S13. `paper/2-03-03.jpg` - курит на крыльце спиной к двери, лицом во двор

- **Сохранить как:** `detgame-media/paper/2-03-03.jpg`
- **Формат:** JPEG, 16:9, ч/б, зерно
- **Приложить:** ничего (Олег уже в чате). Запрос - правка предыдущей картинки в том же чате.

```text
Edit the previous image. Same scene, same camera, porch, door, yard and car. The door is now closed. The man in the dark uniform jacket stands on the porch with his BACK to the door and his face toward the yard, smoking, the cigarette in his hand or at his mouth. The car and the driver inside it are unchanged. Black-and-white grainy CCTV look. No text, no timestamps, no logos.
```

Проверь перед сохранением:

- [ ] дверь закрыта, мужчина стоит спиной к двери, лицом во двор, курит
- [ ] машина на том же месте, водитель в салоне
- [ ] ракурс и ночное ч/б те же

### S14. `paper/2-03-04.jpg` - у машины, разговор с водителем через опущенное стекло, лицо водителя различимо

- **Сохранить как:** `detgame-media/paper/2-03-04.jpg`
- **Формат:** JPEG, 16:9, ч/б, зерно
- **Приложить:** 1 - `portraits/dmitriy.jpg` (лицо Дарьи); при необходимости 2 - `portraits/oleg.jpg`. Запрос - правка предыдущей картинки в том же чате.

```text
Edit the previous image. Same scene, same camera, porch, door, yard and the same car in the same place. The man in the dark uniform jacket now stands next to the car, bending slightly toward the driver's window, which is lowered; the cigarette is in his hand. The woman driver, about 40 years old, leans toward the open window; her face is CLEARLY VISIBLE and matches the attached photo (image 1). Black-and-white grainy CCTV look, the car and the yard are unchanged. No text, no timestamps, no logos, no readable number plate.
```

Проверь перед сохранением:

- [ ] **лицо водителя-женщины различимо** (так сказано в подписи 4 документа 2-03) и похоже на Дарью
- [ ] окно опущено, мужчина с сигаретой склонился к нему
- [ ] машина, крыльцо, дверь на тех же местах

### S15. `paper/2-03-05.jpg` - снова у двери, прикуривает вторую сигарету

- **Сохранить как:** `detgame-media/paper/2-03-05.jpg`
- **Формат:** JPEG, 16:9, ч/б, зерно
- **Приложить:** ничего. Запрос - правка предыдущей картинки в том же чате.

```text
Edit the previous image. Same scene, same camera and the same car in the same place with the driver inside. The man in the dark uniform jacket is back at the closed service door, lighting a second cigarette with a lighter (a small flame in his cupped hands). Black-and-white grainy CCTV look. No text, no timestamps, no logos.
```

Проверь перед сохранением:

- [ ] мужчина у закрытой двери, огонёк зажигалки у лица
- [ ] машина на месте, водитель в салоне
- [ ] второй сигареты нет в руке «слитой» с пальцами - рука читается

### S16. `paper/2-03-06.jpg` - открывает дверь и заходит в здание

- **Сохранить как:** `detgame-media/paper/2-03-06.jpg`
- **Формат:** JPEG, 16:9, ч/б, зерно
- **Приложить:** ничего. Запрос - правка предыдущей картинки в том же чате.

```text
Edit the previous image. Same scene, same camera and the same car in the same place with the driver inside. The man opens the service door and steps inside: the door is half-open and light from inside falls on the porch. Black-and-white grainy CCTV look. No text, no timestamps, no logos.
```

Проверь перед сохранением:

- [ ] дверь полуоткрыта, мужчина входит, из двери падает свет на крыльцо
- [ ] машина и водитель на месте; других людей нет
- [ ] внутрь здания видно не глубже полосы света (камера внутрь не смотрит)

Кадры `2-03-07.jpg` и `2-03-08.jpg` (пустое крыльцо, дверь закрыта, машина и водитель на месте) делаю я из `2-03-01.jpg`.

**Сквозной чек-лист 2-03:** во всех кадрах та же машина на том же месте и тот же ракурс; никаких подписей; кроме Олега и водителя, никого нет. Где ошибается: машина и крыльцо «плывут» от кадра к кадру, появляется второй человек, сигарета сливается с пальцами.

### Кабинет художественного руководителя: два кадра (S17-S18), один чат

Источник - `content/paper/2-06.md` и `docs/PAPER-REQUIREMENTS.md`: 2-й этаж, 11.11.2026 утро (08:50), письменный стол, приставной стол для совещаний, книжные шкафы, афиши прошлых лет и почётные грамоты, у окна диван; на столе - стопки документов, папка-скоросшиватель, ежедневник, письменный прибор, очки, настольная лампа, стационарный телефон, **две чашки на блюдцах с остатками кофе, на одной - след губной помады**; среди бумаг - **мелкая упаковка лекарства, читаемая только при увеличении**.

### S17. `paper/2-06-room.jpg` - кабинет худрука, общий вид от двери

- **Сохранить как:** `detgame-media/paper/2-06-room.jpg`
- **Формат:** JPEG, горизонталь 3:2
- **Приложить:** ничего.

```text
Photorealistic documentation photograph of the office of the artistic director of a provincial theatre, taken from the entrance door in the morning: grey November daylight from the window plus a ceiling lamp. A large writing desk, a side table pushed against it for meetings, bookcases full of books, theatre posters and framed certificates on the walls (abstract, no readable text), a sofa by the window. Nobody in the room, nothing tidied for the camera, a lived-in feel. Wide view, horizontal 3:2. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением:

- [ ] письменный стол, приставной стол, книжные шкафы, афиши и грамоты без читаемого текста, диван у окна
- [ ] серый ноябрьский свет из окна
- [ ] людей нет; надписей нет

### S18. `paper/2-06-office.jpg` - рабочий стол, общий вид

- **Сохранить как:** `detgame-media/paper/2-06-office.jpg`
- **Формат:** JPEG, горизонталь 3:2
- **Приложить:** 1 - готовый `paper/2-06-room.jpg` (образец комнаты). Тот же чат.

```text
Same office as in the attached reference image (same walls, light and furniture). A general view of the whole writing desk surface from the visitor's side, a slightly raised angle. On the desk: stacks of documents; a black ring-binder folder lying on top with a blank white label sticker on its front (leave the label COMPLETELY BLANK, no letters); a diary; a desk pen set; reading glasses; a desk lamp; a landline desk telephone; TWO coffee cups on saucers, both with coffee dregs left, and on the rim of one of them a faint red lipstick mark. Among the papers lies one small plain white-and-blue medicine box: tiny, not in the foreground, with no readable text and no manufacturer logo (it should be noticeable only when zooming in). No blood pressure monitor. Horizontal 3:2. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением:

- [ ] **две** чашки на блюдцах с остатками кофе, **на одной след помады**
- [ ] папка-скоросшиватель с пустой этикеткой (надпись «Фонд „Сцена“: отчёт для администрации города» накладываю я)
- [ ] ежедневник, письменный прибор, очки, лампа, стационарный телефон
- [ ] мелкая упаковка лекарства есть, но не бросается в глаза и без читаемого текста (надпись «Анаприлин» накладываю я, если сценарий оставит деталь); тонометра нет

---


### Фотосеть Инны: 9 атмосферных фото (S20–S28)

Один чат, без людей и лиц (кроме руки в S24). Квадрат 1:1, телефонное фото «для соцсети»: тёплые тона, лёгкий шум, не студийное. Сохранять: `detgame-media/inna/01.jpg` … `09.jpg`.

**S20. `inna/01.jpg`** — капучино с сердечком на пенке в бумажном стаканчике на стойке буфета театра, утро
```text
A casual smartphone photo for a social media feed: капучино с сердечком на пенке в бумажном стаканчике на стойке буфета театра, утро (описание по-русски выше — переведите или вставьте как есть). Square 1:1, warm natural colours, slight phone-camera noise, not a studio shot. No people's faces, no text, no logos, no brand names, no readable signs, no watermarks.
```

**S21. `inna/02.jpg`** — полосатая серая кошка спит на клетчатом пледе на диване, домашний вечерний свет
```text
A casual smartphone photo for a social media feed: полосатая серая кошка спит на клетчатом пледе на диване, домашний вечерний свет (описание по-русски выше — переведите или вставьте как есть). Square 1:1, warm natural colours, slight phone-camera noise, not a studio shot. No people's faces, no text, no logos, no brand names, no readable signs, no watermarks.
```

**S22. `inna/03.jpg`** — противень домашних пирожков на кухонном столе, кухонное полотенце, дневной свет
```text
A casual smartphone photo for a social media feed: противень домашних пирожков на кухонном столе, кухонное полотенце, дневной свет (описание по-русски выше — переведите или вставьте как есть). Square 1:1, warm natural colours, slight phone-camera noise, not a studio shot. No people's faces, no text, no logos, no brand names, no readable signs, no watermarks.
```

**S23. `inna/04.jpg`** — аллея парка с жёлтыми листьями, скамейка, пасмурный день, без людей
```text
A casual smartphone photo for a social media feed: аллея парка с жёлтыми листьями, скамейка, пасмурный день, без людей (описание по-русски выше — переведите или вставьте как есть). Square 1:1, warm natural colours, slight phone-camera noise, not a studio shot. No people's faces, no text, no logos, no brand names, no readable signs, no watermarks.
```

**S24. `inna/05.jpg`** — женская рука с тёмно-вишнёвым маникюром держит чашку чая, без колец
```text
A casual smartphone photo for a social media feed: женская рука с тёмно-вишнёвым маникюром держит чашку чая, без колец (описание по-русски выше — переведите или вставьте как есть). Square 1:1, warm natural colours, slight phone-camera noise, not a studio shot. No people's faces, no text, no logos, no brand names, no readable signs, no watermarks.
```

**S25. `inna/06.jpg`** — ящики с красными яблоками на городском рынке, без вывесок и ценников
```text
A casual smartphone photo for a social media feed: ящики с красными яблоками на городском рынке, без вывесок и ценников (описание по-русски выше — переведите или вставьте как есть). Square 1:1, warm natural colours, slight phone-camera noise, not a studio shot. No people's faces, no text, no logos, no brand names, no readable signs, no watermarks.
```

**S26. `inna/07.jpg`** — окно кухни с новыми светлыми шторами в мелкий цветочек, подоконник с цветком в горшке
```text
A casual smartphone photo for a social media feed: окно кухни с новыми светлыми шторами в мелкий цветочек, подоконник с цветком в горшке (описание по-русски выше — переведите или вставьте как есть). Square 1:1, warm natural colours, slight phone-camera noise, not a studio shot. No people's faces, no text, no logos, no brand names, no readable signs, no watermarks.
```

**S27. `inna/08.jpg`** — та же полосатая серая кошка сидит в картонной коробке на полу
```text
A casual smartphone photo for a social media feed: та же полосатая серая кошка сидит в картонной коробке на полу (описание по-русски выше — переведите или вставьте как есть). Square 1:1, warm natural colours, slight phone-camera noise, not a studio shot. No people's faces, no text, no logos, no brand names, no readable signs, no watermarks.
```

**S28. `inna/09.jpg`** — витрина театрального буфета с пирожными и бутербродами, чистые чашки, без надписей
```text
A casual smartphone photo for a social media feed: витрина театрального буфета с пирожными и бутербродами, чистые чашки, без надписей (описание по-русски выше — переведите или вставьте как есть). Square 1:1, warm natural colours, slight phone-camera noise, not a studio shot. No people's faces, no text, no logos, no brand names, no readable signs, no watermarks.
```

---

## Видео Волкова

Ограничения из `content/pages/video/page.yaml` и 1-08: Слава **в сценическом костюме** читает монолог **в помещении, похожем на репетиционный зал**; около 1 мин; **днём, окно с дневным светом в кадре** (алиби - вечер); файл создан 08.11.2026 14:12:03; в карточке заявлено 1920 x 1080. Путь: **кадр-основа (S19, Gemini) + аудио монолога (делаю я, XTTS) -> Kling -> MP4 -> моя доводка**.

### S19. `work/video_base_frame.jpg` - кадр-основа для Kling (в игру не идёт)

Лицо с этого кадра Kling будет анимировать, поэтому проверяйте строго.

- **Сохранить как:** `detgame-media/work/video_base_frame.jpg`
- **Формат:** JPEG, горизонталь 16:9, полный размер, лицо крупно (не меньше четверти высоты кадра)
- **Приложить:** 1 - `portraits/volkov.jpg`; 2-3 - одно-два сырых фото Славы. До 4 попыток; утверждённый кадр отправьте мне **до оплаты Kling**.

```text
Use the attached images as the strict identity reference for the man. Create a photorealistic frame of this same man, who looks about 31 years old, in a bright rehearsal hall of a provincial theatre on an afternoon in early November, around 14:00. Shot like a smartphone video propped on a chair: completely static, horizontal 16:9, he stands centred, facing the camera, framed from the belt up, looking straight into the lens, mouth closed and relaxed, arms hanging down relaxed, no hands near the face, head upright. He wears a dark 19th-century stage costume: black tailcoat, white shirt with a high collar, dark cravat, dark waistcoat, no hat. Behind him on one side, a large window with CLEAR NATURAL DAYLIGHT: an overcast grey November sky and bare tree branches visible outside, the window clearly lit and clearly visible in the frame. Wooden parquet floor, plain light wall, a long wall mirror on the left, a plastic water bottle on a chair. Flat, slightly amateur daylight, natural skin, no beauty filter. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением:

- [ ] лицо **анфас**, глаза в камеру, **рот закрыт**, руки опущены и не у лица, голова прямо
- [ ] **окно с дневным светом хорошо видно** (не вечер, не лампы); за окном ноябрь: серое небо, голые ветки (не зелень, не снег)
- [ ] сценический костюм: фрак, сорочка с высоким воротом, шейный платок, жилет
- [ ] комната похожа на репетиционный зал (паркет, зеркало); нет текста и логотипов
- [ ] 16:9; лицо узнаваемо как Слава

### K01. Kling AI: шаги и запрос для видео `video/rehearsal.mp4`

- **Сохранить как:** `detgame-media/video/rehearsal.mp4` (все удачные варианты - ещё и в `_attempts/`)
- **Формат:** MP4 H.264 + AAC, 16:9, длительность 40-60 с, **≤ 25 МБ** (сжатие и доводку делаю я; от вас - лучший исходник из Kling)
- **Что загрузить в Kling:** 1 - `work/video_base_frame.jpg` (утверждённый кадр S19); 2 - аудио монолога **`rehearsal_audio.mp3`**, которое **пришлю я** (XTTS-v2, голос Славы; сначала 10-секундная проба, потом полное; если полное не принимается - части `rehearsal_part1.mp3` и `rehearsal_part2.mp3` в тот же кадр). Монолог - Лермонтов, «Маскарад», действие первое, сцена третья, выход пятый (текст и источник - `MEDIA-PLAN-A` §5.2).

Шаги (подробности и расход кредитов - `MEDIA-PLAN-A` §5.3; названия кнопок в Kling и точный тариф, открывающий нужный инструмент, мной не проверялись - смотрите в интерфейсе и на странице тарифов):

1. Войти на klingai.com. **До оплаты** на бесплатных кредитах найти инструмент, который принимает картинку и аудио и делает говорящее видео (в версиях называется по-разному, например Avatar или Lip Sync).
2. Загрузить `video_base_frame.jpg` и 10-секундную пробу аудио, сделать пробный ролик, проверить губы и лицо.
3. Если проба хорошая и инструмент доступен - оплатить тариф на 1 месяц (цену проверить на странице тарифов), автопродление выключить сразу. Оплачивать только в вечер Kling.
4. Загрузить кадр и полное аудио. В поле запроса (если есть) вставить:

```text
A man in a 19th-century theatre costume recites a dramatic monologue in Russian. Natural lip movement in sync with the audio, subtle natural head movements and facial expressions, eyes mostly on the camera. Static camera, no zoom, no camera movement. The bright daylight from the window stays constant. Hands stay down.
```
5. Качество и разрешение - максимум; убедиться, что на скачиваемом файле **нет водяного знака**.
6. Скачать MP4 в лучшем качестве, сохранить все удачные варианты. Закладывайте 4-6 генераций на полный монолог; если кредиты кончаются - не докупать, написать мне. После работы **отменить подписку**.

Проверь перед сохранением (смотреть на телефоне):

- [ ] губы попадают в звуки, нет «проглоченных» фраз
- [ ] лицо стабильно, не «плывёт» и не превращается в другого человека; костюм не меняется
- [ ] **окно в кадре всё время светлое, дневное** (не мигает, не темнеет); камера не дрейфует
- [ ] руки не вылезают в кадр, лишних пальцев нет; длительность 40-60 с

---

## Что прислать оркестратору

После каждого вечера - картинки (или архив) в чат; в конце - один архив `detgame-media.zip` со структурой из `MEDIA-PLAN-A` §7.1. Не накладывайте таймкоды, подписи, рамки и не обрезайте картинки сами.

1. **Файлы по путям из заголовков запросов:** 14 портретов (`portraits/*.jpg`), `news/voroncov_arbenin.jpg`, `gromov/meeting.jpg`, `gromov/cover.jpg`, `inna/brooch.jpg`, `lab/station_cam.jpg`, `lab/pillbox.jpg`, `paper/1-10-*.jpg` (3), `paper/2-03-01..06.jpg` (6), `paper/2-06-room.jpg`, `paper/2-06-office.jpg`, рабочие `work/video_base_frame.jpg` и `work/brooch_ref.jpg`, лучший MP4 из Kling (`video/rehearsal.mp4`).
2. **Запасные варианты и неудачи** - `_attempts/`.
3. **Для каждого трудного кадра** (S02, S05, S06, S07, S09, S14, S19) - сколько попыток ушло и какая правка сработала.
4. **Видимый знак Gemini:** есть ли на скачанных картинках значок в углу и в каком (не подтверждено источниками проекта).
5. **Возраст Инны и Олега в жизни** (по желанию: запросы работают в обе стороны, но он помогает проверить, насколько портрет «сдвинут»).
6. **Настройки Kling:** какой инструмент и тариф использовали, разрешение, был ли водяной знак, сколько генераций и кредитов ушло.
7. **Что осталось нерешённым:** любой кадр, где после 3 правок и нового чата деталь-улика не совпала с чек-листом (таблетница, брошь, окно на вокзале) - пришлите лучший вариант, дорисую в Pillow.

Просьба от меня к автору: после правки R01 пришлите мне новый `voroncov.jpg` на проверку, прежде чем делать остальные портреты и сцены с Воронцовым.
