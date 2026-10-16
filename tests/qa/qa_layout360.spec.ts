// QA: вёрстка на 360 px (docs/05 §3): нет горизонтальной прокрутки ни в одном состоянии,
// длинные имена/варианты/название команды, справочник 9 препаратов, реестр облака.
// Работает и на обычной сборке, и на mod (длинные ФИО, длинный вариант, длинные слова).
import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { loadAnswers, startGame, playToStage, article, fillQuestion, submit, envelopeOpened, labAll, solve } from "../e2e/helpers";
import { readState, writeState, collectErrors } from "./qa_util";

const A = loadAnswers();
const KEYS: Record<string, string> = JSON.parse(readFileSync("engine/salts.lock.json", "utf-8")).pages;
test.setTimeout(400_000);
test.use({ viewport: { width: 360, height: 740 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });

/** Горизонтальная прокрутка документа и элементы, вылезающие за правый край. */
async function overflow(page: Page, label: string) {
  return page.evaluate((label) => {
    const W = document.documentElement.clientWidth;
    const out: string[] = [];
    const sw = document.documentElement.scrollWidth;
    if (sw > W) out.push(`${label}: scrollWidth ${sw} > ${W}`);
    const inScroller = (el: Element) => {
      for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) {
        const ox = getComputedStyle(e).overflowX;
        if (ox === "auto" || ox === "scroll" || ox === "hidden" || ox === "clip") return true;
      }
      return false;
    };
    for (const el of Array.from(document.body.querySelectorAll("*"))) {
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      if (el.closest("[hidden], .visually-hidden, .skip-link")) continue;
      if (r.right > W + 1 && !inScroller(el)) {
        out.push(`${label}: <${el.tagName.toLowerCase()} class="${(el as HTMLElement).className}"> right=${Math.round(r.right)} «${(el.textContent || "").trim().slice(0, 30)}»`);
        if (out.length > 8) break;
      }
    }
    return out;
  }, label);
}

test("главный экран, лаборатория, финал на 360 px", async ({ page }) => {
  const errors = collectErrors(page);
  const issues: string[] = [];
  await page.goto("/");
  issues.push(...(await overflow(page, "intro")));
  await startGame(page);
  // длинное название команды без пробелов (maxlength 60)
  const s = await readState(page);
  await writeState(page, { ...s, team: "Северноебюрорасследованийимени" + "Шерлока".repeat(4) });
  await page.reload();
  issues.push(...(await overflow(page, "этап 1 (длинная команда)")));
  await page.locator(".menu summary").click();
  issues.push(...(await overflow(page, "меню открыто")));
  await page.locator(".menu summary").click();
  await article(page, "s1.q1").getByRole("button", { name: /Подсказка/ }).click();
  issues.push(...(await overflow(page, "модалка подсказки")));
  await page.locator(".modal").getByRole("button", { name: "Отмена" }).click();
  await page.locator(".scorelog summary").click();
  issues.push(...(await overflow(page, "журнал открыт")));

  // этапы 1..3 + лаборатория на каждом
  const done = new Set<string>();
  for (const stage of A.stages.filter((x) => x.n < 4)) {
    await labAll(page, A, stage.n, done);
    await page.goto("/lab/");
    issues.push(...(await overflow(page, `lab этап ${stage.n}`)));
    await page.goto("/");
    issues.push(...(await overflow(page, `этап ${stage.n}`)));
    for (const q of stage.questions.filter((x) => x.kind === "bonus")) await solve(page, q);
    const mand = stage.questions.filter((x) => x.kind === "mandatory");
    for (const q of mand.slice(0, -1)) await solve(page, q);
    const last = mand[mand.length - 1];
    await fillQuestion(page, last);
    await submit(page, last.path);
    await expect(page.locator(".modal")).toBeVisible({ timeout: 30_000 });
    issues.push(...(await overflow(page, `модалка конверта ${stage.n + 1}`)));
    await envelopeOpened(page);
  }
  issues.push(...(await overflow(page, "этап 4")));
  await page.locator("details.passed").evaluateAll((ds) => ds.forEach((d) => ((d as HTMLDetailsElement).open = true)));
  issues.push(...(await overflow(page, "пройденные этапы раскрыты")));
  await page.goto("/lab/");
  const E = A.lab.find((x) => x.object === "station_cam")!;
  await page.locator(".lab-form__grid select").nth(0).selectOption(E.object);
  issues.push(...(await overflow(page, "lab параметры")));
  await labAll(page, A, 4, done);
  await page.goto("/lab/");
  await page.locator(".lab-archive__item.is-done button").first().click();
  issues.push(...(await overflow(page, "lab результат + архив")));
  // документы-экспертизы в окне
  await page.goto("/");
  const labDoc = page.locator(".docs-panel button.docs__link").first();
  if (await labDoc.count()) {
    await labDoc.click();
    issues.push(...(await overflow(page, "окно документа экспертизы")));
    await page.locator(".modal").getByRole("button", { name: "Закрыть" }).first().click();
  }
  // финал
  await page.goto("/final/");
  issues.push(...(await overflow(page, "финал: предупреждение")));
  await page.getByRole("button", { name: "Начать финал" }).click();
  for (const path of A.finalOrder) {
    const q = A.stages[3].questions.find((x) => x.path === path)!;
    await expect(article(page, path)).toBeVisible({ timeout: 30_000 });
    issues.push(...(await overflow(page, `финал ${path}`)));
    await fillQuestion(page, q, q.wrong?.[0]);
    await submit(page, path);
  }
  await expect(page.locator("table.review")).toBeVisible({ timeout: 60_000 });
  issues.push(...(await overflow(page, "итоги")));
  await page.getByRole("button", { name: "Перейти к развязке" }).click();
  for (let i = 0; i < 3; i++) {
    issues.push(...(await overflow(page, `развязка ${i + 1}`)));
    const next = page.getByRole("button", { name: "Дальше" });
    if (await next.count()) await next.click();
  }
  console.log("ISSUES:\n" + issues.join("\n"));
  expect(issues).toEqual([]);
  expect(errors).toEqual([]);
});

