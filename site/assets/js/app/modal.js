// Доступное модальное окно: role="dialog", aria-modal, заголовок через
// aria-labelledby, фокус-ловушка (Tab / Shift+Tab по кругу), Esc закрывает
// (если окно можно закрыть), фон недоступен (inert), по закрытии фокус
// возвращается туда, где был.
//
// openModal(...) → Promise<string|null>: id нажатой кнопки или null (Esc / «Закрыть»).

import { h, uid, append } from "./dom.js";
import { T } from "./texts.js";

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type=hidden])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "summary",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function focusables(root) {
  return Array.from(root.querySelectorAll(FOCUSABLE)).filter(
    (el) => !el.closest("[hidden]") && el.getClientRects().length > 0,
  );
}

/** Открытые окна — стек (окно подтверждения может открыться поверх другого). */
const stack = [];

/**
 * openModal({ title, body, actions, dismissible, stamp, initialFocus, className })
 *   title       — заголовок (текст);
 *   body        — Node | string | массив (строки — абзацы);
 *   actions     — [{ id, label, primary?, danger? }] (по умолчанию одна «Понятно»);
 *   dismissible — Esc и кнопка «Закрыть» доступны (по умолчанию true);
 *   stamp       — элемент штампа над заголовком (переход этапа, ранг);
 *   initialFocus— id действия, которое получает фокус (по умолчанию первое поле
 *                 ввода или основная кнопка).
 */
export function openModal({
  title,
  body = null,
  actions = [{ id: "ok", label: T.ok, primary: true }],
  dismissible = true,
  stamp = null,
  initialFocus = null,
  className = "",
} = {}) {
  return new Promise((resolve) => {
    const returnTo = document.activeElement;
    const titleId = uid("modal-title");
    const bodyId = uid("modal-body");

    const bodyNode = h("div", { class: "modal__body", id: bodyId });
    const parts = Array.isArray(body) ? body : body == null ? [] : [body];
    append(
      bodyNode,
      parts.map((p) => (typeof p === "string" ? h("p", null, p) : p)),
    );

    const buttons = actions.map((a) =>
      h(
        "button",
        {
          type: "button",
          class: ["btn", a.primary ? "btn--primary" : "btn--secondary", a.danger && "btn--danger"],
          dataset: { action: a.id },
        },
        a.label,
      ),
    );

    const closeBtn = dismissible
      ? h("button", { type: "button", class: "modal__close", "aria-label": T.close, dataset: { action: "" } }, "×")
      : null;

    const dialog = h(
      "div",
      {
        class: ["modal", className],
        role: actions.length > 1 ? "alertdialog" : "dialog",
        "aria-modal": "true",
        "aria-labelledby": titleId,
        "aria-describedby": parts.length ? bodyId : null,
        tabindex: "-1",
      },
      stamp ? h("div", { class: "modal__stamp" }, stamp) : null,
      h("h2", { class: "modal__title", id: titleId }, title),
      bodyNode,
      h("div", { class: "modal__actions" }, buttons),
      closeBtn, // в DOM последней: Tab идёт по действиям, затем «Закрыть» (визуально — в углу)
    );
    const backdrop = h("div", { class: "modal-backdrop" }, dialog);

    // Фон недоступен для фокуса и дикторов.
    const siblings = Array.from(document.body.children).filter((n) => n !== backdrop && !n.inert);
    for (const n of siblings) {
      n.inert = true;
      n.setAttribute("data-modal-inert", "");
    }

    function close(result) {
      document.removeEventListener("keydown", onKey, true);
      backdrop.remove();
      const i = stack.indexOf(dialog);
      if (i >= 0) stack.splice(i, 1);
      for (const n of siblings) {
        n.inert = false;
        n.removeAttribute("data-modal-inert");
      }
      if (returnTo && typeof returnTo.focus === "function" && returnTo.isConnected) {
        returnTo.focus();
      }
      resolve(result);
    }

    function onKey(e) {
      if (stack[stack.length - 1] !== dialog) return;
      if (e.key === "Escape") {
        if (dismissible) {
          e.preventDefault();
          e.stopPropagation();
          close(null);
        }
        return;
      }
      if (e.key !== "Tab") return;
      const list = focusables(dialog);
      if (list.length === 0) {
        e.preventDefault();
        dialog.focus();
        return;
      }
      const first = list[0];
      const last = list[list.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === first || !dialog.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || !dialog.contains(active))) {
        e.preventDefault();
        first.focus();
      }
    }

    dialog.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-action]");
      if (!btn || !dialog.contains(btn)) return;
      close(btn.dataset.action === "" ? null : btn.dataset.action);
    });
    // Щелчок по подложке окно не закрывает: решение должно быть явным.

    document.addEventListener("keydown", onKey, true);
    document.body.appendChild(backdrop);
    stack.push(dialog);

    const target =
      (initialFocus && dialog.querySelector(`[data-action="${CSS.escape(initialFocus)}"]`)) ||
      bodyNode.querySelector("input, select, textarea") ||
      dialog.querySelector(".btn--primary") ||
      buttons[0] ||
      dialog;
    target.focus();
  });
}

/** Подтверждение: Promise<boolean>. */
export async function confirmDialog({ title, text, ok, cancel = T.cancel, danger = false }) {
  const res = await openModal({
    title,
    body: text,
    actions: [
      { id: "cancel", label: cancel },
      { id: "ok", label: ok, primary: !danger, danger },
    ],
    initialFocus: danger ? "cancel" : "ok",
  });
  return res === "ok";
}

/** Сообщение с одной кнопкой. */
export async function alertDialog({ title, text, ok = T.ok }) {
  await openModal({ title, body: text, actions: [{ id: "ok", label: ok, primary: true }] });
}
