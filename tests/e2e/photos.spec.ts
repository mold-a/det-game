// Фото в контенте: блоки photo и карточки на сайте организации, галерея «О центре» в лаборатории, папка облака
// kind: photos, подпись к фото статьи (docs/03 §6б, §8; docs/04). Крупный просмотр — нативный <dialog>.
// Фикстуры собирает tests/e2e/photos_fixture.py во временную папку (в content/ тестовых фото нет); нужен ffmpeg.
// Скриншоты 360 px кладутся в PHOTOS_SHOTS (папка), если переменная задана.

import { test, expect, type Page, type Locator } from "@playwright/test";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const PYTHON = process.env.PYTHON || (process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python");
const PORT = 8000 + 800 + Math.floor(Math.random() * 400);
const BASE = `http://127.0.0.1:${PORT}`;
const PHONE = { width: 360, height: 780 };
const SHOTS = process.env.PHOTOS_SHOTS;

let server: ChildProcess;
let info: { site: string; lab: string; cloud: string; cloud_password: string; news: string; folder: string };

test.beforeAll(async () => {
  test.setTimeout(180_000);
  const out = mkdtempSync(join(tmpdir(), "photos-e2e-"));
  const built = spawnSync(PYTHON, ["tests/e2e/photos_fixture.py", out], { encoding: "utf8" });
  expect(built.status, built.stderr).toBe(0);
  info = JSON.parse(readFileSync(join(out, "info.json"), "utf8"));
  server = spawn(PYTHON, ["tests/e2e/photos_fixture.py", out, "--serve", String(PORT)], { stdio: "ignore" });
  for (let i = 0; i < 50; i++) {
    try {
      if ((await fetch(BASE + "/")).ok) break;
    } catch {
      /* ждём запуска */
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  if (SHOTS) mkdirSync(SHOTS, { recursive: true });
});

test.afterAll(() => {
  server?.kill();
});

test.use({ viewport: PHONE, hasTouch: true });

async function noHScroll(page: Page) {
  const [sw, iw] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  expect(sw).toBeLessThanOrEqual(iw);
}

async function shot(page: Page, name: string, fullPage = !name.includes("zoom")) {
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `photos-${name}.png`), fullPage });
}

/** Картинка загрузилась и имеет размер (не сломана). */
async function expectLoaded(img: Locator) {
  await img.scrollIntoViewIfNeeded();
  await expect.poll(() => img.evaluate((el) => (el as HTMLImageElement).complete && (el as HTMLImageElement).naturalWidth), { timeout: 15000 }).toBeGreaterThan(0);
}

/** Окно «фото крупно»: открыто, снимок виден целиком в окне экрана, подпись — как ожидается. */
async function expectZoom(page: Page, caption: string | null) {
  const dlg = page.locator("dialog.svc-zoom[open]");
  await expect(dlg).toBeVisible();
  const big = dlg.locator("img.svc-zoom__img");
  await expectLoaded(big);
  const vp = page.viewportSize()!;
  const box = (await big.boundingBox())!;
  expect(box.width).toBeLessThanOrEqual(vp.width);
  expect(box.height).toBeLessThanOrEqual(vp.height);
  expect(box.width).toBeGreaterThan(vp.width * 0.5); // действительно «крупно», а не миниатюра
  if (caption) await expect(dlg.locator(".svc-zoom__caption")).toHaveText(caption);
  else await expect(dlg.locator(".svc-zoom__caption")).toBeHidden();
  const close = dlg.getByRole("button", { name: "Закрыть" });
  const cb = (await close.boundingBox())!;
  expect(cb.width).toBeGreaterThanOrEqual(44);
  expect(cb.height).toBeGreaterThanOrEqual(44);
  return dlg;
}

async function closeAndCheckFocus(page: Page, opener: Locator, how: "button" | "esc") {
  const dlg = page.locator("dialog.svc-zoom");
  if (how === "button") await dlg.getByRole("button", { name: "Закрыть" }).click();
  else await page.keyboard.press("Escape");
  await expect(page.locator("dialog.svc-zoom[open]")).toHaveCount(0);
  await expect(opener).toBeFocused();
}

