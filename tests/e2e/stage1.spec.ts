// P04: прохождение этапа 1 правильными ответами; неверный ответ −5, повтор — без штрафа;
// перезагрузка не теряет прогресс. Ответы — из tests/.answers.json.
import { test, expect } from "@playwright/test";
import { loadAnswers, startGame, article, fillQuestion, submit, solve, headerScore, envelopeOpened } from "./helpers";

const A = loadAnswers();
const stage1 = A.stages[0];
const penalty = A.settings.penalties.wrongAttempt;

test("этап 1: штраф за неверный ответ, повтор без штрафа, переход к этапу 2", async ({ page }) => {
  await startGame(page);
  expect(await headerScore(page)).toBe(0);

  const order = stage1.questions.find((q) => q.type === "order")!;
  await fillQuestion(page, order, order.wrong[0]);
  await submit(page, order.path);
  await expect(article(page, order.path).locator(".q__msg")).toHaveText(/не подтверждается/);
  expect(await headerScore(page)).toBe(penalty);

  await fillQuestion(page, order, order.wrong[0]);
  await submit(page, order.path);
  await expect(article(page, order.path).locator(".q__msg")).toHaveText("Этот ответ уже проверяли.");
  expect(await headerScore(page)).toBe(penalty);

  // Неформатный ввод — не попытка.
  const form = stage1.questions.find((q) => q.type === "form")!;
  const bad = Object.fromEntries(form.fields!.map((f) => [f.id, f.input]));
  bad[form.fields!.find((f) => f.type === "time")!.id] = "25:70";
  await fillQuestion(page, form, bad);
  await submit(page, form.path);
  await expect(article(page, form.path).locator(".q__msg")).toHaveText(/ЧЧ:ММ/);
  expect(await headerScore(page)).toBe(penalty);

  // Бонус — до перехода, затем обязательные.
  for (const q of stage1.questions.filter((x) => x.kind === "bonus")) {
    await solve(page, q);
  }
  const bonusPts = A.settings.points.bonus * stage1.questions.filter((x) => x.kind === "bonus").length;
  expect(await headerScore(page)).toBe(penalty + bonusPts);

  const mandatory = stage1.questions.filter((q) => q.kind === "mandatory");
  for (const q of mandatory.slice(0, -1)) await solve(page, q);
  const last = mandatory[mandatory.length - 1];
  await fillQuestion(page, last);
  await submit(page, last.path);
  await expect(page.locator(".modal")).toContainText("2", { timeout: 30_000 });
  await envelopeOpened(page);
  await expect(page.locator("#stage-title")).toHaveText("Этап 2");

  // Журнал баллов: одна запись штрафа, бонус.
  await page.locator(".scorelog__summary").click();
  await expect(page.locator(".scorelog tbody tr")).toHaveCount(1 + stage1.questions.filter((x) => x.kind === "bonus").length);

  // Перезагрузка не теряет прогресс и не показывает конверт повторно.
  await page.reload();
  await expect(page.locator("#stage-title")).toHaveText("Этап 2");
  await expect(page.locator(".modal")).toHaveCount(0);
  expect(await headerScore(page)).toBe(penalty + bonusPts);
  await expect(page.locator("details.passed")).toHaveCount(1);
});

test("три ошибки → бесплатная подсказка; покупка уровней 2 и 3 по порядку", async ({ page }) => {
  await startGame(page);
  const order = stage1.questions.find((q) => q.type === "order")!;
  const N = A.settings.hints.autoAfterWrong;
  for (let i = 0; i < N; i++) {
    await fillQuestion(page, order, order.wrong[i]);
    await submit(page, order.path);
    await expect(article(page, order.path).locator(".q__meta")).toHaveText(`Неверных попыток: ${i + 1}`);
  }
  await expect(article(page, order.path).locator(".hints__item")).toHaveCount(1);
  expect(await headerScore(page)).toBe(N * penalty);

  const costs: number[] = A.settings.hints.cost;
  for (const level of [2, 3]) {
    await article(page, order.path).getByRole("button", { name: /Подсказка/ }).click();
    await expect(page.locator(".modal")).toContainText(`Подсказка ${level} уровня`);
    await page.locator(".modal [data-action=ok]").click();
    await expect(article(page, order.path).locator(".hints__item")).toHaveCount(level);
  }
  expect(await headerScore(page)).toBe(N * penalty - costs[1] - costs[2]);
});
