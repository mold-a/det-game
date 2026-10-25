// Голосовые сообщения в постах «Круга» (docs/04 «social», docs/03 §8).
// Страницы-фикстуры (krug-actor открыт, krug-closed закрыт) собирает tests/e2e/voice_fixture.py во временную
// папку и раздаёт своим сервером: в content/ этих страниц нет. Нужен ffmpeg (делает настоящие mp3).

import { test, expect, type Page } from "@playwright/test";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const PYTHON = process.env.PYTHON || (process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python");
const PORT = 8000 + 400 + Math.floor(Math.random() * 400);
const BASE = `http://127.0.0.1:${PORT}`;
const PHONE = { width: 360, height: 780 };

let server: ChildProcess;
let info: { open: string; closed: string };

test.beforeAll(async () => {
  test.setTimeout(120_000);
  const out = mkdtempSync(join(tmpdir(), "voice-e2e-"));
  const built = spawnSync(PYTHON, ["tests/e2e/voice_fixture.py", out], { encoding: "utf8" });
  expect(built.status, built.stderr).toBe(0);
  info = JSON.parse(readFileSync(join(out, "info.json"), "utf8"));
  server = spawn(PYTHON, ["tests/e2e/voice_fixture.py", out, "--serve", String(PORT)], { stdio: "ignore" });
  for (let i = 0; i < 50; i++) {
    try {
      if ((await fetch(BASE + "/")).ok) return;
    } catch {
      /* ждём запуска */
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error("сервер фикстур не запустился");
});

test.afterAll(() => {
  server?.kill();
});

test.use({ viewport: PHONE, hasTouch: true });

async function noHScroll(page: Page) {
  const [sw, iw] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  expect(sw).toBeLessThanOrEqual(iw);
}

test("открытая страница: свой плеер, расшифровка, воспроизведение", async ({ page }) => {
  await page.goto(BASE + info.open);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1");
  await expect(page.locator("audio[controls]")).toHaveCount(0);
  const voices = page.locator(".kr-post > .kr-voice");
  await expect(voices).toHaveCount(2);

  // Пост только с голосовым (без text): плеер есть, текста поста нет.
  const only = page.locator('.kr-post[data-datetime="2026-10-02T09:15"]');
  await expect(only.locator(".kr-post__text")).toHaveCount(0);
  const player = only.locator(".kr-voice");
  const btn = player.locator('[data-act="play"]');
  await expect(player.locator(".kr-voice__label")).toHaveText("Голосовое сообщение");
  await expect(player.locator('[data-role="dur"]')).toHaveText("0:02");
  await expect(btn).toBeEnabled();
  const box = (await btn.boundingBox())!;
  expect(box.width).toBeGreaterThanOrEqual(44);
  expect(box.height).toBeGreaterThanOrEqual(44);

  // «Расшифровка»: свёрнута, раскрывается нажатием.
  const details = player.locator("details");
  await expect(details).not.toHaveAttribute("open", "");
  await expect(player.getByText("Тестовая расшифровка голосового сообщения.")).toBeHidden();
  await details.locator("summary").click();
  await expect(player.getByText("Тестовая расшифровка голосового сообщения.")).toBeVisible();

  // Воспроизведение: кнопка переключает пауза/play, время идёт, волна закрашивается.
  await btn.click();
  await expect(player).toHaveClass(/is-playing/);
  await expect(btn).toHaveAttribute("aria-label", "Пауза");
  await expect.poll(() => player.evaluate((el) => parseFloat((el as HTMLElement).style.getPropertyValue("--p")) || 0)).toBeGreaterThan(0);
  await btn.click();
  await expect(player).not.toHaveClass(/is-playing/);
  await expect(btn).toHaveAttribute("aria-label", "Воспроизвести");
  await noHScroll(page);
});

test("голосовое без файла: неактивная плашка «Голосовое сообщение · 0:12»", async ({ page }) => {
  await page.goto(BASE + info.open);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1");
  const missing = page.locator('.kr-post[data-datetime="2026-10-03T09:15"] .kr-voice');
  await expect(missing).toHaveAttribute("data-missing", "1");
  await expect(missing.locator("audio")).toHaveCount(0);
  await expect(missing.locator('[data-act="play"]')).toBeDisabled();
  await expect(missing.locator(".kr-voice__meta")).toHaveText("Голосовое сообщение · 0:12", { useInnerText: true });
  await expect(missing.locator("details")).toHaveCount(0);
});

test("закрытая страница: голосовое расшифровывается и играет", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(BASE + info.closed);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 15000 });
  const player = page.locator(".kr-post > .kr-voice");
  await expect(player).toHaveCount(1);
  const src = await player.locator("audio").getAttribute("src");
  expect(src).toMatch(/^blob:/); // расшифрованный Blob URL, а не открытый файл
  await expect(player.locator('[data-act="play"]')).toBeEnabled();
  await player.locator('[data-act="play"]').click();
  await expect(player).toHaveClass(/is-playing/);
  await player.locator("summary").click();
  await expect(player.getByText("Расшифровка закрытого голосового.")).toBeVisible();
  expect(errors).toEqual([]);
  await noHScroll(page);
});

