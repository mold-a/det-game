> Актуальная версия — docs/PRODUCTION.md (статусы, свежие промпты, план). Этот документ остаётся для истории и справки.

# Фото, аватарки и голосовые для соцсетей — набор 2 (сценарист, 21.10.2026)

Дополняет `docs/drafts/pages/PHOTOS.md` (F01–F08) и `docs/PROMPTS.md`. Зачем эти кадры и какие из них улики — `docs/CLUE-MAP.md`, раздел 4 и предложения 3.1–3.10. **Шаг 2 выполнен 21.10 (вечер):** посты, пути к файлам и голосовые уже стоят в `content/pages/*`; пока файлов нет, сборка пишет «нет медиафайла» и показывает заглушку. Тексты постов в этом файле — те же, что в `content/` (если расходятся, прав `content/`).

## Что генерировать автору (коротко, по порядку)

1. **Улики — первыми, каждая в своём чате:**
   - `media/krug-voroncov/02.jpg` — VR-02, гримёрка 28.10, дублёр за плечом смотрит в телефон (бонус fb3);
   - `media/krug-voroncov/03.jpg` — VR-03, селфи на набережной, фигура в короткой тёмной куртке (спящая, 4-08);
   - `media/paper/2-06-office.jpg` — **перегенерация** S18: упаковка «Анаприлина» на столе читается при увеличении (раздел 2а);
   - `media/inna/10.jpg` — IN-10, костюм с той же брошью на вешалке у буфета (подкрепление бонуса s2.b2).
2. **Голосовые (5 шт.), нейросетью по клонам:** V1 Молдованов (31.10, «кто-то идёт следом»), V2 и V3 Марина, V4 Вольская, V5 Волков. У Кирилла голосовых **нет**.
3. **Аватарки (8) и обложки (6):** AV-1…AV-8, CV-2…CV-5, CV-7 (у `gromov` обложка уже есть, у `krug-levin` обложки нет).
4. **Фото «из жизни» к постам (22):** VR-01, 04, 05; KR-01…05; MR-01, 02; VS-01…03; VK-01…03; GR-01…03; LV-01; NM-01.
5. Ещё не сделаны и не входят в набор 2: `inna/01.jpg`…`09.jpg` (S20–S28 в `docs/PROMPTS.md`), `portraits/gnedich.jpg`, `portraits/zavyalov.jpg`, `video/rehearsal.mp4`.

Полный список файлов с путями, страницами и пометкой «улика / нет» — раздел 6 в конце.

## Общие правила

- **Только генерация.** Реальных родственников вживую не снимаем (решение автора 21.10). Лица — только по готовым портретам `media/portraits/<id>.jpg`, режим «тот же человек». Портреты `media/portraits/*` остаются для дела и вопросов и **не заменяются**.
- **Возраст** — по `content/characters.yaml`: Воронцов 56, Кирилл 56, Марина 24, Вольская 54, Громова 45, Инна 46, Волков 31, Лёвин 44. В запросе фраза «looks exactly N years old, not older».
- **Без лишнего реквизита у героев:** никаких наушников, бейджей, шнурков с пропуском, значков, формы, часов и украшений, кроме названных в запросе. Очки — только у тех, у кого они есть на портрете (у Воронцова — **прозрачная** оправа).
- **Никаких надписей, логотипов, гербов, флагов и читаемых вывесок**; экраны телефонов и ноутбуков — тёмные или размытые, без текста. Только вымышленные бренды мира.
- **Жанр — «снято на телефон для соцсети»:** живой свет, лёгкий шум, не студия. Не «паспорт»: взгляд и поза свободные.
- **Сохранять как** `media/<page>/<имя>.jpg`; аватар — `media/<page>/avatar.jpg`, обложка — `media/<page>/cover.jpg`, фото к постам — `media/<page>/<nn>.jpg`, голосовые — `media/<page>/voice-<nn>.mp3`. Неудачные варианты — в `_attempts/`.
- **Форматы:** аватар — квадрат 1:1, не меньше 800 px, ≤ 400 КБ; обложка — широкая 3:1 (если генератор дал 16:9, обрежу), ≤ 800 КБ; фото к посту — 4:5 или 1:1 (как указано), ≤ 600 КБ.
- **Порядок:** каждая серия с одним и тем же человеком — в одном чате (лицо держится лучше); новый человек — новый чат. Сначала улики (VR-02, VR-03), потом остальное.
- **Как прикладывать:** сначала портрет(ы) героя, потом образец места, если он указан. В тексте запроса «image 1, image 2…» — в порядке приложения.

Хвост, который уже стоит в конце каждого запроса:

> Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.

Если лицо «уехало», в том же чате — правка из `docs/PROMPTS.md`: `Same image, but make the face match image 1 exactly (same eyes, nose, mouth, face shape and hairline); keep everything else unchanged.`

## Оглавление

1. Аватарки и обложки (AV, CV)
2. Фото к постам: `krug-voroncov` (VR), `krug-kirill` (KR), `krug-marina` (MR), `krug-volskaya` (VS), `krug-volkov` (VK), `krug-levin` (LV), `gromov` (GR), `inna` (IN), `news-most` (NM)
2а. Бумага: перегенерация `paper/2-06-office.jpg`
3. Голосовые (V1–V5) и поле `audio`
4. «Кружки»: что убрано и что осталось
5. Соответствие старым номерам из `PHOTOS.md`
6. Итоговый список файлов

---

## 1. Аватарки и обложки

Обложку `gromov/cover.jpg` (здание администрации) не меняем — она уже есть.

### AV-1. `media/gromov/avatar.jpg` — Громова

- **Приложить:** 1 — `portraits/gromov.jpg`.
- **Характер:** командует и опекает, уверенная, резкая, но тёплая с «своими» (VOICES).

```text
Use image 1 as the strict identity reference: this is the same real woman, keep exactly her face shape, eyes, eyebrows, nose, mouth, skin tone, hairline and hairstyle as in image 1; she looks exactly 45 years old, not older. Casual profile photo taken by a colleague on a smartphone: she stands on a city river embankment on a windy, bright autumn day, wearing a camel wool coat over a dark turtleneck, hair slightly moved by the wind, looking into the camera with a confident, slightly ironic half-smile, chin a little raised, as if she is about to give an instruction. Behind her, out of focus: a stone parapet, the river and yellow trees on the far bank. Natural daylight, a little contrast, light phone-camera grain. Head and shoulders, face slightly off-centre. No jewellery, no badges, no bag, nothing in her hands. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: лицо узнаётся, 45 лет, никаких флагов и вывесок на заднем плане, в руках ничего.

### AV-2. `media/krug-voroncov/avatar.jpg` — Воронцов

- **Приложить:** 1 — `portraits/voroncov.jpg` (прозрачная оправа).
- **Характер:** харизма, улыбка «во все зубы» 😁, брови «генсека».

```text
Use image 1 as the strict identity reference: this is the same real man, keep exactly his face, thick dark eyebrows, grey hair, grey beard and his glasses with a TRANSPARENT clear frame as in image 1; he looks exactly 56 years old, not older. Casual backstage selfie in the wings of a provincial theatre: he holds the phone himself at arm's length (the phone is out of frame), grinning widely with all his teeth, eyebrows raised theatrically, wearing a plain dark T-shirt. Behind him, softly out of focus: black stage curtains, a strip of warm stage light, a lighting stand, a corner of a red velvet curtain. Warm, slightly orange stage light from one side, phone-camera grain. Head and shoulders. No headphones, no badge, no lanyard, no neck chain, no costume. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: оправа прозрачная, брови густые и тёмные, широкая улыбка, никакого реквизита.

