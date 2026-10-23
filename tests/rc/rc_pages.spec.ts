// RC-проход вымышленных страниц на 360 и 1280 px: открытие как по QR, битые картинки, прокрутка, ошибки консоли,
// внешние запросы, все href, голосовые, видео (VD-1 «Закулисье» у Лёвина, VD-3 у Горенковой), поиск «Круга»,
// облако по паролю → auction по ссылке из облака.
import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { watch, shot, brokenImages, placeholders, noHScroll } from "./rc_util";

const answers = JSON.parse(readFileSync("tests/.answers.json", "utf8"));
type PageInfo = { slug: string; access: "open" | "key" | "password"; url: string; key?: string; password?: string };
const PAGES: PageInfo[] = answers.pages;
const BY: Record<string, PageInfo> = Object.fromEntries(PAGES.map((p) => [p.slug, p]));
test.setTimeout(600_000);

async function openPage(page: Page, p: PageInfo) {
  await page.goto(p.url);
  if (p.access === "password") {
    await page.locator('input[name="password"]').fill(p.password!);
    await page.getByRole("button", { name: "Войти" }).click();
  }
  if (p.access !== "open") await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 20000 });
  else await page.waitForLoadState("load");
}

/** Все href открытой страницы: внутренние проверяются запросом, хэш-ссылки — наличием цели. */
async function checkLinks(page: Page, label: string, seen: Map<string, string>) {
  const hrefs: string[] = await page.evaluate(() =>
    Array.from(document.querySelectorAll("a[href]")).map((a) => (a as HTMLAnchorElement).getAttribute("href") || ""),
  );
  const bad: string[] = [];
  for (const href of new Set(hrefs)) {
    if (!href || href === "#") {
      bad.push(`пустая ссылка «${href}»`);
      continue;
    }
    if (/^(mailto:|tel:|javascript:)/.test(href)) continue;
    const abs = new URL(href, page.url());
    if (abs.origin !== new URL(page.url()).origin) {
      bad.push(`внешняя ссылка ${href}`);
      continue;
    }
    if (href.startsWith("#")) {
      const ok = await page.evaluate((id) => !!document.getElementById(decodeURIComponent(id)), href.slice(1));
      if (!ok) bad.push(`нет цели якоря ${href}`);
      continue;
    }
    const key = abs.origin + abs.pathname + abs.search;
    if (!seen.has(key)) {
      const r = await page.request.get(key);
      seen.set(key, r.status() >= 400 ? `HTTP ${r.status()}` : "ok");
    }
    if (seen.get(key) !== "ok") bad.push(`${href} → ${seen.get(key)}`);
  }
  return bad.map((b) => `${label}: ${b}`);
}

const VIEWS = [
  [360, 780],
  [1280, 900],
] as const;

