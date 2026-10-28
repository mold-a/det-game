// Сквозные тесты вымышленных страниц (P06 п.6, docs/04 «Вымышленные страницы», docs/02 §3.8–3.9).
//
// Запуск — после `python -m engine build` и `python -m engine dump-answers`, против запущенного
// `python -m engine serve` (адрес — DETGAME_BASE_URL, иначе baseURL из playwright.config.js):
//   DETGAME_BASE_URL=http://127.0.0.1:8011 PW_CHROMIUM_PATH=/opt/pw-browsers/chromium npx playwright test tests/e2e/pages.spec.ts
//
// Ключи закрытых страниц и пароль облака — из tests/.answers.json (FORMATS §8), не из кода.
// Ожидаемые значения улик — из docs/04 (они же в content/world.yaml).

import { test, expect, type Page, type Locator } from "@playwright/test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const answers = JSON.parse(readFileSync(join(here, "..", ".answers.json"), "utf8"));
type PageInfo = { slug: string; access: "open" | "key" | "password"; url: string; key?: string; password?: string; passwordHint?: string | null };
const PAGES: Record<string, PageInfo> = Object.fromEntries(answers.pages.map((p: PageInfo) => [p.slug, p]));

// Даты улик читаем из content/ (world.yaml, page.yaml), а не зашиваем: сюжет сдвигают целиком (сдвиг дат +2 дня).
const CONTENT = join(here, "..", "..", "content");
const readContent = (rel: string) => readFileSync(join(CONTENT, rel), "utf8");
const yamlStr = (text: string, key: string) => {
  const m = text.match(new RegExp(`^\\s*${key}:\\s*"([^"]+)"`, "m"));
  expect(m, `в content есть ${key}`).toBeTruthy();
  return m![1];
};
/** "2026-11-13T07:50:12" -> "13.11.2026, 07:50:12" (как показывают страницы). */
const ruDateTime = (iso: string) => {
  const [d, t] = iso.split("T");
  const [y, m, dd] = d.split("-");
  return `${dd}.${m}.${y}${t ? ", " + t : ""}`;
};
const ruDate = (iso: string) => ruDateTime(iso.split("T")[0]);
const WORLD = readContent("world.yaml");
const CALL_ISO = yamlStr(WORLD, "anonymous_call");
const PUBLICATION_ISO = yamlStr(WORLD, "publication");
const VIDEO_FILE = yamlStr(WORLD, "volkov_video_file");
const VIDEO_CREATED_ISO = yamlStr(WORLD, "volkov_video_created");
const CLOUD_LAST_CONFIRMATION_ISO = yamlStr(readContent("pages/cloud/page.yaml"), "last_confirmation");
const GROMOV_MEETING_ISO = (() => {
  const m = readContent("pages/gromov/page.yaml").match(/datetime: "([^"]+)"\s*\n\s*geo:[^\n]*\n\s*text: "Рабочее совещание/);
  expect(m, "в gromov/page.yaml есть пост «Рабочее совещание»").toBeTruthy();
  return m![1];
})();

const BROKEN = "Ссылка повреждена. Отсканируйте QR-код ещё раз";
const PHONE = { width: 360, height: 780 };

if (process.env.DETGAME_BASE_URL) test.use({ baseURL: process.env.DETGAME_BASE_URL });

/** Открыть страницу как по QR; закрытые — дождаться расшифровки. */
async function openPage(page: Page, slug: string) {
  const p = PAGES[slug];
  expect(p, `страница ${slug} есть в .answers.json`).toBeTruthy();
  await page.goto(p.url);
  if (p.password) {
    // облако: один замок (access password) или два (ключ QR в адресе + пароль)
    await page.locator('input[name="password"]').fill(p.password!);
    await page.getByRole("button", { name: "Войти" }).click();
  }
  if (p.access !== "open") await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 15000 });
}

/** Элемент улики видим и целиком помещается по ширине экрана (не обрезан). */
async function expectClue(loc: Locator, width = PHONE.width) {
  await expect(loc).toBeVisible();
  await loc.scrollIntoViewIfNeeded();
  const box = await loc.boundingBox();
  expect(box, "у улики есть размеры").toBeTruthy();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(width + 0.5);
}

async function expectNoHorizontalScroll(page: Page) {
  const [sw, iw] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  expect(sw, "нет горизонтальной прокрутки").toBeLessThanOrEqual(iw);
}

