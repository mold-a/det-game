# План производства медиа: набор «А»

Точный план действий для автора. Набор «А» из `docs/MEDIA-AI-OPTIONS.md` §5: голос — XTTS-v2 локально (делает оркестратор), видео — Kling AI (Standard, 1 месяц), фото — Gemini (Nano Banana) бесплатно. Автор сам ничего не снимает и не записывает на камеру: всё генерируется, включая улики.

Что именно нужно по сюжету — `docs/MEDIA-SHOTLIST.md` и `docs/SCENARIO.md`; сервисы и цены — `docs/MEDIA-AI-OPTIONS.md`. Если этот план расходится со сценарием — прав сценарий.

> **Главное предупреждение.** Шот-лист и `MEDIA-AI-OPTIONS` рекомендуют снимать таблетницу и брошь вживую, а видео и звонок — записывать. Автор выбрал полностью сгенерированный путь. Он работает, но **мелкие детали-улики генераторы путают** (надписи кириллицей, гравировка на таблетках, число рядов страз, номера). Для каждой улики ниже есть «чек-лист проверки» и запасной приём. Если после 4–5 попыток деталь не получается — самый надёжный запасной путь: один раз сфотографировать предмет на телефон (минута) или попросить меня дорисовать деталь в Pillow.

---

## 1. Полный список файлов

Состояние `media/` на 20.10.2026: **пусто** (только `.gitkeep`). Всё ниже нужно получить с нуля. Папка `media/_refs/` в `.gitignore` — туда я кладу временные образцы, в репозиторий они не попадают.

Пути взяты из `content/` (поля `photo`, `avatar`, `cover`, `audio`, `video`, `media`) и совпадают с шот-листом. Пути — относительно `media/`.

### 1.1. Портреты — 14 файлов

Поле `photo` в `content/characters.yaml`; `avatar` на страницах `gromov` и `inna`. Генератор: Gemini. Формат: JPEG, вертикаль 4:5 (до квадрата обрезаю я), ≥ 800 px по короткой стороне (я сожму до ≤ 300 КБ). Лицо по центру, **чисто белый фон** (стандарт автора по образцу `voroncov.jpg` от 21.10), взгляд в камеру, «как на документ», одинаковый свет у всех 14. Готовый `portraits/voroncov.jpg` — образец стиля для остальных.

| № | Путь | Персонаж (кто в жизни) | Возраст в игре (в жизни) | Что обязательно видно |
|---|---|---|---|---|
| 1 | `portraits/voroncov.jpg` | Воронцов (автор) | 56 (20) | очки в прозрачной оправе, густые тёмные брови, харизматичный, чуть усталый |
| 2 | `portraits/zavyalov.jpg` | Завьялов, худрук (дедушка) | 61 (69) | властный, костюм, взгляд поверх очков |
| 3 | `portraits/volkov.jpg` | Волков, дублёр (Слава) | 31 (32) | обаятельная улыбка, свитер |
| 4 | `portraits/marina.jpg` | Марина, крестница Воронцова и дочь Кирилла (Алина) | 24 (15) | закрытая, без улыбки. В жизни 15, в игре 24: решено автором 21.10 (24 года, согласие родителей получено; вопрос 1 в §9 закрыт) |
| 5 | `portraits/kirill.jpg` | Кирилл, программист (дядя Саша) | 56 (48) | весёлые глаза, худи или клетчатая рубашка |
| 6 | `portraits/stas.jpg` | Лёвин, актёр | 44 (39) | артистичная мимика |
| 7 | `portraits/reznikova.jpg` | Резникова, помреж (мама) | 47 (51) | собранная |
| 8 | `portraits/gnedich.jpg` | Гнедич, костюмер (бабушка) | 63 (68) | строгая |
| 9 | `portraits/viktor.jpg` | Виктор «Мастер», свет (двоюродный брат) | 50 (25) | немногословный, тёмная футболка |
| 10 | `portraits/oleg.jpg` | Охранник Олег | 64 (в таблице не указан) | добродушный, тёмная куртка |
| 11 | `portraits/inna.jpg` | Инна, буфетчица (мама мужа сестры) | 29 (в таблице не указан) | суетливая, яркая помада |
| 12 | `portraits/dmitriy.jpg` | Водитель (женщина), роль «Дмитрий» (жена брата тёти) | 40 (40) | простая, надёжная, куртка. Женщина |
| 13 | `portraits/volskaya.jpg` | Вольская, меценат (тётя Света) | 54 (46) | светская, жемчуг |
| 14 | `portraits/gromov.jpg` | Громова, чиновник (сестра Юля) | 57 (28) | официальная, пиджак. Женщина |

Возраст в игре — `age` из `content/characters.yaml`; возраст в жизни — из таблицы персонажей (`sources/`). Это нужно для запроса: где разница большая (№ 1, 9, 14, 11), генератор надо явно просить состарить или омолодить (§4.2).

### 1.2. Сцены и улики для онлайн-страниц и экспертиз — 6 файлов

| № | Путь | Для чего | Генератор | Формат | Что обязательно видно |
|---|---|---|---|---|---|
| 15 | `news/voroncov_arbenin.jpg` | новость 1-13 (`pages/news`) | Gemini | 3:2, ≤ 300 КБ | Воронцов в роли Арбенина: костюм XIX века (фрак, шейный платок), сценический свет |
| 16 | `gromov/meeting.jpg` | пост 1-12, **улика** | Gemini | 4:3 (рамка поста 4:3, обрезки нет), ≤ 1 МБ | Громова за длинным столом совещаний; бумаги, вода; **табличка с названием совещания**; **за окном густая летняя зелень** (пресс-служба выложила старое фото; ноябрь за окном — ошибка) |
| 17 | `gromov/cover.jpg` | обложка профиля 1-12 | Gemini | широкая, около 8:3 (рамка 16:6) | здание городской администрации провинциального города; **без гербов, флагов, вывесок** |
| 18 | `inna/brooch.jpg` | фотосеть 2-09, **улика** | Gemini | 1:1 (плитки сетки квадратные), ≤ 1 МБ | Инна в броши, **та же, что в описи 2-08**: овал 6 × 4,5 см, металл под старое серебро, в центре крупный зелёный камень, по краю **два ряда** мелких прозрачных страз, внизу подвеска-капля |
| 19 | `lab/station_cam.jpg` | экспертиза 4-08, **улика** (`media: ["lab/station_cam.jpg"]`) | Gemini | 3:2 или 16:9, ч/б, ≤ 1 МБ | вокзал, камера КАССА-2 сверху; Воронцов у окна кассы № 2; Волков у колонны в 5–7 м, смотрит на него. **Таймкод «30.10.2026 14:37:22 КАССА-2» накладываю я** |
| 20 | `lab/pillbox.jpg` | экспертиза 3-06, **улика** | Gemini | 3:2, сверху, ≤ 1 МБ | недельная чёрная пластиковая таблетница (в тексте 3-06: 18 × 3 × 2 см, **7 отделений в один ряд**, откидные крышки с выпуклыми буквами ПН…ВС): ПН, ВТ **пусто**; СР — белая круглая двояковыпуклая «S»; ЧТ — белая круглая **плоская с риской, чуть крупнее**; ПТ, СБ, ВС — как СР («S») |

Замечание по № 20: в `content/documents/3-06.md` (текст экспертизы уже написан) по состоянию на 20.10.2026 нет поля `media:` (шот-лист просит его добавить). Пока поле не добавлено, фото не попадёт в экспертизу — это правка `content/`, я её не делаю (вопрос 2 в §9).

### 1.3. Фото для бумажных документов — 13 файлов (`media/paper/`)

Поле `media` в `content/paper/*.md`. Все — Gemini, JPEG, ≤ 1 МБ (печатный размер).

