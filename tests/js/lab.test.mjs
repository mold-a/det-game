// core/lab.js на синтетических пакетах (docs/01 §7, docs/02 §3.6, docs/FORMATS.md §2.3, §3).
import { test, describe, before } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";

import {
  labCatalog,
  normalizeParams,
  paramString,
  labFingerprint,
  labRequest,
  restoreLabResults,
  labDocTitles,
  prepareLabRequest,
  labOrders,
} from "../../site/assets/js/core/lab.js";
import { resolveObject } from "../../site/assets/js/core/labmatch.js";
import { randomBytes, b64uEncode } from "../../site/assets/js/core/crypto.js";
import * as S from "../../site/assets/js/core/state.js";
import { makePub, makePack, makeLabEntries } from "./fixtures.mjs";

const pub = makePub();
const K = { 1: randomBytes(32), 2: randomBytes(32), 3: randomBytes(32) };
const keysB64 = Object.fromEntries(Object.entries(K).map(([n, k]) => [n, b64uEncode(k)]));

const OBJ = {
  inhaler: { id: "inhaler", title: "Ингалятор", ord: 2, params: [] },
  water: { id: "water", title: "Бутылка воды", ord: 1, params: [] },
  cam: {
    id: "station_cam",
    title: "Камеры вокзала",
    ord: 5,
    params: [
      { id: "date", type: "date", label: "Дата" },
      { id: "time", type: "time", label: "Время" },
      { id: "window", type: "number", label: "Касса" },
    ],
  },
};
const TYPES = [
  { id: "video", title: "Просмотр видеозаписей", ord: 1 },
  { id: "chem", title: "Химическое исследование", ord: 0 },
];

let packs;

before(async () => {
  // Этап 1: вода (атмосферный результат). Ингалятор появляется на этапе 2 и даёт 2-01
  // по основанию 1-03 или 1-08 (несколько оснований). Этап 3: камеры с допуском по времени
  // и та же экспертиза воды с другим (поздним) результатом.
  const camTimes = ["14:33", "14:34", "14:35", "14:36", "14:37"];
  const lab1 = await makeLabEntries(K[1], [
    { object: "water", type: "chem", basis: "1-01", params: [], entry: { doc: null, title: "Бутылка воды: химическое исследование", form: null, html: "<p>Ничего</p>", media: [] } },
  ]);
  const doc201 = { doc: "2-01", title: "Заключение эксперта-химика", form: "expert", html: "<article>…</article>", media: [] };
  const lab2 = await makeLabEntries(K[2], [
    { object: "inhaler", type: "chem", basis: "1-03", params: [], entry: doc201 },
    { object: "inhaler", type: "chem", basis: "1-08", params: [], entry: doc201 },
  ]);
  const doc408 = { doc: "4-08", title: "Записи камер вокзала", form: "video", html: "<article>…</article>", media: [] };
  const lab3 = await makeLabEntries(K[3], [
    ...camTimes.map((t) => ({ object: "station_cam", type: "video", basis: "3-07", params: ["2026-10-30", t, "2"], entry: doc408 })),
    { object: "water", type: "chem", basis: "1-01", params: [], entry: { doc: "3-05", title: "Повторное исследование", form: "expert", html: "<p/>", media: [] } },
  ]);
  packs = {
    1: makePack(1, [], { lab: { types: TYPES, objects: [OBJ.water], entries: lab1 } }),
    2: makePack(2, [], { lab: { types: [], objects: [OBJ.inhaler], entries: lab2 } }),
    3: makePack(3, [], { lab: { types: [], objects: [OBJ.cam], entries: lab3 }, last: true }),
  };
});

const ctx = (stage) => ({ stage, keys: keysB64, packs });

describe("каталог и параметры", () => {
  test("каталог: виды из pack-1, объекты открытых этапов, сортировка по ord", () => {
    const c1 = labCatalog({ 1: packs[1] });
    assert.deepEqual(c1.types.map((t) => t.id), ["chem", "video"]);
    assert.deepEqual(c1.objects.map((o) => o.id), ["water"]);
    const c3 = labCatalog(packs);
    assert.deepEqual(c3.objects.map((o) => o.id), ["water", "inhaler", "station_cam"]);
  });

  test("параметры нормализуются по типам; неформатный — подсказка, запрос не отправляется", () => {
    const ok = normalizeParams(OBJ.cam, ["30.10", "14.35", "касса №2"], { defaultYear: pub.defaultYear });
    assert.deepEqual(ok, { params: ["2026-10-30", "14:35", "2"], invalid: [] });
    const bad = normalizeParams(OBJ.cam, ["31.02", "", "2"], { defaultYear: pub.defaultYear });
    assert.deepEqual(bad, { params: null, invalid: ["date", "time"] });
    assert.deepEqual(normalizeParams(OBJ.water, [], {}), { params: [], invalid: [] });
    assert.equal(paramString([]), "");
    assert.equal(paramString(["a", "b"]), "a|b");
  });

  test("fp = b64u(sha256(object|type|basis|p)) — F7", async () => {
    const fp = await labFingerprint({ object: "station_cam", type: "video", basis: "3-07", params: ["2026-10-30", "14:35", "2"] });
    const want = createHash("sha256").update("station_cam|video|3-07|2026-10-30|14:35|2").digest("base64url");
    assert.equal(fp, want);
    const empty = await labFingerprint({ object: "water", type: "chem", basis: "1-01", params: [] });
    assert.equal(empty, createHash("sha256").update("water|chem|1-01|").digest("base64url"));
  });
});