test.describe("сайт организации (site)", () => {
  test("широкое и обычное фото, карточки: показываются и открываются крупно", async ({ page }) => {
    await page.goto(BASE + info.site + "#about");
    const figs = page.locator("figure.st-photo");
    await expect(figs).toHaveCount(3);

    // широкое — на всю ширину экрана, как обложка
    const wide = figs.nth(0);
    await expect(wide).toHaveClass(/st-photo--wide/);
    await expectLoaded(wide.locator("img"));
    const wb = (await wide.locator(".st-photo__btn").boundingBox())!;
    expect(Math.round(wb.x)).toBe(0);
    expect(Math.round(wb.width)).toBe(PHONE.width);
    await expect(wide.locator("figcaption")).toHaveText("Тестовый фасад");

    // обычное — в колонке текста (с полями)
    const inside = figs.nth(1);
    await expect(inside).not.toHaveClass(/st-photo--wide/);
    await expectLoaded(inside.locator("img"));
    const ib = (await inside.locator(".st-photo__btn").boundingBox())!;
    expect(ib.x).toBeGreaterThanOrEqual(8);
    expect(ib.width).toBeLessThan(PHONE.width);

    // все картинки ленивые и не сломаны
    for (const img of await page.locator(".st-photo img, .st-card img").all()) {
      await expect(img).toHaveAttribute("loading", "lazy");
      await expectLoaded(img);
    }

    // нет файла: заглушка без кнопки, подпись на месте
    const absent = figs.nth(2);
    await expect(absent.locator("img")).toHaveCount(0);
    await expect(absent.locator("button")).toHaveCount(0);
    await expect(absent.locator(".ph")).toContainText("Здесь будет фото");
    await expect(absent.locator("figcaption")).toHaveText("Тестовый снимок без файла");
    await noHScroll(page);
    await shot(page, "site-360");

    // крупно: кнопка → окно → «Закрыть», Esc; фокус возвращается
    const btn = wide.locator(".st-photo__btn");
    await btn.click();
    await expectZoom(page, "Тестовый фасад");
    await shot(page, "site-zoom-360");
    await closeAndCheckFocus(page, btn, "button");
    const btn2 = inside.locator(".st-photo__btn");
    await btn2.click();
    await expectZoom(page, "Тестовый зал");
    await closeAndCheckFocus(page, btn2, "esc");

    // карточка с фото тоже открывается крупно; карточка без файла — заглушка без кнопки
    const cards = page.locator("li.st-card.has-photo");
    await expect(cards).toHaveCount(2);
    const cardBtn = cards.nth(0).locator("button.st-zoom");
    await cardBtn.scrollIntoViewIfNeeded();
    await cardBtn.click();
    await expectZoom(page, "Тестовая карточка с фото");
    await closeAndCheckFocus(page, cardBtn, "esc");
    await expect(cards.nth(1).locator("button")).toHaveCount(0);
    await expect(cards.nth(1).locator(".ph")).toBeVisible();
  });

  test("тёмная тема и ноутбук: без горизонтальной прокрутки, широкое фото ограничено колонкой", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto(BASE + info.site + "#about");
    await expectLoaded(page.locator(".st-photo img").first());
    await noHScroll(page);
    await shot(page, "site-dark-360");
    await page.setViewportSize({ width: 1280, height: 800 });
    await noHScroll(page);
    const wb = (await page.locator(".st-photo--wide").boundingBox())!;
    expect(wb.width).toBeLessThanOrEqual(1040);
    await shot(page, "site-1280");
    await page.setViewportSize({ width: 768, height: 900 });
    await noHScroll(page);
  });
});

test.describe("лаборатория (/lab/#about)", () => {
  test("галерея «О центре»: три фото, крупно по нажатию, подписи", async ({ page }) => {
    await page.goto(BASE + info.lab + "#about");
    const gallery = page.locator(".pz-gallery");
    await expect(gallery).toBeVisible();
    await expect(gallery.getByRole("heading", { name: "Фотографии центра" })).toBeVisible();
    const items = gallery.locator("li.pz-photo");
    await expect(items).toHaveCount(3);
    await expect(items.nth(0).locator(".pz-photo__cap")).toHaveText("Тестовый вход со двора");
    await expect(items.nth(2).locator(".pz-photo__cap")).toHaveCount(0); // без подписи
    for (const img of await gallery.locator("img").all()) {
      await expect(img).toHaveAttribute("loading", "lazy");
      await expectLoaded(img);
    }
    // цели нажатия ≥ 44 px
    for (const b of await gallery.locator("button").all()) {
      const bb = (await b.boundingBox())!;
      expect(bb.width).toBeGreaterThanOrEqual(44);
      expect(bb.height).toBeGreaterThanOrEqual(44);
    }
    await noHScroll(page);
    await gallery.scrollIntoViewIfNeeded();
    await shot(page, "lab-360");

    const first = items.nth(0).locator("button");
    await expect(first).toHaveAttribute("aria-label", "Открыть фото крупно: Тестовый вход со двора");
    await first.click();
    await expectZoom(page, "Тестовый вход со двора");
    await shot(page, "lab-zoom-360");
    await closeAndCheckFocus(page, first, "esc");

    const third = items.nth(2).locator("button");
    await third.click();
    await expectZoom(page, null);
    await closeAndCheckFocus(page, third, "button");
  });

  test("тёмная тема и ноутбук", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto(BASE + info.lab + "#about");
    await expectLoaded(page.locator(".pz-photo img").first());
    await noHScroll(page);
    await page.locator(".pz-gallery").scrollIntoViewIfNeeded();
    await shot(page, "lab-dark-360");
    await page.setViewportSize({ width: 1280, height: 800 });
    await noHScroll(page);
    await expect(page.locator(".pz-photo")).toHaveCount(3);
    const boxes = await page.locator(".pz-photo").evaluateAll((els) => els.map((e) => e.getBoundingClientRect().top));
    expect(Math.max(...boxes) - Math.min(...boxes)).toBeLessThan(2); // на ноутбуке — один ряд
    await page.locator(".pz-gallery").scrollIntoViewIfNeeded();
    await shot(page, "lab-1280");
    await page.setViewportSize({ width: 768, height: 900 });
    await noHScroll(page);
  });

  test("галерея принадлежит разделу «О центре»: в других разделах не видна", async ({ page }) => {
    await page.goto(BASE + info.lab + "#services");
    await expect(page.locator(".pz-gallery")).toBeHidden();
    await page.goto(BASE + info.lab + "#contacts");
    await expect(page.locator(".pz-gallery")).toBeHidden();
  });
});

