// Криптография — docs/02-architecture.md §3.
// Зеркало engine/crypto.py. Только Web Crypto (globalThis.crypto.subtle), без библиотек;
// работает в браузере (защищённый контекст) и в Node 22. PBKDF2 и HKDF — через deriveBits
// (ключи этапов хранятся в прогрессе как байты); ключи AES импортируются неэкспортируемыми.

export const KEY_LEN = 32;
export const NONCE_LEN = 12;
export const TAG_LEN = 16;
const CONTAINER_VERSION = 1;
const CONTAINER_ALG = "A256GCM";

const ANSWER_PREFIX = "detgame/answer/v1|";
const STAGE_PREFIX = "detgame/stage/v1|";
const START_SECRET = "detgame/stage/v1|start";
const PACK_PREFIX = "detgame/pack/v1|";
const LAB_PREFIX = "detgame/lab/v1|";
const CLOUD_PREFIX = "detgame/cloud/v1|";
const UNIT_SEP = "\x1f";

const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8", { fatal: true });

/** Неверный ключ, AAD, повреждённый контейнер или кодировка. */
export class CryptoError extends Error {
  constructor(message) {
    super(message);
    this.name = "CryptoError";
  }
}

/** Есть ли рабочий Web Crypto (защищённый контекст). Никогда не бросает исключений. */
export function isCryptoAvailable() {
  try {
    if (globalThis.isSecureContext === false) return false;
    const subtle = globalThis.crypto?.subtle;
    return Boolean(
      subtle &&
        typeof subtle.deriveBits === "function" &&
        typeof subtle.importKey === "function" &&
        typeof subtle.decrypt === "function" &&
        typeof globalThis.crypto.getRandomValues === "function",
    );
  } catch {
    return false;
  }
}

function subtle() {
  const s = globalThis.crypto?.subtle;
  if (!s) throw new CryptoError("Web Crypto недоступен: нужен HTTPS или localhost");
  return s;
}

// --- кодирование -------------------------------------------------------------------

export function utf8(s) {
  return encoder.encode(s);
}

export function utf8Decode(bytes) {
  try {
    return decoder.decode(bytes);
  } catch {
    throw new CryptoError("неверный UTF-8");
  }
}

function toBytes(x) {
  if (typeof x === "string") return utf8(x);
  if (x instanceof Uint8Array) return x;
  if (x instanceof ArrayBuffer) return new Uint8Array(x);
  if (ArrayBuffer.isView(x)) return new Uint8Array(x.buffer, x.byteOffset, x.byteLength);
  throw new TypeError("ожидались байты или строка");
}

export function concatBytes(...parts) {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let off = 0;
  for (const p of parts) {
    out.set(p, off);
    off += p.length;
  }
  return out;
}

export function bytesEqual(a, b) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) if (a[i] !== b[i]) return false;
  return true;
}

// Собственный base64url: Uint8Array.fromBase64 нет в Node 22 и на старых телефонах.
export function b64uEncode(bytes) {
  const u8 = toBytes(bytes);
  let bin = "";
  const CHUNK = 0x8000;
  for (let i = 0; i < u8.length; i += CHUNK) {
    bin += String.fromCharCode.apply(null, u8.subarray(i, i + CHUNK));
  }
  return btoa(bin).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

const RE_B64U = /^[A-Za-z0-9_-]*$/;

/** Строгий base64url без «=»: только алфавит, допустимая длина, каноническая форма. */
export function b64uDecode(s) {
  if (typeof s !== "string" || !RE_B64U.test(s) || s.length % 4 === 1) {
    throw new CryptoError("неверная строка base64url");
  }
  const b64 = s.replaceAll("-", "+").replaceAll("_", "/") + "=".repeat((4 - (s.length % 4)) % 4);
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i);
  if (b64uEncode(out) !== s) throw new CryptoError("неканоническая строка base64url");
  return out;
}

export function randomBytes(n) {
  const out = new Uint8Array(n);
  globalThis.crypto.getRandomValues(out);
  return out;
}

// --- выработка ключей ----------------------------------------------------------------