test.describe("телефон 360 px", () => {
  test.use({ viewport: PHONE, hasTouch: true });

  test("call: карточка вызова и свой аудиоплеер", async ({ page }) => {
    await openPage(page, "call");
    await expectClue(page.locator('[data-clue="datetime"]'));
    await expect(page.locator('[data-clue="datetime"]')).toHaveText(ruDateTime(CALL_ISO));
    await expect(page.getByText("Номер скрыт")).toBeVisible();
    // Плеер собственный: нет стандартных controls, есть кнопки и ползунок перемотки.
    await expect(page.locator("audio[controls]")).toHaveCount(0);
    const player = page.locator('[data-player="audio"]');
    await expect(player).toBeVisible();
    await expect(player.locator('[data-act="play"]')).toBeVisible();
    await expect(player.locator('[data-role="seek"]')).toBeVisible();
    await expect(player.locator('[data-role="cur"]')).toHaveText("0:00");
    if (await player.getAttribute("data-missing")) {
      await expect(player.getByText(/Здесь будет/)).toBeVisible();
    } else {
      await expect(player.locator('[data-act="play"]')).toBeEnabled();
    }
    // Решение автора 24.10: расшифровки нет нигде, в карточке — отсылка к сопроводительному листу 1-05.
    await expect(page.getByText("Сведения о вызове — в материалах дела (1-05).")).toBeVisible();
    await expect(page.getByText(/Расшифровка/)).toHaveCount(0);
    await expectNoHorizontalScroll(page);
  });

  test("gromov: пост «Рабочее совещание» с геометкой Северогорск (дата из content)", async ({ page }) => {
    await openPage(page, "gromov");
    const post = page.locator(".kr-post", { hasText: "Рабочее совещание по развитию культурной инфраструктуры" });
    await expect(post).toHaveCount(1);
    await expectClue(post.locator("time"));
    await expect(post.locator("time")).toHaveText(ruDateTime(GROMOV_MEETING_ISO));
    await expectClue(post.locator(".kr-post__geo"));
    await expect(post.locator(".kr-post__geo")).toHaveText("Северогорск");
    // Кнопок аккаунта нет (REDESIGN §4.1): кликабельно только то, что ведёт к содержимому.
    for (const name of ["Подписаться", "Написать", "Войти"]) {
      await expect(page.getByRole("button", { name, exact: true })).toHaveCount(0);
    }
    await expectNoHorizontalScroll(page);
  });

  test("news: статья без запрещённых слов", async ({ page }) => {
    await openPage(page, "news");
    await expectClue(page.locator("h1"));
    await expect(page.locator("h1")).toContainText("скончался");
    await expect(page.getByText("Срочно", { exact: true })).toBeVisible();
    const text = (await page.locator("body").innerText()).toLowerCase().replaceAll("ё", "е");
    for (const word of ["астма", "таблетк", "отравлен", "21:18"]) expect(text).not.toContain(word);
    await expectNoHorizontalScroll(page);
  });

  // 26.10: брошь больше не улика — селфи «Сын подарил» (inna/brooch.jpg); 28.10 — пост в «Круге» (страница по QR 2-09,
  // «Кадр» убран). Страница и дата поста — из content, не из кода.
  test("фото Рябовой: селфи с брошью в «Круге», снимок открывается крупно", async ({ page }) => {
    const docs = readContent("documents.yaml");
    const slug = docs.match(/id: "2-09"[^}\n]*page: ([a-z0-9-]+)/)![1];
    const m = readContent(`pages/${slug}/page.yaml`).match(/datetime: "([^"]+)"\s*\n[^\n]*\n\s*photo: "inna\/brooch\.jpg"/);
    expect(m, `в ${slug}/page.yaml есть пост с inna/brooch.jpg`).toBeTruthy();
    await openPage(page, slug);
    const post = page.locator(".kr-post", { has: page.locator(`time[datetime^="${m![1]}"]`) }).first();
    await expect(post).toBeVisible();
    await expect(post.locator(".kr-post__photo img")).toBeVisible();
    await post.locator(".kr-zoom--photo").click();
    const zoom = page.locator("dialog.svc-zoom[open]");
    await expect(zoom).toBeVisible();
    await zoom.getByRole("button", { name: "Закрыть" }).click();
    await expect(zoom).toBeHidden();
    await expectNoHorizontalScroll(page);
  });

  test("pharma: противопоказания пропранолола и поиск через base()", async ({ page }) => {
    await openPage(page, "pharma");
    const card = page.locator(".fs-card", { has: page.locator("h2", { hasText: "Пропранолол" }) });
    await expectClue(card.locator("tr", { hasText: "Противопоказания" }));
    await expect(card.locator("tr", { hasText: "Противопоказания" })).toContainText("Бронхиальная астма");
    await expect(card.locator("tr", { hasText: "Побочные эффекты" })).toContainText("бронхоспазм");
    await expect(card.locator("tr", { hasText: "Торговые названия" })).toContainText("Анаприлин");
    // Все карточки одного формата.
    const rowCounts = await page.locator(".fs-card").evaluateAll((els) => els.map((e) => e.querySelectorAll("tr").length));
    expect(new Set(rowCounts).size).toBe(1);
    // Поиск: торговое название, без учёта регистра; действующее вещество; «ё».
    const q = page.locator("#fs-q");
    await q.fill("АНАПРИЛИН");
    await expect(page.locator(".fs-card:visible")).toHaveCount(1);
    await expect(card).toBeVisible();
    await q.fill("пропранолол");
    await expect(page.locator(".fs-card:visible")).toHaveCount(1);
    await q.fill("валерёновая");
    await expect(page.locator(".fs-card:visible")).toHaveCount(1);
    await expect(page.locator(".fs-card:visible h2")).toContainText("Валерианы");
    await q.fill("нет такого препарата");
    await expect(page.locator(".fs-card:visible")).toHaveCount(0);
    await expect(page.locator("#fs-empty")).toBeVisible();
    await q.fill("");
    await expect(page.locator(".fs-card:visible")).toHaveCount(await page.locator(".fs-card").count());
    // Алфавитный порядок карточек.
    const names = await page.locator(".fs-card h2").allTextContents();
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b, "ru")));
    await expect(page.getByText(/Справочник создан для игры/)).toBeVisible();
    await expectNoHorizontalScroll(page);
  });

  test("cloud: вход, плашка, реестр с сортировкой, переписка, замок", async ({ page }) => {
    await openPage(page, "cloud");
    const banner = page.locator('[data-clue="banner"]');
    await expectClue(banner);
    await expect(banner).toContainText(`Публикация по расписанию: ${ruDateTime(PUBLICATION_ISO)}`);
    await expect(banner).toContainText(`Последнее подтверждение: ${ruDateTime(CLOUD_LAST_CONFIRMATION_ISO)}`);
    const row = page.locator(".tc-table tbody tr", { hasText: "знал, что копия" });
    await expect(row).toHaveCount(1);
    await expectClue(row);
    await expect(row).toContainText("Табакерка");

    // Сортировка по цене: по возрастанию, затем по убыванию.
    const priceCol = await page.locator(".tc-table thead th").evaluateAll((ths) => ths.findIndex((t) => t.textContent!.includes("Цена")));
    expect(priceCol).toBeGreaterThanOrEqual(0);
    const prices = () =>
      page.locator(".tc-table tbody tr").evaluateAll(
        (trs, c) => trs.map((tr) => Number((tr as HTMLTableRowElement).cells[c as number].dataset.sort!.replace(/\s/g, ""))),
        priceCol,
      );
    const sortBtn = page.locator(".tc-table thead th").nth(priceCol).locator("button");
    await sortBtn.click();
    let got = await prices();
    expect(got).toEqual([...got].sort((a, b) => a - b));
    await expect(page.locator(".tc-table thead th").nth(priceCol)).toHaveAttribute("aria-sort", "ascending");
    await sortBtn.click();
    got = await prices();
    expect(got).toEqual([...got].sort((a, b) => b - a));
    await expect(page.locator(".tc-table thead th").nth(priceCol)).toHaveAttribute("aria-sort", "descending");

    await page.locator('[data-folder-link="chat"]').click();
    await expect(page.locator('.tc-panel[data-folder="chat"]')).toBeVisible();
    await expect(page.locator('.tc-panel[data-folder="registry"]')).toBeHidden();

    const locked = page.locator(".tc-folder--locked");
    await expect(locked).toContainText("Для");
    await locked.click();
    await expect(page.getByText("Папка защищена отдельным паролем.")).toBeVisible();
    await expectNoHorizontalScroll(page);
  });

  test("video: имя файла и «Свойства файла»", async ({ page }) => {
    await openPage(page, "video");
    await expectClue(page.locator('[data-clue="filename"]'));
    await expect(page.locator('[data-clue="filename"]')).toHaveText(VIDEO_FILE);
    await expect(page.getByText(/Изъято с телефона [А-ЯЁ][а-яё]+/)).toBeVisible();
    const created = page.locator('[data-clue="created"]');
    await expect(created).toBeHidden();
    await page.getByRole("button", { name: "Свойства файла" }).click();
    await expectClue(created);
    await expect(created).toHaveText(ruDateTime(VIDEO_CREATED_ISO).replace(", ", " "));
    await expect(page.locator(".ev-props__panel")).toContainText("Альтаир A54");
    await expectNoHorizontalScroll(page);
  });
});

