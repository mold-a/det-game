// QA: частично верная форма / persons не выдают, какое поле верно — ни текстом,
// ни классами/aria, ни заметной разницей во времени (docs/01 §3 form).
import { test, expect, type Page } from "@playwright/test";
import { loadAnswers, startGame, playToStage, article, fillQuestion, submit, reachQuestion } from "../e2e/helpers";
import { waitIdle } from "./qa_util";

const A = loadAnswers();
test.setTimeout(300_000);
const q1 = A.stages[0].questions.find((q) => q.path === "s1.q1")!;
const q22 = A.stages[1].questions.find((q) => q.path === "s2.q2")!;

/** Снимок участка без изменчивых частей (uid, счётчик попыток). */
async function snapshot(page: Page, path: string) {
  return article(page, path).evaluate((el) => {
    const c = el.cloneNode(true) as HTMLElement;
    // счётчик попыток, подсказки и кнопка подсказки зависят от номера попытки, не от полей
    c.querySelectorAll(".q__meta, .hints, .q__actions .btn--secondary").forEach((n) => n.remove());
    c.querySelectorAll(".q__msg").forEach((n) => (n.textContent = (n.textContent || "").replace(" Открыта подсказка 1 уровня — бесплатно.", "")));
    let html = c.outerHTML;
    html = html.replace(/\b(in|sel|f-label|q-prompt|dg)-\d+\b/g, "$1-N");
    return html;
  });
}

async function timedSubmit(page: Page, path: string) {
  const t0 = Date.now();
  await submit(page, path);
  await waitIdle(page, path);
  await expect(article(page, path).locator(".q__msg").first()).not.toHaveText("", { timeout: 30_000 });
  return Date.now() - t0;
}

const median = (xs: number[]) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];

test("форма: 3 из 4 верных полей и 0 из 4 неразличимы в DOM и по времени", async ({ page }) => {
  await startGame(page);
  const right: Record<string, any> = Object.fromEntries(q1.fields!.map((f) => [f.id, f.input]));
  const allWrong = (i: number) => ({ time: `20:1${i}`, conflict: "stas", disease: `грипп${i}`, delivered: "stas" });
  const partial = (i: number) => ({ ...right, time: `21:3${i}` }); // только время неверно

  const tPartial: number[] = [];
  const tWrong: number[] = [];
  let snapP = "";
  let snapW = "";
  for (let i = 0; i < 5; i++) {
    await fillQuestion(page, q1, partial(i));
    tPartial.push(await timedSubmit(page, q1.path));
    snapP = await snapshot(page, q1.path);
    await fillQuestion(page, q1, allWrong(i));
    tWrong.push(await timedSubmit(page, q1.path));
    snapW = await snapshot(page, q1.path);
    expect(snapP).toBe(snapW);
  }
  // aria-invalid нигде не выставлен в «true» после валидной неверной попытки
  await expect(article(page, q1.path).locator('[aria-invalid="true"]')).toHaveCount(0);
  console.log("form timings partial", tPartial, "wrong", tWrong);
  const diff = Math.abs(median(tPartial) - median(tWrong));
  expect(diff).toBeLessThan(Math.max(60, 0.25 * median(tWrong)));
});

test("persons: частично верный набор и полностью неверный неразличимы", async ({ page }) => {
  await playToStage(page, A, 2);
  await reachQuestion(page, A, q22.path);
  const right = q22.input as string[];
  const all = await article(page, q22.path).locator("input[type=checkbox]").evaluateAll((els) => els.map((e) => (e as HTMLInputElement).value));
  const wrongOnly = all.filter((x) => !right.includes(x)).slice(0, 1);
  await fillQuestion(page, q22, right.slice(0, right.length - 1));
  await submit(page, q22.path);
  await waitIdle(page, q22.path);
  const a = await snapshot(page, q22.path);
  await fillQuestion(page, q22, wrongOnly);
  await submit(page, q22.path);
  await waitIdle(page, q22.path);
  const b = await snapshot(page, q22.path);
  expect(a).toBe(b);
});
