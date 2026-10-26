# Производство медиа: что осталось

**Актуально на 25.10.2026.** Готово 124 из 134 позиций, отменено 9, **осталась 1: `VD-4`** (добавлена 25.10 по решению автора об архивной камере). Как пользоваться: пишете в чат **«готово КОД»** (например, «готово GV-1») или **«переделать КОД: причина»**; режиссёр кладёт файл в `media/`, сверяет и ставит ✅. Проверка: `python -m engine build 2>&1 | grep "нет медиафайла"` должно стать пустым. Сюжет кадров — `docs/SCENARIO.md` и `content/`; если что-то расходится, прав сценарий. Образцы лиц и голосов в репозиторий не кладутся (`media/_refs/` в `.gitignore`).

> **Правила автора.** Никаких живых съёмок и записей: лица — по готовым портретам `media/portraits/<id>.jpg`, голоса — клоны по существующим голосовым. Реальные товары и интерфейсы, случайно попавшие в бытовые кадры (телефон, ноутбук, наушники, конфеты), не замазываем (решение 23.10, семейная версия). Сервисы игры остаются вымышленными, логотипов и вывесок нет.

---

## 1. Кто есть кто

Люди называются так, как их зовёт автор, роль в игре — в скобках. Коды файлов и пути (`krug-volkov`, `voroncov.jpg`) остаются по ролям. Источник — `content/characters.yaml` и `docs/VOICES.md`.

| Как зовём | ФИО (в игре) | Роль (рабочее имя, id) |
|---|---|---|
| Артём (автор) | Молдованов Артём Сергеевич, дружеское «Тёма» | погибший народный артист, Арбенин (Воронцов, `voroncov`) |
| дедушка Коля | Тарасов Николай Валентинович | худрук, председатель фонда (Завьялов, `zavyalov`) |
| Слава | Блинов Вячеслав Сергеевич | дублёр Арбенина (Волков, `volkov`) — **не Артём** |
| Алина | Горенкова Алина Александровна | крестница погибшего, дочь Кирилла (Марина, `marina`) |
| дядя Саша | Горенков Александр Сергеевич | друг погибшего, отец Алины (Кирилл, `kirill`) |
| Лёвин | Лёвин Сергей Николаевич | актёр, Звездич (Стас Лёвин, `stas`) |
| мама | Резникова Наталья Сергеевна | помреж (Резникова, `reznikova`) |
| бабушка | Гнедич Галина Сергеевна | заведующая костюмерным цехом (Гнедич, `gnedich`) |
| Антон | Кузнецов Антон Александрович | художник по свету (Виктор «Мастер», `viktor`) |
| Алексей | Лемонов Алексей Иванович | охранник служебного входа (Олег Петрович, `oleg`) |
| Светлана Рябова | Рябова Светлана Витальевна | буфетчица (Инна, `inna`) |
| Дарья | Горохова Дарья Николаевна | водитель погибшего (Дмитрий, `dmitriy`) |
| тётя Света | Вольская Светлана Николаевна | меценат (Софья Вольская, `volskaya`) |
| сестра Юля | Громова Юлия Сергеевна | чиновница (Михаил Громов, `gromov`) |

---

## 2. Осталось сделать

Проверено сборкой 24.10: «нет медиафайла» про 9 файлов. Постеры видео (`video-01.jpg`) режиссёр вырезает из готового ролика сам.

| Код | Файл | Что | Где на сайте | Инструмент | Статус |
|---|---|---|---|---|---|
| `VD-4` | `video/archive-cam.mp4` + постер `video/archive-cam.jpg` | Архивная запись спектакля, момент падения: общий план сцены, 6–10 с, без голосов | начало игры (`TODO(content)`: путь пока нигде не прописан) | Gemini (кадр-основа) → Kling image-to-video → режиссёр (ffmpeg) | ⏳ промпты готовы (§4.2) |

`VD-4` не улика, но кадр обязан сходиться с документами по времени, месту, костюму и свету (§4.2).

**Что нужно от автора:** клоны дяди Саши и Алины уже есть (для `VD-3` Саша говорит обычным голосом, без маскировки звонка); для `VD-1` — клон мамы (Резникова) уже использован в голосовых; для видео — проба Kling Avatar («говорящее фото») на бесплатных кредитах до оплаты, поддержка 9:16.

---

## 3. Общие правила для этих позиций

