// Журнал баллов (docs/01 §6): каждая запись log[] — время, основание, баллы.
// Счёт — сумма log[].d (core/state.js → score). Сворачивается (<details>).

import { h, clear, formatTime } from "./dom.js";
import { T, signed, describeLogEntry } from "./texts.js";
import { score } from "../core/state.js";

/**
 * renderScoreLog(state, { labelFor, open }) → <details class="scorelog">
 *   labelFor(path) — подпись вопроса по пути единицы (из пакета), по умолчанию путь;
 *   open           — развёрнут ли журнал.
 */
export function renderScoreLog(state, { labelFor, open = false } = {}) {
  const root = h("details", { class: "scorelog", open });
  fillScoreLog(root, state, { labelFor });
  return root;
}

/** Перерисовать журнал в существующем <details>, сохранив open. */
export function fillScoreLog(root, state, { labelFor } = {}) {
  const wasOpen = root.open;
  clear(root);
  const log = state?.log ?? [];
  const total = state ? score(state) : 0;

  root.appendChild(
    h(
      "summary",
      { class: "scorelog__summary" },
      h("span", { class: "scorelog__title" }, T.scorelog.title),
      h("span", { class: ["scorelog__total", total < 0 && "is-negative"] }, signedOrZero(total)),
    ),
  );

  if (log.length === 0) {
    root.appendChild(h("p", { class: "scorelog__empty" }, T.scorelog.empty));
    root.open = wasOpen;
    return root;
  }

  const rows = log.map((e) =>
    h(
      "tr",
      { class: e.d < 0 ? "is-penalty" : e.d > 0 ? "is-credit" : null },
      h("td", { class: "scorelog__time" }, formatTime(e.t)),
      h("td", { class: "scorelog__reason" }, describeLogEntry(e, labelFor)),
      h("td", { class: "scorelog__delta" }, signed(e.d)),
    ),
  );

  root.appendChild(
    h(
      "table",
      { class: "scorelog__table" },
      h("caption", { class: "visually-hidden" }, T.scorelog.caption),
      h(
        "thead",
        { class: "visually-hidden" },
        h(
          "tr",
          null,
          h("th", { scope: "col" }, T.scorelog.colTime),
          h("th", { scope: "col" }, T.scorelog.colReason),
          h("th", { scope: "col" }, T.scorelog.colDelta),
        ),
      ),
      h("tbody", null, rows),
      h(
        "tfoot",
        null,
        h(
          "tr",
          null,
          h("th", { scope: "row", colspan: "2" }, T.scorelog.total),
          h("td", { class: ["scorelog__delta", total < 0 && "is-negative"] }, signedOrZero(total)),
        ),
      ),
    ),
  );
  root.open = wasOpen;
  return root;
}

function signedOrZero(n) {
  return n === 0 ? "0" : signed(n);
}
