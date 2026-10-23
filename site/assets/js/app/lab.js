// Сайт экспертного центра на «/lab/» (docs/04 «/lab/», docs/01 §7, docs/05 §2):
// своя марка и палитра, тонкая полоса заказчика сверху, разделы-вкладки
// #order, #orders, #services, #about, #contacts.
//
// Заявка: объект — свободный текст, распознаётся core/labmatch.js среди объектов
// открытых этапов; вид исследования и основание — списки; параметры появляются,
// когда текст распознан как объект с параметрами. Ключ экспертизы и отпечаток
// заявки — прежние (core/lab.js): по id объекта, а не по тексту.
//
// Тексты разделов «Услуги», «О центре», «Контакты» — из content/lab.yaml
// (переменная шаблона lab_site → <script type="application/json" id="lab-site">)
// и из types[].description каталога. Нет данных — раздел показывает короткую
// служебную строку, без пустых мест.

import { h, clear, append, announce, formatDateTime, insertTrustedHtml } from "./dom.js";
import { T, signed } from "./texts.js";
import { renderDocument } from "./docview.js";
import { alertDialog, openModal } from "./modal.js";
import { createInput } from "./questions.js";
import { prismMark } from "./prism.js";
import { initPage, loadProgress, renderLoadError } from "./context.js";
import * as S from "../core/state.js";
import { receivedDocuments } from "../core/game.js";
import { labCatalog, labFingerprint, labRequest, labDocTitles, prepareLabRequest, labOrders } from "../core/lab.js";
import { resolveObject } from "../core/labmatch.js";
import { labPhotos } from "../core/pageui.js";
// Фото крупно — то же окно, что на вымышленных страницах (нативный <dialog>, стили pages/_ui.css).
import { openZoom } from "../pages/page-ui.js";

const TABS = ["order", "orders", "services", "about", "contacts"];
/** Распознавание вживую: пауза после ввода и порог длины для «Нет в описи» (без фокуса — сразу). */
const LIVE_DELAY_MS = 250;
const LIVE_NONE_MIN = 3;

const ctx = await initPage();
const site = readLabSite();
let game = null; // { state, packs, labResults, labEntries, docs } или null — дело не открыто
let els = {};
/** Незаконченная заявка — переживает перерисовку по событию storage. */
let draft = null;

/** Данные сайта из шаблона (content/lab.yaml) или null. */
function readLabSite() {
  try {
    const raw = document.getElementById("lab-site")?.textContent;
    const data = raw ? JSON.parse(raw) : null;
    return data && typeof data === "object" ? data : null;
  } catch {
    return null;
  }
}

/** Строка из lab.yaml; заглушка «TODO(content)» считается пустой — раздел покажет нейтральную строку. */
const str = (v) => (typeof v === "string" && !v.includes("TODO(content)") ? v.trim() : "");
const siteName = () => str(site?.name) || T.lab.nameFallback;
const siteFullName = () => str(site?.full_name) || T.lab.fullNameFallback;