| № | Путь | Документ | Формат | Что обязательно видно |
|---|---|---|---|---|
| 21 | `paper/1-10-general.jpg` | фототаблица 1-10, кадр 1 | 4:3 | гримёрка № 4 от входной двери: гримстолик с зеркалом в лампах, кресло с тёмно-синим пиджаком на спинке, стул с коричневой сумкой, вешалка-стойка с костюмом, диван. **Окон нет** (комната 3 × 4 м). Номерки и линейку накладываю я |
| 22 | `paper/1-10-table.jpg` | 1-10, кадр 2 | 4:3 | столик: часы на ремешке, грим в металлическом кейсе, бутылка воды 0,5 л на треть полная, машинописный текст роли, **зарядка в розетке, кабель свисает, телефона нет**, белые наушники в футляре; **на втором плане, не в фокусе, но различима: открытая сумка на стуле, из неё торчит чёрная таблетница** |
| 23 | `paper/1-10-rack.jpg` | 1-10, кадр 3 | 4:3 | вешалка-стойка: чёрное шерстяное пальто, серый шарф, сценический костюм 1-го действия (фрак, жилет, сорочка), чёрные туфли внизу |
| 24–31 | `paper/2-03-01.jpg` … `paper/2-03-08.jpg` | кадры камеры 2-03 | 16:9, ч/б, вид сверху, зерно | служебный вход театра **ночью** (19:30–20:00, ноябрь): крыльцо, закрытая дверь, у крыльца тёмный легковой автомобиль, в салоне водитель (Дарья). Подписи кадров — в `content/paper/2-03.md`; детали по кадрам — §4.7. Таймкоды 19:30:06 … 20:00:00 накладываю я |
| 32 | `paper/2-06-room.jpg` | фототаблица 2-06, кадр 1 | 3:2 | кабинет худрука от двери: письменный стол, приставной стол для совещаний, книжные шкафы, афиши и грамоты на стенах (без читаемого текста), у окна диван |
| 33 | `paper/2-06-office.jpg` | 2-06, кадр 2 | 3:2 | стол: стопки документов; папка-скоросшиватель с этикеткой (**текст «Фонд „Сцена“: отчёт для администрации города» накладываю я**); ежедневник, письменный прибор, очки, настольная лампа, стационарный телефон; **две чашки на блюдцах с остатками кофе, на одной — след губной помады** (Громова — женщина, `g('', ', на одной — след губной помады')`); **мелкая упаковка лекарства** (решение сценария: читается только при увеличении) |

(Нумерация сквозная: 24–31 — это восемь файлов 2-03.)

### 1.4. Аудио и видео — 2 файла

| № | Путь | Для чего | Чем | Формат | Что обязательно |
|---|---|---|---|---|---|
| 34 | `audio/anonymous_call.mp3` | страница звонка 1-05 (`pages/call`) | XTTS-v2 (я) + телефонный фильтр ffmpeg | MP3 128 кбит/с, **47 с** (в 1-05 «0 мин 47 с», на странице «0:47») | голос Кирилла (дяди); фраза «Было бы за что» (`w.clues.kirill_habit`); голос приглушённый, тихо и быстро, фоновых звуков нет |
| 35 | `video/rehearsal.mp4` | страница видео 4-07 (`pages/video`), **улика** | кадр Gemini + аудио XTTS → Kling | MP4 H.264 + AAC, 16:9 (в карточке файла указано 1920 × 1080), 5–6 с (решение автора 23.10), **≤ 25 МБ** | Слава в сценическом костюме читает монолог Арбенина; **днём, окно с дневным светом в кадре**; репетиционный зал |

### 1.5. Итог

| Вид | Файлов | Откуда |
|---|---|---|
| Портреты | **14** | Gemini |
| Сцены и улики для страниц и экспертиз | **6** | Gemini |
| Фото для бумажных документов | **13** (3 + 8 + 2) | Gemini |
| Аудио | **1** | XTTS-v2 (я) |
| Видео | **1** | Gemini (кадр) + XTTS + Kling |
| **Итого файлов для игры** | **35** | |

Файлов для игры от Gemini — **33** (14 + 6 + 13). Два из 13 бумажных фото (кадры камеры 7 и 8: пустое крыльцо) я получаю из кадра 1 сам (шум и лёгкий дрейф яркости), поэтому генерировать нужно 31 файл, плюс 2 рабочих кадра (основа видео и эталон броши) = **33 удачные генерации**. С учётом неудачных попыток закладывайте **≈ 55–65 запросов** (§3).

### 1.6. Рабочие файлы (в игру не идут)

| Путь на компьютере автора | Для чего |
|---|---|
| `work/video_base_frame.jpg` | кадр-основа для Kling (Слава в зале), 16:9 |
| `work/brooch_ref.jpg` | крупный план броши — эталон, который подставляется в запрос с Инной |
| `refs/…` | фото-образцы лиц (§2) — отправляются только в чат, в репозиторий не кладутся |

### 1.7. Необязательно: фотосеть Инны

`content/pages/inna/page.yaml` содержит `TODO(content): ещё 8–11 фото — быт, еда, кошки, кофе`, в спецификации страницы сетка 9–12 фото. Путей в content пока нет, поэтому **в список выше они не входят**. Если сценарист пропишет пути, понадобится ещё ≈ 8–11 лёгких кадров Gemini (кофе, еда, кошки, быт; 1:1) — это полдня работы с Gemini. Вопрос 3 в §9.

---

## 2. Что нужно от автора до начала

### 2.1. Согласие

Лица и голоса родственников клонируются и «играют» в сюжете (`MEDIA-AI-OPTIONS` §7). Спрашивайте мягко, не раскрывая сюжета: «Можно сделать тебе смешной портрет и озвучку для семейной игры?». Особенно это касается Славы и дяди (голос). Алина: согласие родителей получено (21.10).

### 2.2. Фото-образцы лиц

| Что | Требование |
|---|---|
| Кого | 14 портретных ролей из §1.1. Кроме них — ничьи лица не нужны (врачи, полицейские — вымышленные) |
| Сколько | **2 фото на человека** (3 максимум: Gemini на бесплатном тарифе принимает до 3 образцов за запрос, а сцены с двумя людьми и эталоном броши уже занимают слоты). Для Славы и Воронцова (автора) — по 3 |
| Лицо | анфас или чуть в три четверти, лицо занимает хотя бы треть кадра, глаза открыты, без тёмных очков, без фильтров и «красоты», без шапки и маски |
| Свет | дневной, равномерный, без жёстких теней и без вспышки в лоб |
| Выражение | одно нейтральное, одно с лёгкой улыбкой |
| Качество | не скриншот из мессенджера с сильным сжатием; лучше оригинал из галереи, ≥ 800 px по короткой стороне |
| Очки | если человек носит очки постоянно (Воронцов — прозрачная оправа), одно фото в очках |
| Имя файла | `voroncov_1.jpg`, `voroncov_2.jpg` — по id роли из §1.1 |
| Для Дарьи и Громовой | это женские роли (в жизни — жена брата тёти и сестра): фото именно этих людей |
| Для Инны и Олега | возраст в жизни не указан в таблице: напишите его в сообщении (нужен для просьбы «состарить / омолодить») |

### 2.3. Голосовые образцы

Нужны **два голоса** (`MEDIA-AI-OPTIONS` §1–2; XTTS-v2 клонирует по 15–30 с чистой речи).

| Голос | Для чего | Что записать |
|---|---|---|
| **Дядя (Кирилл)** | звонок 1-05 | 15–30 с обычной речи без музыки и эха. **Лучший вариант: уже существующее голосовое из мессенджера** (если речь чистая) — сюжета не раскрывает. Либо дядя читает нейтральный текст из пункта ниже **дважды: обычным голосом и вполголоса, быстро** (звонок звучит тихо и быстро). Сюжет ему не называть |
| **Слава (Волков)** | монолог в видео 4-07 | 15–30 с обычной речи (тоже можно готовое голосовое), плюс по желанию 6–8 строк стихотворного текста «с выражением», например первые шесть строк монолога из §5.2 — «для школьной декламации». Выразительное чтение помогает клону говорить стихи |

Нейтральный текст для дяди и Славы (≈ 15 с, сюжета не касается):

> «Вчера заезжал в магазин, взял хлеб, молоко и сыр. Потом заправился и поехал домой через мост. Дорога была свободная, дождя не было. Вечером посмотрели футбол, а потом пили чай с лимоном.»

Технические требования: запись на телефон в тихой комнате (не на кухне, не в машине), микрофон в 20–30 см, без фоновой музыки и ТВ, формат любой (`.m4a`, `.ogg`, `.mp3`, `.wav`) — переконвертирую сам.

### 2.4. Как прислать

В чат к оркестратору (в Claude Code), по одному сообщению на человека; имена файлов как в таблице. В репозиторий образцы **не кладём**: я сохраню их только в `media/_refs/` (в `.gitignore`) и удалю после готовности игры. **Открытый вопрос оркестратору:** принимает ли чат аудиофайлы и архивы такого размера (§9, вопрос 4).

### 2.5. Что нужно завести до первого вечера