const VIDEO_POST = '.kr-post[data-datetime="2026-10-04T12:00"]';

test("видео в посте: плеер браузера, без автозапуска, длительность на постере, играет", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(BASE + info.open);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1");
  const post = page.locator(VIDEO_POST);
  const video = post.locator("video");
  await expect(post.locator(".kr-post__text")).toHaveCount(0); // пост только с видео
  await expect(video).toHaveAttribute("playsinline", "");
  await expect(video).toHaveAttribute("preload", "none");
  await expect(video).toHaveAttribute("controls", "");
  await expect(video).not.toHaveAttribute("autoplay", /.*/);
  expect(await video.getAttribute("poster")).toMatch(/^\/m\/[0-9a-f]{32}\.jpg$/);
  expect(await video.getAttribute("src")).toMatch(/^\/m\/[0-9a-f]{32}\.mp4$/);
  // Без нажатия не играет и не качается: preload=none, readyState 0.
  expect(await video.evaluate((v: HTMLVideoElement) => [v.paused, v.readyState, v.autoplay])).toEqual([true, 0, false]);
  const dur = post.locator(".kr-video__dur");
  await expect(dur).toHaveText("0:02");
  // Ширина по ленте: не шире поста, в кадре экрана 360 px.
  const [vb, pb] = [(await video.boundingBox())!, (await post.boundingBox())!];
  expect(vb.width).toBeLessThanOrEqual(pb.width + 0.5);
  expect(vb.width).toBeGreaterThan(300);
  await video.scrollIntoViewIfNeeded();
  // Родные элементы управления: фокус на плеере и пробел (клик по самому кадру в безголовом Chromium не переключает).
  await video.focus();
  await page.keyboard.press("Space");
  await expect.poll(() => video.evaluate((v: HTMLVideoElement) => (!v.paused || v.ended) && v.currentTime > 0)).toBe(true);
  await expect(post.locator(".kr-video")).toHaveClass(/is-started/);
  await expect(dur).toBeHidden(); // длительность живёт только на постере
  expect(await video.evaluate((v: HTMLVideoElement) => v.error)).toBeNull();
  await noHScroll(page);
  expect(errors).toEqual([]);
});

test("видео без файла: «Видео недоступно», ни <video>, ни кнопки", async ({ page }) => {
  await page.goto(BASE + info.open);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1");
  const post = page.locator('.kr-post[data-datetime="2026-10-06T12:00"]');
  await expect(post.locator("video")).toHaveCount(0);
  await expect(post.locator(".kr-video button")).toHaveCount(0);
  await expect(post.locator(".kr-video__off")).toHaveText("Видео недоступно");
  await expect(post.locator(".kr-video__dur")).toHaveText("0:15");
  await noHScroll(page);
});

test("голосовое у комментария: компактный плеер играет, расшифровка раскрывается", async ({ page }) => {
  await page.goto(BASE + info.open);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1");
  const comments = page.locator(VIDEO_POST + " .kr-comments");
  const voices = comments.locator(".kr-voice.kr-voice--compact");
  await expect(voices).toHaveCount(2);
  // Первый — с текстом и расшифровкой, второй — только голосовое, без файла.
  await expect(comments.locator(".kr-comment").nth(0).locator(".kr-comment__text")).toHaveText("Комментарий с текстом и голосовым.");
  await expect(comments.locator(".kr-comment").nth(1).locator(".kr-comment__text")).toHaveCount(0);
  const ok = voices.nth(0);
  const btn = ok.locator('[data-act="play"]');
  await expect(btn).toBeEnabled();
  const box = (await btn.boundingBox())!;
  expect(box.width).toBeGreaterThanOrEqual(44);
  expect(box.height).toBeGreaterThanOrEqual(44);
  await btn.click();
  await expect(ok).toHaveClass(/is-playing/);
  await expect.poll(() => ok.evaluate((el) => parseFloat((el as HTMLElement).style.getPropertyValue("--p")) || 0)).toBeGreaterThan(0);
  await btn.click();
  await expect(ok).not.toHaveClass(/is-playing/);
  await ok.locator("summary").click();
  await expect(ok.getByText("Расшифровка голосового комментария.")).toBeVisible();
  const missing = voices.nth(1);
  await expect(missing).toHaveAttribute("data-missing", "1");
  await expect(missing.locator('[data-act="play"]')).toBeDisabled();
  await expect(missing.locator(".kr-voice__meta")).toHaveText("Голосовое сообщение · 0:07", { useInnerText: true });
  await noHScroll(page);
});

