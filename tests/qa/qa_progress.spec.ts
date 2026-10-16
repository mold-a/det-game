// QA: устойчивость прогресса (docs/01 §10, docs/02 §4): импорт испорченного/чужого
// файла, недоступный localStorage, несовместимая сборка, две вкладки.
import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { loadAnswers, startGame, article, headerScore, fillQuestion, submit } from "../e2e/helpers";
import { readState, writeState, sumLog, STORE_KEY, collectErrors, waitIdle } from "./qa_util";

const A = loadAnswers();
const PEN = Math.abs(A.settings.penalties.wrongAttempt);
const q2 = A.stages[0].questions.find((q) => q.path === "s1.q2")!;
const q1 = A.stages[0].questions.find((q) => q.path === "s1.q1")!;

async function importText(page: Page, name: string, text: string) {
  await page.locator(".menu summary").click();
  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Загрузить из файла" }).click();
  await (await chooser).setFiles({ name, mimeType: "application/json", buffer: Buffer.from(text, "utf-8") });
}

test("импорт: мусор, чужая сборка, подменённый ключ, некорректная форма — прогресс не меняется", async ({ page }) => {
  const errors = collectErrors(page);
  await startGame(page);
  await fillQuestion(page, q2, q2.wrong[0]);
  await submit(page, q2.path);
  await waitIdle(page, q2.path);
  const before = await readState(page);
  const modal = page.locator(".modal");

  const cases: [string, string, RegExp][] = [
    ["garbage.json", "это не json {", /не похож на сохранённый прогресс/],
    ["null.json", "null", /не похож на сохранённый прогресс/],
    ["arr.json", "[]", /не похож на сохранённый прогресс/],
    ["v2.json", JSON.stringify({ ...before, v: 2 }), /не похож на сохранённый прогресс/],
    ["badlog.json", JSON.stringify({ ...before, log: [{ d: "много", r: "x" }] }), /не похож на сохранённый прогресс/],
    ["foreign.json", JSON.stringify({ ...before, saltsId: "f".repeat(64) }), /другой версии сайта/],
    ["othergame.json", JSON.stringify({ ...before, gameId: "other" }), /другой версии сайта/],
    ["badkey.json", JSON.stringify({ ...before, keys: { 1: "A".repeat(43) } }), /другой версии сайта/],
    ["stage3nokey.json", JSON.stringify({ ...before, stage: 3 }), /другой версии сайта/],
  ];
  for (const [name, text, re] of cases) {
    await importText(page, name, text);
    await expect(modal, name).toContainText(re);
    await modal.getByRole("button", { name: "Понятно" }).click();
    await expect(modal).toHaveCount(0);
    expect(await readState(page), name).toEqual(before);
  }
  expect(await headerScore(page)).toBe(-PEN);

  // Корректный экспорт → импорт
  await page.locator(".menu summary").click();
  const dl = page.waitForEvent("download");
  await page.getByRole("button", { name: "Сохранить прогресс в файл" }).click();
  const file = await (await dl).path();
  const text = readFileSync(file!, "utf-8");
  expect(JSON.parse(text).log).toHaveLength(1);
  // сбросить и загрузить
  const mod = JSON.parse(text);
  await importText(page, "ok.json", JSON.stringify({ ...mod, team: "Импорт" }));
  await modal.getByRole("button", { name: "Загрузить" }).click();
  await expect(page.locator(".app-header__team")).toContainText("Импорт");
  expect(errors).toEqual([]);
});

test("localStorage бросает на setItem/getItem: предупреждение, игра работает в памяти", async ({ page }) => {
  const errors = collectErrors(page);
  await page.addInitScript(() => {
    const thrower = () => {
      throw new DOMException("blocked", "SecurityError");
    };
    Storage.prototype.setItem = thrower;
    Storage.prototype.getItem = thrower;
    Storage.prototype.removeItem = thrower;
  });
  await page.goto("/");
  await expect(page.locator(".notice")).toContainText("Браузер не даёт сохранять данные");
  await startGame(page);
  await expect(page.locator(".notice").first()).toContainText("Браузер не даёт сохранять данные");
  await fillQuestion(page, q2, q2.wrong[0]);
  await submit(page, q2.path);
  await waitIdle(page, q2.path);
  expect(await headerScore(page)).toBe(-PEN);
  await fillQuestion(page, q2);
  await submit(page, q2.path);
  await expect(article(page, q2.path)).toHaveClass(/q--solved/, { timeout: 30_000 });
  expect(errors).toEqual([]);
});

