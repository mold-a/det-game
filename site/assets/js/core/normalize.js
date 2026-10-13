// Нормализация ответов — docs/02-architecture.md §2.
// Зеркало engine/normalize.py: обе реализации обязаны давать побайтно одинаковый
// результат. Общие векторы — tests/vectors/normalize.json.
// Работает в браузере и в Node 22: без импортов, только стандартный JS.

export const TYPES = Object.freeze([
  "text", "password", "time", "date", "number",
  "choice", "person", "document", "multi", "persons", "order",
]);
const ID_TYPES = new Set(["choice", "person", "document"]);
const LIST_TYPES = new Set(["multi", "persons", "order"]);
const TYPE_SET = new Set(TYPES);

// Категории Unicode проверяются посимвольно (по кодовым точкам), не через \w.
const RE_LETTER_OR_DIGIT = /^[\p{L}\p{N}]$/u;
const RE_MARK = /^\p{M}$/u;
// Только ASCII-цифры — так же, как в Python ([0-9], не \d).
const RE_DIGIT_GROUP = /[0-9]+/g;
const RE_ID = /^[a-z0-9_-]+$/;

/** NFC → toLowerCase → «ё»→«е» → M* удалить, не L*/N* → пробел → схлопнуть пробелы. */
export function base(s) {
  const lowered = String(s).normalize("NFC").toLowerCase().replaceAll("ё", "е");
  let out = "";
  for (const ch of lowered) {
    if (RE_LETTER_OR_DIGIT.test(ch)) out += ch;
    else if (RE_MARK.test(ch)) continue;
    else out += " ";
  }
  return out.split(" ").filter((part) => part !== "").join(" ");
}

function normId(value) {
  if (typeof value !== "string") return null;
  const v = value.toLowerCase();
  return RE_ID.test(v) ? v : null;
}

function normIds(value) {
  if (!Array.isArray(value) || value.length === 0) return null;
  const ids = [];
  for (const item of value) {
    const v = normId(item);
    if (v === null) return null;
    ids.push(v);
  }
  return ids;
}

function digitGroups(s) {
  return s.match(RE_DIGIT_GROUP) ?? [];
}

// Группа цифр → число; длинные группы заведомо вне диапазона (как _int в Python).
function toInt(group) {
  const stripped = group.replace(/^0+/, "");
  return stripped.length <= 6 ? Number(stripped || "0") : 1e7;
}

const pad = (n, width) => String(n).padStart(width, "0");

function normTime(s) {
  const groups = digitGroups(s);
  let h;
  let m;
  if (groups.length === 1) {
    const g = groups[0];
    if (g.length !== 3 && g.length !== 4) return null;
    h = toInt(g.slice(0, -2));
    m = toInt(g.slice(-2));
  } else if (groups.length === 2) {
    h = toInt(groups[0]);
    m = toInt(groups[1]);
  } else {
    return null;
  }
  if (!(h >= 0 && h <= 23 && m >= 0 && m <= 59)) return null;
  return `${pad(h, 2)}:${pad(m, 2)}`;
}

function isLeap(y) {
  return y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0);
}

function daysInMonth(y, m) {
  return [31, isLeap(y) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
}

function normDate(s, defaultYear) {
  const groups = digitGroups(s);
  let d;
  let m;
  let y;
  if (groups.length === 2) {
    if (defaultYear === undefined || defaultYear === null) {
      throw new Error("normalize('date', …): не передан defaultYear");
    }
    d = toInt(groups[0]);
    m = toInt(groups[1]);
    y = Math.trunc(Number(defaultYear));
  } else if (groups.length === 3) {
    const yg = groups[2];
    if (yg.length === 2) y = 2000 + toInt(yg);
    else if (yg.length === 4) y = toInt(yg);
    else return null;
    d = toInt(groups[0]);
    m = toInt(groups[1]);
  } else {
    return null;
  }
  if (!(y >= 1 && y <= 9999 && m >= 1 && m <= 12)) return null;
  if (!(d >= 1 && d <= daysInMonth(y, m))) return null;
  return `${pad(y, 4)}-${pad(m, 2)}-${pad(d, 2)}`;
}

function normNumber(s) {
  const digits = digitGroups(s).join("");
  if (digits === "") return null;
  return digits.replace(/^0+/, "") || "0";
}

/**
 * Нормализовать ввод по типу единицы. null — невалидный ввод.
 * Для multi/persons/order value — массив ID, для остальных — строка.
 * defaultYear нужен только для date из двух групп цифр.
 */
export function normalize(type, value, { defaultYear } = {}) {
  if (!TYPE_SET.has(type)) throw new Error(`неизвестный тип единицы: ${type}`);

  if (ID_TYPES.has(type)) return normId(value);

  if (LIST_TYPES.has(type)) {
    const ids = normIds(value);
    if (ids === null) return null;
    if (type === "order") {
      return new Set(ids).size === ids.length ? ids.join(",") : null;
    }
    // ID — только ASCII, поэтому порядок UTF-16 совпадает с порядком кодовых точек.
    return [...new Set(ids)].sort().join(",");
  }

  if (typeof value !== "string") return null;

  let result;
  if (type === "text") result = base(value);
  else if (type === "password") result = base(value).replaceAll(" ", "");
  else if (type === "time") result = normTime(value);
  else if (type === "date") result = normDate(value, defaultYear);
  else result = normNumber(value);
  return result ? result : null;
}
