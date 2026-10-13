// Криптография (docs/02 §3): JS расшифровывает и сверяет то, что сделал Python
// (tests/vectors/crypto.json, `python -m engine vectors`).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import * as c from "../../site/assets/js/core/crypto.js";
import { normalize } from "../../site/assets/js/core/normalize.js";

const V = JSON.parse(readFileSync(new URL("../vectors/crypto.json", import.meta.url), "utf8"));
const D = c.b64uDecode;
const hex = (u8) => Buffer.from(u8).toString("hex");
const fromHex = (h) => new Uint8Array(Buffer.from(h, "hex"));
const text = (u8) => new TextDecoder().decode(u8);

test("isCryptoAvailable() в Node 22 — true и не бросает", () => {
  assert.equal(c.isCryptoAvailable(), true);
});

test("isCryptoAvailable() без защищённого контекста — false", () => {
  const desc = Object.getOwnPropertyDescriptor(globalThis, "isSecureContext");
  Object.defineProperty(globalThis, "isSecureContext", { value: false, configurable: true });
  try {
    assert.equal(c.isCryptoAvailable(), false);
  } finally {
    if (desc) Object.defineProperty(globalThis, "isSecureContext", desc);
    else delete globalThis.isSecureContext;
  }
});

test("base64url: валидные векторы в обе стороны", () => {
  for (const v of V.b64u.valid) {
    assert.equal(c.b64uEncode(fromHex(v.hex)), v.b64u);
    assert.equal(hex(c.b64uDecode(v.b64u)), v.hex);
  }
});

test("base64url: невалидные строки отвергаются так же, как в Python", () => {
  for (const s of V.b64u.invalid) assert.throws(() => c.b64uDecode(s), c.CryptoError, JSON.stringify(s));
  assert.throws(() => c.b64uDecode(null), c.CryptoError);
});

test("base64url: большой массив (больше чанка)", () => {
  const big = new Uint8Array(100_000).map((_, i) => (i * 7) & 0xff);
  assert.deepEqual(c.b64uDecode(c.b64uEncode(big)), big);
});

for (const v of V.pbkdf2) {
  test(`PBKDF2 ${v.iterations} итераций: ${v.password}`, async () => {
    assert.equal(hex(c.utf8(v.password)), v.password_hex);
    const key = await c.pbkdf2(c.utf8(v.password), D(v.salt), v.iterations);
    assert.equal(c.b64uEncode(key), v.key);
    // строка = UTF-8 байты
    assert.equal(c.b64uEncode(await c.pbkdf2(v.password, D(v.salt), v.iterations)), v.key);
  });
}

for (const v of V.hkdf) {
  test(`HKDF: ${v.info}`, async () => {
    assert.equal(c.b64uEncode(await c.hkdf(D(v.ikm), c.utf8(v.info))), v.okm);
  });
}

for (const v of V.aesgcm) {
  test(`AES-GCM: контейнер Python, aad=${v.aad}`, async () => {
    const key = D(v.key);
    assert.equal(text(await c.open(key, v.container)), v.plaintext);
    assert.equal(text(await c.open(key, v.container, v.aad)), v.plaintext);
    // тот же nonce → побайтно тот же контейнер
    assert.deepEqual(await c.seal(key, c.utf8(v.plaintext), v.aad, { _nonce: D(v.container.n) }), v.container);
  });

  test(`AES-GCM: неверный ключ и AAD → ошибка, aad=${v.aad}`, async () => {
    const key = D(v.key);
    const wrong = key.slice();
    wrong[0] ^= 1;
    await assert.rejects(c.open(wrong, v.container), c.CryptoError);
    await assert.rejects(c.open(key, { ...v.container, aad: v.container.aad + "x" }), c.CryptoError);
    await assert.rejects(c.open(key, v.container, "pack/9"), c.CryptoError);
    const tampered = D(v.container.c);
    tampered[tampered.length - 1] ^= 1;
    await assert.rejects(c.open(key, { ...v.container, c: c.b64uEncode(tampered) }), c.CryptoError);
  });
}

