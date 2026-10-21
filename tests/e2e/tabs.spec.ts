// docs/02 §4: «/» и «/lab/» в разных вкладках — изменения подхватываются (событие storage).
import { test, expect } from "@playwright/test";
import { loadAnswers, startGame, labRequest, headerScore } from "./helpers";

const A = loadAnswers();

test("две вкладки: запрос в лаборатории виден на главном экране без перезагрузки", async ({ page, context }) => {
  await startGame(page);
  const lab = await context.newPage();
  await lab.goto("/lab/");
  const e = A.lab.find((x) => x.stage === 1)!;

  expect(await labRequest(lab, e, e.wrongBasis)).toMatch(/^Экспертиза ничего не выявила/);
  await expect.poll(() => headerScore(page)).toBe(A.settings.penalties.labNoBasis);
  // Карточка лаборатории на главном экране — тоже по событию storage.
  await expect(page.locator(".labcard__stats")).toContainText("1");

  // И обратно: штраф на главном экране → вкладка лаборатории обновила счёт.
  const q = A.stages[0].questions.find((x) => x.type === "order")!;
  // Фоновая вкладка не рисует кадры (rAF): действия Playwright ждут видимую вкладку.
  await page.bringToFront();
  const { fillQuestion, submit } = await import("./helpers");
  await fillQuestion(page, q, q.wrong[0]);
  await submit(page, q.path);
  await expect.poll(() => headerScore(lab)).toBe(A.settings.penalties.labNoBasis + A.settings.penalties.wrongAttempt);

  let expected = A.settings.penalties.labNoBasis + A.settings.penalties.wrongAttempt;

  // Незаконченная заявка во вкладке лаборатории пережила перерисовку по storage.
  if (q.wrong[1] !== undefined) {
    await lab.bringToFront();
    await lab.locator("#lab-object").fill("черновик заявки");
    await page.bringToFront();
    await fillQuestion(page, q, q.wrong[1]);
    await submit(page, q.path);
    expected += A.settings.penalties.wrongAttempt;
    await expect.poll(() => headerScore(lab)).toBe(expected);
    await lab.bringToFront();
    await expect(lab.locator("#lab-object")).toHaveValue("черновик заявки");
  }

  // Все записи в журнале — ни одна вкладка не затёрла другую.
  await lab.bringToFront();
  await lab.reload();
  expect(await headerScore(lab)).toBe(expected);
});
