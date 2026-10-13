// Фиолетовый штамп — единственная яркая деталь интерфейса (docs/05 §1).
// Отмечает решённые вопросы («Принято»), переход этапа («Конверт №N — вскрыть»)
// и итоговый ранг.
//
// Неровная кромка и «непропечатанная» краска — SVG-фильтр (feTurbulence +
// feDisplacementMap + выщербины по альфе). Фильтр вставляется в документ один раз.
// Наклон детерминированный: зависит от seed (например, пути вопроса), поэтому
// после перезагрузки штамп лежит так же.
// Движение — одно: масштаб 1,15 → 1 с поворотом за 180 мс (CSS, класс stamp--drop);
// при prefers-reduced-motion CSS отключает анимацию.

import { h } from "./dom.js";
import { T } from "./texts.js";

export const STAMP_FILTER_ID = "dg-stamp-rough";

/** Вставить SVG-фильтр штампа в документ (один раз). */
export function ensureStampFilter(doc = document) {
  if (doc.getElementById(STAMP_FILTER_ID)) return;
  const NS = "http://www.w3.org/2000/svg";
  const svg = doc.createElementNS(NS, "svg");
  svg.setAttribute("width", "0");
  svg.setAttribute("height", "0");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.style.position = "absolute";
  // Разметка фиксированная, без данных — innerHTML здесь безопасен.
  svg.innerHTML = `
    <filter id="${STAMP_FILTER_ID}" x="-8%" y="-15%" width="116%" height="130%" color-interpolation-filters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="11" result="warp"/>
      <feDisplacementMap in="SourceGraphic" in2="warp" scale="2.6" xChannelSelector="R" yChannelSelector="G" result="rough"/>
      <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="2" seed="4" result="grain"/>
      <feColorMatrix in="grain" type="matrix"
        values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -3.2 2.35" result="holes"/>
      <feComposite in="rough" in2="holes" operator="in"/>
    </filter>`;
  (doc.body || doc.documentElement).appendChild(svg);
}

/** Детерминированный наклон в градусах из строки: от −9° до −3°. */
export function tiltFor(seed = "") {
  let x = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    x ^= seed.charCodeAt(i);
    x = Math.imul(x, 16777619);
  }
  const t = ((x >>> 0) % 1000) / 1000; // 0..1
  return -9 + t * 6;
}

/**
 * Создать штамп.
 *   text    — надпись (по умолчанию «Принято»);
 *   sub     — вторая строка мелко (дата, ранг и т. п.), необязательно;
 *   variant — "accepted" (на вопросе) | "envelope" (в окне перехода) | "rank" (итог);
 *   seed    — строка для наклона; tilt — явный наклон в градусах;
 *   animate — опустить штамп с анимацией (только в момент решения, не при перерисовке).
 */
export function createStamp({ text = T.stamp.accepted, sub = "", variant = "accepted", seed = text, tilt, animate = false } = {}) {
  ensureStampFilter();
  const deg = typeof tilt === "number" ? tilt : tiltFor(seed);
  const el = h(
    "span",
    {
      class: ["stamp", `stamp--${variant}`, animate && "stamp--drop"],
      role: "img",
      "aria-label": sub ? `${text}. ${sub}` : text,
      style: { "--stamp-tilt": `${deg.toFixed(2)}deg` },
    },
    h("span", { class: "stamp__ink", "aria-hidden": "true" }, h("span", { class: "stamp__text" }, text), sub ? h("span", { class: "stamp__sub" }, sub) : null),
  );
  if (animate) {
    el.addEventListener("animationend", () => el.classList.remove("stamp--drop"), { once: true });
  }
  return el;
}

/** Поставить штамп «Принято» на участок вопроса. Возвращает элемент штампа. */
export function stampAccepted(container, { seed, animate = false, sub = "" } = {}) {
  const old = container.querySelector(":scope > .stamp");
  if (old) old.remove();
  const el = createStamp({ text: T.stamp.accepted, seed, animate, sub });
  container.appendChild(el);
  return el;
}
