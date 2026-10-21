// QA: параметры экспертизы — допуск времени ±tolerance, нормализация как у вопросов,
// неформатный параметр — не заявка и не штраф; повтор пустой — без штрафа (docs/01 §7).
import { test, expect, type Page } from "@playwright/test";
import { loadAnswers, playToStage, headerScore, objectText } from "../e2e/helpers";
import { readState } from "./qa_util";

const A = loadAnswers();
const PEN = Math.abs(A.settings.penalties.labNoBasis);
const E = A.lab.find((x) => x.object === "station_cam")!;
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

  await ok("30.10.2026", E.params.time.input, "2");
  await ok("30.10", lo, "2");
  await ok(" 30/10/26 ", hi, "касса №2");
  await ok("30 10 2026", E.params.time.input.replace(":", "."), "02");
  await ok("30.10.2026", E.params.time.input.replace(":", ""), " 2 ");
  await no("30.10.2026", shift(lo, -1), "2");
  await no("30.10.2026", shift(hi, +1), "2");
  await no("31.10.2026", E.params.time.input, "2");
  await no("30.10.2026", E.params.time.input, "3");
  // повтор отклонённого (другая запись того же ввода) — без штрафа
  expect(await send(page, "30.10.26", shift(hi, +1).replace(":", "."), "№2")).toMatch(/^Такая заявка уже выполнялась/);
  expect(await headerScore(page)).toBe(score);
  // неформат — не запрос
  await fmt("30.10.2026", "25:70", "2", /ЧЧ:ММ/);
  await fmt("31.02.2026", "14:37", "2", /ДД\.ММ/);
  await fmt("30.10.2026", "14:37", "касса", /числ/);
  await fmt("", "14:37", "2", /Заполните все поля/);
  const s = await readState(page);
  expect(s.docs).toContain(E.doc);
  expect(s.log.filter((e: any) => e.r.startsWith("lab:")).length).toBe(4);
});