test("AES-GCM: повреждённые контейнеры → CryptoError", async () => {
  const bad = [
    null,
    {},
    { v: 2, alg: "A256GCM", aad: "x", n: "AAAAAAAAAAAAAAAA", c: "AAAAAAAAAAAAAAAAAAAAAA" },
    { v: 1, alg: "A128GCM", aad: "x", n: "AAAAAAAAAAAAAAAA", c: "AAAAAAAAAAAAAAAAAAAAAA" },
    { v: 1, alg: "A256GCM", aad: "", n: "AAAAAAAAAAAAAAAA", c: "AAAAAAAAAAAAAAAAAAAAAA" },
    { v: 1, alg: "A256GCM", aad: "x", n: "AAAA", c: "AAAAAAAAAAAAAAAAAAAAAA" },
    { v: 1, alg: "A256GCM", aad: "x", n: "AAAAAAAAAAAAAAAA", c: "AAAA" },
    { v: 1, alg: "A256GCM", aad: "x", n: "AAAAAAAAAAAAAAAA=", c: "AAAAAAAAAAAAAAAAAAAAAA" },
  ];
  for (const box of bad) await assert.rejects(c.open(new Uint8Array(32), box), c.CryptoError, JSON.stringify(box));
  await assert.rejects(c.seal(new Uint8Array(32), c.utf8("x"), ""), c.CryptoError);
  await assert.rejects(c.seal(new Uint8Array(16), c.utf8("x"), "lab"), c.CryptoError);
});

test("AES-GCM: случайный nonce, туда-обратно", async () => {
  const key = c.randomBytes(32);
  const a = await c.seal(key, c.utf8("секрет"), "pack/1");
  const b = await c.seal(key, c.utf8("секрет"), "pack/1");
  assert.notEqual(a.n, b.n);
  assert.equal(text(await c.open(key, a)), "секрет");
});

test("медиа: nonce ‖ ct ‖ tag из Python", async () => {
  const m = V.media;
  const key = D(m.key);
  const blob = D(m.blob);
  assert.deepEqual(await c.openMedia(key, blob, m.aad), D(m.data));
  assert.deepEqual(await c.sealMedia(key, D(m.data), m.aad, { _nonce: blob.subarray(0, 12) }), blob);
  await assert.rejects(c.openMedia(key, blob, m.aad + "x"), c.CryptoError);
  await assert.rejects(c.openMedia(key, blob.subarray(0, 20), m.aad), c.CryptoError);
});

test("хелперы: answerKey", async () => {
  for (const v of V.helpers.answer_key) {
    assert.equal(c.answerSecret(v.path, v.normalized), v.secret);
    assert.equal(c.b64uEncode(await c.answerKey(v.path, v.normalized, D(v.salt), v.iterations)), v.key);
  }
});

test("хелперы: startKey, stageSecret, stageKey", async () => {
  const h = V.helpers;
  assert.equal(c.b64uEncode(await c.startKey(D(h.start_key.salt), h.start_key.iterations)), h.start_key.key);
  for (const v of h.stage_secret) assert.equal(c.stageSecret(v.n, v.pairs), v.secret);
  const sk = h.stage_key;
  assert.equal(c.b64uEncode(await c.stageKey(sk.n, sk.pairs, D(sk.salt), sk.iterations)), sk.key);
});

test("хелперы: packInfo, labInfo, FINALE_INFO и ключи HKDF", async () => {
  const h = V.helpers;
  for (const v of h.pack_info) assert.equal(text(c.packInfo(v.n)), v.info);
  assert.equal(c.b64uEncode(await c.hkdf(D(h.pack_key.stage_key), c.packInfo(h.pack_key.n))), h.pack_key.key);
  assert.equal(text(c.FINALE_INFO), h.finale_info);
  assert.equal(c.b64uEncode(await c.hkdf(D(h.finale_key.stage_key), c.FINALE_INFO)), h.finale_key.key);
  for (const v of h.lab_info) assert.equal(text(c.labInfo(v.object, v.type, v.basis, v.params)), v.info);
  assert.equal(text(c.labInfo("o", "t", "b", [])), "detgame/lab/v1|o|t|b|");
});

test("хелперы: cloudKey из ввода через normalize('password')", async () => {
  const ck = V.helpers.cloud_key;
  assert.equal(normalize("password", ck.input), ck.normalized);
  assert.equal(c.b64uEncode(await c.cloudKey(ck.normalized, D(ck.salt), ck.iterations)), ck.key);
});

