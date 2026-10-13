// Проверка ответов и этапы — docs/02 §3.3–3.5, docs/FORMATS.md §1, §2, §4, §7.1.
// Без DOM: тестируется в Node на синтетических пакетах.
//
// Данные загружаются по абсолютным путям (FORMATS F18): /data/public.json,
// /data/pack-<n>.json, /data/finale.json. fetch внедряется (опция fetchFn)
// для тестов; по умолчанию — globalThis.fetch.

import { normalize } from "./normalize.js";
import {
  b64uDecode,
  b64uEncode,
  utf8,
  utf8Decode,
  hkdf,
  open,
  packInfo,
  answerKey,
  checkAnswer,
  startKey as cryptoStartKey,
  stageKey,
  FINALE_INFO,
  CryptoError,
} from "./crypto.js";

export const DATA_ROOT = "/data/";
const FORMAT_VERSION = 1;
const WRONG_PREFIX = "detgame/wrong/v1|";
const FIELD_SEP = "\x1f";

/** Ошибка загрузки или расшифровки данных (пакет, развязка, public.json). */
export class GameDataError extends Error {
  constructor(code, message) {
    super(message || code);
    this.name = "GameDataError";
    this.code = code; // "network" | "format" | "decrypt"
  }
}

async function fetchJson(path, fetchFn = globalThis.fetch) {
  let res;
  try {
    res = await fetchFn(path, { cache: "no-cache" });
  } catch (e) {
    throw new GameDataError("network", `${path}: ${e?.message ?? e}`);
  }
  if (!res.ok) throw new GameDataError("network", `${path}: HTTP ${res.status}`);
  try {
    return await res.json();
  } catch {
    throw new GameDataError("format", `${path}: не JSON`);
  }
}

function parseInner(bytes, what) {
  let obj;
  try {
    obj = JSON.parse(utf8Decode(bytes));
  } catch {
    throw new GameDataError("format", `${what}: повреждённый JSON`);
  }
  if (!obj || obj.v !== FORMAT_VERSION) throw new GameDataError("format", `${what}: неизвестная версия`);
  return obj;
}

/** Ключ из прогресса (b64u) или байты → Uint8Array. */
export function keyBytes(k) {
  return typeof k === "string" ? b64uDecode(k) : k;
}

// ---------------------------------------------------------------- public.json и пакеты

/** /data/public.json (FORMATS §1). */
export async function loadPublic({ fetchFn } = {}) {
  const pub = await fetchJson(DATA_ROOT + "public.json", fetchFn);
  if (!pub || pub.v !== FORMAT_VERSION || typeof pub.gameId !== "string" || typeof pub.saltsId !== "string") {
    throw new GameDataError("format", "public.json: неизвестный формат");
  }
  return pub;
}

/** K1 = PBKDF2("detgame/stage/v1|start", saltStart, iter.stage). */
export function startKey(pub) {
  return cryptoStartKey(b64uDecode(pub.saltStart), pub.iter.stage);
}

/**
 * Открыть пакет этапа n ключом K_n (байты или b64u).
 * box — уже загруженный контейнер (иначе fetch /data/pack-n.json).
 * Ошибка расшифровки → GameDataError("decrypt"): «Пакет не расшифровался».
 */
export async function openPack(n, key, { box, fetchFn } = {}) {
  const container = box ?? (await fetchJson(`${DATA_ROOT}pack-${n}.json`, fetchFn));
  let pt;
  try {
    const k = await hkdf(keyBytes(key), packInfo(n));
    pt = await open(k, container, `pack/${n}`);
  } catch (e) {
    if (e instanceof CryptoError) throw new GameDataError("decrypt", `pack-${n}: ${e.message}`);
    throw e;
  }
  const pack = parseInner(pt, `pack-${n}`);
  if (pack.n !== n) throw new GameDataError("format", `pack-${n}: внутри этап ${pack.n}`);
  return pack;
}

/** Открыть пакеты 1..state.stage ключами из прогресса. → { [n]: pack } */
export async function openPacks(state, opts = {}) {
  const packs = {};
  for (let n = 1; n <= state.stage; n++) {
    const key = state.keys[n];
    if (!key) throw new GameDataError("decrypt", `нет ключа этапа ${n}`);
    packs[n] = await openPack(n, key, { ...opts, box: opts.boxes?.[n] });
  }
  return packs;
}

