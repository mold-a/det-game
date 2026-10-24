// QA: две вкладки одной партии (docs/02 §4, FORMATS §7.2). Гонки воспроизводятся не каждый раз
// (запись localStorage доходит до другой вкладки асинхронно), поэтому каждый сценарий
// повторяется до RUNS раз; тест падает на первом воспроизведении.
import { test, expect, type Page, type BrowserContext } from "@playwright/test";
import { loadAnswers, startGame, headerScore, article, objectText, reachQuestion } from "../e2e/helpers";
import { readState, sumLog } from "./qa_util";

const A = loadAnswers();
const PEN = Math.abs(A.settings.penalties.wrongAttempt);
const RUNS = Number(process.env.QA_RACE_RUNS || 15);
const P = "s1.q2";
const b1 = A.stages[0].questions.find((q) => q.path === "s1.b1")!;
test.setTimeout(400_000);

/** «Ниже» у исходно первой карточки moves раз (без rAF — вкладка может быть фоновой). */
const prep = (p: Page, moves: number) =>
  p.evaluate(([path, m]) => {
    const d = document.querySelector(`article[data-path="${path}"]`)!.querySelectorAll(".order__item .order__move")[1] as HTMLButtonElement;
    for (let i = 0; i < (m as number); i++) d.click();
  }, [P, moves] as const);
const click = (p: Page, path = P) =>
  p.evaluate((path) => (document.querySelector(`article[data-path="${path}"] button[type=submit]`) as HTMLButtonElement).click(), path);

/** Две вкладки на вопросе path (вопросы этапа открываются по одному: предыдущие решаются в первой вкладке). */
async function twoTabs(page: Page, context: BrowserContext, path = P) {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await startGame(page);
  await reachQuestion(page, A, path);
  const p2 = await context.newPage();
  await p2.goto("/");
  await expect(p2.locator("#stage-title")).toHaveText("Этап 1");
  await expect(article(p2, path)).toBeVisible();
  return p2;
}

test("одновременные РАЗНЫЕ неверные ответы: оба штрафа в хранилище и после перезагрузки", async ({ page, context }) => {
  for (let run = 0; run < RUNS; run++) {
    const p2 = await twoTabs(page, context);
    await prep(page, 0);
    await prep(p2, 1);
    await Promise.all([click(page), click(p2)]);
    await page.waitForTimeout(2000);
    const stored = sumLog(await readState(page));
    const hA = await headerScore(page);
    const hB = await headerScore(p2);
    await p2.close();
    await page.reload();
    const after = await headerScore(page);
    expect({ run, stored, hA, hB, after }).toEqual({ run, stored: -2 * PEN, hA: -2 * PEN, hB: -2 * PEN, after: -2 * PEN });
  }
});

test("одновременный ОДИНАКОВЫЙ неверный ответ: один штраф и после следующего действия", async ({ page, context }) => {
  for (let run = 0; run < RUNS; run++) {
    const p2 = await twoTabs(page, context);
    await Promise.all([click(page), click(p2)]);
    await page.waitForTimeout(2000);
    // следующее действие в каждой вкладке (свой новый неверный порядок) записывает слитое состояние
    await prep(page, 2);
    await click(page);
    await page.waitForTimeout(1500);
    await prep(p2, 3);
    await click(p2);
    await page.waitForTimeout(1500);
    const s = await readState(page);
    await p2.close();
    // 3 разных неверных ответа = 3 хеша = 3 штрафа
    expect({ run, hashes: s.wrong[P].length, log: s.log.length, sum: sumLog(s) }).toEqual({ run, hashes: 3, log: 3, sum: -3 * PEN });
  }
});

test("бонус в двух вкладках одновременно: сообщение не противоречит счёту", async ({ page, context }) => {
  const setAndClick = (p: Page, v: string) =>
    p.evaluate(([v]) => {
      const a = document.querySelector('article[data-path="s1.b1"]')!;
      (a.querySelector("input.input") as HTMLInputElement).value = v;
      (a.querySelector("button[type=submit]") as HTMLButtonElement).click();
    }, [v]);
  for (let run = 0; run < RUNS; run++) {
    const p2 = await twoTabs(page, context, b1.path);
    await Promise.all([setAndClick(page, String(b1.wrong[0])), setAndClick(p2, String(b1.input))]);
    await page.waitForTimeout(2000);
    const s = await readState(page);
    const credited = sumLog(s) === A.settings.points.bonus;
    for (const p of [page, p2]) {
      const msg = await p.evaluate((path) => document.querySelector(`article[data-path="${path}"] .q__msg`)?.textContent ?? "", b1.path);
      if (msg.includes("Ответ принят")) expect({ run, msg, credited }).toEqual({ run, msg, credited: true });
      if (msg.includes("Бонусный вопрос закрыт")) expect({ run, msg, credited }).toEqual({ run, msg, credited: false });
    }
    await p2.close();
  }
});

test("ввод в «/» не теряется, когда другая вкладка (лаборатория) пишет прогресс", async ({ page, context }) => {
  await startGame(page);
  const a = article(page, "s1.q1");
  await a.locator(".q__body .field").nth(0).locator("input").fill("21:00");
  const lab = await context.newPage();
  await lab.goto("/lab/");
  const water = A.lab.find((x) => x.object === "water")!;
  await lab.locator("#lab-object").fill(objectText(water));
  await lab.locator("#lab-type").selectOption("chem");
  await lab.locator("#lab-basis").selectOption("1-01");
  await lab.getByRole("button", { name: "Направить заявку" }).click();
  await expect(lab.locator(".lab-form .lab-msg")).not.toHaveText("", { timeout: 15_000 });
  await page.waitForTimeout(1500);
  await expect(a.locator(".q__body .field").nth(0).locator("input")).toHaveValue("21:00");
});