| Что | Где | Платно? |
|---|---|---|
| Аккаунт Google | [gemini.google.com](https://gemini.google.com) | нет |
| Аккаунт Kling AI | [klingai.com](https://klingai.com) | регистрация и пробные кредиты бесплатно; тариф Standard — платно, **оплачивать только в вечер Kling** (§5), не раньше |

**Доступность из России не проверена.** В `MEDIA-AI-OPTIONS` §7 сказано: зарубежные сервисы обычно не принимают российские карты, нужна иностранная карта или платный посредник; российские аналоги не проверялись. Работает ли Gemini в вашем регионе без смены страны аккаунта — по источникам проекта неизвестно, проверьте при регистрации. Цену посредника в бюджет не закладываю, потому что цифр нет. Условия сервисов (регион, возраст, оплата) читайте сами.

---

## 3. План по вечерам

Бесплатный лимит Gemini: **по обзорам ≈ 20 картинок в день** (`MEDIA-AI-OPTIONS` §4; сам Google лимит не публикует), **до 3 образцов в запросе**. По заголовку одного из источников (letsdatascience.com) режим «Nano Banana Pro» на бесплатном тарифе урезан примерно до двух картинок в день — не проверялось; используйте обычный Nano Banana, а «Pro» оставьте на крайний случай. Если лимит кончился раньше — остановитесь и продолжите завтра, не создавайте второй аккаунт.

Всего удачных генераций 33, с повторами ≈ 55–65 запросов — **4 вечера Gemini + 1 вечер Kling** (Kling можно совместить с любым из вечеров 3–4). Запас — пятый день.

| Вечер | Что делает автор | Что делаю я | Запросов Gemini |
|---|---|---|---|
| **0** (≈ 1 ч) | отправляет согласие, образцы лиц и голосов (§2); регистрируется в Gemini и Kling; на бесплатных кредитах Kling проверяет, что есть инструмент «фото + аудио → говорящее видео» (§5.3) | принимаю образцы, делаю пробу голоса XTTS и пишу «качество достаточно / нет»; готовлю аудио монолога (§5.2) и звонка (§6) | 0 |
| **1** | **Кадр-основа видео** (≤ 4 попытки, §5.1) и **портреты 1–8**: Воронцов, Завьялов, Волков, Марина, Кирилл, Стас, Резникова, Гнедич | жду, проверяю присланное, сообщаю правки | ≈ 12–20 |
| **2** | **Портреты 9–14**: Виктор, Олег, Инна, Дарья, Вольская, Громова; затем **15 новость (Арбенин), 16 совещание Громовой, 18 брошь** (сначала эталон `brooch_ref.jpg`, потом селфи Инны) | сжимаю портреты, проверяю брошь против описи 2-08; **присылаю готовое аудио монолога** | ≈ 18–20 |
| **3** | **19 вокзал, 20 таблетница, 21–23 гримёрка (три кадра), 32–33 кабинет худрука**, 17 обложка Громовой. **Kling-вечер** (§5): оплата Standard, загрузка кадра и аудио | проверяю улики по чек-листам (§4.3–4.6), прошу перегенерировать | ≈ 16–20 + Kling |
| **4** | **24–29 кадры камеры 2-03** (шесть уникальных: 1, 2, 3, 4, 5, 6) + перегенерация всего, что я вернул | довожу, накладываю таймкоды, номерки, этикетки; делаю кадры 7–8 из кадра 1; сжимаю видео | ≈ 10–20 |
| **5** (запас) | исправления, докачка видео | сборка и проверка | 0–10 |

Порядок внутри вечера: сначала самое «хрупкое» (улики), потом простое. Если в какой-то вечер лимит исчерпан, переносите в конец списка простые портреты, а не улики.

### 3.1. Как работать в Gemini — «загрузить образец → вставить запрос → скачать»

Названия кнопок в интерфейсе меняются, поэтому описываю действия, а не точные подписи.

1. Откройте [gemini.google.com](https://gemini.google.com), войдите в аккаунт Google.
2. Нажмите «Новый чат». **Каждый новый кадр — новый чат.** Исключение: когда нужно «то же место, другой ракурс» (гримёрка, крыльцо) — продолжайте в том же чате.
3. Включите создание изображений: в строке ввода — инструмент «Создать изображения» (или формулировка в запросе: «Create an image: …»). Модель — обычная Nano Banana.
4. Нажмите «+» / скрепку в строке ввода и **загрузите образцы лиц** (не более 3 файлов за запрос). Порядок важен: сначала лица, потом эталоны (брошь, готовые портреты).
5. Вставьте запрос из §4 целиком. Замените всё, что в `{фигурных скобках}`.
6. Отправьте. Если картинка неверная, **не пишите новый запрос с нуля** — напишите в том же чате короткую правку: «Same image, but …» (экономит лимит и держит сцену).
7. Если лицо не похоже: «Make the face match the reference photo more closely; keep everything else unchanged».
8. Скачайте: наведите на картинку → кнопка скачивания (при наличии выбирайте полный размер). Не делайте скриншот.
9. Сохраните файл **по имени и в папку из §7** (например `detgame-media/portraits/kirill.jpg`). Неудачные не удаляйте до моей проверки: складывайте в `detgame-media/_attempts/`.
10. Проверьте картинку по чек-листу кадра. Если пункт не выполнен — правка в том же чате (до 3 раз), затем новый чат.

**Возможный видимый знак Gemini в углу** (на бесплатном тарифе иногда ставится): источниками проекта не подтверждено, проверьте на первом же снимке. Нижний правый угол кадра я обрежу или закрою, поэтому в запросах там нет ничего важного. Невидимая метка происхождения (SynthID), насколько мне известно, остаётся; источниками проекта это не подтверждено, для семейной игры не мешает.

---

## 4. Запросы к Gemini

> Готовые к копированию запросы — `docs/PROMPTS.md` (приоритет над этим разделом).

**Язык.** Запросы на английском: Gemini понимает и русский, но в английском точнее передаются ракурс, оптика, свет, а это здесь ключевое. Исключения — надписи на кириллице (в запросе даны русскими буквами там, где нужны; многие надписи я всё равно накладываю сам). Ответы Gemini можно получать на русском, это не влияет.

### 4.1. Общие правила и «хвост» запроса

Хвост `{NEG}` добавляется в **конец каждого запроса** (в таблицах ниже — «+NEG»):

> `NEG: Photorealistic photograph, natural imperfect look (visible skin texture, no airbrushing, no plastic skin), not an illustration, not a painting. No text, no captions, no timestamps, no watermarks, no logos, no brand names, no coats of arms, no flags, no readable signs. Keep the bottom-right corner free of important details. Highest available resolution.`

В запросах, где цифры или буквы нужны (вокзал, таблетница), исключение сказано в самом запросе; если Gemini «спорит» с хвостом, уберите из `NEG` слова «no text».

Правила:

- **Образцы лиц — только настоящие фото из §2.** Без образца генератор нарисует незнакомца.
- **После утверждения портрета используйте его вместо сырого образца** в сценах (Арбенин, вокзал, совещание, кадры камеры): портрет уже состарен или омоложен до возраста игры, и не придётся просить об этом снова. Сырой образец оставьте как второй референс, если слот есть.
- **Возраст.** Генератор по умолчанию оставляет возраст образца. Всегда пишите в запросе явное «look about N years old» и направление: для автора (20 → 56), Виктора (25 → 50), Громовой (28 → 57) — «**age the person by about N years**: grey at the temples, lines at the eyes and mouth, heavier face, but keep the same face structure». Для Завьялова (69 → 61) — «look about 61, slightly younger than in the reference». Инну (29) и Олега (64) настраивайте по их реальному возрасту (напишите мне его).
- **Формат кадра** пишите в запросе («3:2», «16:9», «1:1»). Если Gemini выдал другой, не страшно: я обрежу.
- **Не просите текст на предметах**, кроме перечисленных ниже. Кириллица в картинках часто искажается; надписи (таблички, этикетки, дни недели) я накладываю сам.
- **Бренды вымышлены.** Следите: на куртке охранника, машине, телефоне, бутылке, лекарстве не должно быть настоящих логотипов. Если появились, правка: «Remove all logos and brand marks».
- **Лица в кадре с несколькими людьми** (вокзал, 2-03, совещание): заводите по образцу на каждого главного героя; остальные — безликий фон.

### 4.2. Портреты (14 файлов)

Шаблон `{P}` (одинаковый для всех, чтобы свет и фон совпали):

> `Use the attached photo(s) as the identity reference for a real person. Create a photorealistic ID-style portrait of the SAME person: keep the face shape, eyes, nose, mouth, eyebrows and skin tone clearly recognisable. {AGE} {LOOK} Frontal view, head and shoulders, face centred, plain pure white seamless background, soft even daylight from the front, identical neutral lighting as for a series of document photos. Square 1:1. +NEG`

Подставьте `{AGE}` и `{LOOK}`:

| Файл | `{AGE}` | `{LOOK}` |
|---|---|---|
| `voroncov.jpg` | `Age the person by about 35 years so he looks about 56: grey at the temples, fine lines around the eyes and mouth, a fuller face, but the same identity.` | `Charismatic but slightly tired look, subtle half-smile. Keep thin CLEAR (transparent) frame glasses — not black frames — and thick dark eyebrows. Dark jacket over a shirt.` |
| `zavyalov.jpg` | `The person should look about 61 years old, slightly younger than in the reference: fewer deep wrinkles, hair a little less grey.` | `Authoritative, a commanding gaze looking over the top of his glasses (glasses at the end of the nose). Dark suit, tie.` |
| `volkov.jpg` | `The person should look about 31 years old.` | `Charming open smile, friendly eyes. Casual knit sweater.` |
| `marina.jpg` | `The person should look about 24 years old, an adult young woman.` | `Closed, guarded expression, no smile, direct gaze. Simple casual top, hair as in the reference.` |
| `kirill.jpg` | `Age the person by about 8 years so he looks about 56: a few grey hairs, small lines at the eyes.` | `Cheerful, laughing eyes, a hint of a smirk. Hoodie or a checked shirt.` |
| `stas.jpg` | `The person should look about 44 years old.` | `Artistic, expressive face with a slightly raised eyebrow. Dark turtleneck or a shirt with an open collar.` |
| `reznikova.jpg` | `The person should look about 47 years old.` | `Composed, organised, attentive look. Hair tied back. A black stage-manager headset resting around the neck (no brand).` |
| `gnedich.jpg` | `The person should look about 63 years old.` | `Strict, no-nonsense expression. A yellow tailor's measuring tape draped around the neck. Cardigan or a dark blouse.` |
| `viktor.jpg` | `Age the person by about 25 years so he looks about 50: lined face, short greying hair, light stubble, but the same identity.` | `Taciturn, calm look. Plain dark t-shirt.` |
| `oleg.jpg` | `The person should look about 64 years old (adjust from the reference: {older/younger}).` | `Good-natured, kind face. A dark security-guard-style uniform jacket with no logos, patches or insignia.` |
| `inna.jpg` | `The person should look about 29 years old (adjust from the reference: {rejuvenate/keep}).` | `Fussy, lively expression, bright red lipstick. Light blouse with a canteen apron over it.` |
| `dmitriy.jpg` | `The person should look about 40 years old.` | `Plain, reliable, calm look. Practical dark jacket; a woman.` |
| `volskaya.jpg` | `Age the person by about 8 years so she looks about 54.` | `Society-lady look, poised and elegant. A pearl necklace, neat styled hair, tasteful blouse or jacket.` |
| `gromov.jpg` | `Age the person by about 29 years so she looks about 57: grey streaks, lines at eyes and mouth, a firm jaw, but the same identity.` | `Official, composed, slightly stern. A formal blazer with a small plain lapel pin with no symbols, no emblem. A woman.` |

**Чек-лист каждого портрета:** лицо узнаваемо; возраст похож на игровой; белый фон и мягкий свет как у `voroncov.jpg`; нет текста и логотипов; для № 10 — куртка без нашивок; для № 1 — очки и густые брови.

**Где ошибается:** «синдром одного лица» (разные люди становятся похожими друг на друга), слишком гладкая кожа, при сильном старении — дрейф к «другому человеку». Правка: «Keep the exact face of the reference; only change apparent age».

### 4.3. Новость, совещание, обложка (15, 16, 17)

**`news/voroncov_arbenin.jpg`** (подставьте утверждённый портрет Воронцова + образец автора):

> `Use the attached portrait as the identity reference. Photorealistic theatre press photo of this same man, about 56 years old, in the role of Arbenin in Lermontov's play "Masquerade" on the stage of a provincial theatre. Black 19th-century tailcoat, white shirt with a high collar, dark cravat. Serious dramatic expression, half-length shot, warm side stage spotlight, dark background with a hint of heavy curtain, shallow depth of field. Keep his thick dark eyebrows; no glasses on stage. Horizontal 3:2. +NEG`

Чек-лист: узнаваем; костюм XIX века; сцена; без афиш с текстом.

**`gromov/meeting.jpg`** (портрет Громовой + образец):

> `Use the attached portrait as the identity reference. Official press-service style photo of this same woman, about 57 years old, sitting at a long conference table in a municipal administration meeting room. She wears a formal grey blazer. On the table in front of her: papers, a laptop, glass bottles of water, and a blank white landscape A4 sign in a clear plastic holder standing square-on facing the camera (leave it completely blank, no text). Two or three other participants sit further down the table, out of focus, faces not distinguishable. Behind her, a large window: outside is LUSH GREEN SUMMER FOLIAGE in bright summer daylight, full green trees, no autumn colours, no snow. Neutral official wall, no flag, no emblem, no portraits. Straight-on, slightly flat press-office photography, aspect 4:3. +NEG`

Чек-лист: **зелёная листва в окне** (не жёлтая, не голые ветки); табличка пустая и читается как лист в подставке (текст «Рабочее совещание по развитию культурной инфраструктуры» накладываю я); нет флагов и гербов; лицо узнаваемо.

**`gromov/cover.jpg`:**

> `Wide panoramic photo of the main building of a city administration in a provincial Russian-like city: a five-storey light-coloured building with a columned central entrance, a small square in front with trees and a lawn, overcast daylight. NO flags, NO coat of arms, NO signboards, no readable text, no vehicles with readable plates. Very wide horizontal aspect ratio about 8:3. +NEG`

### 4.4. Брошь и Инна (18)

Улика: брошь должна **совпасть с описью 2-08, поз. 7**: «овальная, металл под старое серебро, в центре — крупный зелёный камень (стекло), по краю — два ряда мелких прозрачных страз, внизу — подвеска-капля; 6 × 4,5 см».

**Шаг 1 — эталон `work/brooch_ref.jpg`** (без образцов лиц):

> `Macro product photo of a handmade theatrical costume brooch lying on dark red velvet, front view, sharp focus, even soft light. Oval shape, about 6 x 4.5 cm. Frame of metal that looks like antique tarnished silver. ONE large green faceted stone (green glass) in the centre of the oval. Along the edge of the oval: exactly TWO concentric rows of tiny clear rhinestones. Below the oval, a single teardrop-shaped pendant hangs from the bottom. Showy, vintage look. Square 1:1. +NEG`

Чек-лист эталона (проверить **на 100% увеличении**): 1) овал; 2) **один** крупный зелёный камень по центру; 3) ровно **два** ряда страз по краю (считайте); 4) **одна** подвеска-капля внизу; 5) металл «под старое серебро». Не прошло — правка в том же чате: «Exactly two rows of small clear stones around the edge, one large green stone in the centre, one teardrop pendant at the bottom».

