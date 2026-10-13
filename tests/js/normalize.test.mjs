// Нормализация (docs/02 §2): те же векторы, что у pytest — tests/vectors/normalize.json.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { TYPES, base, normalize } from "../../site/assets/js/core/normalize.js";

const VECTORS = JSON.parse(readFileSync(new URL("../vectors/normalize.json", import.meta.url), "utf8"));

test("векторов не меньше 60 и покрыты все типы", () => {
  assert.ok(Array.isArray(VECTORS));
  assert.ok(VECTORS.length >= 60, `векторов ${VECTORS.length}`);
  assert.deepEqual(new Set(VECTORS.map((c) => c.type)), new Set(TYPES));
});

for (const c of VECTORS) {
  test(`${c.type}: ${JSON.stringify(c.input)}`, () => {
    const got = normalize(c.type, c.input, { defaultYear: c.default_year });
    assert.equal(got, c.expected);
  });
}

test("base: пример из docs/02", () => {
  assert.equal(base(" Бронхиальная  астма! "), "бронхиальная астма");
  assert.equal(base(""), "");
});

test("неизвестный тип — исключение", () => {
  assert.throws(() => normalize("color", "red"));
});

test("date из двух групп без defaultYear — исключение, из трёх — нет", () => {
  assert.throws(() => normalize("date", "05.03"));
  assert.equal(normalize("date", "05.03.2026"), "2026-03-05");
});

test("граничные случаи времени и дат совпадают с pytest", () => {
  const time = [
    ["00:00", "00:00"], ["0:59", "00:59"], ["23:0", "23:00"], ["100", "01:00"], ["2359", "23:59"],
    ["0000", "00:00"], ["23:60", null], ["-1:30", "01:30"], ["1:2:3", null],
    ["99999999999999999999:15", null], ["1".repeat(5000) + ":15", null],
  ];
  for (const [raw, exp] of time) assert.equal(normalize("time", raw), exp, raw.slice(0, 30));
  const date = [
    ["31.01.2026", "2026-01-31"], ["28.02.2026", "2026-02-28"], ["31.06.2026", null],
    ["29.02.1900", null], ["29.02.1600", "1600-02-29"], ["01.01.9999", "9999-01-01"],
    ["1".repeat(5000) + ".01.2026", null],
  ];
  for (const [raw, exp] of date) assert.equal(normalize("date", raw, { defaultYear: 2026 }), exp, raw.slice(0, 30));
});

test("нестроковый ввод — невалидно", () => {
  assert.equal(normalize("multi", ["a", 1]), null);
  assert.equal(normalize("choice", ["a"]), null);
  assert.equal(normalize("text", null), null);
  assert.equal(normalize("text", undefined), null);
});
