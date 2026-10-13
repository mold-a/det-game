// Общий запуск страниц системы расследования (/, /lab/, /final/):
// boot-проверка, public.json, хранилище, совместимость прогресса, пакеты
// открытых этапов, восстановление результатов экспертиз; экран фатальной ошибки.

import { h, clear } from "./dom.js";
import { T } from "./texts.js";
import { openModal } from "./modal.js";
import { restartFlow, loadFromFileFlow } from "./menu.js";
import { createStore, isCompatible } from "../core/state.js";
import { loadPublic, openPacks, receivedDocuments, startKey, GameDataError } from "../core/game.js";
import { b64uEncode } from "../core/crypto.js";
import { restoreLabResults, labDocTitles } from "../core/lab.js";

/** localStorage или null (доступ к свойству тоже может бросить). */
export function safeLocalStorage() {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

/** Данные оформления (FORMATS F19): из data-* на <body>, иначе из временной шапки шаблона. */
export function readChrome(doc = document) {
  const ds = doc.body.dataset;
  const text = (sel) => doc.querySelector(sel)?.textContent.trim() ?? "";
  const chrome = {
    system: ds.system || text(".chrome__system"),
    department: ds.department || text(".chrome__dept"),
    caseNo: ds.caseNo || text(".chrome__case").replace(/^Дело\s*№\s*/u, ""),
  };
  doc.querySelector(".chrome")?.remove();
  return chrome;
}

/** Параметры правил для T.rules из public.json. */
export function rulesCfg(pub) {
  return {
    wrongPenalty: pub.penalties.wrongAttempt,
    hintCosts: pub.hints.cost,
    autoAfter: pub.hints.autoAfterWrong,
    bonus: pub.points.bonus,
    final: pub.points.final,
  };
}

/** Корень приложения: #app шаблона заменяется на <div class="app-root">. */
function prepareMount() {
  const old = document.getElementById("app");
  const root = h("div", { class: "app-root", id: "app" });
  if (old) old.replaceWith(root);
  else document.body.appendChild(root);
  return root;
}

/**
 * Экран ошибки: заголовок, текст, действия (перезагрузить / начать заново /
 * загрузить из файла).
 */
export function renderFatal(ctx, { title = T.errors.title, text, reload = false, restart = false, load = false }) {
  const { mount } = ctx;
  clear(mount);
  const actions = h("div", { class: "q__actions" });
  if (reload) {
    const b = h("button", { type: "button", class: "btn btn--primary" }, T.errors.reload);
    b.addEventListener("click", () => location.reload());
    actions.appendChild(b);
  }
  if (load && ctx.store) {
    const b = h("button", { type: "button", class: "btn btn--secondary" }, T.errors.load);
    b.addEventListener("click", () => loadFromFileFlow(ctx, () => location.reload()));
    actions.appendChild(b);
  }
  if (restart && ctx.store) {
    const b = h("button", { type: "button", class: "btn btn--danger" }, T.errors.restart);
    b.addEventListener("click", async () => {
      if (await restartFlow(ctx.store)) location.assign("/");
    });
    actions.appendChild(b);
  }
  mount.appendChild(
    h("main", { class: "intro", id: "main" }, h("h1", { class: "intro__title" }, title), h("p", { class: "notice notice--error" }, text), actions),
  );
}

/**
 * Запуск страницы. → ctx { pub, store, chrome, mount } или null (boot.js уже
 * показал экран про HTTPS / ошибка показана).
 */
export async function initPage() {
  if (!globalThis.DETGAME_BOOT?.ok) return null;
  const chrome = readChrome();
  const mount = prepareMount();
  const ctx = { pub: null, store: null, chrome, mount };
  try {
    ctx.pub = await loadPublic();
  } catch {
    renderFatal(ctx, { text: T.errors.network, reload: true });
    return null;
  }
  ctx.store = createStore({ storage: safeLocalStorage(), gameId: ctx.pub.gameId });
  return ctx;
}

/**
 * Загрузить прогресс и открыть пакеты.
 * → { ok: true, state, packs, labResults, labEntries, docs }
 *   | { ok: false, code: "none" | "corrupt" | "incompatible" | "pack" | "network" }
 */
export async function loadProgress(ctx, state = ctx.store.get()) {
  if (!state) return { ok: false, code: ctx.store.corrupt ? "corrupt" : "none" };
  if (!isCompatible(state, ctx.pub)) return { ok: false, code: "incompatible" };
  let packs;
  try {
    packs = await openPacks(state);
  } catch (e) {
    if (e instanceof GameDataError && e.code === "network") return { ok: false, code: "network" };
    // Сохранённый ключ не открывает пакет. Если и K1 не тот, что выводится из
    // public.json, — сайт пересобран с другими солями: прогресс несовместим (docs/02 §4).
    // Иначе — «Пакет не расшифровался».
    try {
      const k1 = b64uEncode(await startKey(ctx.pub));
      if (k1 !== state.keys[1]) return { ok: false, code: "incompatible" };
    } catch {
      /* нет данных для сравнения */
    }
    return { ok: false, code: "pack" };
  }
  const labCtx = { stage: state.stage, keys: state.keys, packs };
  let labResults = {};
  try {
    labResults = await restoreLabResults(state.lab.log, labCtx);
  } catch {
    labResults = {};
  }
  const labEntries = {};
  for (const r of Object.values(labResults)) if (r.entry.doc) labEntries[r.entry.doc] = r.entry;
  const docs = receivedDocuments(packs, state, labDocTitles(labResults));
  return { ok: true, state, packs, labResults, labEntries, docs };
}

/** Показать экран ошибки по коду loadProgress. */
export function renderLoadError(ctx, code) {
  if (code === "corrupt") return renderFatal(ctx, { text: T.errors.corrupt, restart: true, load: true });
  if (code === "incompatible")
    return renderFatal(ctx, { title: T.errors.incompatibleTitle, text: T.errors.incompatible, restart: true, load: true });
  if (code === "network") return renderFatal(ctx, { text: T.errors.network, reload: true });
  return renderFatal(ctx, { text: T.errors.pack, reload: true, restart: true });
}

/** Каркас страницы: шапка + две колонки. → { header, main, side } */
export function renderShell(ctx, headerEl) {
  clear(ctx.mount);
  const main = h("main", { class: "main", id: "main", tabindex: "-1" });
  const side = h("aside", { class: "side", "aria-label": T.docs.title });
  ctx.mount.append(
    h("a", { class: "skip-link", href: "#main" }, T.skipToMain),
    headerEl,
    h("div", { class: "layout" }, main, side),
  );
  return { main, side };
}

/** Короткое сообщение-модалка. */
export function info(title, text) {
  return openModal({ title, body: text });
}