### CV-2. `media/krug-voroncov/cover.jpg` — обложка Воронцова

- **Приложить:** ничего.

```text
Very wide photograph of an empty stage of a provincial drama theatre seen from the side wings: bare wooden stage floor, a single "ghost light" (a bare bulb on a tall stand) glowing in the middle of the stage, a heavy dark-red velvet curtain half-open, the dark auditorium with rows of red seats barely visible beyond the footlights, dust in the beam of light. Quiet, melancholic, warm and dark. No people. Very wide horizontal composition, about 3:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

### AV-3. `media/krug-kirill/avatar.jpg` — Кирилл

- **Приложить:** 1 — `portraits/kirill.jpg`.
- **Характер:** балагур, смеётся над собой, «чиню компьютеры, себя — нет».

```text
Use image 1 as the strict identity reference: this is the same real man, keep exactly his face shape, eyes, eyebrows, nose, mouth, hairline, hairstyle and facial hair as in image 1 (glasses only if he wears them in image 1); he looks exactly 56 years old, not older. Casual smartphone selfie on a river bank at early morning: he squints and laughs at the camera, wearing a dark green fleece jacket over a checked shirt, a fishing rod leaning on his shoulder (only the rod shaft is visible), morning mist over calm water and a wooden pier softly out of focus behind him. Soft cool dawn light with a warm touch of the rising sun, light phone-camera grain. Head and shoulders, slightly from below as in a selfie. No hat, no headphones, no badges, no watch. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

### CV-3. `media/krug-kirill/cover.jpg` — обложка Кирилла

```text
Very wide landscape photograph of a calm river at dawn in late September in central Russia: thin mist over the water, an old wooden boat tied to a small pier, reeds in the foreground, a line of birch trees turning yellow on the far bank, the sky pale pink and grey. No people. Very wide horizontal composition, about 3:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

### AV-4. `media/krug-marina/avatar.jpg` — Марина

- **Приложить:** 1 — `portraits/marina.jpg` (утверждённый, 24 года).
- **Характер:** весёлая, «приветик», «прям», любит голосовые; учитель английского.

```text
Use image 1 as the strict identity reference: this is the same real young woman, keep exactly her face shape, eyes, eyebrows, nose, mouth, skin tone, hairline and hairstyle as in image 1; she looks exactly 24 years old - an adult young teacher, not a teenager, not older than 24. Casual smartphone selfie in a cosy café by the window: she holds a big cup of latte with both hands near her chin, laughs with her eyes slightly squinted, head a little tilted, wearing an oversized soft beige knitted sweater. Behind her, softly out of focus: a rainy autumn street seen through the window, warm café lamps, a shelf with plants. Warm, soft light, light phone-camera grain. Head and shoulders. No jewellery, no headphones, no badges, no text on the cup. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: взрослая девушка 24 лет, не подросток; на чашке нет надписей.

### CV-4. `media/krug-marina/cover.jpg` — обложка Марины

```text
Very wide photograph of a quiet street of an old provincial Russian-like town in October after rain: wet cobblestones reflecting warm street lamps, yellow and orange leaves on the pavement, two- and three-storey old houses with lit windows, a tram line curving away into the distance without any tram. Evening blue hour. No people, no shop signs, no readable text. Very wide horizontal composition, about 3:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

### AV-5. `media/krug-volskaya/avatar.jpg` — Вольская

- **Приложить:** 1 — `portraits/volskaya.jpg`.
- **Характер:** светская, уверенная, сдержанно тёплая; театр и музеи.

```text
Use image 1 as the strict identity reference: this is the same real woman, keep exactly her face shape, eyes, eyebrows, nose, mouth, skin tone, hairline and hairstyle as in image 1; she looks exactly 54 years old, not older. Elegant but casual profile photo taken by a friend on a smartphone in a small art museum: she stands three-quarters to the camera in front of a wall with framed watercolours (the paintings are soft and out of focus, river-town views, no captions), turns her head to the camera with a calm, warm, slightly reserved smile. She wears a dark navy silk blouse and a light grey wool cardigan over her shoulders. Soft gallery light. Head and shoulders. No necklaces, no brooches, no rings, no badges, no glasses unless she wears them in image 1. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: **никаких брошей и украшений** (броши — ложный след Инны, табакерка — линия Вольской: не путаем).

### CV-5. `media/krug-volskaya/cover.jpg` — обложка Вольской: вид из ложи

```text
Very wide photograph taken from a theatre box near the stage of a provincial drama theatre: in the foreground the red velvet edge of the box parapet and a folded programme without readable text lying on it, below and beyond — the stage with a closed dark-red curtain softly lit, the warm golden auditorium, a small chandelier. No people, no text. Very wide horizontal composition, about 3:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

### AV-6. `media/inna/avatar.jpg` — Инна (фотосеть «Кадр»)

- **Приложить:** 1 — `portraits/inna.jpg`.
- **Характер:** суетливая, любит красивое, «кофеёк», «новая красота ✨».

```text
Use image 1 as the strict identity reference: this is the same real woman, keep exactly her face shape, eyes, eyebrows, nose, mouth, skin tone, hairline and hairstyle as in image 1; she looks exactly 46 years old, not older. Cheerful smartphone selfie behind the counter of a small theatre buffet: she holds a cup of cappuccino with a heart in the foam next to her cheek and smiles brightly, wearing a soft pastel-pink blouse. Behind her, out of focus: a glass display with pastries and sandwiches, white cups on a shelf, warm buffet lamps. Warm, cosy tones, light phone-camera grain. Head and shoulders. NO brooch, no jewellery, no apron, no badge, no text on the cup or the display. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: **броши нет** — брошь появляется только на улике `inna/brooch.jpg`.

### AV-7. `media/krug-volkov/avatar.jpg` — Волков (страница `krug-volkov` принята 21.10)

- **Приложить:** 1 — `portraits/volkov.jpg`.
- **Характер:** добродушный, услужливый, часто улыбается, говорит быстро.