**Шаг 2 — селфи Инны.** Загрузите: портрет Инны (+ при желании сырой образец) и `brooch_ref.jpg` (итого ≤ 3 файла):

> `Use image 1 (and 2 if attached) as the identity reference for the woman, about 29 years old, with bright red lipstick. Use the LAST image as the exact reference for the brooch. Mirror selfie in a cosy home hallway in the evening, warm indoor light: she holds a smartphone (no logo) in front of her chest, taking the photo in the mirror. She wears a plain light blouse and the brooch is pinned prominently at the collar / upper chest, large and clearly visible, sharp, identical to the brooch reference: oval shape, antique-silver look, one large green stone in the centre, two rows of small clear rhinestones along the edge, a teardrop pendant at the bottom. Pose proud, happy. Square 1:1. +NEG`

Чек-лист: брошь в кадре **крупная и резкая**; те же 5 признаков, что у эталона; рядом нет второй броши; лицо узнаваемо. Если Gemini «упрощает» брошь — пришлите мне: я могу вклеить эталон в кадр (Pillow).

### 4.5. Вокзал (19)

Загрузите утверждённые портреты **Воронцова и Волкова** (2 файла).

> `Use image 1 as the identity reference for the man at the ticket window (about 56 years old) and image 2 as the identity reference for the second man standing by the column (about 31 years old). Create a still frame from a ceiling-mounted CCTV camera, looking down at an angle of about 40 degrees from a high corner, inside the ticket hall of a provincial railway station in daytime. Pure black-and-white, grainy low-resolution surveillance image, slight wide-angle barrel distortion, slight motion blur. Along one wall there are three ticket windows with big plain digits 1, 2, 3 above them from left to right. The first man stands at the middle window, number 2, leaning toward it, wearing a long dark overcoat and glasses, no hat, paying. A thick square concrete column stands opposite the ticket windows, about 6 metres from him; the second man stands next to the column in a short dark jacket, no hat, hands in pockets, his head turned toward the first man and looking at him. Two or three other passengers far in the background, small, not looking. Benches, tiled floor, no brand names, no text except the three digits. 3:2. +NEG`

Чек-лист: **окно № 2** (цифра видна) и Воронцов у него — **длинное тёмное пальто, очки, без шапки**; Волков — **короткая тёмная куртка, без шапки** (так в тексте экспертизы 4-08, около 6 м); колонна; **Волков в 5–7 м от Воронцова и смотрит в его сторону**; ч/б; вид сверху; лица различимы хотя бы в профиль. Таймкод и подпись «КАССА-2» накладываю я; **не просите их у генератора**. Где ошибается: расстояние между героями (слишком близко или в одном «кружке»), цифры на окнах, «глянцевость» вместо зерна.

### 4.6. Таблетница (20) и гримёрка (21–23)

**`lab/pillbox.jpg`** (без лиц). Это самая «хрупкая» улика: по `content/documents/3-06.md` и `content/paper/1-09.md` (поз. 17.3 «таблетница недельная, чёрная, пластиковая»):