- **Gemini (фото и кадры-основы).** Каждый кадр — новый чат. Образцы лиц прикладываются до запроса, портрет — первым; до 3 образцов за запрос. Возраст строго по `characters.yaml`. Неудача: не переписывать запрос, а править в том же чате коротким `Same image, but …` (лицо не похоже: `Same image, but make the face match the reference photos exactly (same eyes, nose, mouth, face shape and hairline); keep the framing, light, age and clothes unchanged.`). Скачивать полный размер (не скриншот); надписи, таймкоды, рамки и обрезку не добавлять, это делает режиссёр. Неудачные варианты не удалять до проверки.
- **Ни на ком в кадре:** короткой тёмной куртки (примета на VR-03 и 4-08), брошей, шалей, длинных перчаток и украшений (пропажи 2-08), лекарств, таблетниц, ингаляторов, телефонов с экраном. Детям лиц не рисуем.
- **Общий «хвост»** уже вписан в каждый запрос ниже: `Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.`
- **Файлы.** Фото и портреты: JPEG (или WebP). Портрет: 4:5, чисто белый фон, ≥ 800 px по короткой стороне. Видео в «Круге»: вертикаль 9:16, 720 × 1280, MP4 H.264 + AAC, ≤ 8 МБ (общий предел игры ≤ 25 МБ), звук ≈ −16 LUFS; сжатие, звук и постер делает режиссёр. Голосовые: присылать MP3 как есть, 2–3 дубля на реплику, имя файла — код (`GV-1_take2.mp3`); режиссёр приводит к формату игры (моно, 64–96 кбит/с, ≈ −16 LUFS, ≤ 300 КБ, лёгкий фон места, без музыки).
- **Деньги и подписки.** Цены и тарифы — `docs/MEDIA-AI-OPTIONS.md`, проверять на сайтах перед оплатой. ElevenLabs Starter и Kling Standard — помесячные, с автопродлением: после работы отменить. Запасной вариант для видео — Hedra («фото + голос»).

---

## 4. Промпты и тексты

### 4.1. Два видео в соцсеть: `VD-1`, `VD-3`

**Решение автора 23.10: каждый ролик ≈ 5 секунд, одна генерация Kling, без склеек.** Губы двигаются только у одного человека (он в кадре, лицо — по готовому портрету), второй — голос за кадром или стоит спиной. Голос за кадром синхронизировать с губами не надо: это готовая дорожка ElevenLabs, которую режиссёр кладёт поверх. Голосов Лёвина и Артёма в роликах нет. В кадрах нет таблеток, таблетниц, ингаляторов, лекарств, сумок, телефонов с экранами, чашек на столах гримёрок, номеров на дверях, часов, надписей и логотипов; гримёрка № 4 не показывается. Улик в роликах нет.

**Порядок для каждого ролика** (одна генерация):

1. **Gemini:** один кадр-основа 9:16; одно узнаваемое лицо — того, кто говорит «в камеру».
2. **ElevenLabs:** каждая реплика отдельным коротким файлом (`VD3_02_kirill.mp3`), 2–3 дубля, в том числе реплики за кадром.
3. **Режиссёр** собирает две дорожки по 5,0 с: «для Kling» (только реплики того, кто в кадре, на своих таймкодах, между ними тишина) и общую (все голоса и лёгкий фон). Вам присылает первую.
4. **Kling:** «говорящее фото» (Avatar): кадр + дорожка «для Kling» = одна генерация, 5 с; 2–3 попытки. Убедиться, что на скачиваемом файле нет водяного знака; русскую речь делает ElevenLabs, а не Kling.
5. **Режиссёр:** кладёт общую дорожку вместо звука Kling, сжимает, вырезает постер.

Голоса: мама — Резникова (клон из §4.1), Алина — Марина (клон уже есть), дядя Саша — Кирилл (обычный голос, без маскировки звонка). Антону (Кузнецов Антон Александрович, роль Виктора «Мастера») клон не нужен: его единственная реплика звучит из аппаратной, спиной к камере, на 1 секунду — подойдёт любой готовый низкий мужской голос ElevenLabs.

#### VD-1. «Закулисье, серия первая: помреж и свет» — `krug-levin/video-01.mp4`, 0:05

Пост `krug-levin`, 02.11.2026 16:44. Губы двигаются **только у Резниковой** (мама; Резникова Наталья Сергеевна, роль помрежа) — в дверях аппаратной, в кадре. Антон (Кузнецов, роль Виктора «Мастера») у пульта спиной, его реплика — голос. Лёвин (Лёвин Сергей Николаевич, роль актёра Лёвина) снимает за кадром и **молчит**: голоса Лёвина не будет (23.10).

| Секунды | Кто | Реплика | Что в кадре |
|---|---|---|---|
| 0,0–2,2 | Резникова (в кадре, говорит в сторону Антона) | «Антон, луч на Нину — опять позже.» | Резникова в дверях аппаратной с папкой и карандашом, смотрит на Антона |
| 2,5–3,6 | Антон — Виктор (голос, не поднимая головы; губ не видно) | «Свет не врёт.» | Антон у пульта, к камере затылком и плечом; не оборачивается |
| 3,8–4,9 | Резникова (в камеру) | «Я записала.» | постукивает карандашом по папке и смотрит прямо в объектив |
| 4,9–5,0 | — | — | камера чуть дёргается, обрыв (без смешка) |

Шутка: «Свет не врёт» (девиз Антона — роль Виктора) против «У меня всё записано» (девиз Резниковой). Комментарии под постом («Луч на меня — это святое», «Свет мой. Снято нормально.») на месте. Дорожка «для Kling»: реплика 1 на 0,0–2,2 и реплика 3 на 3,8–4,9, между ними тишина.

