// Шапка — корешок папки (docs/05 §1): ярлык «Дело №», команда, счёт крупно
// табличными цифрами, четыре конверта (запечатан / вскрыт / текущий), меню.
// Счёт в шапке — сумма журнала; во время финала он не меняется (баллы финала
// пишутся только в finalFinish).

import { h, replace } from "./dom.js";
import { T, signed } from "./texts.js";
import { createMenu } from "./menu.js";
import { score, labClosed } from "../core/state.js";
import { envelopeMarks } from "../core/flow.js";

const NS = "http://www.w3.org/2000/svg";

/**
 * Конверт-значок. state: "sealed" | "opened" | "current".
 * Запечатанный — клапан закрыт, на нём печать; вскрытый — клапан откинут,
 * из конверта виден лист; текущий — вскрытый, лист отмечен цветом печати.
 */
export function envelopeIcon(state) {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 40 34");
  svg.setAttribute("class", `env env--${state}`);
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const sealed = state === "sealed";
  // Разметка постоянная, без данных.
  svg.innerHTML = sealed
    ? `<rect class="env__body" x="2" y="10" width="36" height="22" rx="1.5"/>
       <path class="env__fold" d="M2.8 31 L16 21 M37.2 31 L24 21"/>
       <path class="env__flap" d="M2.5 10.5 L20 23 L37.5 10.5"/>
       <circle class="env__seal" cx="20" cy="22.2" r="4.2"/>
       <circle class="env__seal-ring" cx="20" cy="22.2" r="2.4"/>`
    : `<path class="env__flap-open" d="M2 12 L20 1.5 L38 12 Z"/>
       <rect class="env__sheet" x="7" y="4.5" width="26" height="18" rx="1"/>
       <path class="env__lines" d="M11 9.5 H29 M11 13 H26 M11 16.5 H28"/>
       <path class="env__pocket" d="M2 12 L20 23.5 L38 12 V32 H2 Z"/>
       <path class="env__fold" d="M2.8 31 L16 21 M37.2 31 L24 21"/>`;
  return svg;
}

/**
 * renderHeader(ctx, state, { onChange, verify, rulesCfg, viewOf }) → { el, update(state) }
 *   ctx: { pub, store, chrome }; viewOf(state) → номер этапа, показанного на экране (по умолчанию state.stage):
 *   именно он подсвечивается «текущим», следующий конверт остаётся запечатанным.
 */
export function renderHeader(ctx, state, { onChange = () => location.reload(), verify, rulesCfg, viewOf } = {}) {
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
        h("a", { class: "app-header__case-no", href: "/" }, h("span", { class: "app-header__case-word" }, T.header.caseWord), " ", h("span", { class: "app-header__case-num" }, T.header.caseNum(chrome.caseNo))),
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
    const marks = envelopeMarks(s, s ? viewOf?.(s) : null, pub.stages);
    marks.forEach((mark, i) => {
      const n = i + 1;
      const cur = mark === "current";
      const done = mark === "opened";
      const label = done ? T.header.stageDone(n) : cur ? T.header.stageCurrent(n) : T.header.stageLocked(n);
      items.push(
        h(
          "li",
          { class: ["stages__item", done && "is-done", cur && "is-current"], "aria-label": label, "aria-current": cur ? "step" : null, title: label },
          envelopeIcon(mark),
          h("span", { class: "stages__no", "aria-hidden": "true" }, String(n)),
        ),
      );
    });
    replace(stages, items);
    menu.setLabClosed(labClosed(s));
  }
  update(state);
  return { el, update };
}
