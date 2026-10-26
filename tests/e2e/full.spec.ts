// P05: полное прохождение без ошибок — лаборатория (все результаты, повтор без
// штрафа, пустая экспертиза, предмет не из описи), этапы 1 → 4, финал (ответы без оценки, счёт не
// меняется до конца), итоги с рангом и разбором, развязка.
// Итог: expected.perfectRunScore минус один штраф за пустую экспертизу.
import { test, expect, type Page } from "@playwright/test";
import { loadAnswers, startGame, finishStage, fillQuestion, submit, article, labRequest, headerScore, objectText } from "./helpers";

const A = loadAnswers();
const S = A.settings;

test.setTimeout(240_000);

async function labStage(page: Page, n: number, done: Set<string>) {
  await page.goto("/lab/");
  await expect(page.locator(".lab-form")).toBeVisible();
  for (const e of A.lab.filter((x) => x.stage <= n && !done.has(x.result))) {
    const msg = await labRequest(page, e);
    expect(msg, e.result).toMatch(/^Заключение готово/);
    if (e.doc) {
      expect(msg).toContain(e.doc);
      await expect(page.locator("#lab-basis option", { hasText: e.doc })).toHaveCount(1);
    }
    done.add(e.result);
  }
  await page.goto("/");
}

test("полная игра: этапы, лаборатория, финал, итоги, развязка", async ({ page }) => {
  await startGame(page);
  const done = new Set<string>();

  // Лаборатория на этапе 1: пустая экспертиза → штраф; повтор — без штрафа.
  await page.goto("/lab/");
  const first = A.lab.find((x) => x.stage === 1)!;
  expect(await labRequest(page, first, first.wrongBasis)).toMatch(/^Экспертиза ничего не выявила/);
  expect(await headerScore(page)).toBe(S.penalties.labNoBasis);
  expect(await labRequest(page, first, first.wrongBasis)).toMatch(/^Такая заявка уже выполнялась/);
  expect(await headerScore(page)).toBe(S.penalties.labNoBasis);
  // Предмет, который появляется в материалах позже (objectFromStage > 1), пока «не в описи»: без штрафа.
  const late = A.lab.find((x) => ((x as any).objectFromStage ?? x.stage) > 1)!;
  expect(await labRequest(page, late, first.bases[0])).toMatch(/^Сейчас этот предмет нельзя передать/);
  expect(await headerScore(page)).toBe(S.penalties.labNoBasis);

  for (const stage of A.stages.slice(0, -1)) {
    await labStage(page, stage.n, done);
    await expect(page.locator("#stage-title")).toHaveText(`Этап ${stage.n}`);
    await finishStage(page, stage);
  }

  const lastStage = A.stages[A.stages.length - 1];
  await labStage(page, lastStage.n, done);
  const before = await headerScore(page);

  // Финал
  await page.getByRole("link", { name: "Перейти к финалу" }).click();
  await expect(page.locator(".final-warn")).toContainText("нельзя изменить");
  await page.getByRole("button", { name: "Начать финал" }).click();
  const byPath = Object.fromEntries(lastStage.questions.map((q) => [q.path, q]));
  for (const path of A.finalOrder) {
    const q = byPath[path];
    await expect(article(page, path)).toBeVisible();
    await fillQuestion(page, q);
    await submit(page, path);
    expect(await headerScore(page)).toBe(before); // счёт не выдаёт правильность
  }

  // Итоги
  await expect(page.locator("#final-title")).toHaveText("Итоги", { timeout: 60_000 });
  const expected = A.expected.perfectRunScore + S.penalties.labNoBasis;
  expect(await headerScore(page)).toBe(expected);
  await expect(page.locator(".final-score__value")).toHaveText(`+${expected}`);
  await expect(page.locator(".final-score .stamp")).toBeVisible();
  await expect(page.locator(".review tbody tr.is-wrong")).toHaveCount(0);

  // Развязка: признание → второй протокол (если есть) → письмо → судьбы → «Вернуться к делу»
  await page.getByRole("button", { name: "Перейти к развязке" }).click();
  await expect(page.locator("#final-title")).toHaveText(/Признание/);
  if (A.endingSteps.includes("confession2")) {
    await page.getByRole("button", { name: "Дальше" }).click();
    await expect(page.locator("#final-title")).toHaveText(/Второй допрос/);
  }
  await page.getByRole("button", { name: "Дальше" }).click();
  await expect(page.locator("#final-title")).toHaveText(/Письмо/);
  await page.getByRole("button", { name: "Дальше" }).click();
  await expect(page.locator(".fates__item").first()).toBeVisible();
  if (A.endingSteps.includes("thanks")) await page.getByRole("button", { name: "Дальше" }).click(); // «Спасибо за игру» — последний шаг
  await page.getByRole("link", { name: "Вернуться к делу" }).click();
  await expect(page.locator(".notice")).toContainText("Игра завершена");

  // Перезагрузка финала: итоги снова (finale.json скачивается заново, F9).
  await page.goto("/final/");
  await expect(page.locator("#final-title")).toHaveText("Итоги", { timeout: 30_000 });
});