Кадр-основа (Gemini; приложить `portraits/reznikova.jpg` как image 1 и `portraits/viktor.jpg` как image 2 — лицо Антона в кадре не видно, образец нужен только для сложения, плеч и причёски сзади):

```text
Image 1 is the strict identity reference for the woman; image 2 is the reference for the man's build, hair and the back of his head (his face is not visible). Vertical 9:16 smartphone video frame, handheld, slightly tilted. Inside a small lighting control booth of a provincial theatre, afternoon. In the foreground at the right, a man of about 50 (looks like image 2) sits at a lighting console with rows of faders and small coloured indicator lamps, seen from behind in three-quarter view: we see his shoulder, ear and the back of his head, his face turned toward the console and the dark glass window that looks down into the empty auditorium. In the doorway at the left stands a woman of about 47 (identity from image 1), neat, reading glasses on a cord, holding a cardboard folder and a pencil, looking at him with a strict but amused expression, mouth closed, her face clearly visible, sharp and recognisable. Warm dim booth light, cables, a desk lamp over the console. No screens with readable text, no clocks, no cups, no bags. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Kling (одна генерация, 5 с; кадр + дорожка «только Резникова»):

```text
Handheld phone video, slight natural sway. The woman in the doorway speaks with clear lip movement in sync with the audio; in the silent pause she looks at the man with a raised eyebrow and her mouth stays closed; then she speaks again, taps the pencil on the folder and looks into the camera. The man at the console never turns his face to the camera and barely moves. No cuts.
```

Если Kling шевелит губами и в паузе — повторить генерацию. **Запасной вариант:** Антон молчит, поднимает палец («свет не врёт»); Резникова после паузы говорит вторую реплику.

#### VD-3. Дача крёстного, яблоки — `krug-marina/video-01.mp4`, 0:05

Пост `krug-marina`, 13.10.2026 12:47. В кадре **одна Алина** (Горенкова Алина Александровна, роль Марины, крестницы) — селфи, губы двигаются только у неё. За кадром — **Саша** (Горенков Александр Сергеевич, роль Кирилла, её отца): стоит рядом с телефоном, его в кадре нет, только голос. **Голоса Артёма (роль крёстного Артёма) нет** (решение автора 23.10). Сюжетно: Саша заехал на дачу к обеду за ведром яблок для бабушки — сходится с ответом крёстного под его постом 13.10 «ведро у тебя в багажнике с обеда» и с вопросом Саши там же «Яблоки где? Я спрашиваю для мамы....».

| Секунды | Кто | Реплика | Что в кадре |
|---|---|---|---|
| 0,0–1,6 | Алина (в камеру) | «Одно?! А ведро кому?» | Алина с одним красным яблоком у камеры, за ней на крыльце полное ведро яблок; возмущённая улыбка |
| 1,8–3,7 | Саша (за кадром, со смешком) | «Бабушке. Я только водитель.» | Алина поворачивает голову на его голос, рот закрыт |
| 3,9–5,0 | Алина | смех: «Ахаха» | трясёт яблоком перед камерой, обрыв |

Дорожка «для Kling»: реплика Алины на 0,0–1,6 и смех на 3,9–5,0, между ними тишина. Реплика Саши — клон из шага 2, **обычный голос, без маскировки** (как `KV-1`, `KV-2`), 1,5–2 с, **синхронизировать не надо**; в ней нет «спасибо», «Было бы за что» и слов звонка 1-05. Тон — балагур, шутит над собой. Кардиган горчичный — как на фото облака `X03c` (тот же день, 13.10). Подпись поста («угадайте, сколько досталось мне»), комментарий крёстного («самое красивое, между прочим)») и комментарий Саши («Ведро у меня!!!!! Водитель тоже человек 😂») сходятся: яблоко одно, ведро — бабушке, везёт Саша.

Кадр-основа (Gemini; приложить `portraits/marina.jpg`):

```text
Image 1 is the strict identity reference for the young woman. Vertical 9:16 smartphone selfie video frame, handheld at arm's length. A country dacha garden in mid-October around noon, overcast soft daylight, yellow leaves, an old wooden porch and an apple tree behind. In the foreground a young woman of about 24 (identity from image 1), hair loose, a warm mustard-yellow knitted cardigan, smiling with her mouth closed, holding one red apple in her free hand close to the camera. Behind her on the porch step stands a full enamel bucket of red apples. Nobody else is in the frame. No children, no cars, no other people. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Kling (одна генерация, 5 с; кадр + дорожка «только Алина»):

```text
Handheld selfie video with slight sway. The young woman looks at the apple in her hand, then at the camera with an indignant smile and speaks in sync with the audio; then, with her mouth closed, she turns her head to the side as if listening to someone standing next to the phone; at the end she laughs, waving the apple in front of the camera. Nobody else appears. Natural daylight stays constant.
```

**Запасной вариант:** если Алина в кадре «ломается» на повороте головы — пусть смотрит в камеру весь ролик; поворот на голос Саши не обязателен. Если Kling шевелит губами в паузе (пока говорит Саша) — повторить генерацию.

