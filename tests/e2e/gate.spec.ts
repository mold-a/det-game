// Профили закрытых этапов (docs/04 «Профили закрытых этапов», docs/02 §3.10): до открытия этапа ссылки и поиск
// «Круга» ведут на заглушку, после — на настоящий профиль. Профиль берётся из выдачи поиска на /p/krug/
// (пункт «Профиль закрыт»), а не из кода. Запуск — после build и dump-answers, против `python -m engine serve`:
//   DETGAME_BASE_URL=http://127.0.0.1:8772 PW_CHROMIUM_PATH=… npx playwright test tests/e2e/gate.spec.ts
import { test, expect, type Page } from "@playwright/test";
import { loadAnswers, playToStage } from "./helpers";

if (process.env.DETGAME_BASE_URL) test.use({ baseURL: process.env.DETGAME_BASE_URL });
test.setTimeout(240_000);

const A = loadAnswers();

/** Первый закрытый профиль из открытого индекса поиска: slug и имя. */
async function closedEntry(page: Page) {
  await page.goto("/p/krug/");
  await expect(page.locator("body")).toHaveAttribute("data-gate-ready", "1");
  const li = page.locator(".kr-person:has(.kr-person__pos--closed)").first();
  await expect(li).toHaveCount(1);
  return { slug: (await li.getAttribute("data-slug"))!, name: (await li.getAttribute("data-name"))! };
}

async function search(page: Page, name: string) {
  await page.goto("/p/krug/");
  await expect(page.locator("body")).toHaveAttribute("data-gate-ready", "1");
  await page.locator("#kr-q").fill(name.split(" ").slice(0, 2).join(" "));
  const hit = page.locator(".kr-person:not([hidden])", { hasText: name });
  await expect(hit).toHaveCount(1);
  return hit;
}

test("до открытия этапа — заглушка, после — профиль (ссылки, поиск, переход с заглушки)", async ({ page }) => {
  const { slug, name } = await closedEntry(page);

  // этап 1: «Профиль закрыт», ссылка на krug-private с #to=
  let hit = await search(page, name);
  await expect(hit).toContainText("Профиль закрыт");
  await expect(hit.locator("a")).toHaveAttribute("href", `/p/krug-private/#to=${slug}`);
  await hit.locator("a").click();
  await expect(page).toHaveURL(new RegExp(`/p/krug-private/#to=${slug}$`));
  await expect(page.locator("body")).toHaveAttribute("data-gate-ready", "1");
  await expect(page.getByText("ограничил доступ")).toBeVisible();
  // в сетевом трафике и разметке нет ключа профиля
  const key = (A as any).pages?.find((p: any) => p.slug === slug)?.key;
  if (key) expect(await page.content()).not.toContain(key);

  // открыть этап 2 тем же браузером (прогресс в localStorage)
  await playToStage(page, A, 2, new Set(), "skip");

  hit = await search(page, name);
  await expect(hit).not.toContainText("Профиль закрыт");
  const href = await hit.locator("a").getAttribute("href");
  expect(href).toMatch(new RegExp(`^/p/${slug}/#k=[A-Za-z0-9_-]+$`));
  if (key) expect(href).toBe(`/p/${slug}/#k=${key}`);
  await hit.locator("a").click();
  await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 15_000 });
  await expect(page.locator("h1")).toHaveText(name);

  // старая ссылка-заглушка сама переходит на профиль
  await page.goto(`/p/krug-private/#to=${slug}`);
  await expect(page).toHaveURL(new RegExp(`/p/${slug}/$`), { timeout: 15_000 });
  await expect(page.locator("h1")).toHaveText(name);

  // на главной «Круга» ссылок-заглушек на этот профиль не осталось
  await page.goto("/p/krug/");
  await expect(page.locator("body")).toHaveAttribute("data-gate-ready", "1");
  await expect(page.locator(`a[href*="#to=${slug}"]`)).toHaveCount(0);
});
