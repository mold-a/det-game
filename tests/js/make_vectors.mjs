// Обратное направление кросс-теста: JS выводит ключи и шифрует (случайные nonce,
// как в браузере), печатает JSON в stdout; tests/test_crypto_js_compat.py проверяет в Python.
// Запуск: node tests/js/make_vectors.mjs
import * as c from "../../site/assets/js/core/crypto.js";
import { normalize } from "../../site/assets/js/core/normalize.js";

const E = c.b64uEncode;
const ITERS = 1000;

async function main() {
  const out = { b64u: [], pbkdf2: [], hkdf: [], aesgcm: [], helpers: {} };

  for (const n of [0, 1, 2, 3, 31, 32, 33, 1000]) {
    const raw = c.randomBytes(n);
    out.b64u.push({ hex: Buffer.from(raw).toString("hex"), b64u: E(raw) });
  }

  for (const [password, iterations] of [
    ["detgame/answer/v1|s1.q1|ёж", ITERS],
    ["detgame/cloud/v1|парольёлка2026", ITERS],
    ["latin password", 1],
  ]) {
    const salt = c.randomBytes(16);
    out.pbkdf2.push({ password, salt: E(salt), iterations, key: E(await c.pbkdf2(c.utf8(password), salt, iterations)) });
  }

  for (const info of ["detgame/pack/v1|3", "detgame/lab/v1|obj|type|doc|", "detgame/finale/v1"]) {
    const ikm = c.randomBytes(32);
    out.hkdf.push({ ikm: E(ikm), info, okm: E(await c.hkdf(ikm, c.utf8(info))) });
  }

  for (const [aad, plaintext] of [
    ["pack/1", '{"intro":"Письмо — «тест»","n":1}'],
    ["lab", '{"doc":"x-01","html":"<p>ок ✓</p>"}'],
    ["page/inna", ""],
  ]) {
    const key = c.randomBytes(32);
    out.aesgcm.push({ key: E(key), aad, plaintext, container: await c.seal(key, c.utf8(plaintext), aad) });
  }

  {
    const key = c.randomBytes(32);
    const data = c.randomBytes(500);
    const aad = "media/0123456789abcdef";
    out.media = { key: E(key), aad, data: E(data), blob: E(await c.sealMedia(key, data, aad)) };
  }

  // Единица: варианты нормализуются в JS, записи шифруются в JS; Python находит канон.
  {
    const path = "s2.q3.who";
    const salt = c.randomBytes(16);
    const variants = [["Gromov", "Oleg"], ["oleg", "GROMOV", "gromov"]].map((v) => normalize("persons", v));
    const canonical = variants[0];
    const entries = [];
    for (const v of new Set(variants)) {
      entries.push(await c.sealAnswer(await c.answerKey(path, v, salt, ITERS), path, canonical));
    }
    out.answer_unit = { path, salt: E(salt), iterations: ITERS, canonical, variants, entries };
  }

  {
    const pairs = [["s1.q1.time", "08:15"], ["s1.q2", "ёж"]];
    const salt = c.randomBytes(16);
    const stageKey = await c.stageKey(1, pairs, salt, ITERS);
    const startSalt = c.randomBytes(16);
    const cloudSalt = c.randomBytes(16);
    const request = { object: "obj-1", type: "type_a", basis: "doc-1", params: ["08:15", "2026-03-05"] };
    const labKey = await c.hkdf(stageKey, c.labInfo(request.object, request.type, request.basis, request.params));
    out.helpers = {
      stage: { n: 1, pairs, salt: E(salt), iterations: ITERS, secret: c.stageSecret(1, pairs), key: E(stageKey) },
      start: { salt: E(startSalt), iterations: ITERS, key: E(await c.startKey(startSalt, ITERS)) },
      cloud: {
        normalized: normalize("password", " Пароль-Ёлка "),
        salt: E(cloudSalt),
        iterations: ITERS,
        key: E(await c.cloudKey(normalize("password", " Пароль-Ёлка "), cloudSalt, ITERS)),
      },
      pack: { n: 2, info: new TextDecoder().decode(c.packInfo(2)), key: E(await c.hkdf(stageKey, c.packInfo(2))) },
      finale: { key: E(await c.hkdf(stageKey, c.FINALE_INFO)) },
      lab: {
        request,
        info: new TextDecoder().decode(c.labInfo(request.object, request.type, request.basis, request.params)),
        container: await c.seal(labKey, c.utf8('{"doc":"x-02"}'), "lab"),
      },
    };
  }

  process.stdout.write(JSON.stringify(out));
}

await main();
