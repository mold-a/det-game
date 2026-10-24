// QA: правила баллов, попыток и подсказок в реальном UI (docs/01 §4–6).
import { test, expect } from "@playwright/test";
import { loadAnswers, startGame, article, headerScore, fillQuestion, submit, scoreLog, reachQuestion } from "../e2e/helpers";
import { readState, sumLog, qMsg, collectErrors, waitIdle } from "./qa_util";

const A = loadAnswers();
const PEN = Math.abs(A.settings.penalties.wrongAttempt);
const COST = A.settings.hints.cost;
const AUTO = A.settings.hints.autoAfterWrong;
const q1 = A.stages[0].questions.find((q) => q.path === "s1.q1")!;
const q2 = A.stages[0].questions.find((q) => q.path === "s1.q2")!;
const b1 = A.stages[0].questions.find((q) => q.path === "s1.b1")!;

const formVals = (over: Record<string, any>) => {
  const v: Record<string, any> = {};
  for (const f of q1.fields!) v[f.id] = f.input;
  return { ...v, ...over };
};

test("форма: штраф, повтор без штрафа (регистр/пробелы), неформат, автоподсказка, цены подсказок", async ({ page }) => {
  const errors = collectErrors(page);
  await startGame(page);
  const a = article(page, q1.path);

  // 1. Неверно → −PEN
  await fillQuestion(page, q1, formVals({ time: "21:17" }));
  await submit(page, q1.path);
  await expect(qMsg(page, q1.path)).toHaveText("Ответ не подтверждается материалами дела.", { timeout: 30_000 });
  expect(await headerScore(page)).toBe(-PEN);
  await expect(a.locator(".q__meta")).toContainText("Неверных попыток: 1");

  // 2. Тот же ответ другим регистром/пробелами/разделителем → «уже проверяли», без штрафа
  await fillQuestion(page, q1, formVals({ time: "  21.17 ", disease: "  АСТМА!! " }));
  await submit(page, q1.path);
  await expect(qMsg(page, q1.path)).toHaveText("Этот ответ уже проверяли.", { timeout: 30_000 });
  expect(await headerScore(page)).toBe(-PEN);

  // 3. Неформатный ввод — не попытка
  await fillQuestion(page, q1, formVals({ time: "25:70" }));
  await submit(page, q1.path);
  await expect(qMsg(page, q1.path)).toContainText("ЧЧ:ММ");
  expect(await headerScore(page)).toBe(-PEN);
  // пустое поле — не попытка
  await a.locator(".q__body .field").nth(0).locator("input").fill("");
  await submit(page, q1.path);
  await expect(qMsg(page, q1.path)).toContainText("Заполните все поля");
  expect(await headerScore(page)).toBe(-PEN);
  expect((await readState(page)).wrong[q1.path]).toHaveLength(1);

  // 4. Ещё неверные до порога автоподсказки
  for (let i = 2; i <= AUTO; i++) {
    await fillQuestion(page, q1, formVals({ time: `21:0${i}` }));
    await submit(page, q1.path);
    await waitIdle(page, q1.path);
    await expect(qMsg(page, q1.path)).toContainText("Ответ не подтверждается", { timeout: 30_000 });
  }
  await expect(qMsg(page, q1.path)).toContainText("Открыта подсказка 1 уровня — бесплатно.");
  await expect(a.locator(".hints__item")).toHaveCount(1);
  expect(await headerScore(page)).toBe(-PEN * AUTO);
  let s = await readState(page);
  expect(s.hints[q1.path]).toBe(1);
  expect(s.log.filter((e: any) => e.r.startsWith("hint:"))).toHaveLength(0);

  // 5. Подсказка 2: подтверждение с ценой; «Отмена» не списывает
  const hintBtn = a.getByRole("button", { name: `Подсказка (−${COST[1]})` });
  await hintBtn.click();
  const modal = page.locator(".modal");
  await expect(modal).toContainText(`Подсказка 2 уровня: −${COST[1]} баллов. Открыть?`);
  await modal.getByRole("button", { name: "Отмена" }).click();
  expect(await headerScore(page)).toBe(-PEN * AUTO);
  await hintBtn.click();
  await modal.getByRole("button", { name: `Открыть подсказку (−${COST[1]})` }).click();
  await expect(a.locator(".hints__item")).toHaveCount(2);
  expect(await headerScore(page)).toBe(-PEN * AUTO - COST[1]);
  await a.getByRole("button", { name: `Подсказка (−${COST[2]})` }).click();
  await modal.getByRole("button", { name: `Открыть подсказку (−${COST[2]})` }).click();
  await expect(a.locator(".hints__item")).toHaveCount(3);
  await expect(a).toContainText("Все подсказки открыты");
  const expected = -PEN * AUTO - COST[1] - COST[2];
  expect(await headerScore(page)).toBe(expected);

  // 6. Решение: подсказки остаются видимыми, кнопки подсказки нет; итог = сумма журнала
  await fillQuestion(page, q1);
  await submit(page, q1.path);
  await expect(a).toHaveClass(/q--solved/, { timeout: 30_000 });
  await expect(a.locator(".hints__item")).toHaveCount(3);
  s = await readState(page);
  expect(sumLog(s)).toBe(expected);
  const rows = await scoreLog(page);
  expect(rows.reduce((x, r) => x + r.delta, 0)).toBe(expected);
  await page.reload();
  expect(await headerScore(page)).toBe(expected);
  await expect(article(page, q1.path).locator(".hints__item")).toHaveCount(3);
  expect(errors).toEqual([]);
});

