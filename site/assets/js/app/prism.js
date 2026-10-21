// Знак экспертного центра (docs/05 §2): призма, в которую входит белый луч и
// выходит спектр. Только линии и заливки — без шрифтов и картинок, чтобы знак
// одинаково выглядел в шапке сайта лаборатории, на карточке главного экрана и
// в крупной декорации раздела. Разметка постоянная, без данных.

const NS = "http://www.w3.org/2000/svg";

/** Цвета спектра — сверху вниз (красный … фиолетовый). */
export const SPECTRUM = ["#e5484d", "#f08c2e", "#e9c13b", "#3ba776", "#2f8fd8", "#7a5ce0"];

/**
 * prismMark({ className, title }) → <svg>.
 *   title — доступное имя; без него знак декоративный (aria-hidden).
 */
export function prismMark({ className = "prism-mark", title = "" } = {}) {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 64 48");
  svg.setAttribute("class", className);
  svg.setAttribute("focusable", "false");
  if (title) {
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", title);
  } else {
    svg.setAttribute("aria-hidden", "true");
  }
  // Лучи спектра расходятся веером от правой грани призмы.
  const rays = SPECTRUM.map((c, i) => {
    const y = 16 + i * 3.6;
    return `<path d="M36.5 ${(24.2 + i * 0.55).toFixed(2)} L64 ${y.toFixed(2)}" stroke="${c}" stroke-width="2.4" stroke-linecap="butt"/>`;
  }).join("");
  svg.innerHTML = `
    <path class="prism-mark__beam" d="M0 30.5 L22 25.2" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" opacity=".55"/>
    <g class="prism-mark__rays">${rays}</g>
    <path class="prism-mark__glass" d="M28 5 L46 40 L10 40 Z" fill="currentColor" fill-opacity=".08"/>
    <path class="prism-mark__edge" d="M28 5 L46 40 L10 40 Z" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linejoin="round"/>
    <path class="prism-mark__shine" d="M28 12 L19.5 32" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" opacity=".35"/>`;
  return svg;
}