test.describe("закрытые страницы: ключ", () => {
  test.use({ viewport: PHONE });
  const keyed = Object.values(PAGES).filter((p) => p.access === "key");

  for (const p of keyed) {
    test(`${p.slug}: без ключа — «Ссылка повреждена»`, async ({ page }) => {
      await page.goto(`/p/${p.slug}/`);
      await expect(page.getByText(BROKEN)).toBeVisible();
      await expect(page.locator("#page-content")).toBeEmpty();
    });

    test(`${p.slug}: испорченный ключ — «Ссылка повреждена»`, async ({ page }) => {
      const bad = (p.key![0] === "A" ? "B" : "A") + p.key!.slice(1);
      await page.goto(`/p/${p.slug}/#k=${bad}`);
      await expect(page.getByText(BROKEN)).toBeVisible();
      await page.goto("about:blank"); // иначе смена одного #фрагмента не перезагрузит страницу
      await page.goto(`/p/${p.slug}/#k=not-a-key`);
      await expect(page.getByText(BROKEN)).toBeVisible();
    });

    test(`${p.slug}: ключ убирается из адреса и переживает перезагрузку`, async ({ page }) => {
      await page.goto(p.url);
      if (p.password) {
        // облако с двумя замками: после ключа — форма пароля
        await page.locator('input[name="password"]').fill(p.password);
        await page.getByRole("button", { name: "Войти" }).click();
      }
      await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 15000 });
      expect(new URL(page.url()).hash).toBe("");
      const stored = await page.evaluate((s) => sessionStorage.getItem(`detgame:page:${s}`), p.slug);
      expect(stored).toBe(p.key);
      await page.reload();
      await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 15000 });
      await expect(page.getByText(BROKEN)).toBeHidden();
    });
  }
});