test("order: подсказка 1 за свою цену, автоподсказка не повторяется, повтор порядка без штрафа", async ({ page }) => {
  await startGame(page);
  await reachQuestion(page, A, q2.path);
  const a = article(page, q2.path);
  await a.getByRole("button", { name: `Подсказка (−${COST[0]})` }).click();
  await page.locator(".modal").getByRole("button", { name: `Открыть подсказку (−${COST[0]})` }).click();
  expect(await headerScore(page)).toBe(-COST[0]);
  for (let i = 0; i < AUTO; i++) {
    await fillQuestion(page, q2, q2.wrong[i]);
    await submit(page, q2.path);
    await waitIdle(page, q2.path);
  }
  expect(await headerScore(page)).toBe(-COST[0] - PEN * AUTO);
  await expect(qMsg(page, q2.path)).not.toContainText("бесплатно");
  // тот же неверный порядок ещё раз
  await fillQuestion(page, q2, q2.wrong[0]);
  await submit(page, q2.path);
  await expect(qMsg(page, q2.path)).toHaveText("Этот ответ уже проверяли.", { timeout: 30_000 });
  expect(await headerScore(page)).toBe(-COST[0] - PEN * AUTO);
  // подсказки нельзя купить не по порядку: только уровень 2
  await expect(a.locator("button", { hasText: `−${COST[2]}` })).toHaveCount(0);
});

test("бонус: одна попытка — неверно закрывает без баллов; верно +bonus", async ({ page, browser }) => {
  await startGame(page);
  await reachQuestion(page, A, b1.path); // бонус открывается после обязательных вопросов этапа
  const a = article(page, b1.path);
  await expect(a.locator(".mark-bonus")).toHaveText("Бонус, одна попытка");
  await expect(a.getByRole("button", { name: /Подсказка/ })).toHaveCount(0);
  await fillQuestion(page, b1, b1.wrong[0]);
  await submit(page, b1.path);
  await expect(a).toHaveClass(/q--closed/, { timeout: 30_000 });
  await expect(a.locator("input.input")).toHaveCount(0);
  expect(await headerScore(page)).toBe(0);
  expect((await readState(page)).log).toHaveLength(0);
  await page.reload();
  await expect(article(page, b1.path)).toHaveClass(/q--closed/);

  const ctx2 = await browser.newContext();
  const p2 = await ctx2.newPage();
  await startGame(p2);
  await reachQuestion(p2, A, b1.path);
  // регистр/пробелы в бонусе тоже нормализуются
  await fillQuestion(p2, b1, `  ${String(b1.input).toUpperCase()}  `);
  await submit(p2, b1.path);
  await expect(article(p2, b1.path)).toHaveClass(/q--solved/, { timeout: 30_000 });
  expect(await headerScore(p2)).toBe(A.settings.points.bonus);
  await ctx2.close();
});
