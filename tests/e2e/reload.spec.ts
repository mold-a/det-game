// docs/06 §5 «Перезагрузка посреди этапа 3 → прогресс на месте».
import { test, expect } from "@playwright/test";
import { loadAnswers, playToStage, solve, fillQuestion, submit, article, headerScore, labAll } from "./helpers";

const A = loadAnswers();
test.setTimeout(180_000);

test("перезагрузка посреди этапа 3", async ({ page }) => {
  const done = await playToStage(page, A, 3);
  await labAll(page, A, 3, done);
  const st = A.stages.find((s) => s.n === 3)!;
  const mand = st.questions.filter((q) => q.kind === "mandatory");
  const bonus = st.questions.find((q) => q.kind === "bonus")!;

  await solve(page, mand[0]);
  await solve(page, bonus);
  const wrongQ = mand[1];
  await fillQuestion(page, wrongQ, wrongQ.type === "form" ? Object.fromEntries(wrongQ.fields!.map((f) => [f.id, f.wrong[0]])) : wrongQ.wrong[0]);
  await submit(page, wrongQ.path);
  await expect(article(page, wrongQ.path).locator(".q__meta")).toHaveText("Неверных попыток: 1");
  await article(page, wrongQ.path).getByRole("button", { name: /Подсказка/ }).click();
  await page.locator(".modal [data-action=ok]").click();
  await expect(article(page, wrongQ.path).locator(".hints__item")).toHaveCount(1);
  const score = await headerScore(page);

  await page.reload();
  await expect(page.locator("#stage-title")).toHaveText("Этап 3");
  await expect(page.locator(".modal")).toHaveCount(0);
  expect(await headerScore(page)).toBe(score);
  await expect(article(page, mand[0].path)).toHaveClass(/q--solved/);
  await expect(article(page, mand[0].path).locator(".stamp")).toBeVisible();
  await expect(article(page, bonus.path)).toHaveClass(/q--solved/);
  await expect(article(page, wrongQ.path).locator(".q__meta")).toHaveText("Неверных попыток: 1");
  await expect(article(page, wrongQ.path).locator(".hints__item")).toHaveCount(1);
  await expect(page.locator("details.passed")).toHaveCount(2);
  for (const d of A.lab.filter((l) => l.stage <= 3 && l.doc)) await expect(page.locator(".docs-panel")).toContainText(d.doc!);

  // Повтор того же неверного ответа после перезагрузки — без штрафа.
  await fillQuestion(page, wrongQ, wrongQ.type === "form" ? Object.fromEntries(wrongQ.fields!.map((f) => [f.id, f.wrong[0]])) : wrongQ.wrong[0]);
  await submit(page, wrongQ.path);
  await expect(article(page, wrongQ.path).locator(".q__msg")).toHaveText("Этот ответ уже проверяли.");
  expect(await headerScore(page)).toBe(score);
});