```text
Use image 1 as the strict identity reference: this is the same real young man, keep exactly his face shape, eyes, eyebrows, nose, mouth, short dark hair and clean-shaven face as in image 1; he looks exactly 31 years old, not older. Friendly smartphone selfie in a narrow backstage corridor of a theatre: he smiles openly at the camera, slightly leaning forward, wearing a plain grey knitted sweater. Behind him, out of focus: a corridor with old painted walls, a row of dressing-room doors without numbers or signs, warm ceiling lamps. Natural warm light, light phone-camera grain. Head and shoulders. No jacket, no headphones, no badge, no lanyard, no watch, no costume. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: **серый свитер, не тёмная короткая куртка** — куртка остаётся силуэтом на улике VR-03 и в 4-08, связывать их должны игроки, а не аватарка.

### AV-8. `media/krug-levin/avatar.jpg` — Лёвин (страница `krug-levin` принята 21.10)

- **Приложить:** 1 — `portraits/stas.jpg`.
- **Характер:** болтливый, любит драму, «Я вам как артист скажу»; на странице — пёс, дача, ремонт.

```text
Use image 1 as the strict identity reference: this is the same real man, keep exactly his face shape, eyes, eyebrows, nose, mouth, hairline, hairstyle and facial hair as in image 1 (glasses only if he wears them in image 1); he looks exactly 44 years old, not older. Casual smartphone selfie in a city park on a bright autumn day: he laughs theatrically with one eyebrow raised and his free hand spread in a dramatic gesture, as if telling a story; a big friendly shaggy dog pushes its head into the frame from the lower left and licks his cheek. He wears a dark-green wool coat with a scarf. Behind him, out of focus: yellow maples, a park path, a bench. Natural daylight, light phone-camera grain. Head and shoulders. No hat, no headphones, no badges, no costume. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: лицо узнаётся, 44 года; собака не закрывает лицо; никаких табличек и вывесок.

### CV-7. `media/krug-volkov/cover.jpg` — обложка Волкова: зал праздника

```text
Very wide photograph of a festive banquet hall prepared for an anniversary party, before guests arrive: round tables with white tablecloths, chairs with bows, warm string lights and garlands, balloons in pastel colours, a microphone on a stand in the foreground slightly out of focus, a small dance floor. NO banners or letters, no numbers on balloons, no readable text anywhere. No people. Very wide horizontal composition, about 3:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

---

## 2. Фото к постам

Пометка **УЛИКА** — кадр, на котором держится цепочка рассуждений (CLUE-MAP 3.1, 3.4); его нельзя упрощать. Остальное — жизнь страницы.

### `krug-voroncov` — Воронцов

Манера подписей: строчные, без точки в конце, «)», «!!», 😁, абзац на фразу.

#### VR-01. `media/krug-voroncov/01.jpg` — дача, 11.10 (жизнь)

Пост `2026-10-11T16:40`: «закрыл сезон на даче\nяблоки собраны, листья побеждены\nграбли победили меня 😁»

- **Приложить:** 1 — `portraits/voroncov.jpg`.

```text
Use image 1 as the strict identity reference: the same real man, keep exactly his face, thick dark eyebrows, grey hair, grey beard and glasses with a TRANSPARENT frame; he looks exactly 56 years old, not older. Casual smartphone photo at a small Russian country house garden in mid-October: he stands next to a wheelbarrow full of fallen leaves, leaning on a garden rake with both hands, laughing, wearing an old dark-blue knitted sweater and work trousers. Behind him: a bare apple tree with a few last apples, a simple wooden dacha house with a porch, a wooden fence, grey overcast sky, yellow birches. Natural soft daylight, light phone-camera grain. Medium shot, vertical 4:5. No gloves, no hat, no watch, no badges. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### VR-02. `media/krug-voroncov/02.jpg` — гримёрка, 28.10, перерыв — **УЛИКА**

Пост `2026-10-28T15:52`: «перерыв между сценами\nотмечаюсь, что на месте 😁\nфото — {Лёвин}, он считает, что это искусство» (CLUE-MAP 3.1; подпись смягчена по решению автора 21.10 — не эхо признания R-01). Лёвин в своей ленте 28.10 в 20:15 пишет, что «открыл в себе фотографа», и ссылается на этот пост.

**Что должно быть видно:** Воронцов сидит у гримировального зеркала и набирает что-то на телефоне **одним указательным пальцем**. Дублёр стоит **за его правым плечом**, наклонился и **смотрит в экран**. Экран к камере **не повёрнут** (видна задняя крышка без логотипа). Снято из дверей гримёрки. Сумки, таблетницы, бутылки воды и зарядки в кадре нет: это предметы улик 1-09 и 1-10, их не дублируем.

- **Приложить:** 1 — `portraits/voroncov.jpg`; 2 — `portraits/volkov.jpg`; 3 — `paper/1-10-general.jpg` (образец комнаты: стены, зеркало с лампами, мебель).
- **Формат:** горизонталь 4:3.

```text
Image 1 is the strict identity reference for the OLDER man; image 2 is the strict identity reference for the YOUNGER man; image 3 is ONLY a reference for the room (walls, the make-up mirror framed with light bulbs, the dressing table, the furniture) - do not copy any objects or people from image 3. Casual smartphone photo taken from the open doorway of a small windowless theatre dressing room during a rehearsal break in late October, afternoon. The OLDER man from image 1 (exactly 56 years old, thick dark eyebrows, grey hair, grey beard, glasses with a TRANSPARENT frame) sits in a chair at the dressing table with his back half-turned to the mirror, wearing a plain white shirt with rolled-up sleeves and dark trousers (rehearsal clothes, not a costume). He holds a smartphone at chest height in his left hand and types slowly with ONE index finger of his right hand, concentrated, eyebrows raised. The phone is turned with its BACK to the camera: the screen is NOT visible; the back of the phone is plain dark with no logo. The YOUNGER man from image 2 (exactly 31 years old, short dark hair, clean-shaven) stands right behind the older man's RIGHT shoulder, leaning forward a little with one hand on the back of the chair, looking DOWN at the phone screen with a light friendly smile; he wears a plain grey sweater. Both faces are clearly visible and recognisable. The make-up mirror behind them reflects only blurred warm bulbs and the wall - no reflection of the photographer and no phone screen in the mirror. On the dressing table: only make-up brushes in a cup, a powder box and a script with blurred lines. NO bag, NO pill box, NO water bottle, NO phone charger or cable in the frame. Warm yellow light from the mirror bulbs, slight phone-camera grain and a little motion blur on the typing finger. Horizontal 4:3. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением:
- [ ] оба лица узнаются; Воронцову 56, оправа прозрачная; дублёру 31;
- [ ] дублёр **за правым плечом** и смотрит **в экран**, а не в камеру;
- [ ] экран телефона не виден ни напрямую, ни в зеркале; на задней крышке нет логотипа;
- [ ] в кадре нет сумки, таблетницы, бутылки, зарядки;
- [ ] комната похожа на `1-10-general.jpg` (зеркало с лампами).

Если генератор упорно поворачивает телефон экраном к камере — правка: `Same image, but the phone is turned so that only its plain back is visible to the camera; the screen faces the two men.`

#### VR-03. `media/krug-voroncov/03.jpg` — селфи «со вчерашней прогулки», пост 31.10 — **СПЯЩАЯ УЛИКА**

Пост `2026-10-31T10:12`: «вчерашняя прогулка\nпечатать лень, руки замёрзли — рассказываю голосом 😁» + голосовое V1 (в нём «вчера полдня бродил по городу… кто-то идёт следом»; CLUE-MAP 3.4). Снимок сделан «вчера», 30.10, после обеда.

**Что должно быть видно:** Воронцов в **длинном тёмном пальто, без шапки, в очках** (как в 4-08). На заднем плане, метрах в 12–15, не в фокусе, — **фигура в короткой тёмной куртке, без шапки**, стоит у парапета и смотрит в его сторону. **Лица фигуры не разобрать**: в 4-08 «личность не установлена», здесь тоже.

- **Приложить:** 1 — `portraits/voroncov.jpg`.
- **Формат:** вертикаль 4:5.

```text
Use image 1 as the strict identity reference: the same real man, keep exactly his face, thick dark eyebrows, grey hair, grey beard and glasses with a TRANSPARENT frame; he looks exactly 56 years old, not older. Casual smartphone selfie on a city river embankment on an overcast windy afternoon at the end of October: he holds the phone himself (phone out of frame), smiles with one corner of his mouth and raises one eyebrow ironically, wearing a LONG DARK wool coat with the collar up and NO hat, a dark scarf. Behind him: a stone parapet, the grey river, bare trees and old buildings of a provincial town in soft focus. IMPORTANT: in the background, about 12-15 metres behind him, near the parapet, stands ONE other person - a slim figure in a SHORT DARK jacket and NO hat, dark trousers, standing still and turned towards the camera side; this figure is small, OUT OF FOCUS and in shadow, the FACE is NOT recognisable at all (blurred, no facial features). No other people close by, only two or three tiny distant passers-by far away. Cool grey daylight, light phone-camera grain. Vertical 4:5. No hat, no headphones, no badges. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь:
- [ ] пальто длинное и тёмное, без шапки, очки прозрачные;
- [ ] фигура на заднем плане одна, куртка **короткая тёмная**, без шапки, **лица не видно**;
- [ ] нет вокзала, поездов, касс, вывесок (это набережная).

