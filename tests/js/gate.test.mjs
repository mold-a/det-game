// Профили закрытых этапов (docs/02 §3.10): core/gate.js — адрес из пакета этапа, слияние поиска «Круга»,
// чтение прогресса и кеш; pages/shell.js — ключ из фрагмента убирается, «to=<slug>» остаётся.
import { test } from "node:test";
import assert from "node:assert/strict";

import { randomBytes, b64uEncode } from "../../site/assets/js/core/crypto.js";
import { newState } from "../../site/assets/js/core/state.js";
import {
  gateTarget,
  profileHref,
  pageIndex,
  mergeDirectory,
  openedStages,
  unlockedPages,
  GATE_CACHE,
} from "../../site/assets/js/core/gate.js";
import { makePub, makePack, sealPack, fakeFetch } from "./fixtures.mjs";

const KEY_A = b64uEncode(randomBytes(32));
const KEY_B = b64uEncode(randomBytes(32));
const LATER = { slug: "krug-later", type: "social", key: KEY_A, name: "Поздний Тестовый", position: "тестовая должность" };
const KADR = { slug: "kadr-late", type: "photo", key: KEY_B, name: "Фото Поздняя", position: null };

function memStorage(init = {}) {
  const m = new Map(Object.entries(init));
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
    _map: m,
  };
}

test("gateTarget: slug из #to=… (и из #k=…&to=…), чужое и пустое — null", () => {
  assert.equal(gateTarget("#to=krug-later"), "krug-later");
  assert.equal(gateTarget("#k=abc_-&to=kadr-late"), "kadr-late");
  assert.equal(gateTarget("to=krug-x"), "krug-x");
  assert.equal(gateTarget(""), null);
  assert.equal(gateTarget("#search"), null);
  assert.equal(gateTarget("#to=../../etc"), null);
  assert.equal(gateTarget("#to=<script>"), null);
});

test("profileHref: тот же адрес, что в QR (/p/<slug>/#k=<ключ>)", () => {
  assert.equal(profileHref(LATER), `/p/krug-later/#k=${KEY_A}`);
});

test("pageIndex: поле pages пакетов → Map по slug, мусор отброшен", () => {
  const idx = pageIndex({ 2: { pages: [LATER, { slug: "BAD SLUG", key: "x" }, { slug: "no-key" }] }, 3: { pages: [KADR] }, 1: {} });
  assert.deepEqual([...idx.keys()].sort(), ["kadr-late", "krug-later"]);
  assert.equal(idx.get("krug-later").position, "тестовая должность");
});

test("mergeDirectory: закрытый пункт открывается, новый добавляется по алфавиту, «Кадр» не попадает", () => {
  const existing = [
    { slug: "a", name: "Аверин Пётр", position: "актёр", closed: false },
    { slug: "krug-later", name: "Поздний Тестовый", position: "", closed: true },
    { slug: "z", name: "Яшин Олег", position: "", closed: false },
  ];
  const later2 = { ...LATER, slug: "krug-new", name: "Борисов Новый", key: KEY_B };
  const out = mergeDirectory(existing, pageIndex({ 2: { pages: [LATER, later2, KADR] } }));
  assert.deepEqual(out.map((e) => e.slug), ["a", "krug-new", "krug-later", "z"]);
  const later = out.find((e) => e.slug === "krug-later");
  assert.equal(later.closed, false);
  assert.equal(later.position, "тестовая должность");
  assert.equal(later.href, profileHref(LATER));
  assert.equal(out.find((e) => e.slug === "a").href, undefined); // открытый пункт сборки не трогается
});

test("openedStages: этапы 1..stage, у которых есть ключ", () => {
  assert.deepEqual(openedStages({ stage: 3, keys: { 1: "a", 3: "c" } }), [1, 3]);
});

