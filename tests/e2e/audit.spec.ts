// P08 п. 3 — аудит системы расследования: ни одного запроса вне своего origin,
// нет console.error и ошибок страницы, noindex и robots.txt, фокус и порядок
// табуляции, alt у изображений. Вымышленные страницы — pages.spec (P06).
import { test, expect, type Page, type ConsoleMessage } from "@playwright/test";
import { loadAnswers, startGame, playToStage, labAll, fillQuestion, submit, article } from "./helpers";

const A = loadAnswers();
test.setTimeout(240_000);

function watch(page: Page) {
  const origin = new URL(test.info().project.use.baseURL ?? process.env.E2E_BASE_URL ?? "http://127.0.0.1:8000").origin;
  const foreign: string[] = [];
  const errors: string[] = [];
  const requests: string[] = [];
  page.on("request", (r) => {
    const u = r.url();
    if (u.startsWith("data:") || u.startsWith("blob:")) return;
    requests.push(u);
    if (new URL(u).origin !== origin) foreign.push(u);
  });
  page.on("console", (m: ConsoleMessage) => {
    if (m.type() === "error") errors.push(`${m.text()} @ ${m.location().url}`);
  });
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("response", (r) => {
    if (r.status() >= 400) errors.push(`HTTP ${r.status()} ${r.url()}`);
  });
  return { foreign, errors, requests };
}

async function altCheck(page: Page) {
  const bad = await page.locator("img:not([alt])").count();
  expect(bad, "img без alt").toBe(0);
}

test("сеть, консоль и alt: полное прохождение по всем страницам системы", async ({ page }) => {
  const w = watch(page);
  await page.goto("/");
  await page.goto("/lab/");
  await page.goto("/final/");
  const last = A.stages[A.stages.length - 1];
  const done = await playToStage(page, A, last.n);
  await altCheck(page);
  await labAll(page, A, last.n, done);
  await page.goto("/lab/");
  await page.locator(".lab-archive__item.is-done .btn").first().click();
  await altCheck(page);
  await page.goto("/final/");
  await page.getByRole("button", { name: "Начать финал" }).click();
  const byPath = Object.fromEntries(last.questions.map((q) => [q.path, q]));
  for (const path of A.finalOrder) {
    await fillQuestion(page, byPath[path]);
    await submit(page, path);
  }
  await expect(page.locator("#final-title")).toHaveText("Итоги", { timeout: 60_000 });
  await page.getByRole("button", { name: "Перейти к развязке" }).click();
  await altCheck(page);

  expect(w.foreign, "запросы вне своего origin").toEqual([]);
  expect(w.errors, "console.error / ошибки страницы / HTTP ≥ 400").toEqual([]);
  // finale.json — только после последнего ответа (F9): он должен быть в журнале запросов один раз за переход к итогам.
  expect(w.requests.filter((u) => u.endsWith("/data/finale.json")).length).toBeGreaterThanOrEqual(1);
});

test("finale.json не скачивается до конца финала", async ({ page }) => {
  const w = watch(page);
  await startGame(page);
  await page.goto("/lab/");
  await page.goto("/final/");
  await page.goto("/");
  expect(w.requests.filter((u) => u.includes("finale.json"))).toEqual([]);
});

test("noindex на страницах системы и robots.txt", async ({ page, request }) => {
  for (const path of ["/", "/lab/", "/final/"]) {
    await page.goto(path);
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
    await expect(page.locator('meta[name="viewport"]')).toHaveCount(1);
    await expect(page.locator("html")).toHaveAttribute("lang", "ru");
    expect(await page.title()).not.toBe("");
  }
  const robots = await request.get("/robots.txt");
  expect(robots.ok()).toBeTruthy();
  const text = await robots.text();
  expect(text).toMatch(/User-agent:\s*\*/);
  expect(text).toMatch(/Disallow:\s*\/\s*$/m);
});

/** Описание элемента в фокусе и есть ли у него видимая обводка. */
async function focused(page: Page) {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    if (!el || el === document.body) return { id: "body", visible: false };
    const ring = (n: Element | null) => {
      if (!n) return false;
      const cs = getComputedStyle(n);
      return (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0) || /rgb/.test(cs.boxShadow);
    };
    const visible = ring(el) || ring(el.closest(".person"));
    const label = (el.getAttribute("aria-label") || el.textContent || (el as HTMLInputElement).value || "").trim().slice(0, 30);
    return { id: `${el.tagName.toLowerCase()}.${el.className || ""} ${label}`, visible };
  });
}

test("порядок табуляции и видимый фокус: первый запуск и главный экран", async ({ page }) => {
  await page.goto("/");
  // Первый запуск: фокус в поле названия команды, Tab → «Открыть дело».
  await expect(page.locator("#team")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Открыть дело" })).toBeFocused();

  await startGame(page);
  // Свежая загрузка: последовательная навигация начинается с начала документа.
  await page.reload();
  await expect(page.locator("#stage-title")).toBeVisible();
  await page.keyboard.press("Tab");
  const order: string[] = [];
  const invisible: string[] = [];
  for (let i = 0; i < 80; i++) {
    const f = await focused(page);
    if (f.id === "body") break; // конец документа: дальше — интерфейс браузера
    order.push(f.id);
    if (!f.visible) invisible.push(f.id);
    await page.keyboard.press("Tab");
  }
  // Пропуск к содержанию → шапка (дело, меню) → письмо → вопросы → панель документов.
  expect(order[0]).toMatch(/skip-link/);
  expect(order[1]).toMatch(/app-header__case-no/);
  expect(order[2]).toMatch(/menu__toggle/);
  const letter = order.findIndex((s) => /summary/.test(s) && !/menu/.test(s));
  const firstInput = order.findIndex((s) => /input|select/.test(s));
  expect(letter).toBeGreaterThan(2);
  expect(firstInput).toBeGreaterThan(letter);
  expect(invisible, "элементы в фокусе без видимой обводки").toEqual([]);
  // Последний элемент — журнал баллов в боковой панели (после вопросов и документов).
  expect(order[order.length - 1]).toMatch(/scorelog__summary/);
  console.log("TAB ORDER\n" + order.join("\n"));
});

test("окно подтверждения: фокус внутри, Esc закрывает, фокус возвращается", async ({ page }) => {
  await startGame(page);
  const q = A.stages[0].questions.find((x) => x.kind === "mandatory")!;
  const btn = article(page, q.path).getByRole("button", { name: /Подсказка/ });
  await btn.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".modal")).toBeVisible();
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => !!document.activeElement?.closest(".modal"))).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(page.locator(".modal")).toHaveCount(0);
  await expect(btn).toBeFocused();
  // Фон под окном был недоступен (inert) и снова доступен.
  expect(await page.locator(".layout").evaluate((n) => (n.closest("[inert]") ? 1 : 0))).toBe(0);
});
