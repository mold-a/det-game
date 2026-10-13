// P08 п. 2 — производительность при CPU throttling ×4 (CDP Emulation.setCPUThrottlingRate).
// Замеры — в консоль и во вложение perf.json; жёсткий порог не ставится (отчёт),
// но проверка ответа дольше 2 с считается провалом.
import { test, expect, type Page } from "@playwright/test";
import { loadAnswers, startGame, article, fillQuestion, submit } from "./helpers";

const A = loadAnswers();
test.setTimeout(240_000);

const median = (xs: number[]) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];

async function inPage(page: Page, A: any) {
  const st1 = A.stages[0];
  const form = st1.questions.find((q: any) => q.type === "form" && q.fields.length >= 4);
  const text = A.stages.flatMap((s: any) => s.questions).find((q: any) => q.type === "text");
  const units: Record<string, any> = {};
  for (const q of st1.questions.filter((x: any) => x.kind === "mandatory")) {
    units[q.path] = { status: "solved", canon: q.type === "form" ? Object.fromEntries(q.fields.map((f: any) => [f.id, f.canon])) : q.canon };
  }
  return page.evaluate(
    async ({ formPath, textPath, units, textWrong, formWrong }) => {
      const g = await import("/assets/js/core/game.js");
      const pub = await g.loadPublic();
      const t = async (fn: () => Promise<unknown>) => {
        const s = performance.now();
        await fn();
        return performance.now() - s;
      };
      const res: Record<string, number[]> = { startKey: [], packOpen: [], textCheck: [], form4Check: [], stageKey: [], busyLoop: [] };
      let k1: Uint8Array = new Uint8Array();
      for (let i = 0; i < 3; i++) res.startKey.push(await t(async () => (k1 = await g.startKey(pub))));
      let pack: any;
      for (let i = 0; i < 3; i++) res.packOpen.push(await t(async () => (pack = await g.openPack(1, k1))));
      const all = [pack];
      const textStage = Number(textPath.slice(1, textPath.indexOf(".")));
      const textQ = textStage === 1 ? pack.questions.find((q: any) => q.path === textPath) : null;
      const formQ = pack.questions.find((q: any) => q.path === formPath);
      for (let i = 0; i < 5; i++) {
        if (textQ) res.textCheck.push(await t(() => g.checkQuestion(textQ, textWrong[i % textWrong.length], pub)));
        res.form4Check.push(await t(() => g.checkQuestion(formQ, formWrong, pub)));
      }
      for (let i = 0; i < 3; i++) res.stageKey.push(await t(() => g.nextStageKey(pack, units, pub)));
      // Контроль, что замедление действует на основной поток: чистый JS-цикл.
      for (let i = 0; i < 3; i++)
        res.busyLoop.push(
          await t(async () => {
            let x = 0;
            for (let j = 0; j < 5e6; j++) x = (x + j * 7) % 1000003;
            return x;
          }),
        );
      return { res, iter: pub.iter, n: all.length };
    },
    {
      formPath: form.path,
      textPath: text.path,
      units,
      textWrong: text.wrong.map(String),
      formWrong: Object.fromEntries(form.fields.map((f: any) => [f.id, f.wrong[0]])),
    },
  );
}

async function uiTimings(page: Page) {
  // Проверка в интерфейсе: «Проверить» → сообщение (текстовый бонус и форма из 4 полей).
  const st1 = A.stages[0];
  const text = st1.questions.find((q) => q.type === "text")!;
  const form = st1.questions.find((q) => q.type === "form")!;
  const out: Record<string, number> = {};
  await fillQuestion(page, form, Object.fromEntries(form.fields!.map((f) => [f.id, f.wrong[0]])));
  let s = Date.now();
  await submit(page, form.path);
  await expect(article(page, form.path).locator(".q__msg")).toHaveText(/не подтверждается/, { timeout: 20_000 });
  out.uiForm4 = Date.now() - s;
  await fillQuestion(page, text, text.wrong[0]);
  s = Date.now();
  await submit(page, text.path);
  await expect(article(page, text.path).locator(".q__msg")).not.toHaveText("", { timeout: 20_000 });
  out.uiText = Date.now() - s;
  s = Date.now();
  await page.goto("/lab/");
  await expect(page.locator(".lab-form")).toBeVisible();
  out.labOpen = Date.now() - s;
  s = Date.now();
  await page.goto("/");
  await expect(page.locator("#stage-title")).toBeVisible();
  out.mainOpen = Date.now() - s;
  return out;
}

for (const rate of [1, 4]) {
  test(`производительность, CPU ×${rate}`, async ({ page }) => {
    await startGame(page);
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setCPUThrottlingRate", { rate });
    const { res, iter } = await inPage(page, A);
    const ui = await uiTimings(page);
    const summary: Record<string, number> = { ...ui };
    for (const [k, v] of Object.entries(res)) if (v.length) summary[k] = Math.round(median(v));
    const report = { rate, iter, ms: summary };
    console.log("PERF", JSON.stringify(report));
    await test.info().attach(`perf-x${rate}.json`, { body: JSON.stringify(report, null, 2), contentType: "application/json" });
    expect(summary.form4Check).toBeLessThan(2000);
  });
}
