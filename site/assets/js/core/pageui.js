// Логика вымышленных страниц без DOM (REDESIGN-2026-10 §4.1): вкладки, разделы сайта,
// поиск людей. DOM-часть — pages/page-ui.js. Тесты — tests/js/pageui.test.mjs.

import { base } from "./normalize.js";

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

/** Поиск людей на главной «Круга»: с какой длины запроса искать и сколько результатов показывать. */
export const PEOPLE_MIN = 3;
export const PEOPLE_MAX = 5;

/**
 * Поиск людей по запросу (docs/04, social_home). Без учёта регистра и «ё». Совпадение — по началу имени или
 * фамилии (первые два слова ФИО; отчество не ищется); запрос из нескольких слов — каждое слово должно
 * начинать имя или фамилию. Пустой или слишком короткий запрос ничего не показывает.
 * → { status: "idle" | "short" | "none" | "found", indices: number[] } (индексы в порядке списка, не больше max).
 */
export function searchPeople(names, query, { min = PEOPLE_MIN, max = PEOPLE_MAX } = {}) {
  const q = base(query ?? "");
  if (!q) return { status: "idle", indices: [] };
  if (q.replaceAll(" ", "").length < min) return { status: "short", indices: [] };
  const words = q.split(" ");
  const indices = [];
  names.forEach((name, i) => {
    const own = base(name).split(" ").slice(0, 2);
    if (words.every((w) => own.some((o) => o.startsWith(w)))) indices.push(i);
  });
  return indices.length ? { status: "found", indices: indices.slice(0, max) } : { status: "none", indices: [] };
}

/** Сколько фото показывает галерея «О центре» (docs/04). */
export const LAB_PHOTOS_MAX = 3;

/**
 * Фото лаборатории из данных сайта (`lab_site.photos`): только снимки с адресом в /m/ (сборка кладёт туда
 * открытые медиа; чужие адреса и пустые записи отбрасываются), не больше LAB_PHOTOS_MAX. Подпись — обрезанная
 * строка (заглушка TODO(content) считается пустой); alt — подпись или запасной текст.
 */
export function labPhotos(list, fallbackAlt = "Фотография центра") {
  if (!Array.isArray(list)) return [];
  const out = [];
  for (const p of list) {
    const src = typeof p?.src === "string" ? p.src : "";
    if (!/^\/m\/[0-9a-z._-]+$/i.test(src)) continue;
    const raw = typeof p.caption === "string" && !p.caption.includes("TODO(content)") ? p.caption.trim() : "";
    out.push({ src, caption: raw, alt: raw || fallbackAlt });
    if (out.length >= LAB_PHOTOS_MAX) break;
  }
  return out;
}
