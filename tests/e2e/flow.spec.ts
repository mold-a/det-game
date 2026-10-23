// Вопросы этапа по одному (docs/01 «Поток этапа»): обязательные — следующий после верного ответа; бонусы — после
// последнего обязательного, следующий после ответа (верного или нет); окно конверта — после бонусов или «Пропустить бонусы».
import { test, expect } from "@playwright/test";
import { loadAnswers, playToStage, startGame, labAll, solve, fillQuestion, submit, article, envelopeOpened, headerScore } from "./helpers";

const A = loadAnswers();
const S = A.settings;
test.setTimeout(240_000);

const skipBtn = (page: any, env: number) => page.getByRole("button", { name: `Пропустить бонусы и перейти к конверту №${env}` });

// Подсветка «текущий» в шапке совпадает с этапом на экране; конверты дальше — запечатаны, раньше — вскрыты.
async function expectHeaderCurrent(page: any, n: number) {
  const items = page.locator(".stages__item");
  await expect(page.locator(".stages__item.is-current")).toHaveCount(1);
  await expect(items.nth(n - 1)).toHaveClass(/is-current/);
  await expect(items.nth(n - 1)).toHaveAttribute("aria-current", "step");
  await expect(page.locator("#stage-title")).toHaveText(`Этап ${n}`);
  for (let k = 1; k < n; k++) await expect(items.nth(k - 1)).toHaveClass(/is-done/);
  for (let k = n + 1; k <= (await items.count()); k++) {
    await expect(items.nth(k - 1)).not.toHaveClass(/is-(current|done)/);
    await expect(items.nth(k - 1)).toHaveAttribute("aria-label", `Этап ${k}, конверт не вскрыт`);
  }
}

test("бонусы этапа 2: по одному; неверный ответ тоже открывает следующий; после последнего — окно конверта", async ({ page }) => {
  const done = await playToStage(page, A, 2);
  const st = A.stages.find((s) => s.n === 2)!;
  const mand = st.questions.filter((q) => q.kind === "mandatory");
  const bonuses = st.questions.filter((q) => q.kind === "bonus");
  expect(bonuses.length).toBeGreaterThanOrEqual(2);
  await labAll(page, A, 2, done);

  // Пока обязательные не пройдены, бонусов нет вовсе.
  await expect(page.getByText("Бонусные вопросы")).toHaveCount(0);
  for (const b of bonuses) await expect(article(page, b.path)).toHaveCount(0);
  for (const q of mand.slice(0, -1)) await solve(page, q);
  const last = mand[mand.length - 1];
  await fillQuestion(page, last);
  await submit(page, last.path);

  // Последний обязательный решён: окна нет, виден первый бонус, остальные скрыты, кнопка «Пропустить» на месте.
  await expect(article(page, bonuses[0].path)).toBeVisible({ timeout: 30_000 });
  await expectHeaderCurrent(page, 2);
  await expect(page.locator(".modal")).toHaveCount(0);
  await expect(page.locator("#stage-title")).toHaveText("Этап 2");
  await expect(article(page, last.path)).toHaveClass(/q--solved/);
  await expect(article(page, bonuses[1].path)).toHaveCount(0);
  await expect(page.getByText("Следующий вопрос откроется после ответа на текущий")).toHaveCount(1);
  await expect(skipBtn(page, 3)).toBeVisible();

  // После перезагрузки — то же самое: бонусы, а не окно конверта.
  await page.reload();
  await expect(article(page, bonuses[0].path)).toBeVisible();
  await expect(page.locator(".modal")).toHaveCount(0);
  await expect(article(page, bonuses[1].path)).toHaveCount(0);
  await expectHeaderCurrent(page, 2);

  // Неверный ответ на первый бонус: вопрос закрыт, второй открылся, окна всё ещё нет.
  const before = await headerScore(page);
  await fillQuestion(page, bonuses[0], bonuses[0].wrong[0]);
  await submit(page, bonuses[0].path);
  await expect(article(page, bonuses[0].path)).toHaveClass(/q--closed/);
  await expect(article(page, bonuses[1].path)).toBeVisible();
  await expect(page.locator(".modal")).toHaveCount(0);
  expect(await headerScore(page)).toBe(before);

  // Верный ответ на последний бонус — окно «Откройте конверт №3».
  await solve(page, bonuses[1]);
  await expect(page.locator(".modal")).toContainText("3");
  await expect(page.locator(".modal")).toContainText(S.points.bonus ? "+" : "");
  // Окно открыто, но «Конверт вскрыт» не нажат: на экране ещё этап 2, конверт 3 запечатан.
  await expect(page.locator("#stage-title")).toHaveText("Этап 2");
  await expectHeaderCurrent(page, 2);
  await envelopeOpened(page);
  await expect(page.locator("#stage-title")).toHaveText("Этап 3");
  await expectHeaderCurrent(page, 3);
  expect(await headerScore(page)).toBe(before + S.points.bonus);
  await expect(skipBtn(page, 3)).toHaveCount(0);
});