test("закрытая страница: постер расшифровывается, видео — только по кнопке, затем играет", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  const mediaRequests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/m/")) mediaRequests.push(r.url());
  });
  await page.goto(BASE + info.closed);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 15000 });
  const post = page.locator('.kr-post[data-datetime="2026-10-07T18:00"]');
  const video = post.locator("video");
  await expect(video).toHaveAttribute("preload", "none");
  await expect(video).not.toHaveAttribute("src", /.*/); // файл не расшифрован и не скачан
  await expect(video).not.toHaveAttribute("controls", /.*/);
  await expect.poll(() => video.getAttribute("poster")).toMatch(/^blob:/); // постер расшифрован
  const before = mediaRequests.filter((u) => /\.bin(\?|$)/.test(u)).length;
  const btn = post.locator('[data-act="load"]');
  await expect(btn).toBeVisible();
  await expect(btn).toContainText("Смотреть видео");
  const bb = (await btn.boundingBox())!;
  expect(bb.height).toBeGreaterThanOrEqual(44);
  await btn.click();
  await expect.poll(() => video.getAttribute("src")).toMatch(/^blob:/);
  await expect(video).toHaveAttribute("controls", "");
  await expect.poll(() => video.evaluate((v: HTMLVideoElement) => (!v.paused || v.ended) && v.currentTime > 0)).toBe(true);
  expect(mediaRequests.filter((u) => /\.bin(\?|$)/.test(u)).length).toBeGreaterThan(before); // видео скачано после нажатия
  expect(await video.evaluate((v: HTMLVideoElement) => v.error)).toBeNull();
  // Голосовое у комментария на закрытой странице.
  const cv = post.locator(".kr-comments .kr-voice--compact");
  await expect(cv).toHaveCount(1);
  expect(await cv.locator("audio").getAttribute("src")).toMatch(/^blob:/);
  await noHScroll(page);
  expect(errors).toEqual([]);
});

test("фото в ленте грузятся лениво", async ({ page }) => {
  await page.goto(BASE + info.open);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1");
  const bad = await page.evaluate(() =>
    Array.from(document.querySelectorAll("img"))
      .filter((i) => !i.classList.contains("kr-avatar") && !i.classList.contains("kr-cover"))
      .filter((i) => i.getAttribute("loading") !== "lazy" || i.getAttribute("decoding") !== "async")
      .map((i) => i.className),
  );
  expect(bad).toEqual([]);
});

test("скриншот поста с видео 360", async ({ page }) => {
  const dir = process.env.VIDEO_SHOTS;
  test.skip(!dir, "VIDEO_SHOTS не задан");
  await page.goto(BASE + info.open);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1");
  await page.locator(VIDEO_POST).scrollIntoViewIfNeeded();
  await page.locator(VIDEO_POST).screenshot({ path: join(dir!, "video-post-360-open.png") });
  const gone = page.locator('.kr-post[data-datetime="2026-10-06T12:00"]');
  await gone.scrollIntoViewIfNeeded();
  await gone.screenshot({ path: join(dir!, "video-missing-360.png") });
  for (const [w, h] of [[360, 780], [768, 900], [1280, 900]]) {
    await page.setViewportSize({ width: w, height: h });
    await page.locator(VIDEO_POST).scrollIntoViewIfNeeded();
    await page.screenshot({ path: join(dir!, `video-${w}.png`) });
  }
  await page.setViewportSize({ width: 360, height: 780 });
  await page.emulateMedia({ colorScheme: "dark" });
  await page.screenshot({ path: join(dir!, "video-360-dark.png") });
  await page.goto(BASE + info.closed);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 15000 });
  await page.locator(".kr-video").first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: join(dir!, "video-closed-360-dark.png") });
});

test("скриншоты 360/768/1280 и тёмная тема", async ({ page }) => {
  const dir = process.env.VOICE_SHOTS;
  test.skip(!dir, "VOICE_SHOTS не задан");
  await page.goto(BASE + info.open);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1");
  await page.locator(".kr-voice details summary").first().click();
  for (const [w, h] of [[360, 780], [768, 900], [1280, 900]]) {
    await page.setViewportSize({ width: w, height: h });
    await page.locator('.kr-post[data-datetime="2026-10-03T09:15"]').scrollIntoViewIfNeeded();
    await page.screenshot({ path: join(dir!, `voice-${w}.png`), fullPage: true });
  }
  await page.setViewportSize({ width: 360, height: 780 });
  await page.emulateMedia({ colorScheme: "dark" });
  await page.screenshot({ path: join(dir!, "voice-360-dark.png"), fullPage: true });
});
