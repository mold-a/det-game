// QA на МОДИФИЦИРОВАННОМ контенте (scratchpad/qa2/mod, патч patch_content.py):
//  - во все текстовые поля контента подложено <img src=x onerror=alert(..)><script>alert(..)</script>;
//  - добавлены экспертизы: water/chem/1-09 ещё и на этапе 3 («самый поздний этап»),
//    costume/chem/1-01 на этапе 2 («отклонённый раньше срабатывает после перехода»).
// Запускать из каталога mod (там свой tests/.answers.json) против его сервера.
import { test, expect, type Page } from "@playwright/test";
import {
  loadAnswers, startGame, article, headerScore, fillQuestion, submit, envelopeOpened, labRequest, labAll, solve,
} from "../e2e/helpers";

const A = loadAnswers();
const PEN = Math.abs(A.settings.penalties.labNoBasis);
test.setTimeout(300_000);

function watchXss(page: Page) {
  const fired: string[] = [];
  page.on("dialog", async (d) => {
    fired.push(`${page.url()} :: ${d.message()}`);
    await d.dismiss();
  });
  return fired;
}

async function lab(page: Page, object: string, type: string, basis: string) {
  const e = { result: "", object, types: [type], stage: 0, bases: [basis], params: {}, doc: null, title: "", wrongBasis: "" };
  return labRequest(page, e as any, basis);
}

async function finishStage(page: Page, n: number) {
  const stage = A.stages.find((s) => s.n === n)!;
  const mand = stage.questions.filter((x) => x.kind === "mandatory");
  for (const q of mand.slice(0, -1)) await solve(page, q);
  const last = mand[mand.length - 1];
  await fillQuestion(page, last);
  await submit(page, last.path);
  await envelopeOpened(page);
  await expect(page.locator("#stage-title")).toHaveText(`Этап ${n + 1}`);
}

test("XSS в контенте и имени команды + лаборатория: поздний этап, отклонённый→выполненный", async ({ page }) => {
  const fired = watchXss(page);
  await page.goto("/");
  await page.locator("#team").fill('<img src=x onerror=alert("TEAM")>');
  await page.getByRole("button", { name: "Открыть дело" }).click();
  await envelopeOpened(page);
  await expect(page.locator(".app-header__team")).toContainText('<img src=x onerror=alert("TEAM")>');
  // подсказка уровня 1 (с полезной нагрузкой) — купить
  await article(page, "s1.q1").getByRole("button", { name: /Подсказка/ }).click();
  await page.locator(".modal").getByRole("button", { name: /Открыть подсказку/ }).click();
  await expect(article(page, "s1.q1").locator(".hints__item")).toContainText('alert("HINT1")');
  await expect(article(page, "s1.q1").locator(".q__prompt")).toContainText('alert("PROMPT")');
  await expect(article(page, "s1.q2").locator(".order__item").filter({ hasText: 'alert("ORDER")' })).toHaveCount(1);
  const scoreAfterHint = await headerScore(page);

  // Лаборатория, этап 1
  await page.goto("/lab/");
  expect(await lab(page, "costume", "chem", "1-01")).toMatch(/^Недостаточно оснований/);
  expect(await headerScore(page)).toBe(scoreAfterHint - PEN);
  // повтор — без штрафа
  expect(await lab(page, "costume", "chem", "1-01")).toMatch(/уже рассматривали/);
  expect(await headerScore(page)).toBe(scoreAfterHint - PEN);
  expect(await lab(page, "water", "chem", "1-09")).toMatch(/Экспертиза выполнена/);
  await expect(page.locator(".lab-result")).toContainText("Питьевая вода");
  await expect(page.locator(".lab-result")).not.toContainText("QA-WATER-STAGE3");
  // объект этапа 2 ещё недоступен
  expect(await page.locator(".lab-form__grid select").nth(0).locator('option[value="inhaler"]').count()).toBe(0);

  await page.goto("/");
  await finishStage(page, 1);
  // этап 2: вариант с полезной нагрузкой виден как текст
  await expect(article(page, "s2.b1")).toContainText('alert("OPTION")');

  await page.goto("/lab/");
  const before2 = await headerScore(page);
  expect(await lab(page, "costume", "chem", "1-01")).toMatch(/Экспертиза выполнена/);
  await expect(page.locator(".lab-result")).toContainText("QA-COSTUME-STAGE2");
  expect(await headerScore(page)).toBe(before2);
  // архив: запрос теперь «выполнен», отклонённая запись осталась в истории
  await expect(page.locator(".lab-archive__item.is-done")).toHaveCount(2);

  await page.goto("/");
  await finishStage(page, 2);
  await page.goto("/lab/");
  const before3 = await headerScore(page);
  expect(await lab(page, "water", "chem", "1-09")).toMatch(/Экспертиза выполнена/);
  await expect(page.locator(".lab-result")).toContainText("QA-WATER-STAGE3");
  expect(await headerScore(page)).toBe(before3);
  // архив: «Открыть результат» по старой записи показывает актуальный (поздний) результат
  await page.reload();
  await page.locator(".lab-archive__item.is-done").last().getByRole("button", { name: "Открыть результат" }).click();
  await expect(page.locator(".lab-result")).toContainText("QA-WATER-STAGE3");

  const done = new Set<string>(["water-chem", "qa-water-s3", "qa-costume-s2"]);
  await labAll(page, A, 3, done);
  await finishStage(page, 3);

  // Финал: все ответы верные → разбор и развязка (судьбы с полезной нагрузкой)
  await page.goto("/final/");
  await page.getByRole("button", { name: "Начать финал" }).click();
  const confirm = page.locator(".modal").getByRole("button", { name: "Начать финал" });
  if (await confirm.count()) await confirm.click();
  const last = A.stages[3];
  for (const path of A.finalOrder) {
    const q = last.questions.find((x) => x.path === path)!;
    await expect(article(page, path)).toBeVisible({ timeout: 30_000 });
    await fillQuestion(page, q);
    await submit(page, path);
  }
  await expect(page.locator("table.review")).toBeVisible({ timeout: 60_000 });
  await expect(page.locator("table.review")).toContainText('alert("PROMPT")');
  await page.getByRole("button", { name: "Перейти к развязке" }).click();
  await page.getByRole("button", { name: "Дальше" }).click();
  await page.getByRole("button", { name: "Дальше" }).click();
  await expect(page.locator(".fates")).toContainText('alert("FATE")');
  await page.goto("/");
  await page.locator("details.passed").first().evaluate((d) => ((d as HTMLDetailsElement).open = true));
  await page.waitForTimeout(500);
  expect(fired).toEqual([]);
  const dom = await page.evaluate(() => document.querySelectorAll("img[onerror], script:not([src])").length);
  expect(dom).toBe(0);
});