describe("запросы", () => {
  test("верный запрос → документ; любое из допустимых оснований подходит", async () => {
    for (const basis of ["1-03", "1-08"]) {
      const r = await labRequest({ object: "inhaler", type: "chem", basis, params: [] }, ctx(2));
      assert.equal(r.stage, 2);
      assert.equal(r.entry.doc, "2-01");
    }
  });

  test("без основания (не то основание / не тот вид) → null, штраф один раз, повтор без штрафа", async () => {
    let s = S.newState({ gameId: "g", saltsId: "x", startedAt: "t" });
    for (let i = 0; i < 2; i++) {
      const req = { object: "inhaler", type: "chem", basis: "1-01", params: [] };
      assert.equal(await labRequest(req, ctx(2)), null);
      s = S.labRejected(s, await labFingerprint(req), pub.penalties.labNoBasis, { ...req, stage: 2 });
    }
    assert.equal(S.score(s), -5);
    assert.equal(await labRequest({ object: "inhaler", type: "video", basis: "1-03", params: [] }, ctx(2)), null);
  });

  test("параметры с допуском: любое время из окна → тот же документ, вне окна — null", async () => {
    for (const t of ["14.33", "14:37", "1435"]) {
      const { params } = normalizeParams(OBJ.cam, ["30.10.2026", t, "2"], { defaultYear: pub.defaultYear });
      const r = await labRequest({ object: "station_cam", type: "video", basis: "3-07", params }, ctx(3));
      assert.equal(r?.entry.doc, "4-08", t);
    }
    const { params } = normalizeParams(OBJ.cam, ["30.10", "14:40", "2"], { defaultYear: pub.defaultYear });
    assert.equal(await labRequest({ object: "station_cam", type: "video", basis: "3-07", params }, ctx(3)), null);
  });

  test("запрос, отклонённый раньше, срабатывает после перехода этапа (без нового штрафа)", async () => {
    const req = { object: "inhaler", type: "chem", basis: "1-03", params: [] };
    const fp = await labFingerprint(req);
    let s = S.newState({ gameId: "g", saltsId: "x", startedAt: "t" });

    assert.equal(await labRequest(req, ctx(1)), null, "этап 2 ещё не открыт");
    s = S.labRejected(s, fp, -5, { ...req, stage: 1 });

    const r = await labRequest(req, ctx(2));
    assert.equal(r.entry.doc, "2-01");
    s = S.labDone(s, fp, r.entry.doc, { ...req, stage: 2 });
    assert.deepEqual(s.lab.rejected, []);
    assert.equal(s.lab.done[fp], "2-01");
    assert.deepEqual(s.docs, ["2-01"]);
    assert.equal(S.score(s), -5, "только прежний штраф");
  });

  test("результат есть на нескольких этапах — берётся самый поздний", async () => {
    const req = { object: "water", type: "chem", basis: "1-01", params: [] };
    const early = await labRequest(req, ctx(2));
    assert.equal(early.stage, 1);
    assert.equal(early.entry.doc, null, "атмосферный результат");
    const late = await labRequest(req, ctx(3));
    assert.equal(late.stage, 3);
    assert.equal(late.entry.doc, "3-05");
  });

  test("архив lab.log: результаты выводятся заново, документы получают названия", async () => {
    const log = [
      { t: "1", fp: "a", object: "inhaler", type: "chem", basis: "1-03", params: [], stage: 2, ok: true, doc: "2-01" },
      { t: "2", fp: "b", object: "inhaler", type: "chem", basis: "1-01", params: [], stage: 2, ok: false, doc: null },
    ];
    const restored = await restoreLabResults(log, ctx(3));
    assert.deepEqual(Object.keys(restored), ["a"]);
    assert.deepEqual(labDocTitles(restored), { "2-01": "Заключение эксперта-химика" });
  });
});

