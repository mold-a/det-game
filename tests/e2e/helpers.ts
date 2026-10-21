// Общие шаги сквозных тестов системы расследования. Ответы берутся из
// tests/.answers.json (python -m engine dump-answers), а не из кода (docs/06).
import { readFileSync } from "node:fs";
import { expect, type Page, type Locator } from "@playwright/test";

export type Field = { path: string; id: string; type: string; input: any; wrong: any[] };
export type Question = Field & { kind: string; fields?: Field[] };
export type LabEntry = {
  result: string; object: string; types: string[]; stage: number; bases: string[];
  params: Record<string, { input: string }>; doc: string | null; wrongBasis: string;
};
export type Answers = {
  settings: any;
  stages: { n: number; envelope: number; questions: Question[] }[];
  finalOrder: string[];
  lab: LabEntry[];
  expected: { maxScore: number; perfectRunScore: number };
};

export function loadAnswers(): Answers {
  return JSON.parse(readFileSync("tests/.answers.json", "utf-8"));
}

export const article = (page: Page, path: string) => page.locator(`article[data-path="${path}"]`);

/** Счёт в шапке как число (типографский минус → «-»). */
export async function headerScore(page: Page): Promise<number> {
  const t = (await page.locator(".score__value").textContent()) ?? "0";
  return Number(t.replace("−", "-").replace("+", ""));
}

/** Новая игра в чистом браузере: название команды → «Открыть дело» → конверт №1. */
export async function startGame(page: Page, team = "Тестовая команда") {
  await page.goto("/");
  await page.locator("#team").fill(team);
  await page.getByRole("button", { name: "Открыть дело" }).click();
  await envelopeOpened(page);
  await expect(page.locator("#stage-title")).toHaveText("Этап 1");
}

/** Окно «Откройте конверт №N» → «Конверт вскрыт». */
export async function envelopeOpened(page: Page) {
  const modal = page.locator(".modal");
  await expect(modal).toBeVisible({ timeout: 30_000 });
  await modal.getByRole("button", { name: "Конверт вскрыт" }).click();
  await expect(modal).toHaveCount(0);
}

/** Ввести значение единицы в контейнер (участок вопроса или поле формы). */
export async function fillUnit(scope: Locator, type: string, value: any) {
  switch (type) {
    case "text":
    case "time":
    case "date":
    case "number":
      await scope.locator("input.input").fill(String(value));
      return;
    case "choice":
    case "person":
      await scope.locator(`input[value="${value}"]`).check({ force: true });
      return;
    case "multi":
    case "persons":
      for (const id of value as string[]) await scope.locator(`input[value="${id}"]`).check({ force: true });
      return;
    case "document":
      await scope.locator("select").selectOption(String(value));
      return;
    case "order": {
      const target = value as string[];
      for (let i = 0; i < target.length; i++) {
        for (;;) {
          const ids = await scope.locator(".order__item").evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.id));
          const j = ids.indexOf(target[i]);
          if (j <= i) break;
          await scope.locator(`.order__item[data-id="${target[i]}"] .order__move`).first().click();
        }
      }
      return;
    }
    default:
      throw new Error(`тип ${type}`);
  }
}

/** Заполнить вопрос (форма — все поля) значениями values (по умолчанию — верными). */
export async function fillQuestion(page: Page, q: Question, values?: any) {
  const a = article(page, q.path);
  if (q.type === "form") {
    const fields = a.locator(".q__body .field");
    for (let i = 0; i < q.fields!.length; i++) {
      const f = q.fields![i];
      await fillUnit(fields.nth(i), f.type, values ? values[f.id] : f.input);
    }
  } else {
    await fillUnit(a, q.type, values === undefined ? q.input : values);
  }
}

export async function submit(page: Page, path: string) {
  await article(page, path).locator('button[type="submit"]').click();
}

/** Верно ответить на вопрос этапа и дождаться штампа (или окна конверта). */
export async function solve(page: Page, q: Question) {
  await fillQuestion(page, q);
  await submit(page, q.path);
  await expect(article(page, q.path)).toHaveClass(/q--solved/, { timeout: 30_000 });
}

/**
 * Текст, которым команда называет объект в заявке: название объекта из описи
 * (dump-answers: objectTitle; до него — часть title результата до «: »).
 */