test.describe("облако: пароль", () => {
  test.use({ viewport: PHONE });

  test("неверный пароль — «Неверный пароль», верный — вход, перезагрузка без пароля", async ({ page }) => {
    const p = PAGES.cloud;
    await page.goto(p.url);
    const login = page.locator('input[name="login"]');
    await expect(login).toBeVisible();
    await expect(login).toHaveAttribute("readonly", "");
    const pw = page.locator('input[name="password"]');
    await pw.fill("совсем-не-тот-пароль");
    await page.getByRole("button", { name: "Войти" }).click();
    await expect(page.getByText("Неверный пароль")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("#page-content")).toBeEmpty();
    // Без блокировки: можно сразу попробовать снова, с другим регистром и пробелами по краям.
    await pw.fill(`  ${p.password!.toUpperCase()} `);
    await page.getByRole("button", { name: "Войти" }).click();
    await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 15000 });
    await expect(page.locator('[data-clue="banner"]')).toBeVisible();
    // F13: в sessionStorage — выведенный ключ (43 символа b64u), не пароль.
    const stored = await page.evaluate(() => sessionStorage.getItem("detgame:page:cloud"));
    expect(stored).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(stored).not.toContain(p.password);
    await page.reload();
    await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 15000 });
    await expect(page.locator('input[name="password"]')).toBeHidden();
  });

  test("без ключа QR: ни формы входа, ни логина, ни подсказки — «Ссылка повреждена»", async ({ page }) => {
    const p = PAGES.cloud;
    test.skip(p.access !== "key", "облако с одним замком");
    await page.goto("/p/cloud/");
    await expect(page.getByText(BROKEN)).toBeVisible({ timeout: 15000 });
    await expect(page.locator("#shell-login")).toBeHidden();
    const html = await page.content();
    if (p.passwordHint) expect(html).not.toContain(p.passwordHint);
    expect(await page.locator('input[name="login"]').inputValue()).toBe("");
  });

  test("«Забыли пароль?» показывает подсказку владельца; пароль принимается с пробелом и дефисом", async ({ page }) => {
    const p = PAGES.cloud;
    test.skip(!p.passwordHint, "в page.yaml нет password_hint");
    await page.goto(p.url);
    const hint = page.locator("#shell-hint");
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(hint).toBeHidden();
    const forgot = page.getByRole("button", { name: "Забыли пароль?" });
    await expect(forgot).toHaveAttribute("aria-expanded", "false");
    await forgot.click();
    await expect(hint).toBeVisible();
    await expect(hint).toHaveText(`Подсказка владельца: ${p.passwordHint}`);
    await expect(forgot).toHaveAttribute("aria-expanded", "true");
    // в подсказке нет самого пароля
    expect(p.passwordHint!.toLowerCase()).not.toContain(p.password!.toLowerCase());
    // 360 px: форма с подсказкой без горизонтальной прокрутки
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    // нормализация пароля: регистр, пробел и дефис перед цифрами не важны («Хлестаков 4», «хлестаков-4»)
    const spaced = p.password!.replace(/(\d+)$/, " $1").toLowerCase();
    const dashed = p.password!.replace(/(\d+)$/, "-$1").toLowerCase();
    expect(spaced).not.toBe(p.password);
    await page.locator('input[name="password"]').fill(dashed);
    await page.getByRole("button", { name: "Войти" }).click();
    await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 15000 });
    await page.evaluate(() => sessionStorage.clear());
    await page.goto("about:blank"); // заново, как по QR (ключ в адресе)
    await page.goto(p.url);
    await page.locator('input[name="password"]').fill(spaced);
    await page.getByRole("button", { name: "Войти" }).click();
    await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 15000 });
  });
});

