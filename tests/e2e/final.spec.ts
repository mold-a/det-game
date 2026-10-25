// docs/06 §5 «Финал»: после ответа вернуться нельзя; счёт до конца не меняется;
// неверный ответ — без баллов и с пометкой в разборе; развязка показывается.
import { test, expect } from "@playwright/test";
import { loadAnswers, playToStage, labAll, fillQuestion, submit, article, headerScore } from "./helpers";

const A = loadAnswers();
const S = A.settings;
test.setTimeout(240_000);

test("финал: ответ фиксируется, перезагрузка не возвращает вопрос, разбор и развязка", async ({ page }) => {
  const last = A.stages[A.stages.length - 1];
  const done = await playToStage(page, A, last.n);
  await labAll(page, A, last.n, done);
  const before = await headerScore(page);

  await page.goto("/final/");
  await page.getByRole("button", { name: "Начать финал" }).click();
  const byPath = Object.fromEntries(last.questions.map((q) => [q.path, q]));
  const [first, second, ...rest] = A.finalOrder;

  // Первый ответ — неверный.
  const q1 = byPath[first];
  await fillQuestion(page, q1, q1.type === "form" ? Object.fromEntries(q1.fields!.map((f) => [f.id, f.wrong[0]])) : q1.wrong[0]);
  await submit(page, first);
  await expect(article(page, second)).toBeVisible();
  await expect(page.locator(".final-fixed")).toHaveText("Ответ зафиксирован.");
  expect(await headerScore(page)).toBe(before);

  // «Назад» и перезагрузка не возвращают первый вопрос.
  await page.goBack();
  await page.goto("/final/");
  await expect(article(page, second)).toBeVisible();
  await expect(article(page, first)).toHaveCount(0);
  await page.reload();
  await expect(article(page, second)).toBeVisible();

  for (const path of [second, ...rest]) {
    await fillQuestion(page, byPath[path]);
    await submit(page, path);
    if (path !== rest[rest.length - 1]) expect(await headerScore(page)).toBe(before);
  }

  await expect(page.locator("#final-title")).toHaveText("Итоги", { timeout: 60_000 });
  const pts = (p: string) => (byPath[p].kind === "bonus" ? S.points.bonus : S.points.final);
  const expected = before + [second, ...rest].reduce((s, p) => s + pts(p), 0);
  expect(await headerScore(page)).toBe(expected);
  await expect(page.locator(".review tbody tr.is-wrong")).toHaveCount(q1.type === "form" ? q1.fields!.length : 1);

  // Развязка: три части по порядку.
  await page.getByRole("button", { name: "Перейти к развязке" }).click();
  await expect(page.locator("#final-title")).toHaveText(/Признание/);
  await expect(page.locator(".ending .blank")).toBeVisible();
  await page.getByRole("button", { name: "Дальше" }).click();
  await expect(page.locator("#final-title")).toHaveText(/Письмо/);
  await page.getByRole("button", { name: "Дальше" }).click();
  await expect(page.locator("#final-title")).toHaveText(/Судьбы/);
  await expect(page.locator(".fates__item").first()).toBeVisible();

  // «Спасибо за игру» (finale.thanks): есть шаг — после судеб; нет поля — судьбы последние.
  if (A.thanks) {
    await page.getByRole("button", { name: "Дальше" }).click();
    await expect(page.locator("#final-title")).toHaveText(A.thanks.title);
    for (const para of A.thanks.text.split(/\n{2,}/).filter(Boolean)) await expect(page.locator(".thanks__text")).toContainText(para.trim());
    await expect(page.locator(".thanks__signature")).toHaveText(A.thanks.signature);
    await expect(page.locator(".thanks__score .final-score__value")).toHaveText(new RegExp(`^[+−-]?${expected < 0 ? -expected : expected}$`));
    await expect(page.locator(".thanks__score .stamp")).toBeVisible();
    // 360 px: без горизонтальной прокрутки
    await page.setViewportSize({ width: 360, height: 740 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    // «Начать заново»: отмена не стирает прогресс
    await page.getByRole("button", { name: "Начать заново" }).click();
    await page.locator(".modal [data-action=cancel]").click();
    await expect(page.locator(".thanks__text")).toBeVisible();
  } else {
    await expect(page.getByRole("button", { name: "Дальше" })).toHaveCount(0);
  }

  // Главный экран после игры: вопросов этапа 4 нет, ссылка на итоги.
  await page.getByRole("link", { name: "Вернуться к делу" }).click();
  await expect(page.locator(".notice")).toContainText("Игра завершена");

  // Заново из «Спасибо за игру»: два подтверждения, прогресс стёрт, старт.
  if (A.thanks) {
    await page.goto("/final/");
    await page.getByRole("button", { name: "Перейти к развязке" }).click();
    for (let k = 0; k < 3; k++) await page.getByRole("button", { name: "Дальше" }).click();
    await expect(page.locator("#final-title")).toHaveText(A.thanks.title);
    await page.getByRole("button", { name: "Начать заново" }).click();
    await page.locator(".modal [data-action=ok]").click();
    await page.locator(".modal [data-action=ok]").click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator("#team")).toBeVisible();
  }
});

test("финал закрыт до последнего этапа", async ({ page }) => {
  await page.goto("/");
  await page.locator("#team").fill("Тест");
  await page.getByRole("button", { name: "Открыть дело" }).click();
  await page.locator(".modal [data-action=ok]").click();
  await page.goto("/final/");
  await expect(page.getByText(/Финал откроется после этапа/)).toBeVisible();
});
