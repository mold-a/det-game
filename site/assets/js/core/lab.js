// Экспертизы — docs/01 §7, docs/02 §3.6, docs/FORMATS.md §2.3, §3.
// Без DOM: тестируется в Node.
//
// Запрос: { object, type, basis, params } — params уже нормализованы
// (normalizeParams) в порядке object.params.

import { normalize } from "./normalize.js";
import { hkdf, labInfo, tryEntries, utf8, utf8Decode, b64uEncode, b64uDecode } from "./crypto.js";

const LAB_AAD = "lab";

/**
 * Каталог лаборатории из открытых пакетов: виды — из pack-1, объекты —
 * объединение по пакетам 1..stage, сортировка по ord (FORMATS §2.3).
 */
export function labCatalog(packs) {
  const types = [];
  const objects = [];
  const seenT = new Set();
  const seenO = new Set();
  for (const pack of Object.values(packs)) {
    for (const t of pack.lab?.types ?? []) if (!seenT.has(t.id) && seenT.add(t.id)) types.push(t);
    for (const o of pack.lab?.objects ?? []) if (!seenO.has(o.id) && seenO.add(o.id)) objects.push(o);
  }
  const byOrd = (a, b) => a.ord - b.ord;
  return { types: types.sort(byOrd), objects: objects.sort(byOrd) };
}

/**
 * Нормализовать параметры объекта. raw — массив строк в порядке object.params.
 * → { params: string[] } или { params: null, invalid: [paramId…] } (подсказка
 * формата; запрос не отправляется, штрафа нет).
 */
export function normalizeParams(object, raw, { defaultYear } = {}) {
  const defs = object.params ?? [];
  const params = [];
  const invalid = [];
  defs.forEach((def, i) => {
    const v = raw?.[i];
    const x = v === undefined || v === null || String(v).trim() === "" ? null : normalize(def.type, String(v), { defaultYear });
    if (x === null) invalid.push(def.id);
    params.push(x);
  });
  return invalid.length ? { params: null, invalid } : { params, invalid: [] };
}

/** p = params.join("|") (пусто без параметров). */
export const paramString = (params) => (params.length ? params.join("|") : "");

/** fp = b64u(SHA-256(UTF8(object|type|basis|p))) — FORMATS F7. */
export async function labFingerprint({ object, type, basis, params }) {
  const s = `${object}|${type}|${basis}|${paramString(params)}`;
  const digest = await globalThis.crypto.subtle.digest("SHA-256", utf8(s));
  return b64uEncode(new Uint8Array(digest));
}

/**
 * Поиск результата: этапы от `stage` вниз до 1, ключ HKDF(K_n, labInfo),
 * перебор pack-n.lab.entries; первый успех — самый поздний этап.
 *   keys  — { n: K_n (b64u или байты) };
 *   packs — { n: pack }.
 * → { stage, entry } | null. entry — внутренний JSON записи (FORMATS §3.2).
 */
export async function labRequest(req, { stage, keys, packs }) {
  const info = labInfo(req.object, req.type, req.basis, req.params);
  for (let n = stage; n >= 1; n--) {
    const pack = packs[n];
    const kn = keys[n];
    if (!pack || !kn) continue;
    const entries = pack.lab?.entries ?? [];
    if (!entries.length) continue;
    const key = await hkdf(typeof kn === "string" ? b64uDecode(kn) : kn, info);
    const pt = await tryEntries(key, entries, LAB_AAD);
    if (pt === null) continue;
    const entry = JSON.parse(utf8Decode(pt));
    if (entry?.v !== 1) continue;
    return { stage: n, entry };
  }
  return null;
}

/**
 * Восстановить результаты выполненных экспертиз из архива lab.log (F15):
 * результат не хранится, а выводится повторно (только HKDF — быстро).
 * → { [fp]: { stage, entry } } для записей с ok = true.
 */
export async function restoreLabResults(labLog, ctx) {
  const out = {};
  for (const e of labLog ?? []) {
    if (!e.ok || out[e.fp]) continue;
    const r = await labRequest({ object: e.object, type: e.type, basis: e.basis, params: e.params ?? [] }, ctx);
    if (r) out[e.fp] = r;
  }
  return out;
}

