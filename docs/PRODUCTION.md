# Производство медиа: что осталось

**Актуально на 24.10.2026.** Готово 123 из 133 позиций, отменено 8, **осталось 2 позиции (4 файла)**. Как пользоваться: пишете в чат **«готово КОД»** (например, «готово GV-1») или **«переделать КОД: причина»**; режиссёр кладёт файл в `media/`, сверяет и ставит ✅. Проверка: `python -m engine build 2>&1 | grep "нет медиафайла"` должно стать пустым. Сюжет кадров — `docs/SCENARIO.md` и `content/`; если что-то расходится, прав сценарий. Образцы лиц и голосов в репозиторий не кладутся (`media/_refs/` в `.gitignore`).

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
| VD-1 | `media/krug-levin/video-01.mp4` + `video-01.jpg` | «Закулисье, серия первая: помреж и свет», 0:05, 9:16 | `krug-levin`, пост 31.10 16:44 | Gemini (кадр) + ElevenLabs (реплики) + Kling | ⬜ |
| VD-3 | `media/krug-marina/video-01.mp4` + `video-01.jpg` | Дача крёстного, яблоки, селфи-видео, 0:05, 9:16 | `krug-marina`, пост 11.10 12:47 | Gemini (кадр) + ElevenLabs (реплики) + Kling | ⬜ |

Улик среди семи позиций нет: сюжет от них не зависит.

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

Пост `krug-levin`, 31.10.2026 16:44. Губы двигаются **только у Резниковой** (мама; Резникова Наталья Сергеевна, роль помрежа) — в дверях аппаратной, в кадре. Антон (Кузнецов, роль Виктора «Мастера») у пульта спиной, его реплика — голос. Лёвин (Лёвин Сергей Николаевич, роль актёра Лёвина) снимает за кадром и **молчит**: голоса Лёвина не будет (23.10).

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

Пост `krug-marina`, 11.10.2026 12:47. В кадре **одна Алина** (Горенкова Алина Александровна, роль Марины, крестницы) — селфи, губы двигаются только у неё. За кадром — **Саша** (Горенков Александр Сергеевич, роль Кирилла, её отца): стоит рядом с телефоном, его в кадре нет, только голос. **Голоса Артёма (роль крёстного Артёма) нет** (решение автора 23.10). Сюжетно: Саша заехал на дачу к обеду за ведром яблок для бабушки — сходится с ответом крёстного под его постом 11.10 «ведро у тебя в багажнике с обеда» и с вопросом Саши там же «Яблоки где? Я спрашиваю для мамы....».

| Секунды | Кто | Реплика | Что в кадре |
|---|---|---|---|
| 0,0–1,6 | Алина (в камеру) | «Одно?! А ведро кому?» | Алина с одним красным яблоком у камеры, за ней на крыльце полное ведро яблок; возмущённая улыбка |
| 1,8–3,7 | Саша (за кадром, со смешком) | «Бабушке. Я только водитель.» | Алина поворачивает голову на его голос, рот закрыт |
| 3,9–5,0 | Алина | смех: «Ахаха» | трясёт яблоком перед камерой, обрыв |

Дорожка «для Kling»: реплика Алины на 0,0–1,6 и смех на 3,9–5,0, между ними тишина. Реплика Саши — клон из шага 2, **обычный голос, без маскировки** (как `KV-1`, `KV-2`), 1,5–2 с, **синхронизировать не надо**; в ней нет «спасибо», «Было бы за что» и слов звонка 1-05. Тон — балагур, шутит над собой. Кардиган горчичный — как на фото облака `X03c` (тот же день, 11.10). Подпись поста («угадайте, сколько досталось мне»), комментарий крёстного («самое красивое, между прочим)») и комментарий Саши («Ведро у меня!!!!! Водитель тоже человек 😂») сходятся: яблоко одно, ведро — бабушке, везёт Саша.

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

---

## 5. Сделано

Все позиции ниже приняты (✅), файлы лежат в `media/`. Промпты убраны, оригиналы есть в истории git (`git log -p -- docs/PRODUCTION.md`). **Готово 123 из 133, отменено 8 (❌), осталось 2 (раздел 2).**

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
| `inna` («Кадр») | `AV-6`, `S05` (брошь, улика), `IN-10` (улика), `S20`, `S21`, `S23`, `S24`: `media/inna/` | 7 |
| Бумага | `S08`–`S10` (1-10), `S11`–`S16`, `S11a`, `S11b` (2-03), `S17`, `S18`, `S18b` (2-06): `media/paper/` | 14 |
| «Призма», новости | `S06`, `S07` (`media/lab/`, улики), `NM-01`, `F06`, `F07`, `X01` (`media/news*/`), `X04a`, `X04b` (`media/lab/`) | 8 |
| Сайты театра, фонда, клуба | `F01`, `F02` (`media/theater/`), `F05` (`media/fund/`), `F08`, `X02a`–`X02c` (`media/auction/`) | 7 |
| Облако | `X03a`–`X03c`: `media/cloud/01.jpg`–`03.jpg` | 3 |
| Аудио | `CALL` (`audio/anonymous_call.mp3`, улика, 0:42), `V1`–`V5`, `GV-1`, `GV-2`, `RV-1`, `RV-2`, `MV-1`, `KV-1`, `KV-2` | 13 |
| Видео | `4-07` (`video/rehearsal.mp4`, улика) | 1 |
| **Итого** | | **123** |

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
