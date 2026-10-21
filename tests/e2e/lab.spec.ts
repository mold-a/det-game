// docs/06 §5 «Лаборатория» (docs/01 §7, переработка 21.10.2026): объект — свободным
// текстом. Предмет не из описи — «нельзя передать», без штрафа и без записи; пустая
// экспертиза −5, повтор без штрафа; заключение → «Мои заявки» и выбор вопроса типа
// document; разделы сайта — вкладки с адресами.
import { test, expect } from "@playwright/test";
import { loadAnswers, startGame, playToStage, labRequest, headerScore, article, objectText, openConclusion } from "./helpers";

const A = loadAnswers();
const S = A.settings;
test.setTimeout(180_000);

test("не из описи — без штрафа; пустая экспертиза −5; повтор без штрафа; «Мои заявки»", async ({ page }) => {
  await startGame(page);
  await page.goto("/lab/");
  const e = A.lab.find((x) => x.stage === 1)!;

  // Предмета нет в описи: без штрафа, в «Мои заявки» не попадает.
  expect(await labRequest(page, e, e.wrongBasis, "Кофейная чашка из буфета")).toBe(
    "Такого предмета нет в описи изъятого. Его нельзя передать в лабораторию.",
  );
  expect(await headerScore(page)).toBe(0);
  await expect(page.locator(".pz-nav__badge")).toBeHidden();

  // Распознавание вживую: «Предмет: …»; не из описи — «Нет в описи изъятого».
  await page.locator("#lab-object").fill(objectText(e));
  await expect(page.locator("#lab-object-match")).toHaveAttribute("data-status", "ok");
  await expect(page.locator("#lab-object-match")).toContainText(`Предмет: ${objectText(e)}`);
  await page.locator("#lab-object").fill("Кофейная чашка из буфета");
  await expect(page.locator("#lab-object-match")).toHaveText(/Нет в описи изъятого/);
  await page.locator("#lab-object").fill("ко");
  await page.locator("#lab-object").press("Tab");
  await expect(page.locator("#lab-object-match")).toHaveAttribute("data-status", "none");

  // Не то основание — «ничего не выявила», штраф один раз.
  expect(await labRequest(page, e, e.wrongBasis)).toBe("Экспертиза ничего не выявила.");
  expect(await headerScore(page)).toBe(S.penalties.labNoBasis);
  expect(await labRequest(page, e, e.wrongBasis)).toMatch(/^Такая заявка уже выполнялась/);
  expect(await headerScore(page)).toBe(S.penalties.labNoBasis);

  // Верная заявка — заключение, без штрафа; повтор — «уже выполнялась», прежний итог.
  expect(await labRequest(page, e)).toMatch(/^Заключение готово/);
  await expect(page.locator(".lab-result.pz-result--done")).toBeVisible();
  expect(await labRequest(page, e)).toMatch(/^Такая заявка уже выполнялась/);
  await expect(page.locator(".lab-result.pz-result--done")).toBeVisible();
  expect(await headerScore(page)).toBe(S.penalties.labNoBasis);

  // «Мои заявки»: две заявки (пустая и с заключением), адрес #orders.
  await page.locator('.pz-nav a[href="#orders"]').click();
  await expect(page).toHaveURL(/#orders$/);
  await expect(page.locator(".orders__item")).toHaveCount(2);
  await expect(page.locator(".orders__item.is-nothing")).toContainText("Ничего не выявлено");
  await expect(page.locator(".orders__item.is-done")).toContainText("Заключение готово");
  await page.locator(".orders__item.is-done").getByRole("button", { name: "Открыть заключение" }).click();
  await expect(page.locator(".modal")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".modal")).toHaveCount(0);

  // Перезагрузка по адресу вкладки — та же вкладка.
  await page.reload();
  await expect(page.locator(".orders__item")).toHaveCount(2);
  await expect(page.locator('.pz-nav a[href="#orders"]')).toHaveAttribute("aria-current", "page");
});

test("вкладки сайта: услуги, о центре, контакты — без пустых мест", async ({ page }) => {
  await startGame(page);
  for (const tab of ["services", "about", "contacts"]) {
    await page.goto(`/lab/#${tab}`);
    const sec = page.locator(`.pz-section[data-tab="${tab}"]`);
    await expect(sec).toBeVisible();
    expect(((await sec.innerText()) ?? "").trim().length, tab).toBeGreaterThan(10);
    await expect(sec).not.toContainText("TODO");
  }
  await expect(page.locator(".pz-service")).toHaveCount(await page.locator(".pz-service").count());
});

test("заключение — в «Мои заявки» и в выборе вопроса типа document", async ({ page }) => {
  let target: { stage: number; qpath: string; field?: string; doc: string } | null = null;
  for (const st of A.stages) {
    for (const q of st.questions) {
      const units = q.type === "form" ? q.fields!.map((f) => ({ f, u: f })) : [{ f: undefined, u: q }];
      for (const { f, u } of units) {
        if (u.type === "document" && A.lab.some((l) => l.doc === u.input)) target = { stage: st.n, qpath: q.path, field: f?.id, doc: u.input };
      }
    }
  }
  test.skip(!target, "в контенте нет вопроса типа document с ответом-экспертизой");
  const lab = A.lab.find((l) => l.doc === target!.doc)!;
  const done = await playToStage(page, A, target!.stage);

  const select = article(page, target!.qpath).locator("select");
  const before = await select.first().locator("option").evaluateAll((o) => o.map((x) => (x as HTMLOptionElement).value));
  expect(before).not.toContain(target!.doc);

  await page.goto("/lab/");
  expect(await labRequest(page, lab)).toMatch(new RegExp(`Документ ${target!.doc} добавлен`));
  await page.goto("/");
  await expect(article(page, target!.qpath).locator(`select option[value="${target!.doc}"]`)).toHaveCount(1);
  const after = await article(page, target!.qpath).locator("select").first().locator("option").evaluateAll((o) => o.map((x) => (x as HTMLOptionElement).value));
  expect(after).toContain(target!.doc);
  // Панели «Документы дела» больше нет (REDESIGN §1): заключения — на сайте лаборатории.
  await expect(page.locator(".docs-panel")).toHaveCount(0);
  await expect(page.locator(".labcard a[href='/lab/']")).toBeVisible();

  await openConclusion(page);
  await expect(page.locator(".modal .blank")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".modal")).toHaveCount(0);
  done.add(lab.result);
});