/** PBKDF2-HMAC-SHA256 → 32 байта (Uint8Array). password — байты или строка (UTF-8). */
export async function pbkdf2(password, salt, iterations) {
  if (!(iterations >= 1)) throw new RangeError("iterations должно быть ≥ 1");
  const base = await subtle().importKey("raw", toBytes(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await subtle().deriveBits(
    { name: "PBKDF2", hash: "SHA-256", salt: toBytes(salt), iterations },
    base,
    KEY_LEN * 8,
  );
  return new Uint8Array(bits);
}

const HKDF_SALT = new Uint8Array(32); // явно с обеих сторон (R1)

/** HKDF-SHA256, соль — 32 нулевых байта, 32 байта. info — байты или строка (UTF-8). */
export async function hkdf(ikm, info) {
  const base = await subtle().importKey("raw", toBytes(ikm), "HKDF", false, ["deriveBits"]);
  const bits = await subtle().deriveBits(
    { name: "HKDF", hash: "SHA-256", salt: HKDF_SALT, info: toBytes(info) },
    base,
    KEY_LEN * 8,
  );
  return new Uint8Array(bits);
}

// --- AES-256-GCM ---------------------------------------------------------------------

async function aesKey(key, usage) {
  const raw = toBytes(key);
  if (raw.length !== KEY_LEN) throw new CryptoError(`ключ должен быть ${KEY_LEN} байта`);
  return subtle().importKey("raw", raw, { name: "AES-GCM" }, false, [usage]);
}

/**
 * Зашифровать в контейнер {v, alg, aad, n, c} (docs/02 §3.1).
 * В игре не нужен — для тестов и tests/js/make_vectors.mjs. _nonce — только для тестов.
 */
export async function seal(key, plaintext, aad, { _nonce } = {}) {
  if (typeof aad !== "string" || aad === "") throw new CryptoError("AAD обязателен");
  const nonce = _nonce ? toBytes(_nonce) : randomBytes(NONCE_LEN);
  if (nonce.length !== NONCE_LEN) throw new CryptoError(`nonce должен быть ${NONCE_LEN} байт`);
  const k = await aesKey(key, "encrypt");
  const ct = await subtle().encrypt(
    { name: "AES-GCM", iv: nonce, additionalData: utf8(aad), tagLength: TAG_LEN * 8 },
    k,
    toBytes(plaintext),
  );
  return { v: CONTAINER_VERSION, alg: CONTAINER_ALG, aad, n: b64uEncode(nonce), c: b64uEncode(new Uint8Array(ct)) };
}

function parseContainer(container) {
  if (!container || typeof container !== "object") throw new CryptoError("контейнер должен быть объектом");
  if (container.v !== CONTAINER_VERSION || container.alg !== CONTAINER_ALG) {
    throw new CryptoError("неизвестная версия или алгоритм контейнера");
  }
  if (typeof container.aad !== "string" || container.aad === "") throw new CryptoError("в контейнере нет AAD");
  const nonce = b64uDecode(container.n);
  const ct = b64uDecode(container.c);
  if (nonce.length !== NONCE_LEN || ct.length < TAG_LEN) throw new CryptoError("повреждённый контейнер");
  return { aad: container.aad, nonce, ct };
}

async function decryptWith(k, nonce, ct, aad) {
  try {
    const pt = await subtle().decrypt(
      { name: "AES-GCM", iv: nonce, additionalData: utf8(aad), tagLength: TAG_LEN * 8 },
      k,
      ct,
    );
    return new Uint8Array(pt);
  } catch {
    throw new CryptoError("неверный ключ или AAD");
  }
}

/**
 * Расшифровать контейнер → Uint8Array. aad — ожидаемый AAD: если передан и не совпадает
 * с записанным в контейнере, это ошибка. Неверный ключ/AAD/повреждение → CryptoError.
 */
export async function open(key, container, aad) {
  const parsed = parseContainer(container);
  if (aad !== undefined && aad !== null && aad !== parsed.aad) {
    throw new CryptoError("AAD контейнера не совпадает с ожидаемым");
  }
  const k = await aesKey(key, "decrypt");
  return decryptWith(k, parsed.nonce, parsed.ct, parsed.aad);
}

/**
 * Попробовать расшифровать записи ключом; первая удачная → Uint8Array, иначе null.
 * Записи с другим AAD или повреждённые пропускаются. Ключ импортируется один раз.
 */
export async function tryEntries(key, entries, aad) {
  const k = await aesKey(key, "decrypt");
  for (const entry of entries) {
    let parsed;
    try {
      parsed = parseContainer(entry);
    } catch {
      continue;
    }
    if (parsed.aad !== aad) continue;
    try {
      return await decryptWith(k, parsed.nonce, parsed.ct, parsed.aad);
    } catch {
      // не тот ключ — следующая запись
    }
  }
  return null;
}

/** Медиафайл nonce(12) ‖ ciphertext ‖ tag(16) (docs/02 §4а). Для тестов. */
export async function sealMedia(key, data, aad, { _nonce } = {}) {
  if (!aad) throw new CryptoError("AAD обязателен");
  const nonce = _nonce ? toBytes(_nonce) : randomBytes(NONCE_LEN);
  const k = await aesKey(key, "encrypt");
  const ct = await subtle().encrypt(
    { name: "AES-GCM", iv: nonce, additionalData: utf8(aad), tagLength: TAG_LEN * 8 },
    k,
    toBytes(data),
  );
  return concatBytes(nonce, new Uint8Array(ct));
}

export async function openMedia(key, blob, aad) {
  const u8 = toBytes(blob);
  if (u8.length < NONCE_LEN + TAG_LEN) throw new CryptoError("повреждённый медиафайл");
  const k = await aesKey(key, "decrypt");
  return decryptWith(k, u8.subarray(0, NONCE_LEN), u8.subarray(NONCE_LEN), aad);
}

// --- строки и ключи схемы (docs/02 §3.3–3.9) ----------------------------------------

export function answerSecret(path, normalized) {
  return ANSWER_PREFIX + path + "|" + normalized;
}

/** K(x) = PBKDF2(UTF8("detgame/answer/v1|" + path + "|" + x), salt_u, ITER_ANSWER). */
export function answerKey(path, normalized, salt, iters) {
  return pbkdf2(utf8(answerSecret(path, normalized)), salt, iters);
}

export function answerAad(path) {
  return "ans/" + path;
}

/** Ключ из нормализованного ввода → канонический ответ или null (неверно). Поле p (выравнивание) игнорируется. */
export async function checkAnswer(key, path, entries) {
  const pt = await tryEntries(key, entries, answerAad(path));
  if (pt === null) return null;
  const c = JSON.parse(utf8Decode(pt)).c;
  return typeof c === "string" ? c : null;
}

// Выравнивание открытого текста записей-проверок (docs/02 §3.3), как в engine/crypto.py.
export const ANSWER_PT_BLOCK = 64;
export const ANSWER_PT_MIN = 128;

/** Длина открытого текста записи: кратна 64 и не меньше 128. */
export function answerPlaintextLen(canonical) {
  const need = utf8(JSON.stringify({ c: canonical, p: "" })).length;
  return Math.max(ANSWER_PT_MIN, Math.ceil(need / ANSWER_PT_BLOCK) * ANSWER_PT_BLOCK);
}

/** UTF8(JSON {"c": canonical, "p": <пробелы>}) выровненной длины. */
export function answerPlaintext(canonical) {
  const baseLen = utf8(JSON.stringify({ c: canonical, p: "" })).length;
  return utf8(JSON.stringify({ c: canonical, p: " ".repeat(answerPlaintextLen(canonical) - baseLen) }));
}

/** Запись-проверка ответа, aad = "ans/" + path. В игре не нужна — для тестов. */
export function sealAnswer(key, path, canonical, opts) {
  return seal(key, answerPlaintext(canonical), answerAad(path), opts);
}

/** K1 = PBKDF2(UTF8("detgame/stage/v1|start"), salt_start, ITER_STAGE). */
export function startKey(salt, iters) {
  return pbkdf2(utf8(START_SECRET), salt, iters);
}

/** "detgame/stage/v1|" + N + "\x1f" + "\x1f".join(path + "=" + canon); pairs — [[path, canon], …]. */
export function stageSecret(n, pairs) {
  return STAGE_PREFIX + String(n) + UNIT_SEP + pairs.map(([p, c]) => p + "=" + c).join(UNIT_SEP);
}

/** K_{N+1} = PBKDF2(UTF8(secret_N), salt_stage_N, ITER_STAGE). */
export function stageKey(n, pairs, salt, iters) {
  return pbkdf2(utf8(stageSecret(n, pairs)), salt, iters);
}

export function packInfo(n) {
  return utf8(PACK_PREFIX + String(n));
}

/** "detgame/lab/v1|" + object + "|" + type + "|" + basis + "|" + params.join("|") — завершающий "|" всегда. */
export function labInfo(object, type, basis, params) {
  return utf8(LAB_PREFIX + object + "|" + type + "|" + basis + "|" + params.join("|"));
}

export const FINALE_INFO = utf8("detgame/finale/v1");

/** PBKDF2(UTF8("detgame/cloud/v1|" + password(ввод)), salt_cloud, ITER_STAGE). */
export function cloudKey(passwordNorm, salt, iters) {
  return pbkdf2(utf8(CLOUD_PREFIX + passwordNorm), salt, iters);
}
