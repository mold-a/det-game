// core/game.js на синтетических пакетах (docs/02 §3.3–3.5, docs/FORMATS.md §2, §4, §7.1).
import { test, describe, before } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";

import {
  loadPublic,
  startKey,
  openPack,
  openPacks,
  openFinale,
  checkUnit,
  checkQuestion,
  wrongHash,
  stagePairs,
  nextStageKey,
  isStageComplete,
  finalQuestions,
  earlierBonusPaths,
  receivedDocuments,
  rankFor,
  normalizeQuestion,
  checkQuestionNormalized,
  GameDataError,
} from "../../site/assets/js/core/game.js";
import { b64uEncode, b64uDecode, stageKey } from "../../site/assets/js/core/crypto.js";
import * as S from "../../site/assets/js/core/state.js";
import { makePub, makeQuestion, makeForm, makePack, sealPack, sealFinale, fakeFetch } from "./fixtures.mjs";

const sha256hex = (s) => createHash("sha256").update(Buffer.from(s, "utf8")).digest("hex");

// Дата финального вопроса в синтетическом пакете (тест не зависит от content/; одна пара констант на файл).
const FINAL_DATE_ISO = "2026-11-01";
const FINAL_DATE_SHORT = "01.11";

// Этап 1: форма (время с допуском ±2, лицо, текст с синонимами) + order + бонус.
// Этап 2: один вопрос persons. Этап 3 (последний): финал и бонус.
let pub, K1, K2, K3, pack1, pack2, pack3, boxes;

before(async () => {
  pub = makePub();
  K1 = await startKey(pub);
  const times = ["21:16", "21:17", "21:18", "21:19", "21:20"];
  const q1 = await makeForm(1, "q1", [
    { id: "time", type: "time", variants: times, canon: "21:18" },
    { id: "who", type: "person", variants: ["zavyalov"], canon: "zavyalov", extra: { pool: ["zavyalov", "volkov"] } },
    { id: "disease", type: "text", variants: ["астма", "бронхиальная астма", "астму"], canon: "астма" },
  ]);
  const q2 = await makeQuestion(1, "q2", {
    type: "order",
    variants: ["k3,p8,d1"],
    canon: "k3,p8,d1",
    extra: { items: [{ id: "d1", text: "в" }, { id: "k3", text: "а" }, { id: "p8", text: "б" }] },
  });
  const b1 = await makeQuestion(1, "b1", { kind: "bonus", type: "text", variants: ["северогорск"], canon: "северогорск" });
  pack1 = makePack(1, [q1, b1, q2], {
    documents: [{ id: "1-01", stage: 1, kind: "paper", title: "Вводное письмо", link: null }],
  });
  // K2 выводится так, как это сделает клиент: пары в порядке пакета, только обязательные.
  K2 = await stageKey(
    1,
    [
      ["s1.q1.time", "21:18"],
      ["s1.q1.who", "zavyalov"],
      ["s1.q1.disease", "астма"],
      ["s1.q2", "k3,p8,d1"],
    ],
    b64uDecode(pack1.saltStage),
    pub.iter.stage,
  );
  const q21 = await makeQuestion(2, "q1", { type: "persons", variants: ["gromov,stas"], canon: "gromov,stas", extra: { pool: ["stas", "gromov", "oleg"] } });
  pack2 = makePack(2, [q21], { documents: [{ id: "2-03", stage: 2, kind: "online", title: "Страница", link: "/p/gromov/" }] });
  K3 = await stageKey(2, [["s2.q1", "gromov,stas"]], b64uDecode(pack2.saltStage), pub.iter.stage);
  const f1 = await makeQuestion(3, "f1", { kind: "final", type: "choice", variants: ["a"], canon: "a", extra: { options: [{ id: "a", text: "А" }, { id: "b", text: "Б" }] } });
  const fb = await makeQuestion(3, "fb", { kind: "bonus", type: "number", variants: ["2"], canon: "2" });
  const f2 = await makeQuestion(3, "f2", { kind: "final", type: "date", variants: [FINAL_DATE_ISO], canon: FINAL_DATE_ISO });
  pack3 = makePack(3, [fb, f1, f2], { last: true });
  boxes = {
    1: await sealPack(K1, 1, pack1),
    2: await sealPack(K2, 2, pack2),
    3: await sealPack(K3, 3, pack3),
  };
});