/** Развязка (FORMATS §4, F9): скачивается только после последнего ответа финала. */
export async function openFinale(keyLast, { box, fetchFn } = {}) {
  const container = box ?? (await fetchJson(DATA_ROOT + "finale.json", fetchFn));
  let pt;
  try {
    const k = await hkdf(keyBytes(keyLast), FINALE_INFO);
    pt = await open(k, container, "finale");
  } catch (e) {
    if (e instanceof CryptoError) throw new GameDataError("decrypt", `finale: ${e.message}`);
    throw e;
  }
  return parseInner(pt, "finale");
}

// ---------------------------------------------------------------- проверка ответов

/**
 * Нормализовать сырой ввод единицы. Для multi/persons/order — массив ID.
 * null — ввод невалиден (не попытка, подсказка формата).
 */
export function normalizeInput(unit, raw, pub) {
  if (raw === undefined || raw === null) return null;
  if (typeof raw === "string" && raw.trim() === "") return null;
  if (Array.isArray(raw) && raw.length === 0) return null;
  return normalize(unit.type, raw, { defaultYear: pub.defaultYear });
}

/**
 * Проверить одну единицу: один PBKDF2 и перебор записей (FORMATS §2.4 п. 1).
 * → { valid, correct, canon, normalized }
 */
export async function checkUnit(unit, rawInput, pub) {
  const normalized = normalizeInput(unit, rawInput, pub);
  if (normalized === null) return { valid: false, correct: false, canon: null, normalized: null };
  const key = await answerKey(unit.path, normalized, b64uDecode(unit.salt), pub.iter.answer);
  const canon = await checkAnswer(key, unit.path, unit.entries);
  return { valid: true, correct: canon !== null, canon, normalized };
}

/**
 * Проверить вопрос. inputs: для формы — { fieldId: raw }, иначе — raw.
 * Форма: сначала нормализуются все поля (если хоть одно невалидно — не попытка,
 * invalid = [fieldId…] для подсказки формата), затем все поля проверяются
 * параллельно (Promise.all). Вопрос засчитан, только если верны ВСЕ поля;
 * какое поле неверно, результат не сообщает.
 * → { valid, correct, canon, normalized, invalid }
 *   canon/normalized формы — { fieldId: … } в порядке полей.
 */
export async function checkQuestion(q, inputs, pub) {
  if (q.type !== "form") {
    const r = await checkUnit(q.unit, inputs, pub);
    return { ...r, invalid: r.valid ? [] : [q.id] };
  }
  const fields = q.fields;
  const raw = inputs ?? {};
  const invalid = fields.filter((f) => normalizeInput(f.unit, raw[f.id], pub) === null).map((f) => f.id);
  if (invalid.length) return { valid: false, correct: false, canon: null, normalized: null, invalid };
  const results = await Promise.all(fields.map((f) => checkUnit(f.unit, raw[f.id], pub)));
  const normalized = {};
  fields.forEach((f, i) => (normalized[f.id] = results[i].normalized));
  const correct = results.every((r) => r.correct);
  let canon = null;
  if (correct) {
    canon = {};
    fields.forEach((f, i) => (canon[f.id] = results[i].canon));
  }
  return { valid: true, correct, canon, normalized, invalid: [] };
}

/**
 * Только нормализовать ввод вопроса (финал: ответ фиксируется сразу, а
 * проверяется один раз после последнего ответа — FORMATS §7, final.correct).
 * → { valid, normalized, invalid }; normalized формы — { fieldId: x }.
 */
export function normalizeQuestion(q, inputs, pub) {
  if (q.type !== "form") {
    const x = normalizeInput(q.unit, inputs, pub);
    return { valid: x !== null, normalized: x, invalid: x === null ? [q.id] : [] };
  }
  const raw = inputs ?? {};
  const normalized = {};
  const invalid = [];
  for (const f of q.fields) {
    const x = normalizeInput(f.unit, raw[f.id], pub);
    if (x === null) invalid.push(f.id);
    normalized[f.id] = x;
  }
  return invalid.length ? { valid: false, normalized: null, invalid } : { valid: true, normalized, invalid: [] };
}

/** Проверить уже нормализованное значение единицы → канон или null. */
export async function checkNormalizedUnit(unit, x, pub) {
  if (x === null || x === undefined) return null;
  const key = await answerKey(unit.path, x, b64uDecode(unit.salt), pub.iter.answer);
  return checkAnswer(key, unit.path, unit.entries);
}