async function world(stage) {
  const pub = makePub();
  const keys = {};
  const files = { "/data/public.json": pub };
  for (let n = 1; n <= 3; n++) {
    const k = randomBytes(32);
    keys[n] = b64uEncode(k);
    const pages = n === 2 ? [LATER] : n === 3 ? [KADR] : [];
    files[`/data/pack-${n}.json`] = await sealPack(k, n, { ...makePack(n, []), pages });
  }
  const st = newState({ gameId: pub.gameId, saltsId: pub.saltsId, stage, keys: Object.fromEntries(Object.entries(keys).filter(([n]) => n <= stage)) });
  const storage = memStorage({ [`detgame:${pub.gameId}`]: JSON.stringify(st) });
  return { pub, files, storage, st };
}

test("unlockedPages: без прогресса — пусто; этап 1 — пусто; этап 2 — профиль этапа 2, но не 3", async () => {
  const w1 = await world(1);
  assert.equal((await unlockedPages({ storage: memStorage(), fetchFn: fakeFetch(w1.files) })).size, 0);
  assert.equal((await unlockedPages({ storage: w1.storage, fetchFn: fakeFetch(w1.files) })).size, 0);
  const w2 = await world(2);
  const idx = await unlockedPages({ storage: w2.storage, fetchFn: fakeFetch(w2.files) });
  assert.deepEqual([...idx.keys()], ["krug-later"]);
  assert.equal(idx.get("krug-later").key, KEY_A);
});

test("unlockedPages: другой набор солей или битый прогресс — пусто; сеть подвела — пусто, без исключения", async () => {
  const w = await world(3);
  const other = { ...w.files, "/data/public.json": makePub({ saltsId: "other" }) };
  assert.equal((await unlockedPages({ storage: w.storage, fetchFn: fakeFetch(other) })).size, 0);
  const broken = memStorage({ [`detgame:${w.pub.gameId}`]: "{нет" });
  assert.equal((await unlockedPages({ storage: broken, fetchFn: fakeFetch(w.files) })).size, 0);
  assert.equal((await unlockedPages({ storage: w.storage, fetchFn: fakeFetch({}) })).size, 0);
  const noPack3 = { ...w.files };
  delete noPack3["/data/pack-3.json"];
  assert.deepEqual([...(await unlockedPages({ storage: w.storage, fetchFn: fakeFetch(noPack3) })).keys()], ["krug-later"]);
});

test("unlockedPages: кеш в sessionStorage по набору этапов; новый этап — кеш пересобирается", async () => {
  const w = await world(2);
  const session = memStorage();
  await unlockedPages({ storage: w.storage, session, fetchFn: fakeFetch(w.files) });
  assert.ok(session.getItem(GATE_CACHE));
  // второй раз пакеты не нужны: fetch отдаёт только public.json
  const onlyPub = fakeFetch({ "/data/public.json": w.files["/data/public.json"] });
  assert.deepEqual([...(await unlockedPages({ storage: w.storage, session, fetchFn: onlyPub })).keys()], ["krug-later"]);
  // открыт этап 3 (та же партия: те же соли) — подпись кеша другая, пакеты читаются заново
  const w3 = await world(3);
  const idx = await unlockedPages({ storage: w3.storage, session, fetchFn: fakeFetch(w3.files) });
  assert.deepEqual([...idx.keys()].sort(), ["kadr-late", "krug-later"]);
});

test("shell.takeHashKey: ключ забирается и убирается из адреса, to=<slug> остаётся", async () => {
  globalThis.window ??= {};
  globalThis.document ??= { body: { dataset: {} }, getElementById: () => null };
  const { takeHashKey } = await import("../../site/assets/js/pages/shell.js");
  const calls = [];
  const hist = { state: null, replaceState: (s, t, url) => calls.push(url) };
  assert.equal(takeHashKey({ hash: "#k=KEY1&to=krug-later", pathname: "/p/kadr-late-stub/", search: "" }, hist), "KEY1");
  assert.equal(calls.at(-1), "/p/kadr-late-stub/#to=krug-later");
  assert.equal(takeHashKey({ hash: "#k=KEY2", pathname: "/p/x/", search: "" }, hist), "KEY2");
  assert.equal(calls.at(-1), "/p/x/");
});
