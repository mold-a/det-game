// Синтетические public.json, пакеты, записи экспертиз и развязка — по docs/FORMATS.md,
// зашифрованные core/crypto.js прямо в тесте (без dist/). Не тест: не совпадает с *.test.mjs.

import {
  randomBytes,
  b64uEncode,
  utf8,
  hkdf,
  seal,
  packInfo,
  labInfo,
  answerKey,
  sealAnswer,
  answerAad,
  FINALE_INFO,
} from "../../site/assets/js/core/crypto.js";

// Мало итераций — тесты быстрые; сами числа приходят параметром, как из public.json.
export const ITER = { answer: 1000, stage: 2000 };
export const PAD = 8;

export function makePub(over = {}) {
  return {
    v: 1,
    gameId: "testgame",
    title: "Тестовое дело",
    stages: 3,
    saltStart: b64uEncode(randomBytes(16)),
    iter: { ...ITER },
    entriesPad: PAD,
    points: { bonus: 15, final: 30 },
    penalties: { wrongAttempt: -5, labNoBasis: -5 },
    hints: { cost: [10, 20, 40], autoAfterWrong: 3 },
    ranks: [
      { min: null, max: 99, name: "Стажёр" },
      { min: 100, max: 180, name: "Следователь" },
      { min: 181, max: null, name: "Шерлок" },
    ],
    defaultYear: 2026,
    saltsId: "salts-test",
    buildId: "20261013T000000Z-00000000",
    ...over,
  };
}

/** Записи-паддинг: тот же AAD, та же длина открытого текста, случайный ключ. */
async function padding(aad, sampleLen, count) {
  const out = [];
  for (let i = 0; i < count; i++) out.push(await seal(randomBytes(32), randomBytes(sampleLen), aad));
  return out;
}

function shuffle(list) {
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/**
 * Единица: variants — нормализованные допустимые значения, canon — канон.
 * Как в сборщике: запись на каждый вариант + паддинг до PAD, перемешано.
 */
export async function makeUnit(path, type, variants, canon) {
  const salt = randomBytes(16);
  const entries = [];
  for (const v of variants) {
    const k = await answerKey(path, v, salt, ITER.answer);
    entries.push(await sealAnswer(k, path, canon));
  }
  const len = utf8(JSON.stringify({ c: canon })).length;
  entries.push(...(await padding(answerAad(path), len, Math.max(0, PAD - entries.length))));
  return { path, type, salt: b64uEncode(salt), entries: shuffle(entries) };
}

export async function makeQuestion(n, id, { kind = "mandatory", type, variants, canon, extra = {} }) {
  const path = `s${n}.${id}`;
  return {
    id,
    path,
    kind,
    type,
    prompt: `Вопрос ${path}`,
    help: null,
    hints: kind === "mandatory" ? ["подсказка 1", "подсказка 2", "подсказка 3"] : [],
    ...extra,
    unit: await makeUnit(path, type, variants, canon),
  };
}

/** fields: [{ id, type, variants, canon, extra }] */
export async function makeForm(n, id, fields, { kind = "mandatory" } = {}) {
  const path = `s${n}.${id}`;
  const out = [];
  for (const f of fields) {
    const fpath = `${path}.${f.id}`;
    out.push({
      id: f.id,
      path: fpath,
      type: f.type,
      label: `Поле ${f.id}`,
      help: null,
      ...(f.extra ?? {}),
      unit: await makeUnit(fpath, f.type, f.variants, f.canon),
    });
  }
  return {
    id,
    path,
    kind,
    type: "form",
    prompt: `Форма ${path}`,
    help: null,
    hints: kind === "mandatory" ? ["1", "2", "3"] : [],
    fields: out,
  };
}

export function makePack(n, questions, { saltStage = b64uEncode(randomBytes(16)), last = false, documents = [], lab = {} } = {}) {
  return {
    v: 1,
    n,
    envelope: n,
    introHtml: `<p>Письмо этапа ${n}</p>`,
    onComplete: last ? null : `Ответ принят. Вскройте конверт № ${n + 1}.`,
    saltStage: last ? null : saltStage,
    questions,
    characters: {},
    documents,
    lab: { types: lab.types ?? [], objects: lab.objects ?? [], entries: lab.entries ?? [] },
  };
}

export async function sealPack(key, n, pack) {
  return seal(await hkdf(key, packInfo(n)), utf8(JSON.stringify(pack)), `pack/${n}`);
}

/**
 * Записи экспертиз этапа: requests — [{ object, type, basis, params: [нормализованные], entry }].
 * key — K_n этапа. Паддинг до PAD.
 */
export async function makeLabEntries(key, requests) {
  const out = [];
  let len = 64;
  for (const r of requests) {
    const pt = utf8(JSON.stringify({ v: 1, ...r.entry }));
    len = pt.length;
    out.push(await seal(await hkdf(key, labInfo(r.object, r.type, r.basis, r.params)), pt, "lab"));
  }
  out.push(...(await padding("lab", len, Math.max(0, PAD - out.length))));
  return shuffle(out);
}

export async function sealFinale(keyLast, finale) {
  return seal(await hkdf(keyLast, FINALE_INFO), utf8(JSON.stringify({ v: 1, ...finale })), "finale");
}

/** fetch-заглушка: { "/data/x.json": объект } */
export function fakeFetch(files) {
  return async (path) => {
    if (!(path in files)) return { ok: false, status: 404, json: async () => null };
    return { ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(files[path])) };
  };
}