test("выравнивание открытого текста записи-проверки совпадает с Python", () => {
  for (const v of V.helpers.answer_plaintext) {
    const pt = c.answerPlaintext(v.canonical);
    assert.equal(text(pt), v.plaintext);
    assert.equal(pt.length, v.length);
    assert.equal(c.answerPlaintextLen(v.canonical), v.length);
    assert.ok(pt.length >= 128 && pt.length % 64 === 0);
  }
});

test("записи с ID разной длины — одной длины; checkAnswer игнорирует p", async () => {
  const key = new Uint8Array(32);
  const lens = new Set();
  for (const id of ["a", "fund", "train", "early", "x".repeat(60)]) {
    const box = await c.sealAnswer(key, "s1.q1", id);
    lens.add(D(box.c).length);
    assert.equal(await c.checkAnswer(key, "s1.q1", [box]), id);
  }
  assert.deepEqual([...lens], [128 + 16]);
  // старый формат без "p" тоже читается; без "c" — не ответ
  assert.equal(await c.checkAnswer(key, "s1.q1", [await c.seal(key, c.utf8('{"c":"fund"}'), "ans/s1.q1")]), "fund");
  assert.equal(await c.checkAnswer(key, "s1.q1", [await c.seal(key, c.utf8('{"p":" "}'), "ans/s1.q1")]), null);
});

test("запись-проверка: верный ответ находится среди паддинга", async () => {
  const u = V.answer_unit;
  const salt = D(u.salt);
  assert.equal(u.entries.length, 8);
  assert.equal(new Set(u.entries.map((e) => D(e.c).length)).size, 1);
  // JS с тем же nonce воспроизводит запись Python побайтно
  const real = [];
  for (const variant of u.variants) {
    const key = await c.answerKey(u.path, variant, salt, u.iterations);
    for (const e of u.entries) {
      const box = await c.sealAnswer(key, u.path, u.canonical, { _nonce: D(e.n) });
      if (box.c === e.c) real.push(e);
    }
  }
  assert.equal(real.length, u.variants.length);
  for (const variant of u.variants) {
    const key = await c.answerKey(u.path, variant, salt, u.iterations);
    assert.equal(await c.checkAnswer(key, u.path, u.entries), u.canonical);
  }
  for (const a of u.accept) {
    const norm = normalize(u.type, a.input);
    assert.equal(norm, a.normalized);
    const key = await c.answerKey(u.path, norm, salt, u.iterations);
    assert.equal(await c.checkAnswer(key, u.path, u.entries), u.canonical, a.input);
  }
  for (const r of u.reject) {
    const norm = normalize(u.type, r.input);
    assert.equal(norm, r.normalized);
    const key = await c.answerKey(u.path, norm, salt, u.iterations);
    assert.equal(await c.checkAnswer(key, u.path, u.entries), null, r.input);
  }
  const key = await c.answerKey(u.path, u.canonical, salt, u.iterations);
  assert.equal(await c.tryEntries(key, u.entries, "ans/s1.q2"), null);
});

test("экспертиза: запись открывается своим запросом и не открывается чужим", async () => {
  const lab = V.lab_entry;
  const k = D(lab.stage_key);
  const keyFor = (r) => c.hkdf(k, c.labInfo(r.object, r.type, r.basis, r.params));
  assert.equal(text(await c.tryEntries(await keyFor(lab.request), lab.entries, "lab")), lab.plaintext);
  assert.equal(await c.tryEntries(await keyFor(lab.request), lab.entries, "pack/1"), null);
  for (const r of lab.wrong_requests) assert.equal(await c.tryEntries(await keyFor(r), lab.entries, "lab"), null);
});

test("tryEntries пропускает мусор", async () => {
  const key = new Uint8Array(32);
  const good = await c.seal(key, c.utf8("ok"), "lab");
  const entries = [{ v: 1 }, "мусор", null, { ...good, aad: "pack/1" }, good];
  assert.equal(text(await c.tryEntries(key, entries, "lab")), "ok");
  assert.equal(await c.tryEntries(key, [], "lab"), null);
});