describe("public.json, стартовый ключ, пакеты", () => {
  test("loadPublic читает /data/public.json и проверяет формат", async () => {
    const got = await loadPublic({ fetchFn: fakeFetch({ "/data/public.json": pub }) });
    assert.equal(got.gameId, pub.gameId);
    await assert.rejects(loadPublic({ fetchFn: fakeFetch({ "/data/public.json": { v: 2 } }) }), GameDataError);
    await assert.rejects(loadPublic({ fetchFn: fakeFetch({}) }), (e) => e.code === "network");
  });

  test("K1 детерминирован и открывает pack-1 (через fetch и готовым контейнером)", async () => {
    const again = await startKey(pub);
    assert.deepEqual(again, K1);
    const viaFetch = await openPack(1, K1, { fetchFn: fakeFetch({ "/data/pack-1.json": boxes[1] }) });
    assert.equal(viaFetch.n, 1);
    const viaB64 = await openPack(1, b64uEncode(K1), { box: boxes[1] });
    assert.equal(viaB64.questions.length, 3);
  });

  test("чужой ключ → «Пакет не расшифровался» (decrypt); подмена номера → format", async () => {
    await assert.rejects(openPack(2, K1, { box: boxes[2] }), (e) => e instanceof GameDataError && e.code === "decrypt");
    await assert.rejects(openPack(2, K1, { box: boxes[1] }), (e) => e.code === "decrypt", "AAD pack/1 ≠ pack/2");
  });

  test("openPacks открывает 1..stage ключами прогресса", async () => {
    const s = { stage: 2, keys: { 1: b64uEncode(K1), 2: b64uEncode(K2) } };
    const packs = await openPacks(s, { boxes });
    assert.deepEqual(Object.keys(packs), ["1", "2"]);
    await assert.rejects(openPacks({ stage: 2, keys: { 1: b64uEncode(K1) } }, { boxes }), (e) => e.code === "decrypt");
  });
});