#### VR-04. `media/krug-voroncov/04.jpg` — борщ, 02.11 (жизнь)

Пост `2026-11-02T19:20`: «борщ по маминому рецепту\nмама сказала бы: соли мало\nмама всегда права 😁»

- **Приложить:** ничего (лица нет).

```text
Casual smartphone photo of a home kitchen stove in the evening: a big enamel pot of deep-red borscht with steam, a man's hand holding a ladle above it (only the hand and forearm in a rolled-up dark sweater sleeve, no face), a wooden cutting board with chopped dill and a half of a lemon, a jar of sour cream, warm kitchen lamp light, slightly steamy air. Vertical 4:5. No labels on jars, no text. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

На кухне нет лекарств, таблетниц и упаковок.

#### VR-05. `media/krug-voroncov/05.jpg` — прогон второго акта, пост 06.11 (жизнь, театр)

К существующему посту `2026-11-06T15:26` («прогон второго акта…»). Это бывший F04 из `PHOTOS.md`, новое имя файла.

- **Приложить:** 1 — `portraits/voroncov.jpg`.

```text
Use image 1 as the strict identity reference: the same real man, keep exactly his face, thick dark eyebrows, grey hair, grey beard and glasses with a TRANSPARENT frame pushed up on his forehead; he looks exactly 56 years old, not older. Casual backstage smartphone photo during a rehearsal on the stage of a provincial theatre: he stands centre stage in a plain white shirt with rolled sleeves and dark trousers (rehearsal clothes, not a costume), holding a few sheets of a script, laughing with his head thrown back a little. Bare stage with work lights, a wooden rehearsal table, a couple of chairs; out of focus in the background two other actors, faces not distinguishable. Warm work lighting, slightly grainy. No readable text on the script pages (only blurred lines), no posters, no signs. No bag, no bottles, no pill boxes anywhere. Horizontal 4:3. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Текстовый пост без фото (жизнь), `2026-10-18T09:05`: «полчаса искал очки\nочки были на лбу\nарбенин так не позорился 😁».

### `krug-kirill` — Кирилл

Манера: с заглавной, «....», «!!!!!», 😂 🤷‍♂️ 🥳, «как то», «Есть такое)». Фразы «Было бы за что» нет и быть не может; ему в комментариях не говорят «спасибо». **Голосовых у Кирилла нет** (решение автора 21.10: голос сравнили бы со звонком 1-05 уже на этапе 1).

#### KR-01. `media/krug-kirill/01.jpg` — рыбалка, к посту 04.10 (жизнь)

- **Приложить:** 1 — `portraits/kirill.jpg`.

```text
Use image 1 as the strict identity reference: the same real man, keep exactly his face shape, eyes, eyebrows, nose, mouth, hairline, hairstyle and facial hair (glasses only if in image 1); he looks exactly 56 years old, not older. Casual smartphone photo on a river bank in early October: he sits on a folding stool with a fishing rod, holding up a tiny fish no bigger than his palm with an exaggerated proud face, a thermos and a metal mug next to him on the grass. He wears a dark green fleece jacket and rubber boots. Morning mist, yellow trees on the far bank, calm water. Natural soft light, light phone-camera grain. Vertical 4:5. No hat, no headphones, no badges, no text on the thermos. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### KR-02. `media/krug-kirill/02.jpg` — встреча одноклассников, к посту 17.10 (жизнь)

Кирилл и Воронцов рядом, остальные одноклассники — спиной или размыто. **Чай, не алкоголь** («сейчас у нас по чашечке», 1-08; в крови спирта нет — 3-05, не подкрепляем вариант «алкоголь» в s3.q2).

- **Приложить:** 1 — `portraits/kirill.jpg`; 2 — `portraits/voroncov.jpg`.

```text
Image 1 is the strict identity reference for the man on the LEFT; image 2 is the strict identity reference for the man on the RIGHT (thick dark eyebrows, grey hair, grey beard, glasses with a TRANSPARENT frame). Both look exactly 56 years old, not older. Casual smartphone photo at a reunion of old school classmates in a small cosy café in the evening: the two men sit side by side at a long table, laughing, the man on the right gesturing as if telling a funny story, the man on the left covering his face with his hand from laughter. On the table: teapots, cups of tea, a big cake, plates; NO alcohol, no bottles, no glasses of wine. Around the table four or five other people of the same age, seen from behind or out of focus, faces not distinguishable. Warm café light, slight motion blur, light phone-camera grain. Horizontal 4:3. No badges, no text on cups or walls. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### KR-03. `media/krug-kirill/03.jpg` — «настраивал другу», 20.10 — спящая

Пост `2026-10-20T23:05` (CLUE-MAP 3.7). Ноутбук, две кружки, поздний вечер. **Экран — без текста, без окон программ, без логотипа облака.**

```text
Casual smartphone photo of a home desk late in the evening: an open laptop with its screen glowing but showing only a soft blurred abstract blue wallpaper (no windows, no text, no icons, no logos), two mugs of tea - one half-empty, one full and untouched - a plate with two cookies, a pair of reading glasses, a desk lamp with warm light, a smartphone lying face down. Two chairs pulled up to the desk as if two people were sitting there. No people in the frame. Warm, cosy, slightly grainy. Horizontal 4:3. No brand logo on the laptop or phone, no text on mugs. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### KR-04. `media/krug-kirill/04.jpg` — мамин телефон, к посту 26.10 (жизнь)

```text
Close-up casual smartphone photo at a kitchen table: an elderly woman's hands holding a new simple smartphone with very large icons on a softly blurred screen (no readable text, no logo), a man's hand pointing at the screen with one finger as if explaining, a cup of tea and a plate of pancakes with jam nearby, a crocheted tablecloth. Faces out of frame. Warm daylight from a window. Square 1:1. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### KR-05. `media/krug-kirill/05.jpg` — «кот работает из дома», к посту 07.11 (жизнь)