test("«Пропустить бонусы»: окно конверта; бонусы ждут в блоке пройденного этапа, по одному", async ({ page }) => {
  const done = await playToStage(page, A, 2);
  const st = A.stages.find((s) => s.n === 2)!;
  const bonuses = st.questions.filter((q) => q.kind === "bonus");
  await labAll(page, A, 2, done);

  const mand = st.questions.filter((q) => q.kind === "mandatory");
  for (const q of mand.slice(0, -1)) await solve(page, q);
  await fillQuestion(page, mand[mand.length - 1]);
  await submit(page, mand[mand.length - 1].path);
  await expect(skipBtn(page, 3)).toBeVisible({ timeout: 30_000 });
  const score = await headerScore(page);

  await skipBtn(page, 3).click();
  await expect(page.locator(".modal")).toContainText("3");
  await envelopeOpened(page);
  await expect(page.locator("#stage-title")).toHaveText("Этап 3");
  expect(await headerScore(page)).toBe(score);

  // Пройденный этап 2 раскрыт: виден только первый неотвеченный бонус.
  const passed2 = page.locator("details.passed").filter({ hasText: "Этап 2 пройден" });
  await expect(passed2).toHaveJSProperty("open", true);
  await expect(passed2.locator(`article[data-path="${bonuses[0].path}"] button[type=submit]`)).toBeVisible();
  await expect(passed2.locator(`article[data-path="${bonuses[1].path}"]`)).toHaveCount(0);
  await expect(passed2.getByText("Следующий вопрос откроется после ответа на текущий")).toBeVisible();
  // В текущем этапе 3 этих бонусов нет.
  await expect(page.locator("details.letter ~ section article", { hasText: bonuses[0].prompt ?? "\u0000" })).toHaveCount(0);

  // Ответ в блоке пройденного этапа открывает следующий бонус; окна конверта нет.
  await solve(page, bonuses[0]);
  await expect(passed2.locator(`article[data-path="${bonuses[1].path}"] button[type=submit]`)).toBeVisible();
  await expect(page.locator(".modal")).toHaveCount(0);
  await solve(page, bonuses[1]);
  await expect(page.locator(".modal")).toHaveCount(0);
  await expect(passed2.getByText("Следующий вопрос откроется после ответа на текущий")).toHaveCount(0);

  // Перезагрузка: всё отвечено, блок свёрнут.
  await page.reload();
  await expect(page.locator("#stage-title")).toHaveText("Этап 3");
  await expect(page.locator("details.passed").filter({ hasText: "Этап 2 пройден" })).toHaveJSProperty("open", false);
});

test("полное прохождение с «Пропустить бонусы» на каждом этапе; до финала бонусы остаются доступными", async ({ page }) => {
  await playToStage(page, A, 4, new Set(), "skip");
  await expect(page.locator("#stage-title")).toHaveText("Этап 4");
  // Пропущены бонусы этапов 1–3: блоки пройденных этапов раскрыты и содержат по одному вопросу для ответа.
  const open = page.locator("details.passed.passed--bonus");
  await expect(open).toHaveCount(3);
  for (const n of [1, 2, 3]) {
    const b = A.stages.find((s) => s.n === n)!.questions.find((q) => q.kind === "bonus")!;
    await expect(article(page, b.path).locator("button[type=submit]")).toBeVisible();
  }
});

test("старое сохранение: бонус отвечен раньше обязательного — ответ виден, порядок выводится из состояния", async ({ page }) => {
  await startGame(page);
  const st = A.stages[0];
  const mand = st.questions.filter((q) => q.kind === "mandatory");
  const bonus = st.questions.find((q) => q.kind === "bonus")!;
  // Старый интерфейс показывал бонус сразу: отвечаем на него в сохранении напрямую.
  await page.evaluate((path) => {
    for (const k of Object.keys(localStorage)) {
      const state = JSON.parse(localStorage.getItem(k)!);
      if (state && state.v === 1 && state.stage) {
        state.units[path] = { status: "closed", canon: null, given: "x" };
        localStorage.setItem(k, JSON.stringify(state));
      }
    }
  }, bonus.path);
  await page.reload();
  await expect(article(page, mand[0].path)).toBeVisible();
  await expect(article(page, bonus.path)).toBeVisible();
  await expect(article(page, bonus.path)).toHaveClass(/q--closed/);
  await expect(article(page, mand[1].path)).toHaveCount(0);
  // Все обязательные пройдены, бонус уже отвечен → сразу окно конверта.
  await solve(page, mand[0]);
  await fillQuestion(page, mand[1]);
  await submit(page, mand[1].path);
  await envelopeOpened(page);
  await expect(page.locator("#stage-title")).toHaveText("Этап 2");
  expect(mand.length).toBe(2);
});