Итого на два ролика: 2 кадра Gemini (1–2 попытки), 6 коротких реплик ElevenLabs (четыре в кадре: Резникова ×2, Алина ×2 с учётом смеха; две за кадром: Антон, Саша), 2–3 генерации Kling по 5 с на ролик.

### 4.2. Архивная запись спектакля: `VD-4`

**Решение автора 25.10:** в театре есть архивная камера видеозаписи спектаклей. Она стоит в зале, на балконе, и снимает только сцену: зал и ложи в кадр не попадают. Игра начинается с фрагмента этой записи (6–10 с): общий план сцены во втором действии, артист в костюме Арбенина у левой кулисы покачнулся и упал. Голосов в ролике нет: либо «запись без звука», либо только глухой шум зала. Лицо — по портрету погибшего (Артём, роль Воронцова). Видео автор делает сам в Kling (image-to-video), доводку делает режиссёр.

#### VD-4. «Архивная запись спектакля, момент падения» — `video/archive-cam.mp4` + постер `video/archive-cam.jpg`

**С чем кадр обязан сходиться** (сверено с `content/`):

| Что | Как в документах | Что это значит для кадра |
|---|---|---|
| Время | 2-05: «21:02 СТОП… упал (авансцена, у лев. кулисы). Полный свет. Занавес»; 2-07: 21:02:24 сигнал «СТОП», 21:02:31 аварийный полный свет; 3-01 и 1-08 (Резникова): «в 21:02 упал». В 21:04 только вызвали скорую (1-03, 2-05) | Таймкод **21:02:xx**, а не 21:04. Ролик кончается до 21:02:24, поэтому свет в нём весь ролик ровный, сценический. Полного света, занавеса и людей у тела в ролике нет |
| Место | 2-05, 1-08: авансцена, у левой кулисы; 1-03: «сцена, у левой кулисы, на полу», ингалятор «на полу кулисы» | Падает у самого края левой кулисы, на передней части сцены, не в центре |
| Сцена | 2-05, 2-07: 2-е действие, К. 6 «Бал», с 20:57:47 свет Q24 «бал, центр»; Резникова: «полтруппы на сцене» | За ним в глубине пары в бальных костюмах; центр сцены светлее, у левой кулисы свет мягче |
| Костюм | 1-09, поз. 4: костюм 1-го действия (фрак, жилет, сорочка) остался в гримёрке; на теле — костюм 2-го действия (`expertise.yaml`); комплект Арбенина — сюртук (4-09) | Чёрный сюртук XIX века, тёмный жилет, белая сорочка с высоким воротником, тёмный шейный платок (как на `news/voroncov_arbenin.jpg`). Очков на сцене нет: они лежали в сумке (1-09, поз. 17.1) |
| Состояние | 2-05, 20:56: «темп ушёл, паузы длинные, дыхание (?)»; 1-08 (Лёвин): «сбивался, дышал тяжело… сначала решил, что это он так играет» | Сначала тяжёлое дыхание и пауза, потом падение. Без крови и без судорог |
| Руки | ингалятор нашли на полу кулисы (1-03); о таблетнице в ролике речи нет | В руках ничего нет: ни ингалятора, ни таблеток, ни телефона |

**Исходный кадр.** Брать не `video/rehearsal.mp4`: в нём Слава (Волков, дублёр) в дневном репетиционном зале, а не Артём, так что лицо будет не то. Постера у `rehearsal.mp4` в `media/` нет. Берём два готовых файла:
- image 1 — `media/portraits/voroncov.jpg` (лицо, седина, борода);
- image 2 — `media/news/voroncov_arbenin.jpg` (тот же человек в костюме Арбенина, сценический свет, без очков).

По ним в **Gemini** собираем кадр-основу 16:9 (запрос ниже), и он идёт в Kling как стартовое изображение. Лицо на общем плане мелкое, поэтому главное, чтобы совпадали седина, борода, сложение и костюм. Кадр-основу в репозиторий не кладём, присылаем в чат как `VD-4_base.jpg`.

Кадр-основа (Gemini; image 1 — `portraits/voroncov.jpg`, image 2 — `news/voroncov_arbenin.jpg`):