export function objectText(e: LabEntry): string {
  const any = e as any;
  return any.objectTitle ?? any.object_title ?? String(any.title ?? e.object).split(": ")[0];
}

/** Сообщение формы заявки после отправки. */
export async function labMessage(page: Page) {
  const msg = page.locator(".lab-form .lab-msg");
  await expect(msg).not.toHaveText("", { timeout: 15_000 });
  return ((await msg.textContent()) ?? "").trim();
}

/**
 * Заявка в лабораторию со страницы /lab/ (вкладка «Новая заявка»): объект — текстом,
 * вид, основание, параметры. → текст сообщения. text — свой текст объекта.
 */
export async function labRequest(page: Page, e: LabEntry, basis?: string, text?: string) {
  if (!(await page.locator("#lab-object").isVisible())) await page.locator('.pz-nav a[href="#order"]').click();
  await page.locator("#lab-object").fill(text ?? objectText(e));
  await page.locator("#lab-type").selectOption(e.types[0]);
  const options = await page.locator("#lab-basis option").evaluateAll((els) => els.map((o) => (o as HTMLOptionElement).value));
  const b = basis ?? e.bases.find((x) => options.includes(x));
  if (!b) throw new Error(`нет основания для ${e.result}: ${e.bases}`);
  await page.locator("#lab-basis").selectOption(b);
  const inputs = page.locator(".lab-params input");
  const params = Object.values(e.params);
  const shown = await inputs.count(); // параметры есть, только если объект распознан
  for (let i = 0; i < Math.min(shown, params.length); i++) await inputs.nth(i).fill(params[i].input);
  const msg = page.locator(".lab-form .lab-msg");
  await msg.evaluate((el) => (el.textContent = ""));
  await page.getByRole("button", { name: "Направить заявку" }).click();
  return labMessage(page);
}

/** Пройти этапы 1..target-1 без ошибок (с экспертизами каждого этапа); остановиться на этапе target. */
export async function playToStage(page: Page, A: Answers, target: number, done = new Set<string>()) {
  await startGame(page);
  for (const stage of A.stages.filter((s) => s.n < target)) {
    await labAll(page, A, stage.n, done);
    for (const q of stage.questions.filter((x) => x.kind === "bonus")) await solve(page, q);
    const mand = stage.questions.filter((x) => x.kind === "mandatory");
    for (const q of mand.slice(0, -1)) await solve(page, q);
    const last = mand[mand.length - 1];
    await fillQuestion(page, last);
    await submit(page, last.path);
    await envelopeOpened(page);
    await expect(page.locator("#stage-title")).toHaveText(`Этап ${stage.n + 1}`);
  }
  return done;
}

/** Все экспертизы этапов ≤ n, которых ещё нет в done (через /lab/), затем возврат на «/». */
export async function labAll(page: Page, A: Answers, n: number, done: Set<string>) {
  const todo = A.lab.filter((x) => x.stage <= n && !done.has(x.result));
  if (!todo.length) return;
  await page.goto("/lab/#order");
  await expect(page.locator(".lab-form")).toBeVisible();
  for (const e of todo) {
    const msg = await labRequest(page, e);
    expect(msg, e.result).toMatch(/^Заключение готово/);
    done.add(e.result);
  }
  await page.goto("/");
  await expect(page.locator("#stage-title")).toBeVisible();
}

/** «Мои заявки» на сайте лаборатории: открыть заключение (по умолчанию — самой новой выполненной заявки). */
export async function openConclusion(page: Page, hasText?: string) {
  await page.goto("/lab/#orders");
  const item = page.locator(".orders__item.is-done", hasText ? { hasText } : {}).first();
  await item.getByRole("button", { name: "Открыть заключение" }).click();
  await expect(page.locator(".modal")).toBeVisible();
}

/** Записи журнала баллов: [{ reason, delta }]. */
export async function scoreLog(page: Page) {
  const log = page.locator(".side .scorelog");
  if (!(await log.evaluate((d) => (d as HTMLDetailsElement).open))) await log.locator("summary").click();
  return log.locator("tbody tr").evaluateAll((rows) =>
    rows.map((r) => ({
      reason: r.querySelector(".scorelog__reason")?.textContent ?? "",
      delta: Number((r.querySelector(".scorelog__delta")?.textContent ?? "0").replace("−", "-").replace("+", "")),
    })),
  );
}
