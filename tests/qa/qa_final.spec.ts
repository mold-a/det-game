// QA: финал — одна попытка, счёт в шапке не меняется, баллы после последнего ответа,
// ранги по порогам public.json, итог = сумма журнала (docs/01 §6, §8).
import { test, expect } from "@playwright/test";
import { loadAnswers, playToStage, fillQuestion, submit, article, headerScore } from "../e2e/helpers";
import { readState, writeState, sumLog, collectErrors } from "./qa_util";

const A = loadAnswers();
test.setTimeout(300_000);

test("финал: фиксация без оценки, счёт неизменен до конца, баллы и ранг после последнего ответа", async ({ page }) => {
  const errors = collectErrors(page);
  await playToStage(page, A, 4);
  const before = await headerScore(page);
  const bonusCount = A.stages.filter((s) => s.n < 4).flatMap((s) => s.questions).filter((q) => q.kind === "bonus").length;
  expect(before).toBe(bonusCount * A.settings.points.bonus);

  await page.goto("/final/");
  await expect(page.locator(".final-warn")).toHaveText("Ответы финала нельзя изменить. Убедитесь, что изучили все материалы.");
  await page.getByRole("button", { name: "Начать финал" }).click();

  const last = A.stages[3];
  const byPath = Object.fromEntries(last.questions.map((q) => [q.path, q]));
  // верно: f1, f3, f5, fb; неверно: f2, f4, fb2
  const wrongSet = new Set(["s4.f2", "s4.f4", "s4.fb2"]);
  const logLen0 = (await readState(page)).log.length;
  for (const [i, path] of A.finalOrder.entries()) {
    const q = byPath[path];
    await expect(article(page, path)).toBeVisible({ timeout: 30_000 });
    await expect(page.locator(".q__no")).toHaveText(`Вопрос ${i + 1} из ${A.finalOrder.length}`);
    await fillQuestion(page, q, wrongSet.has(path) ? q.wrong[0] : undefined);
    await submit(page, path);
    if (i < A.finalOrder.length - 1) {
      await expect(article(page, A.finalOrder[i + 1])).toBeVisible({ timeout: 30_000 });
      await expect(page.locator(".final-fixed")).toHaveText("Ответ зафиксирован.");
      expect(await headerScore(page)).toBe(before);
      const s = await readState(page);
      expect(s.log.length).toBe(logLen0);
      expect(s.final.correct).toBeNull();
      // в DOM нет оценки
      await expect(page.locator("main")).not.toContainText(/неверно|верно|Принято/);
      // одна попытка: повторный ответ на зафиксированный вопрос в state невозможен
      await page.reload();
      await expect(article(page, path)).toHaveCount(0);
    }
  }
  await expect(page.locator(".final-score")).toBeVisible({ timeout: 60_000 });
  const expected = before + 3 * A.settings.points.final + A.settings.points.bonus;
  const s = await readState(page);
  expect(sumLog(s)).toBe(expected);
  expect(s.log.filter((e: any) => e.r.startsWith("final:")).map((e: any) => e.r).sort()).toEqual(["final:s4.f1", "final:s4.f3", "final:s4.f5"]);
  expect(s.log.filter((e: any) => e.r.startsWith("bonus:s4")).map((e: any) => e.r)).toEqual(["bonus:s4.fb"]);
  expect(await headerScore(page)).toBe(expected);
  await expect(page.locator(".final-score__value")).toHaveText(`+${expected}`);
  await expect(page.locator(".final-score .stamp")).toHaveAttribute("aria-label", "Следователь");
  // разбор: неверные ответы помечены
  await expect(page.locator("table.review tr.is-wrong")).toHaveCount(3);
  // развязка: три части
  await page.getByRole("button", { name: "Перейти к развязке" }).click();
  await expect(page.locator("#final-title")).toContainText("Признание");
  await page.getByRole("button", { name: "Дальше" }).click();
  await expect(page.locator("#final-title")).toContainText("Письмо");
  await page.getByRole("button", { name: "Дальше" }).click();
  await expect(page.locator("#final-title")).toContainText("Судьбы");
  await expect(page.getByRole("link", { name: "Вернуться к делу" })).toBeVisible();

  // Пороги рангов: двигаем журнал служебной записью и смотрим штамп.
  const pub = await page.evaluate(() => fetch("/data/public.json").then((r) => r.json()));
  const cases: [number, string][] = [];
  for (const r of pub.ranks) {
    if (r.min !== null) cases.push([r.min, r.name], [r.min - 1, pub.ranks[pub.ranks.indexOf(r) - 1].name]);
  }
  cases.push([-50, pub.ranks[0].name]);
  for (const [target, name] of cases) {
    const st = await readState(page);
    st.log = st.log.filter((e: any) => e.r !== "qa:adjust");
    const d = target - sumLog(st);
    if (d !== 0) st.log.push({ t: new Date().toISOString(), d, r: "qa:adjust" });
    await writeState(page, st);
    await page.goto("/final/");
    await expect(page.locator(".final-score .stamp")).toHaveAttribute("aria-label", name);
    expect(await headerScore(page)).toBe(target);
  }
  expect(errors).toEqual([]);
});