```text
Image 1 is the strict identity reference for the man (face, grey hair, grey beard, build); image 2 shows the same man on stage in his costume: copy the costume and the stage make-up from image 2, and he wears NO glasses. Horizontal 16:9 still frame from a fixed archival video camera that records performances in a provincial drama theatre. Static wide shot of the whole stage, taken from the front of the balcony at the back of the auditorium, slightly above stage level, looking straight at the stage. Only the stage is visible: the bottom edge of the picture is the front edge of the stage floor; no auditorium, no seats, no audience, no heads, no balcony railing, no orchestra pit. A modest 19th-century ball scene: dark velvet side curtains (wings) on both sides, a dark backdrop, a few warm chandelier-like lamps, four to six performers in 19th-century ball costumes (long gowns, dark tailcoats) standing in pairs in the middle and back of the stage, small, faces indistinct. Downstage at the far LEFT of the frame, right next to the edge of the left side curtain, stands the man (identity from image 1), about 56, grey hair, grey beard, in a black 19th-century frock coat, dark waistcoat, white shirt with a high collar and a dark cravat; upright, half-turned towards the auditorium as if delivering a line, one hand slightly raised in a small gesture, the other hanging down, both hands empty. His whole figure is visible, about one third of the frame height. Muted warm stage lighting: the centre of the stage is brighter, the downstage-left area where he stands is in softer light. No objects on the floor. The look of a slightly soft, low-contrast archival video frame rather than a cinematic photograph. The top-left corner shows only dark curtain or backdrop. Photorealistic photograph with a natural, slightly imperfect look (visible texture, no airbrushing, no plastic look); not an illustration, not a painting, not 3D. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. The picture fills the whole frame edge to edge as one seamless image (no black boxes or blank areas); in the bottom-right part show only plain background, no important objects. Highest available resolution.
```

Неудачи правим в том же чате: если зал в кадре — `Same image, but crop so that only the stage is visible: no seats, no heads, no railing; keep everything else unchanged.`; если очки — `Same image, but without glasses; keep everything else unchanged.`; если стоит не у левой кулисы — `Same image, but move the grey-haired man in the frock coat to the far left of the stage, right next to the left side curtain; keep everything else unchanged.`

Чек-лист кадра-основы: только сцена, людей в зале нет; он у левой кулисы, впереди, во весь рост, руки пустые; сюртук, а не фрак; без очков; седина и борода как на портрете; надписей, логотипов, вывесок нет; левый верхний и правый нижний углы без важного (туда встанут подписи).

**Kling (image-to-video).** Стартовое изображение — `VD-4_base.jpg`. Длительность — **10 с**: режиссёр вырежет из них 6–10 с. Качество и разрешение — максимальные из доступных. Звук не генерировать: если в интерфейсе есть опция звука, выключить (дорожку всё равно убираем). Конечный кадр не задавать. Поле negative prompt, если оно есть, заполнить строкой ниже. Обычно хватает 3–5 генераций. Перед скачиванием проверить, что на файле нет водяного знака. Расход кредитов и тарифы — `docs/MEDIA-AI-OPTIONS.md` §3, перед оплатой сверить на сайте. Названия кнопок Kling не проверялись. Дописывать в запрос имена, текст роли или слова «умирает» и «смерть» не нужно.

Вариант A — **сдержанный, рекомендованный**:

```text
Static archival recording camera locked off on a tripod at the back of a theatre balcony; one continuous wide shot of the whole stage; no camera movement, no zoom, no pan, no cuts, no close-ups. The warm, muted stage lighting stays exactly the same for the whole clip. The grey-haired actor in the black 19th-century frock coat at the far left of the stage, next to the left side curtain, is delivering a line with a small hand gesture. He stops mid-gesture; his breathing becomes heavy, his shoulders rise and fall; he slowly presses one hand to his chest and takes an unsteady half-step towards the left curtain. His knees give way and he collapses sideways onto the stage floor at the edge of the left wing and lies still. The couples in the background keep moving for a moment, then stop and turn towards him. In the last second one performer in a dark costume hurries towards him from the left wing. Realistic and unhurried, not theatrical; everyone stays small in the frame, seen from far away.
```

Вариант B — **заметнее**:

```text
Static archival recording camera locked off on a tripod at the back of a theatre balcony; one continuous wide shot of the whole stage; no camera movement, no zoom, no pan, no cuts, no close-ups. The warm, muted stage lighting stays exactly the same for the whole clip. The grey-haired actor in the black 19th-century frock coat at the far left of the stage, next to the left side curtain, declaims a line with a wide gesture, then suddenly breaks off, gasps for air and clutches his chest with both hands. He staggers, reaches for the edge of the left curtain, his hand slips off the fabric, he drops to his knees and falls onto his side on the stage floor at the edge of the left wing, and lies motionless. The dancing couples in the background freeze. In the last two seconds two performers rush towards him: one from the left wing, one from the centre of the stage. Realistic, no slow motion; everyone stays small in the frame, seen from far away.
```

Вариант C — **тихий**, как в показаниях Лёвина 1-08 («сначала решил, что это он так играет»):

```text
Static archival recording camera locked off on a tripod at the back of a theatre balcony; one continuous wide shot of the whole stage; no camera movement, no zoom, no pan, no cuts, no close-ups. The warm, muted stage lighting stays exactly the same for the whole clip. The grey-haired actor in the black 19th-century frock coat at the far left of the stage, next to the left side curtain, holds a long dramatic pause, breathing heavily. He sways slightly, lowers his head, one hand drifts to his chest, then he quietly sinks down and lies on the stage floor by the left curtain without moving. For a few seconds nobody on stage reacts, as if this were part of the play; then one performer in a dark costume steps out of the left wing and hurries towards him. Realistic and unhurried; everyone stays small in the frame, seen from far away.
```

Negative prompt (для всех вариантов):

