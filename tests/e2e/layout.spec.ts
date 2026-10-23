// docs/06 §5 «Вёрстка»: скриншоты всех страниц системы расследования на 360, 768,
// 1280 px (и тёмная тема) и проверка отсутствия горизонтальной прокрутки.
// Скриншоты — в test-results/ (вложения отчёта). Вымышленные страницы — pages.spec (P06).
import { test, expect, type Page } from "@playwright/test";
import { loadAnswers, startGame, reachQuestion, playToStage, labAll, fillQuestion, submit, article, openConclusion } from "./helpers";

const A = loadAnswers();
test.setTimeout(240_000);

const WIDTHS = [
  { name: "360", width: 360, height: 780 },
  { name: "768", width: 768, height: 1024 },
  { name: "1280", width: 1280, height: 900 },
  { name: "768-dark", width: 768, height: 1024, dark: true },
];

async function check(page: Page, name: string) {
  await page.evaluate(() => document.fonts.ready);
  const { sw, cw, wide } = await page.evaluate(() => ({
    sw: document.documentElement.scrollWidth,
    cw: document.documentElement.clientWidth,
    wide: [...document.querySelectorAll("body *")]
      .filter((el) => el.getBoundingClientRect().right > document.documentElement.clientWidth + 1 && !el.closest(".review-wrap, .visually-hidden"))
      .slice(0, 3)
      .map((el) => `${el.tagName}.${(el as HTMLElement).className}`),
  }));
  await page.screenshot({ path: test.info().outputPath(`${name}.png`), fullPage: true });
  expect(sw, `${name}: горизонтальная прокрутка (${wide.join(", ")})`).toBeLessThanOrEqual(cw);
}

for (const w of WIDTHS) {
  test(`вёрстка ${w.name}`, async ({ page }) => {
    await page.setViewportSize({ width: w.width, height: w.height });
    if (w.dark) await page.emulateMedia({ colorScheme: "dark" });
    await page.emulateMedia({ reducedMotion: "reduce" });

    await page.goto("/");
    await check(page, "01-intro");
    await page.goto("/final/");
    await check(page, "02-final-not-started");

    // Этап 1 с ошибкой и подсказкой, окно подсказки, меню.
    await startGame(page);
    const order = A.stages[0].questions.find((q) => q.type === "order")!;
    await reachQuestion(page, A, order.path);
    await fillQuestion(page, order, order.wrong[0]);
    await submit(page, order.path);
    await expect(article(page, order.path).locator(".q__msg")).toBeVisible();
    await check(page, "03-stage1");
    await article(page, order.path).getByRole("button", { name: /Подсказка/ }).click();
    await check(page, "04-hint-confirm");
    await page.keyboard.press("Escape");
    await page.locator(".menu__toggle").click();
    await check(page, "05-menu");
    await page.keyboard.press("Escape");
    await page.goto("/final/");
    await check(page, "06-final-locked");
    await page.goto("/lab/");
    await check(page, "07-lab-empty");

    // Этап 4, лаборатория со всеми результатами, документ, финал, итоги, развязка.
    await page.evaluate(() => localStorage.clear());
    const last = A.stages[A.stages.length - 1];
    const done = await playToStage(page, A, last.n);
    await check(page, "08-stage-last");
    await labAll(page, A, last.n, done);
    await page.goto("/lab/#orders");
    await check(page, "09-lab-orders");
    for (const tab of ["services", "about", "contacts"]) {
      await page.goto(`/lab/#${tab}`);
      await check(page, `09-lab-${tab}`);
    }
    await openConclusion(page);
    await check(page, "10-doc-modal");
    await page.keyboard.press("Escape");
    await page.goto("/");
    await page.locator("details.passed").first().locator("summary").click();
    await check(page, "11-passed-open");

    await page.goto("/final/");
    await check(page, "12-final-warning");
    await page.getByRole("button", { name: "Начать финал" }).click();
    const byPath = Object.fromEntries(last.questions.map((q) => [q.path, q]));
    for (const [i, path] of A.finalOrder.entries()) {
      if (i === 0) await check(page, "13-final-question");
      await fillQuestion(page, byPath[path]);
      await submit(page, path);
    }
    await expect(page.locator("#final-title")).toHaveText("Итоги", { timeout: 60_000 });
    await check(page, "14-results");
    await page.getByRole("button", { name: "Перейти к развязке" }).click();
    await check(page, "15-ending-1");
    await page.getByRole("button", { name: "Дальше" }).click();
    await check(page, "16-ending-2");
    await page.getByRole("button", { name: "Дальше" }).click();
    await check(page, "17-ending-3");
    await page.goto("/");
    await check(page, "18-main-finished");
  });
}