Бывший F03 из `PHOTOS.md` — запрос оттуда без изменений, новое имя файла. Если есть фото настоящего кота дяди, приложить и начать с `Use image 1 as the strict reference for the cat's colour and markings.`

### `krug-marina` — Марина

Манера: всё строчными, без точек, «агааа», «прям», «короче», «мб», 🤗 😹 😛😛😛 «:(». Видеокружков нет — только текст и голосовые (раздел 3).

#### MR-01. `media/krug-marina/01.jpg` — Хэллоуин в группе, к посту 31.10 (жизнь)

Голосовое V3. Детей в кадре нет.

```text
Casual smartphone photo on a teacher's desk in a classroom after a Halloween lesson: a carved pumpkin with a funny face and a candle inside, next to it a paper class register (closed, no readable text), a pair of round toy glasses, a small paper witch hat, a few candy wrappers and an English picture dictionary (cover blurred, no readable title). Window light in late October afternoon, warm and playful. No people, no children. Vertical 4:5. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### MR-02. `media/krug-marina/02.jpg` — кухня 03.11, «чай так и не выпил» (эхо 4-14)

Пост `2026-11-03T22:40` (CLUE-MAP 3.9): «дядя тёма заезжал вечером / весь вечер просидели на кухне, а чай так и остыл нетронутый / сказал, всё будет хорошо / мб я чего то не понимаю :(». Формулировка нарочно не повторяет 4-14. Две чашки: одна выпита, вторая **полная**.

```text
Casual smartphone photo of a small kitchen table late in the evening: two cups of tea - one empty with a tea bag on a saucer, the other FULL and untouched with a faint skin of cooled tea; a plate of cookies nobody touched, a man's grey wool scarf forgotten on the back of a chair, a lamp with warm yellow light, dark window with city lights blurred behind. Quiet, a little sad mood. No people. Vertical 4:5. No text, no labels. No pills, no medicine, no pill box anywhere. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

### `krug-volskaya` — Вольская

Публичные посты — полными предложениями, с «Ну…», «)», эмодзи тройками, «Красавчики 👍».

#### VS-01. `media/krug-volskaya/01.jpg` — выставка «Верхнеречинск в акварели», к посту 10.10

- **Приложить:** 1 — `portraits/volskaya.jpg`.

```text
Use image 1 as the strict identity reference: the same real woman, keep exactly her face shape, eyes, eyebrows, nose, mouth, skin tone, hairline and hairstyle; she looks exactly 54 years old, not older. Casual smartphone photo in a small provincial art museum hall: she stands in three-quarter profile looking closely at a framed watercolour of a river town with a theatre building and a bridge, her hand near her chin. She wears a dark navy blouse and a grey wool cardigan. Several other watercolours on the white walls, two other visitors far away from behind. Soft gallery light. Vertical 4:5. No captions or labels under the paintings, no signs, no jewellery, no brooch. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### VS-02. `media/krug-volskaya/02.jpg` — концерт детской студии, к посту 24.10

```text
Casual smartphone photo from the audience of a children's concert on a small theatre stage: six or seven children aged 8-12 in simple folk-tale costumes singing, seen from the side and mostly from behind or in soft focus (faces not distinguishable), a teacher at an upright piano, warm stage light, the backs of parents' heads in the foreground, one parent holding up a phone (screen not visible). Horizontal 4:3. No banners, no text. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### VS-03. `media/krug-volskaya/03.jpg` — пирог с брусникой, 01.11 (жизнь)

Пост `2026-11-01T17:15`: «Ну вот) Пирог с брусникой по бабушкиному рецепту. Получился красавец 👍 / Девочки, приглашение — голосом ❤️ ❤️ ❤️» + голосовое V4.

```text
Casual smartphone photo of a homemade open lingonberry pie on a round wooden board on a dining table, one slice cut out and placed on a porcelain plate with a silver fork, two thin porcelain cups of tea, a small vase with dried flowers, a linen napkin, soft afternoon window light, elegant but homely. No people, no text, no labels. Square 1:1. No jewellery boxes, no silver boxes, no antiques on the table. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

На столе нет серебряных коробочек и антиквариата: табакерка — улика этапов 3–4.

### `krug-volkov` — Волков (принята 21.10)

Манера: с заглавной, коротко, без точки в конце, 👌 🤝 👋 😉.

#### VK-01. `media/krug-volkov/01.jpg` — «третий сезон», 21.09, с Воронцовым за кулисами

- **Приложить:** 1 — `portraits/volkov.jpg`; 2 — `portraits/voroncov.jpg`.

```text
Image 1 is the strict identity reference for the YOUNGER man (exactly 31 years old, short dark hair, clean-shaven); image 2 is the strict identity reference for the OLDER man (exactly 56 years old, thick dark eyebrows, grey hair, grey beard, glasses with a TRANSPARENT frame). Casual smartphone selfie backstage in the wings of a provincial theatre: the younger man holds the phone (out of frame) and smiles widely; the older man stands next to him with his arm around the younger man's shoulders, grinning with all his teeth, eyebrows raised. The younger man wears a plain grey sweater, the older man a dark T-shirt. Behind them: black curtains, a strip of warm stage light, ropes and a lighting stand out of focus. Warm light, light phone-camera grain. Square 1:1. No costumes, no badges, no headphones, no text. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### VK-02. `media/krug-volkov/02.jpg` — спортзал, 04.10 (жизнь)

- **Приложить:** 1 — `portraits/volkov.jpg`.

```text
Use image 1 as the strict identity reference: the same real young man, keep exactly his face, short dark hair and clean-shaven face; he looks exactly 31 years old, not older. Casual mirror selfie in a small city gym after a workout: he stands in a plain dark-grey T-shirt and black training shorts, slightly sweaty, giving a thumbs-up with his free hand and a tired cheerful smile; the phone in his other hand is seen from the back, plain, no logo. Behind him: racks of dumbbells, a squat rack, rubber floor, fluorescent light. Vertical 4:5. No text on the walls or clothes, no logos on equipment, no headphones, no watch. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### VK-03. `media/krug-volkov/03.jpg` — ведущий юбилея, 25.10 (жизнь)

- **Приложить:** 1 — `portraits/volkov.jpg`.

```text
Use image 1 as the strict identity reference: the same real young man, keep exactly his face, short dark hair and clean-shaven face; he looks exactly 31 years old, not older. Lively smartphone photo at an anniversary party in a banquet hall: he is the host, in a dark-blue suit and white shirt without a tie, holding a handheld microphone and laughing, arm stretched towards the guests; behind him guests at round tables raise their hands and clap, all guests out of focus with faces not distinguishable; an elderly man with an accordion sits at the side, blurred. Warm string lights, balloons in pastel colours, garlands. Horizontal 4:3. NO banners, NO letters or numbers on balloons, no text anywhere. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

### `krug-levin` — Лёвин (принята 21.10, без улик)