> `Top-down macro photo, camera directly above, of a black plastic weekly pill organiser with 7 separate rectangular compartments in one row. Each lid is open, and the compartments are labelled left to right on the plastic with raised (embossed) Russian two-letter day abbreviations on the lids: ПН, ВТ, СР, ЧТ, ПТ, СБ, ВС. The organiser is long and slim (about 18 x 3 cm). Contents: compartments ПН and ВТ are completely EMPTY. Compartments СР, ЧТ, ПТ, СБ, ВС each contain exactly ONE white round tablet. The tablet in ЧТ is flat with a bevelled edge, slightly larger (about 9 mm), with a straight score line across its middle and no letter. The tablets in СР, ПТ, СБ and ВС are smaller (about 8 mm), slightly domed and coated, each with a capital letter S engraved in the centre and no score line. The organiser fills most of the frame, lies on a plain light wooden table, soft window daylight from the left, slightly worn plastic, sharp focus. No other objects, no brand names. Horizontal 3:2. +NEG (day labels are allowed)`

Чек-лист (сверять с `3-06`; **на 100% увеличении, по одному отделению**):

| Отделение | Должно быть |
|---|---|
| ПН | пусто |
| ВТ | пусто |
| СР | 1 белая круглая, «S» |
| ЧТ | 1 белая круглая **плоская, крупнее остальных, риска**, без буквы |
| ПТ | 1 белая круглая, «S» |
| СБ | 1 белая круглая, «S» |
| ВС | 1 белая круглая, «S» |

Проверьте также: ровно **7** отделений в один ряд; чёрный пластик; подписи дней в правильном порядке и без опечаток. **Где ошибается генератор:** число отделений (6 или 8), перепутанные или «пустые вместо полных» отделения, «S» на всех таблетках или ни на одной, кириллические подписи дней. Что делаем: при верной общей картине я перерисую подписи дней и гравировку в Pillow по вашему кадру. При неверном порядке содержимого — перегенерация правкой в том же чате: «Wednesday has one S tablet, Thursday has one tablet with a score line and no S».

Крупный план эту же таблетницу не повторяет: на `paper/1-10-table.jpg` она на втором плане, детали там не нужны.

**Гримёрка (21–23)** — один чат, три кадра подряд. Источник деталей — `content/paper/1-09.md` (опись) и `content/paper/1-10.md` (подписи). Комната без окон, 3 × 4 м.

Кадр 1, `paper/1-10-general.jpg`:

> `Photorealistic forensic documentation photo, shot with a compact camera from the entrance doorway of a small windowless theatre dressing room, about 3 by 4 metres, ceiling light plus bulbs around the mirror (all on), mild on-camera-flash feel, neutral colours, slightly lived-in, nobody in the room. Straight ahead: a make-up table with a large mirror framed by round bulbs, a leather armchair in front of it with a dark-blue men's jacket over its back. To the left of the table: a wooden chair with an open brown leather men's bag on it. A washbasin against the wall. To the right of the entrance: a clothes rack with a black wool coat, a grey scarf and a stage costume (tailcoat, waistcoat, shirt), black shoes on the floor under it, and next to it a sofa with a plaid blanket and an opened box of chocolates. A plastic bucket with a bouquet of red roses stands on the floor near the mirror. Horizontal 4:3. No numbers, no ruler, no markers (added later). +NEG`

Кадр 2, `paper/1-10-table.jpg` (в том же чате; **загрузите кадр 1 как образец комнаты**):

> `Same dressing room as in the reference image (same mirror, table, lamps, walls). New view: a closer, slightly angled shot of the make-up table. On the table: a men's wristwatch with a leather strap, an open metal make-up case with brushes and sponges, a comb, a plastic half-litre water bottle already opened and about one third full, a thick typewritten script with pencil notes (no readable text), white wireless earbuds in a white charging case, a half-used pack of paper napkins, a small framed photo of a man and two girls on an embankment (small, tiny faces) near the mirror. A phone charger is plugged into the wall socket to the left of the table, its cable hanging down over the table edge, connected to NOTHING, and there is no phone anywhere in the frame. In the SECOND PLANE on the left, slightly out of focus but recognisable: the open brown leather men's bag on the chair, and sticking out of it a black plastic weekly pill organiser and the corner of a book. Horizontal 4:3. No numbers, no ruler, no markers. +NEG`

Кадр 3, `paper/1-10-rack.jpg`:

> `Same dressing room as in the reference image. New view: the clothes rack by the door, filling the frame. On it: a black wool coat, a grey wool scarf, and a stage costume for the first act (black tailcoat, waistcoat, white shirt) on hangers. A pair of black men's shoes on the floor under the rack. Part of the wall behind. Horizontal 4:3. No numbers, no ruler, no markers. +NEG`

Чек-лист 21–23 (по подписям из `1-10.md`): **21** — виден кресло с пиджаком (6), стул с сумкой (17), вешалка с костюмом (4), диван (19); окон нет; **22** — часы (8), набор грима (9), бутылка (11), текст роли (12), **зарядка с висящим кабелем без телефона (13)**, наушники (14), сумка (17) с таблетницей на втором плане; **телефона нет нигде**; **23** — пальто (1), шарф (2), костюм (4), туфли (5). Номерки-указатели с цифрами и линейку добавляю я.

### 4.7. Кабинет худрука (32, 33)

Деталей мало, но есть жёсткие пункты из `content/paper/2-06.md`. Один чат.

Кадр 1, `paper/2-06-room.jpg`:

> `Photorealistic documentation photo of the office of the artistic director of a provincial theatre, taken from the entrance door in the morning, grey November daylight from the window plus a ceiling lamp. A large writing desk, a separate side table for meetings, bookcases full of books, theatre posters and framed certificates on the walls (abstract, no readable text), a sofa by the window. Nobody in the room. Tidy-lived-in, wide view, horizontal 3:2. +NEG`

Кадр 2, `paper/2-06-office.jpg` (кадр 1 как образец комнаты):

> `Same office as in the reference image. A close view of the writing desk from the visitor's side. On the desk: stacks of documents; a black ring binder folder with a blank white label sticker on its front (leave the label blank); a diary; a desk pen set; reading glasses; a desk lamp; a landline desk telephone; TWO coffee cups on saucers, both with coffee dregs left, and on the rim of one of them a faint lipstick mark. Among the papers lies a small plain white-and-blue pharmacy medicine box, tiny and with no readable text and no manufacturer logo. Do not add a blood pressure monitor. Horizontal 3:2. +NEG`

Чек-лист: **две** чашки на блюдцах; **на одной след помады**; папка с пустой этикеткой (текст «Фонд „Сцена“: отчёт для администрации города» накладываю я); мелкая упаковка лекарства есть, но не бросается в глаза (читается при увеличении; надпись «Анаприлин» накладываю я **только если сценарий оставит эту деталь** — вопрос к сценаристу №3 в `STORY-CHANGES.md`); тонометра нет.

### 4.8. Кадры камеры у служебного входа (24–31)

Источник — `content/paper/2-03.md`: камера **над служебной дверью, направлена вниз**: в кадре крыльцо, дверь и часть двора; внутрь здания не видно. 10.11.2026, 19:30–20:00 — **ночь**, поэтому ч/б «ночной» кадр с фонарём над дверью. Олег (охранник) курит; водитель Дарья сидит в машине всё время. Номер машины не нужен (пустой/размытый).

Работать в **одном чате**, кадр за кадром, каждый раз редактируя предыдущее изображение («edit the previous image, keep the camera, porch, door, yard and car IDENTICAL»). Образцы лиц загружаются там, где человек впервые появляется. Таймкоды и подписи **не просить**: накладываю я.

Кадр 1 → `paper/2-03-01.jpg` (**и основа для 7 и 8**), без образцов:

> `Still frame from a fixed outdoor CCTV camera mounted high above the service entrance door of a theatre and pointing steeply down: we see the porch with three concrete steps, a closed grey metal service door with a small lamp above it, and part of the yard with asphalt. Night, a November evening; black-and-white, grainy, low-resolution infrared-like surveillance look, wide-angle barrel distortion, vignetting. Parked right by the porch: a dark passenger sedan (generic shape, no badges, number plate blank), seen from above; a person sits in the driver's seat behind the windshield. Nobody else. Horizontal 16:9. +NEG`