function currentTab() {
  const t = decodeURIComponent(location.hash.replace(/^#/, ""));
  return TABS.includes(t) ? t : "order";
}

// ================================================================== запуск

let running = null;
let again = false;

/** Запуск и перерисовка (в т. ч. по storage); вызовы не перекрываются. */
function start() {
  if (running) {
    again = true;
    return running;
  }
  running = (async () => {
    try {
      do {
        again = false;
        await startOnce();
      } while (again);
    } finally {
      running = null;
    }
  })();
  return running;
}

async function startOnce() {
  draft = readForm() ?? draft;
  const res = await loadProgress(ctx);
  if (!res.ok && res.code !== "none") return renderLoadError(ctx, res.code);
  game = res.ok ? res : null;
  render();
}

function labCtx() {
  return { stage: game.state.stage, keys: game.state.keys, packs: game.packs };
}

function commit(fn) {
  game.state = ctx.store.update(fn);
  return game.state;
}

// ================================================================== каркас сайта

function render() {
  clear(ctx.mount);
  els = {};
  document.title = siteFullName();
  const catalog = game ? labCatalog(game.packs) : { types: [], objects: [] };

  const scoreValue = h("span", { class: "score__value pz-strip__score" });
  const strip = h(
    "div",
    { class: "pz-strip", role: "region", "aria-label": T.lab.strip },
    h(
      "div",
      { class: "pz-strip__inner" },
      h(
        "p",
        { class: "pz-strip__who" },
        h("span", { class: "pz-strip__label" }, `${T.lab.customer}: `),
        h("span", { class: "pz-strip__dept" }, ctx.chrome.department || ctx.chrome.system),
        h("span", { class: "pz-strip__sep", "aria-hidden": "true" }, " · "),
        h("span", { class: "pz-strip__case" }, T.lab.caseNo(ctx.chrome.caseNo)),
      ),
      game
        ? h("p", { class: "score pz-strip__scorebox", role: "status", "aria-live": "polite" }, h("span", { class: "score__label" }, T.lab.score), " ", scoreValue)
        : null,
      h("a", { class: "pz-strip__back", href: "/" }, h("span", { "aria-hidden": "true" }, "← "), T.lab.back),
    ),
  );

  const navLinks = {};
  const nav = h(
    "nav",
    { class: "pz-nav", "aria-label": T.lab.nav },
    h(
      "ul",
      { class: "pz-nav__list" },
      TABS.map((id) => {
        const badge = id === "orders" ? h("span", { class: "pz-nav__badge" }) : null;
        const a = h("a", { class: "pz-nav__link", href: `#${id}`, dataset: { tab: id } }, h("span", null, T.lab.tabs[id]), badge);
        navLinks[id] = { a, badge };
        return h("li", null, a);
      }),
    ),
  );

  const header = h(
    "header",
    { class: "pz-header" },
    h(
      "div",
      { class: "pz-header__inner" },
      h(
        "a",
        { class: "pz-brand", href: "#order", "aria-label": siteFullName() },
        prismMark({ className: "prism-mark pz-brand__mark" }),
        h("span", { class: "pz-brand__text", "aria-hidden": "true" }, h("span", { class: "pz-brand__name" }, siteName()), h("span", { class: "pz-brand__full" }, siteFullName())),
      ),
      nav,
    ),
  );

  const heroTitle = h("h1", { class: "pz-hero__title", id: "pz-title", tabindex: "-1" });
  const heroLead = h("p", { class: "pz-hero__lead" });
  const hero = h(
    "section",
    { class: "pz-hero", "aria-labelledby": "pz-title" },
    h(
      "div",
      { class: "pz-hero__inner" },
      h("div", { class: "pz-hero__text" }, h("p", { class: "pz-hero__kicker" }, T.lab.cabinet), heroTitle, heroLead),
      prismMark({ className: "prism-mark pz-hero__prism" }),
    ),
  );

  const sections = {
    order: renderOrderSection(catalog),
    orders: h("section", { class: "pz-section", dataset: { tab: "orders" } }),
    services: renderServices(catalog),
    about: renderAbout(),
    contacts: renderContacts(),
  };

  const main = h(
    "main",
    { class: "pz-main", id: "main", tabindex: "-1" },
    hero,
    h("div", { class: "pz-content" }, Object.values(sections)),
  );

  const footer = h(
    "footer",
    { class: "pz-footer" },
    h(
      "div",
      { class: "pz-footer__inner" },
      h("p", { class: "pz-footer__brand" }, prismMark({ className: "prism-mark pz-footer__mark" }), h("span", null, siteFullName())),
      str(site?.contacts?.address) ? h("p", { class: "pz-footer__line" }, str(site.contacts.address)) : null,
      h("p", { class: "pz-footer__line" }, T.lab.footer),
    ),
  );

  ctx.mount.append(h("a", { class: "skip-link", href: "#main" }, T.skipToMain), strip, header, main, footer);
  Object.assign(els, { scoreValue, navLinks, sections, heroTitle, heroLead, catalog });
  // «К основному содержанию» — тоже якорь: не путать с разделами.
  ctx.mount.querySelector(".skip-link").addEventListener("click", (e) => {
    e.preventDefault();
    document.getElementById("main").focus();
  });
  updateDynamic();
  showTab(currentTab(), { focus: false });
}

/** Счёт, число заявок, раздел «Мои заявки», последние заявки рядом с формой. */
function updateDynamic() {
  if (game) {
    const total = S.score(game.state);
    els.scoreValue.textContent = total === 0 ? "0" : signed(total);
    els.scoreValue.classList.toggle("is-negative", total < 0);
  }
  const n = game?.state.lab.log.length ?? 0;
  const badge = els.navLinks.orders.badge;
  badge.textContent = n ? String(n) : "";
  badge.hidden = !n;
  renderOrders(els.sections.orders);
  renderRecent();
}

function showTab(tab, { focus = true } = {}) {
  for (const [id, sec] of Object.entries(els.sections)) sec.hidden = id !== tab;
  for (const [id, { a }] of Object.entries(els.navLinks)) {
    if (id === tab) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  els.heroTitle.textContent = tab === "order" ? T.lab.orderTitle : T.lab.tabs[tab];
  const lead =
    tab === "order"
      ? str(site?.tagline) || T.lab.orderLead
      : tab === "orders"
        ? T.lab.ordersLead
        : tab === "services"
          ? T.lab.servicesLead
          : str(site?.tagline);
  els.heroLead.textContent = lead;
  els.heroLead.hidden = !lead;
  document.body.dataset.tab = tab;
  if (focus) {
    els.heroTitle.focus({ preventScroll: true });
    if (window.scrollY > 0) window.scrollTo({ top: 0 });
  }
}

// ================================================================== новая заявка

function readForm() {
  const input = document.getElementById("lab-object");
  if (!input) return null;
  return {
    text: input.value,
    type: document.getElementById("lab-type")?.value ?? "",
    basis: document.getElementById("lab-basis")?.value ?? "",
    params: Array.from(document.querySelectorAll(".lab-params input")).map((i) => i.value),
    paramsFor: document.querySelector(".lab-params")?.dataset.object ?? "",
  };
}

function renderOrderSection(catalog) {
  const section = h("section", { class: "pz-section pz-section--order", dataset: { tab: "order" } });
  if (!game) {
    section.append(notStarted());
    return section;
  }

  const objectInput = h("input", {
    class: "pz-input",
    id: "lab-object",
    type: "text",
    autocomplete: "off",
    autocapitalize: "off",
    spellcheck: "false",
    maxlength: "120",
    "aria-describedby": "lab-object-help lab-object-match",
  });
  const match = h("p", { class: "pz-match", id: "lab-object-match", "aria-live": "polite" });
  const paramsBox = h("div", { class: "lab-params" });
  const typeSel = h(
    "select",
    { class: "pz-select", id: "lab-type" },
    h("option", { value: "" }, T.lab.choose),
    catalog.types.map((t) => h("option", { value: t.id }, t.title)),
  );
  const basisSel = h("select", { class: "pz-select", id: "lab-basis", "aria-describedby": "lab-basis-help" });
  fillBasis(basisSel);
  const msg = h("div", { class: "lab-msg q__msg", role: "status", "aria-live": "polite" });
  const submit = h("button", { type: "submit", class: "pz-btn pz-btn--primary" }, T.lab.submit);
  const result = h("section", { class: "lab-result", "aria-label": T.lab.result });

  let paramWidgets = [];
  let paramsFor = "";

  /**
   * Распознавание вживую (без штрафа и без записи — те же исходы, что при отправке):
   * «Предмет: …» — распознан; «Уточните: А или Б» — неоднозначно (кнопки подставляют
   * название); «Нет в описи изъятого» — только после ухода фокуса или от LIVE_NONE_MIN
   * символов, чтобы подпись не мигала на первых буквах. Параметры появляются у
   * распознанного объекта с параметрами.
   */
  function recognize({ final = false } = {}) {
    const text = objectInput.value.trim();
    const r = text ? resolveObject(objectInput.value, catalog.objects) : { status: "empty" };
    const obj = r.status === "ok" ? catalog.objects.find((o) => o.id === r.id) : null;
    clear(match);
    let status = r.status;
    if (status === "none" && !final && [...text].length < LIVE_NONE_MIN) status = "empty";
    match.dataset.status = status;
    match.className = `pz-match pz-match--${status}`;
    if (status === "ok") {
      append(match, [
        h("span", { class: "pz-match__label" }, `${T.lab.live.ok}: `),
        h("span", { class: "pz-match__title" }, obj.title),
        obj.ref ? h("span", { class: "pz-match__ref" }, ` (${obj.ref})`) : null,
      ]);
    } else if (status === "ambiguous") {
      const cands = r.ids.map((id) => catalog.objects.find((o) => o.id === id)).filter(Boolean);
      append(match, [
        h("span", { class: "pz-match__label" }, `${T.lab.live.ambiguous}: `),
        cands.map((o, i) => [
          i ? h("span", { class: "pz-match__or" }, i === cands.length - 1 ? ` ${T.lab.live.or} ` : ", ") : null,
          pickButton(o, "pz-match__pick"),
        ]),
      ]);
    } else if (status === "none") {
      match.append(T.lab.live.none);
    }
    match.classList.toggle("is-empty", status === "empty");
    const want = obj?.params?.length ? obj.id : "";
    if (want === paramsFor) return;
    const keep = paramWidgets.map(({ w }) => w.getValue());
    clear(paramsBox);
    paramWidgets = [];
    paramsFor = want;
    paramsBox.dataset.object = want;
    if (!want) return;
    const row = h("div", { class: "pz-params" });
    for (const p of obj.params) {
      const w = createInput({ id: p.id, path: `lab.${p.id}`, type: p.type }, { label: p.label });
      w.el.classList.add("pz-input");
      paramWidgets.push({ def: p, w });
      row.appendChild(h("label", { class: "pz-field pz-field--param" }, h("span", { class: "pz-label", "aria-hidden": "true" }, p.label), w.el));
    }
    paramWidgets.forEach(({ w }, i) => keep[i] !== undefined && w.setValue?.(keep[i]));
    paramsBox.appendChild(h("fieldset", { class: "pz-fieldset" }, h("legend", { class: "pz-label" }, T.lab.params), row));
  }

  /** Кнопка-кандидат: подставляет название предмета из описи. */
  function pickButton(o, className) {
    const b = h("button", { type: "button", class: className, "aria-label": T.lab.pick(o.title) }, o.title);
    b.addEventListener("click", () => {
      clearTimeout(liveTimer);
      objectInput.value = o.title;
      recognize({ final: true });
      say("");
      (typeSel.value ? basisSel : typeSel).focus();
    });
    return b;
  }

  let liveTimer = 0;
  objectInput.addEventListener("input", () => {
    objectInput.removeAttribute("aria-invalid");
    clearTimeout(liveTimer);
    liveTimer = setTimeout(() => recognize(), LIVE_DELAY_MS);
  });
  // Уход фокуса — с той же паузой: подпись не должна сдвинуть кнопку под курсором,
  // пока идёт щелчок по «Направить заявку» (отправка распознаёт текст сама).
  objectInput.addEventListener("blur", () => {
    clearTimeout(liveTimer);
    liveTimer = setTimeout(() => recognize({ final: true }), LIVE_DELAY_MS);
  });

  const step = (n, label, forId, extra = null) =>
    h("label", { class: "pz-label pz-label--step", for: forId }, h("span", { class: "pz-step", "aria-hidden": "true" }, String(n)), label, extra);

  const form = h(
    "form",
    { class: "lab-form pz-card pz-card--form", novalidate: true, "aria-labelledby": "pz-title" },
    h(
      "div",
      { class: "pz-field" },
      step(1, T.lab.object, "lab-object"),
      objectInput,
      h("p", { class: "pz-help", id: "lab-object-help" }, T.lab.objectHelp),
      match,
    ),
    paramsBox,
    h("div", { class: "pz-field" }, step(2, T.lab.type, "lab-type"), typeSel),
    h("div", { class: "pz-field" }, step(3, T.lab.basis, "lab-basis"), basisSel, h("p", { class: "pz-help", id: "lab-basis-help" }, T.lab.basisHelp)),
    msg,
    h("div", { class: "pz-actions" }, submit),
    h("p", { class: "pz-terms" }, T.lab.terms(ctx.pub.penalties.labNoBasis)),
  );

  // Черновик после перерисовки.
  if (draft) {
    objectInput.value = draft.text ?? "";
    typeSel.value = draft.type ?? "";
    basisSel.value = draft.basis ?? "";
  }
  recognize();
  if (draft?.params?.length && draft.paramsFor === paramsFor) paramWidgets.forEach(({ w }, i) => w.setValue?.(draft.params[i] ?? ""));
  draft = null;

  function say(text, kind = "info", extra = null) {
    msg.className = ["lab-msg", "q__msg", kind === "error" && "q__msg--error", kind === "format" && "q__msg--format"].filter(Boolean).join(" ");
    clear(msg);
    if (text) msg.append(h("p", null, text));
    if (extra) msg.append(extra);
    if (text) announce(text);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (submit.disabled) return;
    say("");
    clearTimeout(liveTimer);
    recognize({ final: true });
    paramWidgets.forEach(({ w }) => w.setInvalid(false));
    const prep = prepareLabRequest({
      text: objectInput.value,
      type: typeSel.value,
      basis: basisSel.value,
      params: paramWidgets.map(({ w }) => w.getValue()),
      objects: catalog.objects,
      resolve: resolveObject,
      defaultYear: ctx.pub.defaultYear,
    });
    switch (prep.status) {
      case "empty":
        objectInput.setAttribute("aria-invalid", "true");
        objectInput.focus();
        return say(T.lab.empty, "format");
      case "none":
        objectInput.setAttribute("aria-invalid", "true");
        clear(result);
        return say(T.lab.none, "error");
      case "ambiguous": {
        recognize({ final: true });
        const picks = h("div", { class: "pz-picks" }, prep.objects.map((o) => pickButton(o, "pz-chip")));
        return say(T.lab.ambiguous(prep.objects.map((o) => o.title)), "format", picks);
      }
      case "incomplete": {
        const m = prep.missing;
        const text = m.length > 1 ? T.lab.required.both : T.lab.required[m[0]];
        (m[0] === "type" ? typeSel : basisSel).focus();
        return say(text, "format");
      }
      case "format": {
        paramWidgets.forEach(({ def, w }) => w.setInvalid(prep.invalid.includes(def.id)));
        paramWidgets.find(({ def }) => def.id === prep.invalid[0])?.w.focus();
        return say(prep.empty ? T.format.form : T.format[prep.paramType] ?? T.format.form, "format");
      }
      default:
        break;
    }

    const req = prep.req;
    submit.disabled = true;
    submit.setAttribute("aria-busy", "true");
    submit.textContent = T.lab.sending;
    try {
      const fp = await labFingerprint(req);
      const found = await labRequest(req, labCtx());
      const logReq = { ...req, stage: game.state.stage };
      if (found) {
        let repeat = false;
        commit((s) => {
          repeat = fp in s.lab.done;
          return S.labDone(s, fp, found.entry.doc, logReq);
        });
        game.labResults[fp] = found;
        if (found.entry.doc) game.labEntries[found.entry.doc] = found.entry;
        game.docs = receivedDocuments(game.packs, game.state, labDocTitles(game.labResults));
        fillBasis(basisSel);
        showConclusion(result, found.entry, prep.object);
        say(repeat ? T.lab.repeat : found.entry.doc ? T.lab.doneDoc(found.entry.doc) : T.lab.done, "info");
      } else {
        let repeat = false;
        commit((s) => {
          repeat = S.labSeen(s, fp);
          return S.labRejected(s, fp, ctx.pub.penalties.labNoBasis, logReq);
        });
        showNothing(result, prep.object, repeat);
        say(repeat ? T.lab.repeatNothing : T.lab.nothing, "error");
      }
      updateDynamic();
    } finally {
      submit.disabled = false;
      submit.removeAttribute("aria-busy");
      submit.textContent = T.lab.submit;
    }
  });

  const aside = h("aside", { class: "pz-aside", "aria-label": T.lab.ordersTitle });
  els.recent = aside;
  section.append(h("div", { class: "pz-grid" }, h("div", { class: "pz-col" }, form, result), aside));
  return section;
}

/** Основание — только полученные документы (docs/01 §3). Выбор сохраняется. */
function fillBasis(sel) {
  const cur = sel.value;
  clear(sel);
  sel.appendChild(h("option", { value: "" }, game.docs.length ? T.lab.choose : T.lab.noDocs));
  for (const d of game.docs) sel.appendChild(h("option", { value: d.id }, `${d.id} — ${d.title}`));
  sel.value = cur;
}

/** Шапка итога заявки: объект, статус. */
function resultHead(object, ok) {
  return h(
    "div",
    { class: "pz-result__head" },
    h("span", { class: ["pz-status", ok ? "pz-status--done" : "pz-status--nothing"] }, ok ? T.lab.statusDone : T.lab.statusNothing),
    h("p", { class: "pz-result__object" }, object.title, object.ref ? h("span", { class: "pz-result__ref" }, ` · ${object.ref}`) : null),
  );
}

function showConclusion(container, entry, object) {
  clear(container);
  container.className = "lab-result pz-result pz-result--done";
  container.append(resultHead(object, true), conclusionView(entry), ordersLink());
  container.scrollIntoView({ block: "start", behavior: "smooth" });
}

function showNothing(container, object, repeat) {
  clear(container);
  container.className = "lab-result pz-result pz-result--nothing";
  append(container, [
    resultHead(object, false),
    h("p", { class: "pz-result__text" }, T.lab.nothing),
    repeat ? null : h("p", { class: "pz-result__charge" }, T.lab.charged(ctx.pub.penalties.labNoBasis)),
    ordersLink(),
  ]);
}

/**
 * Заключение на сайте центра. Документ-бланк из сборки (form) показывается как есть;
 * короткий результат без бланка (doc: null) — на фирменном листе центра.
 */
function conclusionView(entry) {
  if (entry.form) return h("div", { class: "pz-doc" }, renderDocument(entry));
  return h(
    "div",
    { class: "pz-doc pz-doc--letter" },
    h(
      "div",
      { class: "pz-letterhead" },
      prismMark({ className: "prism-mark pz-letterhead__mark" }),
      h("div", null, h("p", { class: "pz-letterhead__name" }, siteFullName()), h("p", { class: "pz-letterhead__sub" }, T.lab.conclusion)),
    ),
    h("p", { class: "pz-letterhead__title" }, entry.title),
    renderDocument(entry),
  );
}

function openConclusion(entry) {
  return openModal({
    title: entry.title,
    body: conclusionView(entry),
    className: "modal--doc",
    actions: [{ id: "ok", label: T.close, primary: true }],
  });
}

function ordersLink() {
  return h("p", { class: "pz-result__more" }, h("a", { href: "#orders" }, T.lab.toOrders));
}

function notStarted() {
  return h(
    "div",
    { class: "pz-card pz-card--notice" },
    h("p", null, T.lab.notStarted),
    h("p", { class: "pz-actions" }, h("a", { class: "pz-btn pz-btn--primary", href: "/" }, T.errors.toStart)),
  );
}

// ================================================================== мои заявки

function orderRows() {
  if (!game) return [];
  return labOrders(game.state.lab.log, els.catalog, game.labResults);
}

function openOrder(row) {
  if (row.entry) return openConclusion(row.entry);
  return alertDialog({ title: T.lab.statusDone, text: T.docs.notRestored });
}

function renderOrders(section) {
  clear(section);
  if (!game) {
    section.append(notStarted());
    return;
  }
  const rows = orderRows();
  if (!rows.length) {
    section.append(h("div", { class: "pz-card pz-card--notice" }, h("p", null, T.lab.ordersEmpty), h("p", { class: "pz-actions" }, h("a", { class: "pz-btn pz-btn--ghost", href: "#order" }, T.lab.tabs.order))));
    return;
  }
  const list = h("ol", { class: "orders", reversed: true });
  for (const r of rows) {
    const open = r.ok ? h("button", { type: "button", class: "pz-btn pz-btn--small" }, T.lab.open) : null;
    open?.addEventListener("click", () => openOrder(r));
    const params = r.params.length ? paramsText(r) : null;
    list.appendChild(
      h(
        "li",
        { class: ["orders__item", r.ok ? "is-done" : "is-nothing"] },
        h(
          "div",
          { class: "orders__meta" },
          h("span", { class: "orders__no" }, T.lab.orderNo(r.no)),
          h("span", { class: "orders__time" }, h("span", { class: "visually-hidden" }, `${T.lab.accepted}: `), formatDateTime(r.t)),
        ),
        h(
          "div",
          { class: "orders__what" },
          h("p", { class: "orders__object" }, r.objectTitle, r.ref ? h("span", { class: "orders__ref" }, ` · ${r.ref}`) : null),
          h(
            "dl",
            { class: "orders__facts" },
            h("dt", null, T.lab.colType),
            h("dd", null, r.typeTitle),
            h("dt", null, T.lab.colBasis),
            h("dd", null, basisTitle(r.basis)),
            params ? [h("dt", null, T.lab.colParams), h("dd", null, params)] : null,
          ),
        ),
        h(
          "div",
          { class: "orders__result" },
          h("span", { class: ["pz-status", r.ok ? "pz-status--done" : "pz-status--nothing"] }, r.ok ? T.lab.statusDone : T.lab.statusNothing),
          open,
        ),
      ),
    );
  }
  section.append(list);
}

/** Параметры заявки по-человечески: «<подпись> <значение> · …», дата — ДД.ММ.ГГГГ. */
function paramsText(r) {
  const defs = els.catalog.objects.find((o) => o.id === r.object)?.params ?? [];
  return r.params
    .map((v, i) => {
      const d = defs[i];
      const m = d?.type === "date" ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(v)) : null;
      const shown = m ? `${m[3]}.${m[2]}.${m[1]}` : String(v);
      return d?.label ? `${d.label} ${shown}` : shown;
    })
    .join(" · ");
}

function basisTitle(id) {
  const d = game.docs.find((x) => x.id === id);
  return d ? `${d.id} — ${d.title}` : id;
}

/** Последние заявки рядом с формой (до трёх) — быстрый доступ к заключениям. */
function renderRecent() {
  const aside = els.recent;
  if (!aside) return;
  clear(aside);
  const rows = orderRows().slice(0, 3);
  aside.append(h("h2", { class: "pz-aside__title" }, T.lab.ordersTitle));
  if (!rows.length) {
    aside.append(h("p", { class: "pz-aside__empty" }, T.lab.ordersEmpty));
  } else {
    const ul = h("ul", { class: "pz-recent" });
    for (const r of rows) {
      const body = [
        h("span", { class: "pz-recent__object" }, r.objectTitle),
        h("span", { class: "pz-recent__type" }, r.typeTitle),
        h("span", { class: ["pz-status", "pz-status--tiny", r.ok ? "pz-status--done" : "pz-status--nothing"] }, r.ok ? T.lab.statusDone : T.lab.statusNothing),
      ];
      let item;
      if (r.ok) {
        item = h("button", { type: "button", class: "pz-recent__link", "aria-label": `${T.lab.open}: ${r.objectTitle}, ${r.typeTitle}` }, body);
        item.addEventListener("click", () => openOrder(r));
      } else {
        item = h("div", { class: "pz-recent__row" }, body);
      }
      ul.appendChild(h("li", null, item));
    }
    aside.append(ul, h("p", { class: "pz-aside__more" }, h("a", { href: "#orders" }, T.lab.toOrders)));
  }
  aside.append(h("p", { class: "pz-aside__terms" }, T.lab.serviceTerms));
}

// ================================================================== услуги, о центре, контакты

function pending() {
  return h("p", { class: "pz-pending" }, T.lab.pending);
}

/** Markdown из lab.yaml без сборки HTML: абзацы, списки «- », **полужирный**, *курсив*. */
function mdLite(text) {
  const inline = (s) => {
    const out = [];
    const re = /\*\*([^*]+)\*\*|\*([^*]+)\*/g;
    let last = 0;
    for (let m = re.exec(s); m; m = re.exec(s)) {
      if (m.index > last) out.push(s.slice(last, m.index));
      out.push(m[1] !== undefined ? h("strong", null, m[1]) : h("em", null, m[2]));
      last = re.lastIndex;
    }
    if (last < s.length) out.push(s.slice(last));
    return out;
  };
  const blocks = String(text).split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean);
  return blocks.map((b) => {
    const lines = b.split("\n").map((l) => l.trim());
    if (lines.every((l) => /^[-*]\s+/.test(l))) return h("ul", null, lines.map((l) => h("li", null, inline(l.replace(/^[-*]\s+/, "")))));
    return h("p", null, inline(lines.join(" ")));
  });
}

