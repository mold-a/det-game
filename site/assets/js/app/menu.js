// Меню системы расследования (docs/01 §10, docs/04): правила, сохранить прогресс
// в файл, загрузить из файла, начать заново (двойное подтверждение).
// Работает только через API core/state.js (store). Потоки «загрузить» и
// «начать заново» экспортируются и для экранов ошибок (context.js).

import { h, downloadText, announce } from "./dom.js";
import { T } from "./texts.js";
import { openModal, confirmDialog, alertDialog } from "./modal.js";
import { parseState, isCompatible, exportFileName, StateError } from "../core/state.js";

/** Сайт лаборатории — открывается в той же вкладке (docs/04). */
export const LAB_HREF = "/lab/";

/** «Начать заново» с двойным подтверждением. → true, если прогресс удалён. */
export async function restartFlow(store) {
  const first = await confirmDialog({
    title: T.menu.restartTitle,
    text: T.menu.restart1,
    ok: T.menu.restart1Ok,
    danger: true,
  });
  if (!first) return false;
  const second = await confirmDialog({
    title: T.menu.restartTitle,
    text: T.menu.restart2,
    ok: T.menu.restart2Ok,
    danger: true,
  });
  if (!second) return false;
  store.reset();
  announce(T.menu.restarted);
  return true;
}

/**
 * Выбор файла и загрузка прогресса. ctx: { store, pub, verify? }.
 * verify(state) → Promise<boolean> — вторая часть проверки совместимости
 * (ключ открывает пакет, core/game.js); по умолчанию — true.
 * onChange(state) — после успешной загрузки.
 */
export function loadFromFileFlow(ctx, onChange = () => {}) {
  const input = h("input", { type: "file", accept: ".json,application/json", hidden: true });
  document.body.appendChild(input);
  input.addEventListener("change", async () => {
    const file = input.files && input.files[0];
    input.remove();
    if (file) await importFile(ctx, file, onChange);
  });
  input.click();
}

async function importFile({ store, pub, verify = async () => true }, file, onChange) {
  let text;
  let state;
  try {
    text = await file.text();
    state = parseState(text);
  } catch (e) {
    if (!(e instanceof StateError) && !(e instanceof TypeError)) throw e;
    await alertDialog({ title: T.menu.loadReplaceTitle, text: T.menu.loadBad });
    return;
  }
  let ok = isCompatible(state, pub);
  if (ok) {
    try {
      ok = await verify(state);
    } catch {
      ok = false;
    }
  }
  if (!ok) {
    await alertDialog({ title: T.errors.incompatibleTitle, text: T.menu.loadIncompatible });
    return;
  }
  // Предупреждаем всегда: импорт заменяет прогресс, а открытые вкладки могут
  // при следующей записи слить с ним свои записи (FORMATS §7.2).
  const okReplace = await confirmDialog({
    title: T.menu.loadReplaceTitle,
    text: T.menu.loadReplace,
    ok: T.menu.loadConfirm,
  });
  if (!okReplace) return;
  const loaded = store.importJson(text);
  announce(T.menu.loaded);
  onChange(loaded);
}

/**
 * createMenu({ store, pub, onChange, verify, rulesCfg })
 *   store    — createStore(...);
 *   pub      — public.json (gameId, saltsId);
 *   onChange — (state | null) => void, после загрузки или сброса;
 *   verify   — см. loadFromFileFlow;
 *   rulesCfg — { wrongPenalty, hintCosts, autoAfter, bonus, final } для T.rules;
 *              без него пункт «Правила» не показывается;
 *   lab      — адрес лаборатории для пункта «Лаборатория» (та же вкладка) или null.
 * Возвращает <details class="menu">.
 */
export function createMenu({ store, pub, onChange = () => {}, verify, rulesCfg = null, lab = LAB_HREF }) {
  const item = (label, action, extra = {}) =>
    h("li", null, h("button", { type: "button", class: ["menu__item", extra.danger && "menu__item--danger"], onclick: action }, label));

  // Пункт «Лаборатория» скрыт, пока лаборатория закрыта (финал начат, docs/01 §8); setLabClosed переключает его.
  const labItem = lab ? h("li", { class: "menu__lab" }, h("a", { class: "menu__item menu__item--link", href: lab }, T.lab.menu)) : null;

  const root = h(
    "details",
    { class: "menu" },
    h("summary", { class: "menu__toggle" }, h("span", { class: "menu__label" }, T.menu.title)),
    h(
      "ul",
      { class: "menu__list" },
      labItem,
      rulesCfg ? item(T.menu.rules, showRules) : null,
      item(T.menu.save, save),
      item(T.menu.load, load),
      item(T.menu.restart, restart, { danger: true }),
    ),
  );

  root.setLabClosed = (closed) => {
    if (labItem) labItem.hidden = Boolean(closed);
  };

  function closeMenu() {
    root.open = false;
  }

  async function showRules() {
    closeMenu();
    await openModal({
      title: T.start.rulesTitle,
      body: h("ol", { class: "rules" }, T.rules(rulesCfg).map((line) => h("li", null, line))),
    });
  }

  function save() {
    closeMenu();
    downloadText(exportFileName(pub.gameId), store.exportJson());
    announce(T.menu.saved);
  }

  function load() {
    closeMenu();
    loadFromFileFlow({ store, pub, verify }, onChange);
  }

  async function restart() {
    closeMenu();
    if (await restartFlow(store)) onChange(null);
  }

  // Esc закрывает раскрытое меню и возвращает фокус на кнопку.
  root.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && root.open) {
      root.open = false;
      root.querySelector("summary").focus();
    }
  });
  // Щелчок вне меню закрывает его.
  document.addEventListener("click", (e) => {
    if (root.open && !root.contains(e.target)) root.open = false;
  });

  return root;
}
