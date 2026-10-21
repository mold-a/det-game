// P04: прохождение этапа 1 правильными ответами; неверный ответ −5, повтор — без штрафа;
// перезагрузка не теряет прогресс. Ответы — из tests/.answers.json.
import { test, expect } from "@playwright/test";
import { loadAnswers, startGame, article, fillQuestion, submit, solve, headerScore, envelopeOpened, envelopeOpenedOnly, scoreLog } from "./helpers";

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
  await expect(article(page, order.path).getByText("Все подсказки открыты")).toBeVisible();

  // Журнал: N штрафов, подсказки 2 и 3 по цене; бесплатная подсказка 1 не пишется (F16); итог = счёт.
  const log = await scoreLog(page);
  expect(log.map((e) => e.delta)).toEqual([...Array(N).fill(penalty), -costs[1], -costs[2]]);
  expect(log.filter((e) => /Подсказка 1 уровня/.test(e.reason))).toHaveLength(0);
  await expect(page.locator(".scorelog tfoot td")).toHaveText(String(N * penalty - costs[1] - costs[2]).replace("-", "\u2212"));
});

test("вопросы этапа скрыты за «Перейти к вопросам»; отмена не открывает; флаг переживает перезагрузку", async ({ page }) => {
  await page.goto("/");
  await page.locator("#team").fill("Тестовая команда");
  await page.getByRole("button", { name: "Открыть дело" }).click();
  await envelopeOpenedOnly(page);

  // Письмо руководителя видно, вопросов и подсказок нет.
  await expect(page.locator("details.letter")).toBeVisible();
  const gate = page.getByRole("button", { name: "Перейти к вопросам", exact: true });
  await expect(gate).toBeVisible();
  await expect(page.getByText("Откройте, когда команда изучит все документы конверта")).toBeVisible();
  await expect(page.locator("article[data-path]")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Подсказка/ })).toHaveCount(0);

  // «Отмена» оставляет вопросы скрытыми.
  await gate.click();
  const modal = page.locator(".modal");
  await expect(modal).toContainText("Перейти к вопросам этапа 1?");
  await expect(modal).toContainText("Документы можно изучать и дальше");
  await modal.getByRole("button", { name: "Отмена" }).click();
  await expect(modal).toHaveCount(0);
  await expect(page.locator("article[data-path]")).toHaveCount(0);

  // «Перейти» открывает вопросы; после перезагрузки они остаются открытыми.
  await gate.click();
  await modal.getByRole("button", { name: "Перейти", exact: true }).click();
  await expect(page.locator("article[data-path]").first()).toBeVisible();
  await expect(gate).toHaveCount(0);
  await page.reload();
  await expect(page.locator("article[data-path]").first()).toBeVisible();
  await expect(gate).toHaveCount(0);
  expect(await page.evaluate(() => Object.values(localStorage).map((v) => JSON.parse(v).questionsOpen).find(Boolean))).toEqual([1]);
});

test("старый прогресс без questionsOpen: вопросы начатого этапа открыты", async ({ page }) => {
  await startGame(page);
  await page.evaluate(() => {
    for (const k of Object.keys(localStorage)) {
      const st = JSON.parse(localStorage.getItem(k)!);
      if (st && st.v === 1 && st.stage) {
        delete st.questionsOpen;
        localStorage.setItem(k, JSON.stringify(st));
      }
    }
  });
  await page.reload();
  await expect(page.locator("article[data-path]").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Перейти к вопросам", exact: true })).toHaveCount(0);
});