function richText(htmlKey, mdKey) {
  const box = h("div", { class: "pz-prose" });
  if (str(site?.[htmlKey])) insertTrustedHtml(box, site[htmlKey]);
  else if (str(site?.[mdKey])) box.append(...mdLite(site[mdKey]));
  else return null;
  return box;
}

function renderServices(catalog) {
  const section = h("section", { class: "pz-section", dataset: { tab: "services" } });
  const types = catalog.types;
  // Условия (срок, основание) — одной плашкой над карточками, если они есть в lab.yaml.
  const note = str(site?.services_note);
  if (note) section.append(h("p", { class: "pz-note" }, h("span", { class: "pz-note__mark", "aria-hidden": "true" }), note));
  if (!types.length) {
    section.append(h("div", { class: "pz-card pz-card--notice" }, h("p", null, game ? T.lab.pending : T.lab.notStarted)));
  } else {
    section.append(
      h(
        "ul",
        { class: "pz-services" },
        types.map((t, i) =>
          h(
            "li",
            { class: "pz-service" },
            h("span", { class: "pz-service__no", "aria-hidden": "true" }, String(i + 1).padStart(2, "0")),
            h("h2", { class: "pz-service__title" }, t.title),
            str(t.description) ? h("p", { class: "pz-service__text" }, str(t.description)) : null,
            note ? null : h("p", { class: "pz-service__terms" }, T.lab.serviceTerms),
          ),
        ),
      ),
    );
  }
  return section;
}

