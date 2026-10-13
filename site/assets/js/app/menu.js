// Меню системы расследования (docs/01 §10, docs/04): правила, сохранить прогресс
// в файл, загрузить из файла, начать заново (двойное подтверждение).
// Работает только через API core/state.js (store).

import { h, downloadText, announce } from "./dom.js";
import { T } from "./texts.js";
import { openModal, confirmDialog, alertDialog } from "./modal.js";
import { parseState, isCompatible, exportFileName, StateError } from "../core/state.js";

/**
 * createMenu({ store, pub, onChange, verify, rulesCfg })
 *   store    — createStore(...);
 *   pub      — public.json (gameId, saltsId);
 *   onChange — (state | null) => void, после загрузки или сброса;
 *   verify   — async (state) => boolean: вторая часть проверки совместимости
 *              (keys[stage] открывает pack-<stage>, core/game.js); по умолчанию — true;
 *   rulesCfg — { wrongPenalty, hintCosts, autoAfter, bonus, final } для T.rules;
 *              без него пункт «Правила» не показывается.
 * Возвращает <details class="menu">.
 */
export function createMenu({ store, pub, onChange = () => {}, verify = async () => true, rulesCfg = null }) {
  const fileInput = h("input", {
    type: "file",
    accept: ".json,application/json",
    class: "visually-hidden",
    tabindex: "-1",
    "aria-hidden": "true",
  });

  const item = (label, action, extra = {}) =>
    h("li", null, h("button", { type: "button", class: ["menu__item", extra.danger && "menu__item--danger"], onclick: action }, label));

  const root = h(
    "details",
    { class: "menu" },
    h("summary", { class: "menu__toggle" }, h("span", { class: "menu__label" }, T.menu.title)),
    h(
      "ul",
      { class: "menu__list" },
      rulesCfg ? item(T.menu.rules, showRules) : null,
      item(T.menu.save, save),
      item(T.menu.load, () => fileInput.click()),
      item(T.menu.restart, restart, { danger: true }),
    ),
    fileInput,
  );

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

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files && fileInput.files[0];
    fileInput.value = "";
    closeMenu();
    if (!file) return;
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
    if (!isCompatible(state, pub) || !(await verify(state))) {
      await alertDialog({ title: T.errors.incompatibleTitle, text: T.menu.loadIncompatible });
      return;
    }
    if (store.get()) {
      const ok = await confirmDialog({
        title: T.menu.loadReplaceTitle,
        text: T.menu.loadReplace,
        ok: T.menu.loadConfirm,
      });
      if (!ok) return;
    }
    const loaded = store.importJson(text);
    announce(T.menu.loaded);
    onChange(loaded);
  });

  async function restart() {
    closeMenu();
    const first = await confirmDialog({
      title: T.menu.restartTitle,
      text: T.menu.restart1,
      ok: T.menu.restart1Ok,
      danger: true,
    });
    if (!first) return;
    const second = await confirmDialog({
      title: T.menu.restartTitle,
      text: T.menu.restart2,
      ok: T.menu.restart2Ok,
      danger: true,
    });
    if (!second) return;
    store.reset();
    announce(T.menu.restarted);
    onChange(null);
  }

  // Esc закрывает раскрытое меню и возвращает фокус на кнопку.
  root.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && root.open) {
      root.open = false;
      root.querySelector("summary").focus();
    }
  });

  return root;
}
