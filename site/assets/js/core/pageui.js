// Логика вымышленных страниц без DOM (REDESIGN-2026-10 §4.1): окна сервиса, вкладки, разделы сайта,
// поиск людей. DOM-часть — pages/page-ui.js. Тесты — tests/js/pageui.test.mjs.

import { base } from "./normalize.js";

/** Текст окна → абзацы: строки через перевод строки, пустые отбрасываются. */
export function paragraphs(text) {
  return String(text ?? "")
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Индекс вкладки после нажатия клавиши (ARIA tabs, горизонтальные вкладки) или null, если клавиша не наша.
 * Стрелки зациклены, Home/End — первая и последняя.
 */
export function nextTabIndex(key, current, count) {
  if (!(count > 0)) return null;
  switch (key) {
    case "ArrowRight":
    case "ArrowDown":
      return (current + 1) % count;
    case "ArrowLeft":
    case "ArrowUp":
      return (current - 1 + count) % count;
    case "Home":
      return 0;
    case "End":
      return count - 1;
    default:
      return null;
  }
}

/** Раздел сайта по адресу: «#afisha» → "afisha"; неизвестный или пустой — запасной (первый). */
export function sectionFromHash(hash, ids, fallback = ids[0]) {
  const id = String(hash ?? "").replace(/^#/, "");
  let decoded = id;
  try {
    decoded = decodeURIComponent(id);
  } catch {
    /* оставить как есть */
  }
  return ids.includes(decoded) ? decoded : fallback;
}

/** Какие имена подходят под запрос (без регистра, «ё», знаков препинания; подстрокой по словам). Пустой запрос — все. */
export function filterNames(names, query) {
  const q = base(query ?? "");
  return names.map((n) => !q || base(n).includes(q));
}
