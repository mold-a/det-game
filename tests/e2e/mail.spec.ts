// Почтовый ящик type: mail (docs/04 «mail»): закрытая страница по ключу, папки, список цепочек, открытая цепочка,
// вложения (картинка расшифровывается и открывается крупно), «К списку писем» и системная кнопка «Назад».
// Телефон 360 px — список и цепочка по очереди, без горизонтальной прокрутки; ноутбук — три колонки.
// Фикстуру собирает tests/e2e/mail_fixture.py во временную папку (в content/ ящика нет); нужен ffmpeg.
// Скриншоты кладутся в MAIL_SHOTS (папка), если переменная задана.

import { test, expect, type Page } from "@playwright/test";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const PYTHON = process.env.PYTHON || (process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python");
const PORT = 8000 + 1300 + Math.floor(Math.random() * 400);
const BASE = `http://127.0.0.1:${PORT}`;
const PHONE = { width: 360, height: 780 };
const SHOTS = process.env.MAIL_SHOTS;

let server: ChildProcess;
let info: { mail: string };

test.beforeAll(async () => {
  test.setTimeout(240_000);
  const out = mkdtempSync(join(tmpdir(), "mail-e2e-"));
  const built = spawnSync(PYTHON, ["tests/e2e/mail_fixture.py", out], { encoding: "utf8" });
  expect(built.status, built.stderr).toBe(0);
  info = JSON.parse(readFileSync(join(out, "info.json"), "utf8"));
  server = spawn(PYTHON, ["tests/e2e/mail_fixture.py", out, "--serve", String(PORT)], { stdio: "ignore" });
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

async function noHScroll(page: Page) {
  const [sw, iw] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  expect(sw).toBeLessThanOrEqual(iw);
}

async function shot(page: Page, name: string) {
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `${name}.png`), fullPage: true });
}

async function openMail(page: Page) {
  await page.goto(BASE + info.mail);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 20000 });
  await expect(page).toHaveURL(new RegExp(`/p/mail-sample/$`)); // ключ убран из адреса
}

