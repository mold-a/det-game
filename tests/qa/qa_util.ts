// Общие утилиты QA-тестов (поверх tests/e2e/helpers.ts).
import { expect, type Page } from "@playwright/test";

export const STORE_KEY = "detgame:zakulisami";

/** Прогресс из localStorage как объект. */
export async function readState(page: Page): Promise<any> {
  return page.evaluate((k) => JSON.parse(localStorage.getItem(k) || "null"), STORE_KEY);
}

export async function writeState(page: Page, s: any) {
  await page.evaluate(([k, v]) => localStorage.setItem(k, v), [STORE_KEY, JSON.stringify(s)] as const);
}

export const sumLog = (s: any) => (s?.log ?? []).reduce((a: number, e: any) => a + e.d, 0);

/** Текст сообщения участка вопроса. */
export function qMsg(page: Page, path: string) {
  return page.locator(`article[data-path="${path}"] .q__msg`).first();
}

/** Собрать console.error и pageerror страницы. */
export function collectErrors(page: Page) {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(`console: ${m.text()}`);
  });
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  return errors;
}

/** Ждать окончания проверки (кнопка снова «Проверить»/не занята). */
export async function waitIdle(page: Page, path: string) {
  await expect(page.locator(`article[data-path="${path}"] button[aria-busy="true"]`)).toHaveCount(0, { timeout: 30_000 });
}