Манера: «Я вам как артист скажу», путает авторов («Маскарад» — это Чехов). Жизнь: пёс, ремонт, дача.

#### LV-01. `media/krug-levin/01.jpg` — кабачки, пост 12.10 (жизнь)

Пост `2026-10-12T17:25`: «Дача закрыта. Шланги свёрнуты, кабачки раздарены всем, кто не успел спрятаться 🥒». Лица нет.

```text
Casual smartphone photo on the wooden porch of a small Russian dacha in mid-October: a wooden crate overflowing with huge green and striped zucchini, a man's hands (only hands and forearms in a dark-green coat sleeve, no face) holding up the biggest zucchini towards the camera as a trophy; a coiled green garden hose and a pair of rubber boots on the porch; yellow birches and a grey sky behind. Soft overcast light, light phone-camera grain. Vertical 4:5. No labels, no text. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

### `gromov` — Громова

`gromov/meeting.jpg` (УЛИКА, летняя зелень за окном) и `gromov/cover.jpg` уже есть. Новые — к существующим постам и к одному личному.

#### GR-01. `media/gromov/01.jpg` — субботник, к посту 10.10

- **Приложить:** 1 — `portraits/gromov.jpg`.

```text
Use image 1 as the strict identity reference: the same real woman, keep exactly her face shape, eyes, eyebrows, nose, mouth, skin tone, hairline and hairstyle; she looks exactly 45 years old, not older. Press-style but lively smartphone photo at a city clean-up day on a river embankment in October: she holds a young linden sapling upright while a volunteer (out of focus, face not visible) shovels earth around it; she wears a dark quilted jacket, jeans and simple work gloves, and gives an instruction with her free hand, smiling. In the background: a row of freshly planted saplings, volunteers with rakes from behind, grey river. Overcast daylight. Horizontal 4:3. No flags, no banners, no logos on clothes, no text. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### GR-02. `media/gromov/02.jpg` — чаепитие с ветеранами, к посту 24.10

Пасхалка к комментарию «а это у вас на скатерти что, вишнёвое?» — маленькое пятно варенья у её чашки.

- **Приложить:** 1 — `portraits/gromov.jpg`.

```text
Use image 1 as the strict identity reference: the same real woman, keep exactly her face, hairline and hairstyle; she looks exactly 45 years old, not older. Warm smartphone photo in the hall of a district house of culture: she sits at a long table covered with a white tablecloth among elderly people (all of them seen from the side or out of focus, faces not distinguishable), pouring tea from a big teapot, laughing. On the table: plates of homemade pies, jars of cherry jam, cups; next to her cup there is a small round dark-red jam stain on the white tablecloth. She wears a burgundy blouse. Soft warm indoor light. Horizontal 4:3. No flags, no portraits on the walls, no banners, no text. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

#### GR-03. `media/gromov/03.jpg` — дача и шарлотка, личный пост 01.11

Пост `2026-11-01T13:20` в её манере: «Выходной !!! Дача, последние яблоки, шарлотка ❤️❤️❤️ / Все на свежий воздух. Это приказ» (CLUE-MAP 3.8). Ещё два личных поста без фото: 25.10 «Первый раз за месяц дома до восьми. Кот в шоке. Я тоже 🤣🤣» и 18.10 «Минус два. Город, где шапки ?…».

- **Приложить:** 1 — `portraits/gromov.jpg`.

```text
Use image 1 as the strict identity reference: the same real woman, keep exactly her face, hairline and hairstyle; she looks exactly 45 years old, not older. Casual smartphone selfie in a small dacha garden on a cold sunny November day: she holds up a freshly baked apple charlotte pie in a baking dish towards the camera with a triumphant face, wearing a knitted cream sweater and a quilted vest, hair in a loose ponytail. Behind her: a wooden garden table with a basket of red apples, a bare apple tree, a simple wooden house. Bright low sun, light phone-camera grain. Vertical 4:5. No jewellery, no badges, no text. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

### `inna` — Инна (IN-10 внесён 21.10 — пост 09.11 17:30)

#### IN-10. `media/inna/10.jpg` — буфет перед генеральным прогоном, 09.11, костюм с брошью на вешалке — подкрепление бонуса s2.b2

Пост `2026-11-09T17:30`: «Генеральный прогон 🎭 Буфет готов, костюмы красивые — я бы сама всё надела ✨» Брошь должна **точно** совпадать с 2-08 и с `inna/brooch.jpg`. Опись 2-08: сверка 09.11 после генерального прогона — «все позиции в наличии», т. е. брошь ещё на костюме.

- **Приложить:** 1 — `work/brooch_ref.jpg` (рабочий эталон броши, `PROMPTS.md` S04); 2 — `inna/brooch.jpg`.

```text
Image 1 and image 2 are the strict reference for the BROOCH only: oval, antique-silver-coloured metal, a large green glass stone in the centre, two rows of small clear rhinestones around the edge, a small drop-shaped pendant at the bottom - copy it exactly. Casual smartphone photo of a small theatre buffet before a dress rehearsal: in the foreground the counter with a coffee machine, cups and a tray of pastries; behind the counter, near the service door to the backstage, a costume rack with one 19th-century lady's dress of dark-green velvet on a hanger, and on the bodice of this dress the brooch from the references is pinned, clearly visible but not in the centre of the frame. No people. Warm buffet light. Square 1:1. No text, no signs, no price tags. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: брошь та же (форма, камень, стразы, капля), платье на вешалке, людей нет.

### `news-most` — новость про мост (принята 21.10, вариант А)

#### NM-01. `media/news-most/01.jpg` — Речной мост вечером

```text
Local news photograph of an old concrete road bridge across a wide river in a provincial city at dusk in early November: a steady line of car headlights and red tail lights on the bridge, the left bank with a church-free old town skyline and warm windows, the right bank with five-storey residential buildings and a straight street going away from the bridge, street lamps reflecting in the dark water, overcast sky. Seen from the embankment. No readable signs, no road signs with text, no number plates, no traffic cameras. Horizontal 3:2. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь: камер на мосту не видно (иначе вопрос «почему не запросили»).

---

## 2а. Бумага: перегенерация `media/paper/2-06-office.jpg` (S18, решение автора 21.10)

Сейчас упаковка на столе бело-синяя и не читается даже при увеличении. По `docs/PAPER-REQUIREMENTS.md` и SCENARIO она должна читаться **только при увеличении**, без крупного плана. Сверено с `content/paper/2-06.md`: подпись «Рабочий стол, общий вид.» и текст («среди прочего: стопки документов, папка-скоросшиватель „Фонд „Сцена“: отчёт для администрации города“, ежедневник, письменный прибор, очки, настольная лампа, стационарный телефон, две чашки на блюдцах с остатками кофе, на одной — след губной помады») **не меняются**: упаковка входит в «среди прочего». Надпись на папке, как и раньше, накладывается при обработке.

- **Приложить:** 1 — текущий `paper/2-06-office.jpg` (сохранить стол, ракурс и предметы); 2 — `paper/2-06-room.jpg` (образец комнаты).
- **Формат:** горизонталь 3:2, как сейчас.