test.describe("телефон 360 px", () => {
  test.use({ viewport: PHONE, hasTouch: true });

  test("список → цепочка → назад к списку", async ({ page }) => {
    await openMail(page);
    const rows = page.locator(".ml-row:visible");
    await expect(page.locator(".ml-notice")).toContainText("Выгрузка ящика по запросу № 00-000");
    await expect(page.locator('.ml-folder[aria-current="true"]')).toContainText("Входящие");
    await expect(rows).toHaveCount(2);
    await expect(rows.nth(0)).toContainText("Знакомая Тестовая");
    await expect(page.locator(".ml-thread:visible")).toHaveCount(0);
    await expect(page.locator(".ml-read")).toBeHidden();
    await noHScroll(page);
    await shot(page, "mail-360-list");

    await page.locator('[data-thread-link="work"]').click();
    const work = page.locator("#mt-work");
    await expect(work).toBeVisible();
    await expect(page.locator(".ml-list")).toBeHidden();
    await expect(page.locator(".ml-folders")).toBeHidden();
    await expect(page).toHaveURL(/#mt-work$/);
    await expect(work.locator(".ml-msg")).toHaveCount(2);
    await expect(work).toBeFocused();
    const back = work.getByRole("button", { name: "К списку писем" });
    await expect(back).toBeVisible();
    const bb = (await back.boundingBox())!;
    expect(bb.height).toBeGreaterThanOrEqual(44);
    // вложение-картинка: зашифрованный файл → blob:, крупно в окне сервиса
    const thumb = work.locator("button.ml-file--img img");
    await thumb.scrollIntoViewIfNeeded();
    await expect.poll(() => thumb.getAttribute("src"), { timeout: 15000 }).toMatch(/^blob:/);
    await expect.poll(() => thumb.evaluate((el) => (el as HTMLImageElement).naturalWidth), { timeout: 15000 }).toBeGreaterThan(0);
    await noHScroll(page);
    await page.evaluate(() => window.scrollTo(0, 0));
    await shot(page, "mail-360-thread");
    await work.locator("button.ml-file--img").click();
    const dlg = page.locator("dialog.svc-zoom[open]");
    await expect(dlg).toBeVisible();
    await expect(dlg.locator(".svc-zoom__caption")).toHaveText("график-тест.jpg");
    await page.keyboard.press("Escape");
    await expect(dlg).toHaveCount(0);

    await back.click();
    await expect(page.locator(".ml-list")).toBeVisible();
    await expect(work).toBeHidden();
    await expect(page).toHaveURL(/\/p\/mail-sample\/$/);
    await expect(page.locator('[data-thread-link="work"]')).toBeFocused();
  });

  test("системная «Назад» возвращает к списку; цепочка другой папки, непрочитанное, ссылка во вложении", async ({ page }) => {
    await openMail(page);
    await page.locator('[data-folder-link="2"]').click(); // «Проекты»
    await expect(page.locator(".ml-row:visible")).toHaveCount(1);
    const odd = page.locator('[data-thread-link="odd"]');
    await expect(odd).toHaveClass(/is-unread/);
    await expect(odd.locator(".ml-row__who")).toHaveCSS("font-weight", "700");
    await odd.click();
    const thread = page.locator("#mt-odd");
    await expect(thread).toBeVisible();
    await expect(thread.locator(".ml-msg.is-unread")).toHaveCount(1);
    await expect(thread.locator(".ml-msg__unread")).toHaveText("Не прочитано");
    await expect(thread.locator("a.ml-file--page")).toHaveAttribute("href", "/p/news/");
    await noHScroll(page);
    await page.goBack();
    await expect(page.locator(".ml-list")).toBeVisible();
    await expect(thread).toBeHidden();
    await expect(page.locator('.ml-folder[aria-current="true"]')).toContainText("Проекты");
    // пустая папка
    await page.locator('[data-folder-link="3"]').click();
    await expect(page.locator(".ml-box:visible")).toContainText("В папке нет писем");
    await noHScroll(page);
  });

  test("тёмная тема без горизонтальной прокрутки", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await openMail(page);
    await noHScroll(page);
    await page.locator('[data-thread-link="personal"]').click();
    await expect(page.locator("#mt-personal .ml-file--missing .ph")).toContainText("Здесь будет вложение");
    await noHScroll(page);
    await shot(page, "mail-360-dark-thread");
  });
});

test.describe("ноутбук 1280 px", () => {
  test.use({ viewport: { width: 1280, height: 860 } });

  test("три колонки: папки, список, цепочка рядом; кнопки «назад» нет", async ({ page }) => {
    await openMail(page);
    await expect(page.locator(".ml-folders")).toBeVisible();
    await expect(page.locator(".ml-list")).toBeVisible();
    await expect(page.locator(".ml-read__empty")).toBeVisible();
    await page.locator('[data-thread-link="work"]').click();
    const work = page.locator("#mt-work");
    await expect(work).toBeVisible();
    await expect(page.locator(".ml-list")).toBeVisible(); // список остаётся
    await expect(page.locator(".ml-read__empty")).toBeHidden();
    await expect(work.locator(".ml-back")).toBeHidden();
    const [f, l, r] = await Promise.all([".ml-folders", ".ml-list", ".ml-read"].map((s) => page.locator(s).boundingBox()));
    expect(f!.x + f!.width).toBeLessThanOrEqual(l!.x);
    expect(l!.x + l!.width).toBeLessThanOrEqual(r!.x);
    expect(Math.abs(f!.y - r!.y)).toBeLessThan(2);
    await noHScroll(page);
    await expect.poll(() => work.locator("button.ml-file--img img").getAttribute("src"), { timeout: 15000 }).toMatch(/^blob:/);
    await shot(page, "mail-1280");
    // из цепочки в цепочку — без лишних записей истории: «Назад» сразу к пустой цепочке
    await page.locator('[data-thread-link="personal"]').click();
    await expect(page.locator("#mt-personal")).toBeVisible();
    await expect(work).toBeHidden();
    await page.goBack();
    await expect(page.locator(".ml-read__empty")).toBeVisible();
    await page.setViewportSize({ width: 768, height: 900 });
    await noHScroll(page);
  });
});