test.describe("ноутбук 1280 px", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  for (const slug of Object.keys(PAGES)) {
    test(`${slug}: открывается без горизонтальной прокрутки`, async ({ page }) => {
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(String(e)));
      await openPage(page, slug);
      await expect(page.locator("main")).toBeVisible();
      await expectNoHorizontalScroll(page);
      expect(errors).toEqual([]);
    });
  }
});


// ---------------------------------------------------------------- рабочие элементы (REDESIGN-2026-10 §4.1)

/** На странице нет кнопок аккаунта и окон-заглушек; число лайков и комментариев — обычный текст. */
async function expectNoDeadEnds(page: Page) {
  for (const name of ["Подписаться", "Написать", "Нравится", "Поделиться", "Войти", "Отметить", "Печать", "Ввести пароль"]) {
    await expect(page.getByRole("button", { name, exact: false }), name).toHaveCount(0);
  }
  await expect(page.locator("dialog.svc-dialog, [data-dialog-text]")).toHaveCount(0);
  await expect(page.getByText(/войдите в|не обновляется|Материал недоступен/)).toHaveCount(0);
}

/** Подвал: раскрывающиеся сведения о сервисе (без окон), текст из content/pages/_brands.yaml. */
async function expectServiceDetails(page: Page, textPart: RegExp | string) {
  const det = page.locator("details.svc-about");
  await expect(det).toHaveCount(1);
  await det.scrollIntoViewIfNeeded();
  await expect(det.locator(".svc-about__body")).toBeHidden();
  await det.locator("summary").click();
  await expect(det.locator(".svc-about__body")).toBeVisible();
  await expect(det).toContainText(textPart);
  await expect(page.locator("dialog[open]")).toHaveCount(0);
}

