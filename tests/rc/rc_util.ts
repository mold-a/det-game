// Общее для RC-проходов: сбор ошибок/внешних запросов, проверка вёрстки и картинок, скриншоты.
import { expect, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

export const SHOTS = process.env.RC_SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });

export type Watch = { problems: string[]; bytes: Map<string, number>; urls: string[] };

/** Слушатели: console.error, pageerror, requestfailed, ответы >= 400, запросы не на свой хост. */
export function watch(page: Page): Watch {
  const w: Watch = { problems: [], bytes: new Map(), urls: [] };
  page.on("console", (m) => {
    if (m.type() === "error") w.problems.push(`console.error: ${m.text()} @ ${page.url()}`);
  });
  page.on("pageerror", (e) => w.problems.push(`pageerror: ${e.message} @ ${page.url()}`));
  page.on("requestfailed", (r) => {
    // прерванные нами/браузером запросы медиа (перемотка, закрытие) — не дефект
    w.problems.push(`requestfailed: ${r.url()} ${r.failure()?.errorText} @ ${page.url()}`);
  });
  page.on("request", (r) => {
    const u = r.url();
    w.urls.push(u);
    if (!/^(http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\/|data:|blob:)/.test(u)) w.problems.push(`внешний запрос: ${u}`);
  });
  page.on("response", async (r) => {
    if (r.status() >= 400) w.problems.push(`HTTP ${r.status()}: ${r.url()} @ ${page.url()}`);
    try {
      const len = Number(r.headers()["content-length"] || 0) || (await r.body()).length;
      w.bytes.set(r.url(), len);
    } catch {
      /* тело недоступно */
    }
  });
  return w;
}

/** Нет горизонтальной прокрутки. */
export async function noHScroll(page: Page, what = "") {
  const [sw, iw] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  expect(sw, `горизонтальная прокрутка ${what} ${page.url()}`).toBeLessThanOrEqual(iw);
}

/** Прокрутить страницу целиком (подгрузка ленивых картинок), вернуться вверх. */
export async function scrollThrough(page: Page) {
  await page.evaluate(async () => {
    const h = document.documentElement.scrollHeight;
    for (let y = 0; y < h; y += Math.max(300, innerHeight * 0.8)) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 60));
    }
    window.scrollTo(0, document.documentElement.scrollHeight);
    await new Promise((r) => setTimeout(r, 150));
    window.scrollTo(0, 0);
  });
}

/** Битые картинки: img с src, который не загрузился. → список. */
export async function brokenImages(page: Page): Promise<string[]> {
  await scrollThrough(page);
  await page.waitForTimeout(400);
  return page.evaluate(() =>
    Array.from(document.querySelectorAll("img"))
      .filter((i) => i.getAttribute("src") && (!i.complete || i.naturalWidth === 0))
      .map((i) => (i.getAttribute("src") || "").slice(0, 80) + " alt=" + i.alt),
  );
}

/** Текст «Здесь будет …» / TODO на странице — пустые места-заглушки. */
export async function placeholders(page: Page): Promise<string[]> {
  const t = await page.locator("body").innerText();
  return (t.match(/Здесь будет[^\n]*|TODO\(content\)[^\n]*|undefined|\[object Object\]|NaN/g) ?? []).slice(0, 5);
}

let n = 0;
/** Скриншот (если задан RC_SHOTS) + проверка прокрутки. */
export async function shot(page: Page, name: string, full = true) {
  await noHScroll(page, name);
  if (!SHOTS) return;
  n++;
  await page.screenshot({ path: join(SHOTS, `rc-${name}.png`), fullPage: full });
}