```text
Image 1 is the current version of this photo: keep the same office, the same desk, the same camera angle, the same lighting and the same objects in the same places. Image 2 is only a reference for the room. A general view of the whole writing desk surface from the visitor's side, slightly raised angle, the whole desk in frame (NOT a close-up). On the desk: stacks of documents; a black ring-binder folder lying on top with a blank white label sticker on its front (leave the label COMPLETELY BLANK, no letters); a diary; a desk pen set; reading glasses; a desk lamp; a landline desk telephone; TWO coffee cups on saucers, both with coffee dregs, and a faint red lipstick mark on the rim of one of them. CHANGE ONLY THIS: among the papers next to the telephone lies one small white medicine box with a thin blue stripe, half covered by a sheet of paper; on its visible side the word АНАПРИЛИН is printed in plain dark-blue Cyrillic capital letters. The box is small, not in the foreground and not in the centre: the word must be readable only when the photo is zoomed in. No other text anywhere in the picture: no other letters on the box, no manufacturer logo, no dosage, no captions, no timestamps, no watermarks, no brand names, no coats of arms, no flags, no readable signs. No blood pressure monitor, no pill blister on the desk. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Проверь перед сохранением:
- [ ] всё, что перечислено в 2-06, на месте: папка с пустой этикеткой, **две** чашки на блюдцах, **след помады на одной**, ежедневник, письменный прибор, очки, лампа, стационарный телефон;
- [ ] упаковка маленькая, наполовину под листом, слово «АНАПРИЛИН» читается только при увеличении, других букв на ней нет;
- [ ] ракурс и стол те же, что на старом кадре (фото уже описано в бумаге — «общий вид»).

Если генератор коверкает кириллицу: сгенерировать с **пустой** белой стороной коробки и наложить слово «АНАПРИЛИН» при обработке (PT Sans Bold, тёмно-синий, высота букв ≈ 1 % ширины кадра, лёгкий перспективный наклон под грань коробки) — так же, как надпись на папке.

---

## 3. Голосовые

Решение автора: немного голосовых (5 на всю сеть), голос — нейросетью по клонам из уже существующих голосовых, как запись звонка. Живых записей нет. **Голосовых у Кирилла нет** (решение 21.10). Голосовые бывают только у постов: у комментариев поля `audio` нет, поэтому голосовое Вольской перенесено в её пост 01.11.

**Технически:** MP3, моно, 64–96 кбит/с, громкость около −16 LUFS, лёгкий «телефонный» фон (комната, улица), без музыки. Файл ≤ 300 КБ. Длительность — по таблице ±2 с; поле `duration` в YAML ставится по факту.

**Имена в речи.** Дружеское имя погибшего и имена подруг звучат вслух — для семейной версии это «Тёма» и настоящие имена. Для продажи голосовые переозвучиваются вместе со сменой `characters.yaml`.

| № | Файл | Где | Чей голос | ~Длит. | Текст (произносится) | Тон | Улика? |
|---|---|---|---|---|---|---|---|
| V1 | `media/krug-voroncov/voice-01.mp3` | пост 31.10 10:12 (селфи VR-03) | Молдованов / Воронцов (клон автора) | 16 с | «Вчера полдня бродил по городу. Погода — арбенинская: ветер, тучи, сплошная драма. И всё время казалось, что кто-то идёт следом. Оборачиваюсь — никого. Мнительность у артистов, видимо, прилагается к роли бесплатно». В конце короткий смешок | весело, но с лёгкой паузой перед «кто-то идёт следом» | спящая: слежка 30.10 ↔ 4-08 |
| V2 | `media/krug-marina/voice-01.mp3` | пост 10.11 17:12 («премьера!! 🤞») | Марина | 14 с | «Так, всем приветик! Дядя Тёма сегодня играет премьеру! Я не иду — мне сказали приходить, когда он разыграется. Так что держу кулачки дома, прям вот так. Всё, удачи ему!» | радостно, быстро | нет (её собственные слова; алиби подтверждает сестра, 1-08) |
| V3 | `media/krug-marina/voice-02.mp3` | пост 31.10 18:26 (Хэллоуин, фото MR-01) | Марина | 18 с | «Короче, у меня в группе Хэллоуин, и одна девочка пришла в костюме… меня. С журналом и в очках. Я прям не знаю — гордиться или бояться. Наверное, и то и другое». Смех | смешливо | нет |
| V4 | `media/krug-volskaya/voice-01.mp3` | пост 01.11 17:15 (пирог) | Вольская | 9 с | «Девочки, ну вот — пирог с брусникой, бабушкин рецепт. Жду вас в следующее воскресенье, всех-всех. Не опаздывайте, а то съем сама» | тепло, с улыбкой | нет |
| V5 | `media/krug-volkov/voice-01.mp3` | пост 14.10 19:05 «Ведущий на ваш праздник — голосом…» | Волков | 15 с | «Всем привет! Свадьбы, юбилеи, корпоративы — проведу так, что гости забудут, что пришли по приглашению. Музыка, конкурсы — всё своё. Пишите, договоримся. Хорошего вечера!» | быстро, вежливо, улыбаясь | нет; тот же голос, что в видео 4-07 |

«Было бы за что» нет ни в одном голосовом. В голосовых нет дат, времени, болезней, лекарств, поездок и денег театра.

**Поле в `content/`** (схему добавил фронтенд; плеер — тот же, что на странице `call`). Расшифровки в `content/` — с шаблонами имён и пола; «Тёма» звучит как `familiar`:

```yaml
posts:
  - datetime: "2026-10-31T10:12"
    text: "…"                              # может быть пустым: пост — только голосовое
    audio:
      file: "krug-voroncov/voice-01.mp3"   # путь в media/
      duration: "0:16"
      transcript: "…"                      # необязательно; кнопка «Показать расшифровку», свёрнуто
    comments:
      - { author: "…", page: "…", text: "…" }   # у комментариев голосовых нет