for (const [w, h] of VIEWS) {
  test.describe(`страницы ${w}px`, () => {
    test.use({ viewport: { width: w, height: h }, hasTouch: w < 500 });

    test("каждая страница: картинки, прокрутка, консоль, внешние запросы, ссылки", async ({ page }) => {
      const wt = watch(page);
      const seen = new Map<string, string>();
      const issues: string[] = [];
      const weights: string[] = [];
      for (const p of PAGES) {
        const startBytes = new Set(wt.bytes.keys());
        await openPage(page, p);
        const imgs = await brokenImages(page);
        if (imgs.length) issues.push(`${p.slug}: битые картинки ${imgs.join(" | ")}`);
        const ph = await placeholders(page);
        if (ph.length) issues.push(`${p.slug}: заглушки/мусор ${ph.join(" | ")}`);
        const [sw, iw] = await page.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
        if (sw > iw) issues.push(`${p.slug}: горизонтальная прокрутка ${sw} > ${iw}`);
        issues.push(...(await checkLinks(page, p.slug, seen)));
        await shot(page, `pages-${w}-${p.slug}`);
        let b = 0;
        for (const [u, n] of wt.bytes) if (!startBytes.has(u)) b += n;
        weights.push(`${p.slug}: ${(b / 1024).toFixed(0)} КБ`);
      }
      console.log(`RC ${w}px страницы (докачано, без кэша между страницами): ${weights.join("; ")}`);
      expect(issues).toEqual([]);
      expect(wt.problems).toEqual([]);
    });

    test("голосовые играют (все страницы с .kr-voice и call)", async ({ page }) => {
      const wt = watch(page);
      const issues: string[] = [];
      let played = 0;
      for (const p of PAGES.filter((x) => x.access === "open")) {
        await openPage(page, p);
        const voices = page.locator('[data-player="audio"], .kr-voice');
        const n = await voices.count();
        for (let i = 0; i < n; i++) {
          const v = voices.nth(i);
          const btn = v.locator('[data-act="play"]').first();
          if (!(await btn.count())) continue;
          if (await v.getAttribute("data-missing")) {
            issues.push(`${p.slug}: голосовое #${i} без файла (data-missing)`);
            continue;
          }
          await btn.scrollIntoViewIfNeeded();
          await btn.click();
          const ok = await expect
            .poll(() => v.evaluate((el) => !!el.querySelector("audio") && (el.querySelector("audio") as HTMLAudioElement).currentTime > 0), { timeout: 8000 })
            .toBe(true)
            .then(() => true, () => false);
          if (!ok) issues.push(`${p.slug}: голосовое #${i} не воспроизводится (currentTime=0)`);
          else played++;
          const err = await v.evaluate((el) => (el.querySelector("audio") as HTMLAudioElement | null)?.error?.code ?? null);
          if (err) issues.push(`${p.slug}: голосовое #${i} audio.error=${err}`);
          await btn.click(); // пауза
        }
        if (n && p.slug === "call") await shot(page, `voice-${w}-call`, false);
      }
      console.log(`RC ${w}px: голосовых проиграно ${played}`);
      expect(issues).toEqual([]);
      expect(played).toBeGreaterThan(0);
      expect(wt.problems.filter((x) => !x.startsWith("requestfailed"))).toEqual([]);
    });

    test("видео: VD-1 (krug-levin) и VD-3 (krug-marina) играют", async ({ page }) => {
      const wt = watch(page);
      for (const slug of ["krug-levin", "krug-marina"]) {
        await openPage(page, BY[slug]);
        const video = page.locator("video.kr-video__el").first();
        await expect(video).toHaveCount(1);
        await expect(page.getByText("Видео недоступно")).toHaveCount(0);
        await video.scrollIntoViewIfNeeded();
        await shot(page, `video-${w}-${slug}-closed`, false);
        await video.focus();
        await page.keyboard.press("Space");
        await expect
          .poll(() => video.evaluate((v: HTMLVideoElement) => (!v.paused || v.ended) && v.currentTime > 0), { timeout: 15000, message: `${slug}: видео не играет` })
          .toBe(true);
        const info = await video.evaluate((v: HTMLVideoElement) => ({ err: v.error?.code ?? null, dur: v.duration, w: v.videoWidth, h: v.videoHeight, rs: v.readyState }));
        expect(info.err, `${slug} video.error`).toBeNull();
        expect(info.w).toBeGreaterThan(0);
        console.log(`RC ${w}px ${slug}: ${JSON.stringify(info)}`);
        await shot(page, `video-${w}-${slug}-playing`, false);
        await noHScroll(page);
      }
      expect(wt.problems.filter((x) => !x.startsWith("requestfailed"))).toEqual([]);
    });

    test("поиск «Круга», переходы по карточкам и ссылкам между страницами", async ({ page }) => {
      const wt = watch(page);
      await openPage(page, BY["krug"]);
      const q = page.locator("#kr-q");
      await q.fill("Гор");
      const items = page.locator(".kr-person:not([hidden])");
      await expect(items.first()).toBeVisible();
      const n = await items.count();
      expect(n).toBeGreaterThan(0);
      await shot(page, `krug-${w}-search-gor`, false);
      await q.fill("Zzzzqq");
      await expect(items).toHaveCount(0);
      await shot(page, `krug-${w}-search-none`, false);
      await q.fill("горенк");
      await expect(items.first()).toBeVisible();
      await page.getByRole("button", { name: "Сбросить" }).click();
      await expect(items).toHaveCount(0);
      // Переходы: каждая карточка человека ведёт на открывающуюся страницу
      await q.fill("а");
      const hrefs = await page.locator(".kr-person:not([hidden]) a").evaluateAll((as) => as.map((a) => a.getAttribute("href")));
      expect(hrefs.length).toBeGreaterThan(5);
      for (const href of hrefs) {
        const r = await page.goto(href!);
        expect(r!.status(), href!).toBeLessThan(400);
        await expect(page.locator(".kr-post, .kr-bar").first()).toBeVisible();
        // шапка ведёт обратно в «Круг»
        await expect(page.locator('a.kr-logo[href="/p/krug/"]').first()).toBeVisible();
      }
      await page.locator('a.kr-logo[href="/p/krug/"]').first().click();
      await expect(page).toHaveURL(/\/p\/krug\/$/);
      expect(wt.problems.filter((x) => !x.startsWith("requestfailed"))).toEqual([]);
    });

    test("облако по паролю → auction по ссылке из облака", async ({ page }) => {
      const wt = watch(page);
      const p = BY["cloud"];
      await page.goto(p.url);
      await shot(page, `cloud-${w}-login`, false);
      await page.locator('input[name="password"]').fill("не-тот");
      await page.getByRole("button", { name: "Войти" }).click();
      await expect(page.getByText("Неверный пароль")).toBeVisible({ timeout: 15000 });
      await shot(page, `cloud-${w}-wrong`, false);
      await page.locator('input[name="password"]').fill(`  ${p.password!.toUpperCase()} `);
      await page.getByRole("button", { name: "Войти" }).click();
      await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 20000 });
      expect(await brokenImages(page)).toEqual([]);
      await shot(page, `cloud-${w}-open`);
      const link = page.locator('a[href*="/p/auction/"]').first();
      await expect(link).toHaveCount(1);
      await link.scrollIntoViewIfNeeded();
      await shot(page, `cloud-${w}-auction-link`, false);
      await link.click();
      await expect(page).toHaveURL(/\/p\/auction\/#k=/);
      await expect(page.locator("body")).toHaveAttribute("data-ready", "1", { timeout: 20000 });
      expect(await brokenImages(page)).toEqual([]);
      await shot(page, `auction-${w}-from-cloud`);
      expect(wt.problems.filter((x) => !x.startsWith("requestfailed"))).toEqual([]);
    });

    test("закрытая страница без ключа и с испорченным ключом: «Ссылка повреждена»", async ({ page }) => {
      for (const slug of ["auction", "inna", "pharma", "video"]) {
        const p = BY[slug];
        for (const suffix of ["", "#k=AAAA", "#k=" + p.key!.slice(0, -2) + "xx"]) {
          await page.goto(`/p/${slug}/${suffix}`);
          await expect(page.getByText("Ссылка повреждена")).toBeVisible({ timeout: 15000 });
        }
      }
      await shot(page, `closed-${w}-broken`, false);
    });
  });
}
