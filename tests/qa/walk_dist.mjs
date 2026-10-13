// QA: проход собранного dist/ JS-кодом сайта (core/crypto.js, core/normalize.js) — как браузер.
// Python собирает, JS открывает: пакеты по порядку вопросов ПАКЕТА (FORMATS §2.4), unit.type из пакета,
// экспертизы, закрытые страницы, облако, развязка, подмена AAD.
// Запуск: node tests/qa/walk_dist.mjs <dist> <answers.json>  → stdout JSON {ok, fails[], stats}
import { readFileSync } from "node:fs";
import { join } from "node:path";
import * as c from "../../site/assets/js/core/crypto.js";
import { normalize } from "../../site/assets/js/core/normalize.js";

const [dist, answersPath] = process.argv.slice(2);
const A = JSON.parse(readFileSync(answersPath, "utf8"));
const load = (rel) => JSON.parse(readFileSync(join(dist, rel), "utf8"));
const pub = load("data/public.json");
const D = c.b64uDecode;
const fails = [];
const fail = (m) => fails.push(m);
const json = (u8) => JSON.parse(c.utf8Decode(u8));
const stats = { units: 0, variants: 0, wrong: 0, lab: 0, pages: 0 };

const units = {};
for (const st of A.stages) for (const q of st.questions) for (const u of q.fields ?? [q]) units[u.path] = { ...u, type: u.type ?? q.type };
const norm = (type, x) => normalize(type, x, { defaultYear: pub.defaultYear });

async function openOrNull(key, box, aad) {
  try {
    return await c.open(key, box, aad);
  } catch {
    return null;
  }
}

const K = { 1: await c.startKey(D(pub.saltStart), pub.iter.stage) };
const packs = {};
for (let n = 1; n <= pub.stages; n += 1) {
  const box = load(`data/pack-${n}.json`);
  const pt = await openOrNull(await c.hkdf(K[n], c.packInfo(n)), box, `pack/${n}`);
  if (!pt) {
    fail(`pack-${n}: не открылся ключом K_${n}`);
    break;
  }
  const pack = json(pt);
  packs[n] = pack;
  if (pack.n !== n) fail(`pack-${n}: n=${pack.n}`);
  const pairs = [];
  for (const q of pack.questions) {
    for (const f of q.fields ?? [q]) {
      const unit = f.unit;
      const a = units[unit.path];
      if (!a) {
        fail(`${unit.path}: нет в .answers.json`);
        continue;
      }
      stats.units += 1;
      if (unit.type !== a.type) fail(`${unit.path}: unit.type ${unit.type} ≠ ${a.type}`);
      const salt = D(unit.salt);
      const x = norm(unit.type, a.input);
      const got = x === null ? null : await c.checkAnswer(await c.answerKey(unit.path, x, salt, pub.iter.answer), unit.path, unit.entries);
      if (got !== a.canon) fail(`${unit.path}: ввод ${JSON.stringify(a.input)} → ${got}, ожидался ${a.canon}`);
      for (const v of a.variants) {
        stats.variants += 1;
        const g = await c.checkAnswer(await c.answerKey(unit.path, v, salt, pub.iter.answer), unit.path, unit.entries);
        if (g !== a.canon) fail(`${unit.path}: вариант ${v} → ${g}`);
      }
      for (const w of a.wrong) {
        const wv = norm(unit.type, w);
        if (wv === null) continue;
        stats.wrong += 1;
        const g = await c.checkAnswer(await c.answerKey(unit.path, wv, salt, pub.iter.answer), unit.path, unit.entries);
        if (g !== null) fail(`${unit.path}: неверный ${JSON.stringify(w)} принят`);
      }
      if (q.kind === "mandatory") pairs.push([unit.path, got]);
      // choice/person: вариант ответа не должен выделяться в данных пакета
      if (f.options && f.options.some((o) => Object.keys(o).sort().join() !== "id,text")) fail(`${unit.path}: у вариантов лишние поля`);
      if (f.items) {
        const shown = f.items.map((i) => i.id).join(",");
        if (shown === a.canon) fail(`${unit.path}: карточки order в порядке ответа`);
      }
    }
  }
  if (n < pub.stages) K[n + 1] = await c.stageKey(n, pairs, D(pack.saltStage), pub.iter.stage);
}

