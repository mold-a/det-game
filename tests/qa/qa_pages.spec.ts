// QA: закрытые страницы по QR (docs/02 §3.8–3.9): ключ из #k= — убран из адреса и
// истории, не в localStorage, не в сети; повреждённый ключ → «Эта страница открывается по QR-коду»;
// облако — в sessionStorage ключ, а не пароль; без внешних запросов и console.error.
import { test, expect, type Page, type Request } from "@playwright/test";
import { readFileSync } from "node:fs";
import { collectErrors } from "./qa_util";

const LOCK = JSON.parse(readFileSync("engine/salts.lock.json", "utf-8"));
const KEYS: Record<string, string> = LOCK.pages;
const BROKEN = "Эта страница открывается по QR-коду из материалов дела. Отсканируйте его.";

function recordRequests(page: Page) {
  const reqs: Request[] = [];
  page.on("request", (r) => reqs.push(r));
  return reqs;
}

for (const [slug, key] of Object.entries(KEYS)) {
  test(`закрытая страница ${slug}: ключ убирается и никуда не уходит`, async ({ page, baseURL }) => {
    const errors = collectErrors(page);
    const reqs = recordRequests(page);
    await page.goto("about:blank");
    await page.goto(`/p/${slug}/#k=${key}`);
    await expect(page.locator("body[data-ready='1']")).toHaveCount(1, { timeout: 15_000 });
    expect(page.url()).toBe(`${baseURL}/p/${slug}/`);
    expect(await page.evaluate(() => location.hash)).toBe("");
    const len = await page.evaluate(() => history.length);
    // localStorage не содержит ключа; sessionStorage — да (так задумано)
    const ls = await page.evaluate(() => JSON.stringify({ ...localStorage }));
    expect(ls).not.toContain(key);
    const ss = await page.evaluate(() => ({ ...sessionStorage }));
    expect(ss[`detgame:page:${slug}`]).toBe(key);
    // ни один запрос (URL, заголовки, тело) не содержит ключ; все запросы — на свой origin
    for (const r of reqs) {
      expect(r.url(), r.url()).not.toContain(key);
      const hdrs = JSON.stringify(await r.allHeaders());
      expect(hdrs, r.url()).not.toContain(key);
      expect(r.postData() ?? "").not.toContain(key);
      expect(new URL(r.url()).origin, r.url()).toBe(new URL(baseURL!).origin);
    }
    // переход по ссылке со страницы: referrer без ключа
    await page.evaluate(() => {
      const a = document.createElement("a");
      a.href = "/p/news/";
      a.id = "qa-link";
      a.textContent = "x";
      document.body.append(a);
    });
    await page.click("#qa-link");
    await page.waitForURL("**/p/news/");
    expect(await page.evaluate(() => document.referrer)).not.toContain(key);
    // назад: запись истории без фрагмента; страница открывается из sessionStorage
    await page.goBack();
    expect(page.url()).toBe(`${baseURL}/p/${slug}/`);
    await expect(page.locator("body[data-ready='1']")).toHaveCount(1, { timeout: 15_000 });
    await page.goBack();
    expect(page.url()).toBe("about:blank");
    expect(len).toBe(2);
    // перезагрузка без фрагмента — работает
    await page.goForward();
    await page.reload();
    await expect(page.locator("body[data-ready='1']")).toHaveCount(1, { timeout: 15_000 });
    expect(errors).toEqual([]);
  });
}

test("повреждённые ключи → «Эта страница открывается по QR-коду», плохой ключ не остаётся в sessionStorage", async ({ page, context }) => {
  const errors = collectErrors(page);
  const k = KEYS.inna;
  const bad = [
    "",
    "garbage",
    k.slice(0, -2),
    k.slice(0, -1) + (k.endsWith("A") ? "B" : "A"),
    KEYS.pharma, // ключ другой страницы
    k + "AA",
    "%%%",
  ];
  for (const b of bad) {
    const p = await context.newPage();
    collectErrors(p).length;
    await p.goto(`/p/inna/#k=${b}`);
    await expect(p.locator("#shell-broken"), b).toBeVisible({ timeout: 15_000 });
    await expect(p.locator("#shell-broken")).toHaveText(BROKEN);
    expect(p.url()).not.toContain("#");
    expect(await p.evaluate(() => sessionStorage.getItem("detgame:page:inna"))).toBeNull();
    await p.close();
  }
  // без ключа совсем
  await page.goto("/p/pharma/");
  await expect(page.locator("#shell-broken")).toBeVisible();
  // испорченный ключ в sessionStorage
  await page.evaluate(() => sessionStorage.setItem("detgame:page:pharma", "A".repeat(43)));
  await page.reload();
  await expect(page.locator("#shell-broken")).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem("detgame:page:pharma"))).toBeNull();
  expect(errors).toEqual([]);
});

test("облако: неверный пароль без блокировки; в sessionStorage — выведенный ключ", async ({ page }) => {
  const errors = collectErrors(page);
  const reqs = recordRequests(page);
  await page.goto("/p/cloud/");
  const pw = page.locator("input[name=password]");
  await pw.fill("неверный");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.locator("#shell-error")).toHaveText("Неверный пароль", { timeout: 15_000 });
  await page.getByRole("button", { name: "Войти" }).click(); // пусто
  await pw.fill("");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.locator("#shell-error")).toHaveText("Введите пароль");
  // пароль из контента (TODO(content)) нормализуется как password
  const cfg = readFileSync("content/pages/cloud/page.yaml", "utf-8");
  const m = /^password:\s*"([^"]*)"/m.exec(cfg)!;
  await pw.fill(`  ${m[1].toUpperCase()} `);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.locator("body[data-ready='1']")).toHaveCount(1, { timeout: 15_000 });
  const ss = await page.evaluate(() => ({ ...sessionStorage }));
  const v = ss["detgame:page:cloud"];
  expect(v).toMatch(/^[A-Za-z0-9_-]{43}$/);
  expect(JSON.stringify(ss).toLowerCase()).not.toContain("todo");
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage }))).toBe("{}");
  for (const r of reqs) expect(r.postData() ?? "").toBe("");
  await page.reload();
  await expect(page.locator("body[data-ready='1']")).toHaveCount(1, { timeout: 15_000 });
  expect(errors).toEqual([]);
});
