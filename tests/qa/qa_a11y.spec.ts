// QA: доступность — клавиатура (order ↑/↓, persons), подписи полей (дерево доступности
// Chromium), aria-live для результатов, контраст текста в светлой и тёмной теме (docs/05 §1, §3).
import { test, expect, type Page } from "@playwright/test";
import { loadAnswers, startGame, playToStage, article, openConclusion, reachQuestion } from "../e2e/helpers";

const A = loadAnswers();
test.setTimeout(300_000);

/** Интерактивные узлы без доступного имени (по дереву доступности Chromium). */
async function unnamedControls(page: Page) {
  const cdp = await page.context().newCDPSession(page);
  const { nodes } = (await cdp.send("Accessibility.getFullAXTree")) as any;
  const roles = new Set(["textbox", "checkbox", "radio", "combobox", "button", "link", "searchbox", "spinbutton", "slider", "listbox"]);
  const out: string[] = [];
  for (const n of nodes) {
    if (n.ignored) continue;
    const role = n.role?.value;
    if (!roles.has(role)) continue;
    const name = (n.name?.value ?? "").trim();
    if (!name) out.push(`${role} (backendId ${n.backendDOMNodeId})`);
  }
  await cdp.detach();
  return out;
}

/** Текстовые элементы с контрастом ниже AA (4.5 / 3 для крупного). */
async function lowContrast(page: Page) {
  return page.evaluate(() => {
    const parse = (c: string) => {
      const cs = c.match(/color\(srgb ([^)]+)\)/);
      if (cs) {
        const p = cs[1].split(/[ ,/]+/).filter(Boolean).map(Number);
        return { r: p[0] * 255, g: p[1] * 255, b: p[2] * 255, a: p.length > 3 ? p[3] : 1 };
      }
      const m = c.match(/rgba?\(([^)]+)\)/);
      if (!m) return null;
      const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
      return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
    };
    const lum = (c: any) => {
      const f = (v: number) => {
        v /= 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
      };
      return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
    };
    const blend = (top: any, bottom: any) => ({
      r: top.r * top.a + bottom.r * (1 - top.a),
      g: top.g * top.a + bottom.g * (1 - top.a),
      b: top.b * top.a + bottom.b * (1 - top.a),
      a: 1,
    });
    const bgOf = (el: Element | null): any => {
      const chain: any[] = [];
      for (let e = el; e; e = e.parentElement) {
        const cs = getComputedStyle(e);
        if (cs.backgroundImage && cs.backgroundImage !== "none") return null; // картинка/градиент — не оцениваем
        const c = parse(cs.backgroundColor);
        if (c && c.a > 0) {
          chain.push(c);
          if (c.a >= 1) break;
        }
      }
      let acc = { r: 255, g: 255, b: 255, a: 1 };
      for (let i = chain.length - 1; i >= 0; i--) acc = blend(chain[i], acc);
      return acc;
    };
    const res: string[] = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const seen = new Set<Element>();
    for (let t = walker.nextNode(); t; t = walker.nextNode()) {
      const el = t.parentElement;
      if (!el || seen.has(el) || !(t.textContent || "").trim()) continue;
      seen.add(el);
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      if (r.width === 0 || r.height === 0 || cs.visibility === "hidden" || cs.display === "none") continue;
      if (el.closest("[hidden], .visually-hidden, [aria-hidden='true'], .stamp")) continue;
      if (Number(cs.opacity) < 1) continue;
      const fg = parse(cs.color);
      const bg = bgOf(el);
      if (!fg || !bg) continue;
      const f = blend(fg, bg);
      const L1 = lum(f);
      const L2 = lum(bg);
      const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      const size = parseFloat(cs.fontSize);
      const bold = Number(cs.fontWeight) >= 700;
      const large = size >= 24 || (bold && size >= 18.66);
      const need = large ? 3 : 4.5;
      if (ratio < need) res.push(`${ratio.toFixed(2)} < ${need}: <${el.tagName.toLowerCase()} class="${el.className}"> «${(t.textContent || "").trim().slice(0, 40)}» ${cs.color} on rgb(${Math.round(bg.r)},${Math.round(bg.g)},${Math.round(bg.b)})`);
    }
    return res;
  });
}

test("order: ↑/↓ с клавиатуры, фокус остаётся, проверка Enter", async ({ page }) => {
  await startGame(page);
  const q = A.stages[0].questions.find((x) => x.type === "order")!;
  await reachQuestion(page, A, q.path); // вопросы открываются по одному
  const a = article(page, q.path);
  const ids = () => a.locator(".order__item").evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.id));
  const before = await ids();
  // Tab до первой кнопки «Ниже»
  await a.locator(".order__item").first().locator(".order__move").nth(1).focus();
  await page.keyboard.press("Enter");
  const after = await ids();
  expect(after[1]).toBe(before[0]);
  expect(await page.evaluate(() => document.activeElement?.getAttribute("aria-label"))).toContain("Ниже");
  await page.keyboard.press(" ");
  expect((await ids())[2]).toBe(before[0]);
  // Shift+Tab → «Выше» той же карточки
  await page.keyboard.press("Shift+Tab");
  expect(await page.evaluate(() => document.activeElement?.getAttribute("aria-label"))).toContain("Выше");
  await page.keyboard.press("Enter");
  expect((await ids())[1]).toBe(before[0]);
  // live-область сообщила позицию
  await expect(page.locator("body > .visually-hidden[aria-live]")).toHaveText(/Позиция 2 из/);
  // решить вопрос только клавиатурой: «Выше»/«Ниже» до верного порядка
  const target = q.input as string[];
  for (let i = 0; i < target.length; i++) {
    for (;;) {
      const cur = await ids();
      const j = cur.indexOf(target[i]);
      if (j <= i) break;
      await a.locator(`.order__item[data-id="${target[i]}"] .order__move`).first().focus();
      await page.keyboard.press("Enter");
    }
  }
  await a.locator('button[type="submit"]').focus();
  await page.keyboard.press("Enter");
  await expect(a).toHaveClass(/q--solved/, { timeout: 30_000 });
});