// Развязка — только K_4
const fbox = load("data/finale.json");
for (const [m, k] of Object.entries(K)) {
  const ok = (await openOrNull(await c.hkdf(k, c.FINALE_INFO), fbox, "finale")) !== null;
  if (ok !== (Number(m) === pub.stages)) fail(`finale.json открывается K_${m}: ${ok}`);
}

// Подмена AAD: контейнер пакета 2 под именем пакета 1 и наоборот; поле aad переписано
if (packs[2]) {
  const box1 = load("data/pack-1.json");
  const k1 = await c.hkdf(K[1], c.packInfo(1));
  if (await openOrNull(k1, { ...box1, aad: "pack/2" }, "pack/2")) fail("pack-1 с aad=pack/2 открылся (AAD не связан)");
  if (await openOrNull(k1, { ...box1, aad: "pack/2" })) fail("pack-1 с переписанным aad открылся без ожидаемого AAD");
  if (await openOrNull(k1, load("data/pack-2.json"), "pack/1")) fail("pack-2 открылся как pack-1");
}

// Экспертизы
for (const L of A.lab) {
  const pv = Object.values(L.params).map((p) => p.variants);
  const combos = pv.reduce((acc, vs) => acc.flatMap((a) => vs.map((v) => [...a, v])), [[]]);
  for (const t of L.types) {
    for (const b of L.bases) {
      for (const p of combos) {
        stats.lab += 1;
        const pt = await c.tryEntries(await c.hkdf(K[L.stage], c.labInfo(L.object, t, b, p)), packs[L.stage].lab.entries, "lab");
        if (!pt) {
          fail(`lab ${L.result}: (${t}, ${b}, ${p.join("|")}) не открылась`);
          continue;
        }
        const rec = json(pt);
        if (rec.doc !== L.doc) fail(`lab ${L.result}: doc ${rec.doc}`);
      }
    }
  }
  if (L.wrongBasis) {
    for (let m = 1; m <= pub.stages; m += 1) {
      const p0 = pv.map((v) => v[0]);
      const pt = await c.tryEntries(await c.hkdf(K[m], c.labInfo(L.object, L.types[0], L.wrongBasis, p0)), packs[m].lab.entries, "lab");
      if (pt) fail(`lab ${L.result}: открылась с чужим основанием ${L.wrongBasis} на этапе ${m}`);
    }
  }
}

// Страницы
for (const pg of A.pages) {
  if (pg.access === "open") continue;
  stats.pages += 1;
  const payload = load(`p/${pg.slug}/payload.json`);
  if (pg.access === "key") {
    const pt = await openOrNull(D(pg.key), payload, `page/${pg.slug}`);
    if (!pt || json(pt).slug !== pg.slug) fail(`${pg.slug}: не открылась своим ключом`);
    for (const o of A.pages) {
      if (o.key && o.slug !== pg.slug && (await openOrNull(D(o.key), payload, `page/${pg.slug}`))) fail(`${pg.slug}: открылась ключом ${o.slug}`);
    }
  } else {
    const pw = normalize("password", pg.password);
    const key = await c.cloudKey(pw, D(payload.salt), payload.iter);
    const pt = await openOrNull(key, payload.box, "page/cloud");
    if (!pt) fail("cloud: не открылось паролем");
    const bad = await c.cloudKey(pw + "1", D(payload.salt), payload.iter);
    if (await openOrNull(bad, payload.box, "page/cloud")) fail("cloud: открылось неверным паролем");
  }
}

process.stdout.write(JSON.stringify({ ok: fails.length === 0, fails, stats, keys: Object.fromEntries(Object.entries(K).map(([n, k]) => [n, c.b64uEncode(k)])) }));
