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

/** Запрос в лабораторию со страницы /lab/. → текст сообщения. */
export async function labRequest(page: Page, e: LabEntry, basis?: string) {
  const sels = page.locator(".lab-form__grid select");
  await sels.nth(0).selectOption(e.object);
  await sels.nth(1).selectOption(e.types[0]);
  const options = await sels.nth(2).locator("option").evaluateAll((els) => els.map((o) => (o as HTMLOptionElement).value));
  const b = basis ?? e.bases.find((x) => options.includes(x));
  if (!b) throw new Error(`нет основания для ${e.result}: ${e.bases}`);
  await sels.nth(2).selectOption(b);
  const inputs = page.locator(".lab-params input");
  const params = Object.values(e.params);
  for (let i = 0; i < params.length; i++) await inputs.nth(i).fill(params[i].input);
  await page.getByRole("button", { name: "Направить запрос" }).click();
  const msg = page.locator(".lab-form .q__msg");
  await expect(msg).not.toHaveText("", { timeout: 15_000 });
  return (await msg.textContent()) ?? "";
}
