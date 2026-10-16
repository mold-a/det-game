// QA: мелочи UX, найденные при проверке.
import { test, expect } from "@playwright/test";
import { startGame, article, scoreLog } from "../e2e/helpers";

test("после неверного ответа расстановка order и поля формы не сбрасываются", async ({ page }) => {
  await startGame(page);
  const ids = () => article(page, "s1.q2").locator(".order__item").evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.id).join(","));
  await page.evaluate(() => {
    const l = document.querySelector('article[data-path="s1.q2"] ol.order')!;
    l.appendChild(l.firstElementChild!);
  });
  const arranged = await ids();
  await article(page, "s1.q2").locator('button[type="submit"]').click();
  await expect(article(page, "s1.q2").locator(".q__msg")).toContainText("не подтверждается", { timeout: 30_000 });
  expect(await ids()).toBe(arranged);
});

test("журнал баллов на /lab/ и /final/ подписан так же, как на главном («вопрос 1.2», а не s1.q2)", async ({ page }) => {
  await startGame(page);
  await article(page, "s1.q2").locator('button[type="submit"]').click();
  await expect(article(page, "s1.q2").locator(".q__msg")).toContainText("не подтверждается", { timeout: 30_000 });
  const main = (await scoreLog(page)).map((r) => r.reason);
  for (const u of ["/lab/", "/final/"]) {
    await page.goto(u);
    expect((await scoreLog(page)).map((r) => r.reason), u).toEqual(main);
  }
});
