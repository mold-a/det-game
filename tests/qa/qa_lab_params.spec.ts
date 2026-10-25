// QA: параметры экспертизы — допуск времени ±tolerance, нормализация как у вопросов,
// неформатный параметр — не заявка и не штраф; повтор пустой — без штрафа (docs/01 §7).
import { test, expect, type Page } from "@playwright/test";
import { loadAnswers, playToStage, headerScore, objectText } from "../e2e/helpers";
import { readState } from "./qa_util";

const A = loadAnswers();
const PEN = Math.abs(A.settings.penalties.labNoBasis);
const E = A.lab.find((x) => x.object === "station_cam")!;
// Дата-ответ берётся из контента (dump-answers), а не из литерала: ДД.ММ.ГГГГ и производные форматы ввода.
const [DD, MM, YYYY] = E.params.date.input.split(".");
const YY = YYYY.slice(2);
const DATE = `${DD}.${MM}.${YYYY}`;
const otherDay = (() => {
  const d = new Date(Date.UTC(+YYYY, +MM - 1, +DD + 1));
  const p2 = (n: number) => String(n).padStart(2, "0");
  return `${p2(d.getUTCDate())}.${p2(d.getUTCMonth() + 1)}.${d.getUTCFullYear()}`;
})();
test.setTimeout(300_000);

async function send(page: Page, date: string, time: string, win: string, basis = E.bases[0]) {
  await page.locator("#lab-object").fill(objectText(E));
  await page.locator("#lab-type").selectOption(E.types[0]);
  await page.locator("#lab-basis").selectOption(basis);
  const inputs = page.locator(".lab-params input");
  await inputs.nth(0).fill(date);
  await inputs.nth(1).fill(time);
  await inputs.nth(2).fill(win);
  const msg = page.locator(".lab-form .lab-msg");
  await msg.evaluate((m) => (m.textContent = ""));
  await page.getByRole("button", { name: "Направить заявку" }).click();
  await expect(msg).not.toHaveText("", { timeout: 15_000 });
  return (await msg.textContent()) ?? "";
}

test("камеры вокзала: допуск ±7 мин, форматы ввода, неформат без штрафа", async ({ page }) => {
  await playToStage(page, A, 4);
  await page.goto("/lab/");
  await expect(page.locator(".lab-form")).toBeVisible();
  // подписи параметров: у каждого input есть доступное имя
  await page.locator("#lab-object").fill(objectText(E));
  for (const name of ["Дата", "Время", "Номер кассы"]) await expect(page.getByRole("textbox", { name })).toHaveCount(1);

  const variants: string[] = E.params.time.variants ?? [];
  const lo = variants[0];
  const hi = variants[variants.length - 1];
  const shift = (t: string, d: number) => {
    const [h, m] = t.split(":").map(Number);
    const x = h * 60 + m + d;
    return `${String(Math.floor(x / 60)).padStart(2, "0")}:${String(x % 60).padStart(2, "0")}`;
  };
  let score = await headerScore(page);
  const ok = async (d: string, t: string, w: string) => {
    expect(await send(page, d, t, w), `${d} ${t} ${w}`).toMatch(/^(Заключение готово|Такая заявка уже выполнялась)/);
    expect(await headerScore(page)).toBe(score);
  };
  const no = async (d: string, t: string, w: string) => {
    expect(await send(page, d, t, w), `${d} ${t} ${w}`).toMatch(/^Экспертиза ничего не выявила/);
    score -= PEN;
    expect(await headerScore(page)).toBe(score);
  };
  const fmt = async (d: string, t: string, w: string, re: RegExp) => {
    expect(await send(page, d, t, w), `${d} ${t} ${w}`).toMatch(re);
    expect(await headerScore(page)).toBe(score);
  };

  await ok(DATE, E.params.time.input, "2");
  await ok(`${DD}.${MM}`, lo, "2");
  await ok(` ${DD}/${MM}/${YY} `, hi, "касса №2");
  await ok(`${DD} ${MM} ${YYYY}`, E.params.time.input.replace(":", "."), "02");
  await ok(DATE, E.params.time.input.replace(":", ""), " 2 ");
  await no(DATE, shift(lo, -1), "2");
  await no(DATE, shift(hi, +1), "2");
  await no(otherDay, E.params.time.input, "2");
  await no(DATE, E.params.time.input, "3");
  // повтор отклонённого (другая запись того же ввода) — без штрафа
  expect(await send(page, `${DD}.${MM}.${YY}`, shift(hi, +1).replace(":", "."), "№2")).toMatch(/^Такая заявка уже выполнялась/);
  expect(await headerScore(page)).toBe(score);
  // неформат — не запрос
  await fmt(DATE, "25:70", "2", /ЧЧ:ММ/);
  await fmt("31.02.2026", E.params.time.input, "2", /ДД\.ММ/);
  await fmt(DATE, E.params.time.input, "касса", /числ/);
  await fmt("", E.params.time.input, "2", /Заполните все поля/);
  const s = await readState(page);
  expect(s.docs).toContain(E.doc);
  expect(s.log.filter((e: any) => e.r.startsWith("lab:")).length).toBe(4);
});