describe("проверка ответов", () => {
  test("верный ответ → канон; синоним → тот же канон; неверный → correct=false", async () => {
    const unit = pack1.questions[0].fields[2].unit;
    assert.deepEqual(await checkUnit(unit, "Астма!", pub), { valid: true, correct: true, canon: "астма", normalized: "астма" });
    const syn = await checkUnit(unit, "  Бронхиальная   АСТМА ", pub);
    assert.equal(syn.canon, "астма");
    assert.equal(syn.normalized, "бронхиальная астма");
    const wrong = await checkUnit(unit, "диабет", pub);
    assert.equal(wrong.valid, true);
    assert.equal(wrong.correct, false);
    assert.equal(wrong.canon, null);
  });

  test("пустой и неформатный ввод — не попытка (valid=false)", async () => {
    const time = pack1.questions[0].fields[0].unit;
    for (const bad of ["", "   ", "25:70", "8", null]) {
      const r = await checkUnit(time, bad, pub);
      assert.equal(r.valid, false, String(bad));
    }
  });

  test("допуск времени: варианты в пределах допуска дают канон, вне — неверно", async () => {
    const time = pack1.questions[0].fields[0].unit;
    for (const ok of ["21:16", "21.17", "2118", "21 ч 20"]) {
      const r = await checkUnit(time, ok, pub);
      assert.equal(r.correct, true, ok);
      assert.equal(r.canon, "21:18");
    }
    for (const no of ["21:15", "21:21", "09:18"]) assert.equal((await checkUnit(time, no, pub)).correct, false, no);
  });

  test("форма: засчитывается только если верны все поля; какое неверно — не сообщается", async () => {
    const q = pack1.questions[0];
    const ok = await checkQuestion(q, { time: "21:19", who: "zavyalov", disease: "астму" }, pub);
    assert.equal(ok.correct, true);
    assert.deepEqual(ok.canon, { time: "21:18", who: "zavyalov", disease: "астма" });
    const bad = await checkQuestion(q, { time: "21:19", who: "volkov", disease: "астма" }, pub);
    assert.equal(bad.valid, true);
    assert.equal(bad.correct, false);
    assert.equal(bad.canon, null);
    assert.deepEqual(Object.keys(bad).sort(), ["canon", "correct", "invalid", "normalized", "valid"]);
    assert.deepEqual(bad.normalized, { time: "21:19", who: "volkov", disease: "астма" });
  });

  test("форма с незаполненным или неформатным полем — не попытка, invalid перечисляет поля", async () => {
    const q = pack1.questions[0];
    const r = await checkQuestion(q, { time: "99:99", who: "", disease: "астма" }, pub);
    assert.equal(r.valid, false);
    assert.deepEqual(r.invalid, ["time", "who"]);
  });

  test("order и persons: массивы ID, порядок у persons не важен", async () => {
    const order = pack1.questions[2];
    assert.equal((await checkQuestion(order, ["k3", "p8", "d1"], pub)).correct, true);
    assert.equal((await checkQuestion(order, ["p8", "k3", "d1"], pub)).correct, false);
    const persons = pack2.questions[0];
    assert.equal((await checkQuestion(persons, ["stas", "gromov"], pub)).canon, "gromov,stas");
    assert.equal((await checkQuestion(persons, [], pub)).valid, false);
  });

  test("wrongHash по F17: простой вопрос и форма", async () => {
    const order = pack1.questions[2];
    assert.equal(await wrongHash(order, "p8,k3,d1"), sha256hex("detgame/wrong/v1|s1.q2|p8,k3,d1"));
    const form = pack1.questions[0];
    const h = await wrongHash(form, { disease: "астма", time: "21:19", who: "volkov" });
    assert.equal(h, sha256hex("detgame/wrong/v1|s1.q1|time=21:19\x1fwho=volkov\x1fdisease=астма"), "порядок полей — как в пакете");
    assert.notEqual(await wrongHash({ ...order, path: "s9.q9" }, "p8,k3,d1"), await wrongHash(order, "p8,k3,d1"));
  });
});

