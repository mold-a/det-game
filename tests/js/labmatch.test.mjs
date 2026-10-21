// Распознавание объекта лаборатории (docs/02): те же векторы, что у pytest — tests/vectors/lab-match.json.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { labTokens, resolveObject, TITLE_STEM_MIN, TITLE_STOPWORDS } from "../../site/assets/js/core/labmatch.js";

const V = JSON.parse(readFileSync(new URL("../vectors/lab-match.json", import.meta.url), "utf8"));
const obj = (id, title, ...aliases) => ({ id, title, aliases });

test("векторов достаточно и покрыты все статусы", () => {
  assert.deepEqual(new Set(V.resolve.map((c) => c.expected.status)), new Set(["ok", "ambiguous", "none"]));
  assert.ok(V.resolve.length >= 40 && V.tokens.length >= 8);
  for (const c of V.resolve) assert.ok(c.catalog in V.catalogs, c.catalog);
});

for (const c of V.tokens) {
  test(`labTokens: ${JSON.stringify(c.input)}`, () => {
    assert.deepEqual(labTokens(c.input), c.tokens);
  });
}

for (const c of V.resolve) {
  test(`resolveObject ${c.catalog}: ${JSON.stringify(c.input)} — ${c.note}`, () => {
    assert.deepEqual(resolveObject(c.input, V.catalogs[c.catalog]), c.expected);
  });
}

test("labTokens: пустая строка, пунктуация, «ё»", () => {
  assert.deepEqual(labTokens(""), []);
  assert.deepEqual(labTokens("  ?!  "), []);
  assert.deepEqual(labTokens("«Гримёрка» № 4, —  бутылка!"), ["гримерка", "4", "бутылка"]);
});

test("название — алиас из токенов не короче порога", () => {
  assert.equal(TITLE_STEM_MIN, 3);
  const objects = [obj("water", "Бутылка воды из гримёрки № 4"), obj("phone", "Телефон погибшего")];
  assert.deepEqual(resolveObject("Бутылка воды из гримёрки № 4", objects), { status: "ok", id: "water" });
  assert.deepEqual(resolveObject("Телефон погибшего", objects), { status: "ok", id: "phone" });
  assert.deepEqual(resolveObject("а б", [obj("x", "а б")]), { status: "none" });
});

test("служебные слова не становятся основами названия", () => {
  for (const w of ["для", "при", "над", "под", "без", "или", "что", "как", "это"]) assert.ok(TITLE_STOPWORDS.has(w), w);
  const objects = [obj("case", "Футляр для очков")];
  assert.deepEqual(resolveObject("Футляр для очков", objects), { status: "ok", id: "case" });
  assert.deepEqual(resolveObject("очков футляр", objects), { status: "ok", id: "case" });
  assert.deepEqual(resolveObject("для", objects), { status: "none" });
});

test("ключи из кармана пальто: pos важнее порядка в каталоге", () => {
  const keys = obj("keys", "Связка ключей", "ключ");
  const coat = obj("coat", "Пальто серое", "пальто");
  assert.deepEqual(resolveObject("ключи из кармана пальто", [keys, coat]), { status: "ok", id: "keys" });
  assert.deepEqual(resolveObject("ключи из кармана пальто", [coat, keys]), { status: "ok", id: "keys" });
  assert.deepEqual(resolveObject("пальто, ключи", [keys, coat]), { status: "ok", id: "coat" });
});

test("score решает при равном pos; равный ключ — ambiguous в порядке каталога", () => {
  const a = obj("a", "Аа", "бутылк");
  const b = obj("b", "Бб", "бутылк вод");
  assert.deepEqual(resolveObject("бутылка воды", [a, b]), { status: "ok", id: "b" });
  assert.deepEqual(resolveObject("бутылка", [a, b]), { status: "ok", id: "a" });
  const objs = [obj("z", "Зз", "кув"), obj("a", "Аа", "кув"), obj("m", "Мм", "кув")];
  assert.deepEqual(resolveObject("кувшин", objs), { status: "ambiguous", ids: ["z", "a", "m"] });
});

test("пустой ввод, пустой каталог, объект без aliases", () => {
  const objs = [obj("keys", "Связка ключей", "ключ")];
  assert.deepEqual(resolveObject("", objs), { status: "none" });
  assert.deepEqual(resolveObject("  ", objs), { status: "none" });
  assert.deepEqual(resolveObject("ключи", []), { status: "none" });
  assert.deepEqual(resolveObject("Телефон погибшего", [{ id: "phone", title: "Телефон погибшего" }]), { status: "ok", id: "phone" });
});

test("повтор основы требует двух токенов; основы не обязаны идти по порядку", () => {
  const pair = obj("pair", "Пара", "бут бут");
  assert.deepEqual(resolveObject("бутылка", [pair]), { status: "none" });
  assert.deepEqual(resolveObject("бутылка бутон", [pair]), { status: "ok", id: "pair" });
  const cam = obj("cam", "Камеры вокзала", "камер вокзал");
  assert.deepEqual(resolveObject("вокзал камера", [cam]), { status: "ok", id: "cam" });
  assert.deepEqual(resolveObject("камеры", [cam]), { status: "none" });
});