test("вымышленные страницы на 360 px; справочник — 9 препаратов", async ({ page }) => {
  const errors = collectErrors(page);
  const issues: string[] = [];
  for (const slug of ["call", "gromov", "news"]) {
    await page.goto(`/p/${slug}/`);
    await page.waitForLoadState("networkidle");
    issues.push(...(await overflow(page, slug)));
  }
  for (const [slug, k] of Object.entries(KEYS)) {
    await page.goto(`/p/${slug}/#k=${k}`);
    await expect(page.locator("body[data-ready='1']")).toHaveCount(1, { timeout: 15_000 });
    issues.push(...(await overflow(page, slug)));
    if (slug === "pharma") {
      await expect(page.locator(".fs-card")).toHaveCount(9);
      await page.locator("#fs-q").fill("ё");
      issues.push(...(await overflow(page, "pharma поиск")));
    }
    if (slug === "inna") {
      await page.locator(".kd-tile__btn").first().click();
      issues.push(...(await overflow(page, "inna просмотр")));
    }
    if (slug === "video") {
      const props = page.getByRole("button", { name: /Свойства/ });
      if (await props.count()) {
        await props.click();
        issues.push(...(await overflow(page, "video свойства")));
      }
    }
  }
  await page.goto("/p/cloud/");
  issues.push(...(await overflow(page, "cloud вход")));
  const cfg = readFileSync("content/pages/cloud/page.yaml", "utf-8");
  const pw = /^password:\s*"?([^"\n#]*)"?/m.exec(cfg)![1].trim();
  await page.locator("input[name=password]").fill(pw);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.locator("body[data-ready='1']")).toHaveCount(1, { timeout: 15_000 });
  for (const link of await page.locator("[data-folder-link]").all()) {
    await link.click();
    issues.push(...(await overflow(page, `cloud папка ${await link.textContent()}`)));
  }
  console.log("ISSUES:\n" + issues.join("\n"));
  expect(issues).toEqual([]);
  expect(errors).toEqual([]);
});