test("доступ к window.localStorage бросает (Safari с запретом cookie)", async ({ page }) => {
  const errors = collectErrors(page);
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new DOMException("denied", "SecurityError");
      },
    });
  });
  await page.goto("/");
  await expect(page.locator(".notice")).toContainText("Браузер не даёт сохранять данные");
  await startGame(page);
  await fillQuestion(page, q2, q2.wrong[0]);
  await submit(page, q2.path);
  await waitIdle(page, q2.path);
  expect(await headerScore(page)).toBe(-PEN);
  // лаборатория и финал тоже не падают
  await page.goto("/lab/");
  await expect(page.locator("main")).toBeVisible();
  expect(errors).toEqual([]);
});

test("несовместимая сборка: другой saltsId в public.json и в прогрессе; повреждённый JSON", async ({ page, context }) => {
  const errors = collectErrors(page);
  await startGame(page);
  const st = await readState(page);
  // (а) прогресс с чужим saltsId
  await writeState(page, { ...st, saltsId: "0".repeat(64) });
  await page.reload();
  await expect(page.locator("h1")).toHaveText("Прогресс несовместим");
  await expect(page.getByRole("button", { name: "Начать заново" })).toBeVisible();
  for (const p of ["/lab/", "/final/"]) {
    await page.goto(p);
    await expect(page.locator("h1"), p).toHaveText("Прогресс несовместим");
  }
  // (б) сборка пересобрана: public.json с другим saltsId
  await writeState(page, st);
  await page.route("**/data/public.json", async (route) => {
    const res = await route.fetch();
    const j = await res.json();
    await route.fulfill({ response: res, json: { ...j, saltsId: "1".repeat(64) } });
  });
  await page.goto("/");
  await expect(page.locator("h1")).toHaveText("Прогресс несовместим");
  await page.unroute("**/data/public.json");
  // (в) сборка с теми же saltsId, но другим стартовым ключом (подменённая соль) → тоже «несовместим»
  await page.route("**/data/public.json", async (route) => {
    const res = await route.fetch();
    const j = await res.json();
    await route.fulfill({ response: res, json: { ...j, saltStart: "AAAAAAAAAAAAAAAAAAAAAA" } });
  });
  await writeState(page, { ...st, keys: { 1: "B".repeat(43) } });
  await page.goto("/");
  await expect(page.locator("h1")).toHaveText("Прогресс несовместим");
  await page.unroute("**/data/public.json");
  // (г) нечитаемый JSON
  await page.evaluate((k) => localStorage.setItem(k, "{oops"), STORE_KEY);
  await page.goto("/");
  await expect(page.locator(".notice--error")).toContainText("повреждён");
  // «Начать заново» → двойное подтверждение → первый экран
  await page.getByRole("button", { name: "Начать заново" }).click();
  await page.locator(".modal").getByRole("button", { name: "Продолжить" }).click();
  await page.locator(".modal").getByRole("button", { name: "Удалить прогресс" }).click();
  await expect(page.locator("#team")).toBeVisible();
  expect(errors).toEqual([]);
});

test("пересборка с другим ответом (saltsId тот же, K1 тот же, K2 другой) → «Прогресс несовместим» (docs/01 §10, docs/02 §4)", async ({ page }) => {
  // Эквивалент реального сценария: автор исправил канон ответа этапа 1 и пересобрал сайт —
  // соли постоянны (salts.lock.json), поэтому saltsId и K1 совпадают, а K2 из прогресса пакет 2 не открывает.
  await startGame(page);
  const st = await readState(page);
  await writeState(page, { ...st, stage: 2, envelopeAck: 2, keys: { ...st.keys, 2: "A".repeat(43) } });
  await page.reload();
  await expect(page.locator("h1")).toHaveText("Прогресс несовместим");
});