describe("этапы", () => {
  test("пары stageSecret — только обязательные в порядке пакета; без решения — ошибка", () => {
    const units = {
      "s1.q1": { status: "solved", canon: { time: "21:18", who: "zavyalov", disease: "астма" } },
      "s1.q2": { status: "solved", canon: "k3,p8,d1" },
      "s1.b1": { status: "closed", canon: null },
    };
    assert.deepEqual(stagePairs(pack1, units), [
      ["s1.q1.time", "21:18"],
      ["s1.q1.who", "zavyalov"],
      ["s1.q1.disease", "астма"],
      ["s1.q2", "k3,p8,d1"],
    ]);
    assert.equal(isStageComplete(pack1, units), true);
    assert.equal(isStageComplete(pack1, { "s1.q1": units["s1.q1"] }), false);
    assert.throws(() => stagePairs(pack1, { "s1.q1": units["s1.q1"] }));
  });

  test("прохождение этапа 1 → ключ этапа 2 открывает pack-2 (вместе со state.js)", async () => {
    let s = S.newState({ gameId: pub.gameId, saltsId: pub.saltsId, startedAt: "t", keys: { 1: b64uEncode(K1) } });
    const p1 = await openPack(1, s.keys[1], { box: boxes[1] });
    const [form, , order] = p1.questions;

    // неверная форма → штраф и хеш; повтор того же — без штрафа
    const bad = await checkQuestion(form, { time: "21:19", who: "volkov", disease: "астма" }, pub);
    const h = await wrongHash(form, bad.normalized);
    s = S.recordWrong(s, form.path, h, pub.penalties.wrongAttempt);
    s = S.recordWrong(s, form.path, await wrongHash(form, bad.normalized), pub.penalties.wrongAttempt);
    assert.equal(S.score(s), -5);

    const good = await checkQuestion(form, { time: "2117", who: "Zavyalov", disease: "Бронхиальная астма" }, pub);
    s = S.solve(s, form.path, good.canon);
    assert.equal(isStageComplete(p1, s.units), false);
    const goodOrder = await checkQuestion(order, ["k3", "p8", "d1"], pub);
    s = S.solve(s, order.path, goodOrder.canon);
    assert.equal(isStageComplete(p1, s.units), true, "бонус не нужен для перехода");

    const k2 = await nextStageKey(p1, s.units, pub);
    assert.equal(k2, b64uEncode(K2));
    s = S.advanceStage(s, 2, k2);
    const p2 = await openPack(2, s.keys[2], { box: boxes[2] });
    assert.equal(p2.n, 2);
  });

  test("на последнем этапе ключа следующего нет", async () => {
    assert.equal(await nextStageKey(pack3, {}, pub), null);
  });

  test("финал: сначала final по порядку пакета, затем bonus; бонусы прошлых этапов", () => {
    assert.deepEqual(finalQuestions(pack3).map((q) => q.path), ["s3.f1", "s3.f2", "s3.fb"]);
    assert.deepEqual(earlierBonusPaths({ 1: pack1, 2: pack2, 3: pack3 }, 3), ["s1.b1"]);
  });

  test("финал: ответ нормализуется при отправке, проверяется после последнего (без PBKDF2 на отправке)", async () => {
    const [f1, f2, fb] = finalQuestions(pack3);
    const a1 = normalizeQuestion(f1, "A", pub);
    assert.deepEqual(a1, { valid: true, normalized: "a", invalid: [] });
    assert.equal(normalizeQuestion(f2, "31.02", pub).valid, false, "неформатная дата — не попытка");
    const a2 = normalizeQuestion(f2, FINAL_DATE_SHORT, pub);
    const a3 = normalizeQuestion(fb, "касса 3", pub);
    assert.equal(await checkQuestionNormalized(f1, a1.normalized, pub), true);
    assert.equal(await checkQuestionNormalized(f2, a2.normalized, pub), true);
    assert.equal(await checkQuestionNormalized(fb, a3.normalized, pub), false);
    const form = pack1.questions[0];
    const nf = normalizeQuestion(form, { time: "21:20", who: "zavyalov", disease: "астма" }, pub);
    assert.equal(await checkQuestionNormalized(form, nf.normalized, pub), true);
    assert.deepEqual(normalizeQuestion(form, { time: "", who: "x", disease: "" }, pub).invalid, ["time", "disease"]);
  });

  test("развязка открывается ключом последнего этапа и только им", async () => {
    const box = await sealFinale(K3, { confession: {}, letter: {}, fates: [], answers: { "s1.q2": "а → б → в" } });
    const f = await openFinale(b64uEncode(K3), { fetchFn: fakeFetch({ "/data/finale.json": box }) });
    assert.equal(f.answers["s1.q2"], "а → б → в");
    await assert.rejects(openFinale(K2, { box }), (e) => e.code === "decrypt");
  });
});

describe("документы и ранги", () => {
  test("полученные документы: открытые этапы + результаты экспертиз, без повторов", () => {
    const docs = receivedDocuments({ 2: pack2, 1: pack1 }, { docs: ["2-01", "1-01"] }, { "2-01": "Заключение" });
    assert.deepEqual(
      docs.map((d) => [d.id, d.kind, d.title]),
      [
        ["1-01", "paper", "Вводное письмо"],
        ["2-03", "online", "Страница"],
        ["2-01", "lab", "Заключение"],
      ],
    );
  });

  test("ранг по порогам из public.json, границы включительно", () => {
    assert.equal(rankFor(-40, pub.ranks), "Стажёр");
    assert.equal(rankFor(99, pub.ranks), "Стажёр");
    assert.equal(rankFor(100, pub.ranks), "Следователь");
    assert.equal(rankFor(180, pub.ranks), "Следователь");
    assert.equal(rankFor(181, pub.ranks), "Шерлок");
  });
});
