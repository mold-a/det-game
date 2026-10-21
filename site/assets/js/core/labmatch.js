// Распознавание объекта лаборатории по свободному тексту — docs/02 «Распознавание объекта».
// Зеркало engine/labmatch.py: обе реализации обязаны давать одинаковый результат.
// Общие векторы — tests/vectors/lab-match.json. Без DOM: работает в браузере и в Node 22.
//
//   labTokens(s)                   → string[]   токены нормализованного текста
//   resolveObject(text, objects)   → {status:"ok", id} | {status:"ambiguous", ids} | {status:"none"}
//
// objects — объекты каталога, доступные сейчас, в порядке expertise.yaml: {id, title, aliases}.
// aliases уже нормализованы (основы через пробел), как их кладёт сборка в LabCatalog.

import { normalize } from "./normalize.js";

// Токены названия объекта длиной не меньше этого числа символов — основы алиаса-названия.
export const TITLE_STEM_MIN = 3;

const norm = (s) => normalize("text", String(s ?? "")) ?? "";
// Длина в символах Unicode (как len() в Python), а не в единицах UTF-16.
const len = (s) => [...s].length;

/** Токены нормализованного текста; пустая строка → []. */
export function labTokens(s) {
  const n = norm(s);
  return n === "" ? [] : n.split(" ");
}

const aliasStems = (alias) => String(alias).split(" ").filter((x) => x !== "");
const titleStems = (title) => labTokens(title).filter((t) => len(t) >= TITLE_STEM_MIN);

// Совпадение алиаса: [pos, -score] или null.
function matchStems(stems, tokens) {
  if (stems.length === 0) return null;
  const used = new Set();
  for (const stem of stems) {
    let found = -1;
    for (let i = 0; i < tokens.length; i++) {
      if (!used.has(i) && tokens[i].startsWith(stem)) {
        found = i;
        break;
      }
    }
    if (found < 0) return null;
    used.add(found);
  }
  return [Math.min(...used), -stems.reduce((sum, s) => sum + len(s), 0)];
}

const compareKeys = (a, b) => a[0] - b[0] || a[1] - b[1];

// Лучший ключ [pos, -score] объекта или null.
function bestMatch(obj, tokens) {
  const candidates = (obj.aliases ?? []).map(aliasStems);
  candidates.push(titleStems(obj.title ?? ""));
  let best = null;
  for (const stems of candidates) {
    const key = matchStems(stems, tokens);
    if (key !== null && (best === null || compareKeys(key, best) < 0)) best = key;
  }
  return best;
}

/**
 * Распознать объект по тексту.
 *  - один лучший кандидат   → { status: "ok", id }
 *  - несколько              → { status: "ambiguous", ids } (в порядке objects)
 *  - ни одного              → { status: "none" }
 */
export function resolveObject(text, objects) {
  const tokens = labTokens(text);
  const found = [];
  for (const obj of objects) {
    const key = bestMatch(obj, tokens);
    if (key !== null) found.push({ key, id: obj.id });
  }
  if (found.length === 0) return { status: "none" };
  let top = found[0].key;
  for (const f of found) if (compareKeys(f.key, top) < 0) top = f.key;
  const ids = found.filter((f) => compareKeys(f.key, top) === 0).map((f) => f.id);
  return ids.length === 1 ? { status: "ok", id: ids[0] } : { status: "ambiguous", ids };
}
