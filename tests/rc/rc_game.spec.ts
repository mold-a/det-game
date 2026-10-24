// RC-проход игры правильными ответами на 360 и 1280 px: вопросы по одному, бонусы, «Пропустить бонусы»,
// окна конвертов, лаборатория (нет в описи / ничего не выявила / повтор / заключение), финал и развязка.
import { test, expect, type Page } from "@playwright/test";
import { loadAnswers, startGame, fillQuestion, submit, article, labRequest, headerScore, objectText, envelopeOpened, solve, scoreLog } from "../e2e/helpers";
import { watch, shot, brokenImages, placeholders, noHScroll } from "./rc_util";

const A = loadAnswers();
const S = A.settings;
test.setTimeout(900_000);

for (const [w, h, skipStage] of [[360, 780, 2], [1280, 900, 0]] as const) {
  test(`игра ${w}px${skipStage ? ` (бонусы этапа ${skipStage} пропускаются)` : " (все бонусы)"}`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h });
    const wt = watch(page);
    const tag = `game-${w}`;
    await page.goto("/");
    await shot(page, `${tag}-00-start`);
    await startGame(page);
    await shot(page, `${tag}-01-stage1`, false);

    // Лаборатория: нет в описи / ничего не выявила / повтор
    await page.goto("/lab/");
    await expect(page.locator(".lab-form")).toBeVisible();
    await shot(page, `${tag}-02-lab-empty`);
    const first = A.lab.find((x) => x.stage === 1)!;
    const late = A.lab.find((x) => ((x as any).objectFromStage ?? x.stage) > 1)!;
    let msg = await labRequest(page, late, first.bases[0]);
    expect(msg).toMatch(/^Сейчас этот предмет нельзя передать/);
    expect(await headerScore(page)).toBe(0);
    await shot(page, `${tag}-03-lab-notinventory`, false);
    msg = await labRequest(page, first, first.wrongBasis);
    expect(msg).toMatch(/^Экспертиза ничего не выявила/);
    expect(await headerScore(page)).toBe(S.penalties.labNoBasis);
    await shot(page, `${tag}-04-lab-nothing`, false);
    expect(await labRequest(page, first, first.wrongBasis)).toMatch(/^Такая заявка уже выполнялась/);
    expect(await headerScore(page)).toBe(S.penalties.labNoBasis);

    const done = new Set<string>();
    const labStage = async (n: number) => {
      await page.goto("/lab/#order");
      await expect(page.locator(".lab-form")).toBeVisible();
      for (const e of A.lab.filter((x) => x.stage <= n && !done.has(x.result))) {
        const m = await labRequest(page, e);
        expect(m, e.result).toMatch(/^Заключение готово/);
        done.add(e.result);
      }
      await shot(page, `${tag}-lab-order-stage${n}`, false);
      await page.goto("/lab/#orders");
      await expect(page.locator(".orders__item.is-done").first()).toBeVisible();
      await shot(page, `${tag}-lab-orders-stage${n}`);
      if (n === 1) {
        await page.locator(".orders__item.is-done").first().getByRole("button", { name: "Открыть заключение" }).click();
        await expect(page.locator(".modal")).toBeVisible();
        await shot(page, `${tag}-lab-conclusion`, false);
        await page.keyboard.press("Escape");
        if (await page.locator(".modal").count()) await page.locator(".modal").getByRole("button", { name: /Закрыть|Понятно|OK/i }).first().click();
        await expect(page.locator(".modal")).toHaveCount(0);
      }
      await page.goto("/");
      await expect(page.locator("#stage-title")).toBeVisible();
      const gate = page.getByRole("button", { name: "Перейти к вопросам", exact: true });
      if (await gate.count()) {
        await gate.click();
        await page.locator(".modal").getByRole("button", { name: "Перейти", exact: true }).click();
      }
    };

    let skippedBonuses = 0;
    for (const stage of A.stages.slice(0, -1)) {
      await labStage(stage.n);
      await expect(page.locator("#stage-title")).toHaveText(`Этап ${stage.n}`);
      const mand = stage.questions.filter((x) => x.kind === "mandatory");
      const bonuses = stage.questions.filter((x) => x.kind === "bonus");
      for (const q of mand.slice(0, -1)) {
        await expect(article(page, q.path)).toBeVisible();
        await shot(page, `${tag}-s${stage.n}-${q.path}-open`, false);
        await solve(page, q);
        await shot(page, `${tag}-s${stage.n}-${q.path}-solved`, false);
      }
      const last = mand[mand.length - 1];
      await fillQuestion(page, last);
      await submit(page, last.path);
      if (bonuses.length) {
        await expect(article(page, bonuses[0].path)).toBeVisible({ timeout: 30_000 });
        await expect(page.locator(".modal")).toHaveCount(0);
        await shot(page, `${tag}-s${stage.n}-bonus-phase`);
        if (stage.n === skipStage) {
          await page.getByRole("button", { name: /^Пропустить бонусы и перейти к конверту №\d+$/ }).click();
          skippedBonuses += bonuses.length;
        } else {
          for (const q of bonuses) {
            await shot(page, `${tag}-s${stage.n}-${q.path}-open`, false);
            await solve(page, q);
          }
          await shot(page, `${tag}-s${stage.n}-bonus-done`, false);
        }
      }
      await expect(page.locator(".modal")).toBeVisible({ timeout: 30_000 });
      await shot(page, `${tag}-s${stage.n}-envelope-modal`, false);
      await page.locator(".modal").getByRole("button", { name: "Конверт вскрыт" }).click();
      await expect(page.locator(".modal")).toHaveCount(0);
      await expect(page.locator("#stage-title")).toHaveText(`Этап ${stage.n + 1}`);
      // подсветка текущего конверта в шапке
      await shot(page, `${tag}-s${stage.n + 1}-start`, false);
      const gate = page.getByRole("button", { name: "Перейти к вопросам", exact: true });
      if (await gate.count()) {
        await shot(page, `${tag}-s${stage.n + 1}-gate`, false);
        await gate.click();
        await page.locator(".modal").getByRole("button", { name: "Перейти", exact: true }).click();
        await expect(page.locator(".modal")).toHaveCount(0);
      }
    }
    // Этап 4: лаборатория, вопросы по одному до финала
    const lastStage = A.stages[A.stages.length - 1];
    await labStage(lastStage.n);
    const finalSet = new Set(A.finalOrder);
    for (const q of lastStage.questions.filter((x) => x.kind === "mandatory" && !finalSet.has(x.path))) {
      if (await article(page, q.path).count()) {
        await solve(page, q);
        await shot(page, `${tag}-s4-${q.path}-solved`, false);
      }
    }
    const before = await headerScore(page);
    await shot(page, `${tag}-s4-before-final`);
    await page.getByRole("link", { name: "Перейти к финалу" }).click();
    await expect(page.locator(".final-warn")).toContainText("нельзя изменить");
    await shot(page, `${tag}-final-00-warn`, false);
    await page.getByRole("button", { name: "Начать финал" }).click();
    // при непройденных бонусах просит подтверждения
    const confirm = page.locator(".modal").getByRole("button", { name: "Начать финал" });
    if (await confirm.count()) {
      await shot(page, `${tag}-final-00b-confirm`, false);
      await confirm.click();
    }
    const byPath = Object.fromEntries(lastStage.questions.map((q) => [q.path, q]));
    let i = 0;
    for (const path of A.finalOrder) {
      await expect(article(page, path)).toBeVisible();
      if (i === 0) await shot(page, `${tag}-final-01-q1`, false);
      await fillQuestion(page, byPath[path]);
      await submit(page, path);
      expect(await headerScore(page)).toBe(before);
      i++;
    }
    await expect(page.locator("#final-title")).toHaveText("Итоги", { timeout: 60_000 });
    const total = await headerScore(page);
    const log = await scoreLog(page);
    expect(total).toBe(log.reduce((a, e) => a + e.delta, 0));
    if (!skippedBonuses) expect(total).toBe(A.expected.perfectRunScore + S.penalties.labNoBasis);
    else console.log(`RC ${w}px: пропущено бонусов ${skippedBonuses}, счёт ${total}, идеал ${A.expected.perfectRunScore + S.penalties.labNoBasis}`);
    await shot(page, `${tag}-final-02-results`);
    await page.getByRole("button", { name: "Перейти к развязке" }).click();
    await expect(page.locator("#final-title")).toHaveText(/Признание/);
    await shot(page, `${tag}-final-03-confession`);
    await page.getByRole("button", { name: "Дальше" }).click();
    await expect(page.locator("#final-title")).toHaveText(/Письмо/);
    await shot(page, `${tag}-final-04-letter`);
    await page.getByRole("button", { name: "Дальше" }).click();
    await expect(page.locator(".fates__item").first()).toBeVisible();
    await shot(page, `${tag}-final-05-fates`);
    expect(await brokenImages(page)).toEqual([]);
    expect(await placeholders(page)).toEqual([]);
    await page.getByRole("link", { name: "Вернуться к делу" }).click();
    await expect(page.locator(".notice")).toContainText("Игра завершена");
    await shot(page, `${tag}-final-06-home-finished`);
    await noHScroll(page);
    expect(wt.problems).toEqual([]);
    const tot = [...wt.bytes.values()].reduce((a, b) => a + b, 0);
    console.log(`RC ${w}px: запросов ${wt.urls.length}, байт ${tot}`);
  });
}
