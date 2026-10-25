// Закрытые медиа после новой выкладки (регресс 25.10, mydetgame.ru): фото «Кадра» (inna), видео 4-07 (video),
// фото облака (cloud) расшифровываются и у того, кто уже открывал прошлую сборку. /m/* хостинг отдаёт как
// immutable, а ключ закрытого файла новый в каждой сборке: старая копия из кеша браузера не расшифровывалась.
// Фикстура — tests/e2e/sealed_fixture.py: боевой контент, сервер с заголовками из dist/_headers; нужен ffmpeg.

import { test, expect, type Page, type BrowserContext } from "@playwright/test";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const PYTHON = process.env.PYTHON || (process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python");
const PORT = 8000 + 1200 + Math.floor(Math.random() * 400);
const BASE = `http://127.0.0.1:${PORT}`;

type Info = {
  inna: string; video: string; video_sha256: string;
  cloud: string; cloud_password: string; cloud_folder: string; cloud_photos: number;
};
let out: string;
let info: Info;
let server: ChildProcess;

function buildFixture() {
  const built = spawnSync(PYTHON, ["tests/e2e/sealed_fixture.py", out], { encoding: "utf8" });
  expect(built.status, built.stderr).toBe(0);
  info = JSON.parse(readFileSync(join(out, "info.json"), "utf8"));
}

test.describe.configure({ mode: "serial" });

test.beforeAll(async () => {
  test.setTimeout(300_000);
  out = mkdtempSync(join(tmpdir(), "sealed-e2e-"));
  buildFixture();
  server = spawn(PYTHON, ["tests/e2e/sealed_fixture.py", out, "--serve", String(PORT)], { stdio: "ignore" });
  for (let i = 0; i < 50; i++) {
    try {
      if ((await fetch(BASE + "/")).ok) break;
    } catch {
      /* ждём запуска */
    }
    await new Promise((r) => setTimeout(r, 200));
  }
});

test.afterAll(() => {
  server?.kill();
});

/** Все <img data-media> (кроме заведомо отсутствующих) расшифрованы в blob: и отрисованы. */
async function expectImagesDecrypted(page: Page, scope: string, count?: number) {
  const imgs = page.locator(`${scope} img[data-media]`);
  if (count !== undefined) await expect(imgs).toHaveCount(count);
  const n = await imgs.count();
  expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    const img = imgs.nth(i);
    await img.scrollIntoViewIfNeeded(); // lazy-фото расшифровываются у края экрана
    await expect(img).not.toHaveClass(/media-missing/);
    await expect.poll(() => img.evaluate((el: HTMLImageElement) => el.src.startsWith("blob:") && el.complete && el.naturalWidth > 0),
      { timeout: 15_000 }).toBe(true);
  }
}

async function checkInna(page: Page) {
  await page.goto(BASE + info.inna);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 20_000 });
  await expectImagesDecrypted(page, "body");
  // крупный просмотр — тот же расшифрованный снимок
  await page.locator(".kd-tile__btn").first().click();
  await expect.poll(() => page.locator(".kd-view__img").evaluate((el: HTMLImageElement) => el.src.startsWith("blob:") && el.naturalWidth > 0))
    .toBe(true);
  await page.keyboard.press("Escape");
}

async function checkVideo(page: Page) {
  await page.goto(BASE + info.video);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 20_000 });
  const player = page.locator('[data-player="video"]');
  await player.locator('[data-act="load"]').click();
  await expect(player).toHaveClass(/is-ready/, { timeout: 20_000 });
  await expect(player.locator(".ev-player__error")).toHaveCount(0);
  const video = player.locator("video");
  // расшифровано побайтно то, что лежит в media/
  const sha = await video.evaluate(async (v: HTMLVideoElement) => {
    const buf = await (await fetch(v.src)).arrayBuffer();
    return [...new Uint8Array(await crypto.subtle.digest("SHA-256", buf))].map((b) => b.toString(16).padStart(2, "0")).join("");
  });
  expect(sha).toBe(info.video_sha256);
  await video.evaluate((v: HTMLVideoElement) => {
    v.muted = true;
    return v.play();
  });
  await expect.poll(() => video.evaluate((v: HTMLVideoElement) => v.currentTime > 0 && !v.error)).toBe(true);
}

async function checkCloud(page: Page) {
  await page.goto(BASE + info.cloud);
  await page.locator('input[name="password"]').fill(info.cloud_password);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 20_000 });
  await page.locator(`[data-folder-link="${info.cloud_folder}"]`).click();
  const panel = `.tc-panel[data-folder="${info.cloud_folder}"]`;
  await expect(page.locator(panel)).toBeVisible();
  await expectImagesDecrypted(page, panel, info.cloud_photos);
  await page.locator(`${panel} li.tc-photo button`).first().click();
  await expect.poll(() => page.locator("img.svc-zoom__img").evaluate((el: HTMLImageElement) => el.src.startsWith("blob:") && el.naturalWidth > 0))
    .toBe(true);
}

async function checkAll(ctx: BrowserContext) {
  const page = await ctx.newPage();
  const sealed: string[] = [];
  page.on("response", async (r) => {
    if (!/\/m\/[0-9a-f]{32}\.bin/.test(r.url())) return;
    sealed.push(r.url());
    // кеширование как на хостинге (dist/_headers): без этого тест не ловит регресс
    expect(await r.headerValue("cache-control")).toContain("immutable");
  });
  await checkInna(page);
  await checkVideo(page);
  await checkCloud(page);
  await page.close();
  return sealed;
}

test("закрытые фото и видео открываются и после новой выкладки (кеш /m/ — immutable)", async ({ browser }) => {
  test.setTimeout(300_000);
  const ctx = await browser.newContext(); // один профиль на обе сборки: кеш браузера переживает выкладку
  const first = await checkAll(ctx);
  expect(first.length).toBeGreaterThan(0);
  expect(first.every((u) => /\.bin\?v=[0-9a-f]{16}$/.test(u)), first.join("\n")).toBe(true);

  buildFixture(); // новая выкладка: те же имена /m/<hash>.bin, новые ключи и байты
  const second = await checkAll(ctx);
  // адреса закрытых файлов сменились — старая копия из кеша не используется
  const paths = (us: string[]) => new Set(us.map((u) => new URL(u).pathname));
  expect([...paths(second)].some((p) => paths(first).has(p))).toBe(true);
  expect(second.some((u) => first.includes(u))).toBe(false);
  await ctx.close();
});
