// docs/06 §5 «Лаборатория»: запрос без основания −5; повтор без штрафа; запрос с
// основанием → документ в «Документах дела» и в выборе вопроса типа document.
import { test, expect } from "@playwright/test";
import { loadAnswers, startGame, playToStage, labRequest, headerScore, article } from "./helpers";

const A = loadAnswers();
const S = A.settings;
test.setTimeout(180_000);

test("без основания −5, повтор без штрафа, объект следующего этапа недоступен", async ({ page }) => {
  await startGame(page);
  await page.goto("/lab/");
  const e = A.lab.find((x) => x.stage === 1)!;
  expect(await labRequest(page, e, e.wrongBasis)).toMatch(/^Недостаточно оснований/);
  expect(await headerScore(page)).toBe(S.penalties.labNoBasis);
  expect(await labRequest(page, e, e.wrongBasis)).toMatch(/уже рассматривали/);
  expect(await headerScore(page)).toBe(S.penalties.labNoBasis);
  await expect(page.locator(".lab-archive__item.is-rejected")).toHaveCount(1);

  // Верный запрос того же этапа — без штрафа, в архиве «выполнен».
  expect(await labRequest(page, e)).toMatch(/Экспертиза выполнена/);
  expect(await headerScore(page)).toBe(S.penalties.labNoBasis);
  await expect(page.locator(".lab-archive__item.is-done")).toHaveCount(1);

  const objects = await page.locator(".lab-form__grid select").first().locator("option").evaluateAll((o) => o.map((x) => (x as HTMLOptionElement).value));
  for (const later of A.lab.filter((x) => x.stage > 1)) {
    if (!A.lab.some((x) => x.stage === 1 && x.object === later.object)) expect(objects).not.toContain(later.object);
  }
});

test("документ экспертизы — в панели и в выборе типа document", async ({ page }) => {
  // Найти вопрос (или поле формы) типа document и экспертизу, которая даёт его ответ.
  let target: { stage: number; qpath: string; field?: string; doc: string } | null = null;
  for (const st of A.stages) {
    for (const q of st.questions) {
      const units = q.type === "form" ? q.fields!.map((f) => ({ f, u: f })) : [{ f: undefined, u: q }];
      for (const { f, u } of units) {
        if (u.type === "document" && A.lab.some((l) => l.doc === u.input)) target = { stage: st.n, qpath: q.path, field: f?.id, doc: u.input };
      }
    }
  }
  test.skip(!target, "в контенте нет вопроса типа document с ответом-экспертизой");
  const lab = A.lab.find((l) => l.doc === target!.doc)!;
  const done = await playToStage(page, A, target!.stage);

  const select = article(page, target!.qpath).locator("select");
  const before = await select.first().locator("option").evaluateAll((o) => o.map((x) => (x as HTMLOptionElement).value));
  expect(before).not.toContain(target!.doc);

  await page.goto("/lab/");
  expect(await labRequest(page, lab)).toMatch(new RegExp(`Документ ${target!.doc} добавлен`));
  await expect(page.locator(".docs")).toContainText(target!.doc);
  await page.goto("/");
  await expect(page.locator(".docs-panel")).toContainText(target!.doc);
  const after = await article(page, target!.qpath).locator("select").first().locator("option").evaluateAll((o) => o.map((x) => (x as HTMLOptionElement).value));
  expect(after).toContain(target!.doc);

  // Документ открывается из панели в окне.
  await page.locator(".docs-panel button.docs__link", { hasText: target!.doc }).click();
  await expect(page.locator(".modal .blank")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".modal")).toHaveCount(0);
  done.add(lab.result);
});