test.describe("облако: папка-галерея", () => {
  async function login(page: Page) {
    await page.goto(BASE + info.cloud);
    await page.locator('input[name="password"]').fill(info.cloud_password);
    await page.getByRole("button", { name: "Войти" }).click();
    await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 20000 });
    await page.locator(`[data-folder-link="${info.folder}"]`).click();
  }

  test("сетка миниатюр, расшифровка, крупно с подписью и датой", async ({ page }) => {
    await login(page);
    const panel = page.locator(`.tc-panel[data-folder="${info.folder}"]`);
    await expect(panel).toBeVisible();
    const items = panel.locator("li.tc-photo");
    await expect(items).toHaveCount(4);
    // три файла есть и расшифровываются в blob:, четвёртого нет — заглушка без кнопки
    for (const img of await panel.locator("img").all()) {
      await expect(img).toHaveAttribute("loading", "lazy");
      await expectLoaded(img);
      expect(await img.getAttribute("src")).toMatch(/^blob:/);
    }
    await expect(items.nth(3).locator("img, button")).toHaveCount(0);
    await expect(items.nth(3).locator(".ph")).toContainText("Здесь будет фото");
    await expect(items.nth(0).locator(".tc-photo__cap")).toContainText("Тестовая репетиция");
    await expect(items.nth(0).locator("time")).toHaveText("12.10.2026");
    for (const b of await panel.locator("button").all()) {
      const bb = (await b.boundingBox())!;
      expect(bb.width).toBeGreaterThanOrEqual(44);
      expect(bb.height).toBeGreaterThanOrEqual(44);
    }
    await noHScroll(page);
    await panel.scrollIntoViewIfNeeded();
    await shot(page, "cloud-360");

    const a = items.nth(0).locator("button");
    await a.click();
    const dlg = await expectZoom(page, "Тестовая репетиция · 12.10.2026");
    expect(await dlg.locator("img.svc-zoom__img").getAttribute("src")).toMatch(/^blob:/);
    await shot(page, "cloud-zoom-360");
    await closeAndCheckFocus(page, a, "esc");

    const b = items.nth(1).locator("button");
    await b.click();
    await expectZoom(page, "Только подпись");
    await closeAndCheckFocus(page, b, "button");
    const c = items.nth(2).locator("button");
    await c.click();
    await expectZoom(page, null);
    await closeAndCheckFocus(page, c, "esc");
  });

  test("тёмная тема, 768 и ноутбук", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await login(page);
    await expectLoaded(page.locator(".tc-photo img").first());
    await noHScroll(page);
    await shot(page, "cloud-dark-360");
    for (const w of [768, 1280]) {
      await page.setViewportSize({ width: w, height: 900 });
      await noHScroll(page);
    }
    await shot(page, "cloud-1280");
  });

  test("закрытые фото не лежат открытыми в dist", async ({ request }) => {
    const html = await (await request.get(BASE + info.cloud)).text();
    expect(html).not.toContain("Тестовая репетиция");
    const payload = await (await request.get(BASE + info.cloud + "payload.json")).text();
    expect(payload).not.toContain("tc-photos");
  });
});

test.describe("новости: подпись к фото", () => {
  test("figcaption под фото статьи", async ({ page }) => {
    await page.goto(BASE + info.news);
    const fig = page.locator("figure.nw-article__photo");
    await expectLoaded(fig.locator("img"));
    await expect(fig.locator("figcaption")).toHaveText("Тестовая подпись к фото статьи");
    await expect(fig.locator("img")).toHaveAttribute("loading", "lazy");
    await noHScroll(page);
    await shot(page, "news-360");
  });
});