```text
close-up, zoom, camera movement, handheld shake, pan, cut, face close-up, blood, injury, convulsions, audience, spectators, heads, seats, balcony railing, text, letters, subtitles, timestamp, watermark, logo, slow motion, lens flare, flashing lights, light change, spotlight following the actor, curtain closing, objects in hands, morphing, extra limbs, distorted hands, duplicate people, people appearing from nowhere, cartoon, 3D render
```

**Если не выходит.** Если Kling «съедает» падение (артист просто садится или исчезает), повторить вариант A с припиской `He falls clearly and ends lying on the floor.` Если фигуры на заднем плане искажаются, перегенерировать кадр-основу с меньшим числом пар (`two couples`) или вовсе без них (`the rest of the stage is empty and dim`): сюжет от этого не меняется.

**Приёмка ролика** (смотреть на телефоне): камера неподвижна, без зума; в кадре только сцена, зрителей нет; падает у левой кулисы, на авансцене, и в конце лежит на полу; костюм, седина и борода не меняются, очков нет; в руках ничего нет; нет крови, «плывущего» тела и лишних конечностей; свет ровный до конца, без вспышек; нет надписей, логотипов и водяного знака; есть хотя бы 6 с без брака; в левом верхнем и правом нижнем углах нет важного.

**Что прислать:** 1–2 лучших MP4 как есть (`VD-4_take1.mp4`, `VD-4_take2.mp4`), утверждённый `VD-4_base.jpg` и номер варианта промпта (A, B или C).

**Требования к итоговому файлу** (их выполняет режиссёр при доводке): `media/video/archive-cam.mp4` — MP4 H.264, 1280 × 720 (16:9; 1920 × 1080, если исходник 1080p и размер позволяет), 25 к/с, **≤ 15 МБ** (общий предел игры — 25 МБ), 6–10 с; звука нет либо есть AAC-дорожка с глухим шумом зала без голосов и музыки. Постер `media/video/archive-cam.jpg` — JPEG, кадр до падения, с теми же подписями.

**Что делаем сами при сборке ролика** (заготовка, ещё не запускалась на настоящем ролике; проверена на тестовом сигнале): обрезка до нужного момента; деградация «архивной камеры» — 25 к/с, потеря резкости, приглушённые цвета, зерно, виньетка; подпись `КАМ. 3 СЦЕНА` слева вверху; бегущий таймкод `12.11.2026 21:02:xx` справа внизу; удаление звука или замена его на шум зала; постер; проверка размера. Время на первом кадре подбирается так, чтобы падение пришлось на 21:02:15–21:02:20, а последний кадр был раньше 21:02:24 (сигнал «СТОП», 2-07). Нужен шрифт с кириллицей и цифрами: шрифты игры в `site/assets/fonts/` разбиты на поднаборы woff2 (в кириллическом нет цифр), поэтому по умолчанию взят системный DejaVu Sans Mono, на Windows — `C\:/Windows/Fonts/consola.ttf`. Требуются bash и GNU `date`: на Windows — Git Bash или WSL.