```

Расшифровка — открытый текст страницы: к ней применимы правила `CLUE-MAP` 3.0 (никаких иголок leak scan).

---

## 4. «Кружки»: что убрано и что осталось

Решение автора 21.10: видеосообщений («кружков») в игре нет — нигде не упоминать и не изображать; Марина «любит голосовые».

| Файл | Что сделано 21.10 (вечер) |
|---|---|
| `content/pages/krug-marina/page.yaml` | шапка, `about` («голосовые > текст»), пост 11.11 («даже голосовое не получается записать»), 10.11 и 31.10 — голосовые V2 и V3, 18.10 и 29.09 — текстом |
| `docs/drafts/pages/krug-marina/page.yaml` | заменён копией из `content/` |
| `docs/REDESIGN-2026-10.md`, строка 171 | «текст и голосовые» |
| **Осталось оркестратору** (эти файлы сценарист при параллельной работе не трогает): `docs/VOICES.md` строки 16 («любит кружки и голосовые») и 82 («голосовые и видеокружки»); `docs/STORY-CHANGES.md` строка 476 (старая запись «посты-„кружки“» — историю не переписываем, замена отмечена в записи 21.10 вечер) | |

«Драмкружок» и «театральный кружок» у Кирилла, «кружки» с чаем (KR-03, SCENARIO 2-06) — не видео, оставлены.

---

## 5. Соответствие старым номерам из `PHOTOS.md`

| Было | Стало |
|---|---|
| F03 `krug/kirill_cat.jpg` | KR-05 `media/krug-kirill/05.jpg` (запрос тот же) |
| F04 `krug/voroncov_rehearsal.jpg` | VR-05 `media/krug-voroncov/05.jpg` (запрос уточнён: без сумок и бутылок) |
| F01, F02, F05–F08 | без изменений: `theater/facade.jpg`, `theater/hall.jpg`, `fund/costumes.jpg`, `news/yama.jpg`, `news/hockey.jpg`, `auction/snuffbox_lot.jpg` |

**Итого в наборе 2:** 8 аватаров (AV-1…AV-8), 5 обложек (CV-2…CV-5, CV-7), 23 фото к постам (VR-01…05, KR-01…05, MR-01…02, VS-01…03, VK-01…03, LV-01, GR-01…03, IN-10, NM-01), 1 перегенерация бумаги (2-06-office), 5 голосовых (V1–V5).

---

## 6. Итоговый список файлов

Все пути — от `media/`. «Улика» — кадр или запись, на которых держится рассуждение (CLUE-MAP); «спящая» — смысл понятен только с бумагой поздних этапов; «нет» — жизнь страницы. Промпт — по коду в этом файле (S18 — `docs/PROMPTS.md`, новая версия — раздел 2а).

| Файл | Страница, где стоит | Улика? | Промпт |
|---|---|---|---|
| `gromov/avatar.jpg` | `gromov`, профиль | нет | AV-1 |
| `gromov/01.jpg` | `gromov`, пост 10.10 (субботник) | нет | GR-01 |
| `gromov/02.jpg` | `gromov`, пост 24.10 (чаепитие; пятно варенья — пасхалка к комментарию) | нет | GR-02 |
| `gromov/03.jpg` | `gromov`, пост 01.11 (дача, шарлотка) | нет | GR-03 |
| `krug-voroncov/avatar.jpg` | `krug-voroncov`, профиль | нет | AV-2 |
| `krug-voroncov/cover.jpg` | `krug-voroncov`, обложка | нет | CV-2 |
| `krug-voroncov/01.jpg` | `krug-voroncov`, пост 11.10 (дача) | нет | VR-01 |
| `krug-voroncov/02.jpg` | `krug-voroncov`, пост 28.10 15:52 (гримёрка) | **улика** — бонус fb3, f1 | VR-02 |
| `krug-voroncov/03.jpg` | `krug-voroncov`, пост 31.10 10:12 (селфи) | **спящая** — силуэт из 4-08 | VR-03 |
| `krug-voroncov/04.jpg` | `krug-voroncov`, пост 02.11 (борщ) | нет | VR-04 |
| `krug-voroncov/05.jpg` | `krug-voroncov`, пост 06.11 (прогон) | нет | VR-05 |
| `krug-voroncov/voice-01.mp3` | `krug-voroncov`, пост 31.10 | **спящая** — «кто-то идёт следом» | V1 |
| `krug-kirill/avatar.jpg` | `krug-kirill`, профиль | нет | AV-3 |
| `krug-kirill/cover.jpg` | `krug-kirill`, обложка | нет | CV-3 |
| `krug-kirill/01.jpg` | `krug-kirill`, пост 04.10 (рыбалка) | нет | KR-01 |
| `krug-kirill/02.jpg` | `krug-kirill`, пост 17.10 (встреча одноклассников) | нет | KR-02 |
| `krug-kirill/03.jpg` | `krug-kirill`, пост 20.10 (ноутбук, две кружки) | фон спящего поста (сам кадр без улики) | KR-03 |
| `krug-kirill/04.jpg` | `krug-kirill`, пост 26.10 (мамин телефон) | нет | KR-04 |
| `krug-kirill/05.jpg` | `krug-kirill`, пост 07.11 (кот) | нет | KR-05 (= F03) |
| `krug-marina/avatar.jpg` | `krug-marina`, профиль | нет | AV-4 |
| `krug-marina/cover.jpg` | `krug-marina`, обложка | нет | CV-4 |
| `krug-marina/01.jpg` | `krug-marina`, пост 31.10 (Хэллоуин) | нет | MR-01 |
| `krug-marina/02.jpg` | `krug-marina`, пост 03.11 (две чашки) | нет (эхо 4-14) | MR-02 |
| `krug-marina/voice-01.mp3` | `krug-marina`, пост 10.11 17:12 | нет | V2 |
| `krug-marina/voice-02.mp3` | `krug-marina`, пост 31.10 18:26 | нет | V3 |
| `krug-volskaya/avatar.jpg` | `krug-volskaya`, профиль | нет | AV-5 |
| `krug-volskaya/cover.jpg` | `krug-volskaya`, обложка | нет | CV-5 |
| `krug-volskaya/01.jpg` | `krug-volskaya`, пост 10.10 (выставка) | нет | VS-01 |
| `krug-volskaya/02.jpg` | `krug-volskaya`, пост 24.10 (концерт студии) | нет | VS-02 |
| `krug-volskaya/03.jpg` | `krug-volskaya`, пост 01.11 (пирог) | нет | VS-03 |
| `krug-volskaya/voice-01.mp3` | `krug-volskaya`, пост 01.11 | нет | V4 |
| `krug-volkov/avatar.jpg` | `krug-volkov`, профиль | нет (серый свитер, не куртка) | AV-7 |
| `krug-volkov/cover.jpg` | `krug-volkov`, обложка | нет | CV-7 |
| `krug-volkov/01.jpg` | `krug-volkov`, пост 21.09 (с погибшим за кулисами) | нет | VK-01 |
| `krug-volkov/02.jpg` | `krug-volkov`, пост 04.10 (спортзал) | нет | VK-02 |
| `krug-volkov/03.jpg` | `krug-volkov`, пост 25.10 (юбилей; под ним комментарий кредитора) | нет (улика — комментарий, не кадр) | VK-03 |
| `krug-volkov/voice-01.mp3` | `krug-volkov`, пост 14.10 | нет (тот же голос, что в видео 4-07) | V5 |
| `krug-levin/avatar.jpg` | `krug-levin`, профиль | нет | AV-8 |
| `krug-levin/01.jpg` | `krug-levin`, пост 12.10 (кабачки) | нет | LV-01 |
| `inna/avatar.jpg` | `inna`, профиль | нет (**без броши**) | AV-6 |
| `inna/10.jpg` | `inna`, пост 09.11 17:30 (костюм с брошью у буфета) | **подкрепление** бонуса s2.b2 | IN-10 |
| `news-most/01.jpg` | `news-most`, фото статьи | нет (без камер на мосту) | NM-01 |
| `paper/2-06-office.jpg` | бумага 2-06, кадр 2 (перегенерация) | **улика-деталь** — упаковка «Анаприлина» (f2, f3) | раздел 2а (S18 v2) |

Не из набора 2, но сборка тоже пишет «нет медиафайла»: `inna/01.jpg`…`09.jpg` (S20–S28), `portraits/gnedich.jpg`, `portraits/zavyalov.jpg`, `video/rehearsal.mp4`.