function initials(name) {
  return String(name)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

/** Галерея «О центре»: 1–3 снимка, крупно по нажатию. Файл не загрузился — снимок убирается, без сломанной картинки. */
function renderGallery(photos) {
  return h(
    "section",
    { class: "pz-gallery", "aria-labelledby": "pz-photos-h" },
    h("h2", { class: "pz-subtitle", id: "pz-photos-h" }, T.lab.photos),
    h(
      "ul",
      { class: ["pz-photos", `pz-photos--${photos.length}`] },
      photos.map((p) => {
        const img = h("img", { class: "pz-photo__img", src: p.src, alt: p.alt, loading: "lazy", decoding: "async" });
        const btn = h(
          "button",
          {
            type: "button",
            class: "pz-photo__btn",
            "aria-haspopup": "dialog",
            "aria-label": T.lab.photoOpen(p.caption),
            dataset: { caption: p.caption },
            on: { click: () => openZoom(btn) },
          },
          img,
        );
        const item = h("li", { class: "pz-photo" }, btn, p.caption ? h("p", { class: "pz-photo__cap" }, p.caption) : null);
        img.addEventListener("error", () => item.remove());
        return item;
      }),
    ),
  );
}

function renderAbout() {
  const section = h("section", { class: "pz-section", dataset: { tab: "about" } });
  const prose = richText("about_html", "about");
  const acc = str(site?.accreditation);
  const staff = Array.isArray(site?.staff) ? site.staff.filter((p) => str(p?.name)) : [];
  const photos = labPhotos(site?.photos, T.lab.photoAlt);
  if (!prose && !acc && !staff.length && !photos.length) {
    section.append(h("div", { class: "pz-card pz-card--notice" }, pending()));
    return section;
  }
  section.append(
    h(
      "div",
      { class: "pz-about" },
      prose ? h("div", { class: "pz-card pz-about__text" }, prose) : null,
      acc
        ? h(
            "div",
            { class: "pz-card pz-accred" },
            h("span", { class: "pz-accred__seal", "aria-hidden": "true" }, prismMark({ className: "prism-mark pz-accred__mark" })),
            h("div", null, h("h2", { class: "pz-card__title" }, T.lab.accreditation), h("p", null, acc)),
          )
        : null,
    ),
  );
  if (photos.length) section.append(renderGallery(photos));
  if (staff.length) {
    section.append(
      h("h2", { class: "pz-subtitle" }, T.lab.staff),
      h(
        "ul",
        { class: "pz-staff" },
        staff.map((p) =>
          h(
            "li",
            { class: "pz-person" },
            h("span", { class: "pz-person__avatar", "aria-hidden": "true" }, initials(p.name)),
            h("span", { class: "pz-person__name" }, str(p.name)),
            str(p.role) ? h("span", { class: "pz-person__role" }, str(p.role)) : null,
          ),
        ),
      ),
    );
  }
  return section;
}

function renderContacts() {
  const section = h("section", { class: "pz-section", dataset: { tab: "contacts" } });
  const c = site?.contacts ?? {};
  const rows = ["address", "phone", "hours", "email"].filter((k) => str(c[k]));
  if (!rows.length) {
    section.append(h("div", { class: "pz-card pz-card--notice" }, pending()));
    return section;
  }
  // Телефон и почта — текстом, без tel:/mailto:: вымышленный номер может совпасть с настоящим.
  const value = (k) => str(c[k]);
  section.append(
    h(
      "div",
      { class: "pz-contacts" },
      h(
        "dl",
        { class: "pz-card pz-contacts__list" },
        rows.map((k) => [h("dt", null, T.lab.contact[k]), h("dd", null, value(k))]),
      ),
      // Схема проезда — условная, без настоящей карты (docs/05 §2).
      h("div", { class: "pz-map", "aria-hidden": "true" }, h("span", { class: "pz-map__pin" }, prismMark({ className: "prism-mark pz-map__mark" }))),
    ),
  );
  return section;
}

// ================================================================== запуск

if (ctx) {
  window.addEventListener("hashchange", () => {
    if (els.sections) showTab(currentTab());
  });
  ctx.store.onExternalChange(() => start());
  await start();
}