```bash
#!/usr/bin/env bash
# VD-4. Доводка архивной записи спектакля из ролика Kling. Запуск из корня репозитория:
#   bash archive-cam.sh <VD-4_takeN.mp4> [начало_в_исходнике_с] [длительность_с] ["2026-11-12 21:02:12"]
# Переменные окружения (необязательно): OUT_DIR, FONT, LABEL, FLIP=1, AUDIO=none|roomtone, CRF.
set -euo pipefail

IN="${1:?укажите исходный mp4 из Kling}"
SS="${2:-0}"                               # с какой секунды исходника начинать
DUR="${3:-8}"                              # длительность фрагмента, 6-10 с
TC_START="${4:-2026-11-12 21:02:12}"       # время на первом кадре; конец фрагмента - до 21:02:24 (2-07)
OUT_DIR="${OUT_DIR:-media/video}"
FONT="${FONT:-/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf}"   # Windows: C\:/Windows/Fonts/consola.ttf
LABEL="${LABEL:-КАМ. 3 СЦЕНА}"
FLIP="${FLIP:-0}"                          # 1 - отразить по горизонтали, если кулиса оказалась не с той стороны
AUDIO="${AUDIO:-none}"                     # none - без звука; roomtone - глухой шум зала без голосов
CRF="${CRF:-24}"

# Время -> секунды эпохи; drawtext выводит его через gmtime, поэтому считаем как UTC.
EPOCH=$(date -u -d "$TC_START" +%s 2>/dev/null || date -u -j -f '%Y-%m-%d %H:%M:%S' "$TC_START" +%s)
FLIPF=""; [ "$FLIP" = "1" ] && FLIPF="hflip,"

# Деградация: 25 к/с, потеря резкости (960x540 -> 1280x720), приглушённые цвета, зерно, виньетка;
# затем подпись и бегущий таймкод. Фильтр пишем в файл, чтобы не экранировать двоеточия для оболочки.
FILTER="$(mktemp)"; trap 'rm -f "$FILTER"' EXIT
cat > "$FILTER" <<VF
setpts=PTS-STARTPTS,fps=25,${FLIPF}scale=960:540:flags=bilinear,scale=1280:720:flags=bilinear,
eq=contrast=0.92:saturation=0.70:brightness=-0.02:gamma=0.96,
noise=alls=9:allf=t,vignette=angle=PI/5,
drawtext=fontfile='${FONT}':text='${LABEL}':fontsize=26:fontcolor=white@0.85:borderw=2:bordercolor=black@0.6:x=28:y=24,
drawtext=fontfile='${FONT}':text='%{pts\\:gmtime\\:${EPOCH}\\:%d.%m.%Y %H\\\\\\:%M\\\\\\:%S}':fontsize=26:fontcolor=white@0.85:borderw=2:bordercolor=black@0.6:x=w-tw-28:y=h-th-24,
format=yuv420p
VF

mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/archive-cam.mp4"

if [ "$AUDIO" = "roomtone" ]; then
  # глухой «шум зала»: коричневый шум со срезанными верхами, очень тихо; голосов и музыки нет
  ffmpeg -hide_banner -y -ss "$SS" -t "$DUR" -i "$IN" \
    -f lavfi -t "$DUR" -i "anoisesrc=color=brown:amplitude=0.03:sample_rate=44100" \
    -map 0:v:0 -map 1:a:0 -filter_script:v "$FILTER" -af "lowpass=f=900,highpass=f=60,volume=0.6" \
    -c:v libx264 -preset slow -crf "$CRF" -profile:v high -maxrate 4M -bufsize 8M \
    -c:a aac -b:a 96k -ac 1 -shortest -map_metadata -1 -movflags +faststart "$OUT"
else
  ffmpeg -hide_banner -y -ss "$SS" -t "$DUR" -i "$IN" \
    -map 0:v:0 -filter_script:v "$FILTER" -an \
    -c:v libx264 -preset slow -crf "$CRF" -profile:v high -maxrate 4M -bufsize 8M \
    -map_metadata -1 -movflags +faststart "$OUT"
fi

# Постер: кадр на 1-й секунде (артист ещё стоит), с подписью и таймкодом.
ffmpeg -hide_banner -y -ss 1 -i "$OUT" -frames:v 1 -q:v 3 "$OUT_DIR/archive-cam.jpg"

# Проверки: размер <= 15 МБ, кодек, разрешение, длительность.
SIZE=$(wc -c < "$OUT")
echo "archive-cam.mp4: $SIZE байт"
[ "$SIZE" -le $((15*1024*1024)) ] || { echo "ОШИБКА: больше 15 МБ - поднимите CRF" >&2; exit 1; }
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of compact "$OUT"
```

Пример: падение в исходнике Kling на 5-й секунде, берём 8 с с 1-й секунды и ставим начало на 21:02:12, тогда падение придётся на ≈ 21:02:16, а конец — на 21:02:20: `bash archive-cam.sh VD-4_take1.mp4 1 8 "2026-11-12 21:02:12"`.

**Открыто (до доводки):** (1) таймкод — 21:02 по 2-05, 2-07, 3-01, 1-08; в задании стояло 21:04, но это время вызова скорой; (2) что считать «левой кулисой»: от зрителя (левый край кадра, как в запросах) или от актёра — при необходимости `FLIP=1`; (3) архивной камеры пока нет ни в одном документе `content/`: на плане 1-06 отмечены только две камеры наблюдения, а в 1-07 и на странице театра «фото- и видеосъёмка во время спектакля запрещена» (это правило для зрителей) — нужна строка у сценариста и решение о подписи (`КАМ. 3 СЦЕНА` или, например, `АРХИВ. СЦЕНА`); (4) путь `video/archive-cam.mp4` пока не прописан в `content/` (`TODO(content)`).

---

## 5. Сделано

Все позиции ниже приняты (✅), файлы лежат в `media/`. Промпты убраны, оригиналы есть в истории git (`git log -p -- docs/PRODUCTION.md`). **Готово 124 из 134, отменено 9 (❌), осталась 1 (`VD-4`, §4.2).**

