// Шапка-папка: номер дела, название системы, команда, счёт, этапы 1–N, меню.
// Счёт в шапке — сумма журнала; во время финала он не меняется (баллы финала
// пишутся только в finalFinish).

import { h, replace } from "./dom.js";
import { T, signed } from "./texts.js";
import { createMenu } from "./menu.js";
import { score } from "../core/state.js";

/**
 * renderHeader(ctx, state, { onChange, verify }) → { el, update(state) }
 *   ctx: { pub, store, chrome }.
 */
export function renderHeader(ctx, state, { onChange = () => location.reload(), verify, rulesCfg } = {}) {
  const { pub, chrome } = ctx;
  const team = h("div", { class: "app-header__team" });
  const value = h("span", { class: "score__value" });
  const stages = h("ol", { class: "stages", "aria-label": T.header.stages });
  const menu = createMenu({ store: ctx.store, pub, onChange, verify, rulesCfg });

  const el = h(
    "header",
    { class: "app-header" },
    h(
      "div",
      { class: "app-header__inner" },
      h(
        "div",
        { class: "app-header__case" },
        h("a", { class: "app-header__case-no", href: "/" }, T.header.caseNo(chrome.caseNo)),
        chrome.system ? h("span", { class: "app-header__system" }, chrome.system) : null,
      ),
      team,
      h("div", { class: "score", role: "status", "aria-live": "polite" }, h("span", { class: "score__label" }, T.header.score), value),
      stages,
      menu,
    ),
  );

  function update(s) {
    team.textContent = s?.team ? T.header.team(s.team) : "";
    const total = s ? score(s) : 0;
    value.textContent = total === 0 ? "0" : signed(total);
    value.classList.toggle("is-negative", total < 0);
    const items = [];
    for (let n = 1; n <= pub.stages; n++) {
      const cur = s && n === s.stage && !s.finished;
      const done = s && (n < s.stage || (s.finished && n === s.stage));
      const label = done ? T.header.stageDone(n) : cur ? T.header.stageCurrent(n) : T.header.stageLocked(n);
      items.push(
        h(
          "li",
          { class: ["stages__item", done && "is-done", cur && "is-current"], "aria-label": label, "aria-current": cur ? "step" : null },
          String(n),
        ),
      );
    }
    replace(stages, items);
  }
  update(state);
  return { el, update };
}