| Файл | Что поменять (запрос в том же чате) | Образцы |
|---|---|---|
| `2-03-02.jpg` | `Edit the previous image, keep camera, porch, door, yard and car IDENTICAL. The door is open a little and a heavyset man aged about 64 in a dark security-guard-style jacket (no logos) steps out onto the porch, a cigarette in his hand; the face of the man matches the attached photo.` | портрет Олега |
| `2-03-03.jpg` | `Same scene. The door is closed. The man stands on the porch with his BACK to the door and his face toward the yard, smoking. The car and the driver are unchanged.` | — |
| `2-03-04.jpg` | `Same scene. The man now stands next to the car, bending slightly toward the driver's window, which is lowered. The woman driver, about 40 years old, leans toward the window; her face is clearly visible and matches the attached photo. The cigarette is in the man's hand.` | портрет Дарьи (+ Олега, если лицо ушло) |
| `2-03-05.jpg` | `Same scene. The man is back at the door, closed, lighting a second cigarette with a lighter (a small flame). The car stands in the same place, the driver is in the cabin.` | — |
| `2-03-06.jpg` | `Same scene. The man opens the service door and steps inside; the door is half-open, light from inside falls on the porch. The car and the driver unchanged.` | — |
| `2-03-07.jpg`, `2-03-08.jpg` | **Генерировать не нужно.** Крыльцо пустое, дверь закрыта, машина и водитель на месте = кадр 1. Я сделаю из `2-03-01.jpg` два кадра с чуть другим шумом и яркостью | — |

Чек-лист (по подписям 2-03): **1** дверь закрыта, машина, человек в салоне; **2** охранник выходит с сигаретой; **3** он на крыльце спиной к двери; **4** у машины у опущенного стекла, **лицо Дарьи различимо**; **5** прикуривает у двери; **6** входит; во всех кадрах: **та же машина на том же месте**, тот же ракурс; никакой подписи; в кадрах 1 и 7–8 никого, кроме водителя. Где ошибается: «плывёт» машина и крыльцо от кадра к кадру, исчезает окно или появляется второй человек, сигарета в руке «сливается» с пальцами.

### 4.9. Не нужно делать

Билет 3-07, уведомление 3-03, скриншоты чатов 4-06 и 4-12 и аватарки в них — это графика, не фото; их строят из `content/` сам движок или оркестратор. От автора они не требуются.

---

## 5. Видео Волкова (Kling AI)

> **Решение автора 23.10.2026: видео ≈ 5 секунд, одна генерация Kling, без склеек и без деления аудио на части.** Вместо монолога из 22 строк — **две строки** (Лермонтов, «Маскарад», д. I, сц. 3, выход 5, строки 21–22): «Без них нет у меня ни счастья, ни души, / Ни чувства, ни существованья!». Итоговый файл **5–6 с**. Актуальные текст с ударениями, режиссура и запрос Kling — в `docs/PRODUCTION.md` §4.3. Всё ниже про «40–60 с», «50–58 с», 22 строки, части 1 и 2 — **устарело** и оставлено для истории; неизменно главное: **днём, окно с дневным светом хорошо видно в кадре всё видео** (улика).

Путь: **кадр-основа (Gemini) + аудио монолога (XTTS у меня) → Kling → MP4 → моя доводка**. Ограничения из `content/pages/video/page.yaml` и 1-08 (служебная отметка): Слава **в сценическом костюме** читает монолог **в помещении, похожем на репетиционный зал**; продолжительность (раньше «около 1 мин», с 23.10 — 5–6 с); **днём, окно с дневным светом в кадре** (алиби — вечер); файл `VID_20261108_141203.mp4`, создан 08.11.2026 14:12:03; в карточке заявлено 1920 × 1080.

### 5.1. (а) Кадр-основа в Gemini → `work/video_base_frame.jpg`

Загрузите утверждённый портрет Славы (`volkov.jpg`) и 1–2 сырых образца.

> `Use the attached images as the identity reference for the man. Create a photorealistic frame of this same man, about 31 years old, in a bright rehearsal hall of a provincial theatre on an afternoon in early November, around 14:00. Shot like a smartphone video propped on a chair: completely static, horizontal 16:9, he stands centred, facing the camera, framed from the belt up, looking straight into the lens, mouth closed and relaxed, arms hanging down relaxed, no hands near the face, head upright. He wears a dark 19th-century stage costume: black tailcoat, white shirt with a high collar, dark cravat, dark waistcoat, no hat. Behind him on one side, a large window with CLEAR NATURAL DAYLIGHT: an overcast grey November sky and bare tree branches visible outside, the window clearly lit and clearly visible in the frame. Wooden floor, plain light wall, a long wall mirror at the left, a plastic water bottle on a chair. Flat, slightly amateur daylight, natural skin, no beauty filter. +NEG`

Чек-лист кадра (его лицо Kling будет анимировать — повторять нельзя, поэтому проверьте строго):

- [ ] лицо **анфас**, глаза в камеру, рот закрыт, руки не у лица;
- [ ] **окно с дневным светом хорошо видно** (не вечер, не ночь, не лампы), за окном ноябрь: серое небо, голые ветки (не зелень и не снег);
- [ ] сценический костюм: фрак, сорочка, шейный платок;
- [ ] комната похожа на репетиционный зал (паркет, зеркало);
- [ ] нет текста и логотипов; узнаваемо лицо Славы;
- [ ] 16:9, лицо крупное (не меньше четверти высоты кадра).

До 4 попыток. Утверждённый кадр отправьте мне **до** оплаты Kling.

### 5.2. (б) Аудио — монолог Арбенина (делаю я), текст

Голос Славы (XTTS-v2 / ElevenLabs), **с 23.10 — две строки, ≈ 4–5 с речи** (прежний вариант на 40–60 с — ниже, устарел). Текст подлинный, **Лермонтов, «Маскарад»**, общественное достояние (на странице Викитеки указана лицензия PD-old-70, автор 1814–1841).