const KEYS: Record<string, string> = {
  inna: "m3JSIA6ahzMVtM__42s2Ibq80FFpoIGksFeGA4JcB6Q",
  pharma: "KVEkg_rgJc-0di3z-uQ7FZepoCi4BcIBskTJjiItKK4",
};

test("XSS на вымышленных страницах (открытые, закрытые, облако)", async ({ page }) => {
  const fired = watchXss(page);
  for (const slug of ["gromov", "news", "call"]) {
    await page.goto(`/p/${slug}/`);
    await page.waitForLoadState("networkidle");
  }
  await expect(page.locator("body")).toContainText('alert("CALLNOTE")');
  for (const [slug, k] of Object.entries(KEYS)) {
    await page.goto(`/p/${slug}/#k=${k}`);
    await expect(page.locator("body[data-ready='1']")).toHaveCount(1, { timeout: 15_000 });
  }
  await expect(page.locator("body")).toContainText('alert("CONTRA")');
  await page.locator("#fs-q").fill("img");
  await page.waitForTimeout(200);
  await page.goto("/p/inna/");
  await page.locator(".kd-tile__btn").first().click();
  await expect(page.locator(".kd-view")).toContainText('alert("CAPTION")');
  await page.goto("/p/cloud/");
  await page.locator("input[name=password]").fill("QA pass 1");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.locator("body[data-ready='1']")).toHaveCount(1, { timeout: 15_000 });
  await expect(page.locator("body")).toContainText('alert("REGISTRY")');
  // сортировка реестра по всем колонкам
  const ths = page.locator("table[data-sortable] thead th button:visible");
  for (let i = 0; i < (await ths.count()); i++) await ths.nth(i).click();
  // sessionStorage облака: ключ, а не пароль
  const ss = await page.evaluate(() => ({ ...sessionStorage }));
  expect(JSON.stringify(ss)).not.toMatch(/qa.?pass/i);
  expect(Object.keys(ss)).toContain("detgame:page:cloud");
  expect(fired).toEqual([]);
});