/** Проверить нормализованный ответ вопроса (форма — все поля параллельно) → boolean. */
export async function checkQuestionNormalized(q, normalized, pub) {
  if (q.type !== "form") return (await checkNormalizedUnit(q.unit, normalized, pub)) !== null;
  const res = await Promise.all(q.fields.map((f) => checkNormalizedUnit(f.unit, normalized?.[f.id], pub)));
  return res.every((c) => c !== null);
}

/**
 * wrongHash (FORMATS §7.1, F17):
 *   body = простой вопрос — normalized; форма — join("\x1f", fieldId + "=" + normalized) в порядке полей;
 *   hex(SHA-256(UTF8("detgame/wrong/v1|" + qpath + "|" + body))).
 */
export async function wrongHash(q, normalized) {
  const body =
    q.type === "form"
      ? q.fields.map((f) => `${f.id}=${normalized[f.id]}`).join(FIELD_SEP)
      : String(normalized);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", utf8(WRONG_PREFIX + q.path + "|" + body));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

// ---------------------------------------------------------------- этапы

export const mandatory = (pack) => pack.questions.filter((q) => q.kind === "mandatory");
export const bonuses = (pack) => pack.questions.filter((q) => q.kind === "bonus");

/** Все обязательные вопросы этапа решены (по units прогресса). */
export function isStageComplete(pack, units) {
  return mandatory(pack).every((q) => units[q.path]?.status === "solved");
}

/**
 * Пары (путь единицы, канон) для stageSecret (FORMATS §2.4 п. 3): обязательные
 * вопросы в порядке пакета, поля формы — в порядке fields.
 * Бросает, если не все обязательные решены.
 */
export function stagePairs(pack, units) {
  const pairs = [];
  for (const q of mandatory(pack)) {
    const u = units[q.path];
    if (u?.status !== "solved") throw new Error(`Вопрос ${q.path} не решён`);
    if (q.type === "form") {
      for (const f of q.fields) pairs.push([f.unit.path, u.canon[f.id]]);
    } else {
      pairs.push([q.unit.path, u.canon]);
    }
  }
  return pairs;
}

/** K_{n+1} → b64u. null на последнем этапе. */
export async function nextStageKey(pack, units, pub) {
  if (!pack.saltStage) return null;
  const k = await stageKey(pack.n, stagePairs(pack, units), b64uDecode(pack.saltStage), pub.iter.stage);
  return b64uEncode(k);
}

/** Порядок вопросов финала: final по порядку пакета, затем bonus (PLAN C4). */
export function finalQuestions(pack) {
  return [...pack.questions.filter((q) => q.kind === "final"), ...pack.questions.filter((q) => q.kind === "bonus")];
}

/** Пути бонусов этапов 1..last-1 — закрываются при «Начать финал». */
export function earlierBonusPaths(packs, lastStage) {
  const out = [];
  for (const [n, pack] of Object.entries(packs)) {
    if (Number(n) < lastStage) out.push(...bonuses(pack).map((q) => q.path));
  }
  return out;
}

// ---------------------------------------------------------------- документы и ранги

/**
 * Полученные документы (docs/01 §3, PLAN C8): документы всех видов из открытых
 * пакетов плюс результаты экспертиз. labDocs — { id: title } (из записей экспертиз).
 * → [{ id, stage, kind: "paper"|"online"|"lab", title, link }] по порядку получения.
 */
export function receivedDocuments(packs, state, labDocs = {}) {
  const out = [];
  const seen = new Set();
  const stages = Object.keys(packs).map(Number).sort((a, b) => a - b);
  for (const n of stages) {
    for (const d of packs[n].documents ?? []) {
      if (seen.has(d.id)) continue;
      seen.add(d.id);
      out.push({ ...d });
    }
  }
  for (const id of state.docs ?? []) {
    if (seen.has(id)) continue;
    seen.add(id);
    out.push({ id, stage: null, kind: "lab", title: labDocs[id] ?? id, link: null });
  }
  return out;
}

/** Ранг по счёту: ranks из public.json, границы включительно, null — без границы. */
export function rankFor(score, ranks) {
  for (const r of ranks) {
    if ((r.min === null || score >= r.min) && (r.max === null || score <= r.max)) return r.name;
  }
  return ranks.length ? ranks[ranks.length - 1].name : "";
}