**Источник:** [ru.wikisource.org, Маскарад (Лермонтов)/Действие первое](https://ru.wikisource.org/wiki/%D0%9C%D0%B0%D1%81%D0%BA%D0%B0%D1%80%D0%B0%D0%B4_(%D0%9B%D0%B5%D1%80%D0%BC%D0%BE%D0%BD%D1%82%D0%BE%D0%B2)/%D0%94%D0%B5%D0%B9%D1%81%D1%82%D0%B2%D0%B8%D0%B5_%D0%BF%D0%B5%D1%80%D0%B2%D0%BE%D0%B5) — **действие первое, сцена третья, выход пятый**, реплика Арбенина Нине (начинается словами «Послушай, Нина!..»). Текст загружен с ru.wikisource.org 20.10.2026 в исходном виде (action=raw) и взят оттуда дословно, не по памяти. Редакция Викитеки — четырёхактная, датирована 1835 г.; в других изданиях нумерация действий и сцен может отличаться.

Отрывок: 22 строки, **128 слов**, ≈ 50–58 с чтения в сценическом темпе (проверю по готовому аудио; цель 40–60 с):

> Послушай, Нина!.. я смешон, конечно,
> Тем, что люблю тебя так сильно, бесконечно,
> Как только может человек любить.
> И что за диво? у других на свете
> Надежд и целей миллион:
> У одного богатство есть в предмете,
> Другой в науки погружен,
> Тот добивается чинов, крестов — иль славы,
> Тот любит общество, забавы,
> Тот странствует, тому игра волнует кровь…
> Я странствовал, играл, был ветрен и трудился,
> Постиг друзей, коварную любовь,
> Чинов я не хотел, а славы не добился.
> Богат и без гроша был скукою томим.
> Везде я видел зло и, гордый, перед ним
> Нигде не преклонился.
> Все, что осталось мне от жизни, это ты,
> Созданье слабое, но ангел красоты:
> Твоя любовь, улыбка, взор, дыханье…
> Я человек — пока они мои,
> Без них нет у меня ни счастья, ни души,
> Ни чувства, ни существованья!

Отрывок самостоятельный, сюжетных подсказок про отравление не содержит. Если Kling не принимает аудио такой длины — делю по границам фраз (§5.3, пункт 7): часть 1 — строки 1–10, часть 2 — строки 11–22.

Что я делаю: клонирую голос Славы по образцу, ставлю ударения в стихе, собираю дубли, нормализую громкость, отдаю `rehearsal_audio.mp3` (или части) и точную длительность. Образец и клон показываю автору на прослушивание **до** Kling.

### 5.3. (в) В Kling: загрузка кадра и аудио

**Что в источниках, а что нет.** `MEDIA-AI-OPTIONS` §3: Kling Standard ≈ $6–10 в месяц; по одному обзору — 66 бесплатных кредитов в день; **какой тариф открывает Avatar, источники расходятся — проверить перед оплатой**. Ограничения по длине аудио и расход кредитов на секунду в источниках проекта не указаны; смотрите в интерфейсе.

Порядок:

1. Зайдите на [klingai.com](https://klingai.com), войдите.
2. **Проверка на бесплатных кредитах (до оплаты):** найдите инструмент, который принимает **картинку и аудио** и делает говорящее видео (в разных версиях называется Avatar / Lip Sync / Digital Human — точное название в интерфейсе не проверялось). Если инструмента нет в бесплатном режиме, это не значит, что его нет на Standard — в тарифах смотрите описание; если нигде не видно — переходите к запасному плану (§8.3).
3. Загрузите `work/video_base_frame.jpg` и короткое пробное аудио (я пришлю 10-секундный фрагмент). Сделайте пробный ролик и проверьте губы и лицо.
4. Если проба хорошая и Avatar доступен — оплатите **Standard на 1 месяц** (проверьте цену на странице тарифов; автопродление выключите сразу).
5. Загрузите кадр и полное аудио. Если есть поле запроса, вставьте:
   > `A man in a 19th-century theatre costume recites a dramatic monologue in Russian. Natural lip movement in sync with the audio, subtle natural head movements and facial expressions, eyes mostly on the camera. Static camera, no zoom, no camera movement. The bright daylight from the window stays constant. Hands stay down.`
6. Остальные настройки: качество — максимальное из доступных; разрешение — максимум (нужно 1080p, если есть); водяной знак — убедитесь, что у Standard его нет (проверьте до скачивания; если есть — это повод вернуться к проверке тарифа).
7. **Если аудио не принимается целиком:** загрузите части (`rehearsal_part1`, `rehearsal_part2`) в **тот же кадр**, получите два ролика; я склею их в ffmpeg с мягким переходом. Лишний вечер это не добавит.
8. Скачайте MP4 в лучшем качестве. Сохраните **все удачные варианты**, не только один.

**Сколько попыток закладывать:** 3–5 генераций (5 с каждая; до 23.10 было «4–6 на полный монолог») (кредиты на секунду в источниках не указаны — посмотрите расход после первой генерации и пересчитайте). Если за месяц Standard кредиты кончаются раньше времени, не докупайте — пишите мне.

**Критерии приёмки видео (смотреть на телефоне):**

- [ ] губы попадают в звуки, нет «проглоченных» фраз;
- [ ] лицо стабильно, не «плывёт» и не превращается в другого человека;
- [ ] **окно в кадре всё время светлое, дневное** (не мигает и не темнеет);
- [ ] камера не дрейфует, рук с лишними пальцами нет;
- [ ] длительность **5–6 с** (решение автора 23.10), одна генерация, без склейки;
- [ ] костюм не меняется.

### 5.4. (г) Что прислать мне

1. Лучший MP4 (и ещё один запасной);
2. `work/video_base_frame.jpg`;
3. какие настройки использовали и сколько попыток ушло.

Что делаю после: сжатие до **≤ 25 МБ**, H.264 + AAC, 16:9, масштаб до 1920 × 1080 (если Kling выдал меньше — это апскейл; если нужно честное указание, сценарий поправит карточку файла — вопрос 5 в §9), проверка на телефоне, при желании запись в метаданные `creation_time` = 08.11.2026 14:12:03, имя `rehearsal.mp4`. **Не забудьте отменить подписку Kling.**

---

## 6. Голос звонка 1-05

Файл `audio/anonymous_call.mp3`. Источник — `content/paper/1-05.md`; шаблоны заменены рабочими пометками. Голос Абонента — дядя (Кирилл), клон (XTTS-v2 или ElevenLabs), **но с маскировкой** (решение автора 23.10, вариант «а»): звонящий говорит сипло и приглушённо, «через платок», ближе к трубке; игроки узнают его по фразе-привычке, а не по тембру. В 1-05 это отмечено: «голос приглушённый, сиплый, по-видимому, намеренно изменён». Голосовые Кирилла в «Круге» (`krug-kirill/voice-02.mp3`, `voice-03.mp3`) озвучиваются **обычным** голосом клона, без маскировки — разница на слух должна быть заметной, но не «шпионской». Дежурный (в `content/characters.yaml` это Олеся Дронова, женщина) — **не клон**, я озвучу её стандартным голосом XTTS (решение продюсера: запись входящих вызовов содержит обе стороны, и длительность 47 с в 1-05 относится ко всему разговору).

**Фоновых звуков нет** (по тексту 1-05); телефонная полоса и приглушённость — только фильтр.

| Кто | Реплика (в скобках — не озвучивается) |
|---|---|
| Дежурная | Дежурная часть, слушаю вас. |
| Абонент | Это насчёт театра. Насчёт [фамилия Воронцова, род. п.]. |
| Дежурная | Что именно вы хотите сообщить? |
| Абонент | [фамилия Воронцова] умер не просто так. Я не шучу. Вы слышите? Не просто так. |
| Дежурная | Представьтесь, пожалуйста. Откуда вам это известно? |
| Абонент | Не перебивайте, у меня минута. И всё рассказать. (фраза «Он собирался уехать» вырезана 24.10 — S-81) Посмотрите, кому это мешало. |
| Дежурная | Что рассказать? Кому? Вы можете подъехать и дать объяснение? |
| Абонент | (пауза) Записали? Собирался всё рассказать. И не успел. |
| Дежурная | Записал. Спасибо за сигнал. Теперь назовите себя. |
| Абонент | **Было бы за что.** Всё, больше ничего не скажу. |
| Дежурная | Подождите. Кто вы? |
| (конец) | (Абонент завершил вызов.) Тишина 0,5 с, обрыв. |

Заметки к тексту:

- В 1-05 дежурный говорит «**Записал**» (мужской род), хотя в `characters.yaml` дежурная — женщина (Олеся Дронова). Это несоответствие в самом тексте; озвучиваю как в документе и сообщаю оркестратору (вопрос 6 в §9).
- «Было бы за что» — речевая привычка Кирилла, `w.clues.kirill_habit` (на «спасибо» дежурной в предыдущей реплике, как и положено). В тексте 1-05 фраза звучит **один раз**; шот-лист просит «1–2 раза», но источник — 1-05, поэтому один.
- Фамилии подставляю те, что стоят в `content/characters.yaml` на момент озвучки (сейчас «Воронцов»). Если при шаге P09 они будут заменены настоящими — звонок переозвучивается (минуты работы у меня).

Что делаю я: XTTS-v2 с клоном дяди (для Абонента — по записи «вполголоса, быстро», если автор её пришлёт) и стандартным женским голосом (для Дежурной); сборка диалога с паузами; подгонка длительности к **47 с** (в 1-05 «0 мин 47 с», на странице «0:47»); телефонный фильтр ffmpeg (полоса ≈ 300–3400 Гц, лёгкая компрессия, моно), приглушённость голоса Абонента; MP3 128 кбит/с.

**Маскировка голоса Абонента (реплики Дежурной — без изменений, обычный голос):**

- *Как говорить (клон).* Клон Кирилла, но тише, ниже, сипло, ближе к трубке; темп быстрый, на выдохе, шёпот-полушёпот без «театральности». Фраза «Было бы за что» — **с обычной дядиной интонацией** (сухо-иронично, чуть устало), чтобы по ней узнавали, а не по тембру.
- *ElevenLabs (настройки по умолчанию подбираются на пробе, ориентир):* Stability 35–45 % (ниже — живее, «сипит» и срывается), Similarity 60–70 % (не 100 %: маскировка должна ослабить тембр), Style Exaggeration 15–30 %, Speaker Boost — выключен. В тексте реплик допустимы многоточия и запятые для пауз; если модель поддерживает теги — `[whispers]`/`[hoarse]` в начале реплики (проверить на пробе). Записать по 3–4 дубля каждой реплики, взять самый сиплый и разборчивый.
- *На склейке (делаю я):* только на дорожке Абонента — срез низа до ≈ 300 Гц и верха до ≈ 3400 Гц, сдвиг высоты на −1…−2 полутона без изменения темпа, мягкая «приглушённость» (спад выше ≈ 2,5 кГц, −3…−4 дБ), лёгкая компрессия, громкость на 4–6 дБ ниже Дежурной, шум дыхания не добавлять. Общий телефонный фильтр (≈ 300–3400 Гц, моно) — на обе стороны, как раньше.
- *Чего избегать:* «робота», вокодера, сильного сдвига высоты (≥ 4 полутонов) — звонок не должен звучать как фильм про шпионов. Если после маскировки не разобрать «Было бы за что» — ослабить фильтр, а не переписывать реплику.

Критерии приёмки (прослушивание автором): голос **не** узнаётся сразу как дядин (приглушён, сипит), но интонация и фраза «Было бы за что» узнаваемы; разборчиво; звучит тихо и быстро; 47 с ±1.

---

## 7. Куда сохранять и как присылать

### 7.1. Структура папок на компьютере автора

Повторяет `media/`; имена файлов строго как в §1.

```
detgame-media/
  portraits/   voroncov.jpg zavyalov.jpg volkov.jpg marina.jpg kirill.jpg stas.jpg
               reznikova.jpg gnedich.jpg viktor.jpg oleg.jpg inna.jpg dmitriy.jpg
               volskaya.jpg gromov.jpg                                     (14)
  news/        voroncov_arbenin.jpg                                         (1)
  gromov/      meeting.jpg cover.jpg                                        (2)
  inna/        brooch.jpg                                                   (1)
  lab/         station_cam.jpg pillbox.jpg                                  (2)
  paper/       1-10-general.jpg 1-10-table.jpg 1-10-rack.jpg
               2-03-01.jpg … 2-03-06.jpg   (7 и 8 делаю я из 01)
               2-06-room.jpg 2-06-office.jpg                                (11 + 2 мои)
  video/       rehearsal.mp4                                                (1)
  work/        video_base_frame.jpg  brooch_ref.jpg
  _attempts/   неудачные и запасные варианты
```

Аудио (`audio/anonymous_call.mp3`) делаю я; от автора — только голосовые образцы (§2.3). Фото-образцы лиц — отдельная папка `refs/` вне `detgame-media/`.

### 7.2. Как присылать

- Промежуточно (после каждого вечера): картинки или архив в чат оркестратору, чтобы я мог проверять улики по чек-листам и вернуть правки до следующего вечера.
- В конце: **один архив** `detgame-media.zip` со структурой выше. Оценка размера: 33 JPEG × ≈ 1–2 МБ + видео ≤ 30 МБ ≈ 70–100 МБ. Если чат не принимает такой размер — выложить в облако по ссылке только для меня и удалить после получения (канал уточняется, вопрос 4 в §9).
- Не добавляйте таймкоды, подписи, рамки и «обрезку» в картинки сами.

### 7.3. Что делаю я после получения

| Что | Как |
|---|---|
| Раскладка | кладу в `media/` по путям из §1, проверяю `python -m engine build` / `check` / `release` (список пропавших файлов) |
| Сжатие | портреты ≤ 300 КБ, лента ≤ 300 КБ, улики ≤ 1 МБ; JPEG/WebP, без метаданных генератора |
| Обрезка | убираю возможный знак Gemini в углу, довожу кадры до нужных пропорций (портреты 1:1, 2-03 16:9, обложка 16:6) |
| Накладки | таймкод «30.10.2026 14:37:22 КАССА-2» на 19; таймкоды 19:30:06 … 20:00:00 на 24–31; номерки и линейка на 21–23; этикетка папки на 33; табличка на 16; подписи дней и «S» на таблетнице 20, если Gemini ошибся |
| Кадры 7–8 | из `2-03-01.jpg`: чуть иной шум и яркость |
| Ч/б и зерно | для 19 и 2-03 приведу к серому и добавлю зерно камеры |
| Видео | сжатие, H.264 + AAC, ≤ 25 МБ, проверка на телефоне |
| Звонок | XTTS-v2 + телефонный фильтр, 47 с |
| Образцы | удаляю `media/_refs/` после приёмки |
| Отчёт | список файлов, расхождения с чек-листами, что осталось |

---

## 8. Бюджет, сроки, чек-лист

### 8.1. Бюджет (ориентир, цены проверять по ссылкам — в `MEDIA-AI-OPTIONS` они «ориентир на октябрь 2026»)

| Статья | Сумма |
|---|---|
| Голос: XTTS-v2 у оркестратора | 0 |
| Фото: Gemini, бесплатный лимит | 0 |
| Видео: Kling Standard, 1 месяц ([klingai.com](https://klingai.com)) | **≈ $6–10** |
| Посредник / иностранная карта для оплаты | зависит от выбранного способа; цифр в источниках проекта нет |
| **Итого по набору «А»** | **≈ $6–10** (+ расходы на оплату из России) |

Если Avatar на Standard недоступен: запасной вариант — Hedra Basic ≈ $15 в месяц ([hedra.com/plans](https://www.hedra.com/plans)), набор «Б» из `MEDIA-AI-OPTIONS` (кредиты: 3–6 за секунду, 1 500 кредитов; бесплатно 100 кредитов с водяным знаком — хватит на пробу).

После готовности **отмените подписку**: тарифы помесячные с автопродлением.

### 8.2. Сроки

4 вечера Gemini + 1 вечер Kling (можно совмещать), плюс вечер 0 на образцы и 5-й в запас: **≈ 5 календарных дней, по 2–3 часа**. Узкие места: исчерпание лимита Gemini в день (≈ 20 картинок, по обзорам) и согласие/присылка образцов.

### 8.3. Если что-то не получается

| Проблема | Что делать |
|---|---|
| Gemini отказывается работать с фото конкретного человека (особенно с несовершеннолетним) | сообщить мне; Марину можно сгенерировать без образца (вымышленное лицо) или попробовать ChatGPT ([chatgpt.com](https://chatgpt.com), `MEDIA-AI-OPTIONS` §4). Работу сервисов с фото людей и детей в источниках проекта не проверял |
| Лимит Gemini кончился | дождаться следующего дня; Gemini AI Pro ≈ $20 в месяц даёт ≈ 100 картинок в день (`MEDIA-AI-OPTIONS` §4) |
| Улика не получается за 5 попыток | пришлите лучший вариант: я правлю детали в Pillow; либо один раз фото предмета на телефон (таблетница, брошь) |
| Kling не отдаёт Avatar на Standard | Hedra Basic (см. выше) |
| Видео «кукольное» | вернуться к кадру (проще лицо, меньше движения), другой фрагмент аудио |

### 8.4. Чек-лист «готово»

- [ ] Согласия получены; образцы лиц (14 ролей) и голосов (2) отправлены;
- [ ] 14 портретов: одинаковый фон и свет, возраст как в игре, узнаваемы;
- [ ] `news/voroncov_arbenin.jpg`;
- [ ] `gromov/meeting.jpg`: **летняя зелень в окне**, пустая табличка для надписи; `gromov/cover.jpg`: без гербов и флагов;
- [ ] `inna/brooch.jpg`: брошь совпала с описью 2-08 по пяти признакам;
- [ ] `lab/station_cam.jpg`: окно № 2, Воронцов у окна, Волков у колонны в 5–7 м и смотрит на него, ч/б, сверху;
- [ ] `lab/pillbox.jpg`: 7 отделений, ПН и ВТ пусто, СР «S», ЧТ риска, ПТ–ВС «S»;
- [ ] `paper/1-10-*`: три кадра, зарядка без телефона, таблетница на втором плане, окон нет;
- [ ] `paper/2-03-01…06`: одна и та же машина и крыльцо; лицо Дарьи различимо в 04; 07–08 делаю я;
- [ ] `paper/2-06-*`: две чашки, помада на одной, папка с пустой этикеткой, мелкая упаковка лекарства;
- [ ] `video/rehearsal.mp4`: 5–6 с, ≤ 25 МБ, окно с дневным светом, костюм, голос Славы;
- [ ] `audio/anonymous_call.mp3`: 47 с, «Было бы за что», голос дяди;
- [ ] файлы лежат по путям из §1, сборка и `engine check` проходят (после этого);
- [ ] подписка Kling отменена; образцы лиц и голосов удалены из рабочей папки.

---

## 9. Открытые вопросы

1. ~~Марина — в жизни 15 лет, в игре 24.~~ Решено автором 21.10: 24 года, согласие родителей получено.
2. **`content/documents/3-06.md` без поля `media:`.** Для `lab/pillbox.jpg` нужна строка `media: ["lab/pillbox.jpg"]` (шот-лист §2). Это правка `content/`, прошу оркестратора или сценариста.
3. **Фотосеть Инны:** пока в content только одно фото (брошь). Нужны ли ещё 8–11 «атмосферных» кадров (кофе, еда, кошки) и под какими путями — решение сценариста.
4. **Канал передачи файлов:** принимает ли чат оркестратора аудио, `.zip` и файлы ≈ 100 МБ? Если нет — нужен обмен по ссылке.
5. **Разрешение видео:** в карточке файла 4-07 написано «1920 × 1080». Если Kling даст 720p, апскейл допустим или сценарист поправит карточку на фактическое разрешение.
6. ~~1-05: «Записал» вместо «Записала».~~ Исправлено оркестратором 20.10: реплика по полу дежурной (`c.duty_officer.g(...)`) — дежурную озвучиваем женским голосом.
7. **Упаковка «Анаприлина» на фото 2-06** зависит от вопроса сценаристу № 3 в `STORY-CHANGES.md`: если деталь уберут, запрос кабинета теряет пункт про упаковку.
8. **Возраст Инны (29) и Олега (64):** в таблице персонажей возраст в жизни не указан. Нужен автору для просьбы «омолодить / состарить» к генератору. У Инны по таблице роль — мама мужа сестры, при значительной разнице с 29 годами портрет может получиться слишком непохожим: решение автора — оставить 29 или поправить `age` в content.
9. **Видимая метка Gemini** и **доступность Gemini и Kling из России** — источниками проекта не подтверждены.
10. **Что сгенерировано правдоподобно, но не проверено мной** (сервисы не вызывались): точные названия кнопок в Gemini и Kling, длина аудио, которую принимает Avatar, расход кредитов на секунду, тариф, открывающий Avatar.
