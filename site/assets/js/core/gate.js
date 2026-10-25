// Профили закрытых этапов (docs/02 §3.10, docs/04 «Профили закрытых этапов»). Без DOM: тестируется в Node.
//
// Профиль «Круга» или «Кадра» этапа N ≥ 2 закрыт ключом, как страница по QR. Открытые страницы (и страницы
// ранних этапов) ссылаются на него через заглушку: href="/p/<заглушка>/#to=<slug>" data-gate="<slug>" — ключа
// в открытом файле нет. Ключи профилей этапа N и строки поиска лежат в зашифрованном пакете этапа N (поле
// `pages`). Если в прогрессе этого браузера (localStorage, тот же сайт) есть ключ этапа N, пакет
// расшифровывается и ссылка ведёт на настоящий адрес /p/<slug>/#k=<ключ> — тот же, что в QR.
//
// На другом телефоне без прогресса игры ссылки остаются заглушками — это по замыслу: этап открывает команда.

import { parseState, isCompatible, STORAGE_PREFIX } from "./state.js";
import { loadPublic, openPack } from "./game.js";

export const GATE_PARAM = "to";
/** sessionStorage: расшифрованный индекс (ключи страниц там уже лежат — detgame:page:<slug>). */
export const GATE_CACHE = "detgame:gate";

const SLUG_RE = /^[a-z0-9_-]+$/;

/** slug профиля из фрагмента «#to=<slug>» (адрес заглушки) или null. */
export function gateTarget(hash) {
  const h = String(hash ?? "").replace(/^#/, "");
  if (!h) return null;
  const slug = new URLSearchParams(h).get(GATE_PARAM);
  return slug && SLUG_RE.test(slug) ? slug : null;
}

/** Настоящий адрес профиля: тот же формат, что у QR (engine/templating.py, page_href). */
export function profileHref(entry) {
  return `/p/${entry.slug}/#k=${entry.key}`;
}

/** Поле `pages` пакетов → Map slug → {slug, type, key, name, position}. Порядок этапов не важен. */
export function pageIndex(packs) {
  const out = new Map();
  for (const n of Object.keys(packs).map(Number).sort((a, b) => a - b)) {
    for (const e of packs[n]?.pages ?? []) {
      if (e && typeof e.slug === "string" && SLUG_RE.test(e.slug) && typeof e.key === "string") {
        out.set(e.slug, { slug: e.slug, type: e.type, key: e.key, name: String(e.name ?? ""), position: e.position ?? null });
      }
    }
  }
  return out;
}

function safeGet(st, k) {
  try {
    return st ? st.getItem(k) : null;
  } catch {
    return null;
  }
}

function safeSet(st, k, v) {
  try {
    st?.setItem(k, v);
  } catch {
    /* без хранилища — просто без кеша */
  }
}

/** Этапы, ключи которых есть в прогрессе: 1..stage. */
export function openedStages(state) {
  const out = [];
  for (let n = 1; n <= state.stage; n++) if (state.keys?.[n]) out.push(n);
  return out;
}

/**
 * Профили закрытых этапов, уже открытые в прогрессе этого браузера → Map slug → entry.
 * Нет прогресса, другой набор солей, сеть или расшифровка подвели — пустая Map (ссылки остаются заглушками).
 *   storage — localStorage (прогресс), session — sessionStorage (кеш), fetchFn — fetch (тесты).
 */
export async function unlockedPages({ storage = null, session = null, fetchFn } = {}) {
  let pub;
  try {
    pub = await loadPublic({ fetchFn });
  } catch {
    return new Map();
  }
  const raw = safeGet(storage, STORAGE_PREFIX + pub.gameId);
  if (!raw) return new Map();
  let state;
  try {
    state = parseState(raw);
  } catch {
    return new Map();
  }
  if (!isCompatible(state, pub)) return new Map();
  const stages = openedStages(state);
  const sig = `${pub.saltsId}|${pub.buildId ?? ""}|${stages.join(",")}`;
  try {
    const cached = JSON.parse(safeGet(session, GATE_CACHE) || "null");
    if (cached && cached.sig === sig && Array.isArray(cached.pages)) return pageIndex({ 0: { pages: cached.pages } });
  } catch {
    /* испорченный кеш — пересобрать */
  }
  const packs = {};
  for (const n of stages) {
    try {
      packs[n] = await openPack(n, state.keys[n], { fetchFn });
    } catch {
      /* пакет не открылся — его профили остаются заглушками */
    }
  }
  const index = pageIndex(packs);
  safeSet(session, GATE_CACHE, JSON.stringify({ sig, pages: [...index.values()] }));
  return index;
}

/**
 * Слить открытый индекс поиска людей и профили из пакетов (только «Круг», type social).
 * existing — [{slug, name, position, closed}] из разметки; → новый список в порядке имён (как сортирует сборка:
 * по кодовым точкам), без повторов slug; открытые в пакете — closed: false, должность из пакета.
 */
export function mergeDirectory(existing, index) {
  const bySlug = new Map(existing.map((e) => [e.slug, { ...e }]));
  for (const e of index.values()) {
    if (e.type !== "social") continue;
    bySlug.set(e.slug, { slug: e.slug, name: e.name, position: e.position ?? "", closed: false, href: profileHref(e) });
  }
  return [...bySlug.values()].sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
}