/** { docId: title } для панели документов — из восстановленных результатов. */
export function labDocTitles(results) {
  const out = {};
  for (const r of Object.values(results)) if (r.entry.doc) out[r.entry.doc] = r.entry.title;
  return out;
}

// ---------------------------------------------------------------- заявка «Призмы» (docs/01 §7)

/**
 * Разобрать заявку до криптографии: текст объекта → объект каталога
 * (core/labmatch.js, docs/02 «Распознавание объекта»), заполненность и параметры.
 * Ни один из исходов, кроме "ready", не штрафуется и в архив не попадает.
 *
 *   text    — что команда написала в поле «Объект исследования»;
 *   type    — id вида исследования ("" — не выбран);
 *   basis   — id документа-основания ("" — не выбран);
 *   params  — сырые строки параметров в порядке object.params;
 *   objects — объекты каталога открытых этапов в порядке каталога (labCatalog().objects);
 *   resolve — resolveObject(text, objects) из core/labmatch.js (внедряется: так модуль
 *             не зависит от алгоритма распознавания и тестируется отдельно).
 * →
 *   { status: "empty" }                                   поле объекта пустое;
 *   { status: "none" }                                    предмета нет в описи;
 *   { status: "ambiguous", objects: [obj…] }              уточнить (в порядке каталога);
 *   { status: "incomplete", object, missing: ["type"|"basis"…] };
 *   { status: "format", object, invalid: [paramId…], paramType, empty };
 *   { status: "ready", object, req: { object, type, basis, params } }.
 */
export function prepareLabRequest({ text, type, basis, params = [], objects, resolve, defaultYear }) {
  if (String(text ?? "").trim() === "") return { status: "empty" };
  const r = resolve(String(text), objects);
  if (r.status === "none") return { status: "none" };
  if (r.status === "ambiguous") {
    return { status: "ambiguous", objects: r.ids.map((id) => objects.find((o) => o.id === id)).filter(Boolean) };
  }
  const object = objects.find((o) => o.id === r.id);
  if (!object) return { status: "none" };
  const missing = [];
  if (!type) missing.push("type");
  if (!basis) missing.push("basis");
  if (missing.length) return { status: "incomplete", object, missing };
  const norm = normalizeParams(object, params, { defaultYear });
  if (norm.params === null) {
    const defs = object.params ?? [];
    const i = defs.findIndex((p) => p.id === norm.invalid[0]);
    const empty = String(params?.[i] ?? "").trim() === "";
    return { status: "format", object, invalid: norm.invalid, paramType: defs[i]?.type ?? null, empty };
  }
  return { status: "ready", object, req: { object: object.id, type, basis, params: norm.params } };
}

/**
 * Строки раздела «Мои заявки» из архива lab.log (F15): новые сверху, у каждой —
 * порядковый номер заявки команды (1 — первая), названия объекта и вида из
 * каталога, итог. Повторные записи одного отпечатка (отказ, затем заключение
 * после перехода этапа) — отдельные заявки: так их видела команда.
 *   results — { [fp]: { entry } } восстановленные результаты (restoreLabResults).
 * → [{ no, fp, t, object, objectTitle, ref, type, typeTitle, basis, params, ok, doc, entry }]
 */
export function labOrders(labLog, catalog, results = {}) {
  const title = (list, id) => list.find((x) => x.id === id)?.title ?? id;
  const rows = (labLog ?? []).map((e, i) => {
    const obj = catalog.objects.find((o) => o.id === e.object);
    return {
      no: i + 1,
      fp: e.fp,
      t: e.t ?? "",
      object: e.object,
      objectTitle: obj?.title ?? e.object,
      ref: obj?.ref ?? "",
      type: e.type,
      typeTitle: title(catalog.types, e.type),
      basis: e.basis,
      params: e.params ?? [],
      ok: e.ok === true,
      doc: e.doc ?? null,
      entry: e.ok ? results[e.fp]?.entry ?? null : null,
    };
  });
  return rows.reverse();
}