describe("заявка: текст объекта → запрос (prepareLabRequest)", () => {
  const objects = [
    { id: "water", title: "Бутылка воды из гримёрки № 4", aliases: ["бутыл", "вод"], params: [] },
    { id: "keys", title: "Связка ключей", aliases: ["ключ"], params: [] },
    { id: "coat", title: "Пальто погибшего", aliases: ["пальт"], params: [] },
    { id: "cup", title: "Чашка с водой", aliases: ["чашк", "вод"], params: [] },
    OBJ.cam && { ...OBJ.cam, aliases: ["камер вокзал"] },
  ];
  const base = { type: "chem", basis: "1-09", objects, resolve: resolveObject, defaultYear: pub.defaultYear };

  test("пустое поле и предмет не из описи — без запроса", () => {
    assert.deepEqual(prepareLabRequest({ ...base, text: "  " }), { status: "empty" });
    assert.deepEqual(prepareLabRequest({ ...base, text: "кофейная гуща" }), { status: "none" });
  });

  test("неоднозначно — кандидаты в порядке каталога", () => {
    const r = prepareLabRequest({ ...base, text: "вода" });
    assert.equal(r.status, "ambiguous");
    assert.deepEqual(r.objects.map((o) => o.id), ["water", "cup"]);
  });

  test("распознан по названию и по алиасу; ранний токен важнее («ключи из кармана пальто»)", () => {
    assert.equal(prepareLabRequest({ ...base, text: "Бутылка воды из гримёрки № 4" }).req.object, "water");
    assert.equal(prepareLabRequest({ ...base, text: "ключи из кармана пальто" }).req.object, "keys");
  });

  test("не выбраны вид или основание — подсказка, объект уже известен", () => {
    const r = prepareLabRequest({ ...base, text: "ключи", type: "", basis: "" });
    assert.equal(r.status, "incomplete");
    assert.equal(r.object.id, "keys");
    assert.deepEqual(r.missing, ["type", "basis"]);
    assert.deepEqual(prepareLabRequest({ ...base, text: "ключи", basis: "" }).missing, ["basis"]);
  });

  test("параметры объекта: формат проверяется, нормализуются в порядке объекта", () => {
    const text = "камеры вокзала";
    const bad = prepareLabRequest({ ...base, text, params: ["31.02", "14:35", "2"] });
    assert.equal(bad.status, "format");
    assert.deepEqual(bad.invalid, ["date"]);
    assert.equal(bad.paramType, "date");
    assert.equal(bad.empty, false);
    assert.equal(prepareLabRequest({ ...base, text, params: ["", "", ""] }).empty, true);
    const ok = prepareLabRequest({ ...base, text, type: "video", basis: "3-07", params: ["30.10", "14.35", "касса 2"] });
    assert.deepEqual(ok.req, { object: "station_cam", type: "video", basis: "3-07", params: ["2026-10-30", "14:35", "2"] });
  });

  test("отпечаток заявки — по id объекта, не по тексту", async () => {
    const a = prepareLabRequest({ ...base, text: "бутылку воды" }).req;
    const b = prepareLabRequest({ ...base, text: "Бутылка воды из гримёрки № 4" }).req;
    assert.equal(await labFingerprint(a), await labFingerprint(b));
  });
});

describe("«Мои заявки» (labOrders)", () => {
  test("новые сверху, номер — по порядку подачи, названия из каталога, итог и заключение", () => {
    const catalog = {
      types: [{ id: "chem", title: "Химическое исследование" }],
      objects: [{ id: "water", title: "Бутылка воды", ref: "1-09, поз. 3" }],
    };
    const log = [
      { fp: "a", t: "2026-10-21T10:00:00.000Z", object: "water", type: "chem", basis: "1-01", params: [], stage: 1, ok: false, doc: null },
      { fp: "b", t: "2026-10-21T10:05:00.000Z", object: "water", type: "chem", basis: "1-09", params: [], stage: 1, ok: true, doc: null },
      { fp: "c", t: "2026-10-21T10:06:00.000Z", object: "gone", type: "x", basis: "1-09", ok: true, doc: "2-01" },
    ];
    const entry = { doc: null, title: "Бутылка воды: химическое исследование", html: "<p>…</p>" };
    const rows = labOrders(log, catalog, { b: { stage: 1, entry } });
    assert.deepEqual(rows.map((r) => r.no), [3, 2, 1]);
    assert.equal(rows[1].objectTitle, "Бутылка воды");
    assert.equal(rows[1].ref, "1-09, поз. 3");
    assert.equal(rows[1].typeTitle, "Химическое исследование");
    assert.equal(rows[1].entry, entry);
    assert.equal(rows[2].ok, false);
    assert.equal(rows[2].entry, null);
    assert.equal(rows[0].objectTitle, "gone", "объекта нет в каталоге — id");
    assert.equal(rows[0].entry, null, "заключение не восстановлено");
    assert.deepEqual(labOrders(undefined, catalog), []);
  });
});