| Раздел | Коды и пути | ✅ |
|---|---|---|
| Портреты | `P01`–`P14`: `media/portraits/*.jpg` (voroncov, zavyalov, volkov, marina, kirill, stas, reznikova, gnedich, viktor, oleg, inna, dmitriy, volskaya, gromov); `X05` (`portraits/nina_actress.jpg`) | 14 |
| Соцсети `gromov` | `AV-1`, `S03`, `S02` (совещание, улика), `GR-01`–`GR-03`: `media/gromov/` | 6 |
| `krug-voroncov` | `AV-2`, `CV-2`, `VR-01`–`VR-05` (`VR-02`, `VR-03` — улики), `S01` (`media/news/voroncov_arbenin.jpg`) | 8 |
| `krug-kirill` | `AV-3`, `CV-3`, `KR-01`–`KR-05` | 7 |
| `krug-marina` | `AV-4`, `CV-4`, `MR-01`, `MR-02` | 4 |
| `krug-volskaya` | `AV-5`, `CV-5`, `VS-01`–`VS-03` | 5 |
| `krug-volkov` | `AV-7`, `CV-7`, `VK-01`–`VK-03` | 5 |
| `krug-levin` | `AV-8`, `CV-6`, `LV-01` | 3 |
| Новые страницы «Круга» | `AV-9`–`AV-15`, `CV-8`, `CV-9`, `ZV-01`, `GN-01`, `GN-02`, `ZU-01`, `DM-01`, `RZ-01`, `KZ-01`, `KZ-02`: `krug-zavyalov`, `krug-gnedich`, `krug-zuev`, `krug-gorohova`, `krug-reznikova`, `krug-kuznecov`, `krug-ryabova` | 17 |
| `inna` («Кадр») | `AV-6`, `S05` (брошь; с 26.10 не улика), `S20`, `S21`, `S23`, `S24`: `media/inna/` (`IN-10` снят 26.10, файл удалён) | 6 |
| Бумага | `S08`–`S10` (1-10), `S11`–`S16`, `S11a`, `S11b` (2-03), `S17`, `S18` (2-06; крупный фрагмент `S18b` убран 24.10 — S-83): `media/paper/` | 13 |
| «Призма», новости | `S06`, `S07` (`media/lab/`, улики), `NM-01`, `F06`, `F07`, `X01` (`media/news*/`), `X04a`, `X04b` (`media/lab/`) | 8 |
| Сайты театра, фонда, клуба | `F01`, `F02` (`media/theater/`), `F05` (`media/fund/`), `F08`, `X02a`–`X02c` (`media/auction/`) | 7 |
| Облако | `X03a`–`X03c`: `media/cloud/01.jpg`–`03.jpg` | 3 |
| Аудио | `CALL` (`audio/anonymous_call.mp3`, улика, 0:40), `V1`–`V5`, `GV-1`, `GV-2`, `RV-1`, `RV-2`, `MV-1`, `KV-1`, `KV-2` | 13 |
| Видео | `4-07` (`video/rehearsal.mp4`, улика), `VD-1` (`krug-levin/video-01.mp4`, 0:09), `VD-3` (`krug-marina/video-01.mp4`, 0:06, водяной знак обрезан) | 3 |
| **Итого** | | **124** |

**Отменено (❌), 8:** `S22`, `S25`–`S28` (пять фото Инны; посты перенесены текстом на `krug-ryabova`), `LV-V1` (голос Лёвина), `VD-2` (ролик про усы Звездича), `W-407` (рабочий кадр, в игру не идёт).

---

## 6. По желанию

Ничего из этого не обязательно: готовые файлы работают. Если автор захочет, полные промпты и чек-листы лежат в истории git (`git log -p -- docs/PRODUCTION.md`, раздел «4.11»). Если берёте: **«берём КОД с лицом»**, файл кладётся под тем же именем, старый не удаляется до приёмки.

**Перегенерировать готовые кадры без лиц с лицом** (по портретам `media/portraits/`):

| Код | Было | Предлагается | Ценность |
|---|---|---|---|
| `VR-04` | борщ на плите, людей нет | Воронцов у плиты пробует борщ | высокая |
| `LV-01` | руки с кабачком в тёмной куртке | Лёвин с кабачком на крыльце, свитер вместо куртки | высокая |
| `MR-01` | тыква на учительском столе | Марина в шляпе ведьмы с тыквой, детей нет | средняя–высокая |
| `VS-02` | концерт: дети и затылки | Вольская в первом ряду аплодирует | средняя |
| `VS-03` | пирог с брусникой | Вольская с пирогом, без антиквариата и украшений | низкая–средняя |
| `AV-6` | капучино с сердечком | селфи Инны с тем же капучино, без броши | низкая–средняя |
| `KR-04` | мамины руки с телефоном | Кирилл с мученическим лицом, за плечом мамины руки | низкая |

Не трогаем вовсе: улики и спящие кадры (`VR-02`, `VR-03`, `S02`, `S05`, `IN-10`, `KR-03`, `MR-02`, фототаблицы 1-10, 2-03, 2-06, `S06`, `S07`) и обложки-места.

**Вопрос про `GR-01` (куртка).** На субботнике Громова в короткой тёмно-синей стёганой куртке, а короткая тёмная куртка в игре — примета фигуры на `VR-03` и в 4-08. Риск ложного следа низкий (в 4-08 — «мужчина № 2»). Править ли? Если да, в том же чате или с приложенным `gromov/01.jpg`: `Same image, but the woman wears a long light-beige padded coat instead of the short dark quilted jacket; keep her face, hair, pose, the sapling, the people and everything else exactly the same.`

---

## 7. Справка

Старые документы остаются для истории: `docs/PROMPTS.md`, `docs/drafts/pages/PHOTOS.md`, `PHOTOS-2.md`, `docs/drafts/media/VOICE-VIDEO-3.md`, `docs/MEDIA-PLAN-A.md`; сервисы и цены — `docs/MEDIA-AI-OPTIONS.md`; зачем каждый кадр — `docs/CLUE-MAP.md` §4. Статусы и промпты — только здесь.