test("persons и форма: выбор с клавиатуры, все поля подписаны", async ({ page }) => {
  await playToStage(page, A, 2);
  const q = A.stages[1].questions.find((x) => x.type === "persons")!;
  await reachQuestion(page, A, q.path);
  const a = article(page, q.path);
  const boxes = a.locator("input[type=checkbox]");
  await boxes.first().focus();
  expect(await page.evaluate(() => document.activeElement?.tagName)).toBe("INPUT");
  await page.keyboard.press(" ");
  await expect(boxes.first()).toBeChecked();
  await page.keyboard.press("Tab");
  await page.keyboard.press(" ");
  await expect(boxes.nth(1)).toBeChecked();
  // фокус виден (outline/box-shadow)
  const ring = await page.evaluate(() => {
    const el = document.activeElement as HTMLElement;
    const lab = el.closest("label") as HTMLElement;
    const s = getComputedStyle(el);
    const ls = lab ? getComputedStyle(lab) : null;
    return [s.outlineStyle, s.outlineWidth, s.boxShadow, ls?.outlineStyle, ls?.boxShadow].join(" | ");
  });
  console.log("focus ring persons:", ring);
  expect(await unnamedControls(page)).toEqual([]);
  await page.goto("/lab/");
  await page.locator("#lab-type").selectOption({ index: 1 });
  expect(await unnamedControls(page)).toEqual([]);
});

test("aria-live: сообщение проверки объявляется", async ({ page }) => {
  await startGame(page);
  const q = A.stages[0].questions.find((x) => x.type === "order")!;
  await reachQuestion(page, A, q.path);
  await article(page, q.path).locator('button[type="submit"]').click();
  await expect(page.locator("body > .visually-hidden[aria-live]")).toHaveText("Ответ не подтверждается материалами дела.", { timeout: 30_000 });
  const live = await article(page, q.path).locator(".q__msg").evaluate((m) => [m.getAttribute("role"), m.getAttribute("aria-live")]);
  expect(live).toEqual(["status", "polite"]);
});

for (const scheme of ["light", "dark"] as const) {
  test(`контраст текста AA, тема ${scheme}`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    const report: string[] = [];
    await page.goto("/");
    report.push(...(await lowContrast(page)).map((x) => `/ intro: ${x}`));
    await startGame(page);
    const q = A.stages[0].questions.find((x) => x.type === "order")!;
    await reachQuestion(page, A, q.path);
    await article(page, q.path).locator('button[type="submit"]').click();
    await expect(article(page, q.path).locator(".q__msg")).not.toHaveText("", { timeout: 30_000 });
    await page.locator(".scorelog summary").click();
    report.push(...(await lowContrast(page)).map((x) => `/: ${x}`));
    await page.goto("/lab/");
    await page.locator("#lab-type").selectOption({ index: 1 });
    await page.getByRole("button", { name: "Направить заявку" }).click();
    report.push(...(await lowContrast(page)).map((x) => `/lab/: ${x}`));
    await page.goto("/final/");
    report.push(...(await lowContrast(page)).map((x) => `/final/: ${x}`));
    for (const p of ["/p/call/", "/p/gromov/", "/p/news/", "/p/pharma/"]) {
      await page.goto(p);
      await page.waitForTimeout(300);
      report.push(...(await lowContrast(page)).map((x) => `${p}: ${x}`));
    }
    console.log(`CONTRAST ${scheme}:\n` + report.join("\n"));
    expect(report).toEqual([]);
  });
}

test("контраст AA в тёмной теме: модалки, лаборатория с результатом, итоги и развязка", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  const report: string[] = [];
  await playToStage(page, A, 4);
  await page.locator(".scorelog summary").click();
  await page.locator("details.passed").evaluateAll((ds) => ds.forEach((d) => ((d as HTMLDetailsElement).open = true)));
  report.push(...(await lowContrast(page)).map((x) => `/ этап 4: ${x}`));
  await page.locator(".menu summary").click();
  await page.getByRole("button", { name: "Начать заново" }).click();
  report.push(...(await lowContrast(page)).map((x) => `модалка: ${x}`));
  await page.locator(".modal").getByRole("button", { name: "Отмена" }).click();
  await openConclusion(page);
  report.push(...(await lowContrast(page)).map((x) => `/lab/ результат: ${x}`));
  await page.goto("/final/");
  report.push(...(await lowContrast(page)).map((x) => `/final/ предупреждение: ${x}`));
  await page.getByRole("button", { name: "Начать финал" }).click();
  for (const path of A.finalOrder) {
    const q = A.stages[3].questions.find((x) => x.path === path)!;
    await expect(article(page, path)).toBeVisible({ timeout: 30_000 });
    const { fillQuestion, submit } = await import("../e2e/helpers");
    await fillQuestion(page, q, q.wrong?.[0]);
    await submit(page, path);
  }
  await expect(page.locator("table.review")).toBeVisible({ timeout: 60_000 });
  report.push(...(await lowContrast(page)).map((x) => `итоги: ${x}`));
  await page.getByRole("button", { name: "Перейти к развязке" }).click();
  report.push(...(await lowContrast(page)).map((x) => `развязка: ${x}`));
  console.log("CONTRAST dark extended:\n" + report.join("\n"));
  expect(report).toEqual([]);
});