test.describe("рабочие элементы: «Круг»", () => {
  test.use({ viewport: PHONE, hasTouch: true });

  test("gromov: нет кнопок аккаунта и окон; счётчики — текст; комментарии сворачиваются", async ({ page }) => {
    await openPage(page, "gromov");
    await expectNoDeadEnds(page);
    const post = page.locator(".kr-post").first();
    await expect(post.locator(".kr-stat").first()).toContainText(/\d/);
    await expect(post.locator(".kr-stat").first().locator("xpath=self::button")).toHaveCount(0);
    await expect(page.locator(".kr-compose")).toHaveCount(0);
    const toggle = post.locator("button[data-toggle]");
    if (await toggle.count()) {
      await toggle.click();
      await expect(post.locator(".kr-comments-box")).toBeHidden();
      await toggle.click();
      await expect(post.locator(".kr-comments-box")).toBeVisible();
    }
    await expectNoHorizontalScroll(page);
  });

  test("gromov: вкладки работают с клавиатуры, фото открывается крупно, подвал", async ({ page }) => {
    await openPage(page, "gromov");
    const tabs = page.getByRole("tab");
    await expect(tabs).toHaveCount(3);
    await expect(page.getByRole("tabpanel", { name: "Публикации" })).toBeVisible();
    await tabs.first().focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: "Фото" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("tabpanel", { name: "Фото" })).toBeVisible();
    await expect(page.locator("#kr-panel-posts")).toBeHidden();
    await page.getByRole("tab", { name: "Сведения" }).click();
    await expect(page.locator("#kr-panel-about")).toContainText("Громова");
    await page.getByRole("tab", { name: "Фото" }).click();
    const tile = page.locator(".kr-zoom--tile").first();
    await tile.click();
    const zoom = page.locator("dialog.svc-zoom[open]");
    await expect(zoom).toBeVisible();
    await zoom.getByRole("button", { name: "Закрыть" }).click();
    await expect(zoom).toBeHidden();
    // Подвал: сведения о сервисе раскрываются на месте.
    await expectServiceDetails(page, "Круг");
  });

  test("ссылки: автор без страницы → заглушка, логотип → главная, поиск людей", async ({ page }) => {
    await openPage(page, "gromov");
    await page.locator(".kr-comment__author", { hasText: "Тамара Ведерникова" }).click();
    await expect(page).toHaveURL(/\/p\/krug-private\/$/);
    await expect(page.getByRole("heading", { name: /ограничил доступ/ })).toBeVisible();
    await page.getByRole("link", { name: /Круг: главная/ }).click();
    await expect(page).toHaveURL(/\/p\/krug\/$/);
    const q = page.locator("#kr-q");
    const status = page.locator('[data-role="status"]');
    // Страница сама не показывает, кто в сети: пока запроса нет, виден только совет.
    await expect(page.locator(".kr-person:visible")).toHaveCount(0);
    await expect(status).toHaveText("Введите имя или фамилию");
    await q.fill("гр");
    await expect(page.locator(".kr-person:visible")).toHaveCount(0); // меньше трёх букв
    await q.fill("громова");
    await expect(page.locator(".kr-person:visible")).toHaveCount(1);
    await q.fill("ГРОМ");
    expect(await page.locator(".kr-person:visible").count()).toBeLessThanOrEqual(5);
    await q.fill("мова"); // середина слова не ищется
    await expect(page.locator(".kr-person:visible")).toHaveCount(0);
    await q.fill("нет такого человека");
    await expect(page.locator(".kr-person:visible")).toHaveCount(0);
    await expect(status).toHaveText("Никого не нашли");
    await q.fill("");
    await expect(page.locator(".kr-person:visible")).toHaveCount(0);
    await expect(status).toHaveText("Введите имя или фамилию");
    await q.fill("громова");
    await page.locator(".kr-person:visible .kr-person__link").click();
    await expect(page).toHaveURL(/\/p\/gromov\/$/);
    await expectNoHorizontalScroll(page);
  });

  test("news: рубрики, баннеры и пункты без страницы — не кнопки и не ссылки; подвал раскрывается", async ({ page }) => {
    await openPage(page, "news");
    await expectNoDeadEnds(page);
    // Ссылки: логотип, «Главное», пункты боковой колонки со страницей.
    await expect(page.locator(".nw-nav a")).toHaveCount(1);
    await expect(page.locator(".nw-nav__item", { hasText: "Спорт" })).not.toHaveJSProperty("tagName", "A");
    await expect(page.locator(".nw-banner a, .nw-banner button")).toHaveCount(0);
    await expect(page.locator(".nw-comment__author a, button.nw-comment__author")).toHaveCount(0);
    await expect(page.locator("button")).toHaveCount(0);
    await expectServiceDetails(page, /портал/i);
    await expectNoHorizontalScroll(page);
  });

  test("pharma и cloud: без кнопок-заглушек; замок папки — без кнопки", async ({ page }) => {
    await openPage(page, "pharma");
    await expectNoDeadEnds(page);
    await expectServiceDetails(page, /справочник/i);
    await openPage(page, "cloud");
    await expectNoDeadEnds(page);
    await expect(page.locator("button.tc-bar__account, a.tc-bar__account")).toHaveCount(0);
    await page.locator(".tc-folder--locked").first().click();
    await expect(page.getByText("Папка защищена отдельным паролем")).toBeVisible();
    await expect(page.locator(".tc-locked button, .tc-locked input")).toHaveCount(0);
    await expectServiceDetails(page, /хранилищ/i);
  });

  test("site: у клуба нет «Войти», есть плашка «по приглашению»", async ({ page }) => {
    await openPage(page, "auction");
    await expectNoDeadEnds(page);
    await expect(page.locator(".st-notice").first()).toContainText(/приглашени/i);
    await expectNoHorizontalScroll(page);
  });
});
